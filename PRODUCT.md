# Product

## Register
**product** — Clutch is a desktop developer tool. Design serves the task (chat, workflows, supervision), not marketing spectacle.

## Users & Purpose
- **Who:** Independent developers, technical operators, and builders of local AI workflows / SOP automation.
- **Context:** Long coding/ops sessions on a local machine; supervising agents, not watching a black box.
- **Primary job on Chat:** Type intent → send to the right agent → see progress and intervene when needed.
- **Outcome:** Reliable multi-agent orchestration with transparent supervision and human gates — without cloud tenancy.

## Brand Personality
Precise · restrained · IDE-grade (supervision console, not SaaS landing page).

## References
- **Cursor composer:** one input shell; mode/model as compact in-box controls; secondary actions progressive (menus), not stacked chrome above the field.
- **Existing Clutch docs:** `docs/UI_UX_GUIDELINES.md`, `docs/PRODUCT_INTRO.md` (light theme, Hanken Grotesk, developer-console vibe).

## Anti-references
- Stacking every capability as a full-width bar above the chat input.
- Purple-on-white / cream-serif marketing aesthetics; glassmorphism for its own sake.
- Dashboard clutter (stat strips, pill clusters) in the composer.

## Accessibility
- WCAG AA contrast for body/placeholder text on light surfaces.
- Keyboard: Enter to send, Shift+Enter newline; menus dismissible; icon buttons need accessible names.
- Honor `prefers-reduced-motion`.

## Strategic Design Principles
1. **One primary surface:** the composer is a single unit; visible chrome is only **+ · mode · send**.
2. **Progressive disclosure:** advanced tools (worktree, schedule, sessions, MCP, rewind, usage) live exclusively in the **+** menu; status chips only when active.
3. **State earns chrome:** banners/chips only when running, failed, queued, or worktree-active — never as permanent ads.
4. **Familiar tool patterns:** match Cursor/IDE composer grammar over inventing new control layouts.
