# Cannon Stone / Egg native projectile host seam (#413, parent #169)

Implementation owner: opencode projectiles-lane session on the shared `4laric`
account. Parent [#169](https://github.com/4laric/pikmin-randomizer/issues/169)
(Cannon larvae, Groinks and projectiles); integration contract
[#186](https://github.com/4laric/pikmin-randomizer/issues/186). Policy
contracts: [PIKMIN2_CANNON_STONE_PROJECTILE.md](PIKMIN2_CANNON_STONE_PROJECTILE.md)
(#406) and [PIKMIN2_EGG_HAZARD.md](PIKMIN2_EGG_HAZARD.md) (#410). Workflow:
[PIKMIN2_IMPLEMENTATION_FANOUT.md](PIKMIN2_IMPLEMENTATION_FANOUT.md),
[batch-2 native registration](PIKMIN2_BATCH2_NATIVE_REGISTRATION.md).

This slice binds the already-committed, engine-free Stone (#406) and Egg (#410)
policies to the live P1 engine with a thin, opt-in host. Runtime **was reached**:
a 960x540 centred window ran the private room for 35 s with a live 20-red squad
and real Stone/Egg host events, with no crash and no immediate extinction. Only
host trace/target/contact logging is wired; receiver mutations and item births
were intentionally **not** performed (see §7).

## 1. Commit provenance

| Repo / worktree | Branch | Commit | Dirty state |
|---|---|---|---|
| Native `output/native-projectiles-native` | `opencode/p2-projectiles-native` | `35138970353b78aaccccc76acf6c4d71b8ff693a` (`pc_p2_projectiles: additive Stone/Egg host seam with P1 map trace (#413)`) | clean after commit |
| Root `output/p2-projectiles-native-root` | `opencode/p2-projectiles-native-root` | `0b936855c00f513a31fd2e909c72b9ffdf1aa0f2` + this doc commit | this doc only |

Native base was `1e649cdd` (Egg policy, #410); the seam is a single additive
commit. The committed policies' standalone fixtures
(`tools/p2_cannon_stone_test.cpp`, `tools/p2_egg_hazard_test.cpp`) were not
modified and still build unchanged.

### Owned files

New: `pc_port/pc_p2_projectiles.h`, `pc_port/pc_p2_projectiles.cpp`.
Edited (additive hooks only): `CMakeLists.txt`, `pc_port/pc_p2_preview.cpp`,
`src/plugPikiNakata/tekimgr.cpp`, `src/plugPikiKando/gameCoreSection.cpp`.

## 2. How Kabuto/Rkabuto/Rock/Bomb/Egg are currently staged (identity vs proxy)

This is the pre-existing batch-2 seam (`pc_port/pc_p2_batch2.cpp`, doc
[PIKMIN2_BATCH2_NATIVE_REGISTRATION.md](PIKMIN2_BATCH2_NATIVE_REGISTRATION.md)).
It is a **visual-only P1 proxy**, not source identity.

| P2 species | Native vehicle | `expectedType` | Config source | What is real | What is proxy |
|---|---|---|---|---|---|
| Kabuto, Rkabuto, Fkabuto | P1 Armored Cannon Beetle | `TEKI_Beatle` (17) | `p2-cannon-actors.txt` (`P2_CANNON_ACTORS_1`, `<generator> <Species>`) | generator ID → species string, native teki type | P1 actor AI, health, collision, animation; a sampled P2 pose bank is drawn over it |
| Rock, Stone | P1 Rolling Boulder | `TEKI_Iwagon` (2) | same | as above | as above |
| Bomb, Egg | P1 Dwarf Bulborb | `TEKI_Chappy` (3) | same | as above | as above |

- **Setup** `pc_p2_batch2_setup()` (called from `pc_p2_preview_setup()` after the
  other family setups) parses the actor/bank configs, matches generator IDs to
  live `tekiMgr` vehicles, verifies `mTekiType`, loads
  `courses/pikmin2room/cannon_<species>_<clip>_NN.mod`, and logs
  `P2_BATCH2_BIND generator=… key=<family|Species> visual_only=1
  native_fsm=unimplemented`.
- **Draw** `pc_p2_batch2_draw` is called from both the corpse and live fallback
  chains in `src/plugPikiNakata/tekibteki.cpp`; it returns false for actors it
  does not own, so unconfigured/ordinary P1 actors keep the default draw.
- **Reset/forget** `pc_p2_batch2_reset()` runs at the `tekimgr.cpp` reset /
  teardown / stage-constructor points; `pc_p2_batch2_forget(teki)` runs on actor
  reuse so a recycled pointer is never assumed live.
- **Non-claims**: no source P2 FSM, projectile, damage/elemental receiver,
  capture, boss-phase or reward semantics. All runtime gates were BLOCKED or
  UNTESTED in that pass.

In the run recorded below the batch-2 pose banks were **not installed**
(`P2_BATCH2_BANK total_mod_bytes=0 species=0`); the new projectiles host does
not depend on them, so the Kabuto/Rock/Bomb visual proxies were absent while the
Stone/Egg policies ran. That separation is intentional and documented.

## 3. The new additive host seam

`pc_port/pc_p2_projectiles.{h,cpp}` instantiates the Stone and Egg policies on
top of the live engine:

- **Registration (additive, opt-in)**: setup `pc_p2_projectiles_setup()` from
  `pc_p2_preview_setup()` next to `pc_p2_batch2_setup()`; reset/forget from the
  existing `tekimgr.cpp` batch-2 reset/forget sites; update
  `pc_p2_projectiles_update()` from the hard-lane update seam in
  `gameCoreSection.cpp`. A missing `p2-projectiles.txt` is a no-op, so ordinary
  P1 play and unconfigured rooms are untouched.
- **Terrain trace into the P1 static map**: `ProjectileMapBinding` is a
  dedicated `Creature` proxy (`wallCallback` sets `wall`) never registered with
  an actor manager. P2CannonStone positions are sphere **centres**; P1
  `MapMgr::traceMove` accepts a sphere **base** and adds/subtracts the radius
  itself, so the host sends `base = centre - (0, radius, 0)`, calls
  `traceMove(proxy, MoveTrace(base, velocity, radius, /*ignoreDynColl=*/true),
  delta)`, and recovers `centre = rawBase + (0, radius, 0)`. `ignoreDynColl=true`
  means static-map-only testing, the same explicitly-labelled approximation as
  the BombSarai (#244) adapter. `wallCallback` → policy `traced.wall` →
  `ROCK_Move → ROCK_Dead`.
- **Homing target snapshot**: when `homing=1`, the host snapshots the active
  `naviMgr->getNavi()`, else the nearest live Pikmin within `sightRadius` by 2D
  x/z distance. The source call passes a 180-degree `searchAngle`
  (`kHomingSearchAngleDegrees`, unrestricted), so there is no y or facing
  filter; no target is invented by the policy.
- **Contact / strike logging**: after each Stone tick the host proximity-tests
  the Navi, every Piki and every Teki inside `collisionRadius + 12`, classifies
  the target, and calls the policy `contact(kind, onFloor, …)` once per token.
  `Press`/`Attack`, damage, target token, attribution and `health_zeroed` are
  logged. `onFloor` is a host approximation (position within 40 units of
  `getMinY(x,z,true)`).
- **Egg host**: opt-in injected `damage` at `damageTick` (an explicitly labelled
  fixture intervention) plus drop-group proximity contact, a deterministic
  scripted RNG, and `update()` → `P2EggDrop` selection; the drop table is
  logged, never birthed.
- **Clean reset/forget**: `pc_p2_projectiles_reset()` resets both policies,
  counters and the binding; `pc_p2_projectiles_forget(BTeki*)` clears the
  pointer-derived contact dedupe so a reused pointer cannot suppress a fresh
  contact.

Config format (`p2-projectiles.txt`, read from the run cwd):

```text
P2_PROJECTILES_1
seed <u32>
stone <x> <y> <z> <faceDeg> <homing0|1> <moveSpeed> <searchRumbleSpeed> <turnSpeed> <maxTurnAngle> <attackDamage> <sightRadius> <collisionRadius> <health> <sourceToken>
egg <x> <y> <z> <dropGroup0|1> <singleNectar> <doubleNectar> <mitites> <spicy> <bitter> <forcedDropType> <health> <checkSprays0|1> <damage> <damageTick>
```

## 4. Private build

Toolchain: MinGW GCC 16.2.0, CMake 4.4.3, Ninja 1.13.2 (Python-bundled), private
build dir `output/native-projectiles-native-build/`. `PIKMIN_NATIVE_JAUDIO=ON`
is required: with the default `OFF`, `moviePlayer.cpp` references
`Jac_NoteDemoSkipped()` which is only defined by `src/jaudio/pikidemo.c`, so the
default link fails (`link.log`). This is a pre-existing configuration fact, not
caused by this seam.

```powershell
$env:PATH='C:\msys64\mingw64\bin;' + (Join-Path $env:LOCALAPPDATA 'Packages\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\LocalCache\local-packages\Python312\Scripts') + ';' + $env:PATH
cmake -S output/native-projectiles-native -B output/native-projectiles-native-build -G Ninja -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ -DPIKMIN_NATIVE_JAUDIO=ON
cmake --build output/native-projectiles-native-build --target pikmin_pc -j 6
cmake --build output/native-projectiles-native-build --target pikmin_pc -- -n   # expect: ninja: no work to do.
```

- Build exit code: `0`. Dry run: `ninja: no work to do.`, exit `0`.
- Executable: `output/native-projectiles-native-build/bin/nectar.exe`
  (28,090,745 bytes).
- Executable SHA-256:
  `BB937A2A24D6A0A2C0D5056AA6799C9F1B23FBF6886F2097AFE9B6D8309DCB2C`.

## 5. Fixture baseline adoption

The root `scripts/preview_pikmin2_room.py` in this worktree is byte-identical to
the maintained checkout (SHA-256
`4ABE0E950A1C7F137572D976ED62FD5A794C079683253A13BDE8BFEE47762A5A`), i.e. the
current `overlay()`/`ensure_pikmin_squad()` behavior is present; no script
change was needed. Arena was regenerated into a **new** private directory with
the current root `prepare()`/`overlay()`. The standard `pikmin_pc` entrypoint
(`pc_main.cpp`) was used, not a replacement-main fixture, so no
`provenance.json` applies; the window behaviour is the maintained `pc_main.cpp`
`PIKMIN_P2_ROOM_WINDOW`/`pc_window_center()` path.

```text
Fixture baseline adoption
Child issue / lane / implementation owner: #413 / P2 projectiles (Stone+Egg native host) / Codex (shared 4laric account)
Root commit + dirty state / overlay source: root 0b936855 + this doc commit; clean; scripts/preview_pikmin2_room.py sha256 4ABE0E95…7762A5A (== maintained)
Native commit + dirty state / worktree / private build directory: native 35138970353b78aaccccc76acf6c4d71b8ff693a; clean; output/native-projectiles-native; output/native-projectiles-native-build
Squad change present / window change present (ancestry or source evidence): squad overlay present in current overlay()/generator() (20 red Pikmin records); window behavior present in pc_main.cpp pc_test_window_size()/pc_window_center() and observed
Fresh arena command / run directory / asset and config hashes: prepare(assets=C:/Users/alari/pikmin-local/game/assets, converted=output/pikmin2-room105, output=output/p2-projectiles-native/arena) -> arena/6c979fca3e8e41b5a63aa14aea275c65; default.gen sha256 2F6FD495…8728792; chal0.ini sha256 0F8C38FE…06EBA75; room.mod sha256 BE5DACC8…2283A08; p2-projectiles.txt sha256 5373918F…7D2502A
Executable SHA-256 / fixture provenance status if applicable: BB937A2A24D6A0A2C0D5056AA6799C9F1B23FBF6886F2097AFE9B6D8309DCB2C; standard pikmin_pc (nectar.exe) entrypoint, no replacement-main fixture (provenance.json N/A)
Window setting / observed size and centring evidence: PIKMIN_P2_ROOM_WINDOW=960x540; log line "Experimental preview window set to 960x540 windowed and centered"; GetWindowRect client+chrome 976x579 at desktop-centred (365,232) (window_pw.png shows the "Open Nectar" title bar; the GL client is not GDI-capturable)
Live starting Pikmin / active gameplay / no immediate extinction evidence: "[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1"; "[PC Generator] default: initialised 24 recognised generators, spawned 24 creatures"; sustained ~30 FPS; no PIKI ZERO / GAME OVER / extinction lines in stdout.log
PASS, FAIL, or BLOCKED; remaining work: PASS for the host seam + standard fixture baseline; remaining: natural Kabuto-fired spawn, receiver filtering/damage, item births, animation banks, save/resume (see §7)
```

Primary run dir:
`output/p2-projectiles-native/arena/6c979fca3e8e41b5a63aa14aea275c65/`
(`assets/`, `stdout.log`, `stderr.log`, `window_pw.png`, `p2-projectiles.txt`).
`window.png` is an occluded screen-region capture of a concurrent lane's window
and is **not** evidence.

## 6. Run command and observed events

```powershell
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
# cwd = output/p2-projectiles-native/arena/6c979fca3e8e41b5a63aa14aea275c65
& 'C:\Users\alari\pikmin-randomizer\output\native-projectiles-native-build\bin\nectar.exe' --experimental-pikmin2-room
```

Run exit code: **N/A** — the process was intentionally stopped after 35 s of
live gameplay (it did not self-exit or crash; `Stop-Process` was used). Relevant
`stdout.log` lines:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered ...
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
[Pikipelago] P2_ROOM_READY treasure=bolt carry=5 repairs=1
P2_PROJECTILE_STONE_BORN x=60.0 y=30.0 z=0.0 face_deg=-90.0 homing=1 source=0 radius=27.0
P2_PROJECTILE_EGG_BORN x=-60.0 y=0.0 z=0.0 drop_group=0 health=50.0
P2_PROJECTILES_READY stone=1 egg=1 seed=12345
P2_PROJECTILE_EGG_DAMAGE amount=50.0 health=0.0 injected=1
P2_PROJECTILE_EGG_DROP type=2 items=1 fallback=0 offset_y=2.0
P2_PROJECTILE_EGG_ITEM index=0 kind=2 pellet_color=0 mitites=0 vx=0.0 vy=250.0 vz=0.0
P2_PROJECTILE_STRIKE kind=Press damage=10.0 target=… attributed=1347048276 source=0 health_zeroed=0   (x20 distinct Pikmin tokens)
P2_PROJECTILE_STONE_DEAD x=60.7 y=30.0 z=136.1 timer=15.00 health=99999.0
P2_PROJECTILE_STONE_DESTROY reason=timeout traces=450 floors=0 walls=0
```

`attributed=1347048276` is the host self token `0x504A5354`; `source=0` means the
firing-Kabuto source token was absent, so the Press is self-attributed exactly
as the policy specifies. The Stone ran the full 15 s source timeout with 450
static-map traces (≈30 Hz × 15 s), reached `Dead`, held, and `finishDeath()`
reaped it — the complete birth → motion → contact → destruction path, plus the
Egg damage → drop-table path. The Egg's `EGG_DROP_ITEM` velocity
`(0, 250, 0)` matches `baseSpawnVelocity()`.

## 7. Shared-semantics boundary (#186)

The host deliberately does **not**:

- apply `InteractPress`/`InteractAttack` damage to Navi/Piki/Teki health
  (sources would be mutated here; that is generic damage / receiver routing),
- birth pellets/nectar/Mitites (reward/item semantics),
- change actor lifetime (the policy's `finishDeath()` only marks the host's
  own slot `Killed`; no engine actor is killed),
- touch saves, captain state or the firing Kabuto/Rkabuto FSM.

Those remain **requests for #186 shared-semantics review**, not silently
implemented behavior.

## 8. Arena gates

| # | Gate | Status | Evidence / limitation |
|---|---|---|---|
| 1 | Exact identity and spawn | PASS (host arena spawn); natural FSM BLOCKED | `P2_PROJECTILE_STONE_BORN`/`EGG_BORN`; identity is the #406/#410 policy. Not born from a Kabuto mouth joint; firing Kabuto FSM + mouth alignment unimplemented. |
| 2 | Autonomous movement and animation | PASS (motion); animation UNTESTED | 450 traces, homing steering, 15 s timeout, `Dead`→`Killed`; no converted Stone/Egg animation bank is drawn (batch2 visual proxies were unconfigured: `P2_BATCH2_BANK … species=0`). |
| 3 | Attacks and receivers | PASS (classification/strike event); receiver UNTESTED | 20 `P2_PROJECTILE_STRIKE kind=Press` events, self attribution; host only logs, does not mutate target health (see §7). |
| 4 | Death and corpse | PASS; corpse source-backed N/A | `P2_PROJECTILE_STONE_DEAD`→`_DESTROY`; Egg `Broken` same-tick; `EB_LeaveCarcass` disabled (`Rock.cpp:59`, `egg.cpp:38`). |
| 5 | Actual transport and reward | transport source-backed N/A; drop selection PASS, item birth UNTESTED | `P2_PROJECTILE_EGG_DROP type=2 items=1` + `_EGG_ITEM kind=2 v(0,250,0)`; no pellet/Mitite/Honey birth, no carry route. |
| 6 | Cleanup and re-entry | PASS (host reset/forget + policy kill); full scene teardown UNTESTED | `pc_p2_projectiles_reset/forget` wired into `tekimgr` batch-2 hooks; `finishDeath()` reaps the slot. Manager-recreation is not full scene/heap teardown or campaign resume. |

## 9. Remaining blockers (honest)

- Firing Kabuto/Rkabuto/Fkabuto attack FSM, mouth-joint alignment and the buried
  `FixKabuto` path: not implemented (spawn is host/arena-injected).
- Receiver routing (`InteractPress`/`InteractAttack`) and target-health mutation:
  deferred to #186; only logged here.
- Egg item/pellet/Mitite births, null-check fallbacks, capture/fall physics and
  the `damage1` animation restart: not wired.
- Converted Stone/Egg animation banks and visibility (batch2 proxy draw): not
  exercised; the host is policy/draw-independent.
- Save/resume of in-flight projectiles and full-scene teardown/re-entry.

Exact next command for a human / integration lead after #186 receiver review:

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
cmake --build output/native-projectiles-native-build --target pikmin_pc -j 6
# then run the same arena dir with a p2-projectiles.txt whose stone/egg rows
# exercise a real receiver target once receiver routing lands.
```
