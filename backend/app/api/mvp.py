"""
AXonic — MVP API Blueprint
Two core endpoints + one purchase endpoint.

POST /api/mvp/simulate  → Generate events (Llama) or fallback (rule-based)
POST /api/mvp/report    → Generate intelligence report (Gemini 2.5 Flash)
POST /api/mvp/purchase  → Credit user account after Razorpay payment
GET  /api/mvp/balance   → Return current CU balance for a user
"""

import uuid
import logging

from flask import Blueprint, request, jsonify

from ..services.llm_router        import generate_events, generate_report
from ..services.campaign_simulator import simulate as rule_simulate
from ..services.compute_tracker   import (
    can_afford,
    deduct_and_log,
    add_compute_units,
    get_credits_display,
    get_user_tier,
    get_available_cu,
    CU_RATES,
)

logger   = logging.getLogger("axonic.api.mvp")
mvp_bp   = Blueprint("mvp", __name__)

# ── /simulate ─────────────────────────────────────────────────────────────────

@mvp_bp.post("/simulate")
def simulate_campaign():
    """
    Generate simulation events for a campaign.
    Tries Llama 3.3 70B first; falls back to rule-based simulator on failure.
    Does NOT deduct credits — credit is only deducted on /report.
    """
    data     = request.get_json(silent=True) or {}
    user_id  = data.get("user_id")
    campaign = data.get("campaign")

    if not user_id or not campaign:
        return jsonify({"success": False, "error": "user_id and campaign are required"}), 400

    # Check user has enough CU for the upcoming full flow (events + report)
    min_required = CU_RATES["event_gen_llama"] + CU_RATES["report_flash"]
    if get_available_cu(user_id) < min_required:
        return jsonify({
            "success":         False,
            "error":           "NO_CREDITS",
            "message":         "You need at least 0.5 credits to run a simulation.",
            "credits_display": get_credits_display(user_id),
        }), 402

    # Generate events
    try:
        events, usage = generate_events(campaign)
        source = "llm"
    except Exception as exc:
        logger.warning(f"[LLM] Event generation failed ({exc}), using rule-based fallback.")
        events = rule_simulate(campaign)
        usage  = {"model": "rule-based", "provider": "local", "tokens_in": 0, "tokens_out": 0}
        source = "rules"

    # Deduct CU for event generation
    deduct_result = deduct_and_log(
        user_id       = user_id,
        simulation_id = data.get("simulation_id", str(uuid.uuid4())),
        action        = "event_gen_llama",
        model         = usage.get("model", "rule-based"),
        tokens_in     = usage.get("tokens_in", 0),
        tokens_out    = usage.get("tokens_out", 0),
    )

    return jsonify({
        "success":         True,
        "events":          events,
        "source":          source,
        "cu_remaining":    deduct_result.get("cu_remaining", 0),
        "credits_display": deduct_result.get("credits_display", 0),
    })


# ── /report ───────────────────────────────────────────────────────────────────

@mvp_bp.post("/report")
def generate_campaign_report():
    """
    Generate the AXonic intelligence report from events.
    Deducts CU based on user tier (free → flash, paid → pro pricing).
    """
    data          = request.get_json(silent=True) or {}
    user_id       = data.get("user_id")
    campaign      = data.get("campaign")
    events        = data.get("events", [])
    simulation_id = data.get("simulation_id", str(uuid.uuid4()))

    if not user_id or not campaign:
        return jsonify({"success": False, "error": "user_id and campaign are required"}), 400

    # Determine action based on tier
    tier   = get_user_tier(user_id)
    action = "report_pro" if tier == "paid" else "report_flash"

    if not can_afford(user_id, action):
        return jsonify({
            "success":         False,
            "error":           "NO_CREDITS",
            "message":         "Not enough credits to generate report. Please top up.",
            "credits_display": get_credits_display(user_id),
        }), 402

    # Generate report
    try:
        report, usage = generate_report(campaign, events, tier)
    except Exception as exc:
        logger.error(f"[Gemini] Report generation failed: {exc}")
        return jsonify({"success": False, "error": "REPORT_FAILED", "detail": str(exc)}), 500

    # Deduct CU
    deduct_result = deduct_and_log(
        user_id       = user_id,
        simulation_id = simulation_id,
        action        = action,
        model         = usage.get("model", "gemini"),
        tokens_in     = usage.get("tokens_in", 0),
        tokens_out    = usage.get("tokens_out", 0),
    )

    return jsonify({
        "success":         True,
        "report":          report,
        "tier_used":       tier,
        "model_used":      usage.get("model"),
        "cu_remaining":    deduct_result.get("cu_remaining", 0),
        "credits_display": deduct_result.get("credits_display", 0),
    })


# ── /purchase ─────────────────────────────────────────────────────────────────

@mvp_bp.post("/purchase")
def purchase_credits():
    """
    Called by frontend after a successful Razorpay payment.
    Adds CU to user account based on pack.
    """
    data       = request.get_json(silent=True) or {}
    user_id    = data.get("user_id")
    pack       = data.get("pack")        # 'starter' | 'growth'
    payment_id = data.get("payment_id")  # Razorpay payment ID

    if not user_id or not pack or not payment_id:
        return jsonify({"success": False, "error": "user_id, pack, payment_id required"}), 400

    result = add_compute_units(user_id, pack, payment_id)

    if not result.get("success"):
        return jsonify(result), 500

    return jsonify({
        "success":  True,
        "pack":     pack,
        "credits":  result["credits"],
        "cu_total": result["cu_total"],
        "message":  f"Successfully added {result['cu_added']} CU ({result['credits']} credits).",
    })


# ── /balance ──────────────────────────────────────────────────────────────────

@mvp_bp.get("/balance")
def get_balance():
    """Return current CU balance and credit display for a user."""
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"success": False, "error": "user_id is required"}), 400

    cu      = get_available_cu(user_id)
    tier    = get_user_tier(user_id)

    return jsonify({
        "success":         True,
        "compute_units":   cu,
        "credits_display": round(cu / 100, 1),
        "tier":            tier,
    })
