# P1 Breadbug actor with P2 small Breadbug visuals

Scope #168/#186. `pc_p2_breadbug_actor.h/.cpp` binds only configured existing
TEKI_Collec8 instances. This is a P1 gameplay proxy with P2 appearance, not a
ported PanModoki FSM. Giant and nest substitution are excluded.

`experimental.pikmin2_breadbug_actor.install(profile, private_run, ids)` consumes
the previous verified small visual profile. It validates one existing Collec
record per requested ID, builds exact UTF-8 config bytes and copies16 wait/move
sample models with an actor-specific prefix. It does not rewrite generators or
apply position/yaw. Root arena staging remains responsible for source/template
selection, full effective XYZ, count and ordinary control placement.

Native `P2_BREADBUG_ACTOR_PROXY_1` config contains the two sampled motion rows,
then1..8 unique generator IDs with expected native type8. Setup matches actual
live Teki instances and aborts on missing, wrong-type or duplicate instances.
Logs include ID, native type, effective XYZ and `P1_Collec_proxy`. Existing P1
collision, target selection, nest/cargo arbitration, health, attacks and receipt
behavior are unchanged. No sourceP2 damage/strength thresholds are applied.

Live draw receives the existing actor view matrix. Horizontal velocity selects
wait or move source samples, looping on a30fps visual clock; switching between
them restarts visual phase. This does not drive or synchronize P1 animation
keyevents. Carry, hurt, pulled and hidden states do not gain their P2 source
animations. Dead actors and corpse rendering fall through to the existing P1
visual path. This intentionally avoids representing unimplemented death/corpse
behavior as a completed source port.

Approved shared edits in this lane:

- `tekibteki.cpp`: include new header and delegate live drawing before the other
  family delegates. No corpse-draw hook.
- `tekimgr.cpp`: reset mappings in existing init/create/reset paths and forget
  the exact actor on existing release. No AI or generator changes.

Root owns CMake and the preview setup call. Exports are setup(), reset(),
forget(BTeki*) and draw(BTeki*,Graphics&,const Matrix4f&). Setup must run in the
normal asset-loading heap context; shape storage follows gameflow stage lifetime.
All source resources are validated before loading each bounded shape. No native
reward/name override is installed; the game retains its P1 Breadbug identity.

Validation this batch: native module syntax-only compile passed using observed
MinGW flags (private log output/p2-lifecycle-batch/breadbug-actor-syntax.log).
Eleven tests and four subtests pass across actor installer, visual profile and
asset reference. Tests cover exact type/identity, duplicate generators, config
bytes, source hashes, Giant rejection, frame endpoints, preserved generator bytes
and overwrite refusal. This is not a linked/runtime build claim.

Next native gates after root integration: exact opted-in spawn XYZ and unchanged
control; natural P1 movement with mapped source visuals; stage cleanup/reload
without stale actor registration; later ordinary cargo/receiver/corpse regression.
The first arena should use a non-progression pellet and remain outside live seeds.
No gameplay or natural-carry acceptance is claimed here; installed manifest sets
native_validated=false. No shared build/export/commit was performed by this lane.
