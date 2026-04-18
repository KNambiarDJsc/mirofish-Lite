"""
OASIS Simulation Manager — AXonic (Indian Market Edition)

Orchestrates Twitter + Reddit parallel simulation:
  1. Reads + filters entities from the KG
  2. Generates Indian market OASIS Agent profiles (weighted distributions,
     behavioral traits, agency persona_overrides)
  3. LLM-driven simulation config with IST rhythm + private-network dynamics
  4. Writes all artifacts to disk (OASIS runners read from files) AND optionally
     persists to Supabase (`simulations`, `personas` tables)
"""

import os
import json
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..config import Config
from ..utils.logger import get_logger
from .supabase_entity_reader import SupabaseEntityReader as ZepEntityReader, FilteredEntities
from .oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile
from .simulation_config_generator import SimulationConfigGenerator, SimulationParameters

logger = get_logger('axonic.simulation')

# Optional Supabase persistence (gracefully degrades if unavailable)
try:
    from ..utils.supabase_client import get_client
    _supabase_available = True
except Exception:
    _supabase_available = False


class SimulationStatus(str, Enum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class PlatformType(str, Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"


@dataclass
class SimulationState:
    """Simulation state — persisted to disk as state.json."""
    simulation_id: str
    project_id: str
    graph_id: str

    enable_twitter: bool = True
    enable_reddit: bool = True

    status: SimulationStatus = SimulationStatus.CREATED

    # Preparation data
    entities_count: int = 0
    profiles_count: int = 0
    entity_types: List[str] = field(default_factory=list)

    # Agency control — persona mix overrides (tier/behavior/digital/language/income/life_stage)
    persona_overrides: Optional[Dict[str, Dict[str, float]]] = None

    # Tier distribution summary (populated after profile gen)
    tier_distribution: Dict[str, int] = field(default_factory=dict)
    archetype_distribution: Dict[str, int] = field(default_factory=dict)

    # Config generation
    config_generated: bool = False
    config_reasoning: str = ""

    # Runtime
    current_round: int = 0
    twitter_status: str = "not_started"
    reddit_status: str = "not_started"

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "enable_twitter": self.enable_twitter,
            "enable_reddit": self.enable_reddit,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "persona_overrides": self.persona_overrides,
            "tier_distribution": self.tier_distribution,
            "archetype_distribution": self.archetype_distribution,
            "config_generated": self.config_generated,
            "config_reasoning": self.config_reasoning,
            "current_round": self.current_round,
            "twitter_status": self.twitter_status,
            "reddit_status": self.reddit_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error": self.error,
        }

    def to_simple_dict(self) -> Dict[str, Any]:
        """Compact dict for API responses."""
        return {
            "simulation_id": self.simulation_id,
            "project_id": self.project_id,
            "graph_id": self.graph_id,
            "status": self.status.value,
            "entities_count": self.entities_count,
            "profiles_count": self.profiles_count,
            "entity_types": self.entity_types,
            "tier_distribution": self.tier_distribution,
            "config_generated": self.config_generated,
            "error": self.error,
        }


class SimulationManager:
    """Campaign simulation orchestrator for Indian market."""

    SIMULATION_DATA_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )

    def __init__(self):
        os.makedirs(self.SIMULATION_DATA_DIR, exist_ok=True)
        self._simulations: Dict[str, SimulationState] = {}

    def _get_simulation_dir(self, simulation_id: str) -> str:
        sim_dir = os.path.join(self.SIMULATION_DATA_DIR, simulation_id)
        os.makedirs(sim_dir, exist_ok=True)
        return sim_dir

    def _save_simulation_state(self, state: SimulationState):
        sim_dir = self._get_simulation_dir(state.simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        state.updated_at = datetime.now().isoformat()
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, ensure_ascii=False, indent=2)
        self._simulations[state.simulation_id] = state

        # Optional: mirror to Supabase `simulations` table
        self._persist_simulation_to_supabase(state)

    def _load_simulation_state(self, simulation_id: str) -> Optional[SimulationState]:
        if simulation_id in self._simulations:
            return self._simulations[simulation_id]

        sim_dir = self._get_simulation_dir(simulation_id)
        state_file = os.path.join(sim_dir, "state.json")
        if not os.path.exists(state_file):
            return None

        with open(state_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=data.get("project_id", ""),
            graph_id=data.get("graph_id", ""),
            enable_twitter=data.get("enable_twitter", True),
            enable_reddit=data.get("enable_reddit", True),
            status=SimulationStatus(data.get("status", "created")),
            entities_count=data.get("entities_count", 0),
            profiles_count=data.get("profiles_count", 0),
            entity_types=data.get("entity_types", []),
            persona_overrides=data.get("persona_overrides"),
            tier_distribution=data.get("tier_distribution", {}),
            archetype_distribution=data.get("archetype_distribution", {}),
            config_generated=data.get("config_generated", False),
            config_reasoning=data.get("config_reasoning", ""),
            current_round=data.get("current_round", 0),
            twitter_status=data.get("twitter_status", "not_started"),
            reddit_status=data.get("reddit_status", "not_started"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            error=data.get("error"),
        )

        self._simulations[simulation_id] = state
        return state

    # ── Supabase persistence (optional, non-blocking) ────────────────────────

    def _persist_simulation_to_supabase(self, state: SimulationState):
        """Mirror simulation state to Supabase `simulations` table. Silent on failure."""
        if not _supabase_available:
            return
        try:
            client = get_client()
            payload = {
                "id": state.simulation_id,
                "project_id": state.project_id,
                "graph_id": state.graph_id,
                "simulation_requirement": "",
                "status": state.status.value,
                "total_agents": state.profiles_count,
                "enable_twitter": state.enable_twitter,
                "enable_reddit": state.enable_reddit,
                "config": {
                    "entity_types": state.entity_types,
                    "persona_overrides": state.persona_overrides,
                    "tier_distribution": state.tier_distribution,
                    "archetype_distribution": state.archetype_distribution,
                    "config_reasoning": state.config_reasoning,
                },
                "error": state.error,
            }
            if state.status == SimulationStatus.RUNNING and not payload.get("started_at"):
                payload["started_at"] = datetime.now().isoformat()
            if state.status in (SimulationStatus.COMPLETED, SimulationStatus.STOPPED):
                payload["completed_at"] = datetime.now().isoformat()
            client.table("simulations").upsert(payload, on_conflict="id").execute()
        except Exception as e:
            logger.debug("Supabase simulation persistence skipped: %s", str(e)[:120])

    def _persist_personas_to_supabase(
        self, simulation_id: str, profiles: List[OasisAgentProfile],
    ):
        """Bulk-write personas to Supabase `personas` table. Silent on failure."""
        if not _supabase_available or not profiles:
            return
        try:
            client = get_client()
            rows = []
            for p in profiles:
                rows.append({
                    "simulation_id": simulation_id,
                    "agent_id": p.user_id,
                    "entity_uuid": p.source_entity_uuid,
                    "entity_type": p.source_entity_type,
                    "user_name": p.user_name,
                    "name": p.name,
                    "bio": p.bio,
                    "persona": p.persona,
                    "tier": p.tier,
                    "sec": p.sec,
                    "income": p.income,
                    "life_stage": p.life_stage,
                    "behavior": p.behavior,
                    "digital_pattern": p.digital_pattern,
                    "primary_language": p.primary_language,
                    "archetype": p.archetype,
                    "city": p.city,
                    "profession": p.profession,
                    "age": p.age,
                    "gender": p.gender,
                    "price_sensitivity": float(p.price_sensitivity),
                    "trust_factor": float(p.trust_factor),
                    "influence_susceptibility": float(p.influence_susceptibility),
                    "decision_speed": float(p.decision_speed),
                    "karma": p.karma,
                    "friend_count": p.friend_count,
                    "follower_count": p.follower_count,
                    "statuses_count": p.statuses_count,
                    "interested_topics": p.interested_topics,
                    "raw_profile": p.to_dict(),
                })
            # Upsert in chunks of 100 to stay within payload limits
            CHUNK = 100
            for i in range(0, len(rows), CHUNK):
                client.table("personas").upsert(
                    rows[i:i + CHUNK],
                    on_conflict="simulation_id,agent_id",
                ).execute()
            logger.info("Persisted %d personas to Supabase for %s", len(rows), simulation_id)
        except Exception as e:
            logger.debug("Supabase personas persistence skipped: %s", str(e)[:120])

    # ── Public API ───────────────────────────────────────────────────────────

    def create_simulation(
        self,
        project_id: str,
        graph_id: str,
        enable_twitter: bool = True,
        enable_reddit: bool = True,
        persona_overrides: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> SimulationState:
        """Create a new simulation.

        persona_overrides example (agency control):
            {"tier": {"Tier2": 0.7, "Tier1": 0.2, "Tier3": 0.1},
             "behavior": {"PriceSensitive": 0.5, "TrendDriven": 0.3, "SkepticalResearcher": 0.2}}
        """
        import uuid
        simulation_id = f"sim_{uuid.uuid4().hex[:12]}"

        state = SimulationState(
            simulation_id=simulation_id,
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=enable_twitter,
            enable_reddit=enable_reddit,
            persona_overrides=persona_overrides,
            status=SimulationStatus.CREATED,
        )

        self._save_simulation_state(state)
        logger.info(f"Simulation created: {simulation_id}, project={project_id}, "
                    f"graph={graph_id}, overrides={bool(persona_overrides)}")

        return state

    def prepare_simulation(
        self,
        simulation_id: str,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]] = None,
        use_llm_for_profiles: bool = True,
        progress_callback: Optional[callable] = None,
        parallel_profile_count: int = 3,
        use_lite_mode: bool = False,
        persona_overrides: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> SimulationState:
        """Prepare the simulation environment end-to-end.

        Steps:
          1. Read + filter entities from the KG
          2. Generate Indian market OASIS Agent profiles (parallel, with traits)
          3. LLM-driven config generation (IST rhythm + private-network dynamics)
          4. Save profile + config + state files
          5. Optionally persist to Supabase
        """
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        # Merge per-call overrides with state-level overrides (call wins)
        effective_overrides = persona_overrides or state.persona_overrides

        try:
            if use_lite_mode:
                logger.info(f"Micro-Lite mode enabled for {simulation_id} — forcing "
                            "zero-cost profiles + config")
                use_llm_for_profiles = False

            state.status = SimulationStatus.PREPARING
            if persona_overrides:
                state.persona_overrides = persona_overrides
            self._save_simulation_state(state)

            sim_dir = self._get_simulation_dir(simulation_id)

            # ── Stage 1: Read + filter entities ─────────────────────────────
            if progress_callback:
                progress_callback("reading", 0, "Connecting to KG...")

            reader = ZepEntityReader()

            if progress_callback:
                progress_callback("reading", 30, "Reading node data...")

            filtered = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=defined_entity_types,
                enrich_with_edges=True,
            )

            state.entities_count = filtered.filtered_count
            state.entity_types = list(filtered.entity_types)

            if progress_callback:
                progress_callback(
                    "reading", 100,
                    f"Done — {filtered.filtered_count} entities",
                    current=filtered.filtered_count,
                    total=filtered.filtered_count,
                )

            if filtered.filtered_count == 0:
                state.status = SimulationStatus.FAILED
                state.error = "No entities matched — check that the KG was built correctly."
                self._save_simulation_state(state)
                return state

            # ── Stage 2: Generate Agent profiles (parallel) ─────────────────
            total_entities = len(filtered.entities)

            if progress_callback:
                progress_callback(
                    "generating_profiles", 0, "Starting profile generation...",
                    current=0, total=total_entities,
                )

            # Pass persona_overrides and simulation_requirement via kwargs
            # (OasisProfileGenerator accepts **kwargs for forward-compat)
            generator = OasisProfileGenerator(
                graph_id=state.graph_id,
                persona_overrides=effective_overrides,
                simulation_requirement=simulation_requirement,
            )

            def profile_progress(current, total, msg):
                if progress_callback:
                    progress_callback(
                        "generating_profiles",
                        int(current / total * 100),
                        msg,
                        current=current,
                        total=total,
                        item_name=msg,
                    )

            profiles: List[OasisAgentProfile] = []

            with ThreadPoolExecutor(max_workers=parallel_profile_count) as executor:
                future_to_entity = {
                    executor.submit(
                        generator.generate_profile_from_entity,
                        entity,
                        idx + 1,
                        use_llm_for_profiles,
                    ): entity
                    for idx, entity in enumerate(filtered.entities)
                }

                for future in as_completed(future_to_entity):
                    entity = future_to_entity[future]
                    try:
                        profile = future.result()
                        profiles.append(profile)
                        profile_progress(len(profiles), total_entities,
                                         f"Generated: {entity.name}")
                    except Exception as exc:
                        logger.error(f"Profile generation failed for {entity.name}: {exc}")
                        profile_progress(len(profiles), total_entities,
                                         f"Failed: {entity.name}")

            state.profiles_count = len(profiles)

            # Tier / archetype distribution summary
            tier_dist: Dict[str, int] = {}
            archetype_dist: Dict[str, int] = {}
            for p in profiles:
                if p.tier:
                    tier_dist[p.tier] = tier_dist.get(p.tier, 0) + 1
                if p.archetype:
                    archetype_dist[p.archetype] = archetype_dist.get(p.archetype, 0) + 1
            state.tier_distribution = tier_dist
            state.archetype_distribution = archetype_dist

            logger.info(f"Profile distribution — tiers: {tier_dist}, "
                        f"archetypes: {archetype_dist}")

            # Save profile files (OASIS runners read from disk)
            if progress_callback:
                progress_callback(
                    "generating_profiles", 95, "Saving profile files...",
                    current=total_entities, total=total_entities,
                )

            if profiles:
                if state.enable_reddit:
                    reddit_path = os.path.join(sim_dir, "reddit_profiles.json")
                    self._save_profiles_to_json(profiles, reddit_path, "reddit")

                if state.enable_twitter:
                    twitter_path = os.path.join(sim_dir, "twitter_profiles.csv")
                    self._save_profiles_to_csv(profiles, twitter_path)

                # Persist to Supabase in background (non-blocking on failure)
                self._persist_personas_to_supabase(simulation_id, profiles)

            if progress_callback:
                progress_callback(
                    "generating_profiles", 100,
                    f"Profile generation complete — {len(profiles)} profiles",
                    current=len(profiles), total=len(profiles),
                )

            # ── Stage 3: LLM-driven config generation ───────────────────────
            if progress_callback:
                progress_callback(
                    "generating_config", 0, "Analysing campaign requirement...",
                    current=0, total=3,
                )

            config_generator = SimulationConfigGenerator()

            if progress_callback:
                progress_callback(
                    "generating_config", 30, "Generating system configuration...",
                    current=1, total=3,
                )

            if use_lite_mode:
                sim_params = config_generator.generate_lite_config(
                    simulation_id=simulation_id,
                    project_id=state.project_id,
                    graph_id=state.graph_id,
                    simulation_requirement=simulation_requirement,
                    entities=filtered.entities,
                    enable_twitter=state.enable_twitter,
                    enable_reddit=state.enable_reddit,
                )
            else:
                sim_params = config_generator.generate_config(
                    simulation_id=simulation_id,
                    project_id=state.project_id,
                    graph_id=state.graph_id,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    entities=filtered.entities,
                    enable_twitter=state.enable_twitter,
                    enable_reddit=state.enable_reddit,
                )

            if progress_callback:
                progress_callback(
                    "generating_config", 70, "Saving config file...",
                    current=2, total=3,
                )

            # Save config file
            config_path = os.path.join(sim_dir, "simulation_config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(sim_params.to_json())

            state.config_generated = True
            state.config_reasoning = sim_params.generation_reasoning

            if progress_callback:
                progress_callback(
                    "generating_config", 100, "Config generation complete",
                    current=3, total=3,
                )

            # Note: runner scripts stay in backend/scripts/ and are invoked by
            # simulation_runner — not copied per-simulation.

            state.status = SimulationStatus.READY
            self._save_simulation_state(state)

            logger.info(f"Simulation ready: {simulation_id}, "
                        f"entities={state.entities_count}, "
                        f"profiles={state.profiles_count}, "
                        f"tiers={state.tier_distribution}")

            return state

        except Exception as e:
            logger.error(f"Simulation prepare failed: {simulation_id}, error={str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            state.status = SimulationStatus.FAILED
            state.error = str(e)
            self._save_simulation_state(state)
            raise

    def _save_profiles_to_json(
        self, profiles: List[OasisAgentProfile],
        file_path: str, platform: str,
    ):
        """Save profiles to JSON (Reddit) — preserves Indian market fields."""
        data = []
        for p in profiles:
            if platform == "reddit":
                data.append(p.to_reddit_format())
            elif platform == "twitter":
                data.append(p.to_twitter_format())
            else:
                data.append(p.to_dict())

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_profiles_to_csv(
        self, profiles: List[OasisAgentProfile], file_path: str,
    ):
        """Save profiles to CSV (Twitter — OASIS format)."""
        if not profiles:
            return

        first_profile = profiles[0].to_twitter_format()
        headers = list(first_profile.keys())

        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for p in profiles:
                writer.writerow(p.to_twitter_format())

    def get_simulation(self, simulation_id: str) -> Optional[SimulationState]:
        return self._load_simulation_state(simulation_id)

    def list_simulations(
        self, project_id: Optional[str] = None,
    ) -> List[SimulationState]:
        simulations = []
        if os.path.exists(self.SIMULATION_DATA_DIR):
            for sim_id in os.listdir(self.SIMULATION_DATA_DIR):
                sim_path = os.path.join(self.SIMULATION_DATA_DIR, sim_id)
                if sim_id.startswith('.') or not os.path.isdir(sim_path):
                    continue
                state = self._load_simulation_state(sim_id)
                if state and (project_id is None or state.project_id == project_id):
                    simulations.append(state)
        return simulations

    def get_profiles(
        self, simulation_id: str, platform: str = "reddit",
    ) -> List[Dict[str, Any]]:
        state = self._load_simulation_state(simulation_id)
        if not state:
            raise ValueError(f"Simulation not found: {simulation_id}")

        sim_dir = self._get_simulation_dir(simulation_id)
        profile_path = os.path.join(sim_dir, f"{platform}_profiles.json")

        if not os.path.exists(profile_path):
            return []

        with open(profile_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_simulation_config(self, simulation_id: str) -> Optional[Dict[str, Any]]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        if not os.path.exists(config_path):
            return None
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_run_instructions(self, simulation_id: str) -> Dict[str, str]:
        sim_dir = self._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")
        scripts_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../scripts')
        )

        return {
            "simulation_dir": sim_dir,
            "scripts_dir": scripts_dir,
            "config_file": config_path,
            "commands": {
                "twitter": f"python {scripts_dir}/run_twitter_simulation.py --config {config_path}",
                "reddit":  f"python {scripts_dir}/run_reddit_simulation.py --config {config_path}",
                "parallel": f"python {scripts_dir}/run_parallel_simulation.py --config {config_path}",
            },
            "instructions": (
                f"1. Activate the conda environment: conda activate AXonic\n"
                f"2. Run simulation (scripts in {scripts_dir}):\n"
                f"   - Twitter only: python {scripts_dir}/run_twitter_simulation.py --config {config_path}\n"
                f"   - Reddit only:  python {scripts_dir}/run_reddit_simulation.py --config {config_path}\n"
                f"   - Both (parallel): python {scripts_dir}/run_parallel_simulation.py --config {config_path}"
            ),
        }