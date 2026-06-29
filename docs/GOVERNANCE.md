# Clutch — 维护者治理

> **Normative policy only** — maintainer process, not feature lists. Product: [`PRODUCT_INTRO.md`](./PRODUCT_INTRO.md).

---

## 1. 角色

| 角色 | 职责 |
|------|------|
| **Owner / BDFL** | 架构方向、Non-Goals 守护、Release tag、安全响应 |
| **Maintainer** | Review PR、分类 Issue、运行 CI、文档更新 |
| **Contributor** | Issue、PR、文档、复现包 |
| **User** | Bug 报告、使用反馈、Discussions（若启用） |

当前 Maintainer 名单见仓库 **About / README**（公开后维护）。初期通常为 Owner 一人。

---

## 2. 决策方式

| 事项 | 决策 |
|------|------|
| 日常 bugfix、文档、测试 | Maintainer 可合并（过 CI + `verify.sh`） |
| 新 API / Schema 字段 | Owner 或 Maintainer 共识；大变更需 ADR |
| Non-Goal 范围内功能 | **不合并**；关闭并链 [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) |
| 安全漏洞 | 私密报告（`SECURITY.md`）；Owner 协调修复与公告 |
| Release 发版 | Owner 打 tag；附 `CHANGELOG.md` |

无 Maintainer 共识时：**Owner 终裁**。

---

## 2.1 开源第一阶段 — 贡献政策（当前）

> 完整 contributor 指引见根目录 [`CONTRIBUTING.md`](../CONTRIBUTING.md)。  
> **一句话**：开源 = 任何人可贡献；**不** = 任何 PR 都必须合并。维护者拥有最终决定权。

| 默认 **拒绝** | 默认 **欢迎** |
|---------------|---------------|
| 大型功能 PR | Bug 修复 |
| 架构重写 PR | 文档改进 |
| 改变产品方向的 PR | 测试补充 |
| 路线图外 / Non-Goals 功能 | 小型、范围清晰的优化 |

大型或架构级工作 **必须先开 Issue**， maintainer 明确同意后再动手。关闭 PR 时会链到 `CONTRIBUTING.md` §Contribution Philosophy — **预期行为，非针对个人**。

第一阶段结束条件：在 `CHANGELOG.md` 或本文宣布进入「Phase 2 贡献策略」。

---

## 3. Issue 与 PR 期望

### Issue

- 先搜重复；安装问题附 `./scripts/doctor.sh` 输出  
- 功能请求说明场景，而非直接指定实现  
- 方向性请求对照 [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md)

### PR

- 一 PR 一主题；过 `./scripts/verify.sh`  
- 触及 `apps/desktop/src` 或 `services/orchestrator/src` 时遵循 [`CLAUDE.md`](../CLAUDE.md) 铁律  
- 使用 [PR 模板](../.github/pull_request_template.md)

### 标签（见 [`docs/agents/triage-labels.md`](./agents/triage-labels.md)）

`needs-triage` · `needs-info` · `ready-for-agent` · `ready-for-human` · `wontfix`

---

## 4. 通常不会接受的贡献

| 类型 | 原因 |
|------|------|
| 云服务、多租户、账号登录 | Non-Goal |
| 遥测、分析 SDK、默认上报 | 隐私承诺 |
| 未经讨论的大规模架构重写 | 见 [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) §3 |
| 替换 LangGraph 或其他编排核心 | 架构红线 |
| 绕过工作区白名单 / 默认开放 Sidecar | 安全 |
| 仅 Prototype mock（`setTimeout` 假编排） | 铁律禁止 |
| 与 `wontfix` Issue 重复的 PR | 浪费评审精力 |

**不代表个人 fork 不能做** — 仅说明上游合并预期。

---

## 5. 合并门禁

| 检查 | 要求 |
|------|------|
| CI | `pnpm build` + `pytest` 绿 |
| 本地 | 推荐 `./scripts/verify.sh` |
| 文档 | 用户可见行为变更加 `CHANGELOG`；架构变更加 `DECISIONS.md` |
| 安全 | 密钥不进日志；新端点考虑鉴权（T1+） |

---

## 6. 沟通渠道

| 渠道 | 用途 |
|------|------|
| **GitHub Issues** | Bug、功能讨论、安装问题 |
| **GitHub Security Advisories** | 私密漏洞（`SECURITY.md`） |
| **GitHub Discussions** | 可选；FAQ、Showcase（公开后按需开） |
| **PR Review** | 代码与文档贡献 |

无官方 Discord / Slack 时，以 GitHub 为准。

---

## 7. 相关文档

| 文档 | 内容 |
|------|------|
| [`PROJECT_SCOPE.md`](./PROJECT_SCOPE.md) | Goals / Non-Goals |
| [`EXTENSIBILITY.md`](./EXTENSIBILITY.md) | 扩展边界 |
| [`STABILITY.md`](./STABILITY.md) | API 稳定性 |
| [`OPEN_SOURCE_RELEASE.md`](./OPEN_SOURCE_RELEASE.md) | 开源排期 OSR-xx |
| [`CONTRIBUTING.md`](../CONTRIBUTING.md) | 贡献指南与 Phase 1 政策 |
