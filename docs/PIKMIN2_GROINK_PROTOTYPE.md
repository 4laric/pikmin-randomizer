# Gatling Groink stationary prototype

Implementation owner: Codex using shared account 4laric; issues #169 and #186.
This is an isolated source-data and firing-policy milestone, not a playable enemy.

## Source and extraction

Behavior references use projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96`. Assets are extracted locally from
the user's GPVE01 revision 0 disc; no original assets are committed.

```powershell
py -3.12 -m experimental.pikmin2_groink_assets --iso <local.iso> --output <fresh-output>
py -3.12 -m unittest tests.test_pikmin2_groink_assets
```

MiniHoudai (78) and FminiHoudai (97) share the MiniHoudai model/animations
(`MiniHoudaiMgr.cpp:24,54`). The fixed variant has its own parameter file.
The extractor preserves each parameter block separately: identically named
fields in general and creature-specific blocks must not overwrite each other.

The retail resources contain 18 joints, eight animation registrations and eight
collision nodes. Both variants have search distance 250, attack radius 15,
attack hit angle 65 and attack damage 10; health is 1200 roaming and 700 fixed.
The `kuti` joint is index 13. Its model-space matrix and normalized column-zero
direction are sampled independently of visual conversion. The muzzle origin is
joint translation plus 25 times that direction. These transforms still require
the runtime vertical callback and owner transform before firing in world space.

Two fresh weighted extractions produced 63 identical files, including 24 visual
poses and 24 muzzle samples. Each visual pose has 335 vertices, 608 triangles,
three shapes and six textures. The default converter still rejects envelopes;
the Groink extractor explicitly supplies validated per-draw matrices through
the new skinning adapter. Source BCAs, event registrations and collision metadata
remain intact. Nothing is installed into a native actor yet.

## Source behavior and host contract

`MiniHoudaiShotGun.cpp:1794` derives elevation and shell speed from horizontal
target distance and source delta time, then advances elevation by at most 0.1
radians per update. `angDist(a,b)` is wrapped `a-b`; the lock threshold uses the
error before that update. The vertical callback normalizes the joint basis,
right-multiplies a local Z rotation and restores its scale (`:2071`).

Emission (`:1345`) uses the aimed joint's column zero, a 25-unit muzzle offset,
independent spread in [-0.1,0.1] on each component, renormalization and the
computed shell speed. The retail implementation emits three shells and owns six
pooled nodes; the first policy deliberately models one shell.

Movement (`:86`) traces a radius-10 sphere using the velocity and source delta,
then subtracts 20 from vertical velocity **per update**. A floor/wall collision
or an axis-wise distance greater than 1000 from the owner terminates the shell.
Retail creature-hit processing still occurs during a terminal step; host damage
integration must retain that final sweep, not discard it when recycling.

The integration lead owns shared CMake, renderer, preview and actor registry.
Required integration inputs are an owner position, source target, freshly
evaluated head matrix, source-rate ticks, explicit attack emission events and a
map sphere-trace adapter. Projectile visualization and receiver damage must be
added explicitly. Muzzle samples alone do not implement target acquisition,
body yaw, animation-event playback or the full attack state machine.

Walking, burst/pool behavior, damage receivers, effects, carcass delivery and
replacement-object revival are outside this first milestone. The independent
policy does not substitute any Pikmin 1 enemy AI. The speedup playtest and enemy
integration baseline remain separate.

## Standalone policy validation

The independent native files are `pc_port/pc_p2_groink.h/.cpp` and
`tools/p2_groink_test.cpp`, based on native `d7ff676b`. They add no shared hooks.
The host trace returns both position and velocity, plus ground height for a
collision. The policy preserves terminal sweep endpoints after recycling;
invalid steps are flagged unusable for damage. Host `std::atan2` follows the
source argument order but is an approximation to the original lookup table.

```powershell
g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_groink_test.cpp pc_port/pc_p2_groink.cpp -o <private-test.exe>
```

Compiled and executed successfully with local MinGW. Tests cover numeric near
and far aim results, pre-update lock behavior, local scaled-basis rotation,
muzzle offset, source gravity, trace correction, terminal sweep retention,
exact versus over-1000 range, wall/floor termination and invalid inputs.
This is a standalone policy test, not a native arena or gameplay test.

The skinning audit found eight real envelopes with 18 influences, including
nontrivial weights, and 16 weighted entries in the 30-entry draw table.
The adapter uses each joint's authored EVP1 inverse-bind matrix inside the
weighted sum: `sum(weight * animatedJoint * inverseJoint)`. The inverse table
is indexed by joint, not envelope, matching `J3DModelLoader.cpp:356` and
`J3DMtxBuffer.cpp:376`. Tests include different authored joint inverses and a
rotated animated hierarchy to distinguish incorrect multiplication orders.

Validation: 25 focused Python tests pass; five unrelated optional local-asset
tests skip. Additional retail checks confirm two byte-identical extractions,
default weighted rejection, and unchanged default/rigid room decoding against
base `c36def2`. Geometry inspection covers the firing frame (attack1 frame 25)
and walking from multiple views; all positions are finite and normals unit
length. All 335 converted vertices move between attack frames 0 and 25.

Materials remain approximations. The explicit weighted path consumes but omits
texture-matrix indices (Groink uses TEX2MTXIDX), recording them in conversion
sidecars. Normal baking uses the existing inverse-transpose-and-normalize path;
it does not reproduce J3D's scale-flag-dependent shortcut for unscaled weighted
matrices. Three samples per clip are a pose feasibility bank, not smooth
skeletal animation. Offline geometry images are not native rendering evidence.

## Proposed central arena integration (not implemented)

The lead owns these hooks. Keep the first harness stationary with an explicit
target and emission trigger rather than assigning a Pikmin 1 enemy AI:

```cpp
bool pc_p2_groink_preview_setup(const char* profilePath);
void pc_p2_groink_preview_reset();
bool pc_p2_groink_preview_update(const P2GroinkVec3& owner,
    const P2GroinkMuzzle& currentKutiWorld, const P2GroinkVec3& target,
    bool emitEvent4, const P2GroinkVec3& spreadUnit, float sourceDelta,
    P2GroinkTraceFn trace, void* traceContext);
void pc_p2_groink_preview_draw(Graphics&, const Matrix4f& ownerWorld);
```

Setup validates profile/pose assets and reset releases per-scene state. Update
runs once per authoritative 30 Hz simulation tick, never from draw. Draw belongs
beside the existing P2 actor drawing boundary, with graphics state restored.
The explicit event trigger is a harness control until the real attack FSM is
implemented. A selected baked pose has no animated `kuti` joint in the resulting
MOD: use the matching source muzzle sample transformed by the owner. Applying
aim only to the shell would leave the displayed muzzle unrotated, so dynamic
visual aiming needs an angle-aware bake or retained skeletal geometry before
claiming faithful muzzle alignment.

For a P1 static-map trace adapter, use a dedicated `Creature` collision proxy,
not the Groink owner's collision fields. Clear its ground triangle, collision
flag and wall flag before each trace. Override `wallCallback` to record wall
contact and read `mGroundTriangle` afterward for floor contact. Query
`getMinY(x,z,false)` on a terminal contact and return trace-mutated velocity.

P1 `MapMgr::traceMove` (`plugPikiColin/mapMgr.cpp:2315`) **adds** the radius to
the incoming Y and subtracts it before returning. P2 shell position is already
the sphere center. Therefore construct `MoveTrace` with `center.y - radius`,
then return `trace.mPosition.y + radius`; passing the center directly shifts
the actual collision sphere upward by ten units. Use radius 10 and explicitly
label `ignoreDynColl=true` as static-map-only testing. P1 contact classification
and bounce behavior are host approximations, not Pikmin 2 collision parity.
Test a flat floor and vertical wall before enabling gameplay damage. Never
discard the final retained sweep when a shell terminates.
