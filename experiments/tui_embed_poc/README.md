# TUI Embed POC — Phase 0

> **门控**：[`RESULTS.md`](./RESULTS.md) · 产品方案：对话/终端双模式（`INTERACTIVE_PTY`）  
> **隔离**：不修改 `apps/desktop` / `services/orchestrator` 产品代码。

验证「用户手动操作 xterm + PTY 双向字节流」能否承载 Claude Code / OpenCode 交互 TUI（与 Route A 自动化 expect 不同）。

## 运行

### 1. PTY 泵探针（bash 冒烟，无 API）

```bash
cd experiments/tui_embed_poc
python3 step0_pty_pump.py --smoke
```

### 2. 交互 CLI + WebSocket（需本机 `claude` 或 `opencode`）

```bash
uv run --with websockets python step0_pty_pump.py --cli claude --port 8765
```

浏览器打开 `step0_xterm_harness.html`（或 `python3 -m http.server 8088` 后访问）。

### 3. 记录结论

更新 `RESULTS.md` 与 `runs/*.json`。

## 通过标准

| 检查项 | 条件 |
|--------|------|
| bash 双向 IO | smoke 通过 |
| Claude TUI | xterm 可见 Ink UI，手动输入有回显 |
| OpenCode TUI | 同上（若已安装） |
| detach | 关闭 WS 后进程仍存活（可选） |

## 目录

```
experiments/tui_embed_poc/
├── README.md
├── RESULTS.md
├── step0_pty_pump.py
├── step0_xterm_harness.html
└── runs/
```
