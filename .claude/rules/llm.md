# AI Hybrid Architecture Rules | AXonic

## Core Routing (llm_router.py)
- **Groq (Llama 3.3 70B)**:
  - **Purpose**: Low-latency, fast simulation events and creative generation.
  - **Constraints**: Keep prompts under 4k tokens for optimal speed.
- **Gemini 2.0 Flash**:
  - **Purpose**: Intelligence reports, regional market analysis, and multi-modal tasks.
  - **Constraints**: Use for high-reasoning tasks where cost is balanced by intelligence.

## Cost Efficiency & Optimization
1. **Prefer Groq Over Gemini** for repetitive, templated tasks.
2. **Batching**: Group entity extraction tasks instead of multiple calls.
3. **Prompt Compression**: Avoid repeating the full context in every call; use the `simulation_ipc.py` state management.
4. **Token Tracking**: All calls MUST increment the `compute_tracker.py` for cost analytics.
5. **Deterministic Fallbacks**: Implement `_fallback_events` or `_fallback_report` logic for all core LLM functions.

## Intelligence Principles (Indian Market)
- **Contextual Awareness**: All prompts MUST include Indian market framing (Tier 1/2/3, localized language, UPI).
- **Nuanced Tone**: Use "Inspirational", "Humorous", or "Emotional" tones to simulate local virality.
- **Verification**: Cross-reference AI claims with fixed knowledge (ASCI rules, SEBI guidelines).

## Prohibited
- Hard-coding prompt strings in `.py` files where possible (move complex prompts to `.txt` or service constants).
- Sending redundant campaign metadata if it hasn't changed.
- Recursive LLM calls without a depth limit (max depth: 3).
