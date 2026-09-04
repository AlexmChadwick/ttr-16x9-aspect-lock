# What a 16:9 aspect lock means

TTR Aspect Lock asks the client to present within a 16:9 frame through the experimental `video.forced-aspect-ratio` setting. It does **not** add a new display mode, alter game files, or guarantee that every individual UI element behaves identically in every client build.

When the physical display is wider than 16:9, the expected result is pillarboxing: unused vertical bands at the left and right. When it is taller/narrower than 16:9, the expected result is letterboxing: unused horizontal bands at the top and bottom. On an exact 16:9 display, no bars are expected.

| Display family | Example | Native ratio | Expected 16:9 frame | Approx. unused area |
| --- | ---: | ---: | --- | --- |
| 16:9 | 1920×1080 | 1.7778 | Fits exactly | None |
| 16:10 | 1920×1200 | 1.6000 | Letterbox top/bottom | 60 px each at 1920×1200 |
| 21:9 | 3440×1440 | 2.3889 | Pillarbox left/right | 440 px each at 3440×1440 |
| 32:9 | 5120×1440 | 3.5556 | Pillarbox left/right | 1,280 px each at 5120×1440 |
| 4:3 | 1600×1200 | 1.3333 | Letterbox top/bottom | 150 px each at 1600×1200 |

The examples assume the client retains the entire display area and centers the forced frame. Actual bar color and whether a particular client view crops or scales are client-controlled; verify in game after applying.

## How the numbers are calculated

For a display `W×H`, the desired frame is centered:

- If `W/H > 16/9`, frame width is `H × 16/9`; each side band is `(W - frame width) / 2`.
- If `W/H < 16/9`, frame height is `W ÷ (16/9)`; each top/bottom band is `(H - frame height) / 2`.

Fractional pixels are rounded by the client/display pipeline, so these figures are planning estimates.

## Visual framing & FAQ

- See [DIAGRAMS.md](DIAGRAMS.md) for 21:9 and 32:9 visual diagrams, percentage breakdowns, and UI safety zones.
- See [FAQ.md](FAQ.md) for answers on anti-cheat safety, in-game behavior, and multi-monitor setups.
