# Clutch — 外部安全审计（OSR-22 / FM-22）

> **状态（2026-08-26）：流程已写，外包未启动。** 尚无第三方报告。  
> 漏洞**私密报告**仍走根目录 [`SECURITY.md`](../SECURITY.md)（GitHub Private Vulnerability Reporting）。本文只管**付费/约请**审计。

---

## 1. 何时启动

触发（任一即可，维护者决定）：

- 企业客户或融资要求第三方信函
- 准备去掉 D31、发公证 DMG 前的加固证明
- 重大 Sidecar / MCP / 工作流执行面改动后

日常开源 **不**把 OSR-22 当作发版门禁。

---

## 2. 委托步骤

1. **范围书面化：** 桌面壳（Tauri WebView）、loopback Sidecar（HTTP/WS）、工作区工具、MCP、工作流 JSON、凭据存储。对照 `SECURITY.md` in/out of scope。
2. **签约：** NDA + 报告所有权；禁止把用户密钥、`models.json`、真实 `runs/` 带出测试机。
3. **环境：** 提供 unsigned 或公证 DMG、源码 tag、`docs/ARCHITECTURE.md`；审计机不要用维护者日常工作区。
4. **交付物：** 书面报告（发现、严重度、复现、修复建议）+ 可选 retest 信。
5. **入库：**
   - **公开索引**（可提交）：[`security-audit/README.md`](./security-audit/README.md) 一行：日期、厂商、范围、结论摘要（无武器化细节）。
   - **全文 PDF**（默认可不入库）：本机 `runs/verification/security-audit/`（该目录被 gitignore）。需要对外分享时用加密渠道，不要开 Issue 贴全文。

---

## 3. 完成定义（以后才能勾 OSR-22）

- 至少一份**独立于维护者**的书面报告（可红acted）
- 公开索引已登记；CRITICAL/HIGH 有修复 commit 或明确接受风险（写入 DECISIONS）

FM-22 只表示委托路径与报告入口存在；**不等于**已审计。
