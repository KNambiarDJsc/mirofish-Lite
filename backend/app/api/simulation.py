"""
Simulation API routes — AXonic (Indian Market)

Endpoints for entity reading, simulation prep/run/control, Interview commands,
and real-time monitoring. Keeps the original route paths and response shapes
so the existing frontend continues to work.
"""

import os
import traceback
from flask import request, jsonify, send_file
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import simulation_bp
from ..config import Config
from ..services.supabase_entity_reader import SupabaseEntityReader as ZepEntityReader
from ..services.oasis_profile_generator import OasisProfileGenerator
from ..services.simulation_manager import SimulationManager, SimulationStatus
from ..services.simulation_runner import SimulationRunner, RunnerStatus
from ..utils.logger import get_logger
from ..models.project import ProjectManager

logger = get_logger('axonic.api.simulation')


# Interview prompt prefix — keeps Agent from calling tools, replies in plain text.
# For the Indian market, allow answers in Hinglish/regional if natural.
INTERVIEW_PROMPT_PREFIX = (
    "Using your persona, past memories, and actions — reply directly in text "
    "(Hinglish or regional language is fine if natural for you). Do NOT call any tools. "
    "Question: "
)


def optimize_interview_prompt(prompt: str) -> str:
    """Attach the no-tool-call prefix to every interview prompt."""
    if not prompt:
        return prompt
    if prompt.startswith(INTERVIEW_PROMPT_PREFIX):
        return prompt
    return f"{INTERVIEW_PROMPT_PREFIX}{prompt}"


