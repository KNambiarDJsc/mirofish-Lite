"""
AXonic Lite — MVP API
Engine: Llama 3.3 70B (Groq) → events  |  Gemini 2.5 Flash → report
No rule-based fallback. No OASIS. If LLM fails, return a clean error.

POST /api/mvp/simulate  → Llama 3.3 70B generates real campaign events
POST /api/mvp/report    → Gemini 2.5 Flash generates decision report
POST /api/mvp/purchase  → Credit user after Razorpay payment
GET  /api/mvp/balance   → Current CU balance
"""

import os
import uuid
import logging

from flask import Blueprint, request, jsonify

from ..services.llm_router   import generate_events, generate_report
from ..services.compute_tracker import (
    can_afford,
    deduct_and_log,
    add_compute_units,
    get_credits_display,
    get_user_tier,
    get_available_cu,
    CU_RATES,
)

logger = logging.getLogger("axonic.api.mvp")
mvp_bp = Blueprint("mvp", __name__)
GROQ_MODEL_LABEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/mvp/simulate
# Llama 3.3 70B generates authentic campaign simulation events.
# ─────────────────────────────────────────────────────────────────────────────

@mvp_bp.post("/simulate")
def simulate_campaign():
    data     = request.get_json(silent=True) or {}
    user_id  = data.get("user_id")
    campaign = data.get("campaign")

    if not user_id or not campaign:
        return jsonify({
            "success": False,
            "error":   "user_id and campaign are required",
        }), 400

    # Check minimum CU balance for full run (events + report)
    min_required = CU_RATES["event_gen_llama"] + CU_RATES["report_flash"]
    cu_now = get_available_cu(user_id)
    if cu_now < min_required:
        return jsonify({
            "success":         False,
            "error":           "NO_CREDITS",
            "message":         f"You need at least {min_required} CU (0.5 credits) to run a simulation.",
            "cu_available":    cu_now,
            "credits_display": get_credits_display(user_id),
        }), 402

    sim_id = data.get("simulation_id") or str(uuid.uuid4())

    # ── Llama 3.3 70B — real simulation, no fallback ──────────────────────────
    try:
        events, usage = generate_events(campaign)
    except Exception as exc:
        logger.error(f"[Llama] Event generation failed: {exc}")
        return jsonify({
            "success": False,
            "error":   "SIMULATION_FAILED",
            "message": "Llama simulation engine returned an error. Please retry.",
            "detail":  str(exc),
        }), 500

    # Deduct CU for event generation only after success
    deduct = deduct_and_log(
        user_id       = user_id,
        simulation_id = sim_id,
        action        = "event_gen_llama",
        model         = usage.get("model", GROQ_MODEL_LABEL),
        tokens_in     = usage.get("tokens_in", 0),
        tokens_out    = usage.get("tokens_out", 0),
    )

    return jsonify({
        "success":         True,
        "simulation_id":   sim_id,
        "events":          events,
        "engine":          "llama-3.3-70b",
        "tokens_in":       usage.get("tokens_in"),
        "tokens_out":      usage.get("tokens_out"),
        "cu_remaining":    deduct.get("cu_remaining", 0),
        "credits_display": deduct.get("credits_display", 0),
    })


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/mvp/report
# Gemini 2.5 Flash generates the executive decision report.
# ─────────────────────────────────────────────────────────────────────────────

@mvp_bp.post("/report")
def generate_campaign_report():
    data          = request.get_json(silent=True) or {}
    user_id       = data.get("user_id")
    campaign      = data.get("campaign")
    events        = data.get("events", [])
    simulation_id = data.get("simulation_id") or str(uuid.uuid4())

    if not user_id or not campaign:
        return jsonify({
            "success": False,
            "error":   "user_id and campaign are required",
        }), 400

    if not events:
        return jsonify({
            "success": False,
            "error":   "No simulation events provided. Run /simulate first.",
        }), 400

    # Tier determines token budget (free = 1200 tokens, paid = 2500)
    tier   = get_user_tier(user_id)
    action = "report_pro" if tier == "paid" else "report_flash"

    if not can_afford(user_id, action):
        return jsonify({
            "success":         False,
            "error":           "NO_CREDITS",
            "message":         "Not enough credits to generate report. Please top up.",
            "credits_display": get_credits_display(user_id),
        }), 402

    # ── Gemini 2.5 Flash — real report, no fallback ───────────────────────────
    try:
        report, usage = generate_report(campaign, events, tier)
    except Exception as exc:
        logger.error(f"[Gemini] Report generation failed: {exc}")
        return jsonify({
            "success": False,
            "error":   "REPORT_FAILED",
            "message": "Gemini report engine returned an error. Please retry.",
            "detail":  str(exc),
        }), 500

    # Deduct CU after successful report generation
    deduct = deduct_and_log(
        user_id       = user_id,
        simulation_id = simulation_id,
        action        = action,
        model         = usage.get("model"),
        tokens_in     = usage.get("tokens_in", 0),
        tokens_out    = usage.get("tokens_out", 0),
    )

    return jsonify({
        "success":         True,
        "report":          report,
        "tier":            tier,
        "engine":          "gemini-2.5-flash",
        "tokens_in":       usage.get("tokens_in"),
        "tokens_out":      usage.get("tokens_out"),
        "cu_remaining":    deduct.get("cu_remaining", 0),
        "credits_display": deduct.get("credits_display", 0),
    })


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/mvp/purchase  — credit user after Razorpay payment
# ─────────────────────────────────────────────────────────────────────────────

@mvp_bp.post("/purchase")
def purchase_credits():
    data       = request.get_json(silent=True) or {}
    user_id    = data.get("user_id")
    pack       = data.get("pack")        # 'starter' | 'growth'
    payment_id = data.get("payment_id")  # Razorpay payment_id

    if not user_id or not pack or not payment_id:
        return jsonify({
            "success": False,
            "error":   "user_id, pack, and payment_id are all required",
        }), 400

    result = add_compute_units(user_id, pack, payment_id)

    if not result.get("success"):
        return jsonify(result), 500

    return jsonify({
        "success":  True,
        "pack":     pack,
        "cu_added": result["cu_added"],
        "credits":  result["credits"],
        "cu_total": result["cu_total"],
        "message":  f"Added {result['cu_added']} CU → {result['credits']} credits total.",
    })


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/mvp/balance  — credit balance for the user
# ─────────────────────────────────────────────────────────────────────────────

@mvp_bp.get("/balance")
def get_balance():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id is required"}), 400

    cu   = get_available_cu(user_id)
    tier = get_user_tier(user_id)

    return jsonify({
        "success":         True,
        "compute_units":   cu,
        "credits_display": round(cu / 100, 1),
        "tier":            tier,
        "cu_rates": {
            "simulate": CU_RATES["event_gen_llama"],
            "report":   CU_RATES["report_flash"],
            "per_run":  CU_RATES["event_gen_llama"] + CU_RATES["report_flash"],
        },
    })

