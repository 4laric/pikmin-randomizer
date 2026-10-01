# Two-captain ownership recovery (#1052 / #928)

The previous opt-in single-player switching fixture reached successful walking,
camera control, recruitment and throw, then crashed during captain capture.
`syncOwnership()` wrote null owners into Pikmin born or whistled after the
adapter's initial adoption. Their `ActCrowd` actions still used a captain and
formation plate. The historical closed drafts did not pass final acceptance.

The follow-up reconciles live noncaptive ownership before capture, knockout,
split, transfer and reload. Captor-held identities retain their capture epoch.
Unobserved actors first encountered during synchronization are preserved;
deliberate policy releases of managed actors still become free. Formation
ownership changes abandon the old action while its original captain is valid,
then revalidate the actor and policy before joining the new formation or entering
free mode. Switching retains each squad rather than moving it to the selection.

The existing #928 foundation adds remappable D-pad Up for an explicitly enabled
single-player pair, rejects unsafe targets/held actions and routes input/camera
to the selected captain. Co-op, VS and netplay keep their existing device mapping.
The native candidate contains that unmerged foundation plus this repair; the
repair commit itself is independently identifiable as `948d57282`.

## Regression checks

`native/tools/test_p2_captain_reconciliation.cpp` uses the production adapter
with engine doubles to verify late births, live whistle/disband changes, captain
capture, intentional knockout releases, transfer, captive epoch authority,
unknown actor preservation and invalid enumeration. The first late-born capture
assertion fails against the preserved pre-repair header.

The root test compiles the actual production `live_set_owner_slot()` function
against observable formation doubles. It checks old-owner cleanup, reformation,
free-mode release, no duplicate cleanup and rejection after callback changes to
owner, lifetime, captivity or policy. It does not emulate the function itself.

Run from a root worktree, pointing at the matching private native source:

```powershell
$env:P2_CAPTAIN_SOURCE='C:/Users/alari/pikmin-randomizer/output/native-two-captain-followup'
py -3.12 -m unittest tests.test_pikmin2_captain_reconciliation -v
```

Generated executables and logs stay under ignored `output/`. The CMake target
`p2_captain_reconciliation_test` keeps assertions enabled in Release.

## Acceptance boundary

These are source/compiled-double regressions. They do not prove the engine can
complete captain capture, natural combat, survivor control, ordinary campaign
resume or cave transitions. A fresh guarded pair run must adopt the current
20-Pikmin overlay, centered 960×540 startup and negative captain-down guard.
Production compilation and final runtime evidence must identify exact source
pins and executable hashes. No game assets, saves, binaries or generated fixtures
belong in the source PR. Louie presentation and two-captain campaign/cave
persistence remain separate work.
