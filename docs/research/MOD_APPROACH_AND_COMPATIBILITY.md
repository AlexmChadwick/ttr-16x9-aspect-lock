# Research: TTR aspect locking, content packs, and safety boundaries

**Research date:** 2026-09-04  
**Scope:** public documentation and community-maintained sources only. No TTR
client source, binary modification, or reverse-engineering was used.

## Decision

The least-invasive implementation is a **local `settings.json` edit** which sets
`video.forced-aspect-ratio` to the desired ratio (for 16:9, `1.7777777777777777`).
It should be presented as an opt-in convenience tool, not as an official TTR
feature or a guaranteed ultrawide-UI fix. The installer must back up the file and
offer an exact restore.

This decision deliberately excludes DLL injection, executable/phase-file patching,
memory editing, custom network clients, and anti-cheat bypasses. TTR's terms prohibit
third-party software used to modify the game, cheat, or gain an advantage, and also
prohibit connecting unofficial clients. The terms can change, so users remain
responsible for reviewing the current terms and using the unmodified official client.
[TTR Terms of Service](https://www.toontownrewritten.com/play/terms-of-service/legalese)

## What the evidence says

| Topic | Evidence and confidence | Project implication |
| --- | --- | --- |
| `settings.json` exists in the install directory and has a `video.forced-aspect-ratio` key. | The community-maintained TTR Wiki documents `settings.json` in the install directory and shows the key with default `0.0`. This is a useful configuration reference, but is not an official support promise. [Wiki: settings.json](https://toontownrewritten.wiki/Settings.json) | Locate an existing file; preserve its JSON and only update this one key. Do not create a client-side plugin. |
| A nonzero aspect value has been used for a classic 4:3 lock. | The Classic Pack's public README says that, as of 2023-12-05, the option was unsupported/experimental and reports `1.3333333` as a 4:3 lock, with `0.0` as the disabled value. This is a third-party project, not TTR documentation. [The Classic Pack README](https://github.com/toontownlpz/The-Classic-Pack) | `16 / 9 = 1.7777777777777777` is the analogous numeric value. Label it experimental and require a restart/test; do not claim official support. |
| Native ultrawide resolution is distinct from an aspect lock. | WSGF reports native monitor-resolution selection and native ultrawide support beginning with the historical Options Update (`v2.3.0`), and lists 21:9/32:9 examples. It tested `v2.3.3`, so this is independent community evidence rather than a current compatibility certification. [WSGF profile](https://www.wsgf.org/dr/toontown-rewritten/en) | Do not change the selected display resolution. The lock is for players who prefer a 16:9 presentation on a wider display. |
| Content Packs are an officially documented, visual/audio customization channel. | TTR's FAQ says packs are `.mf` Multifiles placed in the automatically-created `resources` directory; they may alter textures, music, sound effects, and visuals. Packs can be enabled/disabled and ordered in the Video options. TTR cautions that a large number of packs has not been fully tested and may be unstable. [TTR Content Packs FAQ](https://www.toontownrewritten.com/help/faq/content-packs) | This project does not need a content pack. Never install one merely to set an aspect ratio. If a companion pack is ever added, make it optional and document load-order/compatibility risks. |
| Content Packs are limited; they do not replace arbitrary gameplay assets. | The community TTR Wiki says textures, audio, fonts, and cursor can change but models and NPC dialogue cannot. The Classic Pack independently reports that TTR does not allow model replacement by content packs. These are community sources, so treat the detail as informative rather than a contractual specification. [Wiki: Content pack](https://toontownrewritten.wiki/Content_pack) [Classic Pack limitation](https://github.com/toontownlpz/The-Classic-Pack) | Do not propose a content-pack solution for UI layout, models, collision, gameplay, or networking. No `.mf` is shipped by this project. |

## Important caveat: what “forced aspect ratio” will look like

Public sources found here establish the key and a reported 4:3 use, but **do not
authoritatively specify** whether a 16:9 value letterboxes, pillarboxes, crops, or
how every TTR screen anchors its GUI. Therefore claims such as “it fixes stretched
ultrawide UI” must remain conditional until validated on supported client builds and
displays.

The safe user-facing claim is:

> Sets TTR's experimental `video.forced-aspect-ratio` preference to 16:9. On an
> ultrawide display, verify the title screen, Options, in-game HUD, battle UI, and
> cutscenes yourself; restore the backup if the result is not preferred.

Suggested validation matrix:

- Run the official client at one 16:9 resolution and at least one 21:9 and 32:9
  resolution available to the monitor.
- Capture the title/Pick-a-Toon screen, a playground HUD, battle HUD, Options, and
  a cutscene both before and after the change.
- Confirm that the setting persists after closing and relaunching TTR. If TTR rewrites
  or ignores it, restore the backup and treat that client version as unsupported.
- Keep display resolution, other video preferences, and content-pack state fixed while
  comparing results. Disable extra packs when troubleshooting, because TTR documents
  pack ordering and warns that many installed packs may be unstable.

## Compatibility and distribution constraints

- Use only the **official launcher/client**. The current Terms list unofficial clients
  and third-party software that modifies the game, cheats, or gives an advantage as
  prohibited. A configuration helper cannot promise TTR approval; it should not
  conceal its action or attempt to evade client checks.
- Treat `forced-aspect-ratio` as **unsupported/experimental** based on the Classic
  Pack's 2023 report. TTR may remove, rename, or change its semantics in later builds.
- Do not redistribute TTR executables, phase files, assets, accounts, or credentials.
  A configuration utility should contain only its own code and documentation.
- Do not make claims that an aspect lock affects opponents, grants an advantage, or
  repairs every UI defect. It is a local presentation preference.
- Content Packs are third-party files even though TTR documents their use. TTR states
  it neither owns nor is responsible for material on the partner-operated pack site;
  only obtain packs from sources the user trusts. [TTR Content Packs FAQ](https://www.toontownrewritten.com/help/faq/content-packs)

## Source quality notes

1. **Official TTR FAQ and Terms** are primary sources for the documented content-pack
   workflow and conduct boundaries. The Terms page is versioned by TTR and may change.
2. **TTR Wiki, Classic Pack, and WSGF** are secondary/community sources. They provide
   useful evidence for the JSON key, the 4:3 value, model limitation, and historical
   ultrawide behavior, but do not establish official support or present-day guarantees.
3. No primary public source located in this research explicitly documents a 16:9 value
   or the exact rendering/GUI behavior at that value. This is why this project must
   test and caveat its advertised result.
