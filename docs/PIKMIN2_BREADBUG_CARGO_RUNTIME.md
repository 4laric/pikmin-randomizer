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
