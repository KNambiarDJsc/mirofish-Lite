# Vue 3 Frontend Rules | AXonic

## Core Architecture
- **Framework**: Vue 3 (Composition API).
- **Tooling**: Vite (high-speed HMR).
- **Styling**: Tailwind CSS + Vanilla CSS (for custom glassmorphism and AXonic branding).

## Coding Standards
1. **Component Design**: 
   - Favor `<script setup>` for brevity.
   - Separate UI components into `src/components/` and business pages into `src/views/`.
   - Prop validation is MUST.
2. **State Management**:
   - Use Pinia (if available) for global state like `UserAuth` or `SimulationState`.
   - Keep local state within components using `ref`/`reactive` until global state is strictly needed.
3. **Animations**:
   - AXonic UI must feel **ALIVE**. Use GSAP or CSS transitions for all view switches.
   - Use the "Hint Chip" pattern: Small breadcrumb-like UI elements for simulation hints.
4. **Data Fetching**:
   - Use Axios with a global instance configured for `base_url`.
   - Implement common loading/error states for all async actions.

## Prohibited
- `ref` manipulation from parent (use `defineExpose` only if critical).
- Direct DOM manipulation via `document.querySelector`.
- Embedding heavy business logic (AI prompt building) in `.vue` files; move to a separate utility.
