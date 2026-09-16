# BigFoot69 natural Walk translation acceptance (#574, parent #569)

Lane `enemy-bigfoot69-walk`, issue #574. Implementation owner: Codex through
shared account 4laric; executing contributor Muse Spark 1.3. Prior slice
l62 (#502) left BigFoot69 gate 2 UNTESTED (Stay->Wait, no Walk in the
1500-tick window) while Houdai66 walked. This slice extends the window to
4500 observed ticks, wakes BigFoot with the staged captain, and measures
Walk translation separately from residual P1 host locomotion.

## Owned changes (this slice)

Native (private `output/autofill-native-574`, branch to be recorded at
handoff; no shared files touched):

- `pc_port/pc_p2_long_legs.cpp` -- `P2_LONG_LEGS_WALK_END` now appends net
  `start=x,z end=x,z` (walk-entry vs walk-exit body positions) alongside
  the owned applied `distance`/`seconds`, so the audit measures source-rule
  translation separately from host drift. No behavior change.
- `pc_port/pc_p2_long_legs.h` + `.cpp` -- additive read-only
  `pc_p2_long_legs_state_name()` for the fixture wake diagnostic.
- `tools/p2_muse_longlegs_fixture.cpp` -- walk window 1500 -> 4500
  observed ticks; `P2_MUSE_WALK_BIGFOOT_STATE` diagnostic at wake+1500;
  drain timeout 9000 -> 15000. Captain wake/retreat pattern unchanged
  (staged positions only; the actor is never touched).

Root (private `output/autofill-root-574`):

- `experimental/pikmin2_bigfoot69_walk_acceptance.py` -- pure log auditor
  (BigFoot Walk natural PASS rule, Houdai-preserved rule, no-carcass
  static audit) plus a thin `run()` reusing the l62 arena/build helpers.
- `tests/test_pikmin2_bigfoot69_walk_acceptance.py` -- 10 unit tests
  (natural pass, missing/teleport/short-net/old-marker/injected/
  wrong-generator failures, Houdai preservation, carcass audit).
- This doc.

## Acceptance mapping

- Fresh fixture wakes source69 naturally (staged captain visit inside the
  75u private radius; Stay->Land->Wait->Walk via the owned FSM) and the
  4500-tick window contains the full 0.6 s + 5 s + 10 s source cycle with
  margin at any render frame rate.
- Owned steps vs net displacement are reported separately
  (`owned/drift` in the validation JSON); legs stay bind-pose, no IK
  (documented approximation carried over from #502).
- Houdai66 no-carcass behavior and prior gates preserved (Houdai WALK_END
  re-observed in the same run; lane26 evidence otherwise untouched).
  Held-treasure kosi-drop/carry/receipt is an explicit provider follow-on
  to #491 (needs lane-06 treasure objects) -- gate 5 stays source-backed
  N/A and never claims that follow-on.

## Gate table (to be filled from the fresh run)

- Source ID: 69 `BigFoot`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | TBD (fresh BIND expected) | fresh native.log | natural |
| 2. Autonomous movement and animation | TBD (fresh WALK_END expected) | fresh native.log | natural |
| 3. Attacks and receivers | PASS (preserved) | lane26 evidence, see #502 handoff | natural |
| 4. Death and corpse | PASS (preserved) | lane26 evidence, see #502 handoff | natural |
| 5. Actual transport and reward | N/A (source-backed) | Houdai.cpp:71 / BigFoot.cpp:69 disableEvent EB_LeaveCarcass; held treasure -> #491 follow-on | N/A |
| 6. Cleanup and re-entry | PASS (preserved) | lane26 evidence, see #502 handoff | natural |

## Checker output

(To be recorded after the fresh run.)