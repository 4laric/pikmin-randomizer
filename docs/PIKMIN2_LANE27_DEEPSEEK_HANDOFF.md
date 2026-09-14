# Lane 27 (Dirigibug / BombSarai) — DeepSeek handoff

Parent issue #244. Implementation owner: Codex through shared account 4laric;
executing agent: DeepSeek (session `deepseek/p2-l27`). Root/native bases and
commits below are the lane-owned worktrees only; no shared checkout was
modified and nothing was pushed.

## Source identity and slice

- Concrete source ID: **BombSarai — Careening Dirigibug, EnemyID 58** (payload
  `Bomb`, EnemyID 36, `mChildNum=2`). Source projectPiki/pikmin2 rev
  `632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0).
- Slice delivered: **animated capture joint** — the captured payload now rides
  the carrier's moving pose (hover bob + facing) instead of the prior static
  profile joint point. Directly targets the next-wave goal's "animated capture
  joint" and the FSM doc's top open item ("the bomb rides a static joint
  offset, not the animated joint").

## Ordered commits

Native branch `deepseek/p2-l27-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`, clean:

1. `2a57e318` — `lane27: BombSarai animated capture joint: payload rides the moving carrier (#244)`
2. `74533062` — `lane27: CMake hook — register p2_bombsarai_joint_test ctest gate (#244)`

Root branch `deepseek/p2-l27`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`, clean:

1. `2aa53b1` — `lane27: BombSarai animated capture joint — root harness/gates/tests (#244)`

Dirty state at handoff: none on either branch (`git status --short` empty).

## Files owned / interfaces touched

Native, lane-owned:
- `pc_port/pc_p2_bombsarai_bomb.h` / `.cpp` — new `P2BombSaraiBomb::followJoint`
  (moves a Captured bomb to the carrier's current capture-joint world position,
  mirroring `bomb.cpp:23-44`; no-op in any other phase, rejects non-finite input).
- `pc_port/pc_p2_bombsarai_joint.h` — new engine-free `P2BombSaraiJoint::compute`
  (body-local offset rotated by carrier yaw, matching the Release lob convention
  `(50·sin face, 100, 50·cos face)`; kĴamu_jnt1 stand-in until #128).
- `pc_port/pc_p2_bombsarai_arena.h` / `.cpp` — arena now treats the profile
  `joint` as a **body-relative offset**; each source tick it resolves the joint
  into world space from the hover-integrated body origin and calls `followJoint`
  on the held bomb; `supply` captures at the joint world position. New accessor
  `pc_p2_bombsarai_arena_captured_position` for fixtures.
- `tools/p2-bombsarai-arena.txt`, `-purple.txt`, `-death.txt` — `joint 0 -40 0`
  (body-relative) instead of the old absolute `joint 0 55 0`.
- `tools/p2_bombsarai_runtime.cpp` — asserts captured-joint travel each scenario
  (`P2_BOMBSARAI_JOINT_FOLLOW` marker; fails if travel_y <= 0.01).
- `tools/p2_bombsarai_joint_test.cpp` — new standalone transform + follow gate.

Shared-file hook (separate commit, additive only):
- `CMakeLists.txt` — one `add_executable`/`add_test` for `p2_bombsarai_joint_test`
  beside the existing BombSarai ctest block.

Root, lane-owned:
- `experimental/pikmin2_bombsarai_arena.py` — scenario payloads use the
  body-relative joint; new gate `animated_capture_joint` (PASS).
- `tests/test_pikmin2_bombsarai_install.py` — new test asserting scenario
  payloads carry `joint 0 -40 0` and the new gate.
- `docs/PIKMIN2_BOMBSARAI_FSM.md` — open item updated to reflect the follow.

No shared semantics changed: no `teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp` or `pc_p2_preview.cpp` edits.
The arena is still an opt-in profile seam (pinned carrier, scripted events);
this slice is not a gameplay/register admission.

## Build evidence

From `output/dsw/l27-build-evidence.txt` (Ninja + MinGW g++, JAudio ON, private
`native-l27-build`):

```
lane=l27 target=pikmin_pc       native=745330622e027366aa7d7d13b8c99c4401ed74c9 dirty=no exe=...\bin\nectar.exe sha256=e1d500d687b6ac711cc8e5cfa97dc2fa0f67cc54929fd855ea85baa6af76d885 ninja_n="ninja: no work to do."
lane=l27 target=p2_bombsarai_joint_test native=745330622e027366aa7d7d13b8c99c4401ed74c9 dirty=no ninja_n="ninja: no work to do."
```

Production build of `pikmin_pc` succeeded (603 objects, links `nectar.exe`); the
`ninja -n` dry run is clean. Note: the wrapper does not pass
`-DPIKMIN_NATIVE_JAUDIO`; the private build was configured with
`-DPIKMIN_NATIVE_JAUDIO=ON` (the maintained configuration) via a slot-wrapped
`cmake` because the OFF default fails to link `Jac_NoteDemoSkipped`.

## Tests run

Native standalone (compiled `-std=gnu++17 -Wall -Wextra -Werror`, MinGW GCC 16.2),
all PASS:
- `p2_bombsarai_joint_test` (new): zero-yaw offset, yaw rotation of forward and
  lateral offsets matches the lob convention, followJoint rides three hover
  bodies, no-op after throw / before capture, NaN rejection.
- Re-run existing suite: `p2_bombsarai_fsm_test`, `p2_bombsarai_bomb_test`,
  `p2_bombsarai_blast_test`, `p2_bombsarai_clock_test`, `p2_bombsarai_hover_test`,
  `p2_bombsarai_terrain_test`, `p2_bombsarai_induction_test` — all PASS.

Root Python: `py -3.12 -m pytest tests/test_pikmin2_bombsarai_install.py -q`
→ **21 passed**.

## Six arena gates (honest)

| Gate | Status | Evidence / label |
|---|---|---|
| 1 Exact identity and spawn | source-backed N/A (unchanged) | Still the pinned opt-in profile (`P2_BOMBSARAI_ARENA_1`); no ordinary spawn binding. |
| 2 Autonomous movement and animation | PARTIAL (unit only) | Animated capture joint now follows the carrier hover bob + yaw (new `followJoint` + `P2BombSaraiJoint`); carrier horizontal `walkToTarget` still pinned/blocked. |
| 3 Attacks and receivers | UNTESTED (unchanged) | Blast still routes to instrumented receivers, not live creatures (lane 10 boundary). |
| 4 Death and corpse | source-backed N/A (unchanged) | Existing FSM death/corpse decision paths preserved, not re-exercised this slice. |
| 5 Actual transport and reward | source-backed N/A | Out of this slice's scope; no transport/reward seam touched. |
| 6 Cleanup and re-entry | UNTESTED (unchanged) | Arena reset path unchanged; no scene re-entry run. |

Injected vs natural: the entire arena seam (carrier, receivers, event script) is
**injected**; this slice's captured-joint *follow* is a natural policy behavior
validated at unit level (`joint_test`) but not yet on a live arena. A
fixture-only/policy PASS is not claimed as a gameplay PASS.

## Fixture baseline adoption

BLOCKED on the converted room input. `preview_pikmin2_room.prepare` requires the
converted P2 room `C:/Users/alari/pikmin-randomizer/output/pikmin2-room105/room.mod`
(plus `room.ini`, `treasure.mod`), which is now absent on this host (the earlier
`output/pikmin2-room105` directory has been cleaned; `find output -name room.mod`
returns nothing). Regenerating it is converter/install scope (#128 / lane 05),
heavy, and not a lane-27 edit. Therefore the 960x540 centred-window + live
20-red-squad runtime observation was NOT re-executed on this slice; the code
path is unchanged and the runtime fixture's new `P2_BOMBSARAI_JOINT_FOLLOW`
assertion is compile-verified but not yet run against retail room geometry.

## Assumptions

- `joint` profile semantics changed from an absolute world point to a
  **body-relative offset**; the offset `(0,-40,0)` keeps the payload 40 units
  below the body center (clear of the floor during hover) and is chosen for the
  follow demonstration, not a skeleton-extracted value.
- The "animated" component is the carrier hover bob (already integrated) plus
  yaw rotation; no per-clip skeletal pitch tilt is added because the real
  `kamu_jnt1` joint transform is #128 converter work.
- No shared receiver/damage/lifetime semantics were introduced; lane 10/07/08
  remain the providers for live routing and teardown.

## Remaining blockers (named providers)

- Live creature damage/receivers: lane 10 (`#408`).
- Horizontal `walkToTarget` carrier autonomy: lane 27 next slice (Fuefuki's
  Napkid vehicle / a TEKI proxy is the in-repo pattern).
- Real skeletal joint, keyframe timings, visual assets: converter #128 / lane 09.
- Shared Bomb manager pool limit + BombOtakara interplay: lane 06/20.
- Converted room105 regeneration for any live arena run: install #05 / lane 01.

## One exact reproduction command

```powershell
# From the native worktree (MinGW g++ on PATH):
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_bombsarai_joint_test.cpp pc_port/pc_p2_bombsarai_bomb.cpp -o p2_bombsarai_joint_test.exe
./p2_bombsarai_joint_test.exe   # exits 0: PASS (transform + followJoint)
```
