# D25 · Hybrid Runtime 执行计划（HRT）

> **权威任务表**：本文件为 D25（ShellSession + `SHELL_EXEC`）**唯一可执行 Task 清单**。  
> **设计参考**：[`docs/research/pty-session.md`](../../docs/research/pty-session.md)（叙事与 POC 证据，冲突以本文件 + `memory/DECISIONS.md` 为准）。  
> **决策**：D25 · D27 · D28 — [`memory/DECISIONS.md`](../../memory/DECISIONS.md)  
> **验收勾选**：[`memory/ROADMAP.md`](../../memory/ROADMAP.md) §D25 Hybrid Runtime  
> **交付索引**：每 Task commit 后写入 [`memory/DELIVERABLES.md`](../../memory/DELIVERABLES.md)

---

## 1. 范围与命名对齐

### 1.1 已交付（代码存在，≠ 产品验收通过）

| 代号 | 内容 | 主要 Commits / 证据 |
|------|------|---------------------|
| **HRT-S1** | ShellSession · shell_exec · parser · hybrid_executions WS | `d6c6c90`…`848ed7f` 系列 |
| **HRT-S2** | agy Hybrid · sweep · baseline JSON | `b69e35d` · `experiments/pty_poc/runs/` |
| **HRT-S3** | Snapshot API · 侧栏 ↻ · DISCONNECTED 恢复 | `97a2d15` · `39eecba` |
| **HRT-S4** | `runtime_registry.try_shell_exec_hybrid` | `73f6eef` |
| **HRT-S5-partial** | 池上限 8 · Snapshot 30 天 prune | `3c8229c` · `27ea3f4` |

> **命名校正**：`memory/PROGRESS.md` 中曾称「Step 5」的池/prune **不等于** `pty-session.md` §Step 5 全文（并发治理 + 审计）。后者对应本计划 **HRT-05 ~ HRT-07**。

### 1.2 显式不做（人类已确认）

- MCP `hybrid_executions` 折叠区深度 UI 打磨（已有基础 disclosure）
- POC 验收 #9：2h / 100+ 轮压测
- Claude TUI PTY（Route A，已否决）

### 1.3 启用方式

```bash
export CLUTCH_RUNTIME_MODE=hybrid
pnpm --filter @clutch/desktop tauri dev
```

默认 `legacy`；Hybrid 失败应 fallback legacy（验收 #15）。

---

## 2. Task 清单（按依赖顺序）

每个 Task **必须**：原子 commit → `./scripts/verify.sh` → `DELIVERABLES.md` 一节 → 更新 `PROGRESS.md` → 通过后勾选 `ROADMAP.md`。

| ID | 主题 | 状态 | 依赖 | 完成标准 | Verification |
|----|------|------|------|----------|--------------|
| **HRT-00** | 计划与文档对齐 | ✅ | — | 本文件 + ROADMAP/DECISIONS/tasks/FILEMAP 同步 | `check-doc-drift.sh` |
| **HRT-01** | 基础聊天气泡 + idle 恢复 | ⚠️ 待验收 | S1–S4 | 见 §3.1 A–D；含 `848ed7f` 与 HRT-01~03 commit | 人工验收 §3 + pytest |
| **HRT-02** | Marker 完成检测（ANSI / clutch$） | ✅ 代码 | HRT-01 | 真实 `claude -p` turn ≤120s | pytest + 本地 hybrid 单 turn |
| **HRT-03** | Snapshot 仅断线恢复注入 | ✅ 代码 | HRT-01 | 续轮气泡无 `Task summary` / `Working directory` | pytest |
| **HRT-04** | **产品验收：单 session 串行** | ✅ | HRT-01~03 | §3.1 A–E | 用户确认 2026-06-27 |
| **HRT-05** | Hybrid turn 审计 JSONL | ✅ | HRT-04 | 每 turn 写结构化行；含 run_id/marker/duration/result | pytest + 读 jsonl |
| **HRT-06** | `GET /api/runs/{id}/debug` | ✅ | HRT-05 | 返回 status、末 N 条 terminal_logs、最近 audit 行 | pytest API |
| **HRT-07** | 诊断导出（UI 或 CLI script） | ✅ | HRT-06 | 一键导出 run 摘要（无密钥） | `./scripts/export-run-debug.sh` |
| **HRT-08** | 多 session 并发治理 | 🔄 待 commit | HRT-04 | 池满/全 BUSY 时 UI 提示；非 silent Thinking | pytest + 双 session 手动 |
| **HRT-09** | 后台 turn 完成 hydrate | ❌ | HRT-08 | 切 session 后回来可见已完成回复 | 手动：A 发送 → 切 B → 回 A |
| **HRT-10** | POC 验收 #6 #10 自动化 | ❌ | HRT-08 | BUSY 拒绝/排队；两 run_id cwd 隔离 | pytest 或 poc 脚本 |

