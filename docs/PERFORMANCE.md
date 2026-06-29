# Clutch — 性能基线

> **Normative policy only** — performance targets, not caching implementation. Do not duplicate implementation detail from [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## 1. 目标指标

| 指标 | 目标 | 测量点 |
|------|------|--------|
| **冷启动（App → UI 可交互）** | < 8s | DMG 双击至主界面可点击（含 Sidecar 拉起） |
| **Sidecar 健康检查** | < 5s | `curl http://127.0.0.1:8123/health` 成功（见 `src-tauri/README.md`） |
| **Sidecar 进程就绪（dev）** | < 3s | `uvicorn` 本地开发机参考值 |
| **Workflow 模板加载** | < 1s | `GET /api/workflows/templates` P95 |
| **WebSocket `state_patch` 延迟** | < 500ms | 编排节点切换至 UI 高亮（局域网回环） |
| **UI 滚动 / 动画** | ≥ 30 FPS | Terminal 日志滚动、侧栏列表（主观 + Performance panel） |
| **空闲内存（App + Sidecar）** | < 1 GB | 无活跃 Workflow；macOS Activity Monitor 参考 |
| **活跃 Workflow 内存** | < 2 GB | 含 CLI 子进程除外（CLI 另计） |

---

## 2. 非目标（暂不优化）

- 与原生 IDE 比启动速度  
- 超大 monorepo 文件树一次性加载  
- 100+ 并发 Agent 压测（见 `memory/ROADMAP.md` 验收期跳过项）

---

## 3. 测量环境（基准）

| 项 | 参考配置 |
|----|----------|
| 机器 | Apple Silicon Mac，16 GB RAM |
| macOS | 14+ |
| 构建 | Release DMG 或 `pnpm tauri build` |
| 网络 | 离线或仅本地 Ollama（测 LLM 路径时单独注明） |

Intel Mac、Windows 为 **尽力支持**，基线可能偏离 ±30%。

---

## 4. 如何复现（维护者）

```bash
# Sidecar 健康（DMG 安装后）
time curl -sf http://127.0.0.1:8123/health

# 模板 API（sidecar 已运行）
time curl -sf http://127.0.0.1:8124/api/workflows/templates  # dev 端口

# 全量回归（含单元测试，非纯性能）
./scripts/verify.sh
```

未来可在 `runs/verification/` 归档带时间戳的测量记录。

---

## 5. 回归策略

| 触发 | 动作 |
|------|------|
| Hybrid / PTY / 编译器大改 | 手测冷启动 + WS 延迟 |
| PyInstaller / Tauri 升级 | 手测 DMG 启动与包体大小 |
| 前端大列表渲染改动 | 手测 Terminal 长日志滚动 |

自动化性能 CI **尚未** 纳入门禁（P2）；欢迎贡献 benchmark 脚本。

---

## 6. 相关文档

| 文档 | 内容 |
|------|------|
| [`OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) | 分发与验收 |
| [`STABILITY.md`](./STABILITY.md) | 版本承诺 |
