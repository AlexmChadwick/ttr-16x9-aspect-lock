# Frequently asked questions

## What does the tool do?

It changes only `video.forced-aspect-ratio` in a player-owned TTR
`settings.json`, setting it to `1.7777777777777777` (Python's `16 / 9`). Before
an actual change it copies the complete file to a timestamped backup. It has no
runtime component and does not edit, inspect, inject into, or distribute TTR
client files.

## Is 16:9 guaranteed to fix ultrawide UI or work on every client update?

No. The setting is experimental and the TTR client controls rendering, scaling,
bar appearance, input behavior, and persistence of video options. A centered
16:9 frame is the intended request, not a promise of a specific visual result.
Check the examples in [RESOLUTION_MATRIX.md](RESOLUTION_MATRIX.md), then follow
[MANUAL_TEST.md](MANUAL_TEST.md) after applying it.

## Does it affect performance, mouse mapping, anti-cheat, or TTR rules?

The utility is not running while you play, so it has no direct runtime overhead
of its own. It does not use injection, hooks, memory access, network traffic, or
binary modification. That design does not substitute for TTR's current terms,
support guidance, or anti-cheat policy; review those before use and do not use
this tool to bypass game restrictions. If input or UI alignment looks wrong,
quit the game and restore the backup.

## Where is `settings.json`?

Run:

```bash
ttr-aspect-lock discover --verbose
```

The tool checks known per-user locations and both direct and `resources/`
variants. It does not search arbitrary disks or create a file. If yours is not
found, pass its exact location with `--settings PATH`; see
[INSTALL.md](INSTALL.md#automatic-locations).

## Why did the setting revert or why is the game unchanged?

Fully exit and relaunch TTR after applying the change, then run `status`. TTR
may rewrite settings when you change display modes or when it updates. If the
stored value is no longer 16:9, close the game before applying it again. If the
stored value is correct but the result is not useful, restore the backup rather
than repeatedly changing settings while TTR is running.

## How do I undo it?

Close TTR, then restore the newest backup for the selected settings file:

```bash
ttr-aspect-lock restore --latest
# Equivalent alias:
ttr-aspect-lock uninstall --latest
```

For a particular backup, use `restore --backup PATH`. `--dry-run` previews a
restore without writing. Windows wrapper examples are in [INSTALL.md](INSTALL.md#windows-powershell-wrappers).

## Can a Content Pack lock the aspect ratio instead?

**No.** Official TTR Content Packs (`.mf` in `resources/`) can change textures,
audio, fonts, and the cursor only. They **cannot** change aspect ratio, UI
layout, or models. There is no official plugin API for this. Editing
`settings.json` (`video.forced-aspect-ratio`) is intentional and experimental.

This project ships **no** content pack and no proprietary TTR assets. Keep any
separate cosmetic package subject to TTR's current rules, and do not add client
files to this utility or its release archive.

## Is this MIT licensed?

Yes. See [LICENSE](../LICENSE).
