# Six-family native integration (#387)

Codex integration owner using shared account 4laric. Candidate
`opencode/p2-integration-six` at `6e79fe6abb9fc98b1a16ce48dfd43ff02eaa0f11`,
merged onto shared P2 `4b1274421fd61a25bd491b347a3a6cb34c6b1016`.
The #385 receiver fixes are retained. This is the native snapshot submission;
separate root tooling branches are not implicitly merged with it.

## Included candidate milestones

| Lane | Frozen native candidate | Integrated scope |
| --- | --- | --- |
| Beetles #219 | `fe780120` | Bound beetle behavior, flip/drop/gas/escape hooks and scoped parameter overrides |
| Giant Breadbug #220 | `86c2a88d` | Opt-in Collec/Hollec actor/nest binding, press/contest/digestion behavior |
| Mamuta #221 | `9dd12181` | Opt-in P2 bury rules, population cap and captain damage behavior |
| Demon #242 | `418d4f26` | Dedicated registered captain drop state, named transition guards and pre-manager teardown |
| Queen #256 | `650dc165` | Opt-in sampled Empress actor and bounded larva pool |
| King #289 | `4f517e01` | Opt-in sampled Emperor actor, mouth/bomb and state behavior |

The submission also contains BigTreasure and Fuefuki policy sources/tests. They
are not registered gameplay actors by this merge. Their compiled policy tests
are included in the combined validation.

## Review changes

- Queen/King local hit and mouth arrays previously retained raw Pikmin pointers
  across death/recycling. They now revoke matching slots from `Creature::kill`
  before manager recycling. Revocation nulls slots without changing counts or
  indexes because damage callbacks may run during iteration of the same array.
  Arrays are initialized empty. The compiled regression checks removal,
  duplicate slots, stable indexes and same-address reuse.
- Mamuta rules check that the interaction owner is a Teki before downcasting.
  Unrelated bury owners continue through the original path.
- The old Mamuta visual-hook auditor rejected the new rules build entry.
  It now recognizes exactly one optional rules-module entry while preserving
  incomplete, duplicate and unknown-hook rejection. The generation path keeps
  that independent entry intact. Updated tests exercise this combination.

The additive captain state is PC-only. Reviewed its explicit admission guard,
per-motion issuance tokens, named transition velocity cleanup, and retirement
before stage managers are nulled. Unknown target-state impulse semantics and
heap-reset paths bypassing normal stage exit remain the documented #242 limits.
The receiver does not automatically enable natural Demon capture.

## Evidence and acceptance boundary

Worker evidence is reused at the frozen candidates: the six-lane table on #186
records private builds and 24 beetle, 16 Giant Breadbug, 20 Mamuta, 6 Queen and
7 King lane tests. Demon lifecycle documentation records 15 private runtime
scenarios. These are not new combined gameplay runs.

The first configured combined Python suite passed 1,356 tests and failed only
the two stale Mamuta hook audits. After the audit correction, five targeted
tests passed with seven subtests (receiver regression and five compiled family
policies included). Final full-suite and native-build results are recorded below.

The compiled Queen/King tests were copied from the frozen
`kimi/p2-bulblax-234` submission. No generated models, retail assets, binaries,
sessions or logs are committed. Local build/test evidence lives under the
private engine/root worktrees' `output/integration387-*` files.

This merge does not promote every family to complete gameplay parity. Existing
material fidelity, reload/re-entry, Mamuta death/corpse, Queen death/Baby attack,
and King WarCry/cross-Emperor acceptance gaps remain with their family issues.
Player packages and saves are unchanged.

Final combined validation: **1,359 passed, 23 skipped, 670 subtests passed**.
Production native commit `ae4747d4` built successfully. Executable SHA-256:
`fe97b85b4853a097411cf142d137a42ea04dfdb2f6f868180e7eb08880fb6bc7`.
Logs: `output/integration387-tests-final.log` (private root worktree) and
`output/integration387-build-final.log` (private native worktree).
