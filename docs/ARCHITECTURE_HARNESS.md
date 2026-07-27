# Clutch Agent 2.0 Harness Engineering Architecture & Spec

This document details the Harness Engine infrastructure implemented in Clutch, based on the principles of 《深入理解 AI Agent》.

## 🏛️ Core Equation

$$\text{Agent} = \text{Model} + \text{Harness}$$
$$\text{Harness} = \text{Context} + \text{Tools} + \mathbf{Constraints} + \mathbf{Verification} + \mathbf{Correction}$$

---

## 🛠️ Infrastructure Components

### 1. Constraints (harnessLoopDetector.ts)
- **Loop Detector**: Intercepts tool call trajectories. If the same tool + arguments combination is invoked repeatedly 3 times, the execution is automatically halted with a circuit-breaker notice to prevent infinite `Working...` loops.

### 2. Verification (harnessAuditor.ts)
- **Premature Completion Prevention**: Before an agent marks a task complete or sends a final response, the Harness executes deterministic code assertions checking that expected media/document files (`.png`, `.mp4`, `.md`) exist on disk and have a byte size > 0. If missing, the "false completion" is rejected.

### 3. Correction & Fallbacks (agentSanitizer.ts)
- **Zero-Context Base64 Firewall**: Media tools (`generate_image`, `generate_video`) write Base64 data directly to disk and return a lightweight path string (<100 chars) to LLM context, preventing 1.4M+ char token overflow errors.
- **API Circuit Breaker**: 20-second timeout guard on external API calls with automatic disconnect cards.
- **Web Fetch Fallback**: Gracefully handles 403 / anti-scraping blocks by substituting search summary text.

### 4. Context & State Machine (agentStateMachine.ts)
- **Code-Driven Deterministic State Machine**: Harness code updates Todo states based on real tool execution events, ensuring 100% UI accuracy independent of LLM `todo_write` calls.

### 5. Multi-Agent Message Distillation (agentRouter.ts)
- **Generic Agent Router**: Intermediate tool outputs from worker sub-agents are contained in sub-threads, routing only final deliverables to the main UI session.

### 6. Media Asset Registry (agentSanitizer.ts - UniversalArtifactRegistry)
- **Bi-directional Asset Mapping**: Maps generated media filenames (e.g. `task_421...mp4`) to user task names and prompts for seamless in-feed rendering.

### 7. Zero-Token Meta Query Gateway Interceptor (`interceptMetaToolQueries`)
- **Tool Discovery Interception**: Intercepts queries like "你有哪些 tool" or "what tools can you call" directly at the middleware gate, returning structured capability maps in 0.01s without LLM Token consumption or workspace file searches.

### 8. Dynamic Environment Context Provider (`getClientEnvironmentContext`)
- **Real-Time Client Clock & Timezone**: Dynamically attaches client timestamp (`YYYY-MM-DD HH:mm:ss`), timezone (`Asia/Shanghai`), OS platform (`macOS arm64`), and locale to requests without bloating static System Prompt (preserving KV Cache).

### 9. Bilingual Language Alignment Guard (`detectUserLanguage`)
- **Automatic Language Detection**: Detects user input language (`zh` / `en`) and enforces strict language matching for system responses, tool discovery lists, and dynamic context anchors.

### 10. Industry Standard Desktop Isolation Spec (In-Memory Diff & Temp Sandboxing)
- **In-Memory Diff Gate**: Non-destructive code edits are rendered as visual Diff cards (`DiffLine[]`) before physical disk write, conforming to Cursor / OpenAI Canvas IDE specs.
- **Ephemeral Sandbox**: Background test runs and search scripts execute in `.clutch/temp/` sandbox, keeping workspace clean and isolated.

### 11. Progressive Skill Loading Architecture (Skill Sitemap & Lazy On-Demand Reader)
- **Canonical Skill Path**: `/Users/fancy/obsidian/PARA/3_Resources/Skills/Sources/`
- **Sitemap Indexing**: System Prompt maintains a lightweight ~1K Token Skill Sitemap (Name + Short Description only), keeping static prefix small & preserving KV Cache.
- **On-Demand Lazy Loading**: When LLM matches a user task to a domain skill (e.g. `using-git-worktrees`, `mcp-builder`), it dynamically reads `/Skills/Sources/<skill>/SKILL.md` via `view_file`. Conforms to Claude Code & Cursor Rules Specs.

### 12. Safe Context Compaction Spec (Isolation Over Compression & Retention White-List)
- **Isolation Over Compression**: Deep file explorations and web scrapes are delegated to sub-agents, returning only concise conclusions (100 tokens) to main Context.
- **Compaction Priority White-List**: When compaction is triggered at 80% token threshold, System Prompt, architectural constraints, file modification lists, verification pass/fail status, pending TODOs, and exact identifiers (Commit Hashes, UUIDs, IP/Port, URLs) are 100% immune from compression.
- **Lossless Index Pointers**: Compressed tool summaries must retain lossless source links (`[SOURCE INDEX]: src/file.ts#L42`) allowing instant re-retrieval if detail is needed.



