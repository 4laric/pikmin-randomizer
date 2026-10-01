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

The follow-up also closes a runtime-observed lethal-input gap. The source
engine enters death at health <= 1 (`naviState.cpp:1596,3080`), while death
animation completion later calls `NaviDeadState::init`. Opt-in single-player
control now immediately selects an eligible healthy partner after both captain
updates, neutralizes both controllers and binds the shared camera. It does not
normalize health, mark death or release Pikmin early. The native death state
retains those responsibilities. Nonfinite health, unsafe/captive partner,
cinematic input exclusion and unavailable partner fail closed.

## Regression checks

`native/tools/test_p2_captain_reconciliation.cpp` uses the production adapter
with engine doubles to verify late births, live whistle/disband changes, captain
capture, intentional knockout releases, transfer, captive epoch authority,
unknown actor preservation and invalid enumeration. The first late-born capture
assertion fails against the preserved pre-repair header.

The root test compiles the actual production `live_set_owner_slot()` function
against observable formation doubles. It checks old-owner cleanup, reformation,
free-mode release, no duplicate cleanup and rejection after callback changes to
owner, lifetime, captivity or policy. It does not emulate the function itself. A third check compiles the actual
`update_player_switch()` callback and observes immediate selection, camera/input
neutralization and preserved source health, plus excluded/unsafe target cases.
The engine-free health predicate tests the actual <= 1 boundary and rejects
nonfinite health.

Run from a root worktree, pointing at the matching private native source:

```powershell
$env:P2_CAPTAIN_SOURCE='C:/Users/alari/pikmin-randomizer/output/native-two-captain-followup'
py -3.12 -m unittest tests.test_pikmin2_captain_reconciliation -v
```

Generated executables and logs stay under ignored `output/`. The CMake target
`p2_captain_reconciliation_test` keeps assertions enabled in Release.

## Acceptance boundary

Fresh fixture03 runtime at native `0c6e4a28d0fb1b51a58c3f067c055970c9a01628`
passed pair and primary-down survivor checks. Both adopted20live Pikmin and a
centered960x540 window. Walking, both-way selection, camera drag/zoom, original
squad preservation, real disband/recruit, identified held-to-flying throw,
unsafe-held/captive/zero-health rejection and the original capture330 crash
regression passed. Lethal injected `InteractAttack` drove immediate survivor
selection, retained source health-400 until normal death initialization, one
native death roster transition at400,170 repeated selected-survivor frames and
held-Up rejection. Secondary-down formation changed19to0 through native death
release; primary-down began with an empty formation. All20Pikmin stayed alive.
Single and co-op switching exclusion checks passed. Negative captain-down exited86
without the acceptance marker; the guard was active in positive runs too.

Production SHA256:
`d9bfb150e9a151318c23135cd8d286c7fde348c631561e8c4affa0b52032f972`.
Replacement-main fixture SHA256:
`2e43b636542d49857ae389b3397c5ed84eb597a0e23c297bc8781e2ac0a431da`.
Private build dry-run reported `ninja: no work to do.` Five native Release tests
and three root compiled-production-callback tests passed. Exact local receipts
are under `output/two-captain-followup/{build-03,focused-build-03,fixture-03,
pair-05,survivor-05,single-05,coop-05,negative-05}` in the canonical workspace.

These bounded scripted checks use injected attack/captivity and labeled spatial
staging. They establish control/ownership repair, not natural enemy combat,
complete campaign resume, imported-level traversal or cave transitions. Captivity
phase remains adapter-authoritative; generic health refresh is not used to turn
negative engine damage into a premature policy death. No game assets, saves,
binaries or generated fixtures belong in source. Louie presentation and
captain campaign/cave persistence remain separate work. Maintained source export
and integration remain the integration lead's responsibility.
