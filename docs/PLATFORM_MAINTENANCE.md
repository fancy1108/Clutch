# Platform maintenance — macOS & Windows

> Layer 2 governance · 铁律见 [`CLAUDE.md`](../CLAUDE.md)。  
> 定义 **谁改什么**、**共享资源如何同步**，避免跨平台 UI 互相踩脚。

## Maintainers

| Platform | Primary | Scope |
|----------|---------|-------|
| **macOS** | `@fancy1108` | Default workspace chrome, DMG release, macOS UX |
| **Windows** | `@996wuxian` | Windows PTY/sidecar, MSI/NSIS, Windows workspace chrome |

## File boundaries

### Shared (both review — label PR `platform:shared`)

| Path | What |
|------|------|
| `apps/desktop/src/platform/chrome/navConfig.ts` | Nav icons, label keys, test ids |
| `apps/desktop/src/components/**` (logic) | Business UI; layout classes should delegate to platform chrome |
| `services/orchestrator/src/interactive_pty_runtime.py` | PTY manager (platform branches inside OK) |

### macOS-only

| Path | What |
|------|------|
| `apps/desktop/src/platform/chrome/sidebar/SidebarCollapsedRail.macos.tsx` | Collapsed sidebar rail |
| `apps/desktop/src/platform/chrome/sidebar/SidebarToggle.macos.tsx` | Sidebar fold control placement (mac) |

### Windows-only

| Path | What |
|------|------|
| `apps/desktop/src/platform/chrome/sidebar/SidebarCollapsedRail.windows.tsx` | Collapsed sidebar rail |
| `apps/desktop/src/platform/chrome/sidebar/SidebarToggle.windows.tsx` | Sidebar fold control placement (win) |
| `services/orchestrator/src/windows_pty.py` | WinPTY backend |

**Rule:** Do **not** change the other platform’s `*.macos.tsx` / `*.windows.tsx` without owner review.

## Changing icons or nav items

1. Edit **`navConfig.ts` only** (single source of truth).
2. Open PR with label **`platform:shared`** — CODEOWNERS will request both maintainers.
3. If a new nav entry needs different chrome on mac vs win, update **both** `SidebarCollapsedRail.*.tsx` in the same PR.

## PR checklist

```markdown
- [ ] UI chrome only in `platform/chrome/**` (not scattered `if (windows)` in shared components)
- [ ] Shared nav/icon change → `navConfig.ts` + `platform:shared`
- [ ] mac-only chrome → `platform:macos` (Windows maintainer: no action)
- [ ] Windows-only chrome → `platform:windows` (macOS maintainer: no action)
- [ ] `./scripts/verify.sh` passed
```

## Runtime detection

Desktop: `invoke('clutch_host_os')` → `"macos"` | `"windows"` | …  
Hook: `apps/desktop/src/platform/hostOs.ts`

Root shell may set `data-platform={hostOs}` for CSS overrides when needed.

## History

- **2026-07-04** — Introduced after [#30](https://github.com/fancy1108/Clutch/pull/30) (Windows interactive PTY + workspace chrome). Follow-up: platform chrome split (档 A).
