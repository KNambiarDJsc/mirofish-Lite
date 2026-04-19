# AXonic Skill | /simulate

## Description
Execute the full AXonic simulation pipeline from Campaign Definition through Event Generation.

## Pre-conditions
- **Environment**: `.env` configured with `GROQ_API_KEY` and `GEMINI_API_KEY`.
- **Backend Service**: Must be running on port 5001 or reachable via logic.

## Steps
1. **Campaign Validation**: Check `campaign_data` for required fields (`name`, `platform`, `audience`, `goal`).
2. **Ontology Generation**: Process the strategy docs (if any) using `ontology_generator.py`.
3. **Graph Construction**: Pass the ontology to `graph_builder.py` to map the simulation entities.
4. **Persona Creation**: Call `oasis_profile_generator.py` (Llama/OASIS) to build the simulation players.
5. **Event Generation**: Run `simulation_runner.py` through `llm_router.py` (Llama 3.3 70B via Groq) to simulate 3 rounds of action.

## Expected Output
- A `simulation_id`.
- A list of JSON objects representing 3 rounds of campaign events:
  ```json
  [
    {"round": 1, "event": "...", "metric": "...", "sentiment": "..."},
    {"round": 2, "event": "...", "metric": "...", "sentiment": "..."},
    {"round": 3, "event": "...", "metric": "...", "sentiment": "..."}
  ]
  ```
- Incremented usage stats in `compute_tracker.py`.
