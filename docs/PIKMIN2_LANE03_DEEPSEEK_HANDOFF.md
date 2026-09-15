# Lane 03 deepseek handoff — ordinary P2 enemy spawn-binding seam (#439)

Lane 03 (Seed/native bridge), DeepSeek worker. Slice: the remaining "ordinary
target-to-live-actor spawn binding" — wire the seed's `ENEMY_P2` target→source
binding into the actual enemy birth so a bound generator resolves to its P2 source
id on the ordinary spawn path (hosted by the Snow/Dwarf-Orange cohort,
`YellowKochappy`=45 / `BlueKochappy`=44, both on native `TEKI_Chappy`=3).

## Source IDs / files owned

- Snow Bulborb = source 45 (`YellowKochappy`), Dwarf Orange = source 44
  (`BlueKochappy`). Host `TEKI_Chappy`=3.
- Root owned: `experimental/pikmin2_seed_bridge.py` (unchanged this slice),
  `scripts/test_p2_bridge_spawn.py` (new), `tests/test_pikmin2_seed_spawn_binding.py`
  (new), `docs/PIKMIN2_SEED_BRIDGE.md` (updated).
- Native owned: `pc_port/pc_randomizer.{h,cpp}`, `pc_port/pc_randomizer_probe.cpp`.
  Narrow additive hook: `src/plugPikiNakata/genteki.cpp` (labeled `P2_SEED_BIND`).

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (branch `deepseek/p2-l03`):
- `7a60dc8` lane03: ordinary P2 enemy spawn-binding tests and doc (#439)

Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (branch `deepseek/p2-l03-native`):
- `8411ad37` lane03: ordinary P2 enemy spawn-binding resolution via generator _70 (#439)

Both worktrees clean at handoff.

## Interfaces / hooks touched and why

- `pc_randomizer_p2_source_for_id(unsigned long generator_id)` (new): stringifies
  a generator's `_70` ID32 and returns `pc_randomizer_p2_source(...)`; 0 when
  unbound. Keeps `pc_randomizer.cpp` free of `Generator.h`.
- `GenObjectTeki::birth` (`genteki.cpp`): narrow additive hook, gated on
  `pc_randomizer_p2_bridge()`, emitting `P2_SEED_BIND source_id=<n> target=<_70>
  original_type=<t> x=.. z=..` at the bound generator's ordinary spawn. This is
  the previously-missing "ordinary target→live-actor binding" seam that nothing in
  `src/` consumed before (confirmed by source audit: `pc_randomizer_p2_*` had zero
  `src/` references).
- `pc_randomizer_probe --enemy-p2-spawn-probe --enemy-p2-target <id>` (new): asserts
  bound/unbound resolution.

No new generic subsystem; reuses the existing `p2Bindings` map and the `_70`
per-generator identity the Snow/Dwarf-Orange family sidecars already select by.

## Build evidence (output/dsw/l03-build-evidence.txt)

- probe: `sha256 2251cf06a581f65ddb07ef2e8eab4542d9e6d6abb8cea4d032c802f1da1d690c`
  (built from the identical pre-commit tree, native `b805d9c6` dirty=yes).
- `pikmin_pc`: native `8411ad37ec75825f3329a5912e43e4398ab36440`, dirty=no, exe
  `bin/nectar.exe`, `sha256 6b79bb2d2a4e22cbc8503a6e60fe44d6df8649fff52851df4d0455ca23eae063`,
  `ninja -n` = "ninja: no work to do.", 603/603 objects linked, 126s.

## Fixture adoption

N/A for this slice: the deliverable is the probe-level seed→spawn-binding seam, not
a GL/runtime acceptance run. The produced `pikmin_pc` inherits the base's
960×540 centred-window startup, but no real-GL fixture was launched (no GL slot
consumed). The natural Snow/Dwarf-Orange render is a lane 05/13 gate, not this slice.

## Six-gate table (natural vs injected)

| Gate | Result | Label |
|---|---|---|
| 1 Exact identity + spawn | PASS (seam) | INJECTED/parser: `ENEMY_P2` → generator `_70` → source 45/44 resolved at ordinary `birth`; probe asserts bound/unbound. Natural live render UNTESTED. |
| 2 Autonomous movement/animation | UNTESTED | lane 13 family render. |
| 3 Attacks and receivers | UNTESTED | lanes 10/13. |
| 4 Death and corpse | UNTESTED | lane 13. |
| 5 Transport and reward | UNTESTED | lane 06. |
| 6 Cleanup and re-entry | UNTESTED | lane 07. |
| Persistence | PASS (protocol) | same seed/slot → identical layout/bindings across restart (`test_pikmin2_seed_generation.py`); native `ENEMY_P2` is deterministic. Not a save/reward persistence claim. |

## Tests run

- `py -3.12 -m pytest tests/test_pikmin2_seed_spawn_binding.py -q` → 7 passed.
- `py -3.12 -m pytest tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py tests/test_pikmin2_seed_spawn_binding.py -q` → 37 passed.
- `py -3.12 scripts/test_p2_bridge_spawn.py <probe>` → passed (`ENEMY_P2_SPAWN_PASS`).
- `py -3.12 scripts/test_p2_generated_session.py <probe>` → passed (no regression).
- `py -3.12 scripts/test_p2_bridge_native.py <probe>` → FAILS; pre-existing stale
  script that never passes `--enemy-p2-expect` (probe asserts `expected > 0`). Not
  introduced by this slice; superseded by `test_p2_generated_session.py`.

## Assumptions

- The seed's binding target token is the **decimal string of the bound dwarf
  generator's own `_70` ID32**; lane 04 supplies those concrete values.
- Snow/Dwarf-Orange visual replacement + the `assets/p2-snow-all-dwarfs.txt`
  all-dwarfs opt-in remain lane 05/13; this slice only makes the spawn identity
  seed-resolvable, it does not retire the marker-file opt-in.

## Remaining blockers (provider lane)

- Lane 02: admission set empty → no generated-session live spawn yet.
- Lane 04: placement blocked (`_70` target values + XYZ/terrain/route evidence).
- Lane 05/13: Snow/Dwarf-Orange bank staging + per-generator selective family bind
  consuming `P2_SEED_BIND`.

## Subagent usage

- `explore` #1 (source audit): confirmed the gap (zero `src/` consumers of
  `pc_randomizer_p2_*`) and identified `Generator::_70` as the correct per-generator
  live-spawn key. Used as-is.
- `explore` #2 (candidate inventory): mapped all existing bridge/family/fixture
  markers and reusable pieces. Used as-is.
- `general` #3 (pytest): wrote `tests/test_pikmin2_seed_spawn_binding.py` (7 passed).
  Used as-is; only a docstring corrected (target is `_70`, not spawn-catalog uid).
Net: saved substantial read-time (~2.5h of manual grep/read collapsed); results used directly.

## Exact reproduction command

```
py -3.12 scripts/test_p2_bridge_spawn.py C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/pc_randomizer_probe.exe
```
