# Cave navigation diagnostic QA handoff (#193 / independent QA #184)

Codex prepared a new machine-local package. No native game process was
started, focused, driven or stopped. Kimi manual navigation and geyser-return
acceptance remain open.

## Runnable package

Use:

`C:/Users/alari/pikmin-randomizer/output/p2-root-integration/output/p2-cave-nav193/cave-nav-qa-02/Resume-Diagnostics.cmd`

For preflight only, use adjacent `Check.cmd`. The copied standalone launcher
runs from its frozen `launcher-source` directory and forces
`PIKMIN_CAVE_NAV_DIAGNOSTICS=1` for the child. It verifies frozen source,
content inputs, Python executable, runtime/DLL closure, command destinations,
original-package preservation and existing cloned checkpoint before dispatch.
It does not rebuild or use the moving shared executable.

This resumes a **separate clone**, not manual-qa-02. Its mutable session is
`cave-nav-qa-02/session`; future native stages/logs appear beneath
`session/session/runs`. Do not run the native exe directly or launch the
`preflight-stage`: use the guarded command so diagnostics and session ownership
are explicit. A repeat launch resumes this cloned checkpoint; it never resets
it to 20 fresh Pikmin.

## What was preserved and cloned

Original fixed package:
`C:/Users/alari/pikmin-randomizer/output/p2-manual-qa-bundle/output/manual-qa-02`.
All 4133 ordinary-file/link entries matched their before/after snapshot.
Stage asset junctions were recorded without traversing or rewriting them;
asset content inputs were separately checked against the original manifest.
No original ledger, player-state file, log, lock/lease, source or executable
was modified. No process interaction occurred.

Only the exact entry-command bytes and authoritative surface-ledger bytes
were cloned. Revision 2, cave floor 2, 19 red leaf Pikmin, health 0.899999976,
empty receipts. Ledger SHA256:
`b0572e68b842699e3ddc64d254bdcb05121ae16d240c9cedc821ba4779c3500f`.
Campaign/content IDs remain identical because this is an offline snapshot
comparison; the filesystem session is separate. No original runs, pending
handoffs, native saves or leases were copied or replayed.

The historical `entry-command.run` reference remains byte-identical but is
inert: the guard requires a present, valid cloned ledger. The frozen one-trip
launcher takes its existing-ledger branch, stages fresh cave runs under the
clone, and never dispatches that historical surface run. Missing ledger is a
hard refusal, not permission to rebuild/replay the original entrance.

## Immutable runtime/source provenance

- Cave executable built native revision:
  `ba126b0f3b171955868366b094db8dedec196c16`.
- Copied cave SHA256:
  `0640bc10e01637c1d860dc05f839b49886d5260ed571d6419ae807b9d7be9420`.
- Cave bundle contains the exe and four resolved non-system DLLs, individually
  hashed in `cave/runtime-provenance.json`. Windows system dependencies remain
  machine-local. The earlier fixed surface `manual.exe` and its runtime closure
  were copied unchanged from manual-qa-02.
- `production-build.log` copies the root's successful tank225-integrated build
  log. Root confirmed that this exe is the ba126 build. Observed source HEAD
  had advanced to `4695160453eed190e529e7830f63e57eb7e53154` with only unreferenced
  standalone policy/test/docs additions; it is not the claimed binary revision.
  The root's known inherited creatureCollision/goalItem line-ending dirty diff
  remains part of source provenance, not a clean-HEAD binary claim.
- `launcher-source` contains byte-verified Python sources from the frozen QA
  checkout, not the changing integration branch. `diagnostic-launcher.py` is
  separately hashed. Local content assets remain referenced and hash-guarded,
  so this is not portable packaging or a release bundle.
- Manifest integrity is accidental-change detection, not cryptographic
  authentication against deliberate manifest/source rewriting.

## Programmatic acceptance

`Check.cmd` equivalent passed from the copied launcher. Frozen NativeContent
recomputed content identity
`d52e58239300159b4cca044d9ab66e9bca70bd6075abfe3d5be9897013f3934c`,
matching the cloned ledger. A no-process staging call reproduced exact floor2
entry squad/health/token, zero receipt ledger, geyser anchor (-550,25,520),
radius45 and `P2_CAVE_VISUAL_1 geyser`. This checks staging, not native load or
render. `preflight-evidence.json` records every staged config hash.

`launch-preflight.json` records the full guard and command/environment dispatch
with the launch process replaced by a recording callback. No game was launched.
Six focused tests pass: clone identity/floor refusal, changed-file detection,
nontraversed junctions, diagnostic environment override, guard refusal before
dispatch and cloned destination command. Package `cave-nav-qa-01` is retained as
a rejected preflight attempt: its Python identity probe passed strings where
Path objects were required. Use version02 only; no native process ran in01.

Source additions for integration:
`scripts/prepare_pikmin2_cave_nav_qa.py`,
`tests/test_prepare_pikmin2_cave_nav_qa.py`, and this document.
No shared native source/build, branch or existing QA source was changed.

## Navigation and remaining manual gates

Expect an imported geyser model, not a cyan ring. The model branch returns
before fallback-ring drawing. Read the bounded `P2_CAVE_NAV` rows in the new
native.log: captain XYZ/heading, anchor delta, horizontal/vertical distance,
walk/safe state, interaction eligibility, model path and draw count.

Approach X=-550, Z=520 while captain Y is near25. Spatial acceptance is
horizontal distance <=45 and vertical difference <=40. Walk/safe eligibility
is not final transfer acceptance: sprouts, busy/combat Pikmin, confirmation and
other normal rules still apply. Logs are capped at120 rows per stage with at
least2 seconds between rows, so use bounded evidence-led navigation rather
than an extended blind sweep. Draw invocation is not proof of visibility.

Record actual model visibility, F6 confirmation, surviving party/health at
return, completed-trip re-entry refusal and post-return restart preservation
in this new-build clone. These are not passes on the earlier fixed binary.
Nonzero collected receipts are still required to test duplicate rewards;
the inherited zero receipts establish no duplication coverage. This batch
claims no gameplay, terrain accessibility, native compatibility or full-loop
acceptance. Report fresh-build differences with both executable hashes.
