# Flask/Python Backend Rules | AXonic

## Core Architecture
- **Framework**: Flask 3.0 (API Mode).
- **Package Manager**: `uv` (use `uv run python` exclusively).
- **Structure**: Blueprints in `app/api/`, business logic in `app/services/`.

## Coding Standards
1. **Service Layer Separation**:
   - `api` handlers: Validate input (`Pydantic`), call service, return JSON.
   - `services`: Heavy lifting, LLM routing, database calls.
   - `utils`: Generic tools (loggers, config, formatting).
2. **Error Handling**:
   - Global error handler for `404`, `500`, and `422` (Unprocessable Entity).
   - Use `abort(400, message="...")` for client errors.
3. **Database Rules (Supabase)**:
   - Use `supabase-python` client.
   - Vector operations occur in `supabase_memory.py`.
   - Table naming follow snake_case (e.g. `sim_metrics`, `user_credits`).
4. **Environment Variables**:
   - MUST be in `Config (app/config.py)` before usage.
   - Use `.env` with strict `python-dotenv` loading.

## Performance
- **Simulation Concurrency**: Process long-running sims in background `multiprocessing` (see `simulation_runner.py`).
- **Response Format**: AXonic expects `{"status": "success", "data": {...}, "message": "..."}` for all API responses.

## Prohibited
- Manual SQL construction (use Supabase client or safe parameterization).
- Hardcoding LLM API keys.
- Direct `print()` statements (use `logger.info`, `logger.error`).