# ═══════════════════════════════════════════════════════════════════════════════
# Entity read endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@simulation_bp.route('/entities/<graph_id>', methods=['GET'])
def get_graph_entities(graph_id: str):
    """Get all entities in a graph (filtered).

    Query params:
        entity_types: comma-separated list to further filter
        enrich:       include related edge info (default true)
    """
    try:
        entity_types_str = request.args.get('entity_types', '')
        entity_types = [t.strip() for t in entity_types_str.split(',') if t.strip()] \
            if entity_types_str else None
        enrich = request.args.get('enrich', 'true').lower() == 'true'

        logger.info(f"Get graph entities: graph_id={graph_id}, "
                    f"entity_types={entity_types}, enrich={enrich}")

        reader = ZepEntityReader()
        result = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=enrich,
        )

        return jsonify({"success": True, "data": result.to_dict()})

    except Exception as e:
        logger.error(f"Get graph entities failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/entities/<graph_id>/<entity_uuid>', methods=['GET'])
def get_entity_detail(graph_id: str, entity_uuid: str):
    """Get detailed info for a single entity."""
    try:
        reader = ZepEntityReader()
        entity = reader.get_entity_with_context(graph_id, entity_uuid)

        if not entity:
            return jsonify({
                "success": False,
                "error": f"Entity not found: {entity_uuid}",
            }), 404

        return jsonify({"success": True, "data": entity.to_dict()})

    except Exception as e:
        logger.error(f"Get entity detail failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/entities/<graph_id>/by-type/<entity_type>', methods=['GET'])
def get_entities_by_type(graph_id: str, entity_type: str):
    """Get all entities of a specific type."""
    try:
        enrich = request.args.get('enrich', 'true').lower() == 'true'

        reader = ZepEntityReader()
        entities = reader.get_entities_by_type(
            graph_id=graph_id,
            entity_type=entity_type,
            enrich_with_edges=enrich,
        )

        return jsonify({
            "success": True,
            "data": {
                "entity_type": entity_type,
                "count": len(entities),
                "entities": [e.to_dict() for e in entities],
            },
        })

    except Exception as e:
        logger.error(f"Get entities by type failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Simulation management endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@simulation_bp.route('/create', methods=['POST'])
def create_simulation():
    """Create a new simulation.

    Request JSON:
        {
            "project_id": "proj_xxxx",       // required
            "graph_id": "axonic_xxxx",       // optional, falls back to project's graph_id
            "enable_twitter": true,          // optional, default true
            "enable_reddit": true,           // optional, default true
            "persona_overrides": {           // optional — agency control knob
                "tier": {"Tier2": 0.7, "Tier1": 0.2, "Tier3": 0.1},
                "behavior": {"PriceSensitive": 0.5, "TrendDriven": 0.3,
                             "SkepticalResearcher": 0.2}
            }
        }

    Notes:
        Simulation config (max_rounds, timing, etc.) is LLM-generated during
        /prepare — no need to set manually.
    """
    try:
        data = request.get_json() or {}

        project_id = data.get('project_id')
        if not project_id:
            return jsonify({
                "success": False,
                "error": "project_id is required",
            }), 400

        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project not found: {project_id}",
            }), 404

        graph_id = data.get('graph_id') or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error": "Project has no knowledge graph yet — call /api/graph/build first",
            }), 400

        persona_overrides = data.get('persona_overrides')

        manager = SimulationManager()
        state = manager.create_simulation(
            project_id=project_id,
            graph_id=graph_id,
            enable_twitter=data.get('enable_twitter', True),
            enable_reddit=data.get('enable_reddit', True),
            persona_overrides=persona_overrides,
        )

        return jsonify({"success": True, "data": state.to_dict()})

    except Exception as e:
        logger.error(f"Create simulation failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


def _check_simulation_prepared(simulation_id: str) -> tuple:
    """Check whether a simulation has already been prepared.

    Conditions:
      1. state.json exists and status is "ready" (or later)
      2. Required files present: reddit_profiles.json, twitter_profiles.csv,
         simulation_config.json

    Returns (is_prepared: bool, info: dict).
    """
    import json

    simulation_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)

    if not os.path.exists(simulation_dir):
        return False, {"reason": "Simulation directory does not exist"}

    required_files = [
        "state.json",
        "simulation_config.json",
        "reddit_profiles.json",
        "twitter_profiles.csv",
    ]

    existing_files = []
    missing_files = []
    for f in required_files:
        file_path = os.path.join(simulation_dir, f)
        if os.path.exists(file_path):
            existing_files.append(f)
        else:
            missing_files.append(f)

    if missing_files:
        return False, {
            "reason": "Missing required files",
            "missing_files": missing_files,
            "existing_files": existing_files,
        }

    state_file = os.path.join(simulation_dir, "state.json")
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        status = state_data.get("status", "")
        config_generated = state_data.get("config_generated", False)

        logger.debug(f"Prepare check: {simulation_id}, status={status}, "
                     f"config_generated={config_generated}")

        prepared_statuses = ["ready", "preparing", "running", "completed",
                             "stopped", "failed"]
        if status in prepared_statuses and config_generated:
            profiles_file = os.path.join(simulation_dir, "reddit_profiles.json")

            profiles_count = 0
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    profiles_data = json.load(f)
                    profiles_count = len(profiles_data) if isinstance(profiles_data, list) else 0

            # If preparing but files complete, auto-promote to ready
            if status == "preparing":
                try:
                    state_data["status"] = "ready"
                    from datetime import datetime
                    state_data["updated_at"] = datetime.now().isoformat()
                    with open(state_file, 'w', encoding='utf-8') as f:
                        json.dump(state_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Auto-promoted {simulation_id}: preparing -> ready")
                    status = "ready"
                except Exception as e:
                    logger.warning(f"Auto-promote failed: {e}")

            logger.info(f"Simulation {simulation_id} prepared "
                        f"(status={status}, config_generated={config_generated})")
            return True, {
                "status": status,
                "entities_count": state_data.get("entities_count", 0),
                "profiles_count": profiles_count,
                "entity_types": state_data.get("entity_types", []),
                "tier_distribution": state_data.get("tier_distribution", {}),
                "archetype_distribution": state_data.get("archetype_distribution", {}),
                "config_generated": config_generated,
                "created_at": state_data.get("created_at"),
                "updated_at": state_data.get("updated_at"),
                "existing_files": existing_files,
            }
        else:
            logger.warning(f"Simulation {simulation_id} not prepared "
                           f"(status={status}, config_generated={config_generated})")
            return False, {
                "reason": f"Status not in prepared list or config_generated=false: "
                          f"status={status}, config_generated={config_generated}",
                "status": status,
                "config_generated": config_generated,
            }

    except Exception as e:
        return False, {"reason": f"Failed to read state file: {str(e)}"}


@simulation_bp.route('/prepare', methods=['POST'])
def prepare_simulation():
    """Prepare the simulation environment (async task — LLM generates all params).

    Long-running — returns a task_id immediately. Poll
    /api/simulation/prepare/status for progress.

    Features:
      - Auto-detect existing complete preparation (skip regeneration)
      - Force regenerate with force_regenerate=true
      - Agency persona_overrides for tier/behavior/language mix control

    Steps:
      1. Check for existing complete preparation
      2. Read + filter KG entities
      3. Generate Indian market OASIS Agent profiles (with retry)
      4. LLM-generate simulation config (with retry)
      5. Save all artifacts to disk + optional Supabase persistence

    Request JSON:
        {
            "simulation_id": "sim_xxxx",                 // required
            "entity_types": ["Tier1Consumer", ...],      // optional
            "use_llm_for_profiles": true,                // optional
            "parallel_profile_count": 5,                 // optional, default 5
            "force_regenerate": false,                   // optional, default false
            "use_lite_mode": false,                      // optional, zero-LLM mode
            "persona_overrides": {                       // optional, agency control
                "tier": {"Tier2": 0.7, "Tier1": 0.2, "Tier3": 0.1},
                "behavior": {"PriceSensitive": 0.5, "TrendDriven": 0.5}
            }
        }
    """
    import threading
    from ..models.task import TaskManager, TaskStatus

    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation not found: {simulation_id}",
            }), 404

        force_regenerate = data.get('force_regenerate', False)
        logger.info(f"/prepare request: simulation_id={simulation_id}, "
                    f"force_regenerate={force_regenerate}")

        if not force_regenerate:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                logger.info(f"Simulation {simulation_id} already prepared — skipping")
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "message": "Preparation already complete — skipped",
                        "already_prepared": True,
                        "prepare_info": prepare_info,
                    },
                })
            else:
                logger.info(f"Simulation {simulation_id} needs preparation — starting task")

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project not found: {state.project_id}",
            }), 404

        simulation_requirement = project.simulation_requirement or ""
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Project is missing simulation_requirement",
            }), 400

        document_text = ProjectManager.get_extracted_text(state.project_id) or ""

        entity_types_list = data.get('entity_types')
        use_llm_for_profiles = data.get('use_llm_for_profiles', False)
        parallel_profile_count = data.get('parallel_profile_count', 5)
        use_lite_mode = data.get('use_lite_mode', False)
        persona_overrides = data.get('persona_overrides')

        # Persist persona_overrides to state immediately so /state reflects it
        if persona_overrides:
            state.persona_overrides = persona_overrides
            manager._save_simulation_state(state)

        # Pre-fetch entity count synchronously so frontend has expected total
        try:
            logger.info(f"Pre-fetching entity count: graph_id={state.graph_id}")
            reader = ZepEntityReader()
            filtered_preview = reader.filter_defined_entities(
                graph_id=state.graph_id,
                defined_entity_types=entity_types_list,
                enrich_with_edges=False,
            )
            state.entities_count = filtered_preview.filtered_count
            state.entity_types = list(filtered_preview.entity_types)
            logger.info(f"Expected entities: {filtered_preview.filtered_count}, "
                        f"types: {filtered_preview.entity_types}")
        except Exception as e:
            logger.warning(f"Pre-fetch entity count failed (will retry in task): {e}")

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_prepare",
            metadata={
                "simulation_id": simulation_id,
                "project_id": state.project_id,
            },
        )

        state.status = SimulationStatus.PREPARING
        manager._save_simulation_state(state)

        def run_prepare():
            try:
                task_manager.update_task(
                    task_id, status=TaskStatus.PROCESSING, progress=0,
                    message="Starting preparation...",
                )

                stage_details = {}

                def progress_callback(stage, progress, message, **kwargs):
                    stage_weights = {
                        "reading":             (0, 20),
                        "generating_profiles": (20, 70),
                        "generating_config":   (70, 90),
                        "copying_scripts":     (90, 100),
                    }
                    start, end = stage_weights.get(stage, (0, 100))
                    current_progress = int(start + (end - start) * progress / 100)

                    stage_names = {
                        "reading":             "Reading KG entities",
                        "generating_profiles": "Generating Agent personas",
                        "generating_config":   "Generating simulation config",
                        "copying_scripts":     "Preparing simulation scripts",
                    }
                    stage_index = (
                        list(stage_weights.keys()).index(stage) + 1
                        if stage in stage_weights else 1
                    )
                    total_stages = len(stage_weights)

                    stage_details[stage] = {
                        "stage_name": stage_names.get(stage, stage),
                        "stage_progress": progress,
                        "current": kwargs.get("current", 0),
                        "total": kwargs.get("total", 0),
                        "item_name": kwargs.get("item_name", ""),
                    }

                    detail = stage_details[stage]
                    progress_detail_data = {
                        "current_stage": stage,
                        "current_stage_name": stage_names.get(stage, stage),
                        "stage_index": stage_index,
                        "total_stages": total_stages,
                        "stage_progress": progress,
                        "current_item": detail["current"],
                        "total_items": detail["total"],
                        "item_description": message,
                    }

                    if detail["total"] > 0:
                        detailed_message = (
                            f"[{stage_index}/{total_stages}] "
                            f"{stage_names.get(stage, stage)}: "
                            f"{detail['current']}/{detail['total']} — {message}"
                        )
                    else:
                        detailed_message = (
                            f"[{stage_index}/{total_stages}] "
                            f"{stage_names.get(stage, stage)}: {message}"
                        )

                    task_manager.update_task(
                        task_id,
                        progress=current_progress,
                        message=detailed_message,
                        progress_detail=progress_detail_data,
                    )

                result_state = manager.prepare_simulation(
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement,
                    document_text=document_text,
                    defined_entity_types=entity_types_list,
                    use_llm_for_profiles=use_llm_for_profiles,
                    progress_callback=progress_callback,
                    parallel_profile_count=parallel_profile_count,
                    use_lite_mode=use_lite_mode,
                    persona_overrides=persona_overrides,
                )

                task_manager.complete_task(task_id, result=result_state.to_simple_dict())

            except Exception as e:
                logger.error(f"Prepare task failed: {str(e)}")
                task_manager.fail_task(task_id, str(e))

                state = manager.get_simulation(simulation_id)
                if state:
                    state.status = SimulationStatus.FAILED
                    state.error = str(e)
                    manager._save_simulation_state(state)

        thread = threading.Thread(target=run_prepare, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "task_id": task_id,
                "status": "preparing",
                "message": "Preparation task started — poll /api/simulation/prepare/status",
                "already_prepared": False,
                "expected_entities_count": state.entities_count,
                "entity_types": state.entity_types,
                "persona_overrides_applied": bool(persona_overrides),
            },
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404

    except Exception as e:
        logger.error(f"Start prepare task failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/prepare/status', methods=['POST'])
def get_prepare_status():
    """Poll prepare task progress.

    Accepts either task_id (task progress) or simulation_id (check existing prep).
    """
    from ..models.task import TaskManager

    try:
        data = request.get_json() or {}

        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')

        if simulation_id:
            is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
            if is_prepared:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "ready",
                        "progress": 100,
                        "message": "Preparation already complete",
                        "already_prepared": True,
                        "prepare_info": prepare_info,
                    },
                })

        if not task_id:
            if simulation_id:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "status": "not_started",
                        "progress": 0,
                        "message": "Not started — call /api/simulation/prepare",
                        "already_prepared": False,
                    },
                })
            return jsonify({
                "success": False,
                "error": "task_id or simulation_id required",
            }), 400

        task_manager = TaskManager()
        task = task_manager.get_task(task_id)

        if not task:
            if simulation_id:
                is_prepared, prepare_info = _check_simulation_prepared(simulation_id)
                if is_prepared:
                    return jsonify({
                        "success": True,
                        "data": {
                            "simulation_id": simulation_id,
                            "task_id": task_id,
                            "status": "ready",
                            "progress": 100,
                            "message": "Task complete (preparation exists)",
                            "already_prepared": True,
                            "prepare_info": prepare_info,
                        },
                    })

            return jsonify({
                "success": False,
                "error": f"Task not found: {task_id}",
            }), 404

        task_dict = task.to_dict()
        task_dict["already_prepared"] = False

        return jsonify({"success": True, "data": task_dict})

    except Exception as e:
        logger.error(f"Get prepare status failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@simulation_bp.route('/<simulation_id>', methods=['GET'])
def get_simulation(simulation_id: str):
    """Get simulation status."""
    try:
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation not found: {simulation_id}",
            }), 404

        result = state.to_dict()

        if state.status == SimulationStatus.READY:
            result["run_instructions"] = manager.get_run_instructions(simulation_id)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Get simulation failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/list', methods=['GET'])
