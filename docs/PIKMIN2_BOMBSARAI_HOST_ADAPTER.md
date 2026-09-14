# Pikmin 2 Careening Dirigibug host terrain adapter and blast routing contract (#244)

Implementation owner: Codex using shared account 4laric. Terrain/clock pattern #169, integration contract #186. Prior slices: [source audit](PIKMIN2_BOMBSARAI_AUDIT.md), [projectile lifecycle contract](PIKMIN2_BOMBSARAI_PROJECTILE_CONTRACT.md). This slice adds the host terrain-trace adapter contract, the hover vertical-control policy and the blast receiver routing policy. Still no shared hooks, no Groink-lane edits, no converter/build changes, no native actor registration.

## Scope

Lane-owned files, native branch `codex/p2-bombsarai-policy` (worktree `output/native-bombsarai-policy/`):

- `pc_port/pc_p2_bombsarai_terrain.h` / `.cpp` — engine-free host terrain adapter contract (P1 static-map trace + groundY correction).
- `pc_port/pc_p2_bombsarai_hover.h` / `.cpp` — dirigibug hover vertical-control policy over the adapter's height sampling.
- `pc_port/pc_p2_bombsarai_blast.h` / `.cpp` — blast receiver classification/attribution routing policy.
- `tools/p2_bombsarai_terrain_test.cpp`, `tools/p2_bombsarai_hover_test.cpp`, `tools/p2_bombsarai_blast_test.cpp` — standalone fixtures.

Source reference: projectPiki/pikmin2 revision `632af93787b9c95b63f0c13be32b161375ce3a96` (US GPVE01 rev 0).

## Terrain adapter contract

Mirrors the #169 Groink adapter pattern (`pc_p2_groink_map_trace.h/.cpp`, [PIKMIN2_GROINK_PROTOTYPE.md](PIKMIN2_GROINK_PROTOTYPE.md)). The Groink adapter binds P1 `MapMgr`/`Creature` directly; this lane keeps the identical contract engine-free so the binding can be serialized later by the root-owned host integration. The host supplies two primitives as callbacks: a `traceMove` equivalent (sphere base in, trace-mutated position/velocity plus ground-triangle/wall flags out) and a `getMinY(x, z, false)` equivalent. The adapter owns:

- **Center/base conversion.** P1 `traceMove` accepts a sphere base (it adds the radius before collision and subtracts it afterward); the bomb policy stores its center. The adapter traces with `center.y - radius` and returns `position.y + radius`. Passing the center directly shifts the collision sphere upward by the radius.
- **Contact classification.** Floor = ground triangle present; wall = wall callback fired. Floor contact feeds the bomb policy's arming decision; wall contact never arms. The owner's collision fields must never be reused for projectile traces (dedicated proxy rule from the Groink lane).
- **GroundY on contact.** On floor OR wall contact the host must sample `getMinY` and provide a finite value; a contact without a terrain sample fails the whole trace — the adapter never invents ground.
- **Landing correction.** A traced center below the sampled terrain is clamped to the ground. The Groink shell used ground+10 (its source raises a below-ground+20 shell to ground+10); the source bomb rests on its floor triangle with no such offset, so the clamp target is the ground itself. Sphere center therefore rests at `groundY + radius` through the base/center conversion. Any visual rest offset is a converter/asset input owned by the host.
- **Validation.** Non-finite or out-of-range (±100000, same bound as Groink) coordinates, non-positive radius, and any delta other than the 30 Hz source delta fail the trace; the policy then performs straight integration only when no trace was performed.

P1 contact classification and bounce behavior remain host approximations, not Pikmin 2 collision parity.

## Hover vertical-control policy

`P2BombSaraiHover::update` mirrors `BombSarai::Obj::setHeightVelocity`/`addPitchRatio` (`BombSarai.cpp:202-224, 251-257`) over the adapter's height sample:

- Rise factor blends linearly between `fp21` free (1.5) and `fp22` laden (1.0) over the stuck-Pikmin count clamped to [0, 5]; fast takeoff (TakeOff2) forces 6.0. Carrying Pikmin weighs the bug down.
- Vertical velocity = riseFactor × ((minY + newHeight) − y); newHeight is `fp01` (90) plus a `fp11` (20) sine oscillation driven at `fp10` (2.5)/s, engaged only above `fp01 − fp11`, wrapping at TAU.
- Fixed-step only: non-source delta, failed terrain samples and non-finite positions are rejected without output. Horizontal movement, target selection and the FSM remain host-owned.

