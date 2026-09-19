# MUKI + Damagumo #186 review preparation (#813)

Lane `muki-damagumo-186-review-prep`, issue #813, consumer
`p2-challenge-ch-muki-damagumo-p1` (#740, blocked gen 5), classification
`edbc7faab44d86e9cffdf0ae2386d52541a1e8eebef618ab1d2ff71f9ff41db4`.

## Scope

Bounded tooling-only review preparation. The #742 damagumo row and #748 MUKI
rows producers exist with recorded delivery contracts, but the #186 shared
review has no producer. This lane assembles the exact #186 decision packet for
both landings and records where no shared diff exists yet.

## Verified producer diffs (read-only, pinned heads)

- #742 `damagumo-stage-table-row-native` (done gen2): root `f0d2aec3` adds 4
  owned files (doc, experimental row spec, build helper, tests); native
  `185c9d67` adds 3 owned files (`pc_p2_challenge_damagumo_stage.h/.cpp`,
  `p2_damagumo_stage_table_fixture.cpp`). Zero shared-file edits.
- #748 `muki-stage-table-rows-native` (blocked gen5): root `baf82085` adds 4
  owned files (+2 small updates); native `cae86d4e` adds 3 owned files and
  `3c50ca44` tweaks the owned fixture. Zero shared-file edits.

## Decision packet

`experimental/pikmin2_muki_damagumo_186_review_prep.py` verifies the above and
emits a machine-readable packet: the rendered Damagumo row append against the
current destination table, a reference to the existing #777 MUKI packet
(sha `5361c258…`) for the two MUKI rows (not duplicated), destination pins,
the shared-file list, and a per-file recommendation.

## Finding

Neither producer modified shared files, so there are NO shared-file diffs for
#186 to approve or reject. The shared integration (appending the 3 rows to
`kP2ChallengeStages` in `pc_port/pc_bbft.cpp` plus the 2 stage-module
CMakeLists memberships) does not exist yet and must come from the integration
owner. The packet renders the exact proposed Damagumo append for review and
names this missing shared registration as the remaining input.

All six gates UNTESTED. No engine change, no approval granted, no gameplay
acceptance, no ADMIT.
