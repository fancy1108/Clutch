# ROADMAP

> **Default FAIL：** 所有功能项默认 ❌，必须实际验证通过后才能标记 ✅。  
> 验证证据记入 `TESTS.md` 或 `runs/`。

## 功能清单

（第 6 步拆解 `tasks.md` 后填实）

## 待验证前提（来自 proposal §13 依赖与前提）

| 假设 | 待验证内容 |
|------|-----------|
| Python 3.11+ 可运行 | 开发期用户环境；发布期内嵌 runtime 可行性 |
| Claude API Key / Claude Code 已登录 | 用户自行配置路径与 UX |
| 目标项目已 clone 并授权为工作区 | 工作区路径白名单机制 |
| macOS 12+ 为第一平台 | Tauri 打包与 Sidecar 生命周期 |