## Blast receiver routing policy

`p2_bombsarai_route_blast` mirrors the source detonation volume and attribution (`bombState.cpp:140-198`) plus the dirigibug's receiver-side immunity (`BombSarai.cpp:127-135`). The host enumerates candidates (cell-iterator equivalent) and performs the actual `InteractBomb` stimulation; the policy only classifies and attributes.

- **Volume:** exact 3D sphere at the blast radius plus the ±`fp02` (50) vertical gate, alive receivers only. Documented approximation: the source uses CellIterator cell granularity with a custom radius; the exact sphere is at least as strict. The host must never list the bomb itself (source `creature != enemy`).
- **Teki (friendly fire, unconditional):** `fp01` (250) damage, zero knockback (source passes the zero vector), attacker is always the bomb itself. No faction check — a grounded carrier is hit like any other Teki.
- **Airborne dirigibug immunity:** receivers flagged with the dirigibug `bombCallBack` contract are skipped while not grounded (source requires a floor triangle). This is what makes the flying carrier immune to its own and other bombs' blasts.
- **Navi/Pikmin:** general attack damage; knockback = normalizeXZ(receiver − center) × weight with y = weight, weight 100 (Navi) / 200 (Pikmin). A degenerate zero-length XZ separation keeps vertical-only knockback instead of inventing a direction (source `_normaliseXZ` degenerate case). Attribution carries the carrier token only when the blast recorded a confirmed-live carrier; otherwise it falls back to bomb-self, per the stale-mCarrier decision in the projectile contract.
- **Output discipline:** hits truncate cleanly at the caller's capacity; invalid input returns −1.

## Fixture evidence

Standalone MinGW GCC 16.2, all five executables compiled warning-clean (`-std=gnu++17 -Wall -Wextra -Werror`) and passing:

- **terrain:** base/center conversion values, no-sample-no-contact, floor classification with groundY sampling and below-ground clamp, full bomb arming through the adapter with center resting at `groundY + radius`, wall classification without arming, contact-without-sample failure, unbound/wrong-delta/out-of-range/NaN rejection, hover height sampling validation.
- **hover:** rise toward `minY + 90` from below with free factor 1.5, long-run convergence within one pitch amplitude of `fp01`, laden factor 1.0 at 5 stuck Pikmin with the linear 2-Pikmin blend (1.3), clamping of negative/above-5 counts, fast-takeoff 6.0, pitch-band engagement and TAU wrapping, and rejection of failed samples/wrong deltas/NaN.
- **blast:** Teki 250 unconditional with bomb-self attribution, Navi/Pikmin damage with weighted separation knockback and carrier-token attribution, dead-carrier fallback to bomb-self (Teki unaffected), airborne-immune receiver skipped vs grounded receiver hit, exact radius/vertical-gate boundaries, dead/NaN receiver skipping, capacity truncation, invalid-input −1, degenerate XZ knockback.
- **bomb/clock:** prior fixtures rerun, still passing.

These are standalone policy fixtures, not native arena or gameplay tests. The real P1 `traceMove`/`getMinY` binding, receiver enumeration via CellIterator, and `InteractBomb` stimulation are host-integration work serialized by the root.

## Open items for later slices

- Root-owned host binding of the two adapter primitives to the P1 static map (dedicated trace proxy, per the Groink lane's runtime fixture pattern), with flat-floor/vertical-wall runtime probes before enabling gameplay damage.
- Numeric inputs from converted Bomb/BombSarai assets and parms (#128): bomb trace radius, arm-loop length, fuse health, blast radius, general attack damage, gravity per tick, hover fp values if overridden by shipped parms.
- Real shared Bomb manager pool limit under concurrent carriers (audit open question).
- Multi-projectile lifetimes and bomb-on-bomb induction (`ip02`) receiver routing — induction is deliberately not routed by this policy yet.
- Save/resume and cave/day transition semantics (audit persistence caveat).
