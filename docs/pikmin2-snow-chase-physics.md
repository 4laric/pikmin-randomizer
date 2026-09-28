# Snow chase: real physics tick regression (#120)

`experimental/pikmin2_snow_chase_physics.py` instruments a private copy of the room fixture. It records 60 real engine ticks following actual `TaiTracingAction::act` calls. Production files and playtest bundles are unchanged.

The fixture sets `mIsFrozen` on the test actors to suppress AI and animation updates. In `Creature::update`, this guard does not suppress `moveNew` or `moveRotation`, but it does skip `Creature::updateAI`, which normally calls `moveVelocity`. The private fixture therefore invokes native `moveVelocity` once after each tracing command. This controlled acceleration phase uses the current delta time; the next ordinary movement tick may have a different delta time. Commands issued after `PlugPikiApp::idle` are consumed by the following ordinary engine tick; the fixture does not manually invoke or duplicate the movement/collision tick. Native collision, ground response, acceleration and automatic facing remain enabled. A flat empty region and relocated Pikmin keep incidental combat out of this measurement.

Both modes use tracing speed 50. The opt-in Snow profile turns first and sets heading-relative horizontal target velocity, preserving injected desired Y (+7, then -3). The absent-profile baseline points desired velocity directly toward the target and clears desired Y. At tick 31 the target moves across the actor, exercising a second turning arc. Each command is paired with next-tick position, current and target velocity, facing, ground height and native delta time.

Acceptance requires all 60 ordered command/observation pairs, unchanged consumed target velocity, horizontal command magnitude 50, the expected desired Y behavior, finite grounded motion, physical displacement and successful completion. Reporting a target velocity alone is insufficient. The P1 ground projection may preserve the length of the full desired vector before projecting; this test does not equate desired horizontal speed with exact physical speed.

Use the module's `instrument --source ... --output ...` subcommand against an immutable source snapshot, then compile/link privately against matching native objects. The `run` subcommand takes the same `--assets`, `--converted`, `--pod`, `--snow`, `--exe`, and fresh `--output` paths as the existing Snow fixtures. Add `--policy` pointing to the source chase import for the opt-in run; omit for baseline. Use `SDL_AUDIODRIVER=dummy` and the MinGW runtime directory in PATH. Binary hashes are included in evidence.

This is controlled chase steering followed by real native physics. Natural chase-state selection, source animation timing, uneven-terrain navigation, and full Pikmin 2 FSM/locomotion parity remain unmeasured.

## Recorded validation

Both `output/p2-chase-physics/opted-corrected/evidence.json` and `baseline-corrected/evidence.json` passed with exit 0: 60 commands, 60 physical observations and the retarget in each run. The private executable SHA256 is `dc2ea7be39fb079a6dd84b1ce938c1da50e1b2f8010d02855f97fb6af1d1f3bd`. It links 45 copied, hash-verified inputs from native `2dcced12`, with matching archived native headers/source; manifest and recipe are under `output/p2-chase-physics/snapshot-final`. No shared build inputs were consumed after that snapshot.

| Measurement | Opt-in | Absent profile |
|---|---:|---:|
| Observed delta-time sum (seconds) | 1.8772 | 1.8221 |
| Horizontal path length | 88.5846 | 83.0900 |
| Final displacement from start | 45.7749 | 27.3642 |
| Maximum horizontal current speed | 50.4849 | 49.9992 |
| Maximum body-height error from ground | 0 | 0 |

The first opt-in command was `(8.6824, 7, 49.2404)` at 10 degrees; its first physical position became `(0.0685, 0, 0.3886)`. Baseline commanded `(50, 0, 0)` at unchanged initial facing; its first position became `(0.0823, 0, 0)`, while native automatic facing began turning. Both reversed their horizontal target direction after retargeting. These are separate runs with different delta times, so path lengths are observations, not a controlled speed comparison. The opt-in current-speed peak slightly above 50 is consistent with the native ground projection preserving full desired-vector length including Y.

The original `opted` run is retained as failed fixture evidence: AI freezing skipped acceleration, producing zero horizontal displacement. It is superseded by the explicitly controlled native-acceleration fixture, not treated as a gameplay defect.
