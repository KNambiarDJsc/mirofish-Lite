# AXonic Skill | /optimize-cost

## Description
Analyze the simulation pipeline's LLM usage and suggest or apply optimizations to reduce provider API costs.

## Pre-conditions
- **Environment**: `.env` with `GROQ_API_KEY` and `GEMINI_API_KEY`.
- **Logs**: Access to `compute_tracker.py` history or the `.logs` directory.

## Steps
1. **Usage Audit**: Scan `compute_tracker.py` and the current prompt files.
2. **Provider Switch**: 
   - Identify Gemini calls that can be offloaded to Groq (Llama 3.3 70B).
   - Especially candidate: Simple text generation and entity extraction.
3. **Prompt Compression**:
   - Check if campaign contexts are being sent repeatedly.
   - Refactor `llm_router.py` to use minimal context snippets where possible.
4. **Caching Verification**:
   - Check if similar campaign ontologies are being re-generated for the same user.
   - Ensure `SimulationManager` logic isn't wasting tokens on identical requests.

## Expected Output
- A `recommendation_report.md` in the `artifacts` directory detailing:
  - Estimated cost savings (percentage).
  - Specific code lines or prompts to refactor.
  - Verification test results.
- Code diffs applying the optimizations if directed.
