# Epicode — Persistent Memory MCP Server

> **Community/Vendor integration** — Epicode is a third-party project, not a Clutch official service. SaaS mode stores data on epicode.cn servers; users opt in by configuring the MCP connection. See [Privacy](#privacy) below.

> **Category:** AI Memory / Knowledge Graph
> **Protocol:** MCP Streamable HTTP (2025-06-18)
> **Tools:** 35 (memory CRUD, semantic search, recall with KG expansion, skills, feedback loop, identity)
> **License:** MIT (open source) · SaaS at epicode.cn · Self-hostable

## What it gives your Clutch agents

Epicode is a **spatial AI memory operating system**. When your Clutch agents connect to an Epicode MCP server, they gain:

- **Cross-session memory** — an agent remembers prior tasks, decisions, and findings across runs
- **Shared knowledge between agents** — what the Research agent stores, the Builder agent can recall (L2 workflow-level memory sharing)
- **Semantic search + knowledge graph** — not keyword matching; agents retrieve by meaning and explore connected concepts
- **Automatic knowledge linking** — stored memories are auto-related by label co-occurrence and embedding similarity

Without Epicode, each Clutch agent starts blank every session. With it, your workflow accumulates institutional knowledge.

## Quick start (2 minutes)

### Step 1 — Get an Epicode account

Sign up at [epicode.cn](https://epicode.cn) (free tier: 1000 memories). You'll receive an API key starting with `tm-`.

### Step 2 — Add Epicode as an MCP server in Clutch

Go to **Settings → MCP** and add a new server:

| Field | Value |
|-------|-------|
| Name | `epicode` |
| Transport | `HTTP` (Streamable) |
| URL | `https://epicode.cn/api/mcp` |
| Headers | `X-API-Key: tm-your-key-here` |

Click **Connect** — you should see 35 tools become available.

### Step 3 — Bind the MCP server to your agents

In **Settings → Agents**, edit each agent that should have memory (e.g. your Researcher, Builder, Reviewer) and add `epicode` to their **MCP Server** list.

> **For L2 (shared memory):** bind the *same* Epicode account to *all* agents in the workflow. They share one user space, so knowledge flows between them automatically.

### Step 4 — Run the memory pipeline template

The **Memory-Augmented Pipeline (Epicode)** workflow uses the default `clutch-agent` for all nodes. This means a single agent with Epicode MCP bound handles every step — it remembers across steps within the same run.

**For separate specialized agents (optional):** Create three agents in **Settings → Agents** (e.g. `Researcher`, `Builder`, `Reviewer`), bind Epicode MCP to each, then edit the workflow JSON to replace `"agent": "clutch-agent"` with your agent names. This gives each role its own system prompt while sharing the same Epicode memory space.

Give it a task like *"Design a rate-limiting middleware for our Rust API"*. Each agent will `memory_recall` before working and `memory_create` after — building a persistent knowledge base as the pipeline runs.

Run the same task a week later: the Research agent will `memory_recall` last week's findings instead of starting from scratch.

## How agent memory sharing works (L2)

```
┌─────────────┐     memory_create("finding X")     ┌───────────────┐
│ Researcher  │ ──────────────────────────────────▶ │   Epicode     │
└─────────────┘                                      │   Cloud       │
                                                     │ (shared user  │
┌─────────────┐     memory_recall("finding X")      │    space)     │
│   Builder   │ ◀────────────────────────────────── │               │
└─────────────┘                                      └───────────────┘
       │
       │  memory_create("built Y, decided Z")
       ▼
┌─────────────┐     memory_recall("decided Z")       (same space)
│  Reviewer   │ ◀────────────────────────────────────╯
└─────────────┘
```

All three agents authenticate with the same Epicode API key → same user space → shared memory. No manual context passing between workflow nodes needed.

## Key MCP tools your agents will use

| Tool | When to use |
|------|-------------|
| `memory_recall` | **Before** working — retrieves relevant memories + KG-expanded context. Supports `summary` mode for large result sets. |
| `memory_create` | **After** working — stores findings, decisions, code patterns with labels. |
| `memory_search` | Targeted semantic search when you need specific facts. |
| `ctx_save` / `ctx_load` | Save/restore full project context (for cross-session continuity). |
| `pattern_learn` / `pattern_recall` | Teach agents your project's coding conventions. |
| `feedback_submit` | Rate memory quality — improves future recall via the adaptive learning loop. |

## Self-hosting

Prefer to keep data fully local? Epicode is open source (MIT):

```bash
git clone https://github.com/sunormesky-max/epicode.git
cd epicode
# See backend/README.md for build instructions (Rust + ONNX Runtime)
```

Point your Clutch MCP config to `http://localhost:9111/api/mcp` instead.

## Learn more

- **Website:** [epicode.cn](https://epicode.cn)
- **GitHub:** [sunormesky-max/epicode](https://github.com/sunormesky-max/epicode)
- **SMRP Protocol spec:** [epicode.cn/smrp](https://epicode.cn/smrp) (Structured Memory Response Protocol)
- **Dashboard:** [epicode.cn/dashboard](https://epicode.cn/dashboard) (browse your memories, knowledge graph, skills)

## Privacy

- SaaS mode: memories are stored encrypted (AES-256-GCM) on epicode.cn servers (Tencent Cloud, China).
- Self-hosted: all data stays on your machine.
- LLM calls for cognitive features go to your configured provider (DeepSeek/OpenAI/etc) — Epicode does not train on your data.
