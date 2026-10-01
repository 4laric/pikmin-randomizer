# Muse placement handoff (#492): generated-slot contract for 41/57/58/78

Owner: Codex through shared account 4laric; contributor Muse Spark 1.3 through OpenCode.
Lane muse-placement, issue #492, parent #440, wave #491. Attempt 17314b1dcd354824bf2cd104274b3903.

## Scope delivered

Candidate-only legal-slot profiles plus the narrow generated native binding
path for Fuefuki41, Kurage57, BombSarai58 and MiniHoudai78. One defensible
generated slot per identity; fail closed on unsupported terrain/routes. No
admission allowlist or ordinary random-pool change (admitted set still
`[23, 44, 59, 60, 61, 62]`, pinned by
tests/test_pikmin2_admitted_placement.py). Family FSMs untouched.

## Source-ID / slot / generator contract (for #493 and #497-#500)

| Source ID | Identity | Accepted generated slot | Slot label / stage | Vehicle (family sidecar binds it) |
|---|---|---|---|---|
| 41 | Fuefuki | 1254096625 | hope_0-29_2866 / Hope | Napkid11 |
| 57 | Kurage | 689702860 | navel_0-29_1473 / Navel (frog cohort, mixed) | Frog0 |
| 58 | BombSarai | 1787125272 | spring_init_7416 / Spring | Napkid11 |
| 78 | MiniHoudai | 328297937 | navel_0-29_438 / Navel | GroinkHost |

All four slots are non-protected, corpse-route, renewable campaign slots.
Python contract: `randomizer/p2_placement_catalog.py` `MUSE_CANDIDATE_SPECS`,
`muse_candidate_profiles()`, `build_muse_document()`,
`binding_targets_for_muse_sources()`. The lane-04 default document is
unchanged (pinned group keys verified by tests/test_p2_placement.py).
Native contract: `native/pc_port/pc_p2_generated_placement.h`
`MUSE_GENERATED_SLOT_*` constants plus a placement registry
(is_bound/bound_count/forget/reset). The sync test fails on any drift.
Birth markers to correlate on the shared target uid (see
experimental/pikmin2_muse_placement.py `observe_cohort`):

- `P2_SEED_RESOLVE source_id=<n> target=<uid>` (existing, genteki.cpp),
- `P2_GENERATED_PLACEMENT source_id=<n> target=<uid> generator=<g> bound=1`
  (new; `bound=0 reason=slot-rejected|bad-request|registry-full` is a
  fail-closed refusal, not a bind),
- lane-04 `P2_PLACEMENT_SLOT` / `P2_PLACEMENT_PROBE` lines for the same uid.

`bound=1` means placement-accepted only; family behavior still binds through
the family sidecar path, and `pc_p2_generated_placement_bind` keeps returning
false for these ids. Do not read it as a family FSM claim.

## Changes (root worktree, branch codex/muse-l52-placement)

- `randomizer/p2_placement_catalog.py`: additive `MUSE_CANDIDATE_SPECS`,
  `MUSE_GENERATED_SLOTS`, `MUSE_CANDIDATE_IDS`, `muse_candidate_profiles()`,
  `muse_candidate_source_ids()`, `build_muse_document()`,
  `binding_targets_for_muse_sources()`. `randomizer/p2_placement.py` untouched.
- `experimental/pikmin2_muse_placement.py` (new): marker observer.
- `tests/test_pikmin2_muse_placement.py` (new): 16 tests.
- `docs/PIKMIN2_MUSE_PLACEMENT_HANDOFF.md` (this file).

## Changes (native worktree, branch codex/muse-l52-placement-native)

- `native/pc_port/pc_p2_generated_placement.h` / `.cpp`: muse candidate
  table (header-inline), 8-entry placement registry, marker emission,
  `museBind` fail-closed path. Existing 23/59-62 behavior unchanged.
- `native/tools/p2_muse_placement_fixture.cpp` (new): engine-free contract
  fixture, 16/16 PASS (compile-time slot asserts + runtime predicate checks).
  Requested shared hook for #491 (not applied, CMakeLists.txt not owned):
  `add_executable(p2_muse_placement_fixture tools/p2_muse_placement_fixture.cpp)`
  plus an `add_test` entry.

## Validation evidence

- New suite: `py -3.12 -m unittest tests.test_pikmin2_muse_placement`
  -> 16 tests OK (output/muse-wave/l52/tests-muse-placement.log).
- Regression: `test_p2_placement` + `test_p2_placement_audit` +
  `test_pikmin2_admitted_placement` + `test_p2_seed_placement` -> 49 tests OK.
