# AXonic | Claude-Optimized Codebase

## Project Overview
AXonic (MiroFish-Lite) is a production-grade marketing strategy simulation engine specialized for the **Indian market**. It uses a hybrid LLM architecture to simulate consumer behavior, viral spread, and regional dynamics across platforms like Instagram, WhatsApp, and LinkedIn.

## Architecture
- **Frontend**: Vue 3 + Vite (Composition API, Tailwind CSS).
- **Backend**: Python 3.11+ Flask API managed by `uv`.
- **Infrastructure**: Supabase (Postgres + pgvector) for memory and state.
- **Intelligence Layer**:
  - **Llama 3.3 70B (Groq)**: High-speed event & simulation round generation.
  - **Gemini 1.5 Flash**: Deep intelligence reporting and regional breakdown.
  - **Camel-OASIS**: Underlying social simulation framework.

## Key Concepts
- **Simulation Pipeline**: `Ontology` -> `Persona` -> `Graph` -> `Events` -> `Report`.
- **Indian Market Context**: Focus on Tier 1/2/3 dynamics, UPI culture, and regional language nuances.
- **Compute Tracking**: Every simulation tracks token usage and provider costs via `compute_tracker.py`.

## Commands
### Backend
- `cd backend && uv run python run.py` (Start dev server on port 5001)
- `cd backend && uv pip install -r requirements.txt` (Install dependencies)

### Frontend
- `cd frontend && npm run dev` (Start Vite server on port 5173)
- `cd frontend && npm install` (Install dependencies)

## Rules
- **DO NOT** hallucinate API endpoints; check `backend/app/api/` for existing routes.
- **ALWAYS** follow the "Service Layer" pattern: Controllers in `api/` call logic in `services/`.
- **PREFER** Groq for high-volume text generation and Gemini for structured analysis.
- **STAY CONSISTENT** with the "AXonic" branding in UI and logs.
- **OPTIMIZE** for sub-10 second simulation runs.

## Coding Standards
- **Modular Components**: Vue components should be small and single-purpose.
- **Type Safety**: Use Pydantic models for backend data validation.
- **Deterministic Logic**: Use LLMs for creativity, but use code for scoring and state management.

## Important Constraints
- **Low API Cost**: Avoid redundant LLM calls; check `llm_router.py` cache/logic first.
- **Privacy**: Never log raw PII; mask sensitive campaign data in debug logs.
