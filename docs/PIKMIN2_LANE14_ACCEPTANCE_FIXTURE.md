# Lane-14 acceptance fixture descriptor

Tracking: lane 14, issue [#165](https://github.com/4laric/pikmin-randomizer/issues/165);
coordination [#186](https://github.com/4laric/pikmin-randomizer/issues/186);
placement facts [#440](https://github.com/4laric/pikmin-randomizer/issues/440).
Implementation owner: Codex through shared `4laric`. This is a run plan for the
lane-14 natural-combat/reward/re-entry acceptance, not an acceptance report.

Machine-readable companion: `docs/p2_lane14_acceptance_fixture.json`
(`schema: p2-lane14-acceptance-fixture-v1`), checked by
`tests/test_p2_lane14_acceptance_fixture.py`.

## Build and slot provenance

| Field | Value |
|---|---|
| Native branch / commit | `opencode/p2-lane14-native` @ `1531c0baa5f1830637bd2c7abd1bbdcc1a40b542` (based on `codex/p2-sweep437`) |
| Native worktree / build | `output/native-lane14` / `output/native-lane14-build` |
| Executable | `output/native-lane14-build/bin/nectar.exe` (target `pikmin_pc`, `OUTPUT_NAME nectar`) |
| Executable SHA-256 / size | `BBF22D28A86B2067297DEFEF9C47F0CD88F381DFAFE633685AB57D69C01E9841` / 7,633,898 bytes |
| Flags | Ninja, gcc 16.2.0, `Release`, `PIKMIN_NATIVE_JAUDIO=ON`, `PIKMIN_ENABLE_IPO=ON`, `PIKMIN_GAME_VERSION=VERSION_GPIE01_01`, `PIKMIN_NATIVE_OPTIMIZE=OFF`, `PIKMIN_RANDOMIZER_TEST_HOOKS=OFF`; `ninja -n` → no work |
| GL slot | reserved (queued) in #186; **run only after lane 01 releases** |

All runners set `PIKMIN_P2_ROOM_WINDOW=960x540` and prepend the MinGW bin dir.
Adopt the current starting-Pikmin overlay by regenerating the arena into a fresh
lane-owned output directory (below); do not reuse another lane's run dir.

## Inputs

```powershell
$laneP1   = 'C:/Users/alari/bbft/dist/cohesion/pikmin/assets'
$laneP2   = 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso'
$laneOut  = 'output/lane14-accept'
$laneExe  = 'output/native-lane14-build/bin/nectar.exe'
$laneBank = 'output/lane14-accept/assets'
```

Regenerate the converted ground bank fresh (private, ignored). A previously
validated bank exists at `output/p2-lane-verify/ground` as a fallback only:

```powershell
py -3.12 -m experimental.pikmin2_ground_inverts_assets --iso "$laneP2" --output "$laneBank" --pose-limit 3
```

## Natural-behavior runs (no injection)

These use the plain private `nectar.exe`; the markers come from the native
`pc_p2_*` modules. Each run stages the ground arena, then is time-bounded by the
harness (the actor keeps running; `timed_out` is expected).

| Run | Identity (ID) | Module | Seconds | Expected PASS marker |
|---|---|---|---|---|
| `sokkuri` | Sokkuri (79) | `experimental.pikmin2_sokkuri_behavior` | 25 | behavior checks in `P2_SOKKURI_*` |
| `armor` | Armor (15) | `experimental.pikmin2_armor_behavior` | 30 | `P2_ARMOR_STATE/BITE/EAT` checks |
| `elecbug` | ElecBug (28) | `experimental.pikmin2_elecbug_behavior` | 30 | `P2_ELECBUG_*` checks |
| `elecbug_pair` | ElecBug (28) | `experimental.pikmin2_elecbug_pair_behavior` | 40 | `P2_ELECBUG_PAIR_*` |
| `imomushi` | Imomushi (65) | `experimental.pikmin2_imomushi_behavior` | 30 | `P2_IMOMUSHI_*` checks |
| `tamago` | TamagoMushi (68) | `experimental.pikmin2_tamago_behavior` | 30 | `P2_TAMAGO_*` checks |
| `tamago_group` | TamagoMushi (68) | `experimental.pikmin2_tamago_group_behavior` | 30 | `P2_TAMAGO_GROUP_*` |
| `hana` | Hana (84) | `experimental.pikmin2_hana_behavior` | 30 | `P2_HANA_*` checks |
| `hana_residual` | Hana (84) | `experimental.pikmin2_hana_residual_behavior` | 30 | `P2_HANA_*` residual checks |

Command template:

```powershell
py -3.12 -m experimental.<module> run --assets "$laneP1" --imported "$laneBank" --output "$laneOut/<run>" --exe "$laneExe" --seconds <n>
```

## Instrumented runs

These need a private replacement-main `fixture.exe` built against the same
native worktree/build, then run instead of `nectar.exe`.

Build (once per fixture, after the native build is fresh):

```powershell
py -3.12 -m experimental.pikmin2_ground_lifecycle_behavior build --native output/native-lane14 --build-dir output/native-lane14-build --output output/lane14-accept/lifecycle-fixture --head 1531c0baa5f1830637bd2c7abd1bbdcc1a40b542
```

| Run | Identity (ID) | Module | Seconds | Kind | Notes |
|---|---|---|---|---|---|
| `elecbug_immunity` | ElecBug (28) | `experimental.pikmin2_elecbug_immunity_behavior` | 90 | **natural** emitter -> immunity/lethal | lane 10/11 electric path; own `build` |
| `lifecycle` | Sokkuri (79) + Armor (15) | `experimental.pikmin2_ground_lifecycle_behavior` | 150 | **injected** death | `P2_LIFECYCLE_INJECT ... not_natural_combat=1`; corpse/cleanup/re-entry |

## Gate mapping (expected, to be recorded after the run)

| Gate | Natural run coverage | Status in this plan |
|---|---|---|
| A Identity/content | all behavior runs | expected PASS (`P2_*_BIND ... source_id`) |
| B Declared behavior (experimental P1-derived) | Sokkuri, Armor, ElecBug, Imomushi, TamagoMushi, Hana | natural FSM observed; deviations recorded per module |
| C Combat/receivers | ElecBug emitter+immunity; Sokkuri flick; Armor bite | natural for ElecBug/flick/bite; **natural lethal player combat unproven** |
| D Death/drop/transport | lifecycle (corpse) | corpse PASS but **injected**; natural death + carry/reward **untested** |
| E Lifetime | lifecycle (cleanup/re-entry) | PASS but injected; not full scene/heap teardown |
| F Persistence | none | **untested** here; #397 owns reward/restart |
| G Product/mixed scene | none | **untested** here |

## Remaining gap the run will not close

No existing non-injecting fixture drives Pikmin combat to a **natural** ground
invertebrate death, and the ground arena is cargo-free with no Pod
(`pikmin2_batch2_core`), so reward/delivery is absent by construction:

- **Natural death from player combat** must be observed; the lifecycle fixture
  injects `mHealth=0` and is labelled diagnostic.
- **Reward/delivery/receipt** is owned by the lifecycle/reward lane (#397) and
  the Onion/AP endpoint, not this arena.

This descriptor freezes the runnable set; a natural-combat fixture (wait for the
live squad to kill the actor, then observe corpse/carry) is the follow-on code
slice before gate C/D can be claimed natural. Record that limitation on the
same row as the injected result; do not promote it.

## Release procedure (after lane 01 releases the slot)

1. Confirm no concurrent GL run and that #186 shows the slot released.
2. Build the two instrumented fixtures; run the natural-behavior set
   sequentially, then the instrumented set.
3. Record: root/native pins, exe SHA-256, per-run output dir, `native.log` hash,
   natural vs injected, and gates A-G.
4. Post the release comment in #186 with the measured results and remaining
   dependencies, and link the evidence from #165.
