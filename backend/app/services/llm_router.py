"""
AXonic — LLM Router
Routes tasks to the right model:
  - Event generation   → Llama 3.3 70B via Groq (fast, near-free)
  - Report (free tier) → Gemini 2.5 Flash (LAUNCH/HOLD/KILL decision report)
  - Report (paid tier) → Gemini 2.5 Flash with deeper persona + private-network + tier breakdown

Output schema stays consistent with report_agent.py and supabase_schema.sql:
  decision, confidence_score, conversion_impact, brand_risk, failure_mode,
  persona_reactions, private_network, recommendations, etc.
"""

import os
import json
import re
import logging

from groq import Groq
from google import genai
from google.genai import types

logger = logging.getLogger("axonic.llm_router")

# ── Model names (overridable via .env) ───────────────────────────────────────
GROQ_MODEL   = os.environ.get("GROQ_MODEL",   "llama-3.3-70b-versatile")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ── Lazy-initialised clients ─────────────────────────────────────────────────
_groq_client    = None
_gemini_client  = None


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_gemini() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env")
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_event_prompt(campaign: dict) -> str:
    """Llama prompt — Indian market simulation event generator."""
    name        = campaign.get("name", "Unnamed Campaign")
    description = campaign.get("description", "")
    platform    = campaign.get("platform", "Instagram")
    audience    = campaign.get("audience", "Indian consumers")
    tone        = campaign.get("tone", "Inspirational")
    goal        = campaign.get("goal", "brand awareness")

    strategy_prompt = campaign.get("prompt", "")
    strategy_docs   = campaign.get("strategy_docs", "")

    if strategy_prompt:
        campaign_context = f"Strategy Prompt: {strategy_prompt}\n"
        if strategy_docs:
            campaign_context += f"Strategy Documents: {strategy_docs}\n"
    else:
        campaign_context = f"""
  Name        : {name}
  Description : {description}
  Platform    : {platform}
  Audience    : {audience}
  Tone        : {tone}
  Goal        : {goal}
"""

    return f"""You are a senior marketing simulation analyst for the Indian digital market.

Simulate how this campaign realistically unfolds across 3 stages, reflecting genuine Indian consumer behaviour:
- Tier1 (Mumbai/Delhi/Bengaluru) vs Tier2 (Pune/Jaipur/Kochi) vs Tier3 (Patna/Ranchi) reactions diverge
- Regional language + Hinglish dynamics (not one homogenous audience)
- Price sensitivity + value-for-money mindset
- WhatsApp forward culture — private trust beats public ads
- Influencer hierarchy (nano / micro / mega) — each scales differently
- IST time peaks (Reels 7–10 PM, WhatsApp forwards 8–9 AM + 9–10 PM)
- IPL / festive (Diwali/Onam/Durga Puja) / salary-week effects
- UPI cashback + EMI readiness
- ASCI / SEBI / FSSAI guardrails where relevant

Campaign/Strategy:
{campaign_context}

Generate exactly 3 simulation stages — the Indian 3-stage reaction model:

Stage 1 — PUBLIC REACTION   (first 24h, emotional + fast judgement on Instagram/Twitter)
Stage 2 — AMPLIFICATION     (days 2–4, influencers + YouTube reviews shape opinion)
Stage 3 — PRIVATE SPREAD    (days 5–7, WhatsApp/peer forwards either cement or kill the campaign)

For each stage provide:
  - event          : realistic 1–2 sentence description (mention tier if relevant)
  - metric         : one believable quantified metric (e.g. "Reels save-rate 4.2x", "CPM ₹18 in Tier2")
  - sentiment      : one of  positive | negative | neutral | mixed
  - dominant_tier  : Tier1 | Tier2 | Tier3 | mixed  — which tier drove this stage
  - sample_quote   : a short authentic pull-quote a real Indian user might post (Hinglish ok, under 20 words)

Respond ONLY with a valid JSON array — no markdown, no explanation:
[
  {{"round": 1, "stage": "public_reaction", "event": "...", "metric": "...", "sentiment": "...", "dominant_tier": "...", "sample_quote": "..."}},
  {{"round": 2, "stage": "amplification",   "event": "...", "metric": "...", "sentiment": "...", "dominant_tier": "...", "sample_quote": "..."}},
  {{"round": 3, "stage": "private_spread",  "event": "...", "metric": "...", "sentiment": "...", "dominant_tier": "...", "sample_quote": "..."}}
]"""


