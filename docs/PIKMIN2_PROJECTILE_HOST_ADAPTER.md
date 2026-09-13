# Projectile host trace/target adapter contract (#412)

Implementation owner: opencode projectiles-lane session using shared account
`4laric`. Parent: [#169](https://github.com/4laric/pikmin-randomizer/issues/169)
(Cannon larvae, Groinks and projectiles). Integration contract:
[#186](https://github.com/4laric/pikmin-randomizer/issues/186). This is the
#169/#198 "pure policy vs host adapter" slice for the Cannon Stone projectile.

This document covers **only** the host adapter that bridges the pure Cannon
Stone policy (`pc_port/pc_p2_cannon_stone.h/.cpp`, #406) to host services. The
pure policy owns the source state machine, steering, contact classification and
strike events; this adapter owns the three host concerns the policy deliberately
never touches: homing target selection, terrain movement (sphere trace), and
strike-attribution token liveness.

This is an **isolated policy/adapter slice**: lane-owned new files only, no
shared hooks, no converter/build changes, and **no native/runtime claim**. No
actor is registered, no executable beyond the standalone fixture is launched,
and no arena or save is touched.

Source reference is projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0); line numbers
follow `native/pikmin2-research`.

## Lane-owned files

Native branch `opencode/p2-projectiles-host` at base native `1e649cdd`:

- `pc_port/pc_p2_projectile_host.h` / `.cpp` — isolated host adapter.
- `tools/p2_projectile_host_test.cpp` — standalone fixture executable.
- `docs/PIKMIN2_PROJECTILE_HOST_ADAPTER.md` — this contract (root worktree
  `opencode/p2-projectiles-host-root`, base `0b93685`).

No edit to `pc_p2_cannon_stone.*`, `pc_p2_egg_hazard.*`, `pc_p2_bombsarai_*`,
`pc_p2_groink_*` or any shared/engine file. The committed Stone contract is
consumed as-is.

## 1. Interfaces

The adapter adds no universal base class. It exposes three narrow services,
each justified by a field the committed Stone contract already requires.

### 1.1 Homing candidate snapshot and selection

```cpp
struct P2ProjectileHostCandidate {          // one nearby Pikmin/Navi
    P2CannonStoneVec3 position;
    std::uint64_t token = 0;
    bool alive = false;                     // Creature::isAlive()
};

struct P2ProjectileHostCandidateSnapshot {  // host snapshot for one update
    bool hasActiveNavi = false;
    P2CannonStoneVec3 activeNaviPosition;
    std::uint64_t activeNaviToken = 0;
    const P2ProjectileHostCandidate* candidates = nullptr;
    int candidateCount = 0;
};

static P2CannonStoneTarget selectTarget(
    const P2CannonStoneVec3& origin,
    const P2ProjectileHostCandidateSnapshot& snapshot,
    float sightRadius);
```

Selection mirrors `Obj::updateMoveVelocity` (`Rock.cpp:368-388`):

1. **Active Navi first, unconditionally.** The source takes
   `naviMgr->getActiveNavi()` with no range check (`:372-374`). A supplied active
   Navi is used even when outside sight radius and the y window. A non-finite
   active-Navi position is ignored and selection falls through.
2. **Else nearest live candidate** within `sightRadius` and the y window. The
   distance metric is 2D squared distance in x/z, matching
   `getNearestNavi`/`getNearestPikmin` (`enemyAction.cpp:47-53,393-399`).
   Equal distances keep list order (deterministic). Dead and non-finite
   candidates are skipped. `sightRadius < 0` means unlimited, matching the
   source `searchRadius < 0 -> FLT_MAX` (`:23-27`); a non-finite radius yields
   no target.
3. **Else no target** (`P2CannonStoneTarget::hasTarget = false`), which the pure
   policy turns into "keep the current heading"
   (`targetPos = mPosition + mTargetVelocity`, `Rock.cpp:382-384`).

The y window is the committed policy constant
`P2CannonStone::kHomingHeightThreshold` (180.0). The source call site passes
`180.0f` as the `searchAngle` argument to
`EnemyFunc::getNearestPikminOrNavi` (`Rock.cpp:376`); in the decompiled helper
that argument is a horizontal full-circle tolerance (`enemyAction.cpp:21,45`),
so no horizontal facing is filtered here either. The lane reads the committed
180 as a **±180 world-unit y window** (`|candidate.y - origin.y| <= 180`) and
this adapter implements that reading explicitly rather than silently claiming
source parity. The threshold is fixed by the committed policy; the adapter does
not invent a different value.

### 1.2 Terrain-trace provider

```cpp
struct P2ProjectileHostTrace {          // host trace output, sphere-CENTER space
    P2CannonStoneVec3 position;
    P2CannonStoneVec3 velocity;
    bool floor = false;
    bool wall = false;
    float groundY = 0.0f;
    bool hasGroundY = false;
};

typedef bool (*P2ProjectileHostTraceFn)(void* context,
                                        const P2CannonStoneVec3& center,
                                        const P2CannonStoneVec3& velocity,
                                        float delta, float radius,
                                        P2ProjectileHostTrace& result);

static bool trace(void* context, const P2CannonStoneVec3& center,
                  const P2CannonStoneVec3& velocity, float delta, float radius,
                  P2CannonStoneTraceResult& result);  // P2CannonStoneTraceFn
```

The host binds `P2ProjectileHostTraceFn` and passes
`P2ProjectileHostAdapter::trace` directly to
`P2CannonStone::update(delta, target, trace, &adapter)`. The bridge validates
the request, calls the host provider, validates the response and maps it to the
committed `P2CannonStoneTraceResult`. Validation rejects: null context/unbound
provider, non-finite or absurd (>100000) center/velocity, a delta that is not
`P2CannonStone::kSourceDelta`, a non-finite or non-positive radius, non-finite
or absurd host output, and a floor/wall contact without a finite groundY. Any
failure returns `false`, so the policy falls back to direct integration rather
than acting on invented terrain.

`P2CannonStoneTraceResult` carries only `position`, `velocity` and `wall`; the
committed policy has no floor field. The bridge therefore forwards `wall`
(the only contact the pure policy reacts to) and uses the floor/groundY fields
only to enforce the host contract. The adapter does not clamp, bounce or
otherwise invent a landing correction — those remain host terrain-response
decisions.

### 1.3 Strike-attribution token liveness

```cpp
typedef bool (*P2ProjectileHostTokenLiveFn)(void* context, std::uint64_t token);

struct P2ProjectileHostStrikeResult {
    P2CannonStoneContactResult contact;   // pure policy result, unchanged
    bool targetLive = false;
    bool attributedLive = false;
    bool unreachable = false;
    std::uint64_t attributionToken = 0;
};

P2ProjectileHostStrikeResult contact(P2CannonStone& stone,
                                     P2CannonStoneContactKind kind,
                                     bool targetOnFloor, bool targetIsRock,
                                     std::uint64_t targetToken) const;
```

The adapter calls the pure `P2CannonStone::contact` and annotates the result
with host liveness. A strike whose `targetToken` is stale is marked
`unreachable = true`; the host must not route that damage to a dead/reused
creature. A stale attribution token resolves `attributionToken` to the Stone's
`selfToken()`, mirroring the BombSarai stale-carrier fallback to bomb-self
attribution (`pc_p2_bombsarai_bomb.h:49-59`,
`docs/PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md`). An unbound provider or token 0
is unconfirmed (`false`), matching the BombSarai no-callback fallback.

## 2. Coordinate conventions

- **Axes.** x/z are horizontal, y is up. This matches the committed Stone
  policy (`pc_p2_cannon_stone.h:75-79`).
- **Horizontal angle.** `roundAng(atan2(dx, dz))`, per `trig.h:91-94`, matching
  `Creature::getAngDist` (`Creature.h:386-395`). The adapter does not compute
  angles itself; it selects the target position and the policy steers.
- **Y window.** See §1.1: the committed `kHomingHeightThreshold` is read as a
  ±180 world-unit y window.

### 2.1 Trace-space convention (explicitly not the Groink/P1 convention)

The host trace provider receives and returns the projectile sphere **CENTER**.

This deliberately differs from the Groink/BombSarai adapter, whose raw host
primitive is P1 `MapMgr::traceMove`: that primitive takes a sphere **BASE**
(`center.y - radius`), because P1 adds the radius before collision and subtracts
it afterward, so the adapter there constructs `center.y - radius` on the way in
and returns `position.y + radius` on the way out (`PIKMIN2_GROINK_PROTOTYPE.md`
"standalone policy validation" and `pc_p2_bombsarai_terrain.cpp:38-53`).

The pure Stone policy stores its position as the sphere center and passes
`collisionRadius` alongside it (`pc_p2_cannon_stone.h:81-89`). Center-in /
center-out is therefore the direct mapping and avoids a second, error-prone
offset. A host binding a P1 base-space primitive must perform its own
center-to-base conversion before calling that primitive and convert back after;
this adapter does **not** apply the Groink radius conversion.

### 2.2 groundY contract

On a floor or wall contact, the host provider must set `hasGroundY = true` and a
finite `groundY`. A contact without a terrain sample fails the trace instead of
inventing ground. The adapter does not apply the BombSarai shell/landing clamp;
the pure Stone contract has no floor field, so the host owns the terrain
response and any rest offset.

## 3. Host responsibilities

The adapter never dereferences creatures, the map or the effect system:

- Supply the active Navi (if any) and a candidate list each homing update, and
  provide `sightRadius` (the committed `P2CannonStoneConfig::sightRadius`).
- Implement the sphere trace against the real static map / creature physics,
  in center space, and supply floor/wall + groundY on contact.
- Issue stable `uint64_t` tokens for candidates and strike targets and answer
  liveness via `P2ProjectileHostTokenLiveFn`; never hand the adapter raw
  pointers.
- Route `P2CannonStoneStrike` damage to receivers only when not `unreachable`,
  and use `attributionToken` for attribution. Receiver stimulation, effects,
  sound, the firing Kabuto/Rkabuto/Fkabuto FSM, the shared Rock manager limit
  and save/resume remain outside this slice.
- Registration with the native actor registry remains integration-lead work;
  this slice adds no shared hooks.

## 4. Fixture evidence

Standalone MinGW build, no engine objects (same convention as the Groink,
BombSarai and Cannon Stone lanes). Exact command:

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
g++ -std=gnu++17 -Wall -Wextra -Werror `
    -I output/native-projectiles-host/pc_port `
    output/native-projectiles-host/tools/p2_projectile_host_test.cpp `
    output/native-projectiles-host/pc_port/pc_p2_projectile_host.cpp `
    output/native-projectiles-host/pc_port/pc_p2_cannon_stone.cpp `
    -o output/p2-projectiles-host/p2_projectile_host_test.exe
```

Private run directory `output/p2-projectiles-host/`:

| Artifact | Value |
|---|---|
| Compiler | local MinGW GCC 16.2.0 (`C:/msys64/mingw64/bin/g++.exe`) |
| Native base commit | `1e649cdd` |
| `build.log` (stderr) | 0 bytes (warning-clean) |
| Compile exit code | 0 |
| `run.log` (stdout) | 0 bytes |
| Run stderr | 0 bytes |
| Run exit code | 0 |
| Executable SHA-256 | `15E28D6087E0A2ADF3797E28B32AEC12AB2FD27E0515BE4F2FF1D72C8095FA23` |

The MinGW PE linker embeds a link timestamp, so the executable hash is
per-link and not byte-reproducible; the hash above is for the exact artifact
left in `output/p2-projectiles-host/`, built from native `092ba8a5`. A fresh
build of the committed sources is warning-clean with compile exit 0 and the
fixture exits 0.

Fixture coverage (`tools/p2_projectile_host_test.cpp`, asserts active):

- **Active-Navi precedence:** active Navi beats a nearer candidate and is used
  even when far outside sight radius / y window; a non-finite active-Navi
  position falls through to the candidate list.
- **Nearest-candidate selection:** nearest by 2D distance wins; dead candidates
  are skipped; equal distances keep list order; null/empty snapshot yields no
  target.
- **Sight-radius filtering:** outside filtered, exactly-at-radius included,
  `sightRadius < 0` unlimited, non-finite radius yields no target.
- **180 y-threshold filtering:** exactly ±180 included, just outside filtered;
  the window is relative to the Stone's own y.
- **No-target fallback:** empty selection leaves the born heading and
  target-speed unchanged; after a turn, losing the target keeps the new heading.
- **Trace floor/wall mapping:** center/radius passthrough in center space;
  position/velocity mapping; `wall` maps to `P2CannonStoneTraceResult::wall`
  and drives Move -> Dead; floor with groundY is valid and does not set `wall`;
  contact without groundY fails the trace.
- **Token liveness / stale fallback:** live target + live source (attributed to
  source); stale source resolves attribution to the Stone self token; stale
  target marks `unreachable`; Teki self-attribution; unbound provider
  unconfirmed; non-strike contact annotates nothing.
- **Invalid/NaN immutability:** wrong delta, zero/negative/non-finite radius,
  non-finite or absurd center/velocity, non-finite delta, and unbound provider
  all fail `trace` without touching the caller's result; invalid deltas leave
  the pure policy face direction/timer/position unchanged; non-finite
  origin/candidate selection data is ignored.

This is a standalone policy/adapter test, **not** a native arena or gameplay
test. It makes no claim that the Stone is registered or runs natively.

## 5. Open items for later slices

- Bind the adapter to the real P1 `MapMgr`/creature-physics trace with the
  host-side center/base conversion documented in §2.1, and add the center-space
  ground response the pure Stone contract omits.
- Wire receiver routing for `InteractPress`/`InteractAttack` using
  `attributionToken`/`unreachable`, with separate acceptance evidence.
- Native token registry backing `P2ProjectileHostTokenLiveFn` over reused
  creature slots; current host tokens are unimplemented.
- Firing Kabuto/Rkabuto/Fkabuto attack FSM and mouth-joint alignment feeding
  `selectTarget` and `trace`.
- Numeric parm values bound to converted assets (#128/#350) and the shared Rock
  manager pool limit under concurrent Stones.
- Save/resume of in-flight Stones; native registration and arena gates.

Reference issue: [#412](https://github.com/4laric/pikmin-randomizer/issues/412).
