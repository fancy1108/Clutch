Clutch is **unsigned** (no Apple notarization yet — see D31). Gatekeeper warnings are **expected**, not malware or a corrupt download.

**You may see:** “cannot verify developer”, “Clutch is damaged”, or double-click does nothing.

**Fix (pick one):**

1. **Finder:** Applications → right-click `Clutch.app` → **Open** → **Open** again.
2. **Terminal (one-time):** `xattr -cr /Applications/Clutch.app && open -a Clutch`

More: [`docs/INSTALL.md`](docs/INSTALL.md) §2–§4 · [`docs/DATA_AND_PRIVACY.md`](docs/DATA_AND_PRIVACY.md)
