# Changelog

All notable changes to Clutch are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Version policy:** See [`docs/STABILITY.md`](docs/STABILITY.md) for semver and module stability levels.

## [1.0.0] - 2026-06-29

### Added

- MIT [`LICENSE`](LICENSE) and this changelog.
- Open-source preparation docs: [`docs/OPEN_SOURCE_RELEASE.md`](docs/OPEN_SOURCE_RELEASE.md), [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md), [`docs/STABILITY.md`](docs/STABILITY.md), [`docs/EXTENSIBILITY.md`](docs/EXTENSIBILITY.md), [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md), [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).
- [`CONTRIBUTING.md`](CONTRIBUTING.md) with Phase 1 contribution policy.
- [`scripts/doctor.sh`](scripts/doctor.sh) environment self-check.
- GitHub Issue / PR templates under [`.github/`](.github/).
- README product screenshots and unsigned macOS DMG distribution via GitHub Releases (D31).

### Changed

- **First public release** at **`1.0.0`** (semver starting point for open source and DMG distribution).
- **Documentation aligned with implementation (T0):** API keys are stored in local `models.json` with `chmod 600`; macOS Keychain migration is planned for T2 (OSR-13), not claimed as shipped.
- `experiments/pty_poc/runs/` is local-only (gitignored); removed committed runs that contained machine-specific paths.

### Security

- No runtime security changes in this release — Sidecar auth, Keychain, and CLI permission gating remain on the T1/T2 roadmap ([`docs/OPEN_SOURCE_RELEASE.md`](docs/OPEN_SOURCE_RELEASE.md)).
