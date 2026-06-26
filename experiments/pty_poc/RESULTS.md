# PTY POC — Step 0 结果

> 机器可读原始数据：`runs/*.json` · 基准合并：`baseline/*.json`  
> 设计门控：[`docs/research/pty-session.md`](../../docs/research/pty-session.md) §3.0

## 总览（2026-06-26）

| 路线 | 状态 | 结果 | 证据 |
|------|------|------|------|
| **B** Headless 扫描 | ✅ 完成 | 无 `--headless` / `--no-tui`；`-p` 跳过 trust；`stream-json` 仅 print+verbose | `runs/*-route-b-headless-search.json` |
| **A** pexpect 驱动 TUI | ❌ **未过（严格）** | 模型有回复（`⏺OK`）但 Ink ANSI 使 expect 不可靠；宽松判定曾误报 5/5 | `runs/20260626T141659Z-route-a-pexpect.json` |
| **C** Hybrid bash + `claude -p` | ✅ **5/5** | cwd 继承成立；每轮 ~10–35s | `runs/20260626T141235Z-route-c-hybrid.json` |
| **C′** Hybrid bash + `agy -p` | ✅ **4/5** | round 4 偶发空输出（API/超时）；其余轮正常 | `runs/20260626T171156Z-route-c-hybrid-agy.json` |
| **0.5** baseline JSON | ✅ | `baseline/claude.json` · `baseline/agy.json` | `step0_baseline.py` |
| 0.1 裸 PTY（遗留） | ❌ 证伪 | 裸 `os.write` 无法过 trust gate | `runs/20260626T134818Z-claude-pty-probe.json` |

**Step 0 进度：✅ 完成**（Route C claude 5/5 · agy 4/5 · baseline JSON 已合并）

---

## 决策门（BLOCKER）— 当前判定

| 风险 | 等级 | 实测结论 |
|------|------|----------|
| Claude CLI 长期 PTY 驱动（expect） | **BLOCKER** | **未清除**：严格 5/5 失败（round 1 timeout）；TUI 有输出但 ANSI 边界不可靠 |
| Headless 官方模式 | 降险 | 不存在；`-p` 为事实上的 headless |
| Hybrid Plan B | 备选 → **并行可行** | Route C 5/5；实现成本低于 TUI 驱动 |

**架构建议（实测结论 · 已写入方案 v4）：**

1. **否决 Claude TUI PTY**；Step 1 默认 **`ShellSession` + `SHELL_EXEC`**（Route C 5/5）。
2. **`HumanInputKind`**（`BOOT_TRUST` / `TOOL_CONFIRM` / `TEXT` / `AUTH`）为 Runtime 一级概念，非 Provider 字符串特判。
3. **`RuntimeStrategy`** 矩阵见 `docs/research/pty-session.md` §2.2；EngineRouter 第三阶段改为 `strategy = provider.runtime_strategy`。

---

## Route B — Headless 扫描

- `print_skips_trust`: **true**（help 换行折行，检测需 normalize 空白）
- `headless` / `no_tui`: **false**
- `stream_json_print_only`: **true**（`--print` + `--verbose`）
- `bare_mode`: **true**（`--bare` 存在，待评估）

---

## Route A — pexpect TUI

**通过条件**：严格 5/5 ❌（`20260626T141659Z`，round 1 timeout @120s）

**现象**：TUI 实际已输出 `⏺OK`（见 `output_preview`），但 ANSI 光标控制序列导致 `expect` 无法稳定判定轮次结束。宽松匹配（在 prompt 回显里搜 `OK`）会 **误报 5/5** — 不可用。

**Boot Barrier 序列**（新 workspace，已通过）：

```
1. BOOT_TRUST      → send "1\r"
2. Bypass Perms    → send "\x1b[B\r"  (默认停在 "No exit")
3. expect ready    → 5 × (prompt + "\r" → expect output)
```

**失败教训**（已修复）：

| 问题 | 原因 | 修复 |
|------|------|------|
| `timeout BOOT_TRUST` | workspace 已信任 | 每跑使用 `/tmp/clutch-pty-poc-<uuid>` |
| round 1 EOF | 未过 Bypass Permissions | 增加第二道门控 handler |
| 裸 PTY 无效 | Ink TUI + 菜单 | 必须用 pexpect + Enter |

**HumanInputKind 观测**：`BOOT_TRUST`、Bypass（可归入 `BOOT_TRUST` 或扩展 `boot_bypass`）

---

## Route C — Hybrid Runtime

**通过条件**：5/5 + cwd 继承 ✅（`20260626T141235Z`）

```
ShellSession → bash (长驻)
    ├── cd sub && pwd  → cwd 继承 OK
    └── CLUTCH_P='…'; claude -p "$CLUTCH_P" …; echo __MARKER__
```

**关键实现点**：

- 等 **marker** 而非 idle 超时（`claude -p` 常 >1.5s 静默）
- 用 `CLUTCH_P` 环境变量缩短 PTY 行输入（避免 readline 折行）
- `bash --norc --noprofile -i` 减少 login 噪音

**样例输出**：`OK` / `2 + 2 = 4` / `Hi!` / `DONE` / `Blue.`

---

## BoundaryDetector 输入（初稿）

| 字段 | Hybrid (`claude -p`) | TUI PTY (`claude` 交互) |
|------|----------------------|-------------------------|
| `max_silence_ms` | 等 marker；单轮 ~10–35s | 轮间需 expect；模型思考可达 120s |
| `human_confirm_patterns` | print 模式少见 | `Allow tool`、`Overwrite?` → `TOOL_CONFIRM` |
| `human_input_kinds_observed` | — | `BOOT_TRUST`、Bypass Perms |
| TUI / ANSI | 仅 bash echo | 是 — 需剥 ANSI |
| 结构化边界 | `stream-json`（print） | 交互 PTY **无** stream-json |

---

## 下一步

1. Step 5：多 `run_id` 池上限、后台进程审计
2. 验收 #9：2h / 100+ 真机 Hybrid 长测（claude 为主）
3. MCP approve 路径写入 `hybrid_executions`