- Native build (leased runner, generation 1):
  configure + `pikmin_pc -j 6` + `ninja -n` dry run exit 0;
  `ninja: no work to do.`; exe
  `output/msw/native-l52-build/bin/nectar.exe` SHA-256
  `47f59d1ff124e26f97639320accddbd8ef5f442f3df34b8ddb5272f9716ea8f8`;
  log output/muse-wave/l52/build-1789515537751320500.log SHA-256
  `ed4be64d2ff4d3a8f7e01cccd40abaae2694cb923ae65cbd88f86415da6e43c4`.
  Native base 7b9ecaa668fd55332073446cdbdaf6424b209ea7, dirty:
  `M pc_port/pc_p2_generated_placement.cpp`,
  `M pc_port/pc_p2_generated_placement.h`,
  `?? tools/p2_muse_placement_fixture.cpp`.
- Gate-table check: `py -3.12 scripts/check_p2_handoff_gates.py
  docs/PIKMIN2_MUSE_PLACEMENT_HANDOFF.md` (expect BLOCKED/UNTESTED only, no
  refused PASS).
- Fixture baseline adoption: N/A (tooling/placement slice; no runtime claim;
  native executable built but no acceptance run launched).

## Remaining work (exact)

Gate 1 natural closure needs, per identity, one generated-session run that
emits all three markers on the accepted uid with live family behavior. That
needs packaging sidecars (#493: staged banks + `p2-*-teki.txt` for the
accepted slot) and the family arena/runner, owned by observers #497-#500.
This slice delivers the contract they consume; it does not stage arenas,
launch runtime, or close any natural gate.

## Six-gate tables (this slice observes no natural gameplay)

- Source ID: 41 `Fuefuki`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | randomizer/p2_placement_catalog.py MUSE_CANDIDATE_SPECS; native marker spec native/pc_port/pc_p2_generated_placement.h; no natural generated birth yet, needs #493 sidecars + #497 arena run | natural (no run yet) |
| 2. Autonomous movement and animation | UNTESTED | owned by legacy lane 28; not re-observed by this slice | natural (no run yet) |
| 3. Attacks and receivers | UNTESTED | owned by legacy lane 28; not re-observed by this slice | natural (no run yet) |
| 4. Death and corpse | UNTESTED | owned by legacy lane 28; not re-observed by this slice | natural (no run yet) |
| 5. Actual transport and reward | UNTESTED | owned by legacy lane 28; not re-observed by this slice | natural (no run yet) |
| 6. Cleanup and re-entry | UNTESTED | owned by legacy lane 28; not re-observed by this slice | natural (no run yet) |

- Source ID: 57 `Kurage`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | randomizer/p2_placement_catalog.py MUSE_CANDIDATE_SPECS; native marker spec native/pc_port/pc_p2_generated_placement.h; no natural generated birth yet, needs #493 sidecars + #498 arena run | natural (no run yet) |
| 2. Autonomous movement and animation | UNTESTED | owned by legacy lane 29; not re-observed by this slice | natural (no run yet) |
| 3. Attacks and receivers | UNTESTED | owned by legacy lane 29; not re-observed by this slice | natural (no run yet) |
| 4. Death and corpse | UNTESTED | owned by legacy lane 29; not re-observed by this slice | natural (no run yet) |
| 5. Actual transport and reward | UNTESTED | owned by legacy lane 29; not re-observed by this slice | natural (no run yet) |
| 6. Cleanup and re-entry | UNTESTED | owned by legacy lane 29; not re-observed by this slice | natural (no run yet) |

- Source ID: 58 `BombSarai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | randomizer/p2_placement_catalog.py MUSE_CANDIDATE_SPECS; native marker spec native/pc_port/pc_p2_generated_placement.h; no natural generated birth yet, needs #493 sidecars + #499 arena run | natural (no run yet) |
| 2. Autonomous movement and animation | UNTESTED | owned by legacy lane 27; not re-observed by this slice | natural (no run yet) |
| 3. Attacks and receivers | UNTESTED | owned by legacy lane 27; not re-observed by this slice | natural (no run yet) |
| 4. Death and corpse | UNTESTED | owned by legacy lane 27; not re-observed by this slice | natural (no run yet) |
| 5. Actual transport and reward | UNTESTED | owned by legacy lane 27; not re-observed by this slice | natural (no run yet) |
| 6. Cleanup and re-entry | UNTESTED | owned by legacy lane 27; not re-observed by this slice | natural (no run yet) |

- Source ID: 78 `MiniHoudai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | BLOCKED | randomizer/p2_placement_catalog.py MUSE_CANDIDATE_SPECS; native marker spec native/pc_port/pc_p2_generated_placement.h; no natural generated birth yet, needs #493 sidecars + #500 arena run | natural (no run yet) |
| 2. Autonomous movement and animation | UNTESTED | owned by legacy lane 21; not re-observed by this slice | natural (no run yet) |
| 3. Attacks and receivers | UNTESTED | owned by legacy lane 21; not re-observed by this slice | natural (no run yet) |
| 4. Death and corpse | UNTESTED | owned by legacy lane 21; not re-observed by this slice | natural (no run yet) |
| 5. Actual transport and reward | UNTESTED | owned by legacy lane 21; not re-observed by this slice | natural (no run yet) |
| 6. Cleanup and re-entry | UNTESTED | owned by legacy lane 21; not re-observed by this slice | natural (no run yet) |
