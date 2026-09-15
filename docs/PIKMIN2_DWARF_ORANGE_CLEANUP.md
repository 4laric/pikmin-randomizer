# Lane 13 - Dwarf Orange Bulborb (BlueKochappy 44) natural-death cleanup (gate E)

Fan-out lane 13 (`#120`/`#186`), consuming the shared lifetime seam (lane 07,
`#397`). This closes the `BLOCKED` gate E row for the Dwarf Orange Bulborb
candidate on the **natural** path: a real Pikmin fight kills the opted-in source
actor, its corpse is carried to a real goal, the engine's death funnel
(`Pellet::kill -> BTeki::viewKill -> Creature::kill -> BTeki::doKill`) runs
`pc_p2_forget_teki`, and the family registration maps are cleared.

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode.

## 1. Scope and difference from the earlier blocked re-entry probe

The earlier `pikmin2_dwarf_orange_reentry` probe (manager swap) was `BLOCKED`:
the overlay squad killed the source actor before the swap tick, and relocating
the squad tripped the day/movie flow (`#397`). This slice does **not** require a
manager swap. It uses the integrated shared lifetime seam instead: the family
hooks are now called from `BTeki::doKill` on the natural death funnel, so a
naturally delivered corpse is enough to observe cleanup.

- `experimental/pikmin2_dwarf_orange_cleanup.py` - the cleanup observer. It is
  the lane-13 Dwarf Orange delivery observer plus a bounded hold: after the
  carried corpse is removed it keeps running `HOLD_TICKS = 90` engine ticks so
  the death funnel can complete and flush before the process exits. The delivery
  observer previously `std::_Exit(0)`d on the removal tick, before the funnel
  ran, which is why no cleanup marker appeared.
- Native `pc_p2_dwarf_orange_forget` and `pc_p2_kochappy_fsm_forget` now emit
  `P2_DWARF_ORANGE_FORGET` / `P2_KOCHAPPY_FSM_FORGET` when a registered actor is
  actually erased. The marker deliberately does not read `mGenerator`, because
  `BTeki::dieSoon()` detaches the generator before `doKill` runs.

No enemy state, health, target, animation or forget is written by the observer.
The only interventions are the lane-13 combat/delivery stimuli (captain
reposition, free-squad deployment, and at most a transport-task assignment if
the free squad stalls), which are already recorded in the delivery slice.

## 2. Native candidate and build provenance

> Wave-line re-run (DeepSeek lane 13, slice 2): the cleanup witness above was
> cherry-picked unchanged and re-run on the current wave pair (root
> `deepseek/p2-l13`, native `deepseek/p2-l13-native` @ `261ee541`). Result
> `passed=true`, exit 0, all eight checks true — `P2_DWARF_ORANGE_FORGET` and
> `P2_KOCHAPPY_FSM_FORGET` on the `doKill` funnel after a 544.6-unit natural
> corpse carry. Exact run/log/executable pins for that re-run are recorded in
> `docs/PIKMIN2_LANE13_DEEPSEEK_HANDOFF.md` (slice 2); the historical Codex
> provenance described here predates that re-run.

The native forget-signal slice is family-local only: `pc_p2_dwarf_orange_forget`
and `pc_p2_kochappy_fsm_forget` erase their registration maps and print
`P2_DWARF_ORANGE_FORGET` / `P2_KOCHAPPY_FSM_FORGET` when a registered actor is
actually erased (generator is already detached by `dieSoon()`). The full-state
FSM was previously un-ported on the maintained line, which carried only the
five-state opt-in slice; the three cherry-picks apply cleanly because the Dwarf
Orange module is byte-identical between the base `b805d9c6` and the worker
candidate.

Build provenance (historical): Ninja / MinGW `g++ 16.2.0`, `Release`,
`PIKMIN_NATIVE_JAUDIO=ON`, `-j 6`; `ninja -n` → `ninja: no work to do.`; cleanup
fixture built by `scripts/build_pikmin2_fixture.py` (`status=built`).
Exact commit/SHA pins are in the lane-13 handoff, not repeated here.

## 3. Runtime evidence (960x540 centred window)

