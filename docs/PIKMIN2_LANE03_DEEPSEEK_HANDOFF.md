# Lane 03 deepseek handoff (fix1) — ENEMY_P2 spawn-binding resolution, parser + resolution only (#439)

Lane 03 (Seed/native bridge), DeepSeek worker. Fix1 corrects a review finding: the
prior slice keyed the seed's `ENEMY_P2` target on `Generator::_70` (a raw ID32 tag
read only on the non-ram file path), which can never match lane 04's target
contract. The binding now keys on the **spawn-slot uid** (`pc_randomizer_generator_id`
via `pc_randomizer_bind_generator`), exactly the value lane 04 emits as
`str(slot['uid'])`.

Title is now **"parser + resolution only"**: the resolved source id reaches the
ordinary `GenObjectTeki::birth` path and is emitted as a `P2_SEED_RESOLVE` marker,
but nothing yet creates a live bound actor, so game gate A stays UNTESTED.

## Source IDs / files owned

- Snow Bulborb = source 45 (`YellowKochappy`), Dwarf Orange = source 44
  (`BlueKochappy`), host `TEKI_Chappy`=3.
- Root: `experimental/pikmin2_seed_bridge.py` (unchanged), `scripts/test_p2_bridge_spawn.py`
  (rewritten to use `binding_targets_for_sources([45,44])`), `docs/PIKMIN2_SEED_BRIDGE.md`.
  `tests/test_pikmin2_seed_spawn_binding.py` was **dropped** (redundant with
  `tests/test_pikmin2_seed_bridge.py`).
