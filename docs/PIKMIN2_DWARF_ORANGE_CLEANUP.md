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

Native worktree `output/native-lane13-orange-fsm2`, branch
`opencode/p2-lane13-orange-fsm2`, based on the approved maintained baseline
`b805d9c6` (the version that already contains `pc_p2_dwarf_orange`,
`pc_p2_kochappy_fsm` and `pc_p2_teki_lifetime`). Ordered commits:

- `8781664f` full KochappyBase Turn/TurnToHome/GoHome/Press states and Dead path
  (cherry-pick of the worker `940914d5`)
- `95996820` apply queued Pikmin damage inside the FSM (`d3ffb3c4`)
- `e6ceceac` finalize the FSM Dead carcass outside `doAI` (`d9ea68c9`)
- `d847df2d` signal the Dwarf Orange family cleanup on the natural death funnel

The full-state FSM was previously un-ported on the maintained line, which
carried only the five-state opt-in slice. The three cherry-picks apply cleanly
because the Dwarf Orange module is byte-identical between `b805d9c6` and the
worker native candidate `2e3941c8`.

Private build `output/native-lane13-orange-fsm2-build`, Ninja / MinGW
`g++ 16.2.0`, `Release`, `PIKMIN_NATIVE_JAUDIO=ON`, `-j 6`.
`[N/N] Linking CXX executable bin\nectar.exe`, exit 0; `bin/nectar.exe`
SHA-256 `1BEA8E95BB1AAC301A8E5991C5048C717656B1EAC0BF501D20FC8FB63C25EC85`.

Cleanup fixture `output/p2-lane13-orange-fsm2-cleanup-fixture/baseline/fixture.exe`,
built by `scripts/build_pikmin2_fixture.py` from the same private build
(`status=built`, `ninja: no work to do` freshness checks), SHA-256
`E88725A049ECB649ADFAC9399BF4B939EAA0B813867D8D52137B39C5437E724A`.

## 3. Runtime evidence (960x540 centred window)

Arena: a private copy of the FSM-on Dwarf Orange arena
(`output/p2-lane13-orange-fsm-run-on/bd2b9fff954a474b88a7f6e467314cfc`, which
already carries `p2-dwarf-orange-fsm.txt` and the converted `dwarf_orange` bank),
staged into `output/p2-lane13-orange-fsm2-cleanup-arena5`. One source actor
(`211001`), one P1 Chappy control (`211002`), 20 free reds.

Report `output/p2-lane13-orange-fsm2-cleanup-final/evidence.json`: `passed=true`,
`exit_code=0`, all eight checks true. Log
`output/p2-lane13-orange-fsm2-cleanup-final/native.log` sha256
`80EC2F09FF3A2B204DAAFF055CDFFF742B20B23A3608726B22FC68377E6D805E`.

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