def list_simulations():
    """List simulations. Query: project_id (optional filter)."""
    try:
        project_id = request.args.get('project_id')

        manager = SimulationManager()
        simulations = manager.list_simulations(project_id=project_id)

        return jsonify({
            "success": True,
            "data": [s.to_dict() for s in simulations],
            "count": len(simulations),
        })

    except Exception as e:
        logger.error(f"List simulations failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


def _get_report_id_for_simulation(simulation_id: str) -> str:
    """Find the latest report_id associated with a simulation."""
    import json
    reports_dir = os.path.join(
        os.path.dirname(__file__), '../../uploads/reports'
    )
    if not os.path.exists(reports_dir):
        return None

    matching_reports = []
    try:
        for report_folder in os.listdir(reports_dir):
            report_path = os.path.join(reports_dir, report_folder)
            if not os.path.isdir(report_path):
                continue
            meta_file = os.path.join(report_path, "meta.json")
            if not os.path.exists(meta_file):
                continue
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                if meta.get("simulation_id") == simulation_id:
                    matching_reports.append({
                        "report_id": meta.get("report_id"),
                        "created_at": meta.get("created_at", ""),
                        "status": meta.get("status", ""),
                    })
            except Exception:
                continue

        if not matching_reports:
            return None

        matching_reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return matching_reports[0].get("report_id")

    except Exception as e:
        logger.warning(f"Find report for simulation {simulation_id} failed: {e}")
        return None


@simulation_bp.route('/history', methods=['GET'])
def get_simulation_history():
    """Get enriched simulation history (project details + report IDs) for the homepage."""
    try:
        limit = request.args.get('limit', 20, type=int)

        manager = SimulationManager()
        simulations = manager.list_simulations()[:limit]

        enriched = []
        for sim in simulations:
            sim_dict = sim.to_dict()

            config = manager.get_simulation_config(sim.simulation_id)
            if config:
                sim_dict["simulation_requirement"] = config.get("simulation_requirement", "")
                time_config = config.get("time_config", {})
                sim_dict["total_simulation_hours"] = time_config.get("total_simulation_hours", 0)
                recommended_rounds = int(
                    time_config.get("total_simulation_hours", 0) * 60
                    / max(time_config.get("minutes_per_round", 60), 1)
                )
            else:
                sim_dict["simulation_requirement"] = ""
                sim_dict["total_simulation_hours"] = 0
                recommended_rounds = 0

            run_state = SimulationRunner.get_run_state(sim.simulation_id)
            if run_state:
                sim_dict["current_round"] = run_state.current_round
                sim_dict["runner_status"] = run_state.runner_status.value
                sim_dict["total_rounds"] = (
                    run_state.total_rounds if run_state.total_rounds > 0
                    else recommended_rounds
                )
            else:
                sim_dict["current_round"] = 0
                sim_dict["runner_status"] = "idle"
                sim_dict["total_rounds"] = recommended_rounds

            project = ProjectManager.get_project(sim.project_id)
            if project and hasattr(project, 'files') and project.files:
                sim_dict["files"] = [
                    {"filename": f.get("filename", "Unknown file")}
                    for f in project.files[:3]
                ]
            else:
                sim_dict["files"] = []

            sim_dict["report_id"] = _get_report_id_for_simulation(sim.simulation_id)
            sim_dict["version"] = "v1.0.2"

            try:
                sim_dict["created_date"] = sim_dict.get("created_at", "")[:10]
            except Exception:
                sim_dict["created_date"] = ""

            enriched.append(sim_dict)

        return jsonify({
            "success": True,
            "data": enriched,
            "count": len(enriched),
        })

    except Exception as e:
        logger.error(f"Get simulation history failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/profiles', methods=['GET'])
def get_simulation_profiles(simulation_id: str):
    """Get Agent profiles for a simulation."""
    try:
        platform = request.args.get('platform', 'reddit')

        manager = SimulationManager()
        profiles = manager.get_profiles(simulation_id, platform=platform)

        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "count": len(profiles),
                "profiles": profiles,
            },
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404

    except Exception as e:
        logger.error(f"Get profiles failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/profiles/realtime', methods=['GET'])
def get_simulation_profiles_realtime(simulation_id: str):
    """Real-time profile read (reads file directly; useful during generation)."""
    import json
    import csv
    from datetime import datetime

    try:
        platform = request.args.get('platform', 'reddit')

        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": f"Simulation not found: {simulation_id}",
            }), 404

        if platform == "reddit":
            profiles_file = os.path.join(sim_dir, "reddit_profiles.json")
        else:
            profiles_file = os.path.join(sim_dir, "twitter_profiles.csv")

        file_exists = os.path.exists(profiles_file)
        profiles = []
        file_modified_at = None

        if file_exists:
            file_stat = os.stat(profiles_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            try:
                if platform == "reddit":
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        profiles = json.load(f)
                else:
                    with open(profiles_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        profiles = list(reader)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Read profiles file failed (possibly mid-write): {e}")
                profiles = []

        is_generating = False
        total_expected = None

        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    total_expected = state_data.get("entities_count")
            except Exception:
                pass

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "platform": platform,
                "count": len(profiles),
                "total_expected": total_expected,
                "is_generating": is_generating,
                "file_exists": file_exists,
                "file_modified_at": file_modified_at,
                "profiles": profiles,
            },
        })

    except Exception as e:
        logger.error(f"Realtime profiles failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/config/realtime', methods=['GET'])
def get_simulation_config_realtime(simulation_id: str):
    """Real-time config read (reads file directly; useful during generation)."""
    import json
    from datetime import datetime

    try:
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            return jsonify({
                "success": False,
                "error": f"Simulation not found: {simulation_id}",
            }), 404

        config_file = os.path.join(sim_dir, "simulation_config.json")
        file_exists = os.path.exists(config_file)
        config = None
        file_modified_at = None

        if file_exists:
            file_stat = os.stat(config_file)
            file_modified_at = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Read config file failed (possibly mid-write): {e}")
                config = None

        is_generating = False
        generation_stage = None
        config_generated = False

        state_file = os.path.join(sim_dir, "state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    status = state_data.get("status", "")
                    is_generating = status == "preparing"
                    config_generated = state_data.get("config_generated", False)

                    if is_generating:
                        if state_data.get("profiles_generated", False):
                            generation_stage = "generating_config"
                        else:
                            generation_stage = "generating_profiles"
                    elif status == "ready":
                        generation_stage = "completed"
            except Exception:
                pass

        response_data = {
            "simulation_id": simulation_id,
            "file_exists": file_exists,
            "file_modified_at": file_modified_at,
            "is_generating": is_generating,
            "generation_stage": generation_stage,
            "config_generated": config_generated,
            "config": config,
        }

        if config:
            response_data["summary"] = {
                "total_agents": len(config.get("agent_configs", [])),
                "simulation_hours": config.get("time_config", {}).get("total_simulation_hours"),
                "initial_posts_count": len(config.get("event_config", {}).get("initial_posts", [])),
                "hot_topics_count": len(config.get("event_config", {}).get("hot_topics", [])),
                "has_twitter_config": "twitter_config" in config,
                "has_reddit_config": "reddit_config" in config,
                "has_private_network": "private_network" in config,
                "has_amplification": "amplification" in config,
                "generated_at": config.get("generated_at"),
                "llm_model": config.get("llm_model"),
            }

        return jsonify({"success": True, "data": response_data})

    except Exception as e:
        logger.error(f"Realtime config failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/config', methods=['GET'])
def get_simulation_config(simulation_id: str):
    """Get simulation config (full LLM-generated config)."""
    try:
        manager = SimulationManager()
        config = manager.get_simulation_config(simulation_id)

        if not config:
            return jsonify({
                "success": False,
                "error": "Config does not exist — call /prepare first",
            }), 404

        return jsonify({"success": True, "data": config})

    except Exception as e:
        logger.error(f"Get config failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/config/download', methods=['GET'])
def download_simulation_config(simulation_id: str):
    """Download simulation config file."""
    try:
        manager = SimulationManager()
        sim_dir = manager._get_simulation_dir(simulation_id)
        config_path = os.path.join(sim_dir, "simulation_config.json")

        if not os.path.exists(config_path):
            return jsonify({
                "success": False,
                "error": "Config file does not exist — call /prepare first",
            }), 404

        return send_file(
            config_path, as_attachment=True,
            download_name="simulation_config.json",
        )

    except Exception as e:
        logger.error(f"Download config failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/script/<script_name>/download', methods=['GET'])
def download_simulation_script(script_name: str):
    """Download a simulation runner script (from backend/scripts/)."""
    try:
        scripts_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '../../scripts')
        )

        allowed_scripts = [
            "run_twitter_simulation.py",
            "run_reddit_simulation.py",
            "run_parallel_simulation.py",
            "action_logger.py",
        ]

        if script_name not in allowed_scripts:
            return jsonify({
                "success": False,
                "error": f"Unknown script: {script_name}, allowed: {allowed_scripts}",
            }), 400

        script_path = os.path.join(scripts_dir, script_name)
        if not os.path.exists(script_path):
            return jsonify({
                "success": False,
                "error": f"Script not found: {script_name}",
            }), 404

        return send_file(script_path, as_attachment=True, download_name=script_name)

    except Exception as e:
        logger.error(f"Download script failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Standalone profile generation
# ═══════════════════════════════════════════════════════════════════════════════

@simulation_bp.route('/generate-profiles', methods=['POST'])
def generate_profiles():
    """Generate OASIS Agent profiles from a KG directly (no simulation created).

    Request JSON:
        {
            "graph_id": "axonic_xxxx",         // required
            "entity_types": ["Tier1Consumer"], // optional
            "use_llm": true,                   // optional
            "platform": "reddit",              // optional
            "persona_overrides": {...}         // optional — agency mix control
        }
    """
    try:
        data = request.get_json() or {}

        graph_id = data.get('graph_id')
        if not graph_id:
            return jsonify({"success": False, "error": "graph_id is required"}), 400

        entity_types = data.get('entity_types')
        use_llm = data.get('use_llm', True)
        platform = data.get('platform', 'reddit')
        persona_overrides = data.get('persona_overrides')

        reader = ZepEntityReader()
        filtered = reader.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=entity_types,
            enrich_with_edges=True,
        )

        if filtered.filtered_count == 0:
            return jsonify({
                "success": False,
                "error": "No matching entities found",
            }), 400

        generator = OasisProfileGenerator(
            graph_id=graph_id,
            persona_overrides=persona_overrides,
        )

        profiles = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_entity = {
                executor.submit(
                    generator.generate_profile_from_entity,
                    entity, idx + 1, use_llm,
                ): entity
                for idx, entity in enumerate(filtered.entities)
            }

            for future in as_completed(future_to_entity):
                try:
                    profile = future.result()
                    profiles.append(profile)
                except Exception as exc:
                    entity = future_to_entity[future]
                    logger.error(f"Profile generation failed for {entity.name}: {exc}")

        if platform == "reddit":
            profiles_data = [p.to_reddit_format() for p in profiles]
        elif platform == "twitter":
            profiles_data = [p.to_twitter_format() for p in profiles]
        else:
            profiles_data = [p.to_dict() for p in profiles]

        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "entity_types": list(filtered.entity_types),
                "count": len(profiles_data),
                "profiles": profiles_data,
            },
        })

    except Exception as e:
        logger.error(f"Generate profiles failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Simulation control endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@simulation_bp.route('/start', methods=['POST'])
def start_simulation():
    """Start running a prepared simulation.

    Request JSON:
        {
            "simulation_id": "sim_xxxx",              // required
            "platform": "parallel",                   // optional: twitter|reddit|parallel
            "max_rounds": 100,                        // optional: cap round count
            "enable_graph_memory_update": false,      // optional: stream to KG
            "force": false                            // optional: hard restart
        }
    """
    try:
        data = request.get_json() or {}

        if not Config.LLM_API_KEY:
            logger.error("Cannot start simulation: LLM_API_KEY (or GEMINI_API_KEY) not set")
            return jsonify({
                "success": False,
                "error": "No LLM provider configured. Set GEMINI_API_KEY in .env.",
            }), 400

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        platform = data.get('platform', 'parallel')
        max_rounds = data.get('max_rounds')
        enable_graph_memory_update = data.get('enable_graph_memory_update', False)
        force = data.get('force', False)

        if max_rounds is not None:
            try:
                max_rounds = int(max_rounds)
                if max_rounds <= 0:
                    return jsonify({
                        "success": False,
                        "error": "max_rounds must be a positive integer",
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": "max_rounds must be a valid integer",
                }), 400

        if platform not in ['twitter', 'reddit', 'parallel']:
            return jsonify({
                "success": False,
                "error": f"Invalid platform: {platform}. Allowed: twitter|reddit|parallel",
            }), 400

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)

        if not state:
            return jsonify({
                "success": False,
                "error": f"Simulation not found: {simulation_id}",
            }), 404

        force_restarted = False

        if state.status != SimulationStatus.READY:
            is_prepared, _ = _check_simulation_prepared(simulation_id)

            if is_prepared:
                if state.status == SimulationStatus.RUNNING:
                    run_state = SimulationRunner.get_run_state(simulation_id)
                    if run_state and run_state.runner_status.value == "running":
                        if force:
                            logger.info(f"Force mode: stopping running simulation {simulation_id}")
                            try:
                                SimulationRunner.stop_simulation(simulation_id)
                            except Exception as e:
                                logger.warning(f"Stop warning: {str(e)}")
                        else:
                            return jsonify({
                                "success": False,
                                "error": "Simulation already running — call /stop first or use force=true",
                            }), 400

                if force:
                    logger.info(f"Force mode: cleaning simulation logs {simulation_id}")
                    cleanup_result = SimulationRunner.cleanup_simulation_logs(simulation_id)
                    if not cleanup_result.get("success"):
                        logger.warning(f"Cleanup warning: {cleanup_result.get('errors')}")
                    force_restarted = True

                logger.info(f"Simulation {simulation_id} already prepared — "
                            f"resetting to ready (was {state.status.value})")
                state.status = SimulationStatus.READY
                manager._save_simulation_state(state)
            else:
                return jsonify({
                    "success": False,
                    "error": f"Simulation not ready (status={state.status.value}). "
                             "Call /prepare first.",
                }), 400

        graph_id = None
        if enable_graph_memory_update:
            graph_id = state.graph_id
            if not graph_id:
                project = ProjectManager.get_project(state.project_id)
                if project:
                    graph_id = project.graph_id

            if not graph_id:
                return jsonify({
                    "success": False,
                    "error": "Graph memory update requires a valid graph_id. "
                             "Ensure the project has a built KG.",
                }), 400

            logger.info(f"Graph memory update enabled: "
                        f"simulation_id={simulation_id}, graph_id={graph_id}")

        run_state = SimulationRunner.start_simulation(
            simulation_id=simulation_id,
            platform=platform,
            max_rounds=max_rounds,
            enable_graph_memory_update=enable_graph_memory_update,
            graph_id=graph_id,
        )

        state.status = SimulationStatus.RUNNING
        manager._save_simulation_state(state)

        response_data = run_state.to_dict()
        if max_rounds:
            response_data['max_rounds_applied'] = max_rounds
        response_data['graph_memory_update_enabled'] = enable_graph_memory_update
        response_data['force_restarted'] = force_restarted
        if enable_graph_memory_update:
            response_data['graph_id'] = graph_id

        return jsonify({"success": True, "data": response_data})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Start simulation failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/stop', methods=['POST'])
