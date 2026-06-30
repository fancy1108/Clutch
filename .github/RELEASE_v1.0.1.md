## Clutch v1.0.1 — Sidecar & Keychain 修复

**建议所有 v1.0.0 用户升级。**

### 修复了什么

- **Models Config 红字「无法连接 Sidecar」**  
  打包版 Sidecar 实际在运行，但 `/api/models/config` 会因 Keychain 日志 bug 返回 500，或 WebView 拿不到 session token 返回 401；界面误报为「无法连接」。
- **Keychain 弹窗反复出现**  
  旧版每次加载 Models 会读 Keychain 60+ 次；现已缓存，同一进程内最多读一轮（约 6 次）。首次安装仍可能弹 **一次**，请点 **「始终允许」**（Always Allow）。
- **错误提示**  
  Models 页现在能区分：Sidecar 不可达 / 会话未授权 / 后端错误。

### 升级步骤

1. `Cmd+Q` 完全退出 Clutch  
2. 清理残留 Sidecar：`pkill -f "/Applications/Clutch.app/Contents/MacOS/orchestrator"`  
3. 下载下方 DMG，拖入「应用程序」替换旧版  
4. 从 `/Applications` 启动（不要从 DMG 卷内直接运行）

### 校验（可选）

```bash
curl -s http://127.0.0.1:8123/health
# 应返回 {"status":"ok","api_version":"2"}
```

同目录 `SHA256SUMS.txt` 可校验 DMG 完整性。

---

## English

**Patch release — upgrade recommended for v1.0.0 users.**

- Fixes packaged **Models Config** falsely reporting “Cannot reach Clutch sidecar” (HTTP 500 from Keychain logging bug + 401 without Bearer token).
- Reduces macOS Keychain prompt spam via cached key reads.
- Clearer UI errors for auth vs server failures.

**Upgrade:** Quit Clutch (`Cmd+Q`), kill orphan `orchestrator` on port 8123, replace `/Applications/Clutch.app` from the DMG, launch from Applications. Click **Always Allow** on the first Keychain prompt.

Full changelog: [`CHANGELOG.md`](../CHANGELOG.md#101---2026-06-30)