Arena: one source Dwarf Orange actor (`211001`), one P1 Chappy control
(`211002`), 20 free reds, `p2-dwarf-orange-fsm.txt` opt-in and the converted
`dwarf_orange` pose bank. Witness marker set (this is the exact evidence the
gate-E PASS is built on):



Witness lines:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001
  x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0
  behavior=native source_FSM=implemented move_speed=60 sight=95 attack_range=30 attack_angle=20
P2_KOCHAPPY_STATE generator=211001 state=wait
P2_KOCHAPPY_STATE generator=211001 state=turn
P2_KOCHAPPY_STATE generator=211001 state=walk
P2_KOCHAPPY_STATE generator=211001 state=attack
P2_KOCHAPPY_STATE generator=211001 state=dead
P2_KOCHAPPY_DEAD generator=211001 source_id=44 health=0.0
P2_KOCHAPPY_CORPSE generator=211001 source_id=44 native=host_escape_now
P2_DWARF_ORANGE_P1_HAUL tick=600 state=1 alive=1 distance=544.7413 transport=0 goal=1
P2_DWARF_ORANGE_FORGET registered=1
P2_KOCHAPPY_FSM_FORGET registered=1
P2_DWARF_ORANGE_P1_REMOVED distance=544.4386
PASS P2_DWARF_ORANGE_P1_CLEANUP distance=544.4386 reached=1
```

Combat is natural (real accumulated Pikmin damage reaches `mHealth`; the FSM
applies its own queued-damage reaction because it suppresses `doAI`). Death is
natural. The corpse is picked up and carried by the free squad
(`transport_task_injected=false`, `goal=1`). Cleanup is the engine death funnel's
`pc_p2_forget_teki`, not a fixture-injected `kill()` or forget call.

## 4. Gate table (this slice)

| Gate | Status | Evidence |
|---|---|---|
| A Identity/content | PASS | `P2_ENEMY_READY source_id=44`, 64-pose Dwarf Orange bank |
| B Source behavior | PASS (opt-in) | wait/turn/walk/attack/dead witnessed on the full source FSM |
| C Combat/receivers | PASS at P1-proxy level | real Pikmin damage drives health 250 -> 0; frame-8 `InteractAttack` |
| D Death/drop/transport | PASS at P1-proxy level | FSM Dead -> `pcEscapeNow()` carcass; real carry to a goal; corpse removed |
| **E Lifetime (cleanup)** | **PASS** | `P2_DWARF_ORANGE_FORGET registered=1` and `P2_KOCHAPPY_FSM_FORGET registered=1` on the natural `doKill` funnel |
| F Persistence | PASS (unchanged) | `PIKMIN2_DWARF_ORANGE_RESTART.md` |
| G Product/mixed scene | BLOCKED (unchanged) | candidate not integrated; not a generated/randomized session |

## 5. Limits and non-claims

- **Scene re-entry** (a fresh actor after the corpse/scene is released) is still
  open: it needs the `#397` squad-free non-extinct baseline. The shared
  stage-teardown reset (`pc_p2_reset_all_teki`) already clears every family map
  at `exitStage`, so there is no cross-stage stale reference; this slice does not
  claim a spawned-actor re-entry.
- The cleanup proof is on a **P1 Chappy vehicle** with custom in-engine ID
  `211001`; `behavior=native` is the opt-in source FSM, not full P2 fidelity.
  Attack eat/swallow/poison, Press, the notice cry and SFX remain unmodelled
  (`PIKMIN2_KOCHAPPY_FSM.md` §7). This is the documented experimental scope.
- P2 reward/once-credit is lane 06 and is **not** exercised; the corpse transport
  is the ordinary P1 goal path (`p2_receipts=not_applicable`).
- The `pc_p2_forget_teki` funnel also runs on manager-slot reuse; this slice
  proves the death-funnel invocation, not the reuse probe (lane 07 `#397`).

## 6. Tests

- `tests/test_pikmin2_dwarf_orange_cleanup.py` - observer transform (Dwarf
  Orange identity, no Red identity/generator), all-pass witness, and rejection
  when either family forget marker, the corpse removal, the FSM death, the
  completion line or a zero exit code is absent.
