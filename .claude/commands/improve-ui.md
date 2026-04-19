# AXonic Command | /improve-ui <feature>

## Description
Enhance or rebuild a UI component or view in the AXonic frontend while maintaining design standards.

## Reasoning Process
1. **Design System Alignment**: 
   - Check `frontend/index.css` or Tailwind config.
   - Look for the AXonic "Glassmorphism" or "Neon Indian Market" theme.
2. **Component Audit**:
   - Determine if the feature fits in `src/components/` (reusable) or `src/views/` (page specific).
   - Check if the logic is in `src/utils/` or inside the Vue file.
3. **UX Optimization**:
   - Every state change should have an animation/transition.
   - Add loading/empty states for all AI actions (`Simulation`, `Reporting`).
4. **Consistency check**:
   - Use the "Hint Chip" pattern for small data points.
   - Use a clear hierarchy with `<h1>` and a single purpose per page.
5. **Implementation**:
   - Use `write_to_file` for new components.
   - Use `replace_file_content` for view updates.

## UI Examples
- **Simulation Progress**: Use a linear stepper with active animations for each round.
- **Intelligence Report**: Use a cards-based layout for `Risks`, `Opportunities`, and `Verdict`.
- **Campaign Dashboard**: Use a clean, data-intensive table with sparklines for `Engagement` and `Reach`.
