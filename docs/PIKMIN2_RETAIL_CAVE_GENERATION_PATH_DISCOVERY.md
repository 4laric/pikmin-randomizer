# Retail cave generation + cave-save engine path discovery (issue #771)

Lane `retail-cave-generation-path-discovery`, generation 2. Diagnosis only:
read-only source mapping, no engine/file edits, no ADMIT, never an engine
unblock. Downstream consumers: forest1-p1 (#154, blocked), yakushima4-p1
(#161, blocked), tutorial2-later-floors (#747, blocked).

## Verdict: VERIFIED ABSENCE at all three consumer pins and canonical head

No retail engine cave-generation symbols and no cave-save symbols exist in
`native/pc_port` + `native/tools` at any scanned tree. Searched symbol sets:

- retail-gen: `CaveInfo`, `FloorInfo`, `RandomMapCreator`, `TileMap`,
  `Cave::`, `Oeoe::`, `ogCave` — zero hits everywhere.
- cave-save: `ogSave`, `SaveData`, `writeSave`, `saveFile`, `SaveMgr`,
  `saveMgr`, `CaveSave`, `saveCave` — zero hits everywhere.

Scanned trees (adapter markers `P2_RETAIL_CAVE_PATH_ABSENT retail-gen`,
`P2_RETAIL_CAVE_PATH_ABSENT cave-save`,
`P2_RETAIL_CAVE_PATH_VERDICT absence-verified` on each):

| Tree | Pin | Verdict |
|---|---|---|
| `.../caves-forest/prepared/forest1-p1-native` (#154) | `78e8ce9b` | absence-verified |
| `.../caves-yakushima/prepared/yakushima4-p1-native` (#161) | `88188a1e` | absence-verified |
| `.../caves-tutorial/prepared/tutorial2-later-floors-native` (#747) | `8c66708a` | absence-verified |
| canonical `native/` (reference) | `a95040b6` | absence-verified |

## Nearest footholds (randomizer-side, NOT retail; file/symbol evidence)

1. `pc_port/pc_p2_cave_generate.h` / `.cpp` (lane cave-generate-provider,
   #129 done): header-inline policy reading a `p2-cave-generate.txt`
   sidecar manifest, emitting `P2_CAVE_GENERATE_*` markers; opt-in only.
   Symbol: `p2_cave_generate::rotateTurn`, entry
   `pc_p2_cave_generate_run()`. Sidecar-driven randomizer generation —
   not a retail engine path.
2. `pc_port/pc_randomizer.h` / `.cpp`, `pc_randomizer_probe.cpp`:
   `generatorId`/`generator_id` plumbing (generator selection only).
3. `pc_port/pc_p2_cave.cpp` (+ `.h`, `pc_p2_cave_anchor.h`,
   `pc_p2_cave_nav_diagnostics.h`): staging, `pc_p2_cave_floor()`,
   checkpoint-sidecar parse, `P2_CAVE_READY` markers. The only
   save-adjacent text is a marker string `"Saves at floor boundaries"`
   (`pc_p2_cave.cpp:189`); there is no save implementation.
4. `tools/p2_cave_guarded_boot_fixture.cpp`,
   `tools/preview_p2_cave.inc`, `tools/test_p2_cave_anchor.cpp`:
   guarded boot fixture + anchor unit test (no generation/save logic).

## Engine follow-on: no live owner — new scope or explicit deferral

All #129/#132 lanes are done; zero live lanes exist on either issue, so
nothing is duplicated by this diagnosis. Porting the retail Cave
generation + cave-floor save paths needs a NEW native engine scope
(suggested: `native/pc_port/pc_p2_cave_retail.{h,cpp}` + `pikmin_pc`
membership, referencing the research checkout read-only) under #186
review with a leased build and guarded fixture proof — or an explicit
deferral to authored-geometry/randomizer generation
(`yakushima4-authored-geometry-native` #682 pattern) by
integrator/family disposition. This packet does not unblock the engine;
the three consumers stay blocked until that decision lands.

## Method and evidence

- Adapter: `experimental/pikmin2_retail_cave_generation_path_discovery.py`
  (read-only walk of `pc_port` + `tools`, marker grammar above, exit 2
  fail-closed on missing/unreadable input; stdlib only).
- Tests: `tests/test_pikmin2_retail_cave_generation_path_discovery.py` —
  7 focused tests green (absence verdict, sidecar-marker non-confusion,
  found-paths positive, missing-root / no-search-dirs / usage refusals,
  non-source-file ignore).
- No invented callsites: every named symbol above was read from the
  pinned trees. No runtime run was performed (read-only diagnosis plus
  unit tests), so captain safety #632 engages nothing new.
