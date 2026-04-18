"""
OASIS Indian Market Persona Generator — AXonic
Weighted distributions + derived behavioral traits (price_sensitivity,
trust_factor, influence_susceptibility, decision_speed).
"""

import json
import logging
import random
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ..config import Config
from ..utils.llm_client import LLMClient
from .supabase_entity_reader import EntityNode
from .supabase_memory import get_memory

logger = logging.getLogger("axonic.persona_generator")


# ── Indian market distributions (reality-weighted, not uniform) ──────────────

TIER_DISTRIBUTION = {"Tier1": 0.25, "Tier2": 0.45, "Tier3": 0.30}

INCOME_DISTRIBUTION = {"High": 0.12, "UpperMiddle": 0.28, "Middle": 0.40, "LowerMiddle": 0.20}

LIFE_STAGE_DISTRIBUTION = {
    "Student": 0.20, "EarlyCareer": 0.30, "MidCareer": 0.25,
    "FamilyDecisionMaker": 0.20, "Senior": 0.05,
}

BEHAVIOR_DISTRIBUTION = {
    "PriceSensitive": 0.25, "ValueMaximizer": 0.20, "SkepticalResearcher": 0.15,
    "TrendDriven": 0.12, "BrandConscious": 0.08, "ImpulseBuyer": 0.08,
    "Aspirational": 0.07, "RiskAverse": 0.03, "CommunityDriven": 0.02,
}

DIGITAL_DISTRIBUTION = {
    "InstagramHeavy": 0.25, "YouTubeResearcher": 0.20, "WhatsAppForwarder": 0.20,
    "ShortVideoAddict": 0.10, "ReviewDriven": 0.10, "PassiveScroller": 0.10,
    "ActiveCommenter": 0.05,
}

LANGUAGE_DISTRIBUTION = {"English": 0.20, "Hinglish": 0.45, "Regional": 0.35}

TIER_CITY = {
    "Tier1": ["Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", "Pune", "Ahmedabad"],
    "Tier2": ["Jaipur", "Lucknow", "Kochi", "Indore", "Coimbatore", "Nagpur", "Chandigarh", "Bhopal", "Surat", "Vadodara"],
    "Tier3": ["Patna", "Ranchi", "Varanasi", "Guwahati", "Raipur", "Meerut", "Jalandhar", "Tiruchirappalli"],
}

TIER_AGE_RANGE = {"Tier1": (22, 45), "Tier2": (20, 50), "Tier3": (18, 55)}

ARCHETYPE_TRAITS = {
    "trend_driven":         "Follows Reels, early adopter, aesthetic-conscious.",
    "aspirational":         "Signals upward mobility, responds to premium positioning.",
    "skeptical_researcher": "Reads reviews, compares prices, distrusts paid promotion.",
    "early_adopter":        "Tech-forward, beta-tester mindset, follows startup news.",
    "value_hunter":         "UPI cashback chaser, coupon-driven, waits for sales.",
    "family_driven":        "WhatsApp family group is primary info source.",
    "whatsapp_forward":     "Shares news/memes/offers across groups, virality engine.",
    "price_sensitive":      "Waits for festive sales, buys on EMI, discount-responsive.",
}

BEHAVIOR_TO_ARCHETYPE = {
    "PriceSensitive": "price_sensitive", "ValueMaximizer": "value_hunter",
    "BrandConscious": "aspirational", "TrendDriven": "trend_driven",
    "SkepticalResearcher": "skeptical_researcher", "ImpulseBuyer": "trend_driven",
    "Aspirational": "aspirational", "RiskAverse": "skeptical_researcher",
    "CommunityDriven": "whatsapp_forward",
}

