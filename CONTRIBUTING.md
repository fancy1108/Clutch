# Contributing to Clutch

Thank you for your interest in Clutch. This document explains how to contribute and what to expect when you open a pull request.

**Related:** [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md) · [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) · [`docs/EXTENSIBILITY.md`](docs/EXTENSIBILITY.md)

---

## Branch workflow

| Branch | Purpose |
|--------|---------|
| **`dev`** | Integration — **open all pull requests here** |
| **`main`** | Release / stable — maintainer merges from `dev` at release time |

Fork the repo from **`dev`**, branch off **`dev`**, and set the PR **base branch to `dev`**. Do not open feature PRs against `main`.

---

## Contribution Philosophy

Clutch is currently maintained primarily by its original author.

While all contributions are welcome, **acceptance of pull requests is at the sole discretion of the maintainer.**

To keep the project coherent and maintainable, the maintainer may decline pull requests that:

- significantly increase maintenance burden
- change core architecture without prior discussion
- alter the project's goals or philosophy
- introduce features outside the current roadmap

Please open an Issue or Discussion before working on large features.

> **Open source means anyone can contribute code; it does not mean every contribution must be merged.** The maintainer always retains final decision authority.

---

## Phase 1 — Early open source (current)

During the **first phase after going public**, the bar for merging is intentionally conservative:

| Default **decline** | Default **welcome** |
|---------------------|---------------------|
| Large feature PRs | Bug fixes |
| Architecture rewrites | Documentation improvements |
| Product-direction changes | Test additions |
| Features outside [`PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) | Small, focused optimizations |

This phase ends when announced in [`CHANGELOG.md`](CHANGELOG.md) or [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md). Until then, **please do not spend weeks on a large PR without prior maintainer agreement.**

---

## Before you open a PR

1. **Search existing Issues** — avoid duplicates.
2. **Read scope** — [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md) (Goals / Non-Goals).
3. **Large or architectural work** — open an Issue first; wait for maintainer feedback.
4. **One PR, one topic** — keep diffs reviewable.
5. **Run checks locally:**

   ```bash
   ./scripts/doctor.sh    # environment
   ./scripts/verify.sh    # build + tests + doc drift
   ```

6. Use the [pull request template](.github/pull_request_template.md).

---

## What merges easily (Phase 1)

- Reproducible bug fixes with tests when behavior changes
- Doc fixes (README, `docs/*`, comments that clarify public behavior)
- Tests that cover existing behavior (no mock orchestration — see [`CLAUDE.md`](CLAUDE.md))
- Small performance or UX fixes with clear scope

---

## What needs an Issue first

- New HTTP/WebSocket API surface
- Workflow JSON Schema changes
- New CLI adapters or Model Providers
- Anything touching LangGraph compiler / engine router (see [`docs/EXTENSIBILITY.md`](docs/EXTENSIBILITY.md))
- Features listed as Non-Goals in [`docs/PROJECT_SCOPE.md`](docs/PROJECT_SCOPE.md)

Maintainer may close such PRs with a link to this file — **not a judgment on quality**, but on project phase and coherence.

---

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml). Include:

- `./scripts/doctor.sh` output
- Steps to reproduce
- **Redact API keys** — never paste `models.json` or session dumps

Installation problems: [installation issue template](.github/ISSUE_TEMPLATE/installation_issue.yml).

Security vulnerabilities: **do not** open a public Issue. See [`SECURITY.md`](SECURITY.md) and the [security report template](.github/ISSUE_TEMPLATE/security_report.md).

---

## Code expectations

- Follow existing style in touched files.
- Frontend: `apps/desktop/src` only; no mock orchestration (`setTimeout`, fake WS state).
- Backend: `services/orchestrator/src`; LangGraph remains the orchestration SSOT.
- Commits: focused; message explains **why**.

Maintainers run `./scripts/verify.sh` before merge when changes touch application code.

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see root `LICENSE` when published).

---

## Questions

Open a GitHub Issue for bugs and small questions. For direction or partnership, use Issues (or Discussions if enabled) — not unsolicited mega-PRs.
