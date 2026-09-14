# Pikmin 2 Titan Dweevil (BigTreasure) FSM host binding (#246)

Lane 32 of [the P2 implementation fan-out](PIKMIN2_IMPLEMENTATION_FANOUT.md)
(dispatch #435, coordination #186). Child issue
[#246](https://github.com/4laric/pikmin-randomizer/issues/246), parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175).

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash), started 2026-09-13.

Prior slices: [source audit](PIKMIN2_BIGTREASURE_AUDIT.md),
[ownership/teardown contract](PIKMIN2_BIGTREASURE_CONTRACT.md),
[per-element attacks](PIKMIN2_BIGTREASURE_ATTACKS.md),
[host seam integration](PIKMIN2_BIGTREASURE_SEAM.md),
[conversion](PIKMIN2_BIGTREASURE_CONVERSION.md).

This slice closes the lane's `fsm_host` gap with a lane-owned binding between
the 12-state `P2BigTreasureFsm` policy and the host seam
(`P2BigTreasureHostSeam`), and proves **real weapon damage** plus a **natural
phase transition** (weapon knock-off) in a standalone fixture. It adds new
lane-owned native files only; existing modules and the shared CMake are
untouched.

## New native files

Branch `opencode/p2-lane32-fsmhost` (local; native origin never pushed),
base `086ed858c2693d9259679177e0eca00a80f57fbf`, head
`2826d61c7997585d52b55e6dea43e1a38b3790c2`:

- `pc_port/pc_p2_bigtreasure_fsmhost.h/.cpp` — `P2BigTreasureFsmHost`:
  per-tick binding of the FSM to the seam.
- `tools/p2_bigtreasure_fsmhost_test.cpp` — standalone engine-free fixture.

The patch bundle is published on the root branch at
`native-candidates/bigtreasure-fsmhost/` (`bigtreasure-fsmhost-full.patch`,
`patches/0001-…`, `provenance.json`).

## Binding contract

`P2BigTreasureFsmHost::tick(seam, in, out)` runs one 30 Hz source tick:

1. **Damage.** A positive `in.damage` is routed through
   `P2BigTreasureOwnership::damageCallBack` against the current FSM phase
   (Land quarters Pikmin damage; body parts only register at zero weapons).
2. **Knock-off.** `P2BigTreasureOwnership::update` releases every weapon at
   zero HP with the standard `(0,100,0)` pop. This is the observable phase
   transition.
3. **FSM step.** `P2BigTreasureFsm::update` is fed the post-damage loadout
   (`hasAnyWeapon`, per-weapon `weaponAttached[]`, the host `chosenWeapon`
   result, animation keyframe pulses and the host-supplied flick / attack-limit
   / motion booleans).
4. **Actions.** The policy's requests are performed in order:
   `pickWeapon` -> `ownership.pickWeapon(pickThreshold)` (first band in
   elec/fire/gas/water order); `resetAttackLimitTimer` -> pacer reset;
   `startAttack` -> `director.pools.start(chosenWeapon)` (counts
   `seam.attacksStarted`); `finishAttack` -> `pools.finishAttack()`;
   `releaseLoozy` -> `ownership.releaseLouie()`. `throwupItem` / `killed` are
   surfaced through `out.fsm` for the host to drive the finale/teardown.

The FSM remains engine-free and RNG-free; every random input is host-supplied,
so fixtures are deterministic. The binding is a no-op on an inactive seam.

## Fixture evidence (standalone, real modules)

MinGW64 GCC 16.2.0, `-std=gnu++17 -Wall -Wextra -Werror`, warning-clean.
Executable SHA-256 `fd821792183c9d75de114208038b844da6e5e9e9ecd51388a43fa02adc5af86d`.

```
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bigtreasure_fsmhost_test.cpp \
    pc_port/pc_p2_bigtreasure_fsmhost.cpp pc_port/pc_p2_bigtreasure_host.cpp \
    pc_port/pc_p2_bigtreasure_fsm.cpp pc_port/pc_p2_bigtreasure.cpp \
    pc_port/pc_p2_bigtreasure_attacks.cpp -o output/p2_bigtreasure_fsmhost_test.exe
```

`PASS BIGTREASURE_FSMHOST` (exit 0), eight groups:

| Group | Evidence |
| --- | --- |
| `progression` | Stay -> Land -> ItemWalk -> PreAttack -> Attack; elec picked at threshold 0; `startAttack` starts the elec pool |
| `land_quarter` | 100 damage in Land => 25 applied (weapon HP 6000 -> 5975) |
| `knockoff_phase` | 6000 damage to the chosen elec => one knock-off, `weaponCount 4 -> 3`, same-tick PreAttack re-entry and fire re-pick, `finishAttack` cleanup |
| `body_exposure` | armed body hit ignored; four weapon knock-offs drive `bodyExposed`; a body hit then routes `P2BTDMG_Body` |
| `pinch_smoke` | 6000 -> 2500 crosses the strict 3000 boundary; pinch smoke reported, `isNormalAttack` false |
| `kill_dead` | `killed` -> Dead; `keyEvent100` -> throwupItem + releaseLoozy; `animEnd` -> killRequested |
| `inactive` | inactive seam tick is a no-op |
| `defeat_rest` | after one knock-off, host defeat releases the remaining 3 weapons + Louie (already-dropped elec excluded) |

## Remaining gaps

- **Production wiring stays lane 01-owned.** The binding is not yet in the
  shared `pikmin_pc` target; the requested hook is one additive CMake line for
  `pc_port/pc_p2_bigtreasure_fsmhost.cpp`, then a `runFsmHost()` phase in
  `tools/p2_bigtreasure_runtime.cpp` for real-GL evidence.
- **Damage is fixture-sourced.** The receiver routing is exercised through the
  ownership API; a real Pikmin attack volume / generic receiver adapter is lane
  10 / #186 review, not this slice.
- **Motion staging (2/29 clips), the unconverted loozy model, skeletal playback
  and material fidelity** remain #128-gated and unchanged by this slice.
- **Finale treasure (`mPelletDropCode`) and pellet configs** remain disc-data
  unknowns; `throwupItem` is surfaced but not yet bound to a concrete drop.
