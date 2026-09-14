# Breadbug proxy cargo observation

Scope #168/#186, Codex owner on shared 4laric. This private fixture reuses the
unchanged original P1 Impact Site arena and P2 live visual delegate. It creates
one real red 1-pellet through `PelletMgr::newNumberPellet`, `init`, `startAI`,
100 units ahead of the actor's current native facing after normal tutorial
dismissal. Only the fixture captain is moved for camera framing. The fixture
never calls the enemy's grab, carry, release, state transition or velocity API.

The source basis is `native/src/plugPikiNakata/taicollec.cpp`: carry power is 2
(line 509); target eligibility excludes ship parts, unwinnable and overweight
pellets (846 onward); natural hold stores the pellet in creature pointer 2;
carrying calls `Pellet::doCarry` and routes to `getNestPosition`; putting ends
the stick, swallows and kills the pellet when the native animation finishes.
The new fixture observes that pointer, displacement and distance to the nest.
It records release/disappearance without treating every release as nest delivery.

The original practice zero-Pikmin extinction tutorial is dismissed with the
existing private `instrument_tutorial` Controller-A helper. UI flags and
enemy actions remain untouched. Native AI still uses P1 models/animation
internally; the imported visual does not supply P2 animation events or P2 AI.

The parser reports incomplete evidence without turning a successful process
exit into gameplay acceptance. Grabbing, over 15 held frames, over 10 units
of displacement and nest progress, release, and live visual are separate gates.
Combat, Pikmin tug-of-war, corpse rewards and full P2 parity are not covered.

## Observed native result

The real process passed all bounded observation gates. At tick 150 the actor
held the pellet in state 5; state 6 dragged it; state 8 put it down; by tick 330
state 9 had released it and the pellet was no longer alive. It was held for
190 frames, moved 130.704 units horizontally, and approached within 1.546 units
of the recorded nest (98.209 units of progress). No enemy action was injected.
This sequence is consistent with the source's ordinary nest swallow path.

Result: `output/p2-lifecycle-batch/breadbug-cargo-native-01/result.json`.
Run: `4a98fa30503b466b9ba786ecc22516f5` beneath that directory.
Executable: `output/p2-lifecycle-batch/breadbug-cargo-runtime-link-01/fixture.exe`.
SHA256: `e79d7a45124d760cc3e2839800a05435a62bcda47c50de44b5810f678fbd17a4`.
The private `commands.json` records source hashes, fixture compilation and the
current-source tutorial input replacement. It links the previously copied
`breadbug-actor-runtime-link-01` inputs, native base
`d7ff676bf8990a442002e1c3d7050f17a93b01a3`, including the previously recorded
dirty creatureCollision/goalItem diff
`7c5baccf4deb14218bb8690dc795a9a6a0c629e3bf2d2f3b9eec501a6bb957ad`.
No fresh production build or pristine-commit claim is made.

The final inspected capture visibly shows the P2 Breadbug model near the nest.
The grab capture is mostly hidden behind the stump rim, so the capture alone
does not establish mouth/pellet alignment. Native pointer/state/position logs
establish the interaction. Accurate P2 carrying/swallow animation remains a
separate gate: the current renderer still selects only wait/move samples.

Both new parser tests pass; the actual private fixture compiled, linked and
exited 0. No production hook was required for this increment.

## Runnable proxy cargo arena (lane 18, 2026-09-14)

`experimental/pikmin2_breadbug_proxy_cargo.py` is the committed runnable path
that turns the observation above into a build/run/validate workflow on the
maintained line. It builds the unchanged private fixture
`scripts/pikmin2_breadbug_cargo_fixture.cpp` (now on the standard env-driven
960x540 centred window) from a fresh native build via
`scripts.build_pikmin2_fixture`, stages the existing proxy arena through
`experimental.pikmin2_breadbug_arena.prepare`, drives ordinary P1 AI, and parses
the host log through `experimental.pikmin2_breadbug_contest_observation`. The
arena's existing byte-verify step keeps the original course bytes preserved.

Exact commands (coordinator's serialized GL slot; never run two at once):

```powershell
# 1. build (reuses a fresh native build; never rebuilds production)
py -3.12 -m experimental.pikmin2_breadbug_proxy_cargo build `
  --native native --build-dir output/<lane>-build --head <40-hex> `
  --prefix output/p2-lifecycle-batch/breadbug-actor-runtime-build/room-prefix.inc `
  --output output/<lane>-proxy-cargo-build
# 2. run (stages the arena and writes result.json)
py -3.12 -m experimental.pikmin2_breadbug_proxy_cargo run `
  --assets <assets> --profile <breadbug-visual-profile> `
  --exe output/<lane>-proxy-cargo-build/fixture.exe `
  --output output/<lane>-proxy-cargo-run
# 3. validate a captured log
py -3.12 -m experimental.pikmin2_breadbug_proxy_cargo validate --log <staged>/host.log
```

- `validate()` delegates birth/result/strength parsing to `observe()` and adds
  the live-visual and standard-window gates; `complete` requires grab + release
  + live visual, so a clean exit with no grab stays incomplete.
- Tests `tests/test_pikmin2_breadbug_proxy_cargo.py` cover the builder path and
  synthetic grab/release/unobserved logs without any native build or GL run:
  `py -3.12 -m pytest -q tests/test_pikmin2_breadbug_proxy_cargo.py`.
- It observes the P1 host's grab/drag/release of a real number pellet and the
  two strength scales separately (`native_offset_power=2.0` vs
  `source_strength=1.5`), plus the read-only native carrier count from the
  family-local `P2_BREADBUG_CONTEST` tick hook (`native_carriers`,
  `native_hook`). It still does not observe a P2 pull channel and
  `p2_contest_semantics` stays `False`.
