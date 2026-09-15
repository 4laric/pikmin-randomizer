# Groink host registration guard (#210)

Codex hard lane, base 8324a5a0. This is host safety infrastructure, not a
translation of a retail manager or evidence that revival works in game.
The source pellet-kill callback releases its owning enemy before birth;
see P2_GROINK_CARCASS.md. Pointer equality cannot establish continuity.

One persistent P2GroinkLifetime belongs to one host registration slot.
Handles combine an opaque address with a monotonically increasing generation.
Every lookup, delayed hit, target registration and cleanup callback must
validate its handle against the same guard before touching the actor.
Handles are scoped to that guard, not interchangeable across guards. The
class is noncopyable and does not dereference addresses or synchronize threads.

Revival bridge ordering:

1. Capture required birth metadata while the old handle is valid.
2. beginRevival revokes that handle and returns a single-use ticket. Remove
   external registrations and detach references before invoking pellet kill.
   The guard only rejects callbacks; it does not remove external containers.
3. Kill pellet, request birth, initialize the resulting actor and establish
   the intended state using verified source/host lifetime rules. Never use
   the revoked old handle to access a potentially recycled object.
4. finishRevival(ticket, address) publishes a new generation only after
   initialization. Null consumes failed allocation. A wrong/stale ticket
   cannot change a newer registration. Same-address replacement is supported.
5. On scene reset, reset the guard before teardown; it clears registration
   and pending ticket but preserves the serial counter. Keep the guard alive
   across resets. If destroying/recreating it, externally invalidate every
   associated handle; serial uniqueness does not span separate instances.

Attach refuses a live registration or pending birth. Detach accepts only the
current generation. Serial exhaustion fails closed; a failed begin invalidates
the old registration and issues no ticket. None of these operations kills an
actor, frees memory, retires a projectile or restores a corpse.

Validation with MinGW bin on PATH:

```
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_groink_lifetime_test.cpp -o ../groink-lifetime-test-01/test.exe
```

Executable reports p2_groink_lifetime_test PASS. Synthetic tests cover null
attach, occupied/pending refusal, invalidation before birth completion,
same-address generation change, wrong/replayed tickets, stale detach,
allocation failure and reset during birth. Live callback integration and
full corpse/revival/scene lifecycle acceptance remain open. Shared hooks,
build and publication remain with the integration lead.
