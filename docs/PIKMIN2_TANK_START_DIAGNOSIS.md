# Tank single queued Start reproduction

Issue #207. This follows the exact original P1 Tank display-list ownership finding and tests whether one Start edge through the production queue can expose the same day-end stale draw.

## Contract

`scripts/pikmin2_tank_start_fixture.cpp` runs the original P1-only arena and naturally provokes Tank attacks by captain proximity. After gameplay begins it does not call `MoviePlayer::requestSkip` directly. Upon the first observed active demo56, it schedules exactly one Start edge. A private observation hook pumps `pc_bbft_start_button(true)` immediately before the existing `pc_bbft_take_skip()` consumer in `MoviePlayer::update`; the next update releases the button. This preserves the production edge queue, consumer and `movieSkipAllowed` guard. Pumping at the consumer avoids unrelated window polling overwriting a fixture-injected edge.

This is injected input through the production queue, not physical keyboard/controller QA. The fixture still skips startup movies and dismisses the startup tutorial through normal Controller A processing; both cases share that setup. No enemy state, velocity, animation counter or action is forced.

The same binary runs the no-edge control when `TANK_DIAG_START` is absent. All original P1 Tank resource, owner-heap and byte-hash probes remain. No imported Tank appearance or water display is loaded. Native parser warnings, rather than a successful movement gate, are the diagnostic outcome. The observation is bounded to 120 seconds; a timeout in results is explicitly retained.

## Build and evidence

Private completed native base: `b602d8c43dc6a1132821f787b99a28097c3c7521`. Exact frozen input chain and source hashes: `output/p2-lifecycle-batch/tank-start-link-01/commands.json`, referencing the prior private heap probe links. Executable SHA256 `76bc7a67c2f4d9b15f9cf612eda1d83e4db7c75abf886352a12c84843d6f2822`. No production/shared native source, converter or build was changed.

Driver: `scripts/test_pikmin2_tank_start_native.py`, cases `start` and `control`, with local assets/profile, immutable private executable and fresh output paths. The Start parser requires exactly one schedule/delivery/consumer; it distinguishes guard denial from allowance and rejects unexpected control input. Four focused tests pass.

Results and limits follow after the paired runtime completes. A negative result is not evidence that every player timing is safe; a positive result would still require stock-upstream verification before labeling it an upstream regression.

## Single-edge result

The single queued Start reproduced the failure. The fixture scheduled once at `cinemas/demo56.cin`, ready frame 834; the queue logged one delivery, the native consumer logged `allowed=1`, and the next update released the button. There were no direct late `requestSkip` calls.

All seven original `tekis/tank/tank.mod` display lists changed to the same byte hashes seen in the earlier repeated-skip probe, after their owner Teki heap was reset. The first 1792-byte list changed `01273b84 -> 63a3eab6`; the following GX report was a truncated vertex at 1791/1792. Seven DESYNC events were emitted (14 lines including each event's vertex-descriptor detail).

Report: `output/p2-lifecycle-batch/tank-start-one-01/start-result.json`; session `0663f7a96ab8406b9a85390bbff02ed2` contains `heap-evidence.json`. It recorded 22 native Attack samples and timed out at the 120-second observation bound while in day-end flow. The timeout is not relabeled a passing playthrough.

This removes the every-frame direct API call as a necessary trigger. A single injected edge through the production queue is sufficient in this preview arena. Physical Start timing, normal campaign mode and stock upstream remain separate validation gates. No shared fix was made.

## Identical-binary control

`output/p2-lifecycle-batch/tank-start-control-01/start-result.json` records zero scheduled/delivered/consumed Start edges, 23 native Attack samples, demo56 and three Teki-heap resets, with zero GX warnings. Session `a5a466c2e9be45b7954a4403c8e302e0` ran to the same 120-second bound. It used the exact same executable SHA256 as the one-edge case. Thus the input-triggered stale-list draw is reproducible through the queue under these fixture conditions; it is not merely a difference between separately compiled skip/control binaries.

Both cases are diagnostic observations, not completed campaign/save runs. A reviewable fix can now be evaluated against this pair, but this batch deliberately changes no shared rendering, heap or movie policy.
