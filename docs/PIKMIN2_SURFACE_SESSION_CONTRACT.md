# P2 surface session contract (#132, lane surface-session-provider-contract)

Schema `p2-surface-session-1`. Pure engine-free state machine promoting the
accepted provider-save-dayclock-anchor-audit into a consumable contract for
P2 overworld planners, starting with Wistful Wild (course `last`). No
native build, no runtime, no gameplay claim, no ADMIT.

## Accepted evidence cross-reference

- Audit inventory: `output/workflow/autofill/planning-shards/provider-save-progression/prepared/save-anchor-audit/out/inventory.json`
  (gamePlayData.cpp sha256 `4d6c7586...7e020`, 12 anchors;
  singleGameSection.cpp sha256 `6ff0eafb...5ce4be`, 22 anchors).
- Audit verdict (review-ready): day_clock, sunset_loss, debt_equipment,
  louie_president, save_migration anchored with file:line; sprout_regeneration
  absent from both files (retail anchor elsewhere, out-of-scope note);
  `gameSingleGameSection*.cpp` absence recorded verbatim.
- Field anchors consumed: `advanceDayCount` (:216), `CaveDayEndState`
  (:183/:209), `mCaveSaveData.mTime`/`mCurrentTimeOfDay`/`setTime`/sun-gauge,
  `mPokoCount`/`mCavePokoCount`/`mDebtProgressFlags` (:455-466),
  `NAVIID_Olimar/Louie`/`mNaviLifeMax`, `mCaveSaveData.clear`/`mMailSaveData.clear`/
  `mCurrentCaveID`/`mCurrentFloor`/`mIsInCave=false` (:490-491/714/723-724).

## Checker (`experimental/pikmin2_surface_session_contract.py`)

`check_transition(state, event)` over `begin_day | sunset | save | reload |
deliver_receipt | enter_cave | exit_cave`, returning
`(ok, new_state_or_None, reason)`. Enforced: monotonic day (rewind
rejected), single sunset per day, save-after-sunset, course-matched reload,
exactly-once receipts, cave enter/exit gating, non-negative pokos,
verbatim-carried sprouts (recompute unsupported), malformed input raises
`SessionContractError`, unknown events rejected. `request_integration`
rejects all four missing native pieces by name. `wake_criteria(course)`
reports all-false readiness for tutorial/forest/yakushima/last.

## Existing behavior vs missing integration

Existing (anchor-backed): monotonic day count, sunset time snapshot,
verbatim poko/debt carry, captain life flags, cave-flag gating of cave
fields, exactly-once receipt identity shape. Missing (explicitly rejected,
never assumed): native sunset driver, native save serializer, native
receipt ledger endpoint, native generator-cache restore.

## Minimal landing prerequisites + planner wake criteria

1. Disc `user/Abe/stages.txt` bytes + recorded SHA-256 (per-course records).
2. Anchor re-verification against the recorded source hashes on change.
3. Admitted family receipt endpoints (lane-06 provider) before P1 receipts.
4. Native sunset/save/ledger/cache integration before any runtime claim.
5. Per course (tutorial/forest/yakushima/last): record decoded + entrances
   known + endpoints admitted; all currently false.

## Tests

`tests/test_pikmin2_surface_session_contract.py`: 11 tests covering the
full day chain, save/reload roundtrip, duplicate-receipt, rewind,
double-sunset, save-before-sunset, reload-without-save, course mismatch,
cave gating, malformed/unknown inputs, negative pokos, missing-integration
rejection and wake criteria. Log in the lane out/ directory.
