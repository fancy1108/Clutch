## Clutch v1.0.1 — Sidecar、Keychain & 生图修复

**建议所有 v1.0.0 及早期 v1.0.1 DMG 用户重新下载本版。**

### 修复了什么

- **聊天里生图只显示 “Generated image” 占位符**  
  Agnes 返回 CDN 链接（`*.agnes-ai.space`），WebView CSP 拦截外部图片。Sidecar 现自动下载并以内嵌 base64 显示。
- **Release DMG 里模型 API 连不上（Key 正确也失败）**  
  CI 曾打包 python.org 旧 OpenSSL 运行时；Release 工作流已改为仅使用 uv 管理的 Python 3.11。
- **Models Config 红字「无法连接 Sidecar」**  
  Keychain 日志 bug 导致 HTTP 500，或 WebView 无 Bearer token 导致 401；界面误报为 Sidecar 不可达。
- **Keychain 连弹 5 次**  
  改用 `security find` 读取 + 一次性 `-A` ACL 迁移；重启后不应再反复弹窗。
- **右侧 Flow 标签消失**  
  多 Agent 模式下 Flow 标签始终可见（未选工作流时显示引导）。

### 升级步骤

1. **`Cmd+Q`** 完全退出 Clutch
2. 若提示「正在使用中」→ 活动监视器结束 **`Clutch`** 与 **`orchestrator`**
3. 下载本 Release 的 DMG，拖入 **应用程序**
4. 终端执行：`xattr -cr /Applications/Clutch.app && open -a Clutch`
5. Keychain 弹窗 → **始终允许**（首次可能再弹 1 次）

### 校验（可选）

```bash
curl -s http://127.0.0.1:8123/health
# 应返回 {"status":"ok","api_version":"2"}
```

同目录 `SHA256SUMS.txt` 可校验 DMG 完整性。

---

## English

**Patch release — re-download recommended if you installed an earlier v1.0.1 DMG.**

- **Chat images** render inline (sidecar fetches Agnes CDN URLs → base64).
- **Release CI** bundles uv Python (fixes broken outbound HTTPS in prior CI DMGs).
- **Models Config** no longer false “cannot reach sidecar” errors.
- **Keychain** prompts reduced via stable ACL migration.
- **Flow tab** always visible in multi-agent mode.

**Upgrade:** Quit Clutch, replace from DMG, run `xattr -cr /Applications/Clutch.app`, click **Always Allow** on Keychain once.

Full changelog: [`CHANGELOG.md`](../CHANGELOG.md#101---2026-06-30)
