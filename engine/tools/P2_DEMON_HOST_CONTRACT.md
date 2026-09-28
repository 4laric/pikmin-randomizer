# Demon captive host contract (#216)

Source revision632af93787b9c95b63f0c13be32b161375ce3a96. Successor to
ad077a8a, Codex hard lane. No live captain attachment or escape is claimed.

Sarai.cpp:42 initializes Demon's virtual attack timer to12800, making initial
acquisition immediately eligible. FallMeck cleanup (SaraiState.cpp:675)
resets it to0. TargetGate now accepts reset(value); host must explicitly
initialize with12800 and reset0 after this release sequence.

Exactly two mouth slots use rkamujnt and lkamujnt, radius15 each
(Sarai.cpp:153-162). Sarai doUpdate executes FSM before updating slot
transforms; do not silently move the capture query to a later pose phase.

NaviSaraiState (naviState.cpp:3902-3968) starts FALL, clears input history,
and releases Pikmin. The extracted escape helper preserves the 28-update
directional-edge window: test old bit27, decrement, shift, then insert current
edge. It counts at most one edge per update. From six inputs, animation speed
is60+60*(count/22); first random<rate squared gates a second random<0.1.
The helper accepts a callable yielding source randFloat values; host must
preserve that stream and short-circuit consumption. No clamp on rate is added.

Host still owns controller sampling, pause/scheduling, captain switch logic,
and ordered state transitions. On lost attachment the source requests Walk
but continues this exec's switching/escape/speed work; helper intentionally
does not early-return merely because attached is false. Handle that ordering
when composing the full state. Cleanup restores speed30.

SaraiExit init ends stick, starts FALL and disables atari. Ground triangle
presence or bounce returns Walk; cleanup restores atari (naviState.cpp:3974-4008).
These collision/ownership actions are not performed by the helper. Death and
scene cleanup must clear slot and captain linkage before owner reuse.

Validation: MinGW C++17 -Wall -Wextra -Werror with -Ipc_port;
tools/p2_demon_escape_test.cpp and existing p2_demon_capture_test.cpp both PASS.
Tests cover first eligibility after spawn, post-release cooldown, exact input
expiration, six-input threshold, RNG draw count, attachment gating and reset.
Independent source audit confirmed timer resets, mouth geometry and RNG order.
Next: actual model/animated joint extraction and native captain state bridge.
