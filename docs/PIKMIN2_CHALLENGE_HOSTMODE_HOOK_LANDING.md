# Challenge host-mode hook landing (lane challenge-hostmode-hook-landing, #714)

Bounded landing submitting the missing handoff for the done-but-unlanded #710
engine hook. Root-only tooling: the #710 hook is consumed read-only (no
re-derivation, no duplication of its nine files); no family/shared/native
edits, no runtime, no ADMIT. All six gates UNTESTED.

## Re-verified #710 pins (hash-identical to the #710 review)

- Root commit `3e3cdd1d93a3b0196cdd19202ab9eb922a80e9d8` (base `ecf5f53a`),
  4 files: doc, verifier, build helper, tests.
- Native commit `db245877a090d017a09e28ac1c144e6497857227` (base `78b67349`),
  5 files: runtime header/source, `pc_bbft.cpp` hook, `CMakeLists.txt`,
  guarded fixture.
- All eight `out/` evidence files re-hashed byte-identical to the #710 handoff
  record (pytest, verify, fixture-compile, default-config build log, both build
  records, headed run, guard header `d2f678c9...`); doc hash `b0815c8c...` matches.

## Validation against integrated #701/#702

- #701 integrated: root `806952db`, native `f91c2143` (handoff reviewable,
  slice passed; content markers verified).
- #702 integrated: root `75dddcd2`, native `78b67349` (gen-3 reconciliation;
  both marker families observed; validation `7bf92818...`).
- The #710 native commit descends from the integrated #702 native line
  (`78b67349` is its base), and the runtime header binds the landed
  `StageEntry`/`HostState` API (`caveId`/`uiIndex`) driving
  `p2challenge::wiring::syncTick`; `CMakeLists.txt` adds both modules to
  `pikmin_pc`; `pc_bbft.cpp` carries the null-by-default bridge glue.
- #186 scope (review pending): the shared per-tick hook and the CMake
  first-class target. No #186 decision is claimed here.

## Module, tests, packet

- `experimental/pikmin2_challenge_hostmode_hook_landing.py`: machine-readable
  registry builder + fail-closed validator (`--check`, `--registry-out`,
  `--packet-out`) with every pin, blob hash, evidence hash, integration pin,
  #186 item, and the downstream consumer recorded.
- `tests/test_pikmin2_challenge_hostmode_hook_landing.py`: 24 focused tests
  (pins, nine-file integrity, evidence completeness, #186 pending, downstream
  #550, UNTESTED gates, packet contents, refusal battery).
- The emitted packet is integration-ready for the single-writer integrator +
  #186 reviewer and names downstream consumer
  `p2-challenge-ch-abem-leafchappy-p1` (#550), whose zero-marker evidence is
  cited read-only.

## Handoff

`output/workflow/autofill/prerequisites/challenge-hostmode-hook-landing/out/handoff.json`
(kind=tooling) names the exact #710 commits/hashes and the emitted packet; the
packet hash is recorded in the handoff evidence. Downstream: #550 markers
observed once integrated, then the remaining gates.

## Captain safety #632

N/A (no runtime run). Any future runtime work must adopt
`scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`) with
orimaDead/NaviDead/HP<=1 checks, CAPTAIN_DOWN + BLOCKED exit, and a parked
captain; guard/source hashes recorded at adoption.
