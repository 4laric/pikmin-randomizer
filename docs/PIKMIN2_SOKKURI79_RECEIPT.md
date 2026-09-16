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

## Gate table (fresh run evidence to be filled)

- Source ID: 79 `Sokkuri`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (preserved #495) | TBD fresh BIND | natural |
| 2. Autonomous movement and animation | PASS (preserved #495) | TBD | natural |
| 3. Attacks and receivers | PASS (preserved #495) | TBD | natural |
| 4. Death and corpse | PASS (preserved #495) | TBD fresh DEAD | natural |
| 5. Actual transport and reward | TBD (fresh receipt) | TBD onion:p2:79 new=1 + new=0 | natural |
| 6. Cleanup and re-entry | UNTESTED | re-bind is not scene re-entry | unobserved |

## Checker output

(To be recorded after the fresh runs.)