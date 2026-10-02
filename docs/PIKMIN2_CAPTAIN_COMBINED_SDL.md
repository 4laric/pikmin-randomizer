# Current combined captain SDL save/reload (#1130)

For CI-packaged Windows runs, pass `--runtime-dir` pointing to the verified
artifact directory containing the executable's matching MinGW DLLs and
`SDL2.dll`. The runner records their hashes; mixing executable-local DLLs with
a different toolchain is rejected before launch. `--prepare-only` stages inputs
and records provenance without running the game.

Linux omits `--runtime-dir` and records ELF, loader and shared-library evidence
from the staged native run directory, so relative loader paths resolve from the
correct cwd. Pass `--development-launch` for private execution under the current
direct-coordination policy (#1195/#1198). The common launcher retains runtime,
private-path, machine-capacity and bounded process cleanup checks; its optional
controller path remains available without that flag. These options preserve
the sixty-second phase bound and all save, card, population and captain guards.

Even when linked with `PIKMIN_NETPLAY_BUILD=ON`, this replacement-main fixture
runs an offline two-captain session. It does not execute production netplay
startup; the runner clears inherited `PIKMIN_`, `P2_` and `COOP_` settings.
Record the linked profile without claiming online co-op gameplay acceptance.
The results below remain historical evidence pinned to their original builds.

Codex through shared account 4laric. This bounded consumer uses the accepted
combined native `2e6efbb1b841c1889d1bbd3b656e44ba6ae3629b` and root
`22a2a5bc6718b809c4a29cf68d85d32a3659f68a` production foundation. Its only native
change is the standalone replacement-main fixture; root changes add its runner
and this document. It tests original P1 practice campaign geometry with the
generated `p2_second_captain=True` / `CAPTAINS 2` choice.

The fixture routes a real SDL virtual P1 through ordinary controller polling and
the explicit background virtual-input test seam. Both initialized captain guards
run before and after engine idle, including before readiness, movie and menu
returns. No positive actor, HP, species, ownership, timer, card, check or reward
writes occur in the fixture. Fresh setup uses the disclosed production
`TEST_BACKGROUND` stock withdrawal of20; this setup helper is not Onion UI proof.
Both resumed processes instead walk to the actual Onion, select20 in its real UI
and confirm with SDL input. Original generators and20/960×540centered/60s remain.

Actual Windows fixture09 SHA-256
`1d877e1598d86afa4efe724ddf89c928382018fdc53afa0103f0c518d5f96575`
was compiled from clean native `38a325ec6a9ec385b0973530bfc1e2b878051c85`.
The tested runner is root `4aea322d7a62a72d9e80488837ad88c68aacce4b`; the final
documentation commit changes no runtime code. The private production executable
remained byte-exact with build05 and its Ninja dry-run reported no work.

Fresh campaign09 results, each bounded to60seconds:

| Phase | Native outcome | Wall time |
| --- | --- | --- |
| Save via actual pause/sunset/results input | day2→3, exactly generation1 |57.906s |
| First fresh native load and Onion UI withdrawal |20stock→20live, controls pass |25.719s |
| Second fresh native load and Onion UI withdrawal |20stock→20live, controls pass |26.187s |
| Active captain HP0 negative |86, noPASS |10.500s |
| Inactive captain HP0 negative |86, noPASS |9.219s |
| Missing inactive state negative |86, noPASS |9.609s |
| Missing manager negative |86, noPASS |11.609s |

Both loads conserved the exact card bytes, day3, total20 and checked locations /
inventory. Both verified ordinary captain switching, camera binding, selected
movement with inactive horizontal position stable, and whistle. Native save/card
generation and reload are engine operations; no fixture `forceDayEnd`, day-end
flag write, direct `exitPikis` or saved-byte injection supplies positive evidence.
The initialized guard rejects HP≤1, nonfinite HP, dead/missing state and missing
manager; the explicit negatives mutate guarded state and pause only for that test.

Failed arenas and builds remain under `output/captain-combined-followup/`.
The pause confirmation originally arrived before the submenu fade completed.
Later reload diagnostics showed inactive `NAVISTATE_Idle` blocking the fixture
driver while the actual Onion UI already selected20. The corrected readiness
accepts Idle only after established resumed withdrawal; safety guards remain.

The private GitHub runner passed production and242 configured CTests on exact
root4aea/nativec085 in
[run36887620636](https://github.com/4laric/game-build-ci/actions/runs/36887620636).
That Linux result does not compile or run this standalone Windows fixture. Local
builds06–09 therefore linked only the unsupported fixture with an actual private
lease and production no-work checks. Later native changes affect only the fixture.
The canonical supervisor dependency is separately hashed; its full text matches
the private tracked source after explicitly disclosed CRLF→LF normalization.

Movie skipping and results-button holds are disclosed fixture shortcuts; the
fixture does not accelerate the day clock. This is scripted input through ordinary
engine paths, pending independent final review. The evidence supports one native
next-day save/load stock-conservation slice. Full native campaign resume, mid-day per-captain HP/ownership/active-slot
persistence, imported level traversal, full AP campaign and human game feel remain
unaccepted. Human smoke should use a validated direct-to-gameplay script and quick
reset; these automated processes do not constitute human playtest approval.