INDIAN_PROFESSIONS = {
    "Tier1": ["Product Manager", "Software Engineer", "Brand Manager", "Content Creator",
              "Startup Founder", "Marketing Lead", "UX Designer", "Consultant",
              "Data Scientist", "Doctor", "Corporate Lawyer", "Investment Banker"],
    "Tier2": ["Bank Clerk", "School Teacher", "Shop Owner", "Government Employee",
              "Small Business Owner", "Sales Executive", "Nurse", "College Student",
              "Accountant", "Insurance Agent", "Real Estate Agent", "Pharmacist"],
    "Tier3": ["Kirana Owner", "Farmer", "Auto Driver", "Factory Worker",
              "Tutor", "Anganwadi Worker", "Student", "Local Politician",
              "Daily Wage Worker", "Tailor", "Carpenter", "Homemaker"],
}

INDIVIDUAL_TYPES = {
    "consumer", "influencer", "celebrity", "expert", "journalist", "publicfigure",
    "person", "student", "professional", "creator", "reviewer", "finfluencer",
    "homemaker", "farmer",
}


# ── Weighted choice + trait derivation ───────────────────────────────────────

def _wchoice(dist: Dict[str, float]) -> str:
    opts, weights = list(dist.keys()), list(dist.values())
    return random.choices(opts, weights=weights, k=1)[0]


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def derive_behavioral_traits(
    tier: str, income: str, behavior: str, digital: str,
) -> Dict[str, float]:
    """Derive 4 decision-driving traits from persona dimensions."""
    ps, tf, isu, ds = 0.6, 0.5, 0.5, 0.5

    if tier == "Tier1":
        ps -= 0.15; tf += 0.05
    elif tier == "Tier2":
        ps += 0.10
    elif tier == "Tier3":
        ps += 0.15; tf += 0.05

    if income == "High":
        ps -= 0.20
    elif income == "UpperMiddle":
        ps -= 0.05
    elif income == "LowerMiddle":
        ps += 0.20

    bmap = {
        "PriceSensitive":      (0.25, 0, 0, 0),
        "ValueMaximizer":      (0.15, 0.10, 0, -0.05),
        "BrandConscious":      (-0.10, 0, 0.10, 0.05),
        "TrendDriven":         (-0.05, -0.05, 0.20, 0.20),
        "SkepticalResearcher": (0, 0.20, -0.10, -0.20),
        "ImpulseBuyer":        (-0.05, -0.10, 0.10, 0.30),
        "Aspirational":        (-0.10, 0, 0.15, 0.10),
        "RiskAverse":          (0.05, -0.10, -0.10, -0.15),
        "CommunityDriven":     (0, 0.15, 0.10, 0),
    }
    dp, dt, di, sd = bmap.get(behavior, (0, 0, 0, 0))
    ps += dp; tf += dt; isu += di; ds += sd

    dmap = {
        "YouTubeResearcher": (0, 0.15, 0, -0.15),
        "WhatsAppForwarder": (0.05, 0.20, 0.15, 0),
        "InstagramHeavy":    (-0.05, 0, 0.15, 0.10),
        "ReviewDriven":      (0.10, 0.20, -0.05, -0.10),
        "ShortVideoAddict":  (0, -0.05, 0.15, 0.20),
        "PassiveScroller":   (0, 0, 0.05, -0.05),
        "ActiveCommenter":   (0, 0, 0.05, 0.10),
    }
    dp, dt, di, sd = dmap.get(digital, (0, 0, 0, 0))
    ps += dp; tf += dt; isu += di; ds += sd

    return {
        "price_sensitivity": _clamp(ps),
        "trust_factor": _clamp(tf),
        "influence_susceptibility": _clamp(isu),
        "decision_speed": _clamp(ds),
    }


def sample_persona_dimensions(
    overrides: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, str]:
    """
    Agency control knob — override any distribution.
    Example: {"tier": {"Tier2": 0.7, "Tier1": 0.2, "Tier3": 0.1}}
    """
    def pick(domain: str, default: Dict[str, float]) -> str:
        if overrides and domain in overrides:
            return _wchoice(overrides[domain])
        return _wchoice(default)

    return {
        "tier": pick("tier", TIER_DISTRIBUTION),
        "income": pick("income", INCOME_DISTRIBUTION),
        "life_stage": pick("life_stage", LIFE_STAGE_DISTRIBUTION),
        "behavior": pick("behavior", BEHAVIOR_DISTRIBUTION),
        "digital": pick("digital", DIGITAL_DISTRIBUTION),
        "language": pick("language", LANGUAGE_DISTRIBUTION),
    }


