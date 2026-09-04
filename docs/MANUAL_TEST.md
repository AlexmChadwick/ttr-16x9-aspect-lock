# In-game verification checklist

TTR Aspect Lock cannot launch or test Toontown Rewritten for you. Use this
short manual pass after a successful `install`.

1. Fully quit TTR before applying the setting; make sure no launcher/client process remains.
2. Run `ttr-aspect-lock status` and confirm the selected settings file reports `1.7777777778`.
3. Launch TTR normally. Keep any overlays or unrelated modifications out of this
   test so the result is easier to diagnose.
4. In the login screen, verify the visible scene is centered and the expected side/top/bottom bars match your display family in [the resolution matrix](RESOLUTION_MATRIX.md).
5. Enter a safe area and open the Shticker Book, map, friends list, options, battle UI, and a dialog-heavy interface. Check that HUD corners, text, buttons, and mouse hit targets line up visually.
6. Resize or change full-screen/windowed mode once, then revisit the same screens. If the client changes the setting, quit and run `status` again.
7. If anything looks wrong, quit the game and run `ttr-aspect-lock restore --latest`
   (or `uninstall --latest`) before reporting the issue. Include your OS,
   resolution, display mode, client build/date, and the redacted output of
   `status --verbose`.

Pass criteria: centered 16:9 presentation, usable UI, and no unexpected settings loss. A cosmetic difference that follows a TTR update is a client behavior to report to TTR; this tool only manages the setting.
