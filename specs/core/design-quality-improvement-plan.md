# Implementation Plan — UI Quality Improvement & History Switching in Design Mode

This plan outlines the architectural transformations required to align Clutch's Design Mode with premium tools like Stitch and Figma Make. It explicitly shifts the focus toward output quality as the primary user pain point, while maintaining traceability and version switcher features.

> **Reviewer Core Guidance**: 
> *"The current implementation plan spends most of its effort improving traceability (history, reasoning, versioning), but the primary user pain point is output quality. The plan should explicitly prioritize improving generation quality through better design specification generation, layout constraints, curated examples, and an optional review/refinement pass."*

## Priorities (优先级划分)

* **P0 (Highest Leverage)**: UI Quality Improvement (Design Spec Generator, Layout Pattern Library, Premium Few-shot Library, and Design Review Pass).
* **P1 (Traceability)**: Reasoning Capture, Versioned HTML, Round History, and Version Switching.
* **P2 (Deferred Roadmap)**: Update Design.md (User-triggered), Screenshot History.

---

## UI Quality Improvement (P0)

Improving output quality is the highest priority for Design Mode. Rather than relying solely on ad-hoc prompt engineering, the generation pipeline will be strengthened in four stages:

### 1. Upgrade Design.md Generator
The generated `DESIGN.md` should become a complete design specification rather than a simple color/font summary. The generated spec will include the following structured sections:
* `# Brand`
* `# Visual Style`
* `# Layout System`
* `# Grid`
* `# Typography`
* `# Color Tokens`
* `# Radius`
* `# Shadow`
* `# Components`
* `# Motion`
* `# Responsive Rules`
* `# Accessibility Rules`

This ensures that every generated screen strictly complies with an expert design system, rather than guessing styles.

### 2. Layout Pattern Library
Before generating HTML, the pipeline will classify the user request into a predefined layout pattern:
* `Landing Page`
* `Dashboard`
* `CRM`
* `Settings`
* `Analytics`
* `E-commerce`
* `Chat`
* `Mobile App`

The HTML Generator will render code within a proven layout wrapper rather than designing the page structure from scratch.

### 3. Premium Few-shot Library
Instead of relying only on textual prompt rules, the prompt builder will dynamically inject high-quality reference examples based on the identified page layout type. Curated examples include:
* `Login`
* `Dashboard`
* `Pricing`
* `Profile`
* `Analytics`
* `Tables`

### 4. Design Review Pass
Introduce a self-correction pass before outputting the final HTML:
```
Generate HTML ──> Design Review ──> Improve HTML ──> Return Result
```
The Design Reviewer evaluates:
* Visual hierarchy & Modern aesthetics
* Spacing & Typography consistency
* Color consistency & Contrast
* CTA & Accessibility compliance
* Responsive layout

If the quality score is below the expected threshold, the model performs one automated refinement pass.

---

## User Review Required

> [!IMPORTANT]
> **Expert Design Knowledge Injection**: Instead of stacking simple prompt guidelines (Rule 7, 8, etc.), we will build an aggregate knowledge system in the prompt templates (incorporating Layout Rules, Typography rules, spacing systems, and transitions).
> 
> **Reasoning Capture**: Capture and display `reasoning_content` from free models (`big-pickle`, etc.) to show step-by-step thinking in the UI logs.
> 
> **Versioned Screen Storage**: Persist screens as `screens/main_r{round_index}.html` instead of overwriting, enabling history version switching.

---

## Proposed Changes

### Backend (Orchestrator Sidecar)

#### [MODIFY] [http_complete.py](file:///Users/fancy/clutch/services/orchestrator/src/llm/http_complete.py)
* Update `_openai_chat` and `_post_json` to return a dictionary including both `content` and `reasoning_content`.
* Propagate this in `http_chat_complete` to the router.

#### [MODIFY] [router.py](file:///Users/fancy/clutch/services/orchestrator/src/llm/router.py)
* Update `LLMProviderRouter.chat` and `LLMProviderRouter.complete` to support returning `(content, reasoning_content)` objects.

#### [MODIFY] [service.py](file:///Users/fancy/clutch/services/orchestrator/src/design/service.py)
* Implement Design Spec Generator structure matching the 12 headings.
* Add Layout Pattern Selector before HTML generation.
* Update prompt templates with Premium Few-shot selection.
* Implement the Design Review Pass self-correction loop.
* Save generated HTML screens as versioned paths (e.g. `screens/{screen_id}_r{round_index}.html`).
* **HTML-to-React Converter**: Refactor `generate_react` and `_react_scaffold` to replace the current placeholder skeleton stubs with a real LLM translation chain that converts the high-fidelity HTML screens into fully functional React components (Tailwind classes, converted tags, and assets).
* **Multi-Screen Interactive Linking**: Wire up navigation `href` links between the generated screens and inject React state hooks (e.g. `useState(isOpen)`) to control toggleable components like modals or dropdowns.


---

### Frontend (Desktop UI)

#### [MODIFY] [designApi.ts](file:///Users/fancy/clutch/apps/desktop/src/services/designApi.ts)
* Update `DesignProcessEntry` and `DesignSession` to support `reasoning_content` and versioned screens.

#### [MODIFY] [DesignWorkspace.tsx](file:///Users/fancy/clutch/apps/desktop/src/components/design/DesignWorkspace.tsx)
* Introduce `selectedRoundIndex` state variable.
* Render a historical round selector widget at the bottom.
* Render thinking logs and preview files corresponding to the selected round index.

---

## Verification Plan

### Automated Tests
* Run `uv run pytest tests/test_design_service.py` to verify that session manifests generate and iterate correctly with versioned file paths and spec generation.

---

## Future Roadmap (后续规划 — P2/P3 储备任务)

### 1. Update Design.md V2 (用户主动更新规范)
* **Description**: Add an "Update Design.md" button. When clicked, the Agent reads the current active HTML, extracts design rules, and regenerates a new `DESIGN.md` V2 document.

### 2. Screenshot History Persistence (版本快照截图)
* **Description**: For each iteration round, save a visual snapshot (`screens/main_r{round_index}.png`) along with the prompt and HTML to allow visual preview switches.
