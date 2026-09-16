# Muse Armor15 natural death/transport/re-entry observer - handoff (#165)

Lane `armor15-death-transport-reentry-observer`, issue #165, generation 3.
Implementation owner: Codex through shared account `4laric`; executing Muse
Spark 1.3 Contributor. Outcome: **BLOCKED on an exact tooling dependency**;
gates 4/5/6 are NOT claimed. No ADMIT, no ledger writes.

## What was built (all four reserved files, new)

- `native/tools/p2_muse_armor_fixture.cpp` - additive Armor observer App.
  Natural-kill design: real `Attack` orders on a tight inward-facing clump, a
  read-only per-tick health-decrease probe, corpse detection from the engine
  `Pellet`, ordinary FreeMode carry, a FreeMode carrier count probe, then
  `pc_p2_armor_forget` + `pc_p2_armor_reset` + `mGenType->init` + `setup`
  with stale/fresh pointer proof. The App contains **no health write and no
  TransportMode write**; the test suite grep-asserts this.
- `experimental/pikmin2_muse_armor.py` - observer: lane-14 ground prepare with
  Sokkuri parked, local Pod staging (the pinned base predates the shared
  Pod-staging helper, so the same record/clone logic is implemented locally
  with base-available helpers only), private-fixture build splice, run, and a
  dependency-free `validate()` reader that rejects any injected-health run.
- `tests/test_pikmin2_muse_armor.py` - 11 tests + 7 subtests, all passing
  (valid log, prefixed receipt, injected-run rejection both markers,
  written-to-zero rejection, missing receipt, zero transport, missing
  re-entry, failure exit code, dependency-free check, fixture no-write grep).
- this document.

Root commit: see `contributor` section below. Native commit: fixture only.

## Exact blocker (dependency, not scope)

The lane's pinned root base `533e7f4a` ships an older
`scripts/build_pikmin2_fixture.py` that cannot parse the `pikmin_pc` link
command on this host's toolchain:

- Pinned CMake/toolchain emits the executable link as
  `g++.exe -O3 ... -mconsole @CMakeFiles\pikmin_pc.rsp -o bin\nectar.exe ...`
  (confirmed via `ninja -t commands pikmin_pc` in the private build dir; the
  same rule exists in the newer `native-l62` build, so it is not a local
  misconfiguration).
- The pinned base's builder reaches `select_commands()` ->
  `compiler_args()` -> `windows_args()`, which raises
  `BuildRejected('Empty command or unsupported response file')` on the `@`
  token (base file lines ~86, ~116, ~338).
- The newer integration line already fixes this:
  `scripts/build_pikmin2_fixture.py` `expand_response_line()` (line 111) /
  `expand_response_files()` (line 128), applied at line 421 before
  `select_commands`. That function is absent at the pinned base.

**Required dependency:** bump this lane's root pin to an integration-approved
revision whose `scripts/build_pikmin2_fixture.py` includes the response-file
expansion (l62-era or newer), or have the runtime-fixtures provider shard
backport `expand_response_line`/`expand_response_files` into the pinned base.
This is a shared provider/tooling change and is explicitly out of this lane's
owned files.

Workarounds attempted and rejected: `CMAKE_NINJA_FORCE_RESPONSE_FILE=OFF` and
`CMAKE_*_USE_RESPONSE_FILE_FOR_{OBJECTS,LIBRARIES,INCLUDES}=OFF` (still emit
the link rsp); a shorter private build path (reduced rsp count from 617 to 2
but the link rsp remains); manual reconfigure (no supported switch removes the
Windows link response file).

## Six-gate status (honest; no upgrade)

| Gate | Status | Evidence |
|---|---|---|
| 1. identity_spawn | PASS (natural, preserved) | lane-14 evidence; not re-run or relabelled here |
| 2. movement_animation | PASS (natural, preserved) | lane-14 evidence; not re-run or relabelled here |
| 3. attacks_receivers | PASS (natural, preserved) | lane-14 evidence; not re-run or relabelled here |
| 4. death_corpse | BLOCKED | fixture/observer ready; native fixture build blocked by the response-file tooling gap above |
| 5. transport_reward | BLOCKED | same dependency; Pod + corpse-credit path staged and ready |
| 6. cleanup_reentry | BLOCKED | same dependency; forget/reset/rebirth assertions ready |

## Acceptance status

- Natural death/corpse on a live bound actor: NOT observed (no run).
- Corpse carry through Pod credit on the same generator: NOT observed.
- Re-entry rebirth + re-bind stale=0/fresh=1: NOT observed.
- Focused tests: PASS (11 + 7 subtests).
- Checker EXIT=0: N/A (no run to check); no ADMIT, no ledger writes.

## Next bounded step (for the integrator)

1. Re-pin the lane root to a revision with `expand_response_files`, or backport
   it via the runtime-fixtures provider.
2. Re-run: leased `--configure` build, fixture build, `run()` against a fresh
   arena; then the reader yields gates 4/5/6 or an exact in-engine defect.
