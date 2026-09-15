# Consolidated P2 review against main (#430)

Implementation owner: Codex through shared account `4laric`.

This draft consolidates maintained P2 through `ffe6316` (PR #428) with main
`bac60df`. It is a review snapshot, not a release or Family-complete claim.
Unpushed worker files and later lane work are outside this pinned snapshot.

## Review map

- `experimental/` and `scripts/`: local-disc conversion, room/cave previews,
  actor fixtures, asset staging and acceptance tooling.
- `engine/`: P2 actor, animation, material and renderer support plus inherited
  upstream integration. Game code is unchanged from the tested PR #428 snapshot.
- `randomizer/` and `apworld/`: inherited optional Faithful to Prerelease trap;
  main's DeathLink, tracker regeneration and launcher behavior are retained.
- `docs/`: family status, limitations, evidence and lane coordination.
- `tests/`: conversion, mechanics, fixture and integration coverage.

The accumulated diff also includes the Challenge destination prototype and
prerelease trap from the ancestry of draft PRs #98, #101 and #106. Those drafts
remain available. This single draft makes the complete maintained P2 stack
reviewable against main without changing the existing lane branches.

## Integration decisions

Resolved overlaps in seed generation, CLI, bootstrap and AP world construction
by retaining both DeathLink and prerelease options. DeathLink options now live
in the extracted `options.py` alongside existing P2-branch options. A regression
test checks both protocols appear in the same generated bootstrap.

Retained main's player README, AI disclosure, legal notice and launcher help;
added the experimental P2 links and prerelease description. Development history
from both branches is retained. The `--extract-only/assets/.pikmin-assets` marker
already tracked on main is unchanged, not new generated content in this PR.

## Validation

- Universal Tracker: 12 regenerated slots, 48 matching reachability snapshots,
  restrictive fills pass using a temporary packaged world; shared AP unchanged.
- Combined DeathLink/prerelease bootstrap and trap tests: 3 passed.
- Native launcher finalization test: PASS bounded retry, permanent errors,
  destination preservation and filesystem finalization.
- Private native `a740c00f` and all 1591 exported files match. Only launcher
  finalization files/CMake differ from PR #428's validated native production
  source; no new production build or game runtime claim is made for this draft.
- Previous native production build and family runtime evidence is recorded in
  [integration #422](PIKMIN2_INTEGRATION_422.md).
- Full suite result is recorded below after completion. The initial attempt
  lacked the native worktree (20 failures, 1589 passes, 41 skips); all failures
  referenced missing native source. A matching private checkout was then added.

## Fixture and gameplay limits

Use [the mandatory fixture guide](PIKMIN2_IMPLEMENTATION_FANOUT.md): rebuild old
executables and regenerate arenas. The overlay adds 20 red Pikmin only when no
squad exists; both entrypoints use a centred 960x540 preview window by default.

[Family blockers](PIKMIN2_FULL_IMPL_BLOCKERS.md) remain authoritative. Source
FSM/receivers, natural combat, corpse/reward delivery, cleanup, mixed-scene
performance and full campaign acceptance vary by family and remain incomplete.

## Final review result

Full suite with the matching native checkout and MinGW runtime on PATH:
**1627 passed, 24 skipped, 1052 subtests passed** (120.87 seconds).
Draft PR #432 targets main and is mergeable. No merge into main was performed.
Diff whitespace inspection reports five inherited extra blank lines at EOF in
P2 source/tests; no unresolved conflict markers or integration whitespace errors.

## Upstream follow-up #433

Draft #432 now also includes Open Nectar main `511f22fe`. See
[the upstream ledger](../UPSTREAM_SYNC.md) for the new private native build,
conflict resolutions, validation and remaining visual/save acceptance limits.
This supersedes the earlier statement that engine gameplay source was unchanged.

## Completeness correction from audit #434

The draft consolidates the maintained P2 branch, not every pushed worker branch.
Direct source inspection found hard-lane export `87204df` absent despite historical
status text. Newer species, cannon, lifecycle and converter candidates also remain
outside the pinned snapshot. See [the refreshed blockers](PIKMIN2_FULL_IMPL_BLOCKERS.md)
for exact distinctions and the separate production seed/placement/install gap.