**状态图例：** ❌ 未通过 · ⚠️ 部分/未验收 · 🔄 进行中 · ✅ 已验收

### 2.1 执行顺序与维护习惯（D29 · 2026-06-27）

**顺序（已拍板）：** HRT-05 → HRT-06 → HRT-07 → HRT-08~10 → **回看** HRT-05~07 是否需增补。

| 原则 | 说明 |
|------|------|
| **HRT-05~07 是长期基建** | 像 pytest/vitest：Hybrid 相关代码变动时，同步检查 audit 字段、debug API、导出是否仍够用 |
| **先可排查、再扩并发** | 没有结构化日志就做并发，问题仍靠截图 |
| **HRT-08 后回归 audit** | 并发路径可能新增 failure mode，需在 JSONL/API 中可见 |
| **每个代码 Task Check-out** | 若触及 hybrid turn / shell / parser / router：跑 `./scripts/verify.sh`；**考虑**是否补 audit 字段或单测 |

---

## 3. 人工验收清单（HRT-04 门禁）

> 证据写入 `runs/verification/YYYY-MM-DD-hrt-04-acceptance.md`（截图可选，**必须**附 run_id + terminal_logs 摘录）。

### 3.1 单 session（必须通过）

| # | 场景 | 通过标准 |
|---|------|----------|
| A | 首轮 Plain Chat | 气泡**仅** assistant 文本；shell 在「View execution details」 |
| B | 第二轮续聊 | 同上；Terminal 有 `[HYBRID] resume`；发送键恢复 |
| C | 侧栏 ↻ | 至少一轮成功后旧 session 显示 ↻ |
| D | UI 状态 | 回复后 `status: idle`；可切 session；无永久 Thinking |
| E | Terminal | 有 `[HYBRID]` + `[CHAT] ... chars` |

### 3.2 多 session（HRT-08 前：已知限制）

| # | 行为 | 当前预期 |
|---|------|----------|
| F | 两 session 同时发消息 | **可能**双卡；验收期 **串行** |
| G | 排查 | 用 run_id 查 `states/{run_id}.json` 或 HRT-06 API，**不依赖截图** |

---

## 4. 已合入 commit（HRT-01~03）

见 `git log` — `claude_hybrid_output_parser.py` · `engine_router.py` · 单测。

---

## 5. 文档同步矩阵（每个 Task 必做）

| Task 完成时更新 | 内容 |
|----------------|------|
| `memory/DELIVERABLES.md` | Commit · Verification · 证据路径 · `--stat` 文件列表 |
| `memory/PROGRESS.md` | 完成了什么 · 下次优先 HRT-xx |
| `memory/TESTS.md` | 门禁命令与结果（若跑 verify） |
| `memory/ROADMAP.md` | 对应行 ❌→✅ |
| 本文件 §2 状态列 | 同步 Task 状态 |
| `memory/FAILURES.md` | 卡壳 >10min 或验收失败根因 |

**架构/范围变更** 额外：`memory/DECISIONS.md` · `docs/research/pty-session.md` 交叉引用（不扩权铁律）。

---

## 6. 调试数据现状（HRT-05 目标态）

| 存储 | 路径 | 用途 |
|------|------|------|
| 会话 state | `~/Library/Application Support/clutch_dev/sessions/states/{run_id}.json` | messages + terminal_logs |
| 会话列表 | `.../sessions/history.json` | 侧栏元数据 |
| Shell snapshot | `.../shell_snapshots/{run_id}.json` | ↻ 续作 |
| **目标 audit** | `.../logs/hybrid/{date}.jsonl` | HRT-05 新增 |

查询（Sidecar 运行时）：

```bash
curl -s http://localhost:8123/api/runs/{run_id}/state | jq '{status, last_logs: .state.terminal_logs[-8:]}'
```

HRT-06 后：`GET /api/runs/{run_id}/debug`（可选 `logs_limit` / `audit_limit`）。

```bash
curl -s "http://localhost:8123/api/runs/{run_id}/debug?logs_limit=8&audit_limit=20" | jq '{status, terminal_logs, hybrid_audit}'
./scripts/export-run-debug.sh {run_id} --out runs/verification/{run_id}-debug.json
```

---

## 7. 与 `pty-session.md` Step 映射

| pty-session Step | HRT ID | 说明 |
|------------------|--------|------|
| Step 0 | POC | `experiments/pty_poc/RESULTS.md` |
| Step 1 | HRT-S1 | ShellSession 核心 |
| Step 2 | HRT-S2 | agy + baseline |
| Step 3 | HRT-S3 | Snapshot + ↻ |
| Step 4 | HRT-S4 | runtime_registry |
| Step 5（设计全文） | HRT-05~10 | 审计 + 并发 + POC #6/#10 |
| Step 5（已实现子集） | HRT-S5-partial | 仅 pool + prune |
