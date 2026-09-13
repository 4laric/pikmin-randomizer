# P2 integration pass — 2026-09-13

Owner: Codex through shared account 4laric, issue #382. Integration base:
`04e20a6a6fddf289bcfccc9f03601565a996edac` on `codex/pikmin2-room-preview`.

## Included

| Candidate | Integrated result |
| --- | --- |
| `a7c9ad7` → `4cdd044` | Eight enemy source/import lanes: aquatic, cannon/projectiles, Dweevils, flora, flying, ground invertebrates, Snagrets, Waterwraith. These are source contracts and asset tools, not new playable actors. |
| `1c73754` → `16fe7ca` | Aquatic, flying and Snagret private installers/arenas. Native registration remains family-owned. |
| `00086be` → `fcef322` | Deterministic written manifests for six lanes. |
| `db1750c` → `5532cd2` | Bulblax, cannon and Waterwraith manifest determinism. BigTreasure hunk excluded: that importer is absent from this maintained tree. |
| `402a3f4` → `8bea98e` | Family-owned registration documentation; retained the current shared import pipeline, which already states this policy and includes newer engine links. |
| `6aa102e` → `ec8dc1d` | Opt-in Bulblax material diagnosis/profile and tests. New output files only; original banks preserved. UV1, multi-stage TEV, lighting and BTK limitations remain explicit. |
| Cave PRs #326, #328, #331, #332, #335, #336, #339, #341, #345, #355, #359, #360, #362, #368, #377 | Merged frozen source-plan and native-runtime stacks through two-treasure floor-3 hauling. |
| #383 | Frozen cave handoff and remaining acceptance guide. |

The cave merge preserves floor-4 token-bound diagnostic entry and floor-5
unbound engineering surveys. Their shared runner conflicted; the resolution
retains both paths and rejects token-bound floor-5 entry. A regression exercises
the runner with synthetic process output, including wrong-profile rejection.
It is not additional gameplay evidence.

## Shared native review

Native integration commit: `7ca476d2`, based on shared engine `182f64e5`.
All twelve changed native exports are applied to the private engine worktree.
Current shared animation, weighted skinning and joint-correction work is retained.

- Cargo ground selection is restricted to imported, grounded, lifted, fully
  crewed cargo on static map geometry without a platform. It selects an existing
  upward-facing triangle below the cargo body ceiling; height and triangle come
  from the same face. Existing wall collision remains unchanged.
- Cave floor-3 failure commits use existing token/revision guards and explicit
  diagnostic readiness. Cargo terminal handling remains opt-in and pre-receipt.
  Floor-4 diagnostic entry does not enable terminal persistence or floor-5 descent.
- Host receipt handling keeps the worker's actual-event and replay boundaries.
  Full campaign/world restoration is not implied by economy restart acceptance.

The four production physics exports match the #365 evidence SHA-256 values
exactly. Its C++ test has identical Git content; working-file hash differs only
with LF/CRLF checkout conversion. The failed #362 replay is retained as history.

## Combined validation

- Full Python suite with the matching private native checkout: **1,344 passed,
  23 skipped, 658 subtests passed**. Initial run without that checkout stopped
  at four missing-native/toolchain failures after 1,025 passes; the complete
  configured run above passed.
- Subsequent material and merged-runner tests: **15 passed, 15 subtests passed**.
- Compiled floor-3 failure, cave readiness, cave entry and cargo-ground tests:
  all four passed, including the 64-case cargo gate matrix.
- Production `pikmin_pc` build: **210/210 steps passed**.
- Executable SHA-256:
  `fce467aff780479bfe022dfed55e5c477c99882a7317e0d42c6c09cbe0541fbb`.

Local combined logs: `output/integration382-tests-native.log` in the private
root worktree and `output/integration382-build.log` in its native worktree.
Worker gameplay evidence is reused, not relabeled as a new combined playtest:
`output/p2-beasts-donut-fix/output/donut365/verification.json` and
`output/p2-beasts-both-haul/output/both371/verification.json` under the main
workspace. These cover actual green/donut hauling, exact receipts and the
150-to-380 partial economy restart on their frozen executable.

## Still queued

- `kimi/p2-bulblax-234` Queen/King actor candidates (`f2dcc40`, `8eb2439`,
  `b7d9882`, `abbb95a`): native patch-series adoption remains a separate review
  under #256/#289. The existing bank/install changes already match the maintained
  files. This pass adds the material tool, not those actor implementations.
  King evidence explicitly leaves natural death/WarCry untested and uses fixture
  interventions; it must not be reported as complete source parity.
- BigTreasure import/manifest work is not included merely because a determinism
  commit references it.
- Unsubmitted/live private native work is not copied from other tasks.
- Cave campaign transitions, full world restoration, donor-physics fidelity and
  remaining gameplay acceptance are detailed in `PIKMIN2_CAVE_LANE_HANDOFF.md`.

Player executables, generated seeds and saved sessions are unchanged by this pass.
