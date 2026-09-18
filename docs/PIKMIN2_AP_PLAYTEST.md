# P2 Archipelago playtest integration (#439)

Implementation owner: Codex through shared account 4laric.

The AP option `p2_enemy_randomizer: true` now consumes `p2_placement`, a complete
lane-04 p2-placement-v1 mapping in the player YAML. It is passed unchanged to the
existing admission/placement validator. Missing, malformed and denied placement
fail generation. Keep P1 enemy shuffle modes off when enabling P2.

The .apworld bundles a pinned roster/evidence snapshot and the seed/placement
modules under its own package. It needs neither a repository checkout nor global
randomizer/experimental imports. Rebuild the package when admission changes.
No game assets are included. The bundled roster is read-only generation input.

Build and verify:

```
py -3.12 scripts/build_apworld.py --output output/pikmin_randomizer.apworld
py -3.12 scripts/test_p2_apworld.py --ap C:/Users/alari/Archipelago --archive output/pikmin_randomizer.apworld
```

The isolated integration test uses explicitly synthetic placement to check AP
fill, deterministic generation, missing/denied input rejection and saved-manifest
roundtrip. It does NOT establish gameplay placement acceptance.

Native P2 launch requires the existing --content-manifest or --p2-content route;
a bare seed can no longer start an unstaged native process. The content route
must cover seed identities; actor bindings and reviewed source assets remain
required as documented in PIKMIN2_CONTENT_STAGING.md.

## Remaining playtest blockers at this source pin

The actual admitted cohort is 23, 44, 59, 60, 61, 62. The checked-in
PIKMIN2_ADMITTED_PLACEMENT.json only contains Orange/Snow reviewed placements;
the general campaign catalog has no accepted pairs. Actual generation with the
reviewed document fails with unknown candidate identities Sarai, FireOtakara,
WaterOtakara, GasOtakara and ElecOtakara. Their admitted status does not grant new
campaign positions. The identity-keyed content installer resolves 44 but rejects
23 and 59–62. Existing family installers need reviewed binding adapters.

Therefore this package is a tested plumbing fix, not a ready playable seed.
Lane04 must deliver accepted campaign placements for the intended cohort and
lane05 must deliver identity-keyed runtime adapters/content receipts. Then run
actual AP generation and a bounded production-native launch using those exact
pins and inputs before distributing a Play.cmd. Do not substitute arena-only
flags, synthetic test placements, or changed admission to make generation pass.
