# Sokkuri79 exactly-once ordinary Onion receipt (#578, parent #569)

Lane `enemy-sokkuri79-receipt`, issue #578. Implementation owner: Codex
through shared account 4laric; executing contributor Muse Spark 1.3.
Follow-on of #495 (natural haul proven to ~573u, receipt missing because
the preview room runs sessionless by design).

## What this slice does

- Boots the Sokkuri arena fixture WITH a real randomizer session
  (`--randomizer-seed` bootstrap + `state.txt` refresh, same pattern as
  lane-06 `p2_ordinary_receipt_runtime.py`).
- Stages the lane-19 Pod package so carriers have a real Red container
  goal (the #495 cargo-free arena has none).
- Natural FreeMode combat -> combat-culminated corpse -> natural haul ->
  Pod `GoalItem::suckMe` -> bound-source receipt `onion:p2:79:<stage>`.
- Runs TWICE sharing one session ledger: run 1 expects `new=1`, run 2
  (fresh arena, same generator uid) expects duplicate `new=0`.
- Transport PASS needs BOTH the receipt line AND natural-carry markers;
  a receipt alone is interface-only.

## What this slice never does

No Transport/kill/credit injection (the fixture contains no suckMe call),
no health/state writes, no forget/re-entry (the bind must survive until
the single-use delivery consumes it; gate 6 stays UNTESTED), no shared
cargo edits, no ADMIT, no admission-ledger writes. ElecBug28 stays
deferred until this receipt lands.

## Owned changes

- `native/tools/p2_sokkuri79_receipt_fixture.cpp` (new): session-gated
  natural drain/haul/deliver observer with honest timeout FAILs.
- `experimental/pikmin2_sokkuri79_receipt.py` (new): receipt/carry
  auditor + Pod-enabled arena prepare + two-run session driver.
- `tests/test_pikmin2_sokkuri79_receipt.py` (new): 9 unit tests.
- This doc.
- Dependency (separate commit, reviewed #495 `ecc80b72` bind hunk only;
  l55 fixture file excluded): `pc_port/pc_p2_sokkuri.cpp` binds source 79
  at setup and clears it on forget.

## Runtime finding: BLOCKED on a session-capable Sokkuri scene (exact defect)

Two session-enabled launches were built and run (leased private build,
fixture provenance `built`, fresh Pod-enabled arenas, 960x540 window,
squad=20). Both timed out at the fixture session gate with 16000+
`P2_SOKKURI79_SESSION_WAIT` lines and `pc_randomizer_ready()` never true:

- Root cause (read-only source, no shared edits): with
  `--experimental-pikmin2-room`, `pc_bbft_init` takes the lane-03
  bridge-only path (`pc_randomizer_p2_room_bootstrap`: bindings only, no
  session, "the preview never holds") and never calls `pc_randomizer_init`.
  `enabled`/`ready` stay false, so `pc_randomizer_p2_corpse_delivered`
  cannot grant. The room is sessionless BY DESIGN, not by bug.
- The only other scene with a full session is the story campaign, but no
  generated-placement slot exists for source 79 (l52 covered 41/57/58/78;
  79 has a catalog row but no slot uid), so no Sokkuri can appear there.
- Everything else in this slice is staged and proven: family bind fires
  (`P2_SOKKURI_DELIVERY_BIND`/`P2_SOKKURI_BIND` in both logs), Pod anchor
  stages (`P2_POD_READY`, `P2_ROOM_READY`), arena/session/bootstrap/state
  plumbing validates, and the 9 unit tests pass.

## Gate table (honest: gate 5 stays open, gates 1-4 preserved #495)

- Source ID: 79 `Sokkuri`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (preserved #495) | output/muse-wave/l55/run-carry3/capture/native.log:776 BIND chain | natural |
| 2. Autonomous movement and animation | PASS (preserved #495) | output/muse-wave/l55/run-carry3/capture/native.log:876 carry rows | natural |
| 3. Attacks and receivers | PASS (preserved #495) | output/muse-wave/l55/run-carry3/capture/native.log:797 drain 105 to 15 | natural |
| 4. Death and corpse | PASS (preserved #495) | output/muse-wave/l55/run-carry3/capture/native.log:851 DEAD prior 15 | natural |
| 5. Actual transport and reward | BLOCKED | no session-capable Sokkuri scene (see finding); haul-only evidence stays carry, never reward | unobserved |
| 6. Cleanup and re-entry | UNTESTED | re-bind is not scene re-entry | unobserved |

## Proposed bounded follow-on (for integrator #437)

Either (a) a 79 generated-placement slot (placement family, coordinate
through #186; seed then binds 79 in a story session with a real Onion and
this lane exact receipt flow applies unchanged), or (b) an
integrator-blessed room full-session mode (shared `pc_bbft` change, NOT
this lane). ElecBug28 stays deferred. No shared edits were made here.

## Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_SOKKURI79_RECEIPT.md
79 Sokkuri (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [BLOCKED]
  6. cleanup_reentry    ignored [UNTESTED]
EXIT=0 (gates 1-4 preserve #495 historical evidence, cited verbatim above;
gate 5 could not advance: no session-capable Sokkuri scene exists)
```