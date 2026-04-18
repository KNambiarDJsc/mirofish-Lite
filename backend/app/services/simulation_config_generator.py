"""
Simulation Config Generator — AXonic (Indian Market)

IST timezone + tier-realistic rhythm + behavioral traits (price_sensitivity,
trust_factor, influence_susceptibility, decision_speed) + WhatsApp private-
network dynamics + viral amplification thresholds + group/peer influence +
opinion-shift mechanics.
"""

import json
import math
import random
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from .supabase_entity_reader import EntityNode, SupabaseEntityReader as ZepEntityReader

logger = get_logger('axonic.simulation_config')


INDIA_TIMEZONE_CONFIG = {
    "dead_hours": [1, 2, 3, 4, 5],
    "morning_hours": [6, 7, 8, 9],
    "work_hours": list(range(10, 19)),
    "peak_hours": [19, 20, 21, 22],
    "night_hours": [23, 0],
    "activity_multipliers": {
        "dead": 0.05, "morning": 0.45, "work": 0.70, "peak": 1.60, "night": 0.40,
    },
}


# ── Agent config with behavioral traits ──────────────────────────────────────

@dataclass
class AgentActivityConfig:
    """Indian market simulation agent — activity + decision-driving traits."""
    agent_id: int
    entity_uuid: str
    entity_name: str
    entity_type: str

    # Activity
    activity_level: float = 0.5
    posts_per_hour: float = 1.0
    comments_per_hour: float = 2.0
    active_hours: List[int] = field(default_factory=lambda: list(range(8, 23)))

    response_delay_min: int = 5
    response_delay_max: int = 60

    sentiment_bias: float = 0.0
    stance: str = "neutral"   # supportive | opposing | neutral | observer

    # Influence
    influence_weight: float = 1.0

    # Behavioral traits (drive HOW the agent thinks, not HOW OFTEN)
    price_sensitivity: float = 0.5
    trust_factor: float = 0.5
    influence_susceptibility: float = 0.5
    decision_speed: float = 0.5

    # Network / group
    group_id: Optional[int] = None
    peer_influence_strength: float = 0.5

    # Learning during simulation
    opinion_shift_rate: float = 0.1


@dataclass
class TimeSimulationConfig:
    total_simulation_hours: int = 6
    minutes_per_round: int = 60
    agents_per_hour_min: int = 1
    agents_per_hour_max: int = 3

    peak_hours: List[int] = field(default_factory=lambda: [19, 20, 21, 22])
    peak_activity_multiplier: float = 1.6

    off_peak_hours: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    off_peak_activity_multiplier: float = 0.05

    morning_hours: List[int] = field(default_factory=lambda: [6, 7, 8, 9])
    morning_activity_multiplier: float = 0.45

    work_hours: List[int] = field(default_factory=lambda: list(range(10, 19)))
    work_activity_multiplier: float = 0.70


@dataclass
class PrivateNetworkConfig:
    """WhatsApp / peer / family private virality layer."""
    private_spread_factor: float = 1.2
    forward_probability: float = 0.3
    trust_boost_on_forward: float = 0.2
    family_group_multiplier: float = 1.5


@dataclass
class AmplificationConfig:
    """Public → private amplification dynamics."""
    viral_amplification_factor: float = 1.5
    influencer_trigger_threshold: int = 5     # reactions before an influencer jumps in
    media_pickup_threshold: int = 15          # reactions before media amplifies
    echo_chamber_strength: float = 0.5


@dataclass
class EventConfig:
    initial_posts: List[Dict[str, Any]] = field(default_factory=list)
    scheduled_events: List[Dict[str, Any]] = field(default_factory=list)
    hot_topics: List[str] = field(default_factory=list)
    narrative_direction: str = ""


@dataclass
class PlatformConfig:
    platform: str
    recency_weight: float = 0.4
    popularity_weight: float = 0.3
    relevance_weight: float = 0.3
    viral_threshold: int = 10
    echo_chamber_strength: float = 0.5