def stop_simulation():
    """Stop a running simulation."""
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        run_state = SimulationRunner.stop_simulation(simulation_id)

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.PAUSED
            manager._save_simulation_state(state)

        return jsonify({"success": True, "data": run_state.to_dict()})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Stop simulation failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Runtime monitoring
# ═══════════════════════════════════════════════════════════════════════════════

@simulation_bp.route('/<simulation_id>/run-status', methods=['GET'])
def get_run_status(simulation_id: str):
    """Get real-time simulation run status (for polling)."""
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)

        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "current_round": 0,
                    "total_rounds": 0,
                    "progress_percent": 0,
                    "twitter_actions_count": 0,
                    "reddit_actions_count": 0,
                    "total_actions_count": 0,
                },
            })

        return jsonify({"success": True, "data": run_state.to_dict()})

    except Exception as e:
        logger.error(f"Get run status failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/run-status/detail', methods=['GET'])
def get_run_status_detail(simulation_id: str):
    """Detailed simulation run status (with all actions)."""
    try:
        run_state = SimulationRunner.get_run_state(simulation_id)
        platform_filter = request.args.get('platform')

        if not run_state:
            return jsonify({
                "success": True,
                "data": {
                    "simulation_id": simulation_id,
                    "runner_status": "idle",
                    "all_actions": [],
                    "twitter_actions": [],
                    "reddit_actions": [],
                },
            })

        all_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id, platform=platform_filter,
        )

        twitter_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id, platform="twitter",
        ) if not platform_filter or platform_filter == "twitter" else []

        reddit_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id, platform="reddit",
        ) if not platform_filter or platform_filter == "reddit" else []

        current_round = run_state.current_round
        recent_actions = SimulationRunner.get_all_actions(
            simulation_id=simulation_id, platform=platform_filter,
            round_num=current_round,
        ) if current_round > 0 else []

        result = run_state.to_dict()
        result["all_actions"] = [a.to_dict() for a in all_actions]
        result["twitter_actions"] = [a.to_dict() for a in twitter_actions]
        result["reddit_actions"] = [a.to_dict() for a in reddit_actions]
        result["rounds_count"] = len(run_state.rounds)
        result["recent_actions"] = [a.to_dict() for a in recent_actions]

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Get detailed status failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/actions', methods=['GET'])
def get_simulation_actions(simulation_id: str):
    """Get Agent action history with filters."""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        platform = request.args.get('platform')
        agent_id = request.args.get('agent_id', type=int)
        round_num = request.args.get('round_num', type=int)

        actions = SimulationRunner.get_actions(
            simulation_id=simulation_id,
            limit=limit, offset=offset,
            platform=platform, agent_id=agent_id, round_num=round_num,
        )

        return jsonify({
            "success": True,
            "data": {
                "count": len(actions),
                "actions": [a.to_dict() for a in actions],
            },
        })

    except Exception as e:
        logger.error(f"Get actions failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/timeline', methods=['GET'])
def get_simulation_timeline(simulation_id: str):
    """Get simulation timeline (rounds aggregated) for progress view."""
    try:
        start_round = request.args.get('start_round', 0, type=int)
        end_round = request.args.get('end_round', type=int)

        timeline = SimulationRunner.get_timeline(
            simulation_id=simulation_id,
            start_round=start_round, end_round=end_round,
        )

        return jsonify({
            "success": True,
            "data": {
                "rounds_count": len(timeline),
                "timeline": timeline,
            },
        })

    except Exception as e:
        logger.error(f"Get timeline failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/agent-stats', methods=['GET'])
def get_agent_stats(simulation_id: str):
    """Per-Agent activity stats (for leaderboards / action distribution)."""
    try:
        stats = SimulationRunner.get_agent_stats(simulation_id)

        return jsonify({
            "success": True,
            "data": {
                "agents_count": len(stats),
                "stats": stats,
            },
        })

    except Exception as e:
        logger.error(f"Get agent stats failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Database query endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@simulation_bp.route('/<simulation_id>/posts', methods=['GET'])
def get_simulation_posts(simulation_id: str):
    """Get posts from the simulation (SQLite DB per platform)."""
    try:
        platform = request.args.get('platform', 'reddit')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}'
        )

        db_file = f"{platform}_simulation.db"
        db_path = os.path.join(sim_dir, db_file)

        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {
                    "platform": platform,
                    "count": 0,
                    "posts": [],
                    "message": "DB not found — simulation may not have run yet",
                },
            })

        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM post ORDER BY created_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            posts = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT COUNT(*) FROM post")
            total = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            posts = []
            total = 0

        conn.close()

        return jsonify({
            "success": True,
            "data": {
                "platform": platform,
                "total": total,
                "count": len(posts),
                "posts": posts,
            },
        })

    except Exception as e:
        logger.error(f"Get posts failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/<simulation_id>/comments', methods=['GET'])
def get_simulation_comments(simulation_id: str):
    """Get comments (Reddit only)."""
    try:
        post_id = request.args.get('post_id')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        sim_dir = os.path.join(
            os.path.dirname(__file__),
            f'../../uploads/simulations/{simulation_id}'
        )

        db_path = os.path.join(sim_dir, "reddit_simulation.db")
        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "data": {"count": 0, "comments": []},
            })

        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            if post_id:
                cursor.execute("""
                    SELECT * FROM comment WHERE post_id = ?
                    ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (post_id, limit, offset))
            else:
                cursor.execute("""
                    SELECT * FROM comment ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (limit, offset))
            comments = [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            comments = []

        conn.close()

        return jsonify({
            "success": True,
            "data": {"count": len(comments), "comments": comments},
        })

    except Exception as e:
        logger.error(f"Get comments failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


# ═══════════════════════════════════════════════════════════════════════════════
# Interview endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@simulation_bp.route('/interview', methods=['POST'])
def interview_agent():
    """Interview a single Agent.

    Requires the simulation environment to be running (waiting-for-commands mode).

    Request JSON:
        {
            "simulation_id": "sim_xxxx",      // required
            "agent_id": 0,                    // required
            "prompt": "What do you think?",   // required — Hinglish OK
            "platform": "twitter",            // optional: twitter|reddit (omit = both)
            "timeout": 60                     // optional, default 60
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        agent_id = data.get('agent_id')
        prompt = data.get('prompt')
        platform = data.get('platform')
        timeout = data.get('timeout', 60)

        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400
        if agent_id is None:
            return jsonify({"success": False, "error": "agent_id is required"}), 400
        if not prompt:
            return jsonify({"success": False, "error": "prompt is required"}), 400

        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": "platform must be 'twitter' or 'reddit'",
            }), 400

        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": "Simulation environment not running. "
                         "Ensure simulation is alive in waiting-for-commands mode.",
            }), 400

        optimized_prompt = optimize_interview_prompt(prompt)

        result = SimulationRunner.interview_agent(
            simulation_id=simulation_id,
            agent_id=agent_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout,
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result,
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": f"Interview response timed out: {str(e)}",
        }), 504

    except Exception as e:
        logger.error(f"Interview failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/interview/batch', methods=['POST'])
def interview_agents_batch():
    """Interview multiple Agents in a batch.

    Request JSON:
        {
            "simulation_id": "sim_xxxx",
            "interviews": [
                {"agent_id": 0, "prompt": "...", "platform": "twitter"},
                {"agent_id": 1, "prompt": "..."}
            ],
            "platform": "reddit",   // default platform if item doesn't specify
            "timeout": 120
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        interviews = data.get('interviews')
        platform = data.get('platform')
        timeout = data.get('timeout', 120)

        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        if not interviews or not isinstance(interviews, list):
            return jsonify({
                "success": False,
                "error": "interviews (list) is required",
            }), 400

        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": "platform must be 'twitter' or 'reddit'",
            }), 400

        for i, interview in enumerate(interviews):
            if 'agent_id' not in interview:
                return jsonify({
                    "success": False,
                    "error": f"interviews[{i}] missing agent_id",
                }), 400
            if 'prompt' not in interview:
                return jsonify({
                    "success": False,
                    "error": f"interviews[{i}] missing prompt",
                }), 400
            item_platform = interview.get('platform')
            if item_platform and item_platform not in ("twitter", "reddit"):
                return jsonify({
                    "success": False,
                    "error": f"interviews[{i}].platform must be 'twitter' or 'reddit'",
                }), 400

        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": "Simulation environment not running.",
            }), 400

        optimized_interviews = []
        for interview in interviews:
            item = interview.copy()
            item['prompt'] = optimize_interview_prompt(interview.get('prompt', ''))
            optimized_interviews.append(item)

        result = SimulationRunner.interview_agents_batch(
            simulation_id=simulation_id,
            interviews=optimized_interviews,
            platform=platform,
            timeout=timeout,
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result,
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": f"Batch interview timed out: {str(e)}",
        }), 504

    except Exception as e:
        logger.error(f"Batch interview failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/interview/all', methods=['POST'])
def interview_all_agents():
    """Ask the same question to every Agent.

    Request JSON:
        {
            "simulation_id": "sim_xxxx",
            "prompt": "What do you think of this campaign?",
            "platform": "reddit",   // optional
            "timeout": 180
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        prompt = data.get('prompt')
        platform = data.get('platform')
        timeout = data.get('timeout', 180)

        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400
        if not prompt:
            return jsonify({"success": False, "error": "prompt is required"}), 400

        if platform and platform not in ("twitter", "reddit"):
            return jsonify({
                "success": False,
                "error": "platform must be 'twitter' or 'reddit'",
            }), 400

        if not SimulationRunner.check_env_alive(simulation_id):
            return jsonify({
                "success": False,
                "error": "Simulation environment not running.",
            }), 400

        optimized_prompt = optimize_interview_prompt(prompt)

        result = SimulationRunner.interview_all_agents(
            simulation_id=simulation_id,
            prompt=optimized_prompt,
            platform=platform,
            timeout=timeout,
        )

        return jsonify({
            "success": result.get("success", False),
            "data": result,
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except TimeoutError as e:
        return jsonify({
            "success": False,
            "error": f"Global interview timed out: {str(e)}",
        }), 504

    except Exception as e:
        logger.error(f"Global interview failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/interview/history', methods=['POST'])
def get_interview_history():
    """Get interview history from the simulation DB.

    Request JSON:
        {
            "simulation_id": "sim_xxxx",
            "platform": "reddit",   // optional — omit for both platforms
            "agent_id": 0,          // optional
            "limit": 100
        }
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        platform = data.get('platform')
        agent_id = data.get('agent_id')
        limit = data.get('limit', 100)

        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        history = SimulationRunner.get_interview_history(
            simulation_id=simulation_id,
            platform=platform,
            agent_id=agent_id,
            limit=limit,
        )

        return jsonify({
            "success": True,
            "data": {
                "count": len(history),
                "history": history,
            },
        })

    except Exception as e:
        logger.error(f"Get interview history failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/env-status', methods=['POST'])
def get_env_status():
    """Check if the simulation environment is alive (can accept Interview commands)."""
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        env_alive = SimulationRunner.check_env_alive(simulation_id)
        env_status = SimulationRunner.get_env_status_detail(simulation_id)

        message = (
            "Environment running — can accept Interview commands"
            if env_alive else
            "Environment not running or closed"
        )

        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "env_alive": env_alive,
                "twitter_available": env_status.get("twitter_available", False),
                "reddit_available": env_status.get("reddit_available", False),
                "message": message,
            },
        })

    except Exception as e:
        logger.error(f"Get env status failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@simulation_bp.route('/close-env', methods=['POST'])
def close_simulation_env():
    """Gracefully close the simulation environment (sends close_env IPC command).

    Unlike /stop (which kills the process), this lets the sim exit cleanly.
    """
    try:
        data = request.get_json() or {}

        simulation_id = data.get('simulation_id')
        timeout = data.get('timeout', 30)

        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id is required"}), 400

        result = SimulationRunner.close_simulation_env(
            simulation_id=simulation_id, timeout=timeout,
        )

        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        if state:
            state.status = SimulationStatus.COMPLETED
            manager._save_simulation_state(state)

        return jsonify({
            "success": result.get("success", False),
            "data": result,
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Close env failed: {str(e)}")
        return jsonify({
            "success": False, "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500