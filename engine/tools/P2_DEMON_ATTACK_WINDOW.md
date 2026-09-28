# Demon attack decision policy (#232)

Source: projectPiki/pikmin2 revision 632af93787b9c95b63f0c13be32b161375ce3a96,
src/plugProjectNishimuraU/SaraiState.cpp StateAttack::init/exec/cleanup.
Demon inherits this FSM. This is only the capture-window and event decision slice.

Reset the window on attack entry. Each authoritative attack update first calls
step with the current source animation frame, target presence, and floor contact.
Capture attempts occur strictly after16 through30 inclusive. Floor contact latches
only in the (10,30] segment and prevents later attempts until reset, matching the
source generalTimer=30 guard. Source does not increment that timer in Attack.

Apply the returned capture attempt using the receiver, then query actual occupied
mouth slots. Pass this refreshed count to eventDecision. Do not use the number of
stimulation attempts as occupancy. KEYEVENT2 maps Dash,3 Interruptible,4 CaptureCheck,
END End; map explicitly, these enum ordinals are not source numeric IDs.
Honor mIsPlaying and authoritative event delivery; this helper does not deduplicate
repeated host calls. The two methods preserve source ordering: missing-target Move
transition occurs before events; refresh target/animation after its cleanup before
calling eventDecision, and apply any second transition in order.

Untranslated: height/turn/descent motion, event2 velocity, emotion/event flags,
full FSM, mouth update ordering, captain lifecycle, and live attack integration.
Dash is a request for the host's source velocity calculation, not implemented motion.
Header tests cover exact frame boundaries, persistent floor latch/reset, rejected
capture occupancy, event gating and invalid inputs. This establishes policy only.

Validation command (MinGW bin on PATH):
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_demon_attack_window_test.cpp -o ../demon-attack-window-test.exe
