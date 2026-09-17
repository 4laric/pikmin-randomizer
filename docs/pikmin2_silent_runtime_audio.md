# Silent unattended runtime audio policy (tooling, issue #116)

Implementation owner: Codex through shared account `4laric`. Tooling-only
slice: policy module + log checker + focused tests. No native build, no
runtime run, no shared edits, no ADMIT. All six arena gates UNTESTED.

## Problem (#116)

Automated P2 preview fixtures emitted a loud continuous dial tone from the
native process. Closing the fixture process stopped the sound, which proves
which process was audible - not what the fault is. The fanout fixture baseline
requires silent audio for unattended runs, so every automated runtime lane
needs a way to launch silently AND to prove from the log that no device audio
happened.

## Policy (what this slice delivers)

`experimental/pikmin2_silent_runtime_audio.py` (schema 1, policy version 1):

- `silent_run_environ(base)` computes the launch environment with
  `SDL_AUDIODRIVER=dummy` enforced - the same convention all
  `scripts/test_*_native.py` launchers already use, alongside
  `PIKMIN_RANDOMIZER_TEST_BACKGROUND=1`. Never mutates the input; non-mapping
  input fails closed.
- `validate_silent_environ(env)` accepts exactly `dummy`, nothing else.
- `classify_run_log(text)` verdicts, fail-closed:
  - `audio-device-open`: any WASAPI/DirectSound/SDL_OpenAudio/device-open or
    dial-tone marker present (wins over silence markers).
  - `silent-verified`: a silent-launch ack marker AND a run-end marker present
    with no device-open marker.
  - `unknown`: everything else, including logs with no ack/end evidence.
- `describe()` exposes the policy summary for packets.

## Fixture-vs-normal-preview distinction

- Fixture (automated, unattended): launch ONLY through the silent environment
  above and record the verdict per run. `silent-verified` means "this log
  shows no audio-device activity".
- Normal preview (human playtest): unchanged game audio and system volume;
  this policy must never be applied there.

## Native root-cause separation (NOT fixed here)

Muting - even via the dummy driver - is a capture workaround. The sustained
dial-tone root cause stays tracked in #116. If a native hook is required, the
exact request is: instrument the native audio init/shutdown path to log the
opened device name (or dummy selection) at startup plus underflow/xrun counts
at shutdown, so future logs carry first-party evidence. Record that request
and stop; do not implement native changes in this slice.

## Capture requirements for downstream consumers (#632 fixtures, runtime lanes)

1. Launch with the validated silent environment; log the effective
   `SDL_AUDIODRIVER` value at startup.
2. Emit a run-end line on every exit path (including failures).
3. Store the full log; classify with `classify_run_log`; treat `unknown` as
   "not proven silent" and re-run with better capture, never as a pass.
4. Never claim the #116 fault fixed from a `silent-verified` verdict.

## Captain safety #632

Not applicable: tooling-only slice, no runtime run conducted, launched, or
proposed. Any future runtime work adopting this policy must still adopt
`scripts/p2_fixture_captain_guard.h` (orimaDead/NaviDead/HP<=1 checks,
CAPTAIN_DOWN + BLOCKED exit, parked captain, labelled protection, no blanket
invincibility) and record guard/source hashes.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_silent_runtime_audio.py -q` (also
runnable via unittest): env computation, exact-dummy validation, all three
verdicts, device-open precedence, malformed-input fail-closed. No audio
device or game code is touched.
