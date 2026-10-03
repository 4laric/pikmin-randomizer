# Four-course surface travel candidate (#1051)

The candidate stages Valley of Repose, Awakening Wood, Perplexing Pool and
Wistful Wild as four distinct native story destinations. The native course menu
uses their names and ordinary `MapSelect` → `NewPikiGame` transitions. Static water
and topology ownership follow the selected course. Existing tutorial preview and
ordinary Pikmin 1 launches retain their entrypoints.

An invisible fifth record preserves native player-state and card bookkeeping,
which dereferences five stage nodes. It has no generator schedules or playable
destination. Startup requires ordered IDs/indices 0–3 for visible courses and
the exact reserved invisible ID/index 4 record. This does not make ordinary
Pikmin 1 saves compatible with the candidate; its cards remain isolated.

This is an implementation increment, not full playable Pikmin 2 acceptance.
Story unlocks are open for travel testing. Original retail enemies, treasures,
plants and objects remain the original-course provider lane's work. The candidate
uses explicit native Pikmin 1 ship/Red Onion adapters at retail landing anchors
and twenty-red fixture squads on first visits. Materials are approximate and
missing render normals use the existing rigid-bake compute policy. Pool's
zero-area source collision face 2659 is omitted from native collision only;
the immutable source bundle and explicit native-to-source face mapping remain.
Water rendering and dynamic lowering are pending.

From this root checkout, use `scripts/stage_pikmin2_campaign_surfaces.py` with
`--assets <legal-P1-assets>`, `--output <new-private-output>` and all four course
arguments: `--tutorial <bundle> --tutorial-identity <pin>` and equivalent
`--forest`, `--yakushima`, `--last` pairs. Each pin is the SHA-256 of its original
`surface-receipt.json`. All bundle contents are verified before staging. The
stager replaces the P1 stage table to avoid ambiguous IDs, generates per-course
terrain/water/routes, records file hashes and writes `TRAVEL_ACCEPTANCE.txt`.

Launch from the root checkout:

```powershell
py -3.12 scripts/play_pikmin2_campaign_surfaces.py --run <output>/run --exe <private-build>/bin/nectar.exe --course tutorial
```

The launcher checks staged hashes and preserves existing native saves. Native
cards use `save/p2-campaign` inside the private run. Fresh-process resume is
pending; the launcher refuses to start a fresh campaign over an existing card
directory. Use another staged output for another fresh test.

Direct acceptance: observe the centered 960×540 window and twenty live Reds;
move/whistle/throw on the actual terrain, end the day through the ordinary pause
menu, then select each named course with the main stick and A. On the default
keyboard bindings, Enter opens pause; W/S navigates both menus and Space confirms. Confirm the corresponding
terrain and `P2_SURFACE_TRAVEL` log, and revisit a previously visited course.
Record actual day-end/card-write behavior and any failed landing. Conversion,
unit tests and compile success do not establish these gameplay observations.

Validation evidence lives under ignored `output/p2-travel-*`. Four-course staging
reproduced byte-identical terrain outputs in two fresh runs. Native selector
tests cover all destinations, mismatched stage paths and incompatible flags;
independent review found and corrected non-tutorial shipless landing targets.
Full source-provider integration, story progression and actual saved/resumed
four-course campaign acceptance remain open.
