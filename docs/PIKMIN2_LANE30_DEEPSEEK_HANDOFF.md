# Lane 30 — Sarai (Swooping Snitchbug, ID 23) ordinary-spawn admission handoff

Lane 30 / #242 / parent #166. Executing session: opencode (`opencode/p2-l30-drive`,
`opencode/p2-l30-drive-native`), branched off the integration line
`claude/p2-deepseek-wave` / `claude/p2-deepseek-wave-native`.

This slice takes the previously fixture-only Sarai captor work to an **ordinary
spawned, natural, killable and carriable** Sarai so identity 23 satisfies the
lane-02 admission contract: natural PASS on all five `ADMISSION_GATES` plus a
Pod `corpse:` delivery receipt.

## Concrete source ID and files owned

- Source ID: 23 `Sarai` (Swooping Snitchbug), family Snitchbugs/Demon.
- Native (`output/dsw/native-l30-drive`, branch `opencode/p2-l30-drive-native`):
  `pc_port/pc_p2_sarai_manager.{h,cpp}` (new; ordinary-spawn binding, health
  feed, death/forget reporting, Pod receipt), `pc_port/pc_p2_sarai_host.{h,cpp}`
  (anchor bind + real health + death), plus additive hooks in
  `pc_port/pc_p2_preview.cpp`, `pc_port/pc_p2_teki_lifetime.cpp`,
  `src/plugPikiNakata/tekibteki.cpp`, `src/plugPikiKando/gameCoreSection.cpp`,
  `CMakeLists.txt`. The lane also merges `opencode/p2-lane30-rebase` (captor
  lifecycle + dedicated captor identity).
- Root (`output/dsw/l30-drive-root`, branch `opencode/p2-l30-drive`): this handoff.
- Runtime fixtures (private): base `tools/preview_p2_room.cpp` instrumented for
  corpse-approach/transport (Pod receipt) and for the manager re-entry cycle;
  staged 20-red / 960x540 arenas under `output/l30-drive-*-arena`.

No production input, shared-enemy-stat or GenTest semantics were changed; the
Sarai manager is default-off (`PIKMIN_SARAI_ORDINARY=1`).

## Six-gate table (Sarai / source ID 23)

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS | output/l30-drive-arena/b4c465c48592419caed342a1aa6347e7/native.log:787 | natural |
| 2. Autonomous movement and animation | PASS | output/l30-drive-arena/b4c465c48592419caed342a1aa6347e7/native.log:827 | natural |
| 3. Attacks and receivers | PASS | output/l30-drive-arena/b4c465c48592419caed342a1aa6347e7/native.log:854 | natural |
| 4. Death and corpse | PASS | output/l30-drive-pod-arena/15f359d18d8b4adc8cc9ac6fd7470bcf/native.log:840 | natural |
| 5. Actual transport and reward | PASS | corpse:sarai:385875968 output/l30-drive-pod-arena/15f359d18d8b4adc8cc9ac6fd7470bcf/native.log:879 | natural |
| 6. Cleanup and re-entry | PASS | output/l30-drive-reentry-arena/9f0bdb7023dd43798b6dbfe573157beb/native.log:868 | natural |

## Evidence detail

- **Gate 1** `P2_SARAI_READY source_id=23 species=Sarai generator=385875968 type=3 health=130.0 behavior=source`
  — the ordinary generated-slot actor, rebound and drawn as the source Sarai
  (`native.log:787`).
- **Gate 2** `P2_SARAI_TICK … phase=2 state=7` with advancing positions
  (`:827,832,843,846,851`) — the source FSM Wait→Move→Attack on the live actor.
- **Gate 3** `P2_SARAI_CAPTURE source_id=23 generator=385875968 slot=0 owner_exact=1`
  (`:854`), then `phase=3 state=9` CatchFly carry (`:860,863,868`) and
  `phase=4 state=10` FallMeck drop — the capture/drop receiver on the real mouth
  `CollPart`.
- **Gate 4** `P2_SARAI_DEAD source_id=23 generator=385875968 health=0.0`
  (`pod native.log:840`), `P2_LIFECYCLE_DEATH … health=0.00` (`:841`) and
  `P2_LIFECYCLE_BIRTH … pellet=…` (`:848`) — natural Pikmin damage kills the
  actor and the engine births the corpse pellet.
- **Gate 5** free Pikmin self-assign transport, the corpse traverses the room
  (`P2_CORPSE_PROGRESS distance≈381`) and is delivered:
  `P2_POD_RECEIPT id=corpse:sarai:385875968 value=2 new=1 pokos=2`
  (`pod native.log:879`), `P2_LIFECYCLE_REMOVED … distance=397.94` (`:880`),
  fixture `PASS p2 room … native combat kill, far corpse transport and delivery`
  (`:1966`, exit 0).
- **Gate 6** `P2_SARAI_FORGET generator=385875968 phase=cleanup`
  (`reentry native.log:799`) after `TekiMgr::killAll`, then
  `P2_SARAI_REENTRY … old_registry=clear new_bound=1` (`:868`) and a second
  `P2_SARAI_READY …` (`:866`) proving the re-created actor re-binds
  (`PASS P2_SARAI_REENTRY observation`, `:869`).

## Reproduction

```
# gate 1-3: ordinary arena (self-contained stage + private nectar build)
py -3.12 output/deepseek-wave/build_lane.py l30-drive --target pikmin_pc
py -3.12 output/deepseek-wave/slot.py run gl l30-drive -- py -3.12 output/l30-drive-stage.py
# gates 4-5: combat/corpse -> Pod receipt fixture (base preview_p2_room, instrumented)
py -3.12 output/deepseek-wave/slot.py run gl l30-drive -- py -3.12 output/l30-drive-pod.py
# gate 6: manager replacement + re-bind
py -3.12 output/deepseek-wave/slot.py run gl l30-drive -- py -3.12 output/l30-drive-reentry.py
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE30_DEEPSEEK_HANDOFF.md
```

All three runs log `Experimental preview window set to 960x540 windowed and
centered`; every arena is a fresh 20-red `preview_pikmin2_room` overlay and no
run reports `Extinction`.

## Assumptions / limits

- The ordinary Sarai's damage/lifetime anchor is the lane's generated `TEKI_Chappy`
  slot (the same vehicle pattern the accepted Dwarf Orange/Sokkuri sidecars use);
  the Sarai source FSM owns the behaviour and visual. No enemy health, state,
  target or animation is written by any fixture.
- Gates 1-3 come from the free-running ordinary run; gates 4-5 from a private
  squad-deployment fixture (`PIKMIN_SARAI_STATIC=1`, captain parked, free reds);
  gate 6 from a manager-swap fixture. Each is natural; the fixtures only place
  the captain/squad and never inject enemy state.
- Not claimed: generated-seed placement (lane 03/04), campaign save/re-entry,
  whole-scene heap teardown, mixed-scene frame budget.
