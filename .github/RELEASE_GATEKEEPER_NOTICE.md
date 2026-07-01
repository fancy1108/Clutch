# Release body fragments (legacy filename)

> **Superseded:** GitHub Release bodies are assembled by [`scripts/render-release-notes.sh`](../scripts/render-release-notes.sh) from `CHANGELOG.md` plus fragments in [`.github/release-notes/`](./release-notes/).

Install, upgrade, Gatekeeper, Windows, and verify sections live in:

| Fragment | Section |
|----------|---------|
| [`release-notes/install.md`](./release-notes/install.md) | Install |
| [`release-notes/upgrade.md`](./release-notes/upgrade.md) | Upgrade |
| [`release-notes/macos-first-launch.md`](./release-notes/macos-first-launch.md) | macOS first launch |
| [`release-notes/windows.md`](./release-notes/windows.md) | Windows |
| [`release-notes/verify-download.md`](./release-notes/verify-download.md) | Verify download |

**Do not** point `release.yml` `body_path` at this file. Edit fragments or `CHANGELOG.md` instead.
