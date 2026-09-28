# Lane 13 gate B — Dwarf Orange Bulborb (BlueKochappy 44) native KochappyBase FSM

This slice upgrades lane-13 gate B (source behavior) for the Dwarf Orange
Bulborb from the host P1-AI proxy to a native source FSM. It is **opt-in and
defaults OFF**: the module is inert unless the private arena carries
`p2-dwarf-orange-fsm.txt`, so the existing host-AI combat, delivery and restart
evidence is unchanged.

Source of truth: read-only decomp `native/pikmin2-research`
(`include/Game/Entities/KochappyBase.h`, `src/plugProjectYamashitaU/kochappyState.cpp`,
`KochappyBase.cpp`) and the audited retail block in
`docs/PIKMIN2_DWARF_VARIANTS.md` §2/§3.

## 1. Opt-in and module

- `pc_port/pc_p2_kochappy_fsm.{h,cpp}` + `pc_port/pc_p2_kochappy_fsm_policy.h`.
- Enabled only when `p2-dwarf-orange-fsm.txt` exists in the process working
  directory. The first token must be `P2_DWARF_ORANGE_FSM_1`; optional
  whitespace-separated `key value` overrides are accepted for the ten audited
  parameters. Unknown keys, duplicates, non-finite/out-of-range values and
  trailing junk are rejected (`std::abort`) before any actor is touched.
- With no config file the setup returns immediately: no markers, no AI
  suppression, no motion writes, no damage application.
- Ownership comes from `pc_p2_dwarf_orange_registered`; the module never
  re-resolves identity or reloads the converted bank. Visuals reuse
  `pc_p2_dwarf_orange_draw` (the FSM drives the host motion index per state).

## 2. Source state / parm / timing mapping

Covered states (`P2_KOCHAPPY_STATE state=...`), in source StateID order:

| State | Host motion | Source drive | Notes |
| --- | --- | --- | --- |
| Wait | `Wait1` | nearest Pike/Navi within sight fp12=95; notice delay | Turn/TurnToHome choose next |
| Turn | `WaitAct1` | turn to target; attack gate fp20=30 / fp21=20°; out-of-range -> TurnToHome | waitact1 25f/0.833 s |
| Walk | `Move1` | move fp06=60 to target; territory fp09=500 | move1 loops |
| Attack | `Attack` | frame 8 `InteractAttack` (fp22=35, fp24=10) | attack clip 90f/3.0 s |
| Flick | `Flick` | frame 31 `InteractFlick` (fp19=17, fp17=50) | flick clip 80f/2.667 s |
| TurnToHome | `WaitAct1` | turn to home; within fp10=80 -> Wait | waitact1 25f |
| GoHome | `Move1` | walk home; within fp10=80 -> Wait | move1 loops |
| Press | `Type1` | source Press: health 0, type1 anim, then Dead | API only; UNTESTED |
| Dead | `Dead` | health ≤ 0; dead anim 90f/3.0 s then finalize | `pcEscapeNow()` (die + dieSoon) |

Demo(9) is the source `kill(nullptr)` terminal; the host folds it into Dead.
Health fp00=250 is reused from `pc_p2_dwarf_orange` and re-asserted here. The
nearest target is stored on host creature-pointer slot 0, mirroring source
`enemy->mTargetCreature = target`.

Two host adaptations are required because the module suppresses `doAI`:

- **Damage application**: the P1 host applies accumulated Pikmin damage in a TAI
  damage reaction inside `doAI`, so the FSM calls `actor->makeDamaged()` each
  update. Real accumulated `mStoredDamage` reaches `mHealth`; no damage is
  injected.
- **Death finalization**: `die()` only arms `mDeadState`, and `dieSoon()`
  normally runs inside `doAI`. Dead uses the `teki.h` family-lane helper
  `pcEscapeNow()` (`die()` + `dieSoon()`) to birth the carcass outside `doAI`.

