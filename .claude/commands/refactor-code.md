# AXonic Command | /refactor-code <target>

## Description
Perform non-breaking code restructuring for architectural clarity, performance, or maintenance.

## Reasoning Process
1. **Dependency Analysis**: 
   - Check `backend` for circular imports.
   - Check `pyproject.toml` or `package.json` for unused packages.
2. **Component Splitting**:
   - Targets: `report_agent.py` (92KB) or `simulation_runner.py` (76KB).
   - Move logic into sub-services (e.g. `report_agent_paid.py`, `analysis_logic.py`).
3. **Logic Consolidation**:
   - Look for duplicate logic in `SimulationManager` and `SimulationRunner`.
   - Especially candidate: LLM prompt building or JSON cleaning.
4. **Performance Check**:
   - Replace complex list comprehensions with readable generator expressions if data is large.
   - Optimize API fetch loops with `Promise.all` (Frontend) or concurrent tasks (Backend).
5. **Implementation**:
   - Use `multi_replace_file_content` for global naming or path changes.
   - Use `write_to_file` for splitting files.

## Guidelines
- **Zero Regressions**: Ensure tests pass in `backend` and `frontend`.
- **Naming Hygiene**: All private functions in `services/` must start with `_`.
- **Docstrings**: All public functions MUST have docstrings after refactoring.
