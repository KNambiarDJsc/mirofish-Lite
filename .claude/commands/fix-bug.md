# AXonic Command | /fix-bug <description>

## Description
Execute a structured debugging and fix process for a specific issue in AXonic.

## Reasoning Process
1. **Traceback Analysis**: 
   - Scan `.logs/` or terminal output for errors.
   - Look for `ModuleNotFoundError`, `ObjectNotFound`, or `AttributeError`.
2. **Context Scanning**:
   - Check `backend/app/api/` for endpoint mismatch.
   - Check `backend/app/services/` for logic failures (e.g., `llm_router.py` API failures).
   - Check `frontend/` for console errors or API fetch failures.
3. **Hypothesis Generation**:
   - Is it the environment (activation/`.env`)?
   - Is it the code (blueprint/import)?
4. **Fix Implementation**:
   - Use `replace_file_content` or `multi_replace_file_content` for non-contiguous fixes.
5. **Verification**:
   - Run `python run.py` (backend) or check Vite (frontend).
   - Verify the trace is gone.

## Standard Fixes (Common AXonic issues)
- **Venv Activation**: If `PS` fails, use `.\.venv\Scripts\Activate.ps1`.
- **Import Errors**: Check if `sys.path.insert` is correctly configured in `run.py`.
- **API Key Hidden**: Ensure `.env` is NOT missing the `GROQ_API_KEY` or `GEMINI_API_KEY`.