def sample_population(
    n: int, overrides: Optional[Dict[str, Dict[str, float]]] = None,
) -> List[Dict[str, Any]]:
    """Generate N persona dimension+trait bundles (used for agency mix config)."""
    pop = []
    for _ in range(n):
        d = sample_persona_dimensions(overrides)
        t = derive_behavioral_traits(d["tier"], d["income"], d["behavior"], d["digital"])
        pop.append({**d, **t})
    return pop


# ── Profile dataclass ─────────────────────────────────────────────────────────

@dataclass
class OasisAgentProfile:
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str
    karma: int = 1000
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500
    age: Optional[int] = None
    gender: Optional[str] = None

    # Indian market dimensions
    tier: Optional[str] = None
    sec: Optional[str] = None
    income: Optional[str] = None
    life_stage: Optional[str] = None
    behavior: Optional[str] = None
    digital_pattern: Optional[str] = None
    primary_language: Optional[str] = None
    archetype: Optional[str] = None
    city: Optional[str] = None

    # Derived behavioral traits — drive simulation decisions
    price_sensitivity: float = 0.5
    trust_factor: float = 0.5
    influence_susceptibility: float = 0.5
    decision_speed: float = 0.5

    country: str = "India"
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)
    following_agentid_list: List[int] = field(default_factory=list)
    previous_tweets: List[str] = field(default_factory=list)
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def _trait_fields(self) -> Dict[str, Any]:
        return {
            "tier": self.tier, "sec": self.sec, "income": self.income,
            "life_stage": self.life_stage, "behavior": self.behavior,
            "digital_pattern": self.digital_pattern,
            "primary_language": self.primary_language,
            "archetype": self.archetype, "city": self.city,
            "price_sensitivity": round(self.price_sensitivity, 3),
            "trust_factor": round(self.trust_factor, 3),
            "influence_susceptibility": round(self.influence_susceptibility, 3),
            "decision_speed": round(self.decision_speed, 3),
        }

    def to_reddit_format(self) -> Dict[str, Any]:
        profile = {
            "user_id": self.user_id, "username": self.user_name, "realname": self.name,
            "name": self.name, "bio": self.bio, "persona": self.persona,
            "karma": self.karma, "created_at": self.created_at,
            "age": self.age, "gender": self.gender, "country": self.country,
            "profession": self.profession,
        }
        profile.update({k: v for k, v in self._trait_fields().items() if v is not None})
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        return profile

    def to_twitter_format(self) -> Dict[str, Any]:
        profile = {
            "user_id": self.user_id,
            "user_char": self.persona,   # CRITICAL: OASIS reads as persona
            "username": self.user_name,
            "name": self.name,
            "description": self.bio,     # CRITICAL: OASIS reads as bio
            "bio": self.bio, "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
            "following_agentid_list": str(self.following_agentid_list),
            "previous_tweets": str(self.previous_tweets),
            "age": self.age, "gender": self.gender, "country": self.country,
            "profession": self.profession,
        }
        profile.update({k: v for k, v in self._trait_fields().items() if v is not None})
        if self.interested_topics:
            profile["interested_topics"] = str(self.interested_topics)
        return profile

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "user_id": self.user_id, "user_name": self.user_name, "name": self.name,
            "bio": self.bio, "persona": self.persona, "karma": self.karma,
            "friend_count": self.friend_count, "follower_count": self.follower_count,
            "statuses_count": self.statuses_count, "age": self.age,
            "gender": self.gender, "country": self.country, "profession": self.profession,
            "interested_topics": self.interested_topics,
            "following_agentid_list": self.following_agentid_list,
            "previous_tweets": self.previous_tweets,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }
        d.update(self._trait_fields())
        return d