@dataclass
class SimulationParameters:
    simulation_id: str
    project_id: str
    graph_id: str
    simulation_requirement: str

    time_config: TimeSimulationConfig = field(default_factory=TimeSimulationConfig)
    agent_configs: List[AgentActivityConfig] = field(default_factory=list)
    event_config: EventConfig = field(default_factory=EventConfig)
    private_network: PrivateNetworkConfig = field(default_factory=PrivateNetworkConfig)
    amplification: AmplificationConfig = field(default_factory=AmplificationConfig)

    twitter_config: Optional[PlatformConfig] = None
    reddit_config: Optional[PlatformConfig] = None

    llm_model: str = ""
    llm_base_url: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    generation_reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "simulation_requirement": self.simulation_requirement,
            "time_config": asdict(self.time_config),
            "agent_configs": [asdict(a) for a in self.agent_configs],
            "event_config": asdict(self.event_config),
            "private_network": asdict(self.private_network),
            "amplification": asdict(self.amplification),
            "twitter_config": asdict(self.twitter_config) if self.twitter_config else None,
            "reddit_config": asdict(self.reddit_config) if self.reddit_config else None,
            "llm_model": self.llm_model,
            "llm_base_url": self.llm_base_url,
            "generated_at": self.generated_at,
            "generation_reasoning": self.generation_reasoning,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class SimulationConfigGenerator:
    MAX_CONTEXT_LENGTH = 50000
    AGENTS_PER_BATCH = 15
    TIME_CONFIG_CONTEXT_LENGTH = 10000
    EVENT_CONFIG_CONTEXT_LENGTH = 8000
    ENTITY_SUMMARY_LENGTH = 300
    AGENT_SUMMARY_LENGTH = 300
    ENTITIES_PER_TYPE_DISPLAY = 20

    def __init__(self, **kwargs):
        self._llm = LLMClient()
        self.model_name = "llama-3.3-70b-versatile"
        self.base_url = "http://localhost:5001"

    # ── Lite (zero-LLM) config ────────────────────────────────────────────────
    def generate_lite_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
    ) -> SimulationParameters:
        logger.info(f"Generating lite hardcoded config: {simulation_id}")

        time_config = TimeSimulationConfig(
            total_simulation_hours=3,
            minutes_per_round=60,
            agents_per_hour_min=1,
            agents_per_hour_max=1,
            peak_hours=[],
            off_peak_hours=list(range(0, 24)),
            off_peak_activity_multiplier=1.0,
        )

        event_config = EventConfig(
            hot_topics=["product", "offer", "paisa vasool", "worth it or not"],
            narrative_direction="Neutral information sharing across Indian consumer segments.",
            initial_posts=[{
                "content": f"Starting a discussion around: {simulation_requirement[:100]}",
                "poster_type": entities[0].get_entity_type() or "Consumer",
                "poster_agent_id": 1,
            }],
        )

        agent_configs = []
        for i, e in enumerate(entities):
            etype = (e.get_entity_type() or "Consumer").lower()
            lvl = 0.2 if etype in ("brand", "regulator", "mediaoutlet") else 0.5
            cfg = self._agent_config_by_rule(e, overrides={"activity_level": lvl})
            cfg.agent_id = i + 1
            cfg.active_hours = list(range(0, 24))
            agent_configs.append(cfg)

        return SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=agent_configs,
            event_config=event_config,
            twitter_config=PlatformConfig(platform="twitter") if enable_twitter else None,
            reddit_config=PlatformConfig(platform="reddit") if enable_reddit else None,
            llm_model="rule-based",
            generation_reasoning="Lite mode: hardcoded Indian market rules, 0 API calls.",
        )

    # ── Full LLM-driven config ────────────────────────────────────────────────
    def generate_config(
        self,
        simulation_id: str,
        project_id: str,
        graph_id: str,
        simulation_requirement: str,
        document_text: str,
        entities: List[EntityNode],
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> SimulationParameters:
        logger.info(f"Generating Indian market config: id={simulation_id}, "
                    f"entities={len(entities)}")

        num_batches = math.ceil(len(entities) / self.AGENTS_PER_BATCH)
        total_steps = 3 + num_batches
        current_step = 0

        def report(step: int, msg: str):
            nonlocal current_step
            current_step = step
            if progress_callback:
                progress_callback(step, total_steps, msg)
            logger.info(f"[{step}/{total_steps}] {msg}")

        context = self._build_context(simulation_requirement, document_text, entities)
        reasoning = []

        report(1, "Generating time config (IST)...")
        time_result = self._generate_time_config(context, len(entities))
        time_config = self._parse_time_config(time_result, len(entities))
        reasoning.append(f"Time: {time_result.get('reasoning', 'ok')}")

        report(2, "Generating event config + Indian hot topics...")
        event_result = self._generate_event_config(context, simulation_requirement, entities)
        event_config = self._parse_event_config(event_result)
        reasoning.append(f"Events: {event_result.get('reasoning', 'ok')}")

        all_agents: List[AgentActivityConfig] = []
        for batch_idx in range(num_batches):
            s_idx = batch_idx * self.AGENTS_PER_BATCH
            e_idx = min(s_idx + self.AGENTS_PER_BATCH, len(entities))
            batch = entities[s_idx:e_idx]
            report(3 + batch_idx, f"Agent configs ({s_idx + 1}-{e_idx}/{len(entities)})...")
            all_agents.extend(self._generate_agent_configs_batch(
                context, batch, s_idx, simulation_requirement,
            ))

        reasoning.append(f"Agents: {len(all_agents)}")

        # Assign network groups (peer + family clusters)
        self._assign_network_groups(all_agents)

        logger.info("Matching initial posts to agents...")
        event_config = self._assign_initial_post_agents(event_config, all_agents)
        assigned = len([p for p in event_config.initial_posts if p.get("poster_agent_id") is not None])
        reasoning.append(f"Initial posts assigned: {assigned}")

        report(total_steps, "Generating platform + network configs...")
        twitter = PlatformConfig(
            platform="twitter", recency_weight=0.4, popularity_weight=0.3,
            relevance_weight=0.3, viral_threshold=10, echo_chamber_strength=0.5,
        ) if enable_twitter else None
        reddit = PlatformConfig(
            platform="reddit", recency_weight=0.3, popularity_weight=0.4,
            relevance_weight=0.3, viral_threshold=15, echo_chamber_strength=0.6,
        ) if enable_reddit else None

        params = SimulationParameters(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            time_config=time_config,
            agent_configs=all_agents,
            event_config=event_config,
            private_network=PrivateNetworkConfig(),
            amplification=AmplificationConfig(),
            twitter_config=twitter,
            reddit_config=reddit,
            llm_model=self.model_name,
            llm_base_url=self.base_url,
            generation_reasoning=" | ".join(reasoning),
        )

        logger.info(f"Config complete: {len(params.agent_configs)} agents")
        return params

    # ── Context ──────────────────────────────────────────────────────────────
    def _build_context(self, simulation_requirement, document_text, entities) -> str:
        summary = self._summarize_entities(entities)
        parts = [
            f"## Campaign Requirement\n{simulation_requirement}",
            f"\n## Entities ({len(entities)} total)\n{summary}",
        ]
        current = sum(len(p) for p in parts)
        remaining = self.MAX_CONTEXT_LENGTH - current - 500
        if remaining > 0 and document_text:
            doc = document_text[:remaining]
            if len(document_text) > remaining:
                doc += "\n...(truncated)"
            parts.append(f"\n## Strategy Document\n{doc}")
        return "\n".join(parts)

    def _summarize_entities(self, entities: List[EntityNode]) -> str:
        lines = []
        by_type: Dict[str, List[EntityNode]] = {}
        for e in entities:
            by_type.setdefault(e.get_entity_type() or "Unknown", []).append(e)

        for etype, ents in by_type.items():
            lines.append(f"\n### {etype} ({len(ents)})")
            for e in ents[: self.ENTITIES_PER_TYPE_DISPLAY]:
                s = e.summary[: self.ENTITY_SUMMARY_LENGTH]
                if len(e.summary) > self.ENTITY_SUMMARY_LENGTH:
                    s += "..."
                lines.append(f"- {e.name}: {s}")
            if len(ents) > self.ENTITIES_PER_TYPE_DISPLAY:
                lines.append(f"  ... plus {len(ents) - self.ENTITIES_PER_TYPE_DISPLAY} more")
        return "\n".join(lines)

    def _call_llm_with_retry(self, prompt: str, system_prompt: str) -> Dict[str, Any]:
        try:
            return self._llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )
        except Exception as e:
            logger.warning("LLM call failed: %s", str(e)[:80])
            raise

    # ── Time config ──────────────────────────────────────────────────────────
    def _generate_time_config(self, context: str, num_entities: int) -> Dict[str, Any]:
        ctx = context[: self.TIME_CONFIG_CONTEXT_LENGTH]
        max_allowed = max(1, int(num_entities * 0.9))

        prompt = f"""Generate a time config for Indian Standard Time (IST) behaviour.

{ctx}

IST baseline rhythm:
- 1–5 AM: dead (0.05x)
- 6–9 AM: morning ramp (0.45x) — commute + news
- 10 AM–6 PM: steady (0.70x) — WhatsApp + LinkedIn
- 7–10 PM: PRIME TIME (1.60x) — Reels + YouTube + WhatsApp forwards
- 11 PM–midnight: trailing (0.40x)

Context-specific adjustments:
- Cricket/IPL days → attention collapse 7:30–11 PM, spike after
- Salary week (1st–7th) → conversion +25%
- Festival windows (Diwali/Onam/Durga Puja/Eid/Ganesh Chaturthi) → prime extends to midnight
- Student campaigns → late-night peak 10 PM–1 AM
- Homemaker campaigns → morning 9–11 + afternoon 2–4 PM
- B2B campaigns → Mon–Thu 9 AM–12 PM

Return JSON (no markdown):
{{
  "total_simulation_hours": 6,
  "minutes_per_round": 60,
  "agents_per_hour_min": 1,
  "agents_per_hour_max": 3,
  "peak_hours": [19, 20, 21, 22],
  "off_peak_hours": [1, 2, 3, 4, 5],
  "morning_hours": [6, 7, 8, 9],
  "work_hours": [10, 11, 12, 13, 14, 15, 16, 17, 18],
  "reasoning": "campaign-specific justification"
}}

agents_per_hour_max must not exceed {max_allowed}."""

        sys = ("You are a digital-marketing simulation expert for the Indian market. "
               "Return PURE JSON. Match IST consumer rhythm.")
        try:
            return self._call_llm_with_retry(prompt, sys)
        except Exception as e:
            logger.warning(f"Time-config LLM failed: {e}, default IST")
            return self._default_time_config()

    def _default_time_config(self) -> Dict[str, Any]:
        return {
            "total_simulation_hours": 6, "minutes_per_round": 60,
            "agents_per_hour_min": 1, "agents_per_hour_max": 3,
            "peak_hours": [19, 20, 21, 22],
            "off_peak_hours": [1, 2, 3, 4, 5],
            "morning_hours": [6, 7, 8, 9],
            "work_hours": list(range(10, 19)),
            "reasoning": "Default IST rhythm.",
        }

    def _parse_time_config(self, result: Dict[str, Any], num_entities: int) -> TimeSimulationConfig:
        a_min = result.get("agents_per_hour_min", max(1, num_entities // 15))
        a_max = result.get("agents_per_hour_max", max(5, num_entities // 5))

        if a_min > num_entities:
            a_min = max(1, num_entities // 10)
        if a_max > num_entities:
            a_max = max(a_min + 1, num_entities // 2)
        if a_min >= a_max:
            a_min = max(1, a_max // 2)

        return TimeSimulationConfig(
            total_simulation_hours=result.get("total_simulation_hours", 6),
            minutes_per_round=result.get("minutes_per_round", 60),
            agents_per_hour_min=a_min,
            agents_per_hour_max=a_max,
            peak_hours=result.get("peak_hours", [19, 20, 21, 22]),
            off_peak_hours=result.get("off_peak_hours", [1, 2, 3, 4, 5]),
            off_peak_activity_multiplier=0.05,
            morning_hours=result.get("morning_hours", [6, 7, 8, 9]),
            morning_activity_multiplier=0.45,
            work_hours=result.get("work_hours", list(range(10, 19))),
            work_activity_multiplier=0.70,
            peak_activity_multiplier=1.60,
        )

    # ── Event config ─────────────────────────────────────────────────────────
    def _generate_event_config(
        self, context, simulation_requirement, entities,
    ) -> Dict[str, Any]:
        type_examples: Dict[str, List[str]] = {}
        for e in entities:
            etype = e.get_entity_type() or "Unknown"
            type_examples.setdefault(etype, [])
            if len(type_examples[etype]) < 3:
                type_examples[etype].append(e.name)

        type_info = "\n".join(f"- {t}: {', '.join(x)}" for t, x in type_examples.items())
        ctx = context[: self.EVENT_CONFIG_CONTEXT_LENGTH]

        prompt = f"""Generate an event config for an Indian marketing campaign simulation.

Campaign: {simulation_requirement}

{ctx}

## Available entity types + examples
{type_info}

## Task
Produce realistic Indian-market event config.

Rules:
1. **hot_topics** — MUST include authentic Indian marketing phrases. Mandatory flavour:
   - "paisa vasool", "too expensive yaar", "UPI cashback worth it?",
     "scam or legit?", "worth the hype?", "bro is it original?",
     "discount kab aayega", "refer karo", "free delivery hai?",
     "cash on delivery available?", "review dekha kya?", "friend ne bheja hai"
   Pick 6–10 that fit the campaign, blend with campaign-specific keywords.

2. **narrative_direction** — 1–2 sentences on how reaction cascades across Tier1/Tier2/Tier3 and crosses from public (Instagram/Twitter) into private (WhatsApp/peer).

3. **initial_posts** — each with `poster_type` exactly matching an available entity type above. Content in English or Hinglish, ≤200 chars, realistic social copy (not press-release tone).

Return JSON (no markdown):
{{
  "hot_topics": ["keyword1 (mix Indian phrases)", ...],
  "narrative_direction": "how reaction spreads public → private across tiers",
  "initial_posts": [
    {{"content": "post content", "poster_type": "EntityType"}},
    ...
  ],
  "reasoning": "brief justification"
}}"""

        sys = ("You are an Indian market campaign analyst. Return PURE JSON. "
               "Hot topics MUST include authentic Hinglish phrases, not generic English words.")
        try:
            return self._call_llm_with_retry(prompt, sys)
        except Exception as e:
            logger.warning(f"Event-config LLM failed: {e}")
            return {
                "hot_topics": ["paisa vasool", "worth it or not", "scam or legit", "review dekha"],
                "narrative_direction": "",
                "initial_posts": [],
                "reasoning": "Default fallback.",
            }

    def _parse_event_config(self, result: Dict[str, Any]) -> EventConfig:
        return EventConfig(
            initial_posts=result.get("initial_posts", []),
            scheduled_events=[],
            hot_topics=result.get("hot_topics", []),
            narrative_direction=result.get("narrative_direction", ""),
        )

    # ── Network group assignment ─────────────────────────────────────────────
    def _assign_network_groups(self, agents: List[AgentActivityConfig]):
        """Assign peer/family group_ids to enable network effects in simulation."""
        consumer_types = {
            "tier1consumer", "tier2consumer", "tier3consumer", "consumer",
            "person", "student", "parent", "homemaker", "homemakerconsumer",
            "urbanprofessional", "hniconsumer", "massconsumer", "aspirationalconsumer",
        }
        consumers = [a for a in agents if a.entity_type.lower() in consumer_types]
        random.shuffle(consumers)

        # Cluster size 3–6 (WhatsApp family/peer group typical size)
        group_id = 0
        i = 0
        while i < len(consumers):
            size = random.choice([3, 4, 5, 6])
            cluster = consumers[i:i + size]
            for a in cluster:
                a.group_id = group_id
                # Family/homemaker types → stronger peer influence
                if a.entity_type.lower() in ("parent", "homemaker", "homemakerconsumer"):
                    a.peer_influence_strength = random.uniform(0.7, 0.9)
                else:
                    a.peer_influence_strength = random.uniform(0.4, 0.7)
            group_id += 1
            i += size

    # ── Initial post → agent matching ────────────────────────────────────────
    def _assign_initial_post_agents(
        self, event_config: EventConfig, agents: List[AgentActivityConfig],
    ) -> EventConfig:
        if not event_config.initial_posts:
            return event_config

        by_type: Dict[str, List[AgentActivityConfig]] = {}
        for a in agents:
            by_type.setdefault(a.entity_type.lower(), []).append(a)

        aliases = {
            "brand":          ["brand", "company", "competitorbrand"],
            "mediaoutlet":    ["mediaoutlet", "media", "regionalmediaoutlet",
                               "finmediaoutlet", "mediaamplifier"],
            "influencer":     ["influencer", "creator", "microinfluencer", "nanoinfluencer",
                               "megacreator", "finfluencercreator", "reviewer"],
            "tier1consumer":  ["tier1consumer", "urbanprofessional", "hniconsumer", "person", "consumer"],
            "tier2consumer":  ["tier2consumer", "aspirationalconsumer", "person", "consumer"],
            "tier3consumer":  ["tier3consumer", "masconsumer", "massconsumer", "person", "consumer"],
            "consumer":       ["consumer", "person", "student", "homemaker"],
            "consumersegment":["consumersegment", "consumer", "person"],
            "peergroup":      ["peergroup", "person", "consumer"],
            "familygroup":    ["familygroup", "parent", "homemaker", "person"],
            "regulator":      ["regulator", "asciregulator", "sebiregulator", "fssairegulator"],
            "retailer":       ["retailer", "quickcommerceplatform", "moderntraderetailer",
                               "kiranaretailer"],
            "platform":       ["platform", "organization"],
            "person":         ["person", "consumer", "student"],
            "organization":   ["organization", "brand", "ngo", "company"],
            "student":        ["student", "person", "consumer"],
            "parent":         ["parent", "homemaker", "person"],
            "homemaker":      ["homemaker", "homemakerconsumer", "person"],
        }

        used: Dict[str, int] = {}
        updated = []

        for post in event_config.initial_posts:
            ptype = post.get("poster_type", "").lower()
            content = post.get("content", "")
            matched_id = None

            if ptype in by_type:
                ags = by_type[ptype]
                idx = used.get(ptype, 0) % len(ags)
                matched_id = ags[idx].agent_id
                used[ptype] = idx + 1
            else:
                for akey, alist in aliases.items():
                    if ptype in alist or akey == ptype:
                        for a in alist:
                            if a in by_type:
                                ags = by_type[a]
                                idx = used.get(a, 0) % len(ags)
                                matched_id = ags[idx].agent_id
                                used[a] = idx + 1
                                break
                    if matched_id is not None:
                        break

            if matched_id is None:
                logger.warning(f"No match for poster_type='{ptype}', using top-influence agent.")
                if agents:
                    matched_id = sorted(agents, key=lambda x: x.influence_weight, reverse=True)[0].agent_id
                else:
                    matched_id = 0

            updated.append({
                "content": content,
                "poster_type": post.get("poster_type", "Unknown"),
                "poster_agent_id": matched_id,
            })
            logger.info(f"Initial post: {ptype!r} -> agent_id={matched_id}")

        event_config.initial_posts = updated
        return event_config

    # ── Agent configs (batched LLM + rule fallback) ──────────────────────────
    def _generate_agent_configs_batch(
        self, context, entities: List[EntityNode],
        start_idx: int, simulation_requirement: str,
    ) -> List[AgentActivityConfig]:
        entity_list = []
        for i, e in enumerate(entities):
            entity_list.append({
                "agent_id": start_idx + i,
                "entity_name": e.name,
                "entity_type": e.get_entity_type() or "Unknown",
                "summary": e.summary[: self.AGENT_SUMMARY_LENGTH] if e.summary else "",
            })

        prompt = f"""Generate Indian-market simulation configs.

Campaign: {simulation_requirement}

## Entities
```json
{json.dumps(entity_list, ensure_ascii=False, indent=2)}
```

## Rules — realistic Indian behaviour + decision-driving traits

**Brand/CompetitorBrand (official)**
- activity 0.3–0.5, hours 10–22 IST, delay 30–120min, influence 2.0–2.8, stance=observer
- traits: price_sensitivity 0.3, trust 0.5, influence_sus 0.2, decision_speed 0.5

**MediaOutlet/RegionalMediaOutlet/MediaAmplifier**
- activity 0.4–0.6, hours 8–23 IST, delay 5–30min, influence 2.2–2.6, stance=observer
- traits: trust 0.6, influence_sus 0.2

**Influencer/Creator/Reviewer/FinfluencerCreator**
- activity 0.6–0.8, hours 11–23 IST, delay 5–30min, influence 1.8–2.5
- traits: influence_sus 0.6, trust 0.5, decision_speed 0.7

**Tier1Consumer (metros, pro)**
- activity 0.5–0.7, hours 8–10 + 19–23 IST, delay 1–15min, influence 0.9–1.2
- traits: price_sensitivity 0.3–0.5, trust 0.5, influence_sus 0.5, decision_speed 0.6

**Tier2Consumer (Pune/Jaipur/Kochi, value_hunter or aspirational)**
- activity 0.6–0.8, hours 9–14 + 18–23 IST, delay 2–20min, influence 0.8–1.1
- traits: price_sensitivity 0.6–0.8, trust 0.5, influence_sus 0.6, decision_speed 0.4–0.6

**Tier3Consumer (Patna/Ranchi, WhatsApp-heavy)**
- activity 0.4–0.6, hours 18–23 IST, delay 5–45min, influence 0.6–0.9
- traits: price_sensitivity 0.7–0.9, trust 0.7, influence_sus 0.7, decision_speed 0.3–0.5

**Regulator (ASCI/SEBI/FSSAI)**
- activity 0.1–0.2, hours 10–17 weekdays, delay 240–1440min, influence 3.0
- traits: price 0.0, trust 0.8, influence_sus 0.1, decision_speed 0.2

**Retailer/QuickCommercePlatform**
- activity 0.4–0.6, hours 9–23 IST, delay 15–60min, influence 1.5–2.0, stance=observer

**Student**
- activity 0.7–0.9, hours 12–13 + 16–23 + 0–1 IST, delay 1–15min, influence 0.8
- traits: price 0.7, trust 0.4, influence_sus 0.8, decision_speed 0.7

**Parent/Homemaker**
- activity 0.5–0.6, hours 9–11 + 14–16 + 20–21 IST, delay 10–60min, influence 0.9
- traits: price 0.6, trust 0.7, influence_sus 0.4, decision_speed 0.3

**Sentiment bias (CRITICAL — create conflict, not neutrality)**
- Brand → 0.15 to 0.30 (positive own products)
- Competitor → -0.20 to -0.05
- SkepticalResearcher / regulator-adjacent → -0.40 to -0.10
- Tier2 aspirational → -0.10 to 0.30 (mixed)
- Tier3 value_hunter → -0.30 to 0.15
- DO NOT set all to 0.0 — unrealistic.

Return PURE JSON (no markdown):
{{
  "agent_configs": [
    {{
      "agent_id": <must match input>,
      "activity_level": <0.0–1.0>,
      "posts_per_hour": <float>,
      "comments_per_hour": <float>,
      "active_hours": [<0–23 IST>],
      "response_delay_min": <int>,
      "response_delay_max": <int>,
      "sentiment_bias": <-1.0 to 1.0, NOT 0.0>,
      "stance": "<supportive|opposing|neutral|observer>",
      "influence_weight": <float>,
      "price_sensitivity": <0.0–1.0>,
      "trust_factor": <0.0–1.0>,
      "influence_susceptibility": <0.0–1.0>,
      "decision_speed": <0.0–1.0>,
      "opinion_shift_rate": <0.05–0.3>
    }}
  ]
}}"""

        sys = ("You are an Indian social-media behaviour analyst. Return PURE JSON. "
               "Match IST rhythm, tier-based patterns, and set NON-ZERO sentiment biases "
               "so the simulation has realistic conflict.")
        try:
            result = self._call_llm_with_retry(prompt, sys)
            llm_by_id = {cfg["agent_id"]: cfg for cfg in result.get("agent_configs", [])}
        except Exception as e:
            logger.warning(f"Agent-batch LLM failed: {e}, rule fallback")
            llm_by_id = {}

        out = []
        for i, entity in enumerate(entities):
            aid = start_idx + i
            llm_cfg = llm_by_id.get(aid)
            if llm_cfg:
                cfg = self._cfg_from_llm(aid, entity, llm_cfg)
            else:
                cfg = self._agent_config_by_rule(entity)
                cfg.agent_id = aid
            out.append(cfg)
        return out

    def _cfg_from_llm(
        self, agent_id: int, entity: EntityNode, llm: Dict[str, Any],
    ) -> AgentActivityConfig:
        return AgentActivityConfig(
            agent_id=agent_id,
            entity_uuid=entity.uuid,
            entity_name=entity.name,
            entity_type=entity.get_entity_type() or "Unknown",
            activity_level=llm.get("activity_level", 0.5),
            posts_per_hour=llm.get("posts_per_hour", 0.5),
            comments_per_hour=llm.get("comments_per_hour", 1.0),
            active_hours=llm.get("active_hours", list(range(9, 23))),
            response_delay_min=llm.get("response_delay_min", 5),
            response_delay_max=llm.get("response_delay_max", 60),
            sentiment_bias=llm.get("sentiment_bias", 0.0),
            stance=llm.get("stance", "neutral"),
            influence_weight=llm.get("influence_weight", 1.0),
            price_sensitivity=llm.get("price_sensitivity", 0.5),
            trust_factor=llm.get("trust_factor", 0.5),
            influence_susceptibility=llm.get("influence_susceptibility", 0.5),
            decision_speed=llm.get("decision_speed", 0.5),
            opinion_shift_rate=llm.get("opinion_shift_rate", 0.1),
        )

    def _agent_config_by_rule(
        self, entity: EntityNode, overrides: Optional[Dict[str, Any]] = None,
    ) -> AgentActivityConfig:
        """Rule-based fallback, realistic for Indian market."""
        et = (entity.get_entity_type() or "Unknown").lower()

        def rand_bias(lo, hi):
            return round(random.uniform(lo, hi), 2)

        if et in ("brand", "competitorbrand", "company"):
            cfg = dict(
                activity_level=0.4, posts_per_hour=0.3, comments_per_hour=0.2,
                active_hours=list(range(10, 23)),
                response_delay_min=30, response_delay_max=120,
                sentiment_bias=rand_bias(-0.10, 0.25) if et == "competitorbrand" else rand_bias(0.15, 0.30),
                stance="observer", influence_weight=2.4,
                price_sensitivity=0.3, trust_factor=0.5,
                influence_susceptibility=0.2, decision_speed=0.5,
                opinion_shift_rate=0.05,
            )
        elif et in ("mediaoutlet", "regionalmediaoutlet", "finmediaoutlet",
                    "educationmediaoutlet", "automediaoutlet", "mediaamplifier"):
            cfg = dict(
                activity_level=0.5, posts_per_hour=0.8, comments_per_hour=0.3,
                active_hours=list(range(8, 24)),
                response_delay_min=5, response_delay_max=30,
                sentiment_bias=rand_bias(-0.10, 0.10),
                stance="observer", influence_weight=2.5,
                price_sensitivity=0.4, trust_factor=0.6,
                influence_susceptibility=0.2, decision_speed=0.6,
                opinion_shift_rate=0.1,
            )
        elif et in ("influencer", "creator", "nanoinfluencer", "microinfluencer",
                    "megacreator", "reviewer", "finfluencercreator", "foodcreator",
                    "autoinfluencer", "educationinfluencer", "regionalinfluencer"):
            cfg = dict(
                activity_level=0.7, posts_per_hour=0.5, comments_per_hour=1.2,
                active_hours=list(range(11, 24)),
                response_delay_min=5, response_delay_max=30,
                sentiment_bias=rand_bias(-0.20, 0.30),
                stance="neutral", influence_weight=2.0,
                price_sensitivity=0.4, trust_factor=0.5,
                influence_susceptibility=0.6, decision_speed=0.7,
                opinion_shift_rate=0.15,
            )
        elif et in ("tier1consumer", "urbanprofessional", "hniconsumer"):
            cfg = dict(
                activity_level=0.65, posts_per_hour=0.4, comments_per_hour=1.0,
                active_hours=[8, 9, 10, 12, 13, 19, 20, 21, 22, 23],
                response_delay_min=1, response_delay_max=15,
                sentiment_bias=rand_bias(-0.15, 0.25),
                stance="neutral", influence_weight=1.1,
                price_sensitivity=rand_bias(0.3, 0.5),
                trust_factor=0.5, influence_susceptibility=0.5,
                decision_speed=0.6, opinion_shift_rate=0.15,
            )
        elif et in ("tier2consumer", "aspirationalconsumer"):
            cfg = dict(
                activity_level=0.7, posts_per_hour=0.5, comments_per_hour=1.3,
                active_hours=[9, 10, 11, 13, 14, 18, 19, 20, 21, 22, 23],
                response_delay_min=2, response_delay_max=20,
                sentiment_bias=rand_bias(-0.10, 0.30),
                stance="neutral", influence_weight=0.95,
                price_sensitivity=rand_bias(0.6, 0.8),
                trust_factor=0.5, influence_susceptibility=0.6,
                decision_speed=rand_bias(0.4, 0.6),
                opinion_shift_rate=0.2,
            )
        elif et in ("tier3consumer", "massconsumer", "masconsumer"):
            cfg = dict(
                activity_level=0.5, posts_per_hour=0.3, comments_per_hour=1.0,
                active_hours=[18, 19, 20, 21, 22, 23],
                response_delay_min=5, response_delay_max=45,
                sentiment_bias=rand_bias(-0.30, 0.15),
                stance="neutral", influence_weight=0.75,
                price_sensitivity=rand_bias(0.7, 0.9),
                trust_factor=rand_bias(0.6, 0.8),
                influence_susceptibility=0.7,
                decision_speed=rand_bias(0.3, 0.5),
                opinion_shift_rate=0.25,
            )
        elif et in ("regulator", "asciregulator", "sebiregulator", "fssairegulator",
                    "governmentagency", "trairegulator"):
            cfg = dict(
                activity_level=0.15, posts_per_hour=0.1, comments_per_hour=0.05,
                active_hours=list(range(10, 17)),
                response_delay_min=240, response_delay_max=1440,
                sentiment_bias=rand_bias(-0.40, -0.10),
                stance="neutral", influence_weight=3.0,
                price_sensitivity=0.0, trust_factor=0.8,
                influence_susceptibility=0.1, decision_speed=0.2,
                opinion_shift_rate=0.05,
            )
        elif et in ("retailer", "quickcommerceplatform", "moderntraderetailer",
                    "kiranaretailer", "d2cretailer"):
            cfg = dict(
                activity_level=0.5, posts_per_hour=0.4, comments_per_hour=0.5,
                active_hours=list(range(9, 24)),
                response_delay_min=15, response_delay_max=60,
                sentiment_bias=rand_bias(0.05, 0.20),
                stance="observer", influence_weight=1.8,
                price_sensitivity=0.5, trust_factor=0.6,
                influence_susceptibility=0.3, decision_speed=0.6,
                opinion_shift_rate=0.1,
            )
        elif et in ("student", "college", "schoolstudent"):
            cfg = dict(
                activity_level=0.8, posts_per_hour=0.6, comments_per_hour=1.6,
                active_hours=[12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1],
                response_delay_min=1, response_delay_max=15,
                sentiment_bias=rand_bias(-0.15, 0.35),
                stance="neutral", influence_weight=0.85,
                price_sensitivity=rand_bias(0.6, 0.9),
                trust_factor=rand_bias(0.3, 0.5),
                influence_susceptibility=rand_bias(0.7, 0.9),
                decision_speed=0.7, opinion_shift_rate=0.3,
            )
        elif et in ("parent", "homemaker", "homemakerconsumer"):
            cfg = dict(
                activity_level=0.55, posts_per_hour=0.3, comments_per_hour=0.8,
                active_hours=[9, 10, 11, 14, 15, 16, 20, 21],
                response_delay_min=10, response_delay_max=60,
                sentiment_bias=rand_bias(-0.10, 0.20),
                stance="neutral", influence_weight=0.9,
                price_sensitivity=rand_bias(0.5, 0.7),
                trust_factor=rand_bias(0.6, 0.8),
                influence_susceptibility=0.4,
                decision_speed=rand_bias(0.3, 0.4),
                opinion_shift_rate=0.1,
            )
        elif et in ("peergroup", "familygroup"):
            cfg = dict(
                activity_level=0.5, posts_per_hour=0.4, comments_per_hour=1.2,
                active_hours=[9, 10, 11, 19, 20, 21, 22],
                response_delay_min=5, response_delay_max=45,
                sentiment_bias=rand_bias(-0.10, 0.20),
                stance="neutral", influence_weight=1.4,
                price_sensitivity=0.6, trust_factor=0.8,
                influence_susceptibility=0.6, decision_speed=0.4,
                opinion_shift_rate=0.15,
            )
        else:
            cfg = dict(
                activity_level=0.5, posts_per_hour=0.3, comments_per_hour=0.8,
                active_hours=[9, 10, 11, 12, 13, 18, 19, 20, 21, 22],
                response_delay_min=5, response_delay_max=30,
                sentiment_bias=rand_bias(-0.15, 0.15),
                stance="neutral", influence_weight=1.0,
                price_sensitivity=0.5, trust_factor=0.5,
                influence_susceptibility=0.5, decision_speed=0.5,
                opinion_shift_rate=0.1,
            )

        if overrides:
            cfg.update(overrides)

        return AgentActivityConfig(
            agent_id=0,
            entity_uuid=entity.uuid,
            entity_name=entity.name,
            entity_type=entity.get_entity_type() or "Unknown",
            **cfg,
        )