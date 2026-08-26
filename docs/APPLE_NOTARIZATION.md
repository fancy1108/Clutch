# Clutch — Apple 代码签名与公证（OSR-11 / FM-21）

> **状态（2026-08-26）：阻塞。** 维护者**没有** Apple Developer Program 账号，无法签发 Developer ID、无法 `notarytool`。  
> **D31 仍有效：** GitHub Releases 继续发**未签名** DMG；Gatekeeper 绕过见 [`INSTALL.md`](./INSTALL.md) §2–§4。  
> 本文只写**账号到位后**的操作顺序。**不要**把当前 Release 说成已公证。

---

## 1. 用户现在会看到什么

| 现象 | 原因 | 用户动作 |
|------|------|----------|
| 「无法验证开发者」/「已损坏」 | 未签名 + quarantine | [`INSTALL.md`](./INSTALL.md)#gatekeeper |
| 企业 MDM 拦截 | 无 Developer ID | 源码自建或等公证包 |

CI 构建仍是 unsigned：`services/orchestrator/clutch.spec` 里 `codesign_identity=None`；Tauri bundle **未**配置 `signingIdentity`。

---

## 2. 账号与证书（一次性）

1. 加入 [Apple Developer Program](https://developer.apple.com/programs/)（年费）。
2. 在 Certificates 创建 **Developer ID Application**（分发用，不是 Mac App Store）。
3. 导出 `.p12`，只放 CI secret / 本机钥匙串，**禁止**提交仓库。
4. 需要公证时：App Store Connect **App-specific password**，或 **Issuer ID + API key**（`.p8`）。

---

## 3. 签名顺序（账号可用后）

在 **macOS** 上、对 **即将上传的** `.app` 操作：

1. **Sidecar 二进制**（PyInstaller `orchestrator`）：`codesign --force --options runtime --sign "Developer ID Application: …" --timestamp`。若打包解释器拒绝 hardened runtime，再评估最小 entitlements（例如 `com.apple.security.cs.allow-unsigned-executable-memory`）。**避免**默认打开 `disable-library-validation`。
2. **把 `clutch.spec` 的 `codesign_identity` 从 `None` 换成同一身份**，使后续 sidecar 构建自带签名。
3. **Tauri `.app`：** `tauri.conf.json` → `bundle.macOS.signingIdentity`；必要时 `entitlements` 文件。
4. **公证：** `xcrun notarytool submit <dmg-or-zip> --wait`，成功后 `xcrun stapler staple`。
5. **CI：** 在 [`.github/workflows/release.yml`](../.github/workflows/release.yml) 注入证书与 notary 凭证后再构建；未注入前**保持** unsigned 产物，以免半签名包无法打开。

Windows Authenticode **不在** OSR-11 范围。

---

## 4. 完成定义（以后才能勾 OSR-11）

- Stapled DMG 在干净 macOS 上**双击即开**，无需 `xattr -cr`。
- Release 正文去掉「未签名」主警告，改为「Developer ID 已公证」。
- `INSTALL.md` §2 改为历史说明或删除。

在此之前 ROADMAP **OSR-11 保持未勾**；FM-21 只表示本流程已写明、阻塞点已记录。
