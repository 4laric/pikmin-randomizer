# Groink attack-controller slice (#204)

Base: delivered volley-runtime `71721c42`. No shared native hooks, animation
player, renderer or actor registry changes. The new attack and gun rotation
policies compile independently with the existing aim policy.

Source: projectPiki/pikmin2 revision
`632af93787b9c95b63f0c13be32b161375ce3a96`;
`MiniHoudaiState.cpp:267-380`, `MiniHoudaiShotGun.cpp:1286-1303,1732-1743,1976-1993`.
`enemyBase.cpp:2380,3191` confirms finishMotion immediately sets the animator
flag queried by isFinishMotion, including before the same update's fire event.

`P2GroinkAttack::begin` resets the attack wait timer. Host initialization still
owns next-state/health-gauge resets, target velocity, excitement and starting
the source attack clip. Each authoritative source tick supplies current motion,
gun and health/flick observations and at most one animation-event edge:

| Local event | Source event | Commands |
| --- | --- | --- |
| Charge | KEYEVENT_2 | Stop motion, start aim, start charge |
| Smoke | KEYEVENT_3 | Large smoke, finish charge |
| Fire | KEYEVENT_4 | Emit volley under exact source OR guard |
| Return | KEYEVENT_5 | Stop motion, start gun return |
| End | KEYEVENT_END | Dead, Flick or host next-state resolution |

Commands are an ordered list: the host must preserve resume/refresh/finish/event
ordering, including when an interruption and animation edge share a tick. A
living actor requesting finish because of flick still emits at Fire; a dead
actor is suppressed. END gives death priority over flick. Active pause returns
no commands and preserves the timer; invalid active inputs reject immutably.
The host must not consume animation edges while paused or resend held events.
END deactivates this policy until the host enters Attack again.

`P2GroinkGunRotation` owns start/finish/lock flags, angle and speed. Start clears
angle/speed/lock; finish clears lock while retaining active rotation. Aim lock
latches until start/finish. Return uses the source wrapped-zero target and
0.025-radian step, checking the resulting error strictly below 0.01. Completion
clears rotation and sets lock. Call its update at the source manager boundary,
not from drawing. The host must still establish full actor/animation update
ordering before claiming cycle timing parity.

Validation: MinGW C++17 with `-Wall -Wextra -Werror`,
`tools/p2_groink_attack_test.cpp` plus `pc_p2_groink_attack.cpp` and
`pc_p2_groink.cpp`; executable reports `p2_groink_attack_test PASS`.
Tests cover exact command order, zero-wait pause, aim/return resume, living
finish/fire versus dead suppression, death/flick END precedence, pause/reset,
invalid input immutability, lock latching, return wrap and post-step thresholds.
Independent source review found no mismatch within this declared scope.

This is executable source-policy evidence, not animation playback or natural
combat. Next step is a source-event driver using the extracted attack clip,
with pause-aware frame advancement, wired to these commands and the tested
volley pool in an isolated runtime fixture. Confirm original update order,
event delivery and interruption timing before wiring it. Do not substitute a
fixed injected fire tick for that acceptance. World-dependent END transitions,
target ownership, damage receivers, death/corpse/revival, material fidelity and
full scene lifecycle remain open. Groink remains first in the AFK queue.

## Source-event runtime successor (3726aced)

The nonloop attack cursor uses the extracted retail attack1.bca contract:
44 frames; event pairs (11,2), (22,3), (25,4), (32,5). The clip SHA256 is
98fab1f17599653447a783377b7ea03b89b907a1cf481d147793c06f6c8015c8.
It preserves the source strict key-frame comparison, last-event latch and
one-shot END. Paused animation advances by zero. Event-cursor and composed
cycle tests pass, including previous-tick event consumption.

Normal living enemy-manager ordering was checked against enemyMgrBase.cpp,
enemyBase.cpp and MiniHoudai.cpp: existing shells update, FSM consumes the
previous animation latch, gun rotation updates, then animation produces the
next latch. This establishes the normal fixture path, not every movie or
culling path.

Private fixture groink-attack-runtime-fixture-01 built successfully against
stable native 756515d5. Two fresh sessions passed on 2026-09-13:

- Floor: groink-attack-runtime-sessions/22f0b3a0133a4c68b138f5e036cf9153;
  six floor impacts, 246 map traces, two primary shells.
- Wall: groink-attack-runtime-sessions/9d69d953fd9844b9bafaadca0dfab76f;
  six wall impacts, 58 map traces, two primary shells.

Both fired three shells at ticks 41 and 150, each at cursor frame 26, and
completed cycles at ticks 110 and 219. Both logged
P2_GROINK_ATTACK_CYCLES_PASS cycles=2 fire_frame=26 previous_tick_latch=1.
The generic volley runner verified collision receipts and reset; these extra
attack markers were checked separately in stdout.log. Each verification.json
records executable, source-build provenance, asset and capture hashes.

Reproduce using tools/p2_groink_volley_run.py with the attack fixture and the
existing floor/wall stages described in P2_GROINK_VOLLEY.md. This replaces
injected fire ticks with the cursor/controller handshake. The stationary host
explicitly re-enters Attack after END; world-dependent target transitions are
still pending. Rendering remains a baked frame-25 model with debug shells:
this does not establish animated muzzle alignment, material fidelity, six
visually distinct shells, damage, corpse/revival or full scene lifecycle.
