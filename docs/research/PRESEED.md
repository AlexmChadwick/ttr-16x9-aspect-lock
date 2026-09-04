# Pre-seeded research (executor; verify/expand)

## Approach decision
**No official TTR code plugin API.** Client has anti-injection safeguards. Do not inject DLLs or patch binaries.

**Real player-supported approaches:**
1. `settings.json` → `video.forced-aspect-ratio` (experimental/unsupported, added ~Dec 5 2023 per wiki release notes / Classic Pack README)
2. Content Packs (`.mf` in `resources/`) — textures/audio/fonts/cursor only; cannot replace models

## forced-aspect-ratio
- `0.0` = disabled (use native window aspect)
- `1.3333333` ≈ 4/3 classic lock (documented by toontownlpz Classic Pack)
- **This project target:** `1.7777777777777777` = 16/9 exactly (or `16/9` float)
- Effect (expected): letterbox/pillarbox the rendered view so UI layout matches 16:9 safe frame on 21:9/32:9 ultrawide

## settings.json locations (typical; confirm in docs)
- Windows: `%LOCALAPPDATA%\Toontown Rewritten\settings.json` or install dir
- macOS: `~/Library/Application Support/Toontown Rewritten/settings.json`
- Linux: `~/.local/share/Toontown Rewritten/settings.json` or install prefix

## Sources
- https://raw.githubusercontent.com/toontownlpz/The-Classic-Pack/main/README.md (forced-aspect-ratio 4:3)
- https://toontownrewritten.wiki/Release_notes_(2023) (unsupported aspect ratio value)
- https://www.toontownrewritten.com/help/faq/content-packs
- https://www.wsgf.org/dr/toontown-rewritten/en (native ultrawide resolution support since v2.3.0)
- Panda3D aspect2d / DisplayRegion docs (engine background; not for injection)

## Policy
Do not clone proprietary client. Ship installer + docs + tests + zip.
