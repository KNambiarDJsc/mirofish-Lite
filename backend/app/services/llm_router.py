"""
AXonic — LLM Router
Routes tasks to the right model:
  - Event generation → Llama 3.3 70B via Groq (fast, near-free)
  - Report (free tier)  → Gemini 2.5 Flash (smart, cheap)
  - Report (paid tier)  → Gemini 2.5 Flash with deeper prompt + higher token budget
"""

import os
import json
import re
import logging

from groq import Groq
import google.generativeai as genai

logger = logging.getLogger("axonic.llm_router")

# ── Model names (overridable via .env) ───────────────────────────────────────
GROQ_MODEL   = os.environ.get("GROQ_MODEL",   "llama-3.3-70b-versatile")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-preview-04-17")

# ── Lazy-initialised clients ─────────────────────────────────────────────────
_groq_client       = None
_gemini_configured = False


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in .env")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _configure_gemini():
    global _gemini_configured
    if not _gemini_configured:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("LLM_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=api_key)
        _gemini_configured = True


# ── Prompt Builders ───────────────────────────────────────────────────────────

def _build_event_prompt(campaign: dict) -> str:
    """Llama prompt — Indian market simulation event generator."""
    name        = campaign.get("name", "Unnamed Campaign")
    description = campaign.get("description", "")
    platform    = campaign.get("platform", "Instagram")
    audience    = campaign.get("audience", "Indian consumers")
    tone        = campaign.get("tone", "Inspirational")
    goal        = campaign.get("goal", "brand awareness")
    
    # New simplified fields
    strategy_prompt = campaign.get("prompt", "")
    strategy_docs   = campaign.get("strategy_docs", "")

    campaign_context = ""
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

    return f"""You are a senior marketing simulation analyst who specialises in the Indian digital market.

Simulate how this campaign or marketing strategy will realistically unfold over 3 rounds.
Think authentically about Indian consumer behaviour:
- Regional language reactions (Hindi belt vs South India)
- Price sensitivity and value-for-money expectations
- WhatsApp forward culture and family group sharing
- Influencer micro-ecosystems (nano / micro / mega)
- Festival and cricket seasonality effects
- Tier 1 / Tier 2 / Tier 3 city dynamics
- UPI payment readiness and impulse-buy patterns

Campaign/Strategy Details:
{campaign_context}

Generate exactly 3 simulation rounds:
  Round 1 — Launch        (first 24 hours)
  Round 2 — Reaction      (days 2–4, real audience pushback or amplification)
  Round 3 — Spread/Decay  (days 5–7, viral breakout or audience fatigue)

For each round provide:
  - event     : realistic 1-2 sentence description
  - metric    : one believable quantified metric (e.g. "reach grew 340%", "CPM dropped to ₹18")
  - sentiment : one of  positive | negative | neutral | mixed

Respond ONLY with a valid JSON array — no markdown, no explanation:
[
  {{"round": 1, "event": "...", "metric": "...", "sentiment": "..."}},
  {{"round": 2, "event": "...", "metric": "...", "sentiment": "..."}},
  {{"round": 3, "event": "...", "metric": "...", "sentiment": "..."}}
]"""


def _build_report_prompt(campaign: dict, events: list, is_paid: bool) -> str:
    """Gemini prompt — AXonic intelligence report with Indian market depth."""
    name        = campaign.get("name", "Unnamed Campaign")
    description = campaign.get("description", "")
    platform    = campaign.get("platform", "Instagram")
    audience    = campaign.get("audience", "Indian consumers")
    tone        = campaign.get("tone", "Inspirational")
    goal        = campaign.get("goal", "brand awareness")

    # New simplified fields
    strategy_prompt = campaign.get("prompt", "")
    strategy_docs   = campaign.get("strategy_docs", "")

    campaign_context = ""
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
        f"  Round {e.get('round', i + 1)}: {e.get('event', '')} "
        f"[{e.get('metric', '')}] — {e.get('sentiment', 'neutral')}"
        for i, e in enumerate(events)
    )

    paid_fields = ""
    if is_paid:
        paid_fields = """
  "regional_breakdown": {
    "tier1_cities": "Expected performance in Mumbai / Delhi / Bangalore",
    "tier2_cities": "Expected performance in Pune / Jaipur / Lucknow / Kochi",
    "tier3_rural":  "Viability for smaller cities and rural audiences"
  },
  "budget_estimate": {
    "minimum_budget_inr": "₹X for a meaningful test run",
    "optimal_budget_inr": "₹X for full target reach",
    "expected_cpm_inr":   "₹X per 1,000 impressions",
    "roi_estimate":       "Expected return on every ₹1 spent"
  },"""

    tier_note = (
        "You are in PREMIUM mode — provide deeper analysis including regional breakdown and budget estimates."
        if is_paid else ""
    )

    return f"""You are AXonic Intelligence — an elite marketing analyst for the Indian market. {tier_note}

Campaign/Strategy:
{campaign_context}

Simulation Results:
{events_text}

Analyse this campaign using deep knowledge of:
- Indian consumer psychology (value-for-money mindset, social proof, trust signals, aspirational buying)
- Platform dynamics in India ({platform} user behaviour, algorithm traits, content formats)
- Regional and language nuances (Hindi / Tamil / Bengali / Marathi market splits)
- Price sensitivity across income segments (SEC A / B / C / D)
- Current digital trends: UPI payments, Reels culture, cricket/IPL seasonality, festive calendar
- Regulatory context: ASCI guidelines, SEBI rules for financial campaigns, FSSAI for food

Respond ONLY with valid JSON — no markdown, no extra text:
{{{paid_fields}
  "verdict": "Strong Campaign" | "Risky Campaign" | "Weak Campaign",
  "verdict_reason": "one clear sentence",
  "confidence_score": 0-100,
  "risks": [
    "Specific risk 1 with Indian context",
    "Specific risk 2",
    "Specific risk 3"
  ],
  "opportunities": [
    "Specific opportunity 1 (e.g. WhatsApp virality, IPL timing, UPI cashback hook)",
    "Specific opportunity 2",
    "Specific opportunity 3"
  ],
  "recommendations": [
    "Actionable step 1 (be precise, e.g. 'Run Reels at 8–10 pm IST when Delhi NCR engagement peaks')",
    "Actionable step 2",
    "Actionable step 3"
  ],
  "indian_market_insight": "One unique, non-obvious insight about this campaign for the Indian audience"
}}"""


