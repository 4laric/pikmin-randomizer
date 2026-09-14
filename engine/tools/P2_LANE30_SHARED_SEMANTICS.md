# Lane 30 shared-semantics review packet (#186 / lane-12 #130)

Review request, not a design document. No engine or GL build was run for it.

- Base / lane-30 head reviewed: `3e54b927c25524a416ea171ded6f78bcad9e5f6e`
  (`opencode/p2-lane30-rebase`, worktree `output/native-lane30-rebase`).
- Packet + tests branch: `opencode/p2-lane30-verify` (worktree `output/native-lane30-verify`).
- Child issue: #242. Parent/coordination: #186. Captain/squad provider: lane 12 (#130).

## 1. The admission allowlist under review

`pc_port/pc_p2_demon_admission.h` (new in `31eaf3f8`, `#242`) exposes:

- `pc_demon_captain_admission_eligible(Navi*)` — deny-by-default allowlist.
  Default accepts exactly `NAVISTATE_Walk` (0) and `NAVISTATE_Idle` (17). Every
  other state, `nullptr`, and a Navi with no state machine is rejected.
- `pc_demon_admission_walk_only()` — A/B toggle. `PIKMIN_DEMON_WALK_ONLY_ADMISSION=1`
  restores the historical Walk-only gate. The value is read once with `std::getenv`
  into a function-local `static`; it is fixed for the process lifetime.

Call sites (each replaces a literal `getID() != NAVISTATE_Walk`; the existing
`isAlive`, `isStickTo`, `mRope`, exact-owner/part and `isBouncySphereType`
guards are unchanged):

| Call site | Function | Result |
|---|---|---|
| `pc_port/pc_p2_demon_bridge.cpp:39` | `pc_demon_capture` | admits Walk+Idle |
| `pc_port/pc_p2_demon_bridge.cpp:64` | `pc_demon_bound` | keeps ownership through Idle |
| `pc_port/pc_p2_demon_drop_state.cpp:102` | `pc_demon_drop_begin` | admits Walk+Idle |
| `pc_port/pc_p2_demon_escape_state.cpp:35` | `pc_demon_escape_begin` | admits Walk+Idle |

Invariant preserved: a captor may not pre-empt a state that owns control,
animation, damage, impulse, UI or life semantics. `Idle` is the only addition;
it keeps the captain in neutral locomotion, so acceptance no longer requires the
fixture to hold the captain in `Walk` artificially.

Engine-free evidence: `tools/p2_demon_admission_test.cpp` exercises the predicate
over all declared IDs `NAVISTATE_Walk`(0)…`NAVISTATE_IroIro`(35), `DemonDrop`(36),
`DemonEscape`(37) plus `NAVISTATE_NULL` and out-of-range values (46 checks). PASS
in both modes. Observation for review: the predicate checks `!n->mStateMachine`
but not `!n->getCurrState()`; it relies on the engine invariant that a Navi with
a state machine always has a current state.

## 2. Lane-30 edits that touch a shared file

