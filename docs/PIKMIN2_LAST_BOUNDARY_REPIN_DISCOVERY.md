# AREA LAST engine-boundary re-pin discovery (issue #151)

Lane `shard-overworld-last-boundary-repin-discovery`, recovery `40fa0cd5`.
Owner: Codex through shared account 4laric. BOUNDED tooling job: read-only
reassessment of the five surface-session boundaries for Wistful Wild against
pins that postdate the cycle-26 wall finding. No source edits, no shared-file
changes, no builds, no runtime runs, no ADMIT. Issue #151 stays OPEN.

## Method

- Research pins re-verified fresh against read-only
  `native/pikmin2-research` (`init@singleGameSection:183`,
  `write@gamePlayDataMemCard:39`, `actOnyon@onyonMgr:403`,
  `read@gameGeneratorCache:557`); the rest carried verbatim from the done
  #658 registry with provenance labels. Anything unverifiable would be
  recorded ABSENT (none needed: all 22 pins verify).
- Native preview-entry pin re-verified fresh against the canonical
  read-only `native` checkout (`--experimental-pikmin2-room` at
  `pc_port/pc_bbft.cpp:44`).
- #736 engine-save-serializer handoff read for its run_save evidence
  (recorded `run_save` sha `560fd7ca`); canonical guard re-hashed fresh
  (`d2f678c9`, match). #712 conformance (done) closes the audit side.
- Machine-readable registry:
  `experimental/pikmin2_last_boundary_repin_discovery.py` (`registry()` /
  `verify_registry()`); reusable checker is the module CLI; focused tests:
  `tests/test_pikmin2_last_boundary_repin_discovery.py` (17 green).

## Verdicts

| Boundary | Status | Owner / review |
|---|---|---|
| overworld_boot | WALL | existing engine lanes + #186 (no last-area boot observed anywhere) |
| day_advance | WALL | #186 (pins exist, no owner; sunset-loss enumeration still unpinned) |
| save_serializer | CONSUMABLE | #736 (handoff_ready, integration pending) + #132 + #712 |
| receipt_ledger | WALL | #606 + #186 (no owner; endpoint unscoped) |
| exit_reentry | WALL | #607 + #186 (no owner; needs generator-side owner) |

Only the save-serializer boundary flipped since cycle-26 (wall ->
consumable) on the integrated #736 engine item plus #712 conformance. The
other four are unchanged walls with exact pins and review contracts.

## Downstream spec outline (save_serializer only)

Proposed follow-on lane files (proposals, not claims):
`experimental/content_lanes/p2-overworld-last-save.py`,
`tests/content_lanes/test_p2_overworld_last_save.py`,
`docs/content_lanes/p2-overworld-last-save.md`.

Acceptance: drive the #736 serializer fixture path for AREA LAST inputs
and observe save markers on a real run with captain safety #632 adopted
(guard/source hashes recorded); all six gates UNTESTED unless genuinely
observed; validated handoff with exact remaining blockers; no ADMIT.

## Remaining work

- Route the four wall boundaries to their review owners via #570; do not
  duplicate #186/#606/#607 scopes from this lane.
- The save-consumer probe above is the next bounded slice once #736
  integrates; until then P1 native runtime for area last stays parked.
- Full P1/P2 acceptance for area last stays OPEN.