SYSTEM_PROMPT = (
    "You are an Indian market persona expert generating realistic social-media personas "
    "for marketing campaign simulation. Return ONLY valid JSON. Hinglish is acceptable "
    "for bio/persona when natural for the segment."
)


def _is_individual(entity_type: str) -> bool:
    return entity_type.lower() in INDIVIDUAL_TYPES


def _pick_tier_for_entity(entity_type: str, summary: str) -> str:
    s = (summary or "").lower()
    et = entity_type.lower()

    for tier, cities in TIER_CITY.items():
        if any(c.lower() in s for c in cities):
            return tier

    if et in ("brand", "company", "mediaoutlet", "platform", "bank", "quickcommerceplatform"):
        return "Tier1"
    if et in ("influencer", "celebrity", "expert", "creator", "finfluencer"):
        return _wchoice({"Tier1": 0.55, "Tier2": 0.35, "Tier3": 0.10})
    return _wchoice(TIER_DISTRIBUTION)


def _build_prompt(
    entity_name, entity_type, entity_summary, entity_attributes,
    context, is_individual, tier, dims, traits,
) -> str:
    attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "none"
    ctx = context[:2000] if context else "no additional context"
    archetype = BEHAVIOR_TO_ARCHETYPE.get(dims["behavior"], "value_hunter")

    if is_individual:
        return f"""Generate an Indian social-media persona.

Entity          : {entity_name} ({entity_type})
Summary         : {entity_summary}
Attributes      : {attrs_str}
Context         : {ctx}

Pre-sampled dimensions (use these — do not regenerate):
  tier            : {tier}
  income          : {dims['income']}
  life_stage      : {dims['life_stage']}
  behavior        : {dims['behavior']}  → archetype {archetype}
  digital_pattern : {dims['digital']}
  language        : {dims['language']}

Pre-derived behavioral traits:
  price_sensitivity        : {traits['price_sensitivity']:.2f}
  trust_factor             : {traits['trust_factor']:.2f}
  influence_susceptibility : {traits['influence_susceptibility']:.2f}
  decision_speed           : {traits['decision_speed']:.2f}

Return JSON:
- bio               : ≤200-char authentic bio (Hinglish ok for Tier2/3)
- persona           : ~1000-char paragraph on decision-making, trust cues, preferred platforms and how they'll react to marketing. Reference the behavioral traits explicitly.
- age               : realistic for tier
- gender            : "male" | "female"
- city              : specific city in {tier}
- sec               : "A" | "B" | "C" | "D"
- profession        : realistic for tier
- interested_topics : 3–5 items"""
    else:
        return f"""Generate an organization persona for the Indian market.

Entity  : {entity_name} ({entity_type})
Summary : {entity_summary}
Context : {ctx}
Market  : {tier}

Return JSON: bio, persona, age (30), gender ("other"), city (metro HQ), sec ("A"), profession, interested_topics (3–5)."""


