# Assignment 4: test the candidate before admission

Tracking #444; implementation owner Codex through 4laric. This resolves the
admission-before-QA circular dependency. Assignment 4 should gather private
candidate encounter evidence now; lane 02 admits only after review. It must not
wait for admission to begin that work.

The native Snow binding was first published at root `b7ec784`. Current QA snapshot: native
`5b446a64156b338628c6d636cab3dc76f5a9d224`, clean. Its executable is
`C:/Users/alari/pikmin-randomizer/output/p2-integration-5b446a64/nectar.exe`,
SHA-256 `4abdd82ada810088e95a41ded05c7e959f4aeb44d16207743a41cee65c9240a6`.
This commit-specific executable copy stays fixed across later integration builds.
Fetch `origin/codex/p2-main-review` for the new Python-only candidate helper.
Record the actual root commit after updating; no native rebuild is required.
Do not use the historical occupied `output/p2-main-review/native` checkout.

## Runnable entrypoint

`experimental.pikmin2_candidate_session` is a separate diagnostic process that
scopes the existing admission function to Snow source **45 only**, then uses the
existing generator, manifest validation and launcher. The normal CLI and roster
are unchanged. Candidate manifests remain rejected by the normal loader while
Snow is unadmitted. The override is restored on errors and process exit.
Placement compatibility, content hashes/identity and executable pin checks remain
in force. No source changes or per-agent monkeypatch script are needed.

From your updated private root worktree, use the assignment-3 placement document
and assignment-1 Snow content manifest. These must be real handed-off inputs;
do not invent placement acceptance or use synthetic unit-test slots.

```powershell
$qaRoot = git rev-parse HEAD
$qaPin = @('--root-commit', $qaRoot,
  '--native-commit', '5b446a64156b338628c6d636cab3dc76f5a9d224',
  '--executable', 'C:/Users/alari/pikmin-randomizer/output/p2-integration-5b446a64/nectar.exe',
  '--executable-sha256', '4abdd82ada810088e95a41ded05c7e959f4aeb44d16207743a41cee65c9240a6',
  '--assets', 'C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
# Set these to the actual assignment handoffs:
# $qaPlacement = 'absolute/path/to/reviewed-placement.json'
# $qaContent = 'absolute/path/to/snow-content-manifest.json'
py -3.12 -m experimental.pikmin2_candidate_session plan @qaPin --seed snow-candidate-01 --placement $qaPlacement --output output/qa-snow-plan.json
py -3.12 -m experimental.pikmin2_candidate_session prepare @qaPin --seed snow-candidate-01 --placement $qaPlacement --content-manifest $qaContent --session-dir output/qa-snow-session-01 --output output/qa-snow-prepared.json
py -3.12 -m experimental.pikmin2_candidate_session run --prepared output/qa-snow-prepared.json
```

The last command uses the ordinary launcher and content overlay, with the same
private admission scope during manifest loading. Repeat it for process-restart
checks of that session. It verifies the executable hash again before launching.
A normal `python -m randomizer run` will still reject the candidate; that is an
expected regression check, not the candidate launch command.

If assignment 1 delivered an import directory rather than a content manifest,
use `python -m experimental.pikmin2_enemy --imported <directory>
--content-manifest <new-file>` to generate the manifest. This does not generate
placement evidence. Missing placement or content is a specific dependency to
coordinate with assignments 3 or 1, rather than an empty-admission blocker.

## What to prove

Observe ordinary spawn, natural interaction/combat, real death and transport,
correct reward delivery, revisit and restart, plus opt-in-off/P1 controls.
Keep the mandatory current starting-Pikmin and centered 960x540 fixture baseline;
verify actual gameplay, not just a title-screen process. The candidate helper
runs the ordinary launcher: it does not bypass the title, force a kill, add a
squad to arbitrary campaign stages or turn arena-only evidence into campaign
acceptance. Coordinate the single-GL slot through #186.

Plan/preparation reports carry `candidate_scope=private-snow-candidate-v1` and
`product_admission=false`. The existing observe command can collect stage
markers, but keep results in a separately labeled pre-admission candidate
report. Missing combat/reward evidence stays missing; built-in profiles prove
staging only. The product `records` command rejects candidate preparations.
After candidate evidence is reviewed and lane 02 admits Snow, rerun the normal
product plan/prepare/records path on the admitted pair. Do not make admission a
prerequisite for collecting the candidate evidence that justifies it.

Dwarf Orange is not enabled by this helper. Add its explicit identity only after
its generated host/staging connection is integrated and ready for candidate QA.

Validation: 80 focused candidate, generated-session, bridge and QA tests passed.
They cover private generation/preparation, launcher argument reconstruction,
normal rejection, override restoration, exact-source restriction and rejection
of candidate evidence by product acceptance records. These are tooling tests,
not a gameplay acceptance claim.
