# Groink target and attack-END snapshot policy (#206)

Codex hard lane, based on 69ad3b05. Source revision
632af93787b9c95b63f0c13be32b161375ce3a96, MiniHoudai.cpp:447-456,492-530
and MiniHoudaiState.cpp:336-398. These new modules have no shared hooks,
actor pointers, target registrations or locomotion implementation.

The corridor selector returns the first qualifying cell candidate, preserving
iterator order rather than sorting by distance. Candidates must be living
captains or actual Pikmin. Relative to the shotgun origin, vertical separation
must be strictly below 200, lateral separation strictly below 25, and forward
projection strictly greater than 1 and below searchDistance. No result means
preserve the old stored target position, not clear it.

The host must first enumerate the source-compatible cell sphere centered at
body position + direction * (searchDistance/2), radius 0.75*searchDistance,
with source iteration order. The selector does not replace this broad phase.
Supply the horizontal source getDirection(faceDir) vector; tolerance 0.001
on squared unit length accommodates source trig approximations without
renormalizing supplied values. Tests that directly supply candidates establish
narrow-phase behavior, not live spatial-query parity.

Attack END chooses in this exact order:

1. Nonpositive health -> Dead; flick -> Flick.
2. XZ squared distance strictly beyond territory radius squared -> home.
3. Successful fresh corridor query -> Attack.
4. Successful searched-target query -> Walk/Turn at inclusive max attack angle.
5. Strictly inside home radius -> WalkPath/TurnPath.
6. Otherwise -> WalkHome/TurnHome.

Home/path walking includes the exact 45-degree boundary. The host supplies
getAngDist results in radians, while maxAttackAngle remains source degrees.
This avoids silently replacing the source atan lookup and wrapping behavior.
Source getAngDist ignores Y and computes angDist(target angle, face direction).

Queries in the snapshot must be side-effect-free until the decision is valid:
commit mTargetPosition only when useAttackableQuery AND attackable, using the
selector's found position. Reset mHealthGaugeTimer only when useSearchedQuery
AND searchedTarget. A failed search preserves both fields; searched target
does not itself overwrite mTargetPosition in Attack END. Earlier branches
must not perform later-query side effects. Receiver/target lifetime remains
host-owned. The source nearest helper prefers a Pikmin result over a captain
result; exact underlying candidate tie ordering is not established here.

Adapter validation rejects nonfinite or out-of-budget snapshots atomically,
even if an invalid later field would not be read by the source branch. Vector
components/radii/health/degrees are bounded to absolute 1e6, squared home
distance to 4e12, and angle separations to absolute 2*pi. Counts are bounded
to 4096; null is accepted only for zero candidates. These are host API limits,
not retail gameplay constraints. Default result with valid=false has no effect.

Validation (MinGW bin on PATH):

```
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_groink_target_test.cpp pc_port/pc_p2_groink_target.cpp -o ../groink-target-test-01/test.exe
```

Executable reports p2_groink_target_test PASS. Independent source review
found no semantic mismatch within this snapshot contract. Tests exercise first-candidate
selection, species/alive filtering, translated/rotated corridors, strict
position boundaries, atomic malformed input, transition precedence, query
side-effect gating, and inclusive angle/exclusive radius boundaries.

Next runtime slice should replace the stationary fixture's forced re-entry
with live host candidate snapshots and these decisions, preserving the
shell/FSM/gun/animation phase order established in P2_GROINK_ATTACK.md.
Exiting to a returned movement state is not executing that movement state.
Natural pursuit, receiver damage, animated muzzle alignment, death/corpse/
revival and full scene teardown remain open. Groink is not yet a playable
completed enemy and retains priority in the AFK hard queue.
