# Challenge-mode registration landing (#676)

Recovery prerequisite for the stranded producer #656. Implementation owner:
Codex through shared GitHub account 4laric; contributor Muse Spark 1.3 via
OpenCode. Private root `.../p1-challenge/prepared/hostmode-landing-root`
(ecf5f53a); private native `.../hostmode-landing-native` on
`codex/hostmode-landing` at the canonical native head `a95040b6`. No
maintained/shared native edit or claim; no ADMIT. All six runtime gates
UNTESTED.

## Applied registration (private only)

- #661 patch `registration.patch` sha256
  `3c2cf41c4ce9183aadc8b7740e77642c323a745342c43a2ae30878ffc1f8989c`
  applied cleanly on the canonical anchor (`git apply --check` -> 0).
- **Correction applied:** the #661 patch's raw block used the hardcoded
  `${CMAKE_SOURCE_DIR}/../scripts` include. The pinned #651/#186 review
  (review sha `fc3901ad...`) required an explicit, validated cache PATH with
  no vendoring, so the private landing upgrades that block to
  `P2_CHALLENGE_GUARD_INCLUDE_DIR` (default root-relative `scripts/`;
  `FATAL_ERROR` if the guard header is missing). This is a deliberate,
  documented supersession of that one packet line, not a byte-identical land.
- Resulting private native commits: `a81eb0d0` (fixture + packet block) then
  `6156a8d0` (reviewed cache-var block). Post-apply `CMakeLists.txt` sha256
  `2f0a67f73479b3541332285aeaef84df0380448bfc55d45cb73939a82193315f`.

## Verified facts

- Target `p2_challenge_mode_fixture` links BOTH the module TU
  `pc_port/pc_p2_challenge_mode.cpp` and the #651 fixture
  `tools/p2_challenge_mode_fixture.cpp`; CTest entry present.
- Fail-closed validator `scripts/validate_p2_challenge_mode_registration.py`
  passes against the real private tree (patch hash, target membership,
  guard-include contract, no vendored guard, CTest entry).
- Focused tests `tests/test_p2_challenge_mode_registration_build.py`: 10/10.
- Leased private build (canonical lease CLI, exclusive private dir
  `.../prepared/hostmode-landing-build`): configure + target build exit 0;
  `ninja: no work to do.` on the dry run; executable
  `p2_challenge_mode_fixture.exe` sha256
  `4a449158bda72bb9dc86da857edd52ab3910c956207ad875c6ccae4c7c8f45c8`.
- #632 guarded path exercised: normal run exit 0 (host-state chain,
  `--ui-index 3`); `--captain-down` exits **86** with
  `P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED` before any observed tick.
  Guard source `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`.
  The guard include resolved via a **private junction**
  `.../prepared/scripts` -> canonical `scripts/` (a link, never a vendored
  copy), because the default root-relative path was the intended read-only
  parent include.

## Owner-review contract for maintained `native/CMakeLists.txt`

The maintained file already has a live `handoff_ready` owner
(`mar-native-registration-668`, #668) with pending shared reviews. Any
maintained CMake edit is that owner's plus **#186**'s decision. Required
decision: land the `p2_challenge_mode_fixture` target block (cache-var guard
include + `add_executable`/`add_test`) after #668's block. File identities:
maintained pre-edit anchor sha (canonical native head) and the private
post-edit sha are recorded above; this lane does NOT edit or claim it.

## Downstream

#656 (stranded producer) -> #651 (host-mode consumer) -> P1 stage lanes
#563-#567 (recovery request `ee616d33`). Integrator retains final
merge/export authority.