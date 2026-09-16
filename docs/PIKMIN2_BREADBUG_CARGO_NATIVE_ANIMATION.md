# Optional Breadbug cargo visuals

Scope #168, Codex implementation owner under shared 4laric. The existing
`P2_BREADBUG_ACTOR_PROXY_1` profile remains valid and unchanged when the optional
`p2-breadbug-cargo.txt` bank is absent. The bank adds source Back/Hide models
only; P1 AI, animation events, carry arbitration, nest destruction and corpse
behavior remain authoritative.

`experimental.pikmin2_breadbug_cargo_install.install(bank, visual_profile, run)`
requires a private existing actor session. It binds the bank and base visuals
to the same source import, reconstructs/verifies the existing actor config
and model bytes, checks all new hashes and exact clip/event/sample structure,
then refuses any existing destination before writing. Config bytes use LF.
The native parser also validates ordered sample frames, duration 49, expected
event-frame samples, file resource structure and no trailing config data.

The pure C++ helper `pc_p2_breadbug_cargo_phase.h` implements this contract:

| Native state and motion | P2 source frame |
|---|---|
| 5, Move2, cargo pointer 2 present | Native counter 0..loop-start maps to Back 0..10 |
| 6, Move2, cargo pointer 2 present | Native loop-start..loop-end maps to Back 10..39 |
| 8, Type3, cargo pointer 2 present | Native counter 0..last frame maps to Hide 0..48 |
| 9 | Suppress this optional live visual |

Values clamp at endpoints. Pani info-key types 0/1 are the actual loop bounds
(`panianimator.cpp:262` onward), not the distinct public key-event enum values
5/6. Invalid/missing bounds, absent cargo or mismatched motion fall back to
the legacy wait/move visual. Dead actors still decline the live delegate and
use their unchanged P1 corpse. State 9 handling applies only with the new bank.

The mapping is stateless and evaluated from the current native animator. A
pause/repeated draw returns exactly the same frame; native loop wraps or
state transitions immediately determine the new phase. No SDL clock, elapsed
time accumulator or gameplay event callback is used for the cargo motions.
Legacy wait/move timing is unchanged. Reset clears both banks and actor
registrations; forget removes the existing actor entry as before.

## Validation and remaining runtime gate

- The family module passed syntax-only compilation. Root owns the full build.
- `py -3.12 native/tools/test_p2_breadbug_cargo_phase.py` compiles and executes
  the actual helper, covering intro, loop, swallow clamp, pause/repeated draw,
  loop wrap, invisibility and invalid observations/bounds.
- Twelve Python tests and four subtests pass across installer, source bank,
  cargo observation parser and actor installer. Installer tests cover exact
  bytes, source mismatch, tampering before writes and refusal to overwrite.
- The actual nineteen-model source bank installed successfully into private
  `output/p2-lifecycle-batch/breadbug-cargo-install-01/6a55246a8378431480b10357cc2048ce`.
  Config SHA256:
  `437e8c6b47970207d76099f56f2fb831c486d081d5e68110d1563f3da214de37`.

Native playback has not been run in this batch. The next runtime gate repeats
the proven natural pellet interaction with this optional bank, checks Back/Hide
selection and visible alignment, exercises pause, and requires unchanged
grab/haul/release evidence. Source P2 frame events and full AI remain out of scope.