Origin column: lane-30 commit that introduced the edit in this tree. `ae4747d4`
(#387) is the baseline integration of lane 30's drop-state prototype; the net-new
review focus is `31eaf3f8` plus the escape/bridge/host hooks.

| Shared file:line | Lane-30 edit | Origin | Invariant preserved | Decision requested (#186 / #130) |
|---|---|---|---|---|
| `include/NaviState.h:56-60` | under `PIKI_PC_PORT`, append `NAVISTATE_DemonDrop=36`, `NAVISTATE_DemonEscape=37`; `Count` becomes 38 | `ae4747d4` | retail IDs 0-35 and non-PC `Count`(36) unchanged | Accept the PC-only state-ID allocation; #186 ID-conflict review, lane-12 state ownership |
| `src/plugPikiKando/naviState.cpp:2-4` | includes `pc_p2_demon_drop_state.h`, `pc_p2_demon_escape_state.h`, `pc_p2_demon_bridge.h` | `ae4747d4`, `9e75a95b` | no include changes semantics | Acknowledge |
| `src/plugPikiKando/naviState.cpp:87-88` | `pc_demon_before_transition`, `pc_demon_drop_before_transition` before `StateMachine<Navi>::transit` | `ae4747d4`, `9e75a95b` | retail transit order/normal states unchanged; veto scoped to demon states | Lane 12: confirm transit veto is the right boundary for denying unadmitted drop transitions (#242) |
| `src/plugPikiKando/naviState.cpp:97-98` | `registerState(pc_demon_drop_state_create())`, `registerState(pc_demon_escape_state_create())` in `NaviStateMachine::init` | `ae4747d4`, `9e75a95b` | retail registrations and order unchanged | Lane 12: confirm captain state registration ownership by lane 30 |
| `src/plugPikiKando/navi.cpp:3-4` | includes `pc_p2_demon_drop_state.h`, `pc_p2_demon_bridge.h` | `ae4747d4`, `9e75a95b` | no include changes semantics | Acknowledge |
| `src/plugPikiKando/navi.cpp:594-595` | `pc_demon_reset(this)`, `pc_demon_drop_reset(this)` in `Navi::reset` | `ae4747d4` | clears only lane-30 bindings; retail reset untouched | Lanes 12/07: confirm reset ownership |
| `src/plugPikiKando/navi.cpp:1074-1075` | `pc_demon_drop_post_physics(this)`, `pc_demon_follow_mouth(this)` after `Creature::update` | `ae4747d4`, `ea7b86c6` | post-physics ordering preserved; acts only while bound | Lane 12: confirm the carried-captain motion hook does not fight the captain controller (#130) |
| `src/plugPikiKando/navi.cpp:1477-1485` | `pc_demon_bound` early-return in `Navi::doAI`, suppressing normal AI while carried | `9e75a95b` | normal AI unaffected when not bound | Lane 12: confirm interruption semantics for a held captain (#130) |
| `src/plugPikiKando/navi.cpp:1718` | `pc_demon_suppress_atari` in `Navi::isAtari` | `9e75a95b` | suppression scoped to the bound captain | Lane 12: confirm targetability contract |
| `src/plugPikiKando/navi.cpp:2416` | `pc_demon_capture_matrix` branch in the draw transform | `ea7b86c6` | falls through to the normal draw path when not capturing | Acknowledge family visual transform |
| `src/plugPikiKando/gameCoreSection.cpp:5-6,20` | includes `pc_p2_demon_drop_state.h`, `pc_p2_demon_bridge.h`, `pc_p2_demon_host.h` | `ae4747d4`, `9e75a95b`, `56204bb6` | no include changes semantics | Acknowledge |
| `src/plugPikiKando/gameCoreSection.cpp:863-864` | `pc_demon_drop_scene_exit()`, `pc_demon_scene_exit()` in `GameCoreSection::exitStage` | `ae4747d4` | scene exit clears demon bindings, no stale receiver/owner | Lanes 07/12: confirm lifetime/teardown ownership |
| `src/plugPikiKando/gameCoreSection.cpp:1389` | `pc_p2_demon_manager_setup()` in `finalSetup` (after kurage/onikurage) | `d45bb808` | setup runs after stage finalization; baseline setups retained | Confirm setup ordering |
| `src/plugPikiNakata/tekimgr.cpp:23,135,162,295,311` | include; `pc_p2_demon_manager_reset()` in `initTekiMgr`/`TekiMgr()`/`reset`; `pc_p2_demon_manager_forget((BTeki*)teki)` in `newTeki` | `a7564f53` | baseline per-lane reset/forget lists retained; only demon binding cleared | Lane 07/lane 12: confirm reset and forget-on-recycle ownership for actor identity |
| `src/plugPikiNakata/tekibteki.cpp:24,157,460,2049` | include; `pc_p2_demon_manager_draw_actor` prepended to both draw chains; `pc_p2_demon_manager_update_actor(this)` in `BTeki::update` | `66337853` | baseline draw/update chains retained and fall through | Confirm shared actor draw/update dispatch for the captor |
| `CMakeLists.txt:168-171` | add `pc_p2_demon_drop_state.cpp`, `pc_p2_demon_escape_state.cpp`, `pc_p2_demon_bridge.cpp`, `pc_p2_demon_host.cpp` to `PC_PORT_SOURCES` | `ae4747d4`, `9e75a95b`, `789f3f30` | no new target/define; additive source list only | Acknowledge: no shared build-semantics change |

## 3. Explicit questions for #186 / lane-12 (#130)

1. **Admission default.** Should the source-backed default admission set (Walk +
   Idle) remain, with Walk-only available only via `PIKMIN_DEMON_WALK_ONLY_ADMISSION=1`?
   Or should lane 30 revert to Walk-only as the default until lane 12 signs off?
2. **Toggle lifetime.** Should the `PIKMIN_DEMON_WALK_ONLY_ADMISSION` A/B toggle
   ship in the production binary, or be removed once #186 accepts the Walk+Idle
   set? It is a process-lifetime `getenv` read, not a settings-menu option.
3. **Source correctness.** Does retail P2 actually grab a captain from `Idle`
   (`NaviStateWait`) and keep the mouth/stick relation across Walk↔Idle, which is
   the entire justification for adding `Idle`? Lane 12 owns the captain/squad
   contract (#130).
4. **State IDs.** Is appending PC-only `DemonDrop`=36 / `DemonEscape`=37 and
   changing PC `Count` to 38 the agreed allocation, with retail 0-35 and non-PC
   `Count`=36 preserved?
5. **Transit and registration.** Does #186 accept `NaviStateMachine::transit`
   veto hooks and two lane-30 `registerState` entries inside the shared captain
   state machine?
6. **Captain control.** Are the `doAI` early-return (no normal AI while carried),
   `isAtari` suppression, reset, post-physics and draw-transform hooks the agreed
   captain-interruption boundary, and do they conflict with two-captain/held-Pikmin
   semantics in #130?
7. **Actor lifetime.** Do the TekiMgr reset/forget and BTeki draw/update hooks
   belong to lane 30, or should lane 07 own the recycled-address/stale-binding
   guarantees?
