# Cannon projectile proxy receiver (lane 20, #169 / #406 / #410–#413 / #424/#425/#427)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4.1-flash), 2026-09-13. Extends the projectile integration
candidate; this is the **strike -> receiver** half of the lane, bounded to a
private host-owned proxy so no engine `Creature` health is touched and no
#186 shared damage semantics are needed.

## What it adds

`pc_port/pc_p2_projectile_receiver.{h,cpp}` — a host-owned `P2ProjectileReceiver`
(id, max/current health, alive) plus a fixed-capacity, token-keyed registry:

- `applyStrike(kind, damage, targetToken, attributedToken)` clamps damage at zero,
  sets dead exactly once, and reports the applied amount in
  `P2ProjectileReceiverHit` (`known`/`applied`/`died`).
- Overloads accept the existing `P2CannonStoneContactResult` /
  `P2RockHazardContactResult`; a contact that emits no strike is a no-op, so the
  damage model is never re-derived (it consumes the Stone/Rock policy result).
- `receiver <token> <maxHealth>` rows register exact receivers; `receiver any
  <maxHealth>` registers a single wildcard sink. The wildcard exists because
  engine creature tokens are runtime pointers an arena config cannot name, which
  is what makes a real runtime demo possible.

Wiring (`pc_port/pc_p2_projectiles.cpp`): `detectStoneContacts()` and
`detectRockContacts()` route each emitted strike into the registry and print

```
P2_PROJECTILE_RECEIVER_HIT token=<u64> kind=InteractPress|InteractAttack damage=<f> health=<f> attributed=<u64>
P2_PROJECTILE_RECEIVER_DEAD token=<u64>
```

`receiver` rows are parsed and validated (non-finite/non-positive health,
duplicate tokens, capacity exhaustion, malformed selectors all fail closed).
`pc_p2_projectiles_reset()` clears the registry. The only shared edit is one
additive `CMakeLists.txt` source line.

## Verification

- Standalone (engine-free, warning-clean): `tools/p2_projectile_receiver_test.cpp`
  covers damage math, clamp/death-once, unknown-token and `None`-kind no-ops,
  registry validation/reset, the wildcard sink and exact-token precedence, and
  direct comparisons against the documented Stone/Rock contact rules.
  ```powershell
  g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_projectile_receiver_test.cpp `
      pc_port/pc_p2_projectile_receiver.cpp pc_port/pc_p2_cannon_stone.cpp pc_port/pc_p2_rock_hazard.cpp `
      -o output/p2_projectile_receiver_test.exe   # exit 0, sha256 7AD5DB8E...E269C2D
  ```
- Private `pikmin_pc` build (`output/native-projectiles-integration-build`,
  `PIKMIN_NATIVE_JAUDIO=ON`): links and `ninja -n` -> no work to do; `nectar.exe`
  SHA-256 `68B70E2EC41A9543C159BFFF7557E7C677AEFE809C46CEF91EF410FB03919AFC`.
- Real-GL run (`--experimental-pikmin2-room`, 960x540, cwd = the private
  projectile arena, config `receiver any 20`): `output/p2-projectiles-receiver-01`
  (log sha256 `14CCB489...2DD80FED`, config sha256 `A84EA999...4164ED5`) shows
  `P2_PROJECTILE_STRIKE` -> `P2_PROJECTILE_RECEIVER_HIT damage=10.0 health=10.0`
  -> `P2_PROJECTILE_RECEIVER_HIT ... health=0.0` ->
  `P2_PROJECTILE_RECEIVER_DEAD` (2 hits, 1 death). The window line is
  `Experimental preview window set to 960x540 windowed and centered`.

## Fixture baseline note

This run used the lane's **custom projectile arena harness**
(`output/p2-projectiles-native/arena/...`, 24 generator-spawned creatures, no
Onion/Pod), not a regenerated family room; the fan-out permits unsupported
custom runners with explicit equivalent starting-squad evidence, which is the
arena's 24 recognised generators and the 960x540 window above. A full #404
adoption with the current overlay is still required for the final lane
acceptance once the real Kabuto actor path lands.

## Remaining (not claimed here)

- Real Kabuto/Rkabuto/Fkabuto actor registration + per-species animated mouth
  matrix/animation bank (the "actual cannon actor + moving muzzle" half).
- Egg drop commands -> real births (`P2_PROJECTILE_EGG_ITEM` is still a report).
- Engine receiver wiring / target-health mutation, which is shared-semantics and
  needs #186 review; the proxy is deliberately not that.
- Locomotion, save/resume, and animation-event execution.

## Provenance

Native candidate: `opencode/p2-projectiles-integration` (local-only, not pushed)
@ `be8037af5e1d50dcd0d96333d48761cf52e27f84`, base `104d6dfa`. Patch series:
`native-candidates/projectiles-receiver/0001-*.patch`. Native origin/upstream
were not pushed. No maintained checkout or shared build modified.
