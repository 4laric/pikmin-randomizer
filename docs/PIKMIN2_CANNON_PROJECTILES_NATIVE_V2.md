# Cannon Stone / Egg / FSM / Rock native projectile host seam v2 (#425, parent #169)

Implementation owner: opencode projectiles-lane session on the shared `4laric`
account. Parent [#169](https://github.com/4laric/pikmin-randomizer/issues/169)
(Cannon larvae, Groinks and projectiles); integration contract
[#186](https://github.com/4laric/pikmin-randomizer/issues/186). Child issue
#425. Predecessor evidence: [PIKMIN2_CANNON_PROJECTILES_NATIVE.md](PIKMIN2_CANNON_PROJECTILES_NATIVE.md)
(#413). Policy contracts: [PIKMIN2_CANNON_STONE_PROJECTILE.md](PIKMIN2_CANNON_STONE_PROJECTILE.md)
(#406), [PIKMIN2_EGG_HAZARD.md](PIKMIN2_EGG_HAZARD.md) (#410),
[PIKMIN2_ROCK_HAZARD.md](PIKMIN2_ROCK_HAZARD.md) (#411),
[PIKMIN2_PROJECTILE_HOST_ADAPTER.md](PIKMIN2_PROJECTILE_HOST_ADAPTER.md) (#412),
[PIKMIN2_KABUTO_CANNON.md](PIKMIN2_KABUTO_CANNON.md) (#424). Workflow:
[PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md).

This slice extends the #413 host seam in three additive ways and then reaches
runtime: (1) the Stone is now born from a **host-driven P2KabutoCannon FSM
attack cycle** (`Wait -> Turn -> Attack -> KEYEVENT_2 -> END`) using a
configured mouth joint and species homing, instead of the static setup birth;
(2) the inline homing snapshot is replaced by the committed
`P2ProjectileHostAdapter::selectTarget` fed from a live Navi/Pikmin
`P2ProjectileHostCandidateSnapshot`; (3) one `P2RockHazard` is instantiated and
driven through its falling-Rock transitions. Runtime **was reached**: a 960x540
window ran the private room 40 s with a live 20-red squad, two FSM-driven Stone
births (timeout teardown), full Rock `DropWait -> Fall -> Dead -> Killed`
teardown, an Egg drop and no extinction. Receiver/item mutations remain
deliberately unwired (see §7).

## 1. Commit provenance

| Repo / worktree | Branch | Commit | Dirty state |
|---|---|---|---|
| Native `output/native-projectiles-seam2` | `opencode/p2-projectiles-seam2` | `51bbaf00734b47de52fc9b0e8768c28d5aa382b2` (`pc_p2_projectiles: FSM-driven Stone birth, host-adapter selection, Rock hazard (#425)`) | clean after commit |
| Root `output/p2-projectiles-seam2-root` | `opencode/p2-projectiles-seam2-root` | `41b2f34c5f47f087173a800ca65f21bcc0326798` + this doc commit | this doc only |

Native base was `55621028` (`merge: Cannon Beetle fire-FSM policy (#424)`).
The commit is additive: the committed policies and their standalone fixtures
(`tools/p2_cannon_stone_test.cpp`, `p2_egg_hazard_test.cpp`,
`p2_rock_hazard_test.cpp`, `p2_projectile_host_test.cpp`,
`p2_kabuto_cannon_test.cpp`) were **not** modified.

### Owned / changed files

Edited (additive): `pc_port/pc_p2_projectiles.cpp`,
`pc_port/pc_p2_projectiles.h`, `CMakeLists.txt`. No other native file changed.
`CMakeLists.txt` now compiles three already-committed policy TUs into
`pikmin_pc`: `pc_port/pc_p2_kabuto_cannon.cpp`,
`pc_port/pc_p2_projectile_host.cpp`, `pc_port/pc_p2_rock_hazard.cpp` (they were
previously only used by the standalone fixtures).

## 2. What v2 adds

- **FSM-driven Stone birth (#424).** `pc_p2_projectiles.cpp` hosts one
  `P2KabutoCannon`. A `kabuto` row selects the species (`Kabuto`/`Rkabuto`/
  `Fkabuto`), the mouth-joint world position and facing, `mMaxAttackAngle` and
  `mHealth`, plus the `Wait`/`Turn`/`Attack` tick lengths and the `KEYEVENT_2`
  fire tick. The host ticks one 30 Hz source event at a time and, on
  `P2KabutoAction::FireStone`, calls
  `P2KabutoCannon::takeBirth(mouthJoint, faceDir, birth)` and then
  `P2CannonStone::birth(birth.mouthPosition, birth.faceDir, birth.homing,
  kabutoSelf, stoneSelf)`. `takeBirth` applies the source `+25 y` mouth offset
  (`Kabuto.cpp:276`) and Rkabuto-only homing (`Kabuto.cpp:268-290`). The cycle
  freezes while a Stone is in flight and resumes after teardown, so exactly one
  Stone is active at a time. When a `kabuto` row is present the #413 static
  setup birth is suppressed; the `stone` row still supplies the projectile
  parameters. Without a `kabuto` row the #413 static birth path is unchanged.
- **Adapter homing selection (#412).** `selectHostTarget()` enumerates the
  active `naviMgr->getNavi()` and every live `Piki` into a
  `P2ProjectileHostCandidateSnapshot` (Navi also present as a candidate so the
  population matches `EnemyFunc::getNearestPikminOrNavi`), then calls
  `P2ProjectileHostAdapter::selectTarget(origin, snapshot, sightRadius)`. The
  adapter applies active-Navi precedence, else the nearest live candidate by 2D
  x/z squared distance. This replaces the former inline snapshot.
- **Falling-Rock hazard (#411).** A `rock` row instantiates one `P2RockHazard`.
  The host supplies `P2RockHazardDetection` (active Navi / any live Pikmin
  within `mSightRadius`, a 3D host approximation), a `RockMapBinding` P1
  static-map sphere trace (center/base conversion, `floorTriangle` from
  `mGroundTriangle`), and proximity-based contacts. Every phase change and
  contact/strike/health-zero event is logged. The host does not apply damage.
- **Registration unchanged.** Still `pc_p2_projectiles_setup()` from
  `pc_p2_preview_setup()`, reset/forget from the `tekimgr.cpp` batch-2 sites and
  `pc_p2_projectiles_update()` from the `gameCoreSection.cpp` hard-lane seam.
  A missing `p2-projectiles.txt` remains a no-op.

## 3. `p2-projectiles.txt` format (extended)

```text
P2_PROJECTILES_1
seed <u32>
stone  <x> <y> <z> <faceDeg> <homing0|1> <moveSpeed> <searchRumbleSpeed> <turnSpeed> <maxTurnAngle> <attackDamage> <sightRadius> <collisionRadius> <health> <sourceToken>
kabuto <Kabuto|Rkabuto|Fkabuto> <mouthX> <mouthY> <mouthZ> <faceDeg> <maxAttackAngle> <health> <waitTicks> <turnTicks> <attackTicks> <key2Tick>
rock   <x> <y> <z> <dropGroupNone0|1> <timedAppear0|1> <initialTimer> <fallSpeed> <fallOffset> <scaleUpRate> <sightRadius> <attackDamage> <collisionRadius> <health> <sourceToken> <selfToken>
egg    <x> <y> <z> <dropGroup0|1> <singleNectar> <doubleNectar> <mitites> <spicy> <bitter> <forcedDropType> <health> <checkSprays0|1> <damage> <damageTick>
```

Rows are optional but at least one of `stone`/`egg`/`rock` is required; a
`kabuto` row additionally requires a `stone` row. `stone` and `egg` are the v1
rows. For `kabuto`, `<mouth*> ` is the **mouth joint** world position *before*
the source `+25 y` birth offset, `<faceDeg>` is the firing facing, and
`<waitTicks>/<turnTicks>/<attackTicks>` are motion hold lengths with
`<key2Tick>` the `KEYEVENT_2` frame (`attackTicks > key2Tick >= 0`). For `rock`,
`1` for `dropGroupNone` starts the hidden `Wait` branch and `0` starts
`DropWait -> Fall`; `sourceToken`/`selfToken` are Press attribution tokens.

Arena config actually used (SHA-256
`352956DE6856F589C691AA8A44FB6D14391A777228E650EA6F3275F0C5D5BEED`):

```text
P2_PROJECTILES_1
seed 12345
stone 60.0 30.0 0.0 -90.0 1 250.0 100.0 0.3 30.0 10.0 350.0 27.0 99999.0 0
kabuto Rkabuto 60.0 30.0 0.0 -90.0 30.0 850.0 30 15 20 8
rock 60.0 120.0 0.0 0 0 0.0 250.0 100.0 5.0 350.0 10.0 27.0 99999.0 0 1347048015
egg -60.0 0.0 0.0 0 0.5 0.35 0.05 0.05 0.05 0 50.0 1 50.0 20
```

## 4. Private build (private directory; never `native/build-randomizer`)

Toolchain: MinGW GCC (msys64) `C:/msys64/mingw64/bin/g++.exe`, CMake 4.4.3,
Ninja (Python-bundled). `PIKMIN_NATIVE_JAUDIO=ON` is required (default `OFF`
fails to link `Jac_NoteDemoSkipped()`, a pre-existing configuration fact).
Private build dir: `output/native-projectiles-seam2-build/`.

```powershell
$env:PATH='C:\msys64\mingw64\bin;' + (Join-Path $env:LOCALAPPDATA 'Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts') + ';' + $env:PATH
cmake -S output/native-projectiles-seam2 -B output/native-projectiles-seam2-build -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DPIKMIN_NATIVE_JAUDIO=ON
cmake --build output/native-projectiles-seam2-build --target pikmin_pc -j 6
cmake --build output/native-projectiles-seam2-build --target pikmin_pc -- -n   # expect: ninja: no work to do.
```

| Step | Result |
|---|---|
| Configure exit code | `0` |
| Build exit code | `0` (`[521/521] Linking CXX executable bin\nectar.exe`) |
| Dry-run | `ninja: no work to do.`, exit `0` |
| Executable | `output/native-projectiles-seam2-build/bin/nectar.exe` (28,154,036 bytes) |
| Executable SHA-256 | `A34EB0B71709319CD7C27CAF090FFBCA69A2CDF7E1DE109290E6E1376DFF59FA` |

Logs: `output/p2-projectiles-seam2/configure.log`, `build.log`, `dryrun.log`.

## 5. Fixture baseline adoption

Root `scripts/preview_pikmin2_room.py` in this worktree is byte-identical to the
maintained checkout (SHA-256
`4ABE0E950A1C7F137572D976ED62FD5A794C079683253A13BDE8BFEE47762A5A`), i.e. the
`overlay()`/`ensure_pikmin_squad()` behaviour is present; no script change was
needed. Arena was regenerated into a **new** private directory with the current
root `prepare()`/`overlay()`. The standard `pikmin_pc` (`nectar.exe`) entrypoint
was used, not a replacement-main fixture, so no `provenance.json` applies; the
window path is the maintained `pc_main.cpp`
`PIKMIN_P2_ROOM_WINDOW`/`pc_window_center()` path.

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #425 / P2 projectiles (FSM Stone birth, host-adapter selection, Rock hazard) / Codex (shared 4laric account)
Root commit + dirty state / overlay source: root 41b2f34c5f47f087173a800ca65f21bcc0326798 + this doc commit; this doc only; scripts/preview_pikmin2_room.py sha256 4ABE0E950A1C7F137572D976ED62FD5A794C079683253A13BDE8BFEE47762A5A (== maintained)
Native commit + dirty state / worktree / private build directory: native 51bbaf00734b47de52fc9b0e8768c28d5aa382b2; clean; output/native-projectiles-seam2; output/native-projectiles-seam2-build
Squad change present / window change present (ancestry or source evidence): squad overlay present in current overlay()/generator() (20 red Pikmin records); window behaviour present in pc_main.cpp and observed (log line + Win32 measurement)
Fresh arena command / run directory / asset and config hashes: prepare(assets=C:/Users/alari/pikmin-local/game/assets, converted=output/pikmin2-room105, output=output/p2-projectiles-seam2/arena) -> arena/11c1ec853c034aa8a030e161fc87915a; default.gen(chal0) sha256 2F6FD4950392FA2D7707F664C390366AFDAD1E8CF8A4300D18BE707B07228792; chal0.ini sha256 0F8C38FE73AECF593F3B580D5C60F6511536AEBD4221008CC5BD2F26E06EBA75; room.mod sha256 BE5DACC8E01406F800AF1C60094DB9BCFDAD5C6C3E1C81E0F2A5715C42283A08; p2-projectiles.txt sha256 352956DE6856F589C691AA8A44FB6D14391A777228E650EA6F3275F0C5D5BEED
Executable SHA-256 / fixture provenance status if applicable: A34EB0B71709319CD7C27CAF090FFBCA69A2CDF7E1DE109290E6E1376DFF59FA; standard pikmin_pc (nectar.exe) entrypoint, no replacement-main fixture (provenance.json N/A)
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540; log line "Experimental preview window set to 960x540 windowed and centered"; Win32 GetWindowRect re-measure returned "Open Nectar" chrome rect 976x579 at (365,232) on a 1707x1067 primary display (x-centre (1707-976)/2=365.5 matches)
Live starting Pikmin / active gameplay / no immediate extinction evidence: "[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1"; "[PC Generator] default: initialised 24 recognised generators, spawned 24 creatures"; sustained 29.6-30.1 FPS (19 samples over the run); no PIKI ZERO / GAME OVER / extinction lines in run_stdout.log or run_stderr.log
PASS, FAIL, or BLOCKED; remaining work: PASS for FSM-driven birth + adapter selection + Rock transitions + standard fixture baseline; remaining: real per-species mouth matrix/animation bank, receiver routing and target-health mutation, Egg item births, save/resume and full-scene teardown (see §8)
```

Primary run dir:
`output/p2-projectiles-seam2/arena/11c1ec853c034aa8a030e161fc87915a/`
(`run_stdout.log`, `run_stderr.log`, `p2-projectiles.txt`,
`probe_stdout.log`, `probe_stderr.log`).

## 6. Run command and observed events

```powershell
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
# cwd = output/p2-projectiles-seam2/arena/11c1ec853c034aa8a030e161fc87915a
& 'C:\Users\alari\pikmin-randomizer\output\native-projectiles-seam2-build\bin\nectar.exe' --experimental-pikmin2-room
```

The 40 s launch was driven by `// py -3.12 output/p2-projectiles-seam2/run_acceptance.py`
(Python `subprocess` with stdout/stderr redirected to files, per the #413 note
that `Start-Process -RedirectStandardOutput` captures zero bytes for this app).
Python wrapper exit `0`; child `returncode 1` because it was intentionally
terminated after 40 s (it did not self-exit or crash). `run_stdout.log` 50,308
bytes; `run_stderr.log` 607 bytes. Relevant `run_stdout.log` lines:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered (override with PIKMIN_P2_ROOM_WINDOW=WxH or =off).
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
P2_PROJECTILE_KABUTO_READY species=Rkabuto mouth=(60.0,30.0,0.0) face_deg=-90.0 max_attack_angle=30.0 health=850.0 wait=30 turn=15 attack=20 key2=8
P2_PROJECTILE_ROCK_PHASE from=Inactive to=DropWait pos=(60.0,120.0,0.0) scale=1.0000 traces=0 floors=0
P2_PROJECTILE_EGG_BORN x=-60.0 y=0.0 z=0.0 drop_group=0 health=50.0
P2_PROJECTILES_READY stone=1 egg=1 kabuto=1 rock=1 seed=12345
P2_PROJECTILE_ROCK_PHASE from=DropWait to=Fall pos=(60.0,120.0,0.0) scale=1.0000 traces=0 floors=0
P2_PROJECTILE_ROCK_PHASE from=Fall to=Dead pos=(60.0,27.0,0.0) scale=1.0000 traces=12 floors=1
P2_PROJECTILE_EGG_DAMAGE amount=50.0 health=0.0 injected=1
P2_PROJECTILE_EGG_DROP type=2 items=1 fallback=0 offset_y=2.0
P2_PROJECTILE_EGG_ITEM index=0 kind=2 pellet_color=0 mitites=0 vx=0.0 vy=250.0 vz=0.0
P2_PROJECTILE_ROCK_DESTROY reason=floor traces=12 floors=1 contacts=0
P2_PROJECTILE_ROCK_PHASE from=Dead to=Killed pos=(60.0,27.0,0.0) scale=1.0000 traces=12 floors=1
P2_PROJECTILE_KABUTO_ACTION phase=Turn action=ToTurn tick=30
P2_PROJECTILE_KABUTO_ACTION phase=Attack action=ToAttack tick=15
P2_PROJECTILE_KABUTO_FIRE species=Rkabuto homing=1 mouth=(60.0,30.0,0.0) birth=(60.0,55.0,0.0) face_deg=-90.0 source=1347109460 fire=1
P2_PROJECTILE_KABUTO_ACTION phase=Attack action=FireStone tick=8
P2_PROJECTILE_STONE_DEAD x=60.8 y=55.0 z=135.5 timer=15.00 health=99999.0
P2_PROJECTILE_STONE_DESTROY reason=timeout traces=450 floors=0 walls=0
P2_PROJECTILE_KABUTO_ACTION phase=Turn action=ToTurn tick=20
P2_PROJECTILE_KABUTO_ACTION phase=Attack action=ToAttack tick=15
P2_PROJECTILE_KABUTO_FIRE species=Rkabuto homing=1 mouth=(60.0,30.0,0.0) birth=(60.0,55.0,0.0) face_deg=-90.0 source=1347109460 fire=2
P2_PROJECTILE_KABUTO_ACTION phase=Attack action=FireStone tick=8
```

Interpretation:

- The FSM sequence is exactly `Wait END -> ToTurn`, `Turn END -> ToAttack`,
  `Attack KEYEVENT_2 -> FireStone`, then after the Stone dies
  `Attack END -> ToTurn` and a second `FireStone`. The `_ACTION` line prints the
  phase **after** the action, hence `phase=Turn action=ToTurn`.
- `mouth=(60,30,0)` and `birth=(60,55,0)` prove the `takeBirth` `+25 y` offset.
  `homing=1` proves the Rkabuto species homing flag.
- Homing steering is evidenced by the trajectory: `face_deg=-90` implies an
  initial `-x` velocity (`moveSpeed*sin(-90 deg)`), but the Stone ended at
  `x=60.8, z=135.5`, i.e. redirected toward `+z` by the adapter-selected target.
- The first Stone ran the full 15 s source timeout with 450 static-map traces,
  `Move -> Dead`, held, and was reaped by `finishDeath()`.
- The Rock completed `DropWait -> Fall -> Dead(floor) -> Killed`; `contacts=0`
  in this arena (no creature overlap on the fall column), so only phase
  transitions are proven for contacts here.
- The Egg ran the injected-damage -> drop-table path; no items were birthed.

## 7. Shared-semantics boundary (#186)

Unchanged from #413. The host does **not** apply `InteractPress`/`InteractAttack`
to target health, does not birth pellets/nectar/Mitites, does not change actor
lifetime (policies only mark their own host slots), and does not touch saves,
captain state or the real per-species Kabuto actor. These remain requests for
#186 review.

## 8. Arena gates

| # | Gate | Status | Evidence / limitation |
|---|---|---|---|
| 1 | Exact identity and spawn | PASS (host arena spawn + FSM birth); natural engine actor BLOCKED | `KABUTO_FIRE` + `takeBirth` birth at `(60,55,0)`; identity is the #424 FSM + #406 Stone policy. Not a real `tekiMgr` Kabuto; no per-species mouth matrix/animation bank. |
| 2 | Autonomous movement and animation | PASS (motion); animation UNTESTED | 450 Stone traces, adapter homing steering, 15 s timeout; Rock fall trace 12 calls. No converted Stone/Kabuto/Rock animation drawn. |
| 3 | Attacks and receivers | PASS (FSM fire + classification path); receiver UNTESTED | FSM `FireStone` twice; host contact classification exists but this run logged 0 Stone/Rock strikes (no overlap). No target-health mutation. |
| 4 | Death and corpse | PASS; corpse source-backed N/A | `STONE_DEAD -> DESTROY reason=timeout`; `ROCK_PHASE Fall -> Dead -> Killed`, `ROCK_DESTROY reason=floor`; Egg `Broken`. `EB_LeaveCarcass` disabled in source. |
| 5 | Actual transport and reward | transport source-backed N/A; drop selection PASS, item birth UNTESTED | `EGG_DROP type=2 items=1` + `EGG_ITEM kind=2 v(0,250,0)`; no pellet/Mitite/Honey birth, no carry route. |
| 6 | Cleanup and re-entry | PASS (host reset/forget + policy kill); full scene teardown UNTESTED | `pc_p2_projectiles_reset/forget` wired to `tekimgr` hooks and clear both contact dedupe sets; `finishDeath()` reaps. Manager recreation is not full scene/heap teardown or campaign resume. |

## 9. Standalone suites (task 7)

Recompiled from the merged/base worktree `output/native-projectiles-seam2` with
MinGW GCC, `-std=gnu++17 -Wall -Wextra -Werror`, run into
`output/p2-projectiles-seam2/suites/`. All warning-clean and exit 0:

| Suite | Sources | Compile exit | Build stderr | Run exit |
|---|---|---|---|---|
| `p2_cannon_stone_test` | `pc_p2_cannon_stone.cpp` | 0 | 0 bytes | 0 |
| `p2_egg_hazard_test` | `pc_p2_egg_hazard.cpp` | 0 | 0 bytes | 0 |
| `p2_rock_hazard_test` | `pc_p2_rock_hazard.cpp` | 0 | 0 bytes | 0 |
| `p2_projectile_host_test` | `pc_p2_projectile_host.cpp` + `pc_p2_cannon_stone.cpp` | 0 | 0 bytes | 0 |
| `p2_kabuto_cannon_test` | `pc_p2_kabuto_cannon.cpp` + `pc_p2_cannon_stone.cpp` | 0 | 0 bytes | 0 |

## 10. Remaining blockers (honest)

- **Real Kabuto/Rkabuto actor**: still a host-driven FSM with a configured mouth
  joint; the per-species mouth matrix, animation bank, actor registration and
  damage/death of the firing Beetle are unimplemented. The FSM is proven as a
  policy, not as a live `tekiMgr` enemy.
- **Receiver routing and target health**: deferred to #186; only logged.
- **Stone/Rock strikes in this arena**: 0 contacts because the FSM mouth birth
  is at `y=55` and the fall/travel column did not overlap a creature; the
  classification path itself is covered by the #412/#406/#411 fixtures, not by
  runtime strikes here.
- **Animation/visuals**: no converted Stone/Kabuto/Rock visual; the host is
  policy/draw-independent.
- **Egg item births, capture/fall physics, `damage1` restart**: not wired.
- **Save/resume and full-scene teardown/re-entry**: untested.

Exact next command after a future `kabuto`/receiver change:

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake --build output/native-projectiles-seam2-build --target pikmin_pc -j 6
# rerun the arena dir with p2-projectiles.txt adjusted for the new mouth joint
# or a receiver target once #186 routing lands.
```
