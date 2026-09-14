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
phase transition** (weapon knock-off) first in a standalone fixture and then in
a **real-GL fixture run**. It also adopts the mandatory
[fan-out fixture baseline](PIKMIN2_IMPLEMENTATION_FANOUT.md): the 960x540
centered experimental-room window (native `1d5a242b`) and the 20-red starting
squad overlay (`scripts/preview_pikmin2_room.py`).

## New native files

Branch `opencode/p2-lane32-fsmhost` (local; native origin never pushed),
base `086ed858c2693d9259679177e0eca00a80f57fbf`, head
`c4c4095420a355f3da51e6ce78c348b0fbdee153`. Ordered commits:

1. `2826d61c` — `pc_port/pc_p2_bigtreasure_fsmhost.h/.cpp`,
   `tools/p2_bigtreasure_fsmhost_test.cpp` (FSM host binding + standalone
   fixture).
2. `6391a5a7` — `CMakeLists.txt` adds `pc_p2_bigtreasure_fsmhost.cpp` to the
   `pikmin_pc` target; `tools/p2_bigtreasure_runtime.cpp` gains the
   `runFsmHost()` real-GL phase; `tools/p2_bigtreasure_runtime_run.py`
   validates the new markers.
3. `a82e0f44` — cherry-pick of native `1d5a242b`
   (`pc_port: open experimental-room windows small and centered by default`):
   the mandatory 960x540 centered experimental-room window and
   `pc_window_center()`. Not an ancestor of the `086ed858` base; adopted by
   source evidencing per the fan-out guide.
4. `c4c40954` — the fixture entrypoint adopts the same 960x540 centered window
   after `pc_settings_init()`.
5. `0a4aedb3` — the real-GL fixture drives the full four-weapon knock-off
   progression (four transitions, body exposure, `DropItem`, body damage
   routing).

The patch bundle is published on the root branch at
`native-candidates/bigtreasure-fsmhost/` (`bigtreasure-fsmhost-full.patch`,
`patches/0001..0005`, `provenance.json`).

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

## Real-GL runtime evidence

Private build `output/native-lane32-build` (Ninja, Release, JAudio ON, optimize
OFF, hooks OFF), `ninja -n pikmin_pc` = `no work to do`; production
`nectar.exe` SHA-256 `ca8af151c633ae6138c8d13ed595c56b2d679adcf858c3e73468cced9a45cf`.
Private fixture `output/lane32-fsmhost-fixture-03` (`provenance.json`
status `built`), fixture SHA-256
`2b80ff7376b7a641758a8e02b72d09e507f93ee3d1468004e75992134b135489`. Fresh
overlay run `output/lane32-fsmhost-runtime4/8e0eaa7e98c248b294f9975bbcb14cb4`,
`verification.json` status `passed`, exit 0:

| Marker | Result |
| --- | --- |
| `P2_BIGTREASURE_WINDOW size=960x540 pos=373,263` | baseline window adopted |
| `P2_BIGTREASURE_FLOOR_PROBE ground=-0.000000 center=20.000000 floor=1` | floor conversion |
| `P2_BIGTREASURE_WALL_PROBE wall=1 groundY=-0.000000` | wall contact |
| `P2_BIGTREASURE_ELEC_PROBE_PASS bounces=10 traces=3000 floors=2720` | elec bounce |
| `P2_BIGTREASURE_WATER_PROBE_PASS ticks=59 hits=1 ground=-0.000000` | water arc |
| `P2_BIGTREASURE_HOST_SEAM_PASS ticks=361 attacks=1 events=5` | seam lifetime |
| `P2_BIGTREASURE_FSMHOST_FULL_PASS knockoffs=4 weapons=0 phase=DropItem transitions=4` | **full four-weapon phase progression** |
| `PASS BIGTREASURE_RUNTIME` | suite pass |

Two PPM captures were produced (wait1, dead). The squad overlay ran with
20 reds (`[Pikipelago] P2_ROOM_PREVIEW ... red=20`) and entered active gameplay.
Each of the four weapons is damaged to zero on the real map, released, and the
policy re-picks (or drops to `DropItem` on the last one); the body then accepts
damage. The earlier single-transition run
(`output/lane32-fsmhost-runtime3/3fa5cb8f…`, fixture-02) is superseded but kept
for the record.

## Integration-ready series on the lane-01 native line

The slice was rebased onto the lane-01 reconciled native head (Batch D, #437)
and re-verified, so it is ready to integrate without re-resolving shared files:

- Native branch `opencode/p2-lane32-integ` @ `d288dd7b7771b4fe6c45bdc35ace37bb3ff986de`,
  based on `opencode/p2-lane01-hardlanes` @ `90d87f53` (clean). Commits
  `1acc4481` → `149ce1b5` → `aa1eefc4` → `d288dd7b`. The only shared-file edit is
  the additive `CMakeLists.txt` TU line; it was resolved additively here. The
  mandatory window baseline was already present in the lane-01 line as
  `9f179c88`, so the equivalent cherry-pick resolved empty and was skipped.
- Bundle: `native-candidates/bigtreasure-fsmhost-integ/`
  (`bigtreasure-fsmhost-integ-full.patch`, `patches/0001..0004`,
  `provenance.json`).
- Private build `output/native-lane32-integ-build` (534/534), `ninja -n` = no
  work, exe SHA-256
  `ab078d117e6226b31e09ec044a49eda2c8c39f505f761cb91738cfff9a1b5ffe`.
- Fixture `output/lane32-integ-fixture-01` SHA-256
  `367e50593fc08d8a4f34eeb00912a89bb658bf7dd5d9c6596e548ac906fbe449`; run
  `output/lane32-integ-runtime-01/2d0df22bd44b43f4bb5f67bf9630feb0` status
  `passed` with `P2_BIGTREASURE_FSMHOST_FULL_PASS knockoffs=4 weapons=0
  phase=DropItem transitions=4`, `P2_BIGTREASURE_WINDOW size=960x540`, and
  `PASS BIGTREASURE_RUNTIME`.

## Remaining gaps

- **Receiver routing from a real Pikmin attack volume is lane 10.** The damage
  in this fixture is supplied through the ownership/receiver API; the generic
  receiver adapter still needs wiring.
- **Motion staging (2/29 clips), the unconverted loozy model, skeletal playback
  and material fidelity** remain #128-gated and unchanged by this slice.
- **Finale treasure (`mPelletDropCode`) and pellet configs** remain disc-data
  unknowns; `throwupItem` is surfaced but not yet bound to a concrete drop.
- **Integration #450:** CMake registration, the existing window baseline and the updated replacement-main fixture are integrated. The normal hardlane update still does not call the FSM host; natural attack and reward adapters remain open.
