# AXonic Skill | /generate-report

## Description
Generate the intelligence report for a completed simulation run using the Gemini 1.5 Flash analysis model.

## Pre-conditions
- **Environment**: `.env` configured with `GEMINI_API_KEY`.
- **Simulation**: Must have existing simulation events and campaign metadata.

## Steps
1. **Event Aggregation**: Fetch the simulation results from the `SimulationManager`.
2. **Context Enrichment**: Map regional consumer behavior patterns to the results using `report_agent.py`.
3. **Intelligence Generation**: Call `generate_report` in `llm_router.py` (Gemini 1.5 Flash).
   - If user type is `paid`, use the deeper prompt with `regional_breakdown` and `budget_estimate`.
   - If user type is `free`, use the standard analysis prompt.
4. **Validation**: Ensure the verdict (`Strong` / `Risky` / `Weak`) is consistent with simulation metrics.

## Expected Output
- A structured JSON report containing:
  - `verdict` and `verdict_reason`.
  - `confidence_score` (0–100).
  - List of `risks`, `opportunities`, and `recommendations`.
  - `indian_market_insight`.
  - Usage stats for Gemini-specific tokens.
