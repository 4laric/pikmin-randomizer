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

## Fresh runtime evidence (generation 3): exactly-once ordinary receipt PASS

The previous blocker (room is sessionless by design because
`pc_bbft_init` takes the lane-03 bridge-only path with
`--experimental-pikmin2-room`) is closed **without any shared-file edit**:
the replacement-main fixture (owned) enables the full session itself
(`if(!pc_randomizer_enabled())pc_randomizer_init(argc,argv);` inserted into
main from this lane's splice logic), and the arena is deliberately
cargo-free so `pc_p2_preview_deliver` returns false and
`GoalItem::suckMe` -> `pc_randomizer_p2_corpse_delivered` is the real
endpoint that fires.

Runs (same session ledger `<runs>/campaign/p2-delivery-receipts.txt`;
fresh arena per run, cargo-free, session bootstrap + state refresh):

- run1 `output/workflow/autofill/enemy-sokkuri79-receipt/runs/run1/b643942fa892401b879fc70ce3f0da4b`
  (`capture/native.log` sha256 `87e29af12abeaffe7059330b4f5311c0b0494d5241c9122e60f0aa6cb441815f`)
- run2 `output/workflow/autofill/enemy-sokkuri79-receipt/runs/run2/e71c5aa9c590406091fd817cda9a25b5`
  (`capture/native.log` sha256 `31cfc2a6b5d217a8601730a85ec199c9d6012d28b65e58094174bedee8b11c91`)
- fixture `fixture-session/fixture.exe` sha256
  `fdac270cb294c2788ecab0fdee64ee5f0e937799095b5452c041cb15e07e96be`
  provenance `built` vs native `237a750b`.

Exact receipt (the acceptance's exactly-once pair):

```
run1 native.log:1307  P2_ORDINARY_P2_RECEIPT seed=66d576...5d84 id=onion:p2:79:0 generator=346005 new=1
run2 native.log:1346  P2_ORDINARY_P2_RECEIPT seed=66d576...5d84 id=onion:p2:79:0 generator=346005 new=0
```

Natural chain in the SAME run (run1 citations; run2 shows the identical set):

- `:8` `Experimental preview window set to 960x540 windowed and centered`.
- `:785` `P2_SOKKURI_DELIVERY_BIND generator=346005 source_id=79`;
  `:786` `P2_SOKKURI_BIND ... source_id=79 visual_only=0`;
  `:838` `P2_SOKKURI79_READY squad=20 sokkuri_gen=346005 reg=1 session=1`.
- `:843`+ seven `P2_SOKKURI_DAMAGE` hits 105.0 -> 15.0 (real InteractAttack
  drain; no health write anywhere): `:955`
  `P2_SOKKURI_DEAD ... health=0 prior_health=15.0` (combat-culminated).
- `:1014` `P2_SOKKURI79_CORPSE pellet=1`.
- `:1306` `P2_SOKKURI79_CARRY tick=900 moved=567.61 goal_dist=3.16 state=1`
  (natural free-Pikmin haul of ~568u to the container;
  `:837` `P2_SOKKURI79_POD container=1`).
- `:1308` `P2_SOKKURI79_DELIVERED_TO_GOAL tick=923 moved=567.61`; `:1570`
  `PASS P2_SOKKURI79_RECEIPT_RUN delivered=1`.
- No injection: no `P2_LL_INJECT` / `P2_LIFECYCLE_INJECT` / injected_health /
  direct transport / fallback markers in either log. Squad was staged in
  FreeMode near the actor (same staging as #495); no Transport was assigned.

## Gate table

- Source ID: 79 `Sokkuri`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | output/workflow/autofill/enemy-sokkuri79-receipt/runs/run1/b643942fa892401b879fc70ce3f0da4b/capture/native.log:786 (P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0) | natural |
| 2. Autonomous movement and animation | PASS | output/muse-wave/l55/run-carry3/capture/native.log:876 carry rows (preserved #495) | natural |
| 3. Attacks and receivers | PASS | output/workflow/autofill/enemy-sokkuri79-receipt/runs/run1/b643942fa892401b879fc70ce3f0da4b/capture/native.log:843 (P2_SOKKURI_DAMAGE 105.0 -> 15.0, 7 hits) | natural |
| 4. Death and corpse | PASS | output/workflow/autofill/enemy-sokkuri79-receipt/runs/run1/b643942fa892401b879fc70ce3f0da4b/capture/native.log:955 (P2_SOKKURI_DEAD prior_health=15.0) :1014 (CORPSE pellet=1) | natural |
| 5. Actual transport and reward | PASS | output/workflow/autofill/enemy-sokkuri79-receipt/runs/run1/b643942fa892401b879fc70ce3f0da4b/capture/native.log:1306 (natural haul 567.61u) :1307 (onion:p2:79 new=1); output/workflow/autofill/enemy-sokkuri79-receipt/runs/run2/e71c5aa9c590406091fd817cda9a25b5/capture/native.log:1346 (duplicate new=0) | natural |
| 6. Cleanup and re-entry | UNTESTED | re-bind is not scene re-entry; scene restart is not full re-entry | unobserved |

## Session-enablement disclosure (what is staged vs natural)

- Staged/instrumented: the fixture is a replacement main and explicitly
  calls `pc_randomizer_init` because the room preview would otherwise never
  hold a session. The arena is cargo-free so the Pod path cannot claim the
  corpse. The 20-red squad is deployed in FreeMode near the actor (as in
  #495) and the room is a private isolated course.
- Natural and observed: the 7-hit InteractAttack drain, death, corpse
  spawn, ~568u free-Pikmin haul into the container, `suckMe` ordinary
  endpoint, `onion:p2:79 new=1` then duplicate `new=0`.
- No shared file was edited; no ADMIT/ledger write; no Transport/kill/credit
  injection. The family bind used is the reviewed #495 `ecc80b72` hunk.

## Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_SOKKURI79_RECEIPT.md
79 Sokkuri (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    ignored [UNTESTED]
EXIT=0
```
