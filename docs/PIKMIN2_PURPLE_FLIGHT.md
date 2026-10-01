# Purple throw, HipDrop and impact feedback

Batch 3, 2026-09-13, issue [#393](https://github.com/4laric/pikmin-randomizer/issues/393), parent #113. Implementation owner: Codex through shared account `4laric`. Scope and acceptance were recorded before implementation in [the issue](https://github.com/4laric/pikmin-randomizer/issues/393#issuecomment-5656583244); shared hooks were [reviewed under #186](https://github.com/4laric/pikmin-randomizer/issues/186#issuecomment-5656628885). Two Sol lanes implement flight and source motion; root owns feedback, fixture preparation and integration.

## Source behavior

Read-only P2 revision `632af93787b9c95b63f0c13be32b161375ce3a96`, `src/plugProjectKandoU/pikiState.cpp`: Flying enters HipDrop when a Purple's vertical velocity reaches zero or becomes negative. HipDrop pauses for 0.25 seconds, starts descent at `-gravity * 0.5`, selects the nearest living enemy from its custom-radius-50 search by 3D distance, and supplies horizontal velocity 120 toward it. Descent spins at `PI / 0.2` radians per second. Ground/platform contact produces impact and holds recovery for 0.3 seconds; enemy collision follows direct Hipdrop → earthquake → conditional Press and exits without ground recovery.

Flying starts `ROLLJUMP` (`motion/rolljmp.bca`, 14 frames). HipDrop entry does not replace that motion. Descent starts `FALL` (`motion/fall.bca`, 20 frames); ground recovery retains it. Both source clips use repeat mode at 30 frames per second. There is no separate landing clip in this state sequence. Phase elapsed time and motion elapsed time therefore differ across entry/recovery transitions. The BCA files have no event metadata; this does not establish the absence of events elsewhere in the source animation system.

The local GPVE01 rev0 `user/Kando/piki/pikis.szs` archive hashes to `913a01d6f9c77a7e7b2de604c2a708ba256de9aaf890702b0b8e1b6bf038eef3`. ROLLJUMP SHA256: `c89360d460b26d1efe04983597f609d50086d68c836ead0d7fbe8c9c18c454b1`; FALL SHA256: `0316ca28e51f262fd29b417af1efdab50bd173b903c770b025fd6384de77761b`.

## Native integration boundary

`p2-purple-flight.txt` with version `P2_PURPLE_FLIGHT_1` enables the new lifecycle only alongside an enabled Purple impact profile. Real captain throws arm per-Piki Ascent state. Unarmed Flying transitions, including rescue/falls, do not acquire the new lifecycle. `pc_p2_purple_flight.*` owns phases and clocks; the motion renderer consumes those clocks without maintaining a second actor-lifetime registry.

P1 flower gliding must not run during HipDrop descent, and duplicate ground contacts must not skip recovery. Cancellation, death, reset and pooled initialization clear the flight/feedback state and restore temporary physics/facing flags. Re-arming first cancels the prior flight, so temporary flags cannot become the next throw's baseline. Prior separately enabled adult direct damage remains 50; the shockwave remains nondamaging. Native target enumeration with `50 + mCollisionRadius` and native organic eligibility is an explicit adaptation of the P2 cell iterator/living-thing checks, not a port of its spatial partition.

The P2 HipDrop collision callback ignores Pikmin and ends the state on other creature contacts after feedback and any enemy interactions. The separate platform callback uses ground recovery. Ascent-only ground contact uses ordinary landing without a HipDrop wave. Native ordinary-AI re-entry adapts P2 `invokeAI`; these boundaries must not accidentally keep P1's bouncing flight active after a body-slam contact.

## Feedback adaptation

P2 source effects are `TPkBlackDown` during HipDrop and three-part `TPkBlackDrop` on impact (`efxPikmin.cpp`). Its sound IDs are DOSUN `0x284e` and DOSUN_HIT `0x287c`, with Fixed11 rumble and LightFastShort camera vibration. Those P2 particle/audio banks are not loaded by this P1 runtime.

The new feedback module implements these event roles using native adapters: finite purple-tinted sparkle trail bursts, a scaled dust ring/cloud/hit flash, and spatial native thud/hit audio. No particle holds a Piki pointer; cancel stops subsequent trail emission and detached particles fade. It adds a separate camera event at appended ID5 (0.12 seconds, amplitude0.08, frequency30), preserving existing IDs/parameters. Nearby impacts can pulse at most once per150ms. SDL controller rumble lasts80ms and respects the game's vibration preference; absent hardware is reported separately. The old PAD motor function is a stub, so simply calling it would not deliver feedback.

These are functional native effects, not claims of original P2 JPA rendering, exact sound timbre, exact camera waveform, or hardware rumble verification. Source motion poses are separately imported from the disc.

## Reproducible fresh arena

`experimental/pikmin2_purple_flight_arena.py` regenerates the stage through current `preview_pikmin2_room.prepare/overlay`, preserving its20-red starting squad and using an explicitly bound adult. Imported presentation files contribute only models/configs; old stage/save/runtime files are not copied. Every run records source/config/model hashes and current root revision. The radius-zero spawn adjustment is documented as an engineering fixture intervention.

```powershell
python -m experimental.pikmin2_purple_flight_arena --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --converted output/pikmin2-room105 --presentation output/p2-purple-direct393/run-adult-02 --output output/purple-flight-batch3/arenas --motion output/purple-motion-batch3/import-03
```

Use a new run directory and set `PIKMIN_P2_ROOM_WINDOW=960x540`. Replacement-main fixtures must explicitly initialize and centre that window; source ancestry alone does not prove observed adoption. Runtime evidence must distinguish actual full throws from staged descent, verify a live squad/active gameplay, and identify fixture provenance `status=built` before launching.

## Regular Purple preview

`scripts/preview_pikmin2_emergence.py` accepts `--purple-motion <bank>` alongside `--purple` and `--pod`. It validates and stages all 34 source poses and the motion config, enables the flight profile and adds the impact opt-in to the private copy of the Purple config. Existing callers retain their prior defaults. It does not invent direct-damage receiver bindings or change campaign checkpoint contents. Violet conversion remains available in this preview, so players can create and throw Purples normally.

The complete staging command passed with local Emergence `import-03`, Atlas Pod `atlas-01`, Purple foundation `import-05` and corrected motion `import-03`. Its fresh output is `output/purple-flight-batch3/playable/0d03679d37ef4a8aa111915e503b9611`; `preview.json` retains the correct source unit name and reports `purple_motion: true`. This staging check is not controller acceptance.

## Validation status

The focused root suite passes 56 tests and eight subtests across Purple/White foundation, impact references, direct damage, poison, Pod, source motion and fresh arena preparation. Compiled Purple direct, earthquake and White poison policy tests pass. Fresh arena checks cover 20 starting records, the correct native adult ID, unchanged source assets, and rejection of missing presentation before output creation.

Motion imports `output/purple-motion-batch3/import-03` and `import-04` match byte for byte across 36 files; `repeat-hashes-03-04.json` records the comparison. Each pose uses weighted source transforms, including animated scale, Purple body color and the growth attachment matrix. The config hash is `f5bbf867c6ab9db3b0795ae22a5fd233bef761f931a16835f7542987b7847798`. Earlier imports 01/02 had an invalid config row order and are retired; a regression test now rejects that order.

Native production revision: `12096ee2848b176d82137374d60e6edb00fded74`, fast-forwarded from `ac86dc0d4fe433d6e26d2180526c4d17877ffe58`. Final integrated revision `f9e139d86afab0b7581599f2178ee1a95dcf33af` adds only the standalone tests described below. The maintained Release build passes with JAudio ON, native optimization OFF and randomizer test hooks OFF. `output/purple-flight-batch3/maintained-build-02.log` records the build; the final Ninja dry run reports no work. Maintained executable SHA256: `d2b9c49a42561a2c70151a337a1841c1d413c513cc9d5f5f9da34bdbbcc595f8`. The source export contains 1,577 files and excludes binaries, local assets and untracked runtime state.

`tools/test_p2_purple_flight_actual.cpp` compiles the actual production flight module against minimal Piki/manager/feedback test doubles. It passes disabled/unarmed/Red/dead exclusions, phase timing, nearest living organic target selection, zero-distance homing, cancellation, and preservation of original flags. Regressions specifically interrupt a pause with reset and rearm a pause/descent: introduced flags must clear and the next flight must not inherit them. These are module-level tests, not substitutes for live actor death, physical multi-target collisions or full scene teardown.

```powershell
g++ -std=c++17 -I native/tools/p2_purple_flight_stubs -I native/pc_port native/pc_port/pc_p2_purple_flight.cpp native/tools/test_p2_purple_flight_actual.cpp -o output/purple-flight-batch3/test-flight-actual.exe
# Run from a disposable working directory: the test writes/removes its own flight config.
```

`output/purple-flight-batch3/runtime-final-06.log` passes against immutable `fixture-final-06/provenance.json` (`status: built`). The test waits for the captain's Walk state, observes 20 live Reds, rejects a Red flight arm, then converts one to a flower Purple. It interrupts one ascent and reuses the actor for a full physical ground throw. The apex remains at Y=49.283 with zero velocity throughout the 0.257-second observed pause. Descent reaches the floor and recovery is observed for 0.285 seconds, within one frame of the 0.3-second contract. Ground feedback counts one entry, four trail bursts and one impact, with three native effects created and one sound/camera request.

A second complete captain throw collides with the explicitly bound native adult, queues exactly 50 damage and leaves no active flight state. Cumulative feedback is two entries, eight trail bursts and two impacts. The fixture prepares captain/Pikmin modes and positions, converts maturity/species, and holds the adult at its starting position; it never injects a descending Purple position or velocity. The adult result proves real collision dispatch and queued damage; prior batch evidence separately demonstrates normal damage resolution and death/corpse behavior.

Audio uses the fixture's dummy output device, so a sound request is not audible acceptance. Rumble reports no connected controller (`-2`, zero accepted requests). Full controller/campaign sign-off, original P2 effect/audio fidelity, and existing dwarf crush acceptance remain separate gates. The first run began before the normal-gameplay gate and failed the pause check; its smoke-obscured images and pause result are not acceptance evidence.

## Final fixture baseline adoption

The final run regenerated a new arena at `output/purple-flight-batch3/arenas/cd1674e4751e4780a3f8b8453375d93d` and reused the unchanged, built fixture 06. Its executable hash is `c8cb6cfba749ff52004343cc9536554520d06648e8a33fa3051ce21dd7697d36`; the private production executable hashes to `344a11f55d0a6da5d3e1af5ce29f5dd36a6a4aacd5f2560633cc347803c73680`. `runtime-adoption-final.log` exits zero, holds Y=48.324 throughout the observed 0.279-second pause, observes 0.276 seconds of recovery, and again queues 50 adult damage. The two complete throws produce two entries, nine trail bursts and two impacts.

The arena manifest records root `8fb94cd3457f5f99310e92a252d22c6285db7420` with implementation work uncommitted; overlay SHA256 is `4abe0e950a1c7f137572d976ed62fd5a794c079683253a13bde8bfee47762a5a`. The private native worktree is clean at the runtime revision above. Maintained export preserves its inherited dirty `creatureCollision.cpp`/`goalItem.cpp` working files and untracked research checkout; no cleanup or original-checkout edits were performed.

The live window has a 960×540 client. Win32 observes outer bounds `(365,232)-(1341,811)` on DISPLAY1 with work area `(0,0)-(1707,1019)`; horizontal centering is within one pixel, with Windows DPI/nonclient metrics affecting outer-frame vertical placement. The fixture explicitly sets the size and calls the shared center function. Active Walk gameplay and 20 live starting Reds establish no immediate extinction. Root inspected the final pause, descent and impact captures: the airborne Purple body/growth attachment and changed flight pose are visible. Impact creation is also logged; these captures are not a complete effects or camera-waveform audit.

[Runtime adoption](https://github.com/4laric/pikmin-randomizer/issues/393#issuecomment-5656894664), [remaining runtime matrix](https://github.com/4laric/pikmin-randomizer/issues/393#issuecomment-5656898084), and [shared feedback review](https://github.com/4laric/pikmin-randomizer/issues/186#issuecomment-5656898235) record the handoff. Distinct platform collision, death during the pause and complete scene/campaign re-entry still need live gameplay coverage; a successful scripted throw is not blanket family acceptance.
