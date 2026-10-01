# Tank day-end display-list ownership probe

Follow-up to #207. All evidence uses private native snapshot `b602d8c43dc6a1132821f787b99a28097c3c7521`; no production code or allocator behavior was changed.

## Exact corrupted resource

The stale resource is the original P1 `tekis/tank/tank.mod`, not an imported P2 pose or the static water display. Private `StdSystem::loadShape` instrumentation records its seven display lists in owner heap 4 (`SYSHEAP_Teki`). Later DGX submissions use the same shape/list pointers with changed bytes after that heap is reset:

| List bytes | Initial FNV-1a | After reset |
|---:|---|---|
| 1792 | 01273b84 | 63a3eab6 |
| 704 | 7c374697 | 53e00eee |
| 736 | 1c27753e | 22cdf798 |
| 512 | 072701ef | eab72587 |
| 672 | 5b610747 | edd6767c |
| 1024 | efbd9515 | 72dc2720 |
| 960 | 9ad42994 | 99be7f1a |

In this process, the first failing shape is `00000258da48fe40`; its 1792-byte list is `0000025895086b40`. The changed-byte draw probe is immediately followed by `Invalid PNMTXIDX 106` and a truncated vertex at 1791/1792. Subsequent changed lists are followed by the corresponding bad opcodes/lengths. Pointers are process-specific; source path, size, and byte hashes are the durable identity.

This corrects the earlier coarse movie-log inference: the relevant owner is the enemy heap, not the movie heap. Mixed stdout/stderr line order alone is insufficient to infer the precise moment of reuse. The private stderr probes independently record owner-heap resets and changed draw bytes.

## Source path and remaining distinction

At the frozen revision:

- `include/system.h` identifies heap4 as Teki and heap5 as Movie.
- `src/sysCommon/shapeBase.cpp`, `DispList::read`, allocates aligned display-list bytes from the active heap.
- `src/sysCommon/stdSystem.cpp`, `loadShape`, caches the loaded Shape; `resetHeap` invalidates heap-owned cache entries before resetting the stack. Cache eviction exists already and does not revoke pointers held by live Teki instances.
- `src/plugPikiColin/newPikiGame.cpp`, `DayOverModeState::initialisePhaseOne`, resets Teki heap before loading the regular day-end/TakeOff movies into it.
- `src/plugPikiKando/gameCoreSection.cpp`, `hideTeki`, hides gameplay enemies only while a movie is active; `NewPikiGameSetupSection::mainRender` gates world drawing on NonGameMovie.
- `src/plugPikiColin/moviePlayer.cpp` clears the active movie flag and demo flags on completion. The fixture repeatedly requests skips.
- `GameMovieInterface::movieSkipAllowed` guards existing results/challenge/final/memcard windows. That alone does not describe ownership during the gap before a results window exists.

The observed failure is a retained gameplay Tank submitting reused enemy-heap bytes after day-end. Whether normal player input can expose the same pre-results gap needs a production-mode reproduction. The fixture calls the real skip API every active frame, which is a much stronger input pattern than a player pressing Start. This is an upstream candidate only after establishing that path outside the preview fixture; it is not yet an upstream regression claim.

A minimal fix proposal should protect the resource invariant: once the Teki heap is repurposed for a day-end scene, old gameplay Teki must not render until reloaded. Alternatively, prevent completion of a results-background movie before its owning UI takes control if that is the specific invalid transition. Do not select a broad skip ban or change allocation lifetimes without validating the intended day-end sequence.

## Private probe and reproducibility

`experimental/pikmin2_tank_heap_diagnostic.py` inserts strict, exact-match observation calls into frozen StdSystem and DGX source. `scripts/tank_heap_probe.cpp/.h` use a fixed static registry, without dynamic allocation, to record shape paths, lists, hashes and heap reset markers. The original GX submission and heap reset remain unchanged. Changed hashes and warning context are parsed with an explicit caveat that the nearest logged submission is not automatically sufficient ownership evidence for every warning.

Compiled probe: `output/p2-lifecycle-batch/tank-heap-link-01/fixture.exe`, SHA256 `a63ccfb84a4432d380b9f051a82330f68e2123422633a71faedf1cb6a594fdab`. Exact source hashes/commands are in that directory; sources were read from the frozen revision and linked against frozen link-03 inputs. Local build recipe is `output/p2-lifecycle-batch/build_tank_heap_probe.py`.

Baseline result: `output/p2-lifecycle-batch/tank-heap-absent-01/result.json`; session `5d19d989c1a84750b29da96758f319ee`, including `heap-evidence.json`. No imported profile was present. The diagnostic ended with the expected old fixture timeout (exit1), not a gameplay PASS. Four focused instrumentation/parser tests pass.

## No-late-skip control

A second private fixture keeps only startup movie skipping and never calls `requestSkip` after gameplay begins. It retains the same real proximity-triggered Tank attacks and the same pointer probes. `scripts/pikmin2_tank_heap_fixture.cpp` preserves this source; only the skip condition and bounded observation duration differ from the earlier fixture.

Executable `output/p2-lifecycle-batch/tank-heap-link-02/fixture.exe`, SHA256 `fcdc81b1dfea25ec480806525b0da0928486e2eff85164937a43abe152cd462a`. Result `output/p2-lifecycle-batch/tank-heap-noskip-01/result.json`, session `e52c8af2da804a4cad3cb962a826a696`.

The 120-second bounded observation recorded 23 native Attack samples, demo56 loading, three Teki-heap resets and normal post-attack movie completion, with **zero GX warnings**. It ended at the host timeout while waiting in the day-end flow; it is not a completed-playthrough claim. This supports a skip-transition exposure, rather than unavoidable corruption during every day-end rendering path.

There is a production input route to the same API: `pc_window.cpp` forwards Start edges to `pc_bbft_start_button`, `pc_bbft.cpp` queues an accepted edge, and `MoviePlayer::update` consumes it through `pc_bbft_take_skip()` and calls `requestSkip()`. However, the failed fixture bypasses that edge queue and requests a skip on every active frame. Exact frame timing through the production Start queue, and stock upstream behavior without the randomizer/preview, remain untested. Do not describe this as a confirmed upstream bug yet.
