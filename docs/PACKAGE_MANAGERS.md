# Package managers — Homebrew · winget · Intel Mac

> **Audience:** End users and release maintainers.  
> **Related:** [`INSTALL.md`](./INSTALL.md) · [`scripts/install.sh`](../scripts/install.sh) · [`scripts/install.ps1`](../scripts/install.ps1)

---

## Summary

| Channel | Status | Install |
|---------|--------|---------|
| **macOS DMG** (Apple Silicon) | ✅ Primary | Releases · `install.sh` |
| **macOS DMG** (Intel) | 🚧 **Not built yet** | See [§ Intel Mac](#intel-mac-workload) |
| **Windows NSIS** | ⚠️ CI-built · **not verified on hardware** ([#23](https://github.com/fancy1108/Clutch/issues/23)) | Releases · `install.ps1` |
| **Homebrew Cask** | ✅ Manifest in repo · tap optional | See [§ Homebrew](#homebrew) |
| **winget** | ✅ Manifest in repo · **not in winget-pkgs yet** | See [§ winget](#winget) |

Clutch is a **desktop app**, not an `npm` / `cargo` CLI. Package managers wrap the same GitHub Release installers.

---

## Homebrew

Cask source: [`packaging/homebrew/Casks/clutch.rb`](../packaging/homebrew/Casks/clutch.rb)

### From a cloned repo (works today)

```bash
git clone https://github.com/fancy1108/Clutch.git
cd Clutch
brew install --cask ./packaging/homebrew/Casks/clutch.rb
```

The cask runs `xattr -cr` after install (unsigned DMG). **Apple Silicon only** (`depends_on arch: :arm64`).

### Official tap (recommended after publish)

Homebrew taps require a repo whose **root** contains `Casks/`. Mirror the cask to:

`https://github.com/fancy1108/homebrew-clutch` → `Casks/clutch.rb`

Then:

```bash
brew tap fancy1108/clutch
brew install --cask clutch
```

Submitting to [homebrew-cask](https://github.com/Homebrew/homebrew-cask) is optional and slower review; a project tap is enough for OSS.

### Maintainer: bump on release

1. Update `version` and `sha256` in `clutch.rb` (from Release `SHA256SUMS.txt`).
2. Sync to `homebrew-clutch` repo if used.
3. `brew audit --cask clutch` (in tap repo).

---

## winget

Manifests: [`packaging/winget/manifests/f/fancy1108/Clutch/`](../packaging/winget/manifests/f/fancy1108/Clutch/)

### Local manifest install (works today)

```powershell
git clone https://github.com/fancy1108/Clutch.git
cd Clutch
winget install --manifest .\packaging\winget\manifests\f\fancy1108\Clutch\1.0.2
```

Uses the NSIS `Clutch_*_x64-setup.exe` from GitHub Releases. **Not yet verified on physical Windows hardware** ([#23](https://github.com/fancy1108/Clutch/issues/23)).

### Microsoft community repository (after PR merge)

After a PR to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) is merged:

```powershell
winget install --id Fancy1108.Clutch
```

Maintainer flow per release:

1. Copy `packaging/winget/manifests/f/fancy1108/Clutch/<version>/` into winget-pkgs (or use [`wingetcreate`](https://github.com/microsoft/winget-create)).
2. Update `InstallerSha256` from `SHA256SUMS.txt`.
3. Open PR; wait for/winget bot validation.

---

## Intel Mac workload

**Short answer:** **中等工作量（约 1–2 天）**，不是改一行配置就行，但也不需要重写产品。

### Why it's not trivial

| Piece | Today | Intel needs |
|-------|--------|-------------|
| **GitHub Actions** | `macos-latest` → **arm64** host | Second job or cross-target build |
| **Tauri / Rust** | Native `aarch64-apple-darwin` | `x86_64-apple-darwin` target |
| **PyInstaller sidecar** | Built for host triple in `build-sidecar.py` | **Separate x86_64** `orchestrator-x86_64-apple-darwin` binary |
| **Release asset** | `Clutch_*_aarch64.dmg` | e.g. `Clutch_*_x64.dmg` |
| **install.sh / Cask** | `aarch64` only | Arch detection + second cask or `on_arch` |
| **App updater** | `darwin-aarch64` in `latest.json` | Optional second entry |

The **sidecar** is the main cost: PyInstaller must run with an x86_64 Python on CI (e.g. `arch -x86_64` + x86_64 `uv` Python on Apple Silicon runner, or a self-hosted Intel Mac).

### Suggested implementation order

1. CI job `build-macos-intel-dmg` — `pnpm tauri build --target x86_64-apple-darwin` + x86_64 sidecar script.
2. Upload `Clutch_*_x64.dmg` to Releases + `SHA256SUMS.txt`.
3. Extend `install.sh` / Homebrew cask with `on_arch` blocks.
4. Smoke on a real Intel Mac (or Rosetta-only validation with caveats).

### Until then

- Intel users: [`BUILD_FROM_SOURCE.md`](./BUILD_FROM_SOURCE.md) on the machine, or use Apple Silicon DMG on M-series only.
- `doctor.sh` already warns on `x86_64` hosts.

---

## Comparison with CLI tools (Codex, Reasonix)

Those projects ship **Node CLIs** → `npm install -g` / `brew install` formula is natural.

Clutch ships a **bundled GUI + Python sidecar** → package managers install the **same DMG/EXE** as manual download. There is no `npm install -g clutch`.
