# Release snapshots (`docs/releases/`)

> **Purpose:** Freeze **what the product was** at each major/minor version.  
> **Current product truth:** [`PRODUCT_INTRO.md`](../PRODUCT_INTRO.md) — always describes the latest shipped behavior.  
> **Per-change log:** [`CHANGELOG.md`](../../CHANGELOG.md) — user-facing deltas between versions.  
> **GitHub Release body:** CI runs [`scripts/render-release-notes.sh`](../../scripts/render-release-notes.sh) — the matching `## [x.y.z]` section becomes **What's in this release** at the top of the Release page; install/Gatekeeper fragments follow below.

## When to create a file

| Trigger | Action |
|---------|--------|
| First public **major** or **minor** tag | Add `vX.Y.md` summarizing capabilities at ship time |
| Patch tag only | Usually **no** new snapshot — `CHANGELOG.md` entry suffices |
| Feature removed or reintroduced across versions | Update **new** snapshot; do not rewrite old files |

## File template

```markdown
# Clutch vX.Y — Product Snapshot

**Released:** YYYY-MM-DD  
**Tag:** vX.Y.Z  
**Changelog:** [CHANGELOG § X.Y.Z](../../CHANGELOG.md)

## What this version is

(2–4 sentences positioning.)

## Shipped capabilities

(Bullet list — mirror PRODUCT_INTRO at release time, not aspirational.)

## Not included / known limits

(Explicit non-goals for this version.)
```

## Index

| Version | Snapshot | Notes |
|---------|----------|-------|
| 1.2.1 | [`v1.2.1.md`](./v1.2.1.md) | **macOS only** · Chat/Design/Models hotfix · Sidecar hotpatch client (D37) |
| 1.2.0 | [`v1.2.0.md`](./v1.2.0.md) | **macOS only** · Design mode (D36) · ZCode CLI · Agent Log step tags |
| 1.1.2 | [`v1.1.2.md`](./v1.1.2.md) | **macOS only** · MiMo Code CLI · Cursor Agent CLI · Terminal Orchestra fixes |
| 1.1.1 | [`v1.1.1.md`](./v1.1.1.md) | Windows interactive PTY · platform chrome split · #30 |
| 1.1.0 | [`v1.1.0.md`](./v1.1.0.md) | Terminal Orchestra · Windows polish · CodeBuddy · OpenCode Zen · Agnes Video |
| 1.0.3 | [`v1.0.3.md`](./v1.0.3.md) | Hybrid pool queue · OpenCode · brand refresh · Ollama fix |
| 1.0.2 | [`v1.0.2.md`](./v1.0.2.md) | Windows + macOS in-app update + #18 sidecar fix |
| 1.0.0 | [`v1.0.md`](./v1.0.md) | First public DMG + open source |

## Governance

- Snapshots are **historical** — edit only to fix factual errors, not to reflect later releases.
- Agents: do not append roadmap or backlog items here; use `memory/ROADMAP.md` / `memory/BACKLOG.md`.
