# Demon forced-drop lifecycle policy (#237)

Successor of #236 source contract. pc_p2_demon_drop_policy.h expresses commands
for the source FallMeck -> KokeDamage path without calling a captain or writing HP.
Source revision and exact receiver details remain in P2_DEMON_FORCED_DROP.md.

Host contract:
- Allocate a strictly increasing, nonzero drop generation for each begin. Keep
  the policy alive across drops; cancel retains its generation. If reconstructing
  the policy, invalidate the entire callback domain first. IDs never wrap/reuse.
- begin must follow successful ownership/admission validation. Apply FALL and
  detach, set actual Y to the returned -400/-100 while preserving actual X/Z,
  then set full target velocity to (0,targetY,0). Do not use a P1 virtual setter
  without verifying its semantics. These commands describe final P2 values.
- bounce is a first valid terrain impact. Positive damage requests addDamage(0,
  true) and JKOKE; it does not request positive HP loss. Water/smoke/rumble and
  actual state transitions remain the host's responsibility.
- Feed animationEnd with the generation and the animation phase that EMITTED
  the event, not whatever phase the policy currently has. Only JKOKE END emits
  stored damage (source playSound=false). Use the normal damage receiver, not
  direct health subtraction. State advances before returning the command.
- Tick Lay once per simulation update after source exec ordering; paused calls
  must be omitted or use zero delta. One simulation second requests GETUP. Its
  END requests source Walk/backup-state recovery, not a hard-coded stale state.
- During nonfalling phases the source zeros actual/target velocity; the host
  must do so while retaining animation updates. Falling keeps ordinary physics.
- Cancel synchronously before death, external state/motion interruption, movie
  exits, inactive-world Koke exits, or captain/scene teardown. Cancellation emits
  no recovery command, preserving the external state. Source FALL-motion loss
  and Koke backup-state fallback require explicit host handling; they are not
  inferred by this policy. No queued damage may survive that cancellation.

Generation checks, rejection of concurrent begin, finite-value validation and
phase-qualified duplicate suppression are host safety constraints, not claims
that these fields exist in the P2 decomp. A rejected command makes no mutation.
The nonpositive-damage case immediately requests Walk/nudge on first bounce.
Effects repeated by raw source bounce calls are not modeled; the helper handles
only the first state-changing impact. Owner flick and voluntary SaraiExit escape
remain separate and must not enter this path.

Tests cover positive/zero damage, actual-versus-target velocity, deferred one-shot
damage, duplicate bounce/END, exact recovery timing, interrupted pending damage,
stale generations, concurrent admission and malformed values. Build:

g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_demon_drop_policy_test.cpp -o ../demon-drop-policy-test.exe

No live captain, native hook integration, terrain/animation fidelity or damage
receiver acceptance follows from these tests. Root retains shared integration.

Generation exhaustion intentionally fails closed; start a new callback domain rather than wrapping IDs. Independent source review found no policy blocker; additional regressions cover immediate cancellation, negative damage and large finite recovery delta.
