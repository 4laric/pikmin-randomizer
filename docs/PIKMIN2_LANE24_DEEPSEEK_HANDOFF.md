# Lane 24 (Bulblax/larvae) DeepSeek handoff

Child issue [#445](https://github.com/4laric/pikmin-randomizer/issues/445); parent [#172](https://github.com/4laric/pikmin-randomizer/issues/172); actor [#289](https://github.com/4laric/pikmin-randomizer/issues/289). Implementation owner: Codex through shared account 4laric; executing agent/session: DeepSeek lane-24 (`deepseek/p2-l24`).

## Source ID and slice

Concrete source enemy ID: **Emperor Bulblax (KingChappy, enemy 53).**
Missing gate closed: **natural combat -> lethal death**, un-injected. The bumped #289
fixture only reaches the `Dead` frame-185 key through the opt-in kill injection
(health forced to 0). This slice proves the lethal path through the actor's own
`receiveScan` (continuous stuck-Pikmin latch damage) with no health/kill
injection, no bombs, and no force/Flick injection.

## Owned files

Native (worktree `output/dsw/native-l24`, branch `deepseek/p2-l24-native`):
- `pc_port/pc_p2_king.cpp`
- `pc_port/pc_p2_king_policy.h`

Root (worktree `output/dsw/l24-root`, branch `deepseek/p2-l24`):
- `experimental/pikmin2_king_natural_death_runtime.py`
- `tests/test_pikmin2_king_natural_death_runtime.py`
- `tests/pikmin2_king_policy.cpp`
- `docs/PIKMIN2_BULBLAX_NATURAL_COMBAT.md`

No shared files (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
`gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`, CMake) were touched.

## Ordered commits

Root (base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`), clean at head:
```
8917781 lane24: King natural combat->death harness and tests (#445)
63d15ea lane24: latch the natural-death squad outside the tongue/trample reach (#445)
d0673a7 lane24: natural combat->death docs and handoff (#445)
```

Native (base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`), clean at head:
```
1131c8fb lane24: King natural combat -> lethal death receiver (continuous latch damage) (#445)
```

## Interfaces / hooks

- `pc_p2_king_policy.h`: two new constants `DamagePerBlow = 1.0f` (stuck-to-part
  tier x1) and `BlowIntervalTicks = 20` (2/3 s at the 30 Hz behavior clock),
  documented as the ordinary Pikmin attack cadence approximation.
- `pc_p2_king.cpp`: `receiveScan` adds a per-actor `damageClock`; while any Pikmin
  remains stuck it applies `stuckCount * DamagePerBlow` each `BlowIntervalTicks`
  and emits `P2_KING_COMBAT_DAMAGE`. The entry blow and the `blows`/`stuckCount`
  flick counters are unchanged, so the already-passed flick/trample timing is
  untouched. No public header/signature change; `pc_p2_king.h` unchanged.

Why: the inherited receiver only dealt a unit blow once per Pikmin on entry, so
natural health-to-zero was unreachable; stuck Pikmin must keep delivering blows.

## Already integrated vs actually new

Both KingChappy natural Flick/trample (with `P2_KING_COMBAT_DAMAGE` absent) and
the injected WarCry/bomb/death gates were already in the branch. This slice only
adds continuous latch damage plus a new natural-death harness/tests/docs. No
already-passed injected gate is re-run with unchanged inputs.

## Build evidence (`output/dsw/l24-build-evidence.txt`)

```text
2026-09-14T19:52:13 lane=l24 target=pikmin_pc native=1131c8fb723d731f0c11d286b2456dd89166e0ce dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l24-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l24-build\bin\nectar.exe sha256=325041047cd29ac59f85a3d25326b05a1c3bd1447232410dff797ece451a66d9 ninja_n="ninja: no work to do." seconds=124
```

- Private build dir `output/dsw/native-l24-build`, Ninja + MinGW g++ 16.2.0, Release,
  `PIKMIN_NATIVE_JAUDIO=ON`, `PIKMIN_GAME_VERSION=VERSION_GPIE01_01`.
  (`build_lane.py` does not set `PIKMIN_NATIVE_JAUDIO` or `CMAKE_MAKE_PROGRAM`;
  the lane pre-configured once wrapped in the build slot, then reused the wrapper
  for the build.)
- Fixture `output/dsw/l24-out/king-natdeath-fixture2/build/fixture.exe`, provenance
  status `built`, expected native head `1131c8fb...`, SHA-256
  `7840a6ddf52327751270f500d01150a5799c93e33b5025ab69dd2abc911b1afc`.

## Fixture adoption evidence

- Window: `PIKMIN_P2_ROOM_WINDOW=960x540`; `native.log`:
  `Experimental preview window set to 960x540 windowed and centered`.
- Live starting Pikmin: `P2_KING_NATDEATH_BASELINE red=32 other=0` (authored
  32-red squad; overlay `ensure_pikmin_squad` did not top up). No extinction screen.
- Assets: P1 `C:/Users/alari/bbft/dist/cohesion/pikmin/assets`; bank rebuilt this
  session from `C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso` into
  `output/dsw/l24-out/bulblax-bank` (174 poses, 8,154,624 bytes).

## Six-gate table

| Gate | Status | Natural/injected |
|---|---|---|
| 1. Exact identity and spawn | PASS | natural spawn `P2_KING_READY id=230020 enemy=53 variant=default` |
| 2. Autonomous movement and animation | PASS | natural `P2_KING_APPEAR_TRIGGER` + sampled clip draw |
| 3. Attacks and receivers | PASS | natural `P2_KING_COMBAT_DAMAGE` 38 lines, health 1236 -> 0 |
| 4. Death and corpse | PASS | natural `P2_KING_STATE ... to=2 health=0`, `P2_KING_DEAD_KEY frame=185 kill=1` |
| 5. Actual transport and reward | source-backed N/A | Emperor has no corpse/carry reward in fixture (rewards owned by lane 06) |
| 6. Cleanup and re-entry | PASS | natural exit 0, no leftover process; re-entry alias not exercised this slice |

Only labeled fixture staging is the larger authored squad (32 reds) and the
per-tick re-pin of the live squad into a ring (same as the natural-Flick harness).
There is no `p2-king-inject.txt` and no bomb in the run.

Note: the `receiveScan` change is a changed input to the already-passed
natural-Flick gate. Its unit validator still passes; the required early checks
(`checkFlick next=3`, trample) fire before health falls below half, so the
natural-Flick GL run should still pass, but it was not re-run this slice; lane 01
should re-run it at the combined build.

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_king_natural_death_runtime.py tests/test_pikmin2_king_natural_flick_runtime.py tests/test_pikmin2_king_actor.py tests/test_pikmin2_bulblax_behavior.py tests/test_pikmin2_bulblax_bank.py -q` -> 64 passed, 3 skipped.
- `tests/test_pikmin2_king_actor.py` with `P2_NATIVE_PC_PORT=<native>/pc_port` also
  compiled and ran `tests/pikmin2_king_policy.cpp` (strict MinGW), asserting the
  new constants.

## Assumptions

- P1 per-color blow strength is out of scope; the family keeps a unit blow (documented).
- Blow interval 20 ticks is an approximation of Pikmin attack cadence (~1.5/s).
- The 32-red authored squad and ring re-pin are the same labeled staging as the
  accepted natural-Flick harness, not injected state.

## Remaining blockers (provider lane)

- Material/BTK/TEV fidelity, host lighting: lane 09 (#239/#128).
- Reward/transport/corpse carry endpoint: lane 06.
- Generated-session ordinary spawn binding / persistence: lanes 03/06.
- Campaign lifecycle/re-entry and mixed-scene budget: lanes 07/33.

## Reproduction command (exact)

```powershell
cd C:\Users\alari\pikmin-randomizer\output\dsw\l24-root
py -3.12 C:\Users\alari\pikmin-randomizer\output\deepseek-wave\slot.py run gl l24 -- py -3.12 -m experimental.pikmin2_king_natural_death_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/bulblax-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/king-natdeath-runtime2" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/king-natdeath-fixture2/build/fixture.exe"
```
(set `PIKMIN_P2_ROOM_WINDOW=960x540` and `PYTHONUTF8=1`; wrap in `slot.py run gl`.)
