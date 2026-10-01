# Native floor 3 engineering survey (#311)

Historical #311 reproduction below targets frozen root `8ce3fe9`. The current
survey helper requires the [#317 native entry APIs](PIKMIN2_BEASTS_FLOOR3_ENTRY.md);
use that follow-up's private native build when generating the current helper.

Owner: Codex using shared 4laric account. Root base: frozen #309,
`b472aef777f13b51aec4b501a6caddff72dadfac`. This validates native captain movement
through the five-unit engineering assembly. It does not enable floor-three
campaign entry, treasure carrying, hazards or descent.

Two fresh native processes restored ten Reds and ten Purples with mixed maturity
and captain health 0.625. Each traversed 12 ordered controller goals, crossing
block-room/corridor and corridor/north-room seams in both directions and returning
to the starting area. Native ground distance stays below five units at every
survey update after initialization. The fixture selects controller directions;
it never teleports the captain or alters movement physics. All 20 survivors,
their species/maturity and health remain unchanged. Rewards stay zero and repairs
remain unchanged.

The actual geometry capture was inspected: the block room and Red/Purple party
render, but source materials remain approximate, camera occlusion is visible and
the P1 preview UI persists. This is not visual-fidelity or natural-play sign-off.
The party survives the survey; individual squad seam traversal and carrying are
not asserted.

## Stage API and launch boundary

`experimental.pikmin2_beasts_floor3_runtime.stage(assets, assembly, purple, pod,
output, party)` returns a fresh UUID run directory. `party` is exactly
`{"health": 0.625, "squad": [{"species": "red" or "purple", "maturity": 0..2}, ...]}`,
with 20 entries. Inputs are `Path` values; `assembly` is the frozen #309 package.
The returned `survey.json` records all overridden inputs, assembly hash, anchors,
goals and the party. `run(exe, directory)` rejects reused runs, validates hashes,
runs the child, and records `acceptance.json` and `native.log`.

**This API is not an authorized campaign launcher.** It uses existing
`P2_CAVE_ENTRY_1` with engineering floor tag 2 solely to restore the party; the
geometry is floor 3. `campaign_entry=false`, `native_ready=false` and
`party_restore_protocol_floor=2` are explicit. No checkpoint token from the
campaign ledger is accepted or consumed, and no native handoff is emitted.
Future supervisor integration must use a distinct reviewed floor-three contract.

## Fixture and reproduction

The fixture is generated externally from the frozen native room fixture by three
checked text anchors and a new survey include. It reuses the source includes,
controller and survivor snapshot helpers. No native source files were edited.
The fixture builder reused the completed private production build at native
`e23986231d81b6f275d9fd900610c1bd82105b31`; Ninja freshness remained no-work before
and after linking. The provenance does not certify historical object compilation.

From private root `output/p2-beasts-floor3-track`:

```powershell
python -m experimental.pikmin2_beasts_floor3_runtime fixture `
  --source ../native-cave-lane/tools/preview_p2_room.cpp `
  --output output/floor3-311/new-fixture/survey.cpp
$env:PATH='C:/msys64/mingw64/bin;'+$env:PATH
python -m scripts.build_pikmin2_fixture `
  --source ../native-cave-lane --build ../native-cave-lane/build-cave `
  --fixture output/floor3-311/new-fixture/survey.cpp `
  --output output/floor3-311/new-linked `
  --expected-native-head e23986231d81b6f275d9fd900610c1bd82105b31
python -m experimental.pikmin2_beasts_floor3_runtime stage `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --assembly output/floor3-306/final-a `
  --purple ../../output/pikmin2-purple113/import-05 `
  --pod ../../output/pikmin2-pod111/import-02 `
  --party PATH_TO_PARTY_JSON --output output/floor3-311/new-runs
python -m experimental.pikmin2_beasts_floor3_runtime run `
  --exe output/floor3-311/new-linked/fixture.exe --stage RETURNED_RUN_DIRECTORY
```

Fixture executable SHA256:
`f3c917d1fa58fe7b50864717217bb3baae10acf7b161e4075a4cdba346cafdb4`.
Provenance: `output/floor3-311/linked/provenance.json`.

Final runs below both passed; their `acceptance.json` records unchanged input and
executable hashes. Full hashes are in `output/floor3-311/verification.json`.

| Run under output/floor3-311/final | Native log SHA256 |
|---|---|
| c68963d58b0c43909c28c31273b8e8fd | `71e35dfc337ef77ccfe00eecfc6c49043616cf951a3170ee264cf86964fd8fb7` |
| 7aa73e4bda26497d8e8c7b9de83e484e | `1a14a925b2f95894305d0a76ccf0d218cd3b8123afc531cc4b20d76e3677a31c` |

The first probe also completed native walking but failed host acceptance because
the reused party parser expected different phase names. The host now explicitly
maps already-validated survey phase markers into that strict parser; both final
runs were fresh after this fix. The original probe remains preserved.

12 tests and 28 subtests passed across the new survey, party restoration,
floor-three assembly and navigation suites. Tests reject unordered/distant/
ungrounded points, changed party/health, injected rewards/failures, duplicate
markers and changed fixture anchors. No shared build, player package or save was
modified. Hiba, plants, both treasures, actual cave exit, carrying and campaign
resume remain open.
