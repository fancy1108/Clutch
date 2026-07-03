# TUI Embed POC — Phase 0 结果

> 机器可读：`runs/*.json` · 设计门控：对话/终端双模式 `INTERACTIVE_PTY`

## 总览（2026-07-02）

| 检查项 | 状态 | 结果 | 证据 |
|--------|------|------|------|
| bash PTY 双向 IO | ✅ | 3/3 echo 回显 | `runs/*-bash-smoke.json` |
| Claude TUI + xterm | ⏳ 待人工 | 需本机 `claude` + `step0_pty_pump.py --cli claude` + harness | 脚本已就绪 |
| OpenCode TUI + xterm | ⏳ 待人工 | 需本机 `opencode` | 脚本已就绪 |
| 与 Route A 区别 | ✅ 已澄清 | 本 POC **不做** expect 轮次判定；仅验证人工 xterm 场景 | — |

## 决策门

| 项 | 判定 |
|----|------|
| PTY 字节泵（bash） | **Go** — smoke 通过 |
| 嵌入 xterm（产品 Phase B/C） | **Go（有条件）** — 技术路径成立；CLI TUI 需真机 harness 复验 |
| 修改现有 `SHELL_EXEC` headless | **禁止** — 终端模式走独立 `interactive_pty_runtime.py` |

## 下一步

1. 产品 Phase A：Chat/Terminal 切换 UI（默认 chat）
2. Phase B/C：`pty_output` / `pty_input` + `interactive_pty_runtime`
3. 维护者在本机跑 `uv run --with websockets python step0_pty_pump.py --cli claude` 补全 Claude/OpenCode 行
