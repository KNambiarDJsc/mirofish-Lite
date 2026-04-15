"""
AXonic — Compute Tracker
Maps real LLM token usage → Compute Units (CU) → Credits.
1 Credit = 100 CU.

Free users start with 300 CU (3 credits).
Every action costs a fixed CU rate reflecting real API cost.
"""

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger("axonic.compute_tracker")

# ── CU rates per action ───────────────────────────────────────────────────────
# These represent normalised cost units, NOT actual token counts.
CU_RATES: dict[str, int] = {
    "event_gen_llama":  15,   # Llama 3.3 70B via Groq (~2k tokens)
    "report_flash":     35,   # Gemini 2.5 Flash report (~5k tokens)
    "report_pro":       80,   # Gemini 2.5 Flash paid (deeper, more tokens)
    "rerun_simulation": 25,   # Partial re-compute
    "export_pdf":        5,   # Lightweight
    "agent_chat":       20,   # Per interaction turn
}

# Your estimated USD cost per action (for internal margin tracking only)
USD_COST: dict[str, float] = {
    "event_gen_llama":  0.0002,
    "report_flash":     0.0008,
    "report_pro":       0.0015,
    "rerun_simulation": 0.0004,
    "export_pdf":       0.0000,
    "agent_chat":       0.0010,
}

FREE_SIGNUP_CU = 300  # 3 credits on signup


# ── Supabase client ───────────────────────────────────────────────────────────
_supabase: Client | None = None


def _db() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY missing in .env")
        _supabase = create_client(url, key)
    return _supabase


# ── Public helpers ────────────────────────────────────────────────────────────

def get_available_cu(user_id: str) -> int:
    """Return how many Compute Units the user currently has."""
    try:
        res = _db().table("users").select("compute_units").eq("id", user_id).single().execute()
        return res.data.get("compute_units", 0) if res.data else 0
    except Exception as exc:
        logger.error(f"get_available_cu failed for {user_id}: {exc}")
        return 0


def get_credits_display(user_id: str) -> float:
    """Return the human-readable credit balance (CU / 100)."""
    return round(get_available_cu(user_id) / 100, 1)


def can_afford(user_id: str, action: str) -> bool:
    """Check if the user has enough CU for the given action."""
    cost = CU_RATES.get(action, 0)
    return get_available_cu(user_id) >= cost


def get_user_tier(user_id: str) -> str:
    """Return 'free' or 'paid'."""
    try:
        res = _db().table("users").select("plan").eq("id", user_id).single().execute()
        return res.data.get("plan", "free") if res.data else "free"
    except Exception as exc:
        logger.error(f"get_user_tier failed for {user_id}: {exc}")
        return "free"


def deduct_and_log(
    user_id:       str,
    simulation_id: str,
    action:        str,
    model:         str,
    tokens_in:     int = 0,
    tokens_out:    int = 0,
) -> dict:
    """
    Deduct CU for the action and write to usage_log.
    Returns a result dict with success flag and remaining balance.
    """
    cu_cost  = CU_RATES.get(action, 0)
    usd_cost = USD_COST.get(action, 0.0)
    current  = get_available_cu(user_id)

    if current < cu_cost:
        logger.warning(f"Insufficient CU for {user_id}: has {current}, needs {cu_cost}")
        return {
            "success":          False,
            "reason":           "INSUFFICIENT_CU",
            "cu_available":     current,
            "cu_required":      cu_cost,
            "credits_display":  round(current / 100, 1),
        }

    new_balance = current - cu_cost

    try:
        _db().table("users").update({"compute_units": new_balance}).eq("id", user_id).execute()
        _db().table("usage_log").insert({
            "user_id":       user_id,
            "simulation_id": simulation_id,
            "action":        action,
            "model_used":    model,
            "tokens_in":     tokens_in,
            "tokens_out":    tokens_out,
            "compute_units": cu_cost,
            "cost_usd":      usd_cost,
        }).execute()
    except Exception as exc:
        logger.error(f"deduct_and_log DB write failed for {user_id}: {exc}")
        return {"success": False, "reason": "DB_ERROR", "detail": str(exc)}

    logger.info(
        f"[CU] {user_id} — action={action} cost={cu_cost}CU "
        f"remaining={new_balance}CU ({round(new_balance / 100, 1)} credits)"
    )

    return {
        "success":         True,
        "cu_deducted":     cu_cost,
        "cu_remaining":    new_balance,
        "credits_display": round(new_balance / 100, 1),
    }


def add_compute_units(user_id: str, pack: str, payment_id: str) -> dict:
    """
    Credit a user's account after a successful Razorpay payment.
    Pack options: 'starter' (500 CU / ₹1,500) | 'growth' (1000 CU / ₹5,000)
    """
    PACKS = {
        "starter": {"cu": 500,  "price_inr": 1500},
        "growth":  {"cu": 1000, "price_inr": 5000},
    }

    pack_info = PACKS.get(pack)
    if not pack_info:
        return {"success": False, "reason": f"Unknown pack: {pack}"}

    current    = get_available_cu(user_id)
    new_total  = current + pack_info["cu"]

    try:
        _db().table("users").update({
            "compute_units": new_total,
            "plan":          "paid",
        }).eq("id", user_id).execute()

        _db().table("credit_purchases").insert({
            "user_id":      user_id,
            "pack":         pack,
            "compute_units": pack_info["cu"],
            "price_inr":    pack_info["price_inr"],
            "payment_id":   payment_id,
        }).execute()
    except Exception as exc:
        logger.error(f"add_compute_units DB write failed for {user_id}: {exc}")
        return {"success": False, "reason": "DB_ERROR", "detail": str(exc)}

    logger.info(f"[CU] Added {pack_info['cu']} CU to {user_id} (pack={pack})")

    return {
        "success":    True,
        "cu_added":   pack_info["cu"],
        "cu_total":   new_total,
        "credits":    round(new_total / 100, 1),
    }


def create_user_with_free_credits(user_id: str, email: str, name: str = "") -> dict:
    """
    Register a new user with the free 3-credit (300 CU) signup bonus.
    Call this after email verification.
    """
    try:
        _db().table("users").insert({
            "id":            user_id,
            "email":         email,
            "name":          name,
            "compute_units": FREE_SIGNUP_CU,
            "plan":          "free",
        }).execute()

        _db().table("usage_log").insert({
            "user_id":       user_id,
            "action":        "signup_bonus",
            "model_used":    "system",
            "compute_units": -FREE_SIGNUP_CU,   # negative = granted, not spent
            "cost_usd":      0.0,
        }).execute()
    except Exception as exc:
        logger.error(f"create_user_with_free_credits failed for {user_id}: {exc}")
        return {"success": False, "reason": str(exc)}

    return {
        "success":        True,
        "compute_units":  FREE_SIGNUP_CU,
        "credits_display": round(FREE_SIGNUP_CU / 100, 1),
    }