# ── Public API ────────────────────────────────────────────────────────────────

def generate_events(campaign: dict) -> tuple:
    """
    Calls Llama 3.3 70B via Groq to generate simulation events.
    Returns: (events_list, usage_dict)
    """
    client = _get_groq()
    prompt = _build_event_prompt(campaign)

    logger.info(f"[Groq/{GROQ_MODEL}] Generating events for: {campaign.get('name')}")

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
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
    """
    Calls Gemini 2.5 Flash to generate the intelligence report.
    Paid tier gets a higher token budget and deeper prompt sections.
    Returns: (report_dict, usage_dict)
    """
    _configure_gemini()

    is_paid    = (tier == "paid")
    max_tokens = 2500 if is_paid else 1200
    prompt     = _build_report_prompt(campaign, events, is_paid)

    logger.info(f"[Gemini/{GEMINI_MODEL}] Generating report — tier: {tier}")

    model = genai.GenerativeModel(
        GEMINI_MODEL,
        generation_config=genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.35,
            response_mime_type="application/json",
        ),
    )

    response = model.generate_content(prompt)
    raw      = response.text.strip()

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
    return report, usage


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_parse_json(raw: str, fallback):
    """Strips markdown fences and parses JSON. Falls back gracefully."""
    try:
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$",           "", cleaned, flags=re.MULTILINE)
        return json.loads(cleaned.strip())
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning(f"JSON parse failed ({exc}) — using fallback.")
        return fallback


def _fallback_events(campaign: dict) -> list:
    """Rule-based fallback events when Groq is unavailable."""
    platform = campaign.get("platform", "Instagram")
    tone     = campaign.get("tone",     "Inspirational")
    audience = campaign.get("audience", "Indian consumers")

    r2 = {
        "Aggressive":    f"Skeptical {audience} pushed back on hard-sell messaging. Trust score fell 9%.",
        "Inspirational": f"Strong emotional resonance across {audience}. Save rate jumped 4.2× in 48 hours.",
        "Informational": f"High bookmark rate observed — {audience} saving content for future reference.",
        "Emotional":     f"Sharing wave triggered within close-knit community groups. Organic reach +280%.",
        "Humorous":      f"Meme remixes appeared on Twitter within 36 hours. Earned media worth ₹2.1L.",
    }.get(tone, f"Moderate engagement. {audience} responded cautiously to initial messaging.")

    r3 = {
        "Instagram": "Instagram Reels algorithm amplified reach 7×. Three micro-influencers (50K–200K followers) reshared.",
        "Twitter":   "Trending hashtag entered top-15 in target region. Journalists picked up the story.",
        "LinkedIn":  "Four industry leaders reshared the post, generating three inbound partnership queries.",
        "WhatsApp":  "Forward chain spread across family and interest groups — reached 6 degrees of separation.",
        "YouTube":   "Algorithm surfaced video to non-subscribers; average watch time up 3.8 minutes per session.",
    }.get(platform, f"Organic spread on {platform}. Audience retention above category benchmark.")

    return [
        {
            "round": 1,
            "event": f"Campaign launched on {platform} targeting {audience}. Initial impressions began accumulating across key pin codes.",
            "metric": "Reach: 12,400 in first 6 hours",
            "sentiment": "neutral",
        },
        {"round": 2, "event": r2, "metric": "Engagement rate: 4.7% (category benchmark: 2.1%)", "sentiment": "positive"},
        {"round": 3, "event": r3, "metric": "Total reach: 1,87,000 | Cost-per-result: ₹3.20", "sentiment": "positive"},
    ]


def _fallback_report(campaign: dict) -> dict:
    """Minimal fallback report when Gemini is unavailable."""
    return {
        "verdict":               "Risky Campaign",
        "verdict_reason":        "Full analysis could not be generated — please retry.",
        "confidence_score":      50,
        "risks":                 ["Model response unavailable", "Please re-run for full analysis", "Check GEMINI_API_KEY in .env"],
        "opportunities":         ["Retry with a more specific description", "Add detailed audience info", "Specify your campaign goal"],
        "recommendations":       ["Re-run the simulation", "Ensure API keys are valid", "Contact support if the issue persists"],
        "indian_market_insight": "Analysis unavailable — please retry.",
    }
