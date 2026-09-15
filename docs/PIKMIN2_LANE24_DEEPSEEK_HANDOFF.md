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
- e9afed6 lane24: handoff accuracy (commit list + natural-flick re-run note) (#445)
- (integrator review-fix commits follow on both branches)
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
per-tick re-pin of the live squad into a ring (same as the natural-Flick harness). Review note: the pin neutralises the shake-off, so the entry blow re-fires for all stuck Pikmin after every Flick (~220 of 1300 HP from that loop); staging that inflates damage, labelled as such, not injection.
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

## Slice 2

### (a) King free-mode natural death (no per-tick re-pin)

`experimental/pikmin2_king_free_mode_runtime.py` stages 20 reds in a ring ONCE and
switches them to `PikiMode::FreeMode`; there is no per-tick re-pin, no bomb, no
injection. Result: **the 20 free Pikmin DID kill the Emperor** (killed=True,
227 `P2_KING_COMBAT_DAMAGE` lines, health 1266 -> 0, `P2_KING_DEAD_KEY frame=185`,
exit 0). Mechanism: after the first Flick scatters the squad, a small persistent
latch (stuck 3-6) is maintained autonomously (P1 idle/latch-resume within
`mIdleAttackSearchRange` 100) and drives 1300 HP down over ~151 s. This does not
rely on the slice-1 ring re-pin (whose entry-blow re-fire the reviewer flagged);
the reproduction is a genuine natural combat -> death without that inflation.
Run dir `output/dsw/l24-out/king-freemode-runtime/king/900fd67a...`; fixture
`king-freemode-fixture/build/fixture.exe` sha256 `845b487c...`.

### (b) Natural-Flick GL re-run on current head

`experimental/pikmin2_king_natural_flick_runtime.py` re-run against native
`340d7377` (which carries the slice-1 continuous-damage receiver + the review
`damageClock=0` reset). **PASS** (`king-natural True`, run dir
`king-natflick-runtime/king/c165aad1...`; fixture `king-natflick-fixture/build/fixture.exe`
sha256 `6ad899a3...`). The receiver change is now covered by its own run, not
just by markers inside the death log.

### (c) Queen natural lifecycle (births / baby bite / death cleanup)

`experimental/pikmin2_queen_natural_runtime.py` + native Queen changes (below).
Un-injected result **PASS** (exit 0; run dir `queen-natural-runtime2/queen/609b57d0...`):
9 natural larva births from the 2.0 s timer with exactly-once `born=` accounting
(1..9, no gaps), a natural Baby captain bite (`P2_QUEEN_LARVA_ATTACK damage=2
captain_before=500.0 captain_health=498.0` — real health drop on a live captain),
and Queen death (`P2_QUEEN_STATE from=4 to=0 health=0.0`,
`P2_QUEEN_COMBAT_DAMAGE ... health=0.0`) releasing all 3 live larvae
(`P2_QUEEN_DEATH_LARVA_RELEASE released=3`). No injected health; death is driven
by the mirrored continuous latch damage.

### Native changes (slice 2)

- `pc_port/pc_p2_queen.cpp`: continuous stuck-Pikmin latch damage in `receiveScan`
  (mirrors the King; `P2_QUEEN_COMBAT_DAMAGE`), `damageClock=0` reset on Flick,
  exactly-once `births` counter (`born=` in `P2_QUEEN_LARVA`), and Queen-death
  larva release (`P2_QUEEN_DEATH_LARVA_RELEASE`, set `active=false` on all live
  larvae, exactly once via `deathReleased`).
- `pc_port/pc_p2_queen_policy.h`: `DamagePerBlow = 1.0f`, `BlowIntervalTicks = 20`.
- `pc_port/pc_p2_queen.h` + `.cpp`: `pc_p2_queen_death_released()` fixture getter.

### Root files (slice 2)

- `experimental/pikmin2_king_free_mode_runtime.py`
- `experimental/pikmin2_queen_natural_runtime.py`
- `experimental/pikmin2_lane24_gates.py` (pure validators `king_free_mode_validate`, `queen_natural_validate`)
- `tests/test_pikmin2_lane24_gates.py`
- `tests/pikmin2_queen_policy.cpp` (two new constant assertions)

### Ordered commits (slice 2 only)

Root (base `ef1cace`):
```
2406259 lane24: slice2 free-mode + Queen natural-lifecycle harnesses, gate validators, tests (#445)
846705e lane24: Queen natural fixture — 64-red combat pool, hold-away births, press-avoiding ring (#445)
```
Native (base `b805d9c6`, after the slice-1 integrator review-fix `0f57d8a0`):
```
cafdc5e6 lane24: Queen natural lifecycle — continuous latch damage, exactly-once births, death larva release (#445)
340d7377 lane24: expose Queen death-released observation getter for the natural-lifecycle fixture (#445)
```

### Build evidence (slice 2)

`output/dsw/l24-build-evidence.txt` (build dir `native-l24-build`, Ninja/MinGW
Release, JAudio ON):
```text
... lane=l24 target=pikmin_pc native=340d737722181495bacba5e7fde919acfb54a28c dirty=no exe=...bin/nectar.exe sha256=f8beeecc54dfc25d5fd245da46e0a3699c105d926a2d391bae6d43a16ba98171 ninja_n="ninja: no work to do."
```
Fixtures (all provenance `built`, expected native head `340d7377...`):
`king-freemode-fixture` `845b487c...`, `king-natflick-fixture` `6ad899a3...`,
`queen-natural-fixture2` `6dcf6da3...`. All runs: `PIKMIN_P2_ROOM_WINDOW=960x540`,
centred window logged, live squad, no extinction.

### Tests (slice 2)

`py -3.12 -m pytest tests/test_pikmin2_lane24_gates.py tests/test_pikmin2_king_natural_death_runtime.py tests/test_pikmin2_king_natural_flick_runtime.py tests/test_pikmin2_king_actor.py tests/test_pikmin2_queen_actor.py tests/test_pikmin2_bulblax_behavior.py -q`
-> 68 passed, 3 skipped; with `P2_NATIVE_PC_PORT=<native>/pc_port` the King/Queen
policy C++ tests compile and pass (13 passed).

### Subagent usage

- explore #1 (source audit Queen/Baby/King): returned exact birth-timer/born-key
  facts, Baby bite key frame 10 / damage 2 / dist 30 / angle 45, the six Queen
  death entry points, and the Piki idle/latch-resume re-engage AI. Used as-is for
  the native edits and the free-mode mechanism note (high value; saved the manual
  source trace). One correction: it asserted the King "cannot re-latch autonomously",
  which the free-mode run disproved for the proximity receiver — the proximity
  scan, not the Piki AI, is what re-sticks them.
- explore #2 (inventory): located the exact untouched native markers, confirmed the
  Baby bite was unexercised by any harness and that no Queen-death cleanup path
  existed, and pointed to `pikmin2_kochappy_arena_combat.py` as the free-mode ring
  deploy pattern. Used as-is.
- general #3 (tests/harness scaffolding): wrote `experimental/pikmin2_lane24_gates.py`
  and `tests/test_pikmin2_lane24_gates.py` (8 tests) to the spec on the first run;
  both harnesses import these validators. Used as-is (no corrections).

Estimated net: ~25-35 min of manual source tracing and scaffolding saved; no
rework needed from any of the three.

### Remaining blockers (unchanged)

- Queen material/BTK/TEV fidelity: lane 09 (#239/#128). King/Queen reward/transport
  carry endpoint: lane 06. Generated-session ordinary spawn/persistence: 03/06.
  Campaign lifecycle/re-entry, mixed-scene budget: 07/33. The Queen's ~5000 HP
  (vs the King's 1300) means natural death needs the 64-red combat pool here;
  per-color blow strength remains out of scope.

### Reproduction (slice 2)

```powershell
cd C:\Users\alari\pikmin-randomizer\output\dsw\l24-root
# (a) King free-mode
py -3.12 C:\Users\alari\pikmin-randomizer\output\deepseek-wave\slot.py run gl l24 -- py -3.12 -m experimental.pikmin2_king_free_mode_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/bulblax-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/king-freemode-runtime" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/king-freemode-fixture/build/fixture.exe"
# (c) Queen natural lifecycle
py -3.12 C:\Users\alari\pikmin-randomizer\output\deepseek-wave\slot.py run gl l24 -- py -3.12 -m experimental.pikmin2_queen_natural_runtime run --assets "C:/Users/alari/bbft/dist/cohesion/pikmin/assets" --bank "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/bulblax-bank" --output "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/queen-natural-runtime2" --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l24-out/queen-natural-fixture2/build/fixture.exe"
```
(each with `PIKMIN_P2_ROOM_WINDOW=960x540` and `PYTHONUTF8=1`; wrap in `slot.py run gl`.)
