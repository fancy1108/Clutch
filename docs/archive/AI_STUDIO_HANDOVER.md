# Archive Notice

This file is archived and read-only.

Do not append new records here.

For current project state, see:

- memory/PROGRESS.md
- memory/DELIVERABLES.md
- memory/ROADMAP.md

Archived on: 2026-06-29
Reason: prototype handover — superseded by FILEMAP and ARCHITECTURE

---

# Frontend Architecture Handover Document

This document serves as an architectural handover from the prototyping phase to the local development environment. It is intended for the local AI coding agent (e.g., Cursor, Claude Code) to seamlessly integrate the current React frontend within a Tauri + Python ecosystem.

## 1. Component Tree Map

The UI is divided into three primary horizontal sections orchestrated by the main layout container (`App.tsx`):

```text
src/
├── App.tsx (Main Layout & Global State Container)
│
├── components/
│   ├── LanguageContext.tsx (I18n Provider)
│   ├── SystemPreferencesModal.tsx (Unified Preferences & Config Modal)
│   │
│   ├── Sidebar.tsx (Left Navigation & Environment Info)
│   ├── SidebarFlows.tsx (Left Sub-navigation for Workspace Flows)
│   │
│   ├── ChatFeed.tsx (Center Chat View & Interaction Orchestration)
│   │
│   ├── RightPanel.tsx (Right Context Panel Wrapper)
│   │   ├── TerminalPanel.tsx (Action Logs & Interactive Terminal)
│   │   └── (Additional Context Panels: Changes, Properties, etc.)
│   │
│   ├── AgentManager.tsx (Agent Config & Overrides)
│   ├── WorkflowOrchestration.tsx (Multi-Agent Connectors)
│   ├── AiToolsManager.tsx (Functions & MCP integrations)
│   ├── McpServerHub.tsx (MCP External Process Hub)
│   ├── ModelsManager.tsx (LLM Backend Config)
│   ├── SkillsRegistry.tsx (Prompt & Skill Injection)
│   └── ThemeManager.tsx (Global Appearance Control)
│
├── mockData.ts (Decoupled Hardcoded State & Payloads)
├── types.ts (Centralized TypeScript Interfaces)
└── services/
    └── api.ts (Abstracted Async Operation Handlers)
```

**Key Regions:**
- **Left Sidebar:** Handled by `Sidebar` and `SidebarFlows`. Responsible for navigation and workspace/branch selection.
- **Center Canvas:** Typically `ChatFeed`. Displays the interactive Agent messages, code snippets, and execution deliverables.
- **Right Context:** Handled by `RightPanel` and `TerminalPanel`. Shows current uncommitted file states, properties, and streaming terminal daemon logs.
- **Floating Modals:** Features like `SystemPreferencesModal` and specific managers (`AgentManager`, `WorkflowOrchestration`) render above the main interface when triggered.

## 2. State Management

The application currently utilizes a **Lifting State Up** pattern, centralizing cross-cutting concerns primarily in `App.tsx`:
- **Prop Drilling:** Most critical domain states such as `chatMessages`, `terminalLogs`, `runStatus`, `uncommittedFiles`, and `currentView` are held in `App.tsx` and passed down manually to `Sidebar`, `ChatFeed`, and `RightPanel` explicitly via Props.
- **React Context:** Used exclusively for cross-cutting global utilities like internationalization (`LanguageContext.tsx`).
- **Local State:** Component-specific toggle states (e.g., expanded folders in `RightPanel`, input values in `ChatFeed`) are encapsulated within their respective component (`useState`).

*Note for Refactoring:* If prop drilling becomes unwieldy during local development, consider introducing Zustand or React Context for the global workflow execution state.

## 3. Integration Points

Data manipulation has been abstracted into asynchronous handlers inside `src/services/api.ts`. All actual API requests OR real-time WebSocket bindings should occur within this file to replace the mocked behavior.

**Mocked Functions to Replace:**
- `submitChatMessage(text, flow, runStatus)`: Sends user instruction. Should be replaced with a REST/HTTP POST or WebSocket emission.
- `loadFlowState(flowId)`: Retrieves initial context when switching workspace branches.
- `approveNode()` / `rejectNode()`: Human-in-the-loop manual overrides.
- `retryNodeWithInstructions(instructions)`: Submits repair instructions to the model.
- `reassignToBuilder()`: Moves workflow step backward in the graph.

**Integration Strategy:**
Modify `src/services/api.ts` to instantiate a WebSocket connection (or use Tauri's IPC channels) pointing to the Python sidecar. Component code (e.g. `App.tsx` or `ChatFeed.tsx`) does not need to be refactored to support real data, as long as the returned promises from `api.ts` conform to the interfaces in `src/types.ts`.

## 4. TODOs for Python Backend

Based on the structure established by `mockData.ts` and `api.ts`, the Python Backend (via FastAPI / Socket.IO / Tauri IPC) must expose the following capabilities:

### Core Endpoints & Connections
1. **Agent Metadata API (GET):**
   - Provide the initial list of Agents (`initialAgents` format matching `Agent` interface).
2. **Model Configurations API (GET/PUT):**
   - Sync configured models and MCP servers.
3. **Workspace Retrieval API (GET):**
   - Fetch the state of a specific branch/workflow (returns `messages`, `runStatus`, `logs`, `uncommittedFiles`).
4. **Agent Action Submission (POST / WebSocket Emit):**
   - Receive user prompt/instructions, trigger LangChain/LangGraph workflow.

### Streaming WebSocket Events
The UI relies heavily on streaming observability. The Backend should push the following events:
- `onTerminalLog`: Emits streaming bash/orchestrator strings to append to the right panel terminal.
- `onAgentMessageChunk`: Streams agent conversation and code generation into the center feed.
- `onStatusChange`: Emits global execution status transitions (`running` -> `failed` -> `passed`).
- `onFileModified`: Reports new or modified file diffs to update the `UncommittedFile` tree.
- `onHumanInterventionRequired`: Triggers UI to halt and await `approveNode()` or `rejectNode()`.
