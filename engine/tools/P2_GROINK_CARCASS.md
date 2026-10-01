# Groink carcass recovery policy (#209)

Codex hard lane, base 6202d852. Source MiniHoudai.cpp:282-325 at revision
632af93787b9c95b63f0c13be32b161375ce3a96. Pure timer/command policy only:
no pellet destruction, birth allocation or live revival is performed.

become() mirrors the carcass hook: timer and health start at zero. With a live
pellet, the timer first crosses the supplied gauge delay, optionally emitting
ActivateGauge. Because the source uses else-if, health recovery starts only
on a later update. It increases by maxHealth/recoverySeconds * delta and is
not clamped. Crossing max emits KillPellet followed by RequestBirth once;
the policy does not invent a retry if the host birth fails.

If the pellet is dead, timer and health reset only when the gauge manager
exists AND the delay threshold was reached. Without a gauge manager, the
source leaves them unchanged. Zero gauge delay is valid; it does not produce
an initial ActivateGauge event. Zero max health produces no recovery request.
Pause preserves state and emits nothing; reset invalidates the policy.

Host ordering and unresolved lifecycle:

1. Call only for an existing carcass/pellet relationship; the source caller
   checks pellet presence before doUpdateCarcass. Never retain a stale pointer.
2. Apply KillPellet first. Preserve required old-object birth metadata across
   that call: position, face angle from base-matrix zx/zz, existence duration,
   enemy type and Piklopedia flag.
3. Pellet::onKill (pelletMgr.cpp:786-789) calls viewOnPelletKilled, clears the
   owner's pellet link, and detaches the view. EnemyBase::viewOnPelletKilled
   (enemyBase.cpp:2983-3008) ends with mMgr->kill(this). Thus the owner is
   released to its manager before the birth request; it is incorrect to
   assume pellet kill leaves a separately active old owner behind.
   Request the manager birth. On success the source calls returnedGroink->init,
   then mFsm->transit(this, Rebirth) on the caller. It is not yet established
   whether returnedGroink necessarily aliases this after pellet cleanup.
   Neither distinct-object replacement nor same-object revival is assumed by
   this timer module. Verify allocation/lifetime before binding these calls.
4. Birth failure leaves the pellet already killed and the owner released.
   Stop scheduling through a cleared pellet link; do not synthesize success
   or assume a later carcass tick occurs. The dead-pellet branch is a separately
   supplied source condition, not proof of failed-birth lifecycle recovery.

Rebirth animation/receivers are not included. Source event 2 flicks attached
and nearby Pikmin/Navis, resets flick timer and enables NoInterrupt; event 3
disables it and emits a down effect; cleanup also disables it. END ordering
differs from Attack: death, flick, attackable target, searched target, path.
It does not include Attack's territory/home-radius branch. Do not reuse the
Attack END policy unchanged.

Validation (MinGW bin on PATH):

```
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_groink_carcass_test.cpp pc_port/pc_p2_groink_carcass.cpp -o ../groink-carcass-test-01/test.exe
```

Executable reports p2_groink_carcass_test PASS. Independent review found no
timer-policy mismatch. Root corrected an incomplete identity audit by tracing
the pellet-view callback through owner-manager release. Coverage includes exact delay
crossing, later recovery, overshoot, ordered kill/birth, no invented retry,
manager-null behavior, dead pellet before/after delay, zero delay/max health,
pause and invalid-input immutability. The no-retry probe deliberately continues
with a synthetic live-pellet snapshot after the request; it does not model
real post-kill scheduling. Config values are finite nonnegative
and at most 1e6, recoverySeconds strictly positive with a finite rate; active
delta is finite in [0,0.25]. These are adapter limits; retail parameters must
come from the validated profile, not these test values.

No shared hooks/build/export changed. Carry/delivery, pellet ownership,
birth identity, corpse visuals, revival effects/receivers and full scene
cleanup remain runtime gates. Groink stays unfinished and first in the queue.
