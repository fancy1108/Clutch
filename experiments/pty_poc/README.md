# PTY Session POC — Step 0（三路线）

> **权威设计**：[`docs/research/pty-session.md`](../../docs/research/pty-session.md)（v4 · **ShellSession + `SHELL_EXEC`**）  
> **证据**：[`RESULTS.md`](./RESULTS.md) · `runs/*.json`（**本地生成，已 gitignore，勿提交**）

Step 0 目标：**在写 Sidecar 代码之前**，确认 **ShellSession（长驻 bash + per-turn exec）** 为默认 Runtime，**否决 Claude TUI PTY**。

## 决策门（2026-06-26 结论）

| 项 | 结论 |
|----|------|
| Claude TUI PTY（Route A） | **否决** — 严格 5/5 未过 |
| **ShellSession + `SHELL_EXEC`（Route C）** | **默认** — 5/5 |
| `RuntimeStrategy` 矩阵 | 见方案 §2.2 |

**原则**：不要让架构对抗上游产品设计；PTY 长驻的是 **shell**，不是 Claude Ink TUI。

---

## 路线 A（优先）— 真 PTY + expect

**目标**：证明 `claude` 交互 TUI 可被 **pexpect 风格**稳定驱动（非裸 `stdin.write`）。

```bash
cd experiments/pty_poc
uv run --with pexpect python step0_route_a_pexpect_probe.py --rounds 5
```

流程：

1. `pexpect.spawn("claude …")`
2. `expect(trust)` → `send("1\r")` — **BOOT_TRUST**（每 workspace 一次，可自动）
3. `expect(prompt_ready)`
4. `send(prompt + "\r")` → `expect(output)`
5. 连续 **5 轮**，**5/5** 则全量 PTY 方案继续

产物：`runs/*-route-a-pexpect.json`

---

## 路线 B — Headless / 非 TUI 模式扫描

**目标**：CLI 是否提供官方 headless / pipe 模式（避免驱动 Ink TUI）。

```bash
python3 step0_route_b_headless_search.py
```

扫描：`claude --help` 及子命令 help，关键词：`headless` `raw` `json` `stdio` `pipe` `no-tui` …

产物：`runs/*-route-b-headless-search.json`

**已知（2026-06-26）**：无 `--headless`；`-p` 在非 TTY 下**跳过 workspace trust**；`stream-json` 仅 `--print` + `--verbose`。

---

## 路线 C（默认）— ShellSession · Hybrid Runtime

**目标**：**ShellSession**（长驻 bash PTY）+ 每轮 exec `claude -p` / `agy -p` / `codex exec`。

```
ShellSession
    └── bash (长驻)
            ├── cd / export / npm run dev …
            └── claude -p "…"   # 每轮子调用
```

保留：cwd、shell 状态、dev server、环境变量。  
避免：Ink/React TUI 驱动。

```bash
python3 step0_route_c_hybrid_probe.py --rounds 5
```

产物：`runs/*-route-c-hybrid.json`

Route C **5/5** → Step 1 实现 **`ShellSessionManager` + `SHELL_EXEC`**（见方案 §2.2 · §3.1）。

---

## 辅助脚本（遗留 / 补充）

| 脚本 | 用途 |
|------|------|
| `step0_pty_probe.py` | 裸 PTY `os.write` 探测（已证伪 trust gate，供对比） |
| `step0_print_mode_probe.py` | `--print --output-format stream-json` 事件采样 |
| `step0_baseline.py` | 合并探测 JSON → `baseline/*.json` |

## 推荐执行顺序

1. **Route B**（快，无 API）  
2. **Route A**（BLOCKER）  
3. **Route C**（并行准备 Plan B）  
4. 更新 `RESULTS.md` → 回写 `docs/research/pty-session.md`

## 依赖

- Python 3.11+
- Route A：`pexpect`（`uv run --with pexpect …`）
- 路线 A/C 调用真实 Claude API（凭证 + 网络）

## 目录

```
experiments/pty_poc/
├── README.md
├── RESULTS.md
├── baseline_schema.json
├── step0_route_a_pexpect_probe.py   # Route A
├── step0_route_b_headless_search.py # Route B
├── step0_route_c_hybrid_probe.py    # Route C
├── step0_pty_probe.py
├── step0_print_mode_probe.py
├── step0_baseline.py
└── runs/          # local POC output (gitignored)
```