def _build_report_prompt(campaign: dict, events: list, is_paid: bool) -> str:
    """Gemini prompt — AXonic Campaign Decision Report (LAUNCH/HOLD/KILL)."""
    name        = campaign.get("name", "Unnamed Campaign")
    description = campaign.get("description", "")
    platform    = campaign.get("platform", "Instagram")
    audience    = campaign.get("audience", "Indian consumers")
    tone        = campaign.get("tone", "Inspirational")
    goal        = campaign.get("goal", "brand awareness")

    strategy_prompt = campaign.get("prompt", "")
    strategy_docs   = campaign.get("strategy_docs", "")

    if strategy_prompt:
        campaign_context = f"Strategy Prompt: {strategy_prompt}\n"
        if strategy_docs:
            campaign_context += f"Strategy Documents: {strategy_docs}\n"
    else:
        campaign_context = f"""
  Name        : {name}
  Description : {description}
  Platform    : {platform}
  Audience    : {audience}
  Tone        : {tone}
  Goal        : {goal}
"""

    events_text = "\n".join(
        f"  Stage {e.get('round', i + 1)} [{e.get('stage', 'n/a')}]: "
        f"{e.get('event', '')} | {e.get('metric', '')} | "
        f"sentiment={e.get('sentiment', 'neutral')} | "
        f"dominant_tier={e.get('dominant_tier', 'mixed')}"
        + (f" | quote: \"{e.get('sample_quote', '')}\"" if e.get('sample_quote') else "")
        for i, e in enumerate(events)
    )

    paid_fields = ""
    if is_paid:
        paid_fields = """
  "regional_breakdown": {
    "tier1_cities":  "Expected performance in Mumbai / Delhi / Bengaluru — cite specific driver",
    "tier2_cities":  "Expected performance in Pune / Jaipur / Kochi — cite specific driver",
    "tier3_rural":   "Viability in smaller cities — cite specific driver, or state that coverage is thin"
  },
  "budget_estimate": {
    "minimum_budget_inr": "₹X for a meaningful Tier1 test",
    "optimal_budget_inr": "₹X for full target reach across tiers",
    "expected_cpm_inr":   "₹X per 1,000 impressions (tier-weighted)",
    "roi_estimate":       "Expected return on every ₹1 spent with reasoning"
  },
  "creative_suggestions": [
    "Specific creative/messaging/pricing change with expected per-tier impact",
    "Specific creative/messaging/pricing change with expected per-tier impact",
    "Specific creative/messaging/pricing change with expected per-tier impact"
  ],"""

    tier_note = (
        "You are in PREMIUM mode — include regional breakdown, budget estimates and creative suggestions."
        if is_paid else
        "You are in FREE mode — keep the report tight but still decisive."
    )

    return f"""You are AXonic Intelligence — a senior Indian marketing strategist generating a Campaign Decision Report. {tier_note}

Campaign/Strategy:
{campaign_context}

Simulation Results (3-stage Indian reaction model):
{events_text}

[Decision rigor — MANDATORY]
- decision must be exactly LAUNCH, HOLD, or KILL
- confidence_score must be a single integer 0–100 (no ranges, no "around 70")
- Provide expected outcome (1–2 lines on realistic market behaviour)
- Business impact: conversion_impact = High|Medium|Low, brand_risk = High|Medium|Low
- If HOLD: state what must change to move to LAUNCH
- If KILL: state the dominant failure_mode

[Failure mode detection — required when HOLD or KILL]
Identify whether failure is due to:
- pricing       (price perception mismatch)
- cultural      (language/region/festival-timing mismatch)
- trust         (skepticism, brand perception, past associations)
- differentiation (campaign reads like noise — nothing distinguishing)
Label ONE dominant failure mode. For LAUNCH, set failure_mode to null.

[Persona quantification — required]
For persona_reactions, quantify each tier:
- sentiment_split: approximate % positive vs negative (e.g. "~65% positive, 35% skeptical")
- dominant_driver: price | trust | influencer | brand | peer_validation
- conversion_likelihood: High | Medium | Low

[Private network dynamics — required]
Explicitly analyse WhatsApp/peer/family forward behaviour:
- Does the campaign survive when it crosses from public platforms into private chats?
- Does trust amplify or decay in private networks?
If coverage is thin, state it explicitly — do not fabricate.

[Actionability rule]
Every recommendation must include: the specific change, the expected per-tier impact, and the mechanism (not just "improve messaging").

[Analysis depth — use genuinely Indian context]
- Consumer psychology: SEC A/B/C/D, value-for-money, social proof, aspirational buying
- Platform dynamics on {platform} in India (algorithm traits, content formats, IST peaks)
- Regional/language: Hindi / Tamil / Bengali / Marathi market splits
- Regulatory: ASCI guidelines, SEBI (financial campaigns), FSSAI (food), TRAI (telecom)
- Seasonality: IPL / festive calendar / salary week / exam season

Respond ONLY with valid JSON — no markdown, no preamble:
{{{paid_fields}
  "decision": "LAUNCH" | "HOLD" | "KILL",
  "decision_reason": "one sharp sentence explaining the call",
  "confidence_score": 0-100,
  "expected_outcome": "1–2 lines on realistic market behaviour (reach, engagement, conversion shape)",
  "business_impact": {{
    "conversion_impact": "High" | "Medium" | "Low",
    "brand_risk":        "High" | "Medium" | "Low"
  }},
  "failure_mode": "pricing" | "cultural" | "trust" | "differentiation" | null,
  "what_to_change_for_launch": "Only if HOLD: exactly what to change. Else null.",
  "persona_reactions": {{
    "tier1_metros": {{
      "sentiment_split":       "approximate % positive vs negative",
      "dominant_driver":       "price | trust | influencer | brand | peer_validation",
      "conversion_likelihood": "High | Medium | Low",
      "pull_quote":            "A real persona quote from the simulation (or stated as unavailable)"
    }},
    "tier2_cities": {{
      "sentiment_split":       "...",
      "dominant_driver":       "...",
      "conversion_likelihood": "...",
      "pull_quote":            "..."
    }},
    "tier3_rural": {{
      "sentiment_split":       "...",
      "dominant_driver":       "...",
      "conversion_likelihood": "...",
      "pull_quote":            "..."
    }}
  }},
  "private_network_dynamics": {{
    "survives_whatsapp_layer": true | false,
    "trust_movement":          "amplifies | decays | neutral",
    "explanation":             "One sentence on why it does or does not translate into private-network trust"
  }},
  "risks": [
    "Specific Indian-context risk 1 (ASCI / cultural / pricing / timing)",
    "Specific risk 2",
    "Specific risk 3"
  ],
  "opportunities": [
    "Specific opportunity 1 (WhatsApp virality / IPL timing / UPI cashback hook / festive calendar)",
    "Specific opportunity 2",
    "Specific opportunity 3"
  ],
  "recommendations": [
    "Actionable step 1: specific change + expected per-tier impact + mechanism",
    "Actionable step 2",
    "Actionable step 3"
  ],
  "simulation_limitations": "State honestly if any tier/segment coverage was thin, or 'None' if all tiers are well-represented",
  "indian_market_insight": "One non-obvious insight a senior strategist would add"
}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_events(campaign: dict) -> tuple:
    """Calls Llama 3.3 70B via Groq to generate 3-stage simulation events.
    Returns (events_list, usage_dict).
    """
    client = _get_groq()
    prompt = _build_event_prompt(campaign)

    logger.info(f"[Groq/{GROQ_MODEL}] Generating events for: {campaign.get('name')}")

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1100,
        temperature=0.75,
    )

    raw   = response.choices[0].message.content.strip()
    usage = {
        "model":      GROQ_MODEL,
        "provider":   "groq",
        "tokens_in":  response.usage.prompt_tokens,
        "tokens_out": response.usage.completion_tokens,
    }

    logger.info(
        f"[Groq] Events done — {usage['tokens_in']} in / {usage['tokens_out']} out"
    )

    events = _safe_parse_json(raw, fallback=_fallback_events(campaign))
    return events, usage


def generate_report(campaign: dict, events: list, tier: str = "free") -> tuple:
    """Calls Gemini 2.5 Flash to generate the Campaign Decision Report.
    Paid tier gets higher token budget + deeper prompt sections.
    Returns (report_dict, usage_dict).
    """
    client = _get_gemini()

    is_paid    = (tier == "paid")
    max_tokens = 3000 if is_paid else 1600
    prompt     = _build_report_prompt(campaign, events, is_paid)

    logger.info(f"[Gemini/{GEMINI_MODEL}] Generating report — tier: {tier}")

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=0.35,
            response_mime_type="application/json",
        ),
    )

    raw = (response.text or "").strip()

    usage = {
        "model":      GEMINI_MODEL,
        "provider":   "gemini",
        "tier":       tier,
        "tokens_in":  getattr(response.usage_metadata, "prompt_token_count",      0),
        "tokens_out": getattr(response.usage_metadata, "candidates_token_count",  0),
    }

    logger.info(
        f"[Gemini] Report done — {usage['tokens_in']} in / {usage['tokens_out']} out"
    )

    report = _safe_parse_json(raw, fallback=_fallback_report(campaign))
    report = _normalize_report(report)
    return report, usage


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_parse_json(raw, fallback):
    """Parse JSON safely — accepts raw string (stripping markdown fences) or dict."""
    if isinstance(raw, (dict, list)):
        return raw
    if not raw:
        logger.warning("Empty LLM response — using fallback.")
        return fallback
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$",           "", cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(f"JSON parse failed ({exc}) — using fallback.")
        return fallback


def _normalize_report(report: dict) -> dict:
    """Coerce / validate critical fields so downstream code + DB columns stay consistent.
    - decision uppercased to LAUNCH/HOLD/KILL
    - confidence_score clamped to int 0–100
    - failure_mode forced null when decision == LAUNCH
    """
    if not isinstance(report, dict):
        return report

    # Decision
    decision = str(report.get("decision", "")).strip().upper()
    if decision not in ("LAUNCH", "HOLD", "KILL"):
        # Legacy verdict mapping (migrate smoothly from older schema)
        legacy = str(report.get("verdict", "")).strip().lower()
        decision = {
            "strong campaign": "LAUNCH",
            "risky campaign":  "HOLD",
            "weak campaign":   "KILL",
        }.get(legacy, "HOLD")
    report["decision"] = decision

    # Confidence score — clamp to int 0–100
    try:
        score = int(float(report.get("confidence_score", 50)))
    except (TypeError, ValueError):
        score = 50
    report["confidence_score"] = max(0, min(100, score))

    # Failure mode — null when LAUNCH
    if decision == "LAUNCH":
        report["failure_mode"] = None
    else:
        fm = report.get("failure_mode")
        if fm not in ("pricing", "cultural", "trust", "differentiation", None):
            fm = None
        report["failure_mode"] = fm

    # Business impact — ensure dict shape exists for frontend
    bi = report.get("business_impact") or {}
    if not isinstance(bi, dict):
        bi = {}
    bi.setdefault("conversion_impact", "Medium")
    bi.setdefault("brand_risk",        "Medium")
    report["business_impact"] = bi

    return report


def _fallback_events(campaign: dict) -> list:
    """Rule-based fallback events when Groq is unavailable — matches the 3-stage schema."""
    platform = campaign.get("platform", "Instagram")
    tone     = campaign.get("tone",     "Inspirational")
    audience = campaign.get("audience", "Indian consumers")

    r2 = {
        "Aggressive":    f"Skeptical {audience} pushed back on hard-sell messaging. Trust score fell 9%.",
        "Inspirational": f"Strong emotional resonance. Save-rate jumped 4.2x in 48 hours across Tier1 metros.",
        "Informational": f"High bookmark rate — audience saved content for later reference.",
        "Emotional":     f"Sharing wave triggered within close-knit community groups. Organic reach +280%.",
        "Humorous":      f"Meme remixes appeared on Twitter within 36 hours. Earned media worth ₹2.1L.",
    }.get(tone, f"Moderate engagement. {audience} responded cautiously to initial messaging.")

    r3 = {
        "Instagram": "Reels algorithm amplified reach 7x. Three micro-influencers (50K–200K) reshared.",
        "Twitter":   "Trending hashtag entered top-15 in target region. Journalists picked up the story.",
        "LinkedIn":  "Four industry leaders reshared; three inbound partnership queries arrived.",
        "WhatsApp":  "Forward chain spread across family + interest groups — reached 6 degrees of separation.",
        "YouTube":   "Algorithm surfaced video to non-subscribers; avg watch time up 3.8 min per session.",
    }.get(platform, f"Organic spread on {platform}. Retention above category benchmark.")

    return [
        {
            "round": 1,
            "stage": "public_reaction",
            "event": f"Campaign launched on {platform} targeting {audience}. "
                     f"Tier1 metros absorbed first impressions.",
            "metric": "Reach: 12,400 in first 6 hours | CTR 1.9%",
            "sentiment": "neutral",
            "dominant_tier": "Tier1",
            "sample_quote": "Ad looks interesting, but price kya hoga?",
        },
        {
            "round": 2,
            "stage": "amplification",
            "event": r2,
            "metric": "Engagement rate: 4.7% (category benchmark: 2.1%)",
            "sentiment": "positive",
            "dominant_tier": "mixed",
            "sample_quote": "Actually worth the hype — micro creator ne review bhi dala hai.",
        },
        {
            "round": 3,
            "stage": "private_spread",
            "event": r3,
            "metric": "Total reach: 1,87,000 | Cost-per-result: ₹3.20",
            "sentiment": "positive",
            "dominant_tier": "Tier2",
            "sample_quote": "Bhai group mein forward kar diya, sab bol rahe le lo.",
        },
    ]


def _fallback_report(campaign: dict) -> dict:
    """Minimal fallback report when Gemini is unavailable — matches new LAUNCH/HOLD/KILL schema."""
    return {
        "decision":           "HOLD",
        "decision_reason":    "Full analysis could not be generated — please retry.",
        "confidence_score":   50,
        "expected_outcome":   "Analysis unavailable.",
        "business_impact": {
            "conversion_impact": "Medium",
            "brand_risk":        "Medium",
        },
        "failure_mode":             "differentiation",
        "what_to_change_for_launch": "Re-run the analysis with a clearer campaign description.",
        "persona_reactions": {
            "tier1_metros": {
                "sentiment_split":       "unavailable",
                "dominant_driver":       "unavailable",
                "conversion_likelihood": "Low",
                "pull_quote":            "Analysis unavailable — please retry.",
            },
            "tier2_cities": {
                "sentiment_split":       "unavailable",
                "dominant_driver":       "unavailable",
                "conversion_likelihood": "Low",
                "pull_quote":            "Analysis unavailable — please retry.",
            },
            "tier3_rural": {
                "sentiment_split":       "unavailable",
                "dominant_driver":       "unavailable",
                "conversion_likelihood": "Low",
                "pull_quote":            "Analysis unavailable — please retry.",
            },
        },
        "private_network_dynamics": {
            "survives_whatsapp_layer": False,
            "trust_movement":          "neutral",
            "explanation":             "Analysis unavailable — retry with a valid API key.",
        },
        "risks":           [
            "Model response unavailable",
            "Please re-run for full analysis",
            "Check GEMINI_API_KEY in .env",
        ],
        "opportunities":   [
            "Retry with a more specific description",
            "Add detailed audience info",
            "Specify your campaign goal",
        ],
        "recommendations": [
            "Re-run the simulation",
            "Ensure API keys are valid",
            "Contact support if the issue persists",
        ],
        "simulation_limitations": "Full analysis failed — all tier coverage is unavailable.",
        "indian_market_insight":  "Analysis unavailable — please retry.",
    }