class OasisProfileGenerator:
    def __init__(self, graph_id: Optional[str] = None, **kwargs):
        self.llm_client = LLMClient()
        self.memory = get_memory()
        self.graph_id = graph_id

    def generate_profile_from_entity(
        self, entity: EntityNode, user_id: int, use_llm: bool = True,
    ) -> OasisAgentProfile:
        entity_type = entity.get_entity_type() or "Consumer"
        name = entity.name
        user_name = self._make_username(name)
        context = self._build_context(entity)
        is_ind = _is_individual(entity_type)

        tier = _pick_tier_for_entity(entity_type, entity.summary)

        if is_ind:
            dims = sample_persona_dimensions(overrides={"tier": {tier: 1.0}})
        else:
            dims = {
                "tier": tier, "income": "High", "life_stage": "MidCareer",
                "behavior": "BrandConscious", "digital": "InstagramHeavy",
                "language": "English" if tier == "Tier1" else "Hinglish",
            }
        traits = derive_behavioral_traits(
            dims["tier"], dims["income"], dims["behavior"], dims["digital"]
        )

        if use_llm:
            profile_data = self._generate_with_llm(
                name, entity_type, entity.summary, entity.attributes,
                context, is_ind, tier, dims, traits,
            )
        else:
            profile_data = self._rule_based(entity_type, name, entity.summary, tier, dims, traits)

        archetype = BEHAVIOR_TO_ARCHETYPE.get(dims["behavior"], "value_hunter")

        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"Indian {entity_type}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            tier=tier,
            sec=profile_data.get("sec"),
            income=dims["income"],
            life_stage=dims["life_stage"],
            behavior=dims["behavior"],
            digital_pattern=dims["digital"],
            primary_language=dims["language"],
            archetype=archetype,
            city=profile_data.get("city") or random.choice(TIER_CITY[tier]),
            price_sensitivity=traits["price_sensitivity"],
            trust_factor=traits["trust_factor"],
            influence_susceptibility=traits["influence_susceptibility"],
            decision_speed=traits["decision_speed"],
            country="India",
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )

    def _make_username(self, name: str) -> str:
        base = "".join(c for c in name.lower().replace(" ", "_") if c.isalnum() or c == "_")
        return f"{base}_{random.randint(100, 999)}"

    def _build_context(self, entity: EntityNode) -> str:
        parts = []
        if entity.attributes:
            attrs = [f"- {k}: {v}" for k, v in entity.attributes.items() if v]
            if attrs:
                parts.append("Attributes:\n" + "\n".join(attrs))
        if entity.related_edges:
            facts = [e.get("fact", "") for e in entity.related_edges if e.get("fact")]
            if facts:
                parts.append("Relations:\n" + "\n".join(f"- {f}" for f in facts[:10]))
        if self.graph_id:
            try:
                related = self.memory.search_nodes(self.graph_id, entity.name, top_k=3)
                summaries = [n.get("summary", "") for n in related if n.get("summary")]
                if summaries:
                    parts.append("Related entities:\n" + "\n".join(f"- {s}" for s in summaries))
            except Exception:
                pass
        return "\n\n".join(parts)

    def _generate_with_llm(
        self, entity_name, entity_type, entity_summary, entity_attributes,
        context, is_individual, tier, dims, traits,
    ) -> Dict[str, Any]:
        prompt = _build_prompt(entity_name, entity_type, entity_summary,
                               entity_attributes, context, is_individual,
                               tier, dims, traits)
        try:
            result = self.llm_client.chat_json(
                messages=[{"role": "system", "content": SYSTEM_PROMPT},
                          {"role": "user", "content": prompt}],
                temperature=0.7,
            )
            if not result.get("bio"):
                result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
            if not result.get("persona"):
                result["persona"] = entity_summary or f"{entity_name} is an Indian {entity_type}."
            return result
        except Exception as e:
            logger.warning("LLM persona gen failed for %s: %s — rule-based fallback",
                           entity_name, str(e)[:80])
            return self._rule_based(entity_type, entity_name, entity_summary, tier, dims, traits)

    def _rule_based(self, entity_type, name, summary, tier, dims, traits) -> Dict[str, Any]:
        et = entity_type.lower()
        city = random.choice(TIER_CITY[tier])
        age_min, age_max = TIER_AGE_RANGE[tier]
        base_bio = summary[:200] if summary else f"A {entity_type} in {city}."
        archetype = BEHAVIOR_TO_ARCHETYPE.get(dims["behavior"], "value_hunter")
        sec_map = {"Tier1": ["A", "B"], "Tier2": ["B", "C"], "Tier3": ["C", "D"]}
        sec = random.choice(sec_map[tier])

        if et in ("consumer", "person", "student", "shopper", "homemaker", "farmer"):
            persona = (
                f"{name} is a {archetype.replace('_', ' ')} consumer from {city} "
                f"({tier}, SEC {sec}, {dims['income']} income). Primary language: "
                f"{dims['language']}. Digital pattern: {dims['digital']}. "
                f"Price sensitivity {traits['price_sensitivity']:.2f}, trust factor "
                f"{traits['trust_factor']:.2f}, influence susceptibility "
                f"{traits['influence_susceptibility']:.2f}, decision speed "
                f"{traits['decision_speed']:.2f}. {ARCHETYPE_TRAITS.get(archetype, '')}"
            )
            return {
                "bio": base_bio, "persona": persona,
                "age": random.randint(age_min, age_max),
                "gender": random.choice(["male", "female"]),
                "city": city, "sec": sec,
                "profession": random.choice(INDIAN_PROFESSIONS[tier]),
                "interested_topics": _topics_for_archetype(archetype),
            }

        if et in ("influencer", "creator", "reviewer", "finfluencer"):
            return {
                "bio": f"Creator | {city} | {dims['language']} content",
                "persona": (
                    f"{name} is a {city}-based creator. Audience skews {tier}. "
                    f"Content in {dims['language']}. Influence susceptibility "
                    f"{traits['influence_susceptibility']:.2f}."
                ),
                "age": random.randint(22, 35),
                "gender": random.choice(["male", "female"]),
                "city": city, "sec": "A",
                "profession": "Content Creator",
                "interested_topics": ["Lifestyle", "Trends", "Reviews", "Brand Collabs"],
            }

        if et in ("mediaoutlet", "journalist", "news"):
            return {
                "bio": "Indian media | News, business, culture",
                "persona": f"{name} covers Indian consumer trends, publishes in {dims['language']}.",
                "age": 35, "gender": "other",
                "city": random.choice(["Mumbai", "Delhi", "Bengaluru"]),
                "sec": "A", "profession": "News Media",
                "interested_topics": ["Business", "Consumer Trends", "Policy"],
            }

        if et in ("brand", "company"):
            return {
                "bio": "Official account | Serving Indian consumers",
                "persona": f"{name} targets {tier} Indian consumers. Bilingual, festive moments.",
                "age": 30, "gender": "other",
                "city": random.choice(["Mumbai", "Bengaluru", "Gurugram", "Delhi"]),
                "sec": "A", "profession": "Brand",
                "interested_topics": ["Product", "Customer Service", "Offers"],
            }

        if et in ("regulator", "governmentagency"):
            return {
                "bio": "Regulatory authority | India",
                "persona": f"{name} is a regulator; formal tone, issues advisories.",
                "age": 40, "gender": "other", "city": "Delhi",
                "sec": "A", "profession": "Regulator",
                "interested_topics": ["Compliance", "Guidelines", "Consumer Protection"],
            }

        if et in ("retailer", "quickcommerceplatform"):
            return {
                "bio": "Retail platform | Pan-India",
                "persona": f"{name} runs pricing + festival sales + UPI cashback.",
                "age": 28, "gender": "other",
                "city": random.choice(["Bengaluru", "Gurugram", "Mumbai"]),
                "sec": "A", "profession": "Retailer",
                "interested_topics": ["Offers", "Delivery", "Pricing"],
            }

        return {
            "bio": base_bio,
            "persona": f"{name} represents {entity_type} in {tier}.",
            "age": random.randint(age_min, age_max),
            "gender": random.choice(["male", "female", "other"]),
            "city": city, "sec": sec,
            "profession": entity_type.capitalize(),
            "interested_topics": ["General", "Indian Market"],
        }


def _topics_for_archetype(archetype: str) -> List[str]:
    return {
        "trend_driven":         ["Fashion", "Reels", "Brand Launches", "Pop Culture", "OTT"],
        "aspirational":         ["Premium Brands", "Travel", "Career", "Lifestyle"],
        "skeptical_researcher": ["Reviews", "Comparisons", "Unboxings", "Tech Specs"],
        "early_adopter":        ["Tech", "Startups", "Apps", "Innovation"],
        "value_hunter":         ["Deals", "Cashback", "Coupons", "Quick Commerce"],
        "family_driven":        ["Family", "Festivals", "Home", "Parenting"],
        "whatsapp_forward":     ["News", "Memes", "Offers", "Community"],
        "price_sensitive":      ["Discounts", "EMI Offers", "Local Brands", "Value Packs"],
    }.get(archetype, ["General", "Lifestyle"])