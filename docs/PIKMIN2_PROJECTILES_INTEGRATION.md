# Cannon projectiles lane — integration candidate (#406/#410/#411/#412/#413)

Lane owner: opencode projectiles lane via shared account `4laric`. Parent
[#169](https://github.com/4laric/pikmin-randomizer/issues/169); integration
contract [#186](https://github.com/4laric/pikmin-randomizer/issues/186).
This is a **reviewable candidate**, not a maintained-line merge. Local private
branches only; nothing pushed, `native/build-randomizer` and
`export_native_source.py` untouched.

## Candidate branches

Native `opencode/p2-projectiles-integration` @ **`3c30aa39`** (base native
`b6334b8e`, itself on `1e649cdd`):

- `292f4c80` merge Rock hazard (#411) — `7c34ec7e`
- `a637fe56` merge host adapter (#412) — `56d98c6b`
- `3c30aa39` merge native seam (#413) — `3dc24c46`

Root `opencode/p2-projectiles-integration-root` @ **`4106736`** (base
`bfe4802`):

- `d35efe5` merge Rock docs (#411) — `faa2979`
- `029bdd0` merge host adapter docs (#412) — `b6b3501`
- `4106736` merge native seam docs (#413) — `f44b834`

Both merges were clean (no conflicts); the shared
`pc_p2_cannon_stone.h` search-angle correction was identical on the Stone, host
and native branches and merged without a hunk conflict.

## Merged contents

Native (policies are standalone; the seam is the only CMake target change):

- `pc_port/pc_p2_cannon_stone.h/.cpp`, `tools/p2_cannon_stone_test.cpp` (#406)
- `pc_port/pc_p2_egg_hazard.h/.cpp`, `tools/p2_egg_hazard_test.cpp` (#410)
- `pc_port/pc_p2_rock_hazard.h/.cpp`, `tools/p2_rock_hazard_test.cpp` (#411)
- `pc_port/pc_p2_projectile_host.h/.cpp`, `tools/p2_projectile_host_test.cpp` (#412)
- `pc_port/pc_p2_projectiles.h/.cpp` + additive `CMakeLists.txt`,
  `pc_port/pc_p2_preview.cpp`, `src/plugPikiKando/gameCoreSection.cpp`,
  `src/plugPikiNakata/tekimgr.cpp` (#413)

Root docs: `PIKMIN2_CANNON_STONE_PROJECTILE.md`,
`PIKMIN2_EGG_HAZARD.md`, `PIKMIN2_ROCK_HAZARD.md`,
`PIKMIN2_PROJECTILE_HOST_ADAPTER.md`, `PIKMIN2_CANNON_PROJECTILES_NATIVE.md`.

The seam is opt-in via a `p2-projectiles.txt` in the experimental-room arena;
a missing config is a no-op. It does not change save/reward/captain/damage/
physics/actor-lifetime semantics; target health is never mutated and drops are
reported, not birthed (receiver routing is a #186 request).

## Verification (merged tree)

Standalone suites, `g++ -std=gnu++17 -Wall -Wextra -Werror`, warning-clean
(0-byte build logs) and exit 0 on the merged worktree:

- `p2_cannon_stone_test`, `p2_egg_hazard_test`, `p2_rock_hazard_test`,
  `p2_projectile_host_test` (private dir `output/p2-projectiles-integration/`).

Full private native build (`output/native-projectiles-integration-build`,
`PIKMIN_NATIVE_JAUDIO=ON`):

- configure 0, build **518/518 exit 0**, `ninja -n` → `ninja: no work to do.`
- `bin/nectar.exe` SHA-256
  **`6DAB2B935742C10A341D661BDE483DDC520761E9774D530D8016B8CED07B6B2C`**.

Real-GL runtime on the merged binary (arena
`output/p2-projectiles-native/arena/6c979fca3e8e41b5a63aa14aea275c65`,
`PIKMIN_P2_ROOM_WINDOW=960x540`, experimental-room entrypoint, ~40 s,
`stdout6.log`):

- `Experimental preview window set to 960x540 windowed and centered`
- `P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`; 24 creatures
  spawned; sustained ~30 FPS; no PIKI ZERO / GAME OVER.
- `P2_PROJECTILE_STONE_BORN` (homing=1, radius=27) → `P2_PROJECTILE_STRIKE
  kind=Press damage=10.0` ×N → `P2_PROJECTILE_STONE_DEAD timer=15.00` →
  `P2_PROJECTILE_STONE_DESTROY reason=timeout traces=450`.
- `P2_PROJECTILE_EGG_BORN` → injected `P2_PROJECTILE_EGG_DAMAGE amount=50.0` →
  `P2_PROJECTILE_EGG_DROP type=2 items=1` + `EGG_ITEM kind=2 v=(0,250,0)`.

The corrected native branch (`5B6A34FE…`) and the merged candidate
(`6DAB2B93…`) were each run; the pre-correction evidence (`BB937A2A…`,
`stdout4.log`) is superseded.

## Source-semantics correction

`Rock.cpp:376` passes `180.0f` as the `getNearestPikminOrNavi` **searchAngle**
in degrees (`enemyAction.cpp:21,45`), not a y-threshold. All branches now use
`P2CannonStone::kHomingSearchAngleDegrees` and filter homing candidates by 2D
x/z distance only; the erroneous y-window was removed.

## Gate status (candidate)

| Gate | Status |
|---|---|
| 1. Exact identity and spawn | PASS host arena; natural Kabuto FSM/mouth BLOCKED |
| 2. Autonomous movement and animation | PASS motion; animation UNTESTED (no bank drawn) |
| 3. Attacks and receivers | PASS classification/strike logging; receiver health mutation UNTESTED (#186) |
| 4. Death and corpse | PASS Dead→Killed + Egg Broken; corpse source-backed N/A |
| 5. Transport and reward | transport source-backed N/A; drop selection PASS, item birth UNTESTED |
| 6. Cleanup and re-entry | PASS reset/forget + policy kill; full scene teardown UNTESTED |

## Remaining blockers

- Firing Kabuto/Rkabuto FSM and mouth-joint alignment for the Stone.
- Receiver routing / target health mutation (shared-semantics #186 review).
- Item/pellet/Mitite births and the drop fallback.
- Animation banks and materials (#128).
- Mixed-scene performance and save/resume.

## Integration lead notes

- Native merge target: `codex/pikmin2-room-preview` maintained checkout; the
  seam's additive hooks touch `gameCoreSection.cpp`, `tekimgr.cpp` and
  `pc_p2_preview.cpp`, so review those hunks. Then rebuild
  `native/build-randomizer`, run `ninja -n`, and `py -3.12
  scripts/export_native_source.py`.
- Do not push native origin. Keep this candidate immutable once QA copies it.
