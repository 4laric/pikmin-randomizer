# Flora scenario boot (#766)

Lane `flora-scenario-boot`, issue [#766](https://github.com/4laric/pikmin-randomizer/issues/766).
Bounded real-engine-world follow-on to the completed bridge-only flora P1
observer (#737) for the enemies-1 flora gate: 47 Clover, 80 Tukushi,
89 Chiyogami. Owns only `experimental/pikmin2_flora_scenario_boot.py`,
`tests/test_pikmin2_flora_scenario_boot.py`, this doc and
`native/tools/p2_flora_scenario_boot_fixture.cpp`.

## What this lane proves

The replacement-main fixture boots the **real engine world** over the settled
private arena entry path (`--experimental-pikmin2-room` plus the caller-staged
arena entry package), stages a live starting squad with a centred 960x540
startup, parks the captain outside attack reach, and runs the canonical captain
guard (#632) on every observed tick before any readiness or PASS. Once a live
squad is on the floor it drives the landed #697 converter through the #723
engine hookup bridge for the three identities and emits receipt-parseable
`P2_FLORA_SCENARIO_*` markers with absorb-never-haul accounting.

Observed run (private, under `output/`): centred 960x540 window, `floor=1`
entry applied, `pikis=20` live squad, no immediate extinction, and

```
P2_FLORA_SCENARIO_SESSION identity=Clover converted=7 received=7 hauled=0
P2_FLORA_SCENARIO_SESSION identity=Tukushi converted=7 received=7 hauled=0
P2_FLORA_SCENARIO_SESSION identity=Chiyogami converted=3 received=3 hauled=0
PASS FLORA_SCENARIO_BOOT sessions=3
```

Captain safety: self-test PASS (7 rows) and negative test prints
`P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED` and exits 86 with no PASS.

## Explicit non-claims

The engine has **no flora conversion call site**: `pc_port/pc_bbft.cpp` and
`CMakeLists.txt` contain no flora references, and the #697 converter plus the
#723 bridge are engine-free TUs included only by fixtures. Flora native
registration is visual-only P1 proxy anchors (`pc_port/pc_p2_batch2.cpp`; no
FSM, no reward, no collision). The conversion observed here is therefore
**bridge-driven from fixture facts, not natural gameplay**. All six runtime
gates stay UNTESTED. No ADMIT, no ledger writes, no playability claim beyond
what is observed.

## Remaining blockers (not this lane)

Landing the shared per-tick hookup call in `pc_port/pc_bbft.cpp` and the
`pikmin_pc` CMake membership is the serialized follow-on owned by #722
(mechanics) and #171 owner + #186 hook review. Until it lands, natural
47/80/89 conversion and reward cannot be observed in-engine and the natural
admission gate cannot close.

## Reproduce

```
python -m pytest tests/test_pikmin2_flora_scenario_boot.py -q
```

Fixture build (light one-TU replacement-main link against the configured
private engine build; no production rebuild):

```
py -3.12 scripts/build_pikmin2_fixture.py \
  --build output/shard-enemies-1-flora-p1observer-build \
  --source <configured native source at 7cebe68c> \
  --fixture tools/p2_flora_scenario_boot_fixture.cpp \
  --output <fresh private evidence dir> \
  --expected-native-head 7cebe68c0a1dda18d68bd73062c43caf4e25ad32
```

Staged run (private arena with `assets/` plus the arena entry package):

```
py -3.12 scripts/run_pikmin2_fixture.py --exe <fixture.exe> --run-dir <fresh run dir> \
  --timeout 60 --arg=--experimental-pikmin2-room --pass-marker "PASS FLORA_SCENARIO_BOOT"
```