- Native: `pc_port/pc_randomizer.{h,cpp}`, `pc_port/pc_randomizer_probe.cpp`; narrow
  additive hook in `src/plugPikiNakata/genteki.cpp`.

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (branch `deepseek/p2-l03`):
- `7a60dc8` lane03: ordinary P2 enemy spawn-binding tests and doc (#439)  [superseded test file dropped in fix1]
- `8056354` lane03: deepseek handoff (#439)
- `…` lane03: review fixes — spawn-binding keys on spawn-slot uid (#439)  [fix1]

Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (branch `deepseek/p2-l03-native`):
- `8411ad37` lane03: ordinary P2 enemy spawn-binding resolution via generator _70 (#439)  [superseded]
- `30eee29f` lane03: review fixes — key ENEMY_P2 bindings on the spawn-slot uid, not Generator::_70 (#439)

Both worktrees clean at handoff.

## Interfaces / hooks touched and why

- `pc_randomizer_set_generator_id` / `pc_randomizer_bind_generator`: the
  `!pc_randomizer_spawn_slots()` early-outs now also allow `pc_randomizer_p2_bridge()`,
  so the generator→spawn-uid map is populated under `ENEMY_P2` (which forbids the P1
  slot layouts; `pc_randomizer_spawn_slots()` is false and the map used to stay empty).
- `pc_randomizer_p2_source_for_id(unsigned long)`: stringifies a spawn-slot uid and
  returns `pc_randomizer_p2_source(...)` (0 when unbound).
- `GenObjectTeki::birth`: emits `P2_SEED_RESOLVE source_id=<n> target=<uid>
  original_type=<t> x=.. z=..` via `pc_randomizer_generator_id(info.mGenerator)`.
  Resolution marker only — not a bound actor.
- `pc_randomizer_probe --enemy-p2-spawn-probe`: re-derives and re-resolves every bound
  slot uid across an unset+rebind (cache reload), asserting reload stability.

## Build evidence (output/dsw/l03-build-evidence.txt)

- probe: native `30eee29f283e86678f382da710c1fbc826ef6068` dirty=no,
  `sha256 d43844d960b09bd2543ab4261eb578dd7504e6a62770c0ab4b34d8660f618fd5`,
  `ninja -n` = "ninja: no work to do."
- `pikmin_pc`: native `30eee29f283e86678f382da710c1fbc826ef6068` dirty=no,
  `bin/nectar.exe`, `sha256 236a878611b3bcfb54e590488b59ab936adb195a3a00d62d74aeb9fb1aaae476`,
  `ninja -n` = "ninja: no work to do."

## Fixture adoption

N/A (probe-level slice; no GL/input run). The produced `pikmin_pc` inherits the base's
960×540 centred-window startup but was not launched.

## Six-gate table (natural vs injected)

| Gate | Result | Label |
|---|---|---|
| 1 Exact identity + spawn | UNTESTED | Parser+resolution only: `ENEMY_P2` → spawn-slot uid → source 45/44 resolves at ordinary `birth` (`P2_SEED_RESOLVE`). No live bound actor created. |
| 2 Autonomous movement/animation | UNTESTED | lane 13 family render. |
| 3 Attacks and receivers | UNTESTED | lanes 10/13. |
| 4 Death and corpse | UNTESTED | lane 13. |
| 5 Transport and reward | UNTESTED | lane 06. |
| 6 Cleanup and re-entry | UNTESTED | lane 07. |
| Persistence | PASS (protocol) | same seed/slot → identical layout/bindings across restart; native resolution is deterministic and reload-stable (unset+rebind re-resolves in the probe). |

## Tests run

- `py -3.12 scripts/test_p2_bridge_spawn.py <probe>` → **passed**: 49 real lane-04 uids
  (`binding_targets_for_sources([45,44])`) resolve to the seed's Snow/Dwarf-Orange
  sources end to end; stdout saved to `output/dsw/l03-out/p2_spawn_probe.txt`.
- `py -3.12 scripts/test_p2_generated_session.py <probe>` → **passed** (no regression);
  stdout saved to `output/dsw/l03-out/p2_generated_session.txt`.
- `py -3.12 -m pytest tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py -q`
  → **30 passed** (redundant `test_pikmin2_seed_spawn_binding.py` removed).
- `py -3.12 scripts/test_p2_bridge_native.py <probe>` → still fails; pre-existing stale
  script (never passes `--enemy-p2-expect`) superseded by `test_p2_generated_session.py`.

## Assumptions

- Lane 04's contract (`str(slot['uid'])`, `randomizer/p2_placement_catalog.py`) is the
  authoritative target token; `Generator::_70` is a fixture-stamped ID tag, not stable
  across cache reload, and not the placement key.
- Creating a live bound actor is lane 13/05 work: their `-actors.txt`/vehicle selection
  is `_70`-keyed today and must switch to the spawn-slot uid.

## Remaining blockers (provider lane)

- Lane 02: admission set empty.
- Lane 04: placement evidence (`_70`→spawn-uid calibration already consistent; XYZ/route
  evidence pending).
- Lane 13/05: a real birth consumer (`pc_p2_kochappy_fsm` for Dwarf Orange; the Snow
  campaign seam) must consume the resolved source id at the spawn-slot uid.

## Subagent usage

- `explore` #1 (source audit): confirmed the reviewer's `_70`-vs-uid finding with exact
  citations (generator.cpp:748-755/830-833, p2_placement_catalog.py:346, spawn uid = crc32).
  Used as-is; directly drove the correction.
- `explore` #2 (candidate inventory): named `pc_p2_kochappy_fsm`/Snow-campaign as the
  future consumer and confirmed `test_pikmin2_seed_spawn_binding.py` redundancy. Used as-is.
- `general` #3 (test rewrite): rewrote `scripts/test_p2_bridge_spawn.py` to use
  `binding_targets_for_sources([45,44])` (49 real uids) and verified py_compile + layout.
  Used as-is; I ran it against the rebuilt probe (it passed).
Net: saved substantive read/verification time; the correction itself was native work I did directly.

## Exact reproduction command

```
py -3.12 scripts/test_p2_bridge_spawn.py C:/Users/alari/pikmin-randomizer/output/dsw/native-l03-build/pc_randomizer_probe.exe
```
