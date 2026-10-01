# Demon source attachment pose (#224)

Codex hard lane successor to e685aa8a. Source revision
632af93787b9c95b63f0c13be32b161375ce3a96.

MouthCollPart::getPosition returns the joint world matrix translation;
copyMatrixTo copies that full matrix (collinfo.cpp:1641-1653). MouthSlots
setup supplies a zero offset, and Demon is not the OniKurage special path.
Creature::updateStick (creatureStick.cpp:213-259) zeros velocity, concatenates
the mouth world matrix with local Rz(pi/2), writes the captive base transform,
then sets position from its translation. Thus the captain center belongs at
the extracted joint center, even when it appears below the visible hand.
Do not add an eyeballed hand correction.

The helper implements that affine product exactly for a mathematical quarter
turn, preserving source scale/shear and translation. It does not approximate
the original trig implementation's tiny floating-point residuals. Input is a
full WORLD mouth matrix, after owner transform, not the extracted local one.
Finite components bounded to absolute1e6 are a host API restriction. The
returned position is redundant so host position/base-matrix writes agree.

Host obligations remain: verify accepted ownership, zero velocity, apply
the full matrix and position in the correct update phase, and release both
captain and mouth linkage on exit/death/reset. This helper neither attaches
nor releases anything. P1 captain draw/state code must be checked before
writing its transform; simple resetPosition is not equivalent to updateStick.

Validation: MinGW C++17 -Wall -Wextra -Werror -Ipc_port,
tools/p2_demon_attachment_test.cpp reports PASS. Tests cover identity-world
quarter turn, translated/rotated nonuniform scale and nonfinite rejection.
Earlier visual captures222 establish visible centers and changing poses,
not captain orientation/contact. Exact model/joint fidelity remains open.
Next isolated runtime should draw a captain at this full source pose, then
implement actual receiver/state ownership with release and escape behavior.
