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

## Fresh run evidence (run-bigfoot69-near)

LOG = `output/workflow/autofill/enemy-bigfoot69-walk/run-bigfoot69-near/9d6c7680676e4b0791423634265c1571/capture/native.log`
Fixture `fixture-bigfoot69/fixture.exe` (`15f40728...da29cfe`, provenance
`built` against native `9ac7cee6`), fresh arena via `prepare_near`
(BigFoot at (150, 1870)), `PIKMIN_P2_ROOM_WINDOW=960x540`, squad=20,
501.5 s wall. Validator: 10/10 unit tests green; this log validates
`PASSED True` (`muse-bigfoot69-validation.json` beside the log).

- Window: LOG:7 (`Experimental preview window set to 960x540 windowed
  and centered`). READY squad=20: LOG:746. No `Extinction` in the log.
- BIND: LOG:730 (Houdai 312001) and LOG:731 (BigFoot 312002,
  `native_fsm=implemented`). Natural wake: Stay->Land (LOG:750) ->Wait
  (LOG:756) after the staged captain visit; no actor teleport, no state
  or health writes anywhere (`P2_LL_INJECT` absent).
- BigFoot walks (all natural FSM transitions with STATE lines):
  - LOG:976: owned=454.3 net=34.8 (early walk with residual P1-opposed
    drift, honestly reported, not selected).
  - LOG:1500: owned=35.2 net=31.0 in 9.52 s (target reached, motion stops).
  - LOG:1642: owned=143.3 net=143.4 in 2.05 s = 69.9 u/s ~ source 70,
    Flick-interrupted (source-correct interrupt).
  - LOG:3622 (selected): owned=223.8 net=223.8 drift=+0.0 in 3.20 s =
    69.9 u/s ~ source 70 u/s budget 87.5, STATE Walk at LOG:3551.
  - Afterwards BigFoot walked into the squad area and Flick-loops
    source-correctly (accumulate -> Flick), confirming the prey target rule.
- Houdai preserved: LOG:1048 (38.5u/0.15s) and LOG:1286 (57.4u/0.23s =
  249.6 u/s within source 250 budget).
- Bonus tail limit (honest, not gated): the Houdai drain never connected
  (HP frozen, Flick/Shot lock) and the fixture exited 1 with
  `FAIL ... drain_timeout` at LOG:10164. Houdai natural death stays
  preserved from #502/lane26, not re-claimed here.

## Gate table

- Source ID: 69 `BigFoot`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | output/workflow/autofill/enemy-bigfoot69-walk/run-bigfoot69-near/9d6c7680676e4b0791423634265c1571/capture/native.log:731 (BIND generator=312002 species=BigFoot native_fsm=implemented) | natural |
| 2. Autonomous movement and animation | PASS | output/workflow/autofill/enemy-bigfoot69-walk/run-bigfoot69-near/9d6c7680676e4b0791423634265c1571/capture/native.log:3622 (WALK_END owned=223.8 net=223.8 seconds=3.20 avg=69.9 u/s ~ source 70) + output/workflow/autofill/enemy-bigfoot69-walk/run-bigfoot69-near/9d6c7680676e4b0791423634265c1571/capture/native.log:3551 STATE Walk; legs bind-pose, no IK (documented approximation) | natural |
| 3. Attacks and receivers | PASS (preserved) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:734 (CRUSH pikmin=20) :762 (DAMAGE drain 130 to 0); accepted lane26 evidence preserved, see #502 handoff | natural |
| 4. Death and corpse | PASS (preserved) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:802 (DEAD prior_health=10.00) :803 (BIRTH count=30) :805 (NATURAL_DEATH bigfoot=1); accepted lane26 evidence preserved, see #502 handoff | natural |
| 5. Actual transport and reward | N/A (source-backed) | native/pikmin2-research/src/plugProjectNishimuraU/Houdai.cpp:71 / BigFoot.cpp:69 disableEvent EB_LeaveCarcass; held treasure -> #491 follow-on | N/A |
| 6. Cleanup and re-entry | PASS (preserved) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:939 (FORGET BigFoot count=0 registered=0) :944 (REENTRY stale=0 fresh=1); accepted lane26 evidence preserved, see #502 handoff | natural |

## Checker output

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_BIGFOOT69_WALK_ACCEPTANCE.md
69 BigFoot (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    accepted [PASS]
EXIT=0
```