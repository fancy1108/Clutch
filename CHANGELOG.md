# Changelog

All notable changes to Clutch are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

**Version policy:** While `0.x`, breaking changes may land in any release — see [`docs/STABILITY.md`](docs/STABILITY.md).

## [0.1.0] - 2026-06-27

### Added

- MIT [`LICENSE`](LICENSE) and this changelog.
- Open-source preparation docs: [`docs/OPEN_SOURCE_RELEASE.md`](docs/OPEN_SOURCE_RELEASE.md), [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md), [`docs/STABILITY.md`](docs/STABILITY.md), [`docs/EXTENSIBILITY.md`](docs/EXTENSIBILITY.md), [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md), [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md).
- [`CONTRIBUTING.md`](CONTRIBUTING.md) with Phase 1 contribution policy.
- [`scripts/doctor.sh`](scripts/doctor.sh) environment self-check.
- GitHub Issue / PR templates under [`.github/`](.github/).

### Changed

- Project version `0.0.0` → **`0.1.0`** (semver starting point for open source).
- **Documentation aligned with implementation (T0):** API keys are stored in local `models.json` with `chmod 600`; macOS Keychain migration is planned for T2 (OSR-13), not claimed as shipped.
- `experiments/pty_poc/runs/` is local-only (gitignored); removed committed runs that contained machine-specific paths.

### Security

- No runtime security changes in this release — Sidecar auth, Keychain, and CLI permission gating remain on the T1/T2 roadmap ([`docs/OPEN_SOURCE_RELEASE.md`](docs/OPEN_SOURCE_RELEASE.md)).
