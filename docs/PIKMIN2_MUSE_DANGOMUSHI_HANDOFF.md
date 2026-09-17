# Muse DangoMushi94 death/corpse and cleanup/re-entry observer handoff (#376)

Lane `dangomushi94-death-cleanup-observer` (generation 2). Owner: Codex through
the shared `4laric` account; executing Muse Spark 1.3 contributor. Parent family
work: the snagret-family batch-2 children (#376); roster row source 94
`DangoMushi` (Segmented Crawbster), role source.

## Slice summary

Deliver an additive, dependency-free observer that closes DangoMushi's missing
`death_corpse` and `cleanup_reentry` gates the moment a live bound actor
produces natural death -> corpse -> stage-boundary reset -> rebirth with
re-bind. Transport (`transport_reward`) is family-dependent and is reported
only if the family actually emits a Pod receipt; no receipt is fabricated.

The family FSM and its modules are read-only: no family change was made or
requested, so no existing-owner review is needed. No ADMIT and no ledger
writes.

## Files owned (all new, additive)

- `experimental/pikmin2_muse_dangomushi.py` - dependency-free `parse(text)`
  verdict. Requires the same generator file id across the family bind
  (`P2_DANGOMUSHI_BIND ... source_id=94`), the family death marker
  (`P2_DANGOMUSHI_DEAD ... source_id=94 health=0`) after it, the generic
  batch-3 corpse draw (`P2_BATCH3_DRAW corpse=1 key=DangoMushi clip=dead*`)
  after the death, and a second bind of the same generator after the corpse
  (re-entry/re-bind). A family Pod receipt for the same generator is reported
  as `transport_observed` but never required. Any missing leg, mismatch,
  wrong order, injected marker, or captain-down evidence yields `gate_ok`
  False. Emits no markers.
- `tests/test_pikmin2_muse_dangomushi.py` - 13 contract/negative tests
  (correlated death/corpse/re-entry, optional receipt reported, missing
  corpse, missing rebind, wrong order, generator mismatch, wrong source id,
  non-DangoMushi corpse key, injected health, raw mHealth write, captain-down
  block, empty log, proxy birth without family legs).
- `native/tools/p2_muse_dangomushi_fixture.cpp` - standalone, engine-free
  stdlib-only checker implementing the same contract; exit 0 only on a fully
  correlated run with no injected markers and no captain-down evidence.
- `docs/PIKMIN2_MUSE_DANGOMUSHI_HANDOFF.md` - this file.

## Verification (this turn)

- `py -3.12 -m pytest tests/test_pikmin2_muse_dangomushi.py -q` -> 13 passed.
- Standalone checker compiles clean under `g++ -std=c++17 -Wall -Wextra
  -Werror` and both directions behave: correlated good log -> exit 0
  (`P2_MUSE_DANGOMUSHI_GATE46 ... gate_ok=1 death_corpse=1 cleanup=1
  reentry=1 transport=1`); injected log -> exit 1
  (`gate_ok=0 ... injected=1`).
- No native build, no runtime run, no shared-file edits.

## Six arena gates (honest, prior gates preserved)

Source ID: 94 `DangoMushi`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED (preserved) | Family module `native/pc_port/pc_p2_dangomushi.cpp` emits `P2_DANGOMUSHI_BIND generator=<id> source_id=94`; prior family acceptance in `experimental/pikmin2_dangomushi_behavior.py`. Not re-driven here. | natural (prior) |
| 2. Autonomous movement and animation | UNTESTED (preserved) | Prior DangoMushi roller FSM acceptance (`pikmin2_dangomushi_behavior.py`, `P2_DANGOMUSHI_STATE`). Not re-driven here. | natural (prior) |
| 3. Attacks and receivers | UNTESTED (preserved) | Prior roller attack/flick + damage admission (`pc_p2_dangomushi_invulnerable`). Not re-driven here. | natural (prior) |
| 4. Death and corpse | BLOCKED | Observer ready; no production driver exists to produce a natural free-squad death and corpse for this species (family module is read-only; no family change requested). Contract pinned by tests/checker. | natural (n/a - not run) |
| 5. Actual transport and reward | UNTESTED | Family-dependent (boss drop semantics). Observer reports `transport_observed` only if the family emits a Pod receipt; none observed, none fabricated. | natural (n/a - not run) |
| 6. Cleanup and re-entry | BLOCKED | Observer ready; requires a stage-boundary reset + real generator rebirth with re-bind, which no current driver produces for this species. Contract pinned by tests/checker. | natural (n/a - not run) |

Prior gates are restated for continuity only; this slice adds no new runtime
PASS. The observer and checker are fail-closed and emit no markers, so a
future natural run closes gates 4/6 with zero observer changes.

## Exact blocker

Gates 4 and 6 need a production driver that (a) lets a real free squad deal
the source damage to a live bound DangoMushi and (b) performs a stage-boundary
reset plus generator rebirth. Adding that driver is a family-module change and
therefore requires existing-owner review (#376 / lane-25 family claim); it is
not requested here. The observer contract, negatives, and standalone checker
are complete and validated, so the remaining work is driver-only.

## Captain safety (baseline #632)

No runtime run was performed, so no guard adoption is recorded. Any future
runner for this lane must adopt `scripts/p2_fixture_captain_guard.h` (or a
tested equivalent): check `orimaDead`, `NaviDead` and `HP<=1` before
pause/movie returns or observed ticks, emit `CAPTAIN_DOWN` and exit BLOCKED,
park the captain outside attack reach when not testing captain hits, and
record guard/source hashes. The observer already maps captain-down tokens to
`blocked`/`captain-down`, never a PASS.

## Boundaries

No proposal/manifest writes; no family edits; no ADMIT; no ledger writes; no
runtime/gameplay acceptance claimed.


## Generation-3 reassessment (attempt 641f7f15)

Three integrated prerequisites were inspected against this slice's blocker
(no production driver for a natural free-squad death + stage-boundary reset +
generator rebirth):

- `shard-enemies-1-snagret70-p0` (native `009f0937`, issue #376): the merge is
  the ElecBug28 delivery-bind + receipt fixture; it adds no DangoMushi
  natural-death or reset driver.
- `enemy-elecbug28-gate5-adjudication` (root `15fcbb69`, issue #585):
  tooling adjudication only (native null); no driver.
- `shard-enemies-1-pom-actor-provider` (native `c2790169`, issue #448): the
  Candypop pom actor-birth seam; not the DangoMushi driver.

The existing `experimental/pikmin2_dangomushi_behavior.py` stages the squad
near the actor for FSM observation (gates 1-3) and does not drive combat,
death, haul, or a stage-boundary reset. No registry lane or new artifact
provides that driver. The dependency is therefore still unresolved and no
prerequisite merge was needed (none touches this slice's files).

Remaining concrete gap: a family-side (or approved lifecycle) driver that
(a) lets a real free squad deal source damage to the live bound DangoMushi,
(b) observes the host corpse pellet, and (c) performs a stage-boundary reset
plus generator rebirth with re-bind. That is a family-module change requiring
existing-owner review on #376; not requested here.


## Generation-4 reassessment (attempt 124b128b)

The prerequisite set was inspected again, including the newly added
`shard-enemies-5-bluekochappy44-observer` (#461, done, tooling-only: three
Python observer files, native null). None of the four integrated
prerequisites provides the missing DangoMushi production driver:

- `shard-enemies-1-snagret70-p0` (#376): SnakeWhole70 P0 source audit
  (Python tooling).
- `enemy-elecbug28-gate5-adjudication` (#585): tooling adjudication (native null).
- `shard-enemies-1-pom-actor-provider` (#448): Candypop pom actor-birth seam
  (native `c2790169`), unrelated to DangoMushi death/cleanup.
- `shard-enemies-5-bluekochappy44-observer` (#461): tooling observer (native null).

No registry lane or new artifact drives a natural free-squad death + host
corpse + stage-boundary reset + generator rebirth for DangoMushi. The
dependency is still unresolved; no prerequisite merge was needed (none touches
this slice's files). Observed worktrees remain clean at root `b8c52bde` /
native `e663a45f`.
