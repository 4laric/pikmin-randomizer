# Combined P2 source delivery (#1118)

Implementation owner: Codex through shared GitHub account `4laric`.

This snapshot exports native `2e6efbb1b841c1889d1bbd3b656e44ba6ae3629b` from a
clean private worktree. It includes the accepted #1105 source plus the reviewed
White refund/player-pluck (#1103), White checkpoint/restoration (#1111), shared
enemy death/attachment availability (#1064), and generated native/AP delivery
fixture support (#1096). Native PRs 104, 106, 102 and 108 and their root source
PRs were merged after exact-producer review and green current CI.

The separate online netplay feature line contains the smaller radar (#1102) and
live Onion capacity refresh (#1108). Their root documentation/launch helpers are
available, but this P2 engine snapshot does not export that feature branch.
The reviewed co-op package keeps its own production/fixture pins.

## Actual build and export

- Private source: `output/native-p2-combined-1118`; dirty state empty.
- Private Release Ninja/GCC build: `output/native-p2-combined-build-1118`.
- Production `bin/nectar.exe` SHA-256:
  `83d2162930338eb33ab18b05bbf6c0268d04a1a96d5658c82168a4141213246b`.
- Current-source build and `ninja -n` passed; dry run reports no work.
- All 4,090 preflight native/tool/guard input hashes stayed unchanged across the
  current-source incremental build. The preceding clean full build is preserved.
- Export copied and byte-verified 4,023 native source files; 53 Android/touch
  binary assets and the ordinary exporter exclusions were skipped.
- Six pre-existing root-only source dependencies remain separately inventoried
  with their frozen #1105 hashes. They are not counted as current native files.
- Focused root checks passed121 tests and17 subtests, with two local White asset
  checks skipped because the private root has no derived White cache. Legal
  source assets and the independently recorded native White runtime evidence
  remain available in their separate canonical/private lanes.

Immutable local evidence is under `output/p2-combined-1118/`: current
`build-result-03.json`, `build03-inputs.json`, and `export02/export.json`.
The earlier missing-Ninja configuration, wrong executable-name collector, and
wrong guessed legacy-file names remain recorded. Their corrected pre-#1096
export is superseded, with no source-byte mismatch or deletion of legacy files.

## Bounded gameplay evidence

The frozen #1096 producer completed ordinary combat, corpse carry and Onion
delivery for source44 at original admitted Spring singleton3921089765
(`3/0-14.gen@231`). The real native journal produced `P2:44`; genuine AP
LocationChecks1347094060 produced reward1347096616. Session persistence and
authenticated reconnect preserved single credit. The 43.219-second positive
and same-pin captain-down exit86 were independently reviewed.

That producer predates #1064. Consumer #1119 therefore repeats the original
failure-sensitive case on the combined death/White source. Its positive passed
in42.891 seconds and the same-build captain-down control exited86 with no PASS
in1.11 seconds. Independent review verified all32 handoff references and3,308
provenance hashes and approved this bounded combined-source consumer case. Its
compiled producer pin stays distinct from the merged source. A byte-identical
fixture alias is the only source-tree difference; it does not change production.
The local immutable consumer handoff is
`output/generated-delivery-consumer-1119/handoff.json`; the independent review is
`output/p2-tested-merge/reviews/generated-delivery-1119-level-review-v1.json`.
Formal consumer registry submission awaits the producer's actual source-export
integration receipt; that administrative limit does not widen gameplay scope.

This case uses an existing audited placement subset, original unpruned scene,
real native withdrawal of20 starters, SDL virtual P1 input, and disclosed
movie/tutorial suppression. It does not move actors, change health, attach
carriers, alter route/gate state, or write checks/rewards. The accepted case uses
an open route; bramble completion is not inferred from it. All runtime tests use
fresh state, centered960x540 startup, initialized-captain safety checks before
early waits and a60-second wall-clock supervisor.

White #1103 proves bounded ordinary conversion/refund/player-pluck conservation.
White #1111 proves one naturally acquired White's species/maturity conservation
through a global native checkpoint and fresh restoration. That checkpoint
bypasses confirmation and does not prove full-squad Pod arrival or Ivory budget
persistence. #1064 headless contracts and startup adoption support the shared
death semantics; they do not accept every enemy's natural corpse behavior.

## Remaining gameplay gates

Human game feel, reliable Purple uptake, White ingestion/poison/buried mechanics,
ordinary procedural cave progression, full native day/save/campaign resume,
broader enemy/slot routes and combined second-captain campaign continuity remain
open. Earlier two-captain control/camera/whistle approval is preserved within its
own scope. Source delivery and one scripted loop do not grant full P2 campaign
acceptance. Short user-operated fresh-reset gameplay smokes remain the preferred
way to obtain human judgment.