## 3. Additive wiring

- `CMakeLists.txt`: adds `pc_port/pc_p2_kochappy_fsm.cpp`.
- `pc_port/pc_p2_preview.cpp`: `pc_p2_kochappy_fsm_setup()` after
  `pc_p2_dwarf_orange_setup()`.
- `src/plugPikiNakata/tekibteki.cpp`: `pc_p2_kochappy_fsm_update(this)` in
  `BTeki::update`, and `pc_p2_kochappy_fsm_suppress_ai(this)` in `BTeki::doAI`.
- `src/plugPikiNakata/tekimgr.cpp`: reset/forget symmetric with the Dwarf
  Orange module.
- `pc_p2_kochappy_fsm_press(BTeki*)` transitions a callable actor to Press; no
  P1 Chappy press callback is wired to this P2 actor.

Every hook is a no-op for unregistered actors and for the default-OFF path.

## 4. Build provenance

- Native worktree `output/native-lane13-orange-fsm`. Slices: `099b022c`
  (five-state opt-in FSM), `940914d5` (Turn/TurnToHome/GoHome/Press + Dead),
  `d3ffb3c4` (queued Pikmin damage), `d9ea68c9` (Dead carcass finalize).
- Private build `output/native-lane13-orange-fsm-build`, Ninja / MinGW
  `g++ 16.2.0`, `Release`, `PIKMIN_NATIVE_JAUDIO=ON`, `-j 6`.
  `ninja -n` → `ninja: no work to do.`
- `bin/nectar.exe` SHA-256
  `1EAB39CA89FC030CDFAECA4E660CCAE396298F0311B50228D5DDFD44E388448A`.
- Witness fixture `output/p2-lane13-orange-fsm-witness-fixture/baseline/fixture.exe`
  SHA-256 `208D36BE34917D242BE63922B56996A08A3F06F2A2A3729FA5B1C591B15EBAEA`
  (`status=built`, expected native head `d9ea68c9`).

Tooling note: the combined lane-13 head pushes CMake's final link command over
its response-file threshold, so `scripts/build_pikmin2_fixture.py` expands
Ninja response files (generated with `ninja -d keeprsp`).

## 5. Runtime evidence (960x540 centred window)

Arena: copy of `output/p2-lane13-orange-arena2/bd2b9fff954a474b88a7f6e467314cfc`
plus `p2-dwarf-orange-fsm.txt` (ON) / without it (OFF). One source actor
(`211001`), 20 free red Pikmin. The witness observer
(`experimental/pikmin2_dwarf_orange_fsm_witness.py`) reuses the lane-13 combat
stimulus (captain reposition + free-squad deployment) and adds only
player-equivalent Pikmin AttackMode orders; it writes no enemy health, state,
target or animation.

Opt-in ON, Dead witnessed (`output/p2-lane13-orange-fsm-dead4/native.log`):

```text
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001
  x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0
  behavior=native source_FSM=implemented move_speed=60 sight=95 attack_range=30 attack_angle=20
P2_KOCHAPPY_STATE generator=211001 state=wait
P2_KOCHAPPY_STATE generator=211001 state=turn
P2_KOCHAPPY_STATE generator=211001 state=attack
P2_KOCHAPPY_ATTACK generator=211001 frame=8 damage=10
P2_KOCHAPPY_STATE generator=211001 state=dead
P2_KOCHAPPY_DEAD generator=211001 source_id=44 health=0.0
P2_KOCHAPPY_CORPSE generator=211001 source_id=44 native=host_escape_now
DONE P2_DWARF_ORANGE_COMBAT
```

First damage tick 25; health 250→0; carcass (`corpses=1`) born. Walk,
TurnToHome and GoHome were also exercised by the same state machine in the
pre-finalization witness run (`output/p2-lane13-orange-fsm-dead2/native.log`,
136 walk / 133 turn_to_home / 132 go_home markers) when the actor survived
longer; Flick `state=flick` / `frame=31` was observed in the earlier tuning run
(`output/p2-lane13-orange-fsm-on2/native.log`).

