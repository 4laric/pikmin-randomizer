# Demon cross-policy scenarios (#237 follow-on)

The executable combines the real target/capture, attack-event, escape-window and
forced-drop policy headers with an explicitly simulated receiver. It tests the
host ordering that standalone boundary tests cannot demonstrate:

- An attempted but rejected grab leads to Fail/Move, not CatchFly.
- Accepted occupancy prevents a second grab and controls the attack END choice.
- Receiver detachment removes occupancy before subsequent event decisions.
- Forced drop delays positive damage until knockdown END; a duplicate delivers none.
- Six deterministic input edges escape, clear occupancy, and never arm forced-drop damage.
- Cancellation followed by a new generation rejects an old knockdown event.

Build with MinGW bin on PATH:
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_demon_policy_scenario_test.cpp -o ../demon-policy-scenario-test.exe

This does not run Navi, real InteractSarai, any native captain hooks, animation
callbacks, terrain or health code. The receiver acceptance and endStick effect
are simulated. A PASS is policy ordering evidence only; actual receiver ownership,
control/physics consistency and lifecycle acceptance remain root integration gates.

Delivery chain: this successor preserves forced-drop policy 1ef8cea4, corrected
contract aa3efa50, attack policy b51255bc and escape bridge 02973d4c. Root should
review the new scenario together with those existing handoffs; do not interpret
its simulated receiver as a replacement for the native bridge fixture.