Opt-in OFF regression (`output/p2-lane13-orange-fsm-off2/native.log`): the
original marker is intact, no FSM marker appears (0 matches), and the observer
completes with the host AI corpse:

```text
P2_ENEMY_READY species=BlueKochappy source_id=44 ... behavior=P1 purple_stun=bluekochappy_5s
P2_DWARF_ORANGE_COMBAT tick=225 health=0.0000 state=0 target=0 ... corpses=1
DONE P2_DWARF_ORANGE_COMBAT
```

## 6. Admission gates

| Gate | Status | Evidence |
|---|---|---|
| A Identity/content | PASS (unchanged) | `P2_ENEMY_READY source_id=44`, Dwarf Orange bank |
| B Source behavior | PASS (opt-in candidate) | full source state set + `source_FSM=implemented`; wait/turn/attack/dead witnessed, flick/walk/turn_to_home/go_home witnessed |
| C Combat/receivers | PASS (natural) | real Pikmin damage drives health 250→0; frame-8 bite + `P2_KOCHAPPY_EAT eaten=1 slot=1` and frame-88 `P2_KOCHAPPY_SWALLOW swallowed=1` (few-Pikmin observation squad) |
| D Death/drop/transport | PASS at P1-proxy level | FSM Dead → `pcEscapeNow()` carcass, `corpses=1` |
| E Lifetime | PASS (cleanup) / re-entry open | natural death → real corpse carry/removal → engine `doKill` → `pc_p2_dwarf_orange_forget` + `pc_p2_kochappy_fsm_forget`; see [the cleanup witness](PIKMIN2_DWARF_ORANGE_CLEANUP.md). Scene re-entry still needs the #397 squad-free baseline; the #397 stage-teardown reset already clears the maps. |
| F Persistence | PASS (unchanged) | restart evidence untouched |
| G Product/mixed scene | BLOCKED (unchanged) | not integrated |

## 7. Partial states / events (recorded)

- Press is implemented as a state and a trigger API but **UNTESTED**: the P1
  Chappy vehicle exposes no press callback for this P2 actor, so no in-engine
  squash reaches `pc_p2_kochappy_fsm_press`.
- Attack applies one `InteractAttack` at frame 8 (the bite), then source
  `eatPikmin` sticks one free Pikmin to a free mouth slot (`eaten=1 slot=1`) and
  source `swallowPikmin` kills the mouth-stuck Pikmin at frame 88
  (`swallowed=1`); a White Pikmin applies the proper-fp02 poison
  (`eatWhitePikminCallBack` equivalent, `P2_KOCHAPPY_SWALLOW white=1`). The
  no-free-slot one-shot eat path (`InteractSwallow` with a null slot) is
  UNTESTED, and `flickStickPikmin` (frame 8) remains approximated by the
  standalone Flick contact-radius path.
- `EnemyFunc::isStartFlick` (a Pikmin stuck to the body) is approximated by a
  contact-radius test; attack posture takes precedence.
- `isTargetOutOfRange` is approximated by distance > sight fp12 = 95.
- The Wait notice cry (`PSSE_EN_KOCHAPPY_NOTICE`) and all SFX/effects are
  omitted.
- Turn rate 2.0 rad/s is a recorded adaptation (host drive API takes a rate).

## 8. Tests

- `tests/test_pikmin2_kochappy_fsm.py` compiles `pc_p2_kochappy_fsm_policy.h`
  and checks the default source parms, all nine source state names and IDs, the
  accepted magic/override grammar, and rejection of bad magic,
  unknown/duplicate keys, missing/non-finite/out-of-range values and trailing
  junk.
- `tests/test_pikmin2_fixture_build.py` covers the response-file expansion.
