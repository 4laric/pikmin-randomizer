# Throughput worker l76: review and deployment of fenced handoff reconciliation (#520)

Owner: Codex via shared 4laric; executing worker: paid Muse (`muse-tooling-integrator`,
lane 76, generation 1). Parent input: l75/#511 candidate and
`output/workflow/integration-speedup/l75/handoff.json`.
Private root: `C:\Users\alari\pikmin-randomizer\output\msw\l76-root`, base
`d0f954da8fa97283bac8a6c6e035e637d25116f1`.
Session: `opencode:ses_f56f34bc7ffeSckAXdbFKMIpki`, attempt `5d7c170faa984183aade3f73f5d4f00f`.

## 1. Candidate review (accepted, no changes requested)

Reviewed branch `codex/muse-l75-p2-reconcile`, verified actual head `fdb7e928`
(matches the reported head; parent is exactly the maintained base `d0f954da`).
Scope is 4 additive files, 399 insertions, zero deletions:

- `workflow/control.py` (+44): new `ControlMixin.reconcile_handoff` — blocked to
  `handoff_ready` only, failing closed unless fresh generation/revision, recorded
  worker confirmed dead (live/unknown refused), no live/unknown lease or queued
  request for the lane/generation, no in-flight controller launch, and the
  submitted handoff plus all referenced evidence revalidates via existing
  `check_handoff`. Preserves handoff record, source identities and pending
  reviews; `integrate()` still refuses while reviews are pending.
- `scripts/reconcile_pikmin2_handoffs.py` (+47, new): thin audited CLI wrapper;
  all guards stay in the registry method; never edits SQLite directly.
- `tests/test_pikmin2_reconciliation.py` (+199, new): 10 tests covering happy
  path through to `integrate`/`done`, stale generation/revision, live/unknown
  owner refusal, handoff-file and evidence drift refusal, non-blocked and
  handoff-less rejection, review preservation with `integrate` still refusing,
  in-flight launch refusal, and live-lease refusal with dead-lease tolerance.
- `docs/PIKMIN2_RECONCILIATION_511.md` (+109, new): diagnosis record.

Review findings:

- Dead-owner fencing: live AND unknown probe results are refused; leases and
  queued requests are re-probed per resource. No automatic worker restart path.
- Generation/revision races: `lane(state, key, generation, revision)` enforces
  exact fencing; stale values raise instead of overwriting.
- Hash revalidation: full `check_handoff` rerun, so silently edited handoffs or
  drifted evidence fail closed (covered by tests).
- Review-preserving: pending reviews survive; `integrate()` behaviour untouched.
- Remote-worker compatibility: no host-specific calls; new tests run on isolated
  temp registries.
- No gameplay changes, no validator weakening, no controller config edits.
- All four file hashes in the producer worktree match the handoff evidence
  exactly (`e395fd84…`, `bee9891a…`, `c43271ac…`, `98608d5e…`).

## 2. Test reproduction (independent, before integration)

In read-only producer worktree `output/msw/l75-root`:

- `py -3.12 -m unittest tests.test_pikmin2_reconciliation` — 10/10 pass.
- `py -3.12 -m unittest tests.test_pikmin2_workflow tests.test_pikmin2_controller
  tests.test_pikmin2_fixture_build` — 76/76 pass, no regressions.

## 3. Private integration

Branch `codex/muse-l76-tooling-integrator` in the private root was fast-forwarded
to `fdb7e928` (clean ff; `d0f954da` is the direct parent; working tree clean).
Post-merge validation in the private root:

- Combined suite: 86/86 pass (`test_pikmin2_reconciliation` +
  `test_pikmin2_workflow` + `test_pikmin2_controller` +
  `test_pikmin2_fixture_build`).

This report (`docs/PIKMIN2_THROUGHPUT_76.md`) is the lane's only authored file
and stays on the private branch; it is NOT part of the maintained-root
deployment.

## 4. Maintained-root deployment (tooling lead authority)

Pre-write verification of `C:\Users\alari\pikmin-randomizer`: HEAD
`d0f954da` (== candidate parent, no concurrent commits beyond base), no dirty
tracked files (only unrelated untracked lane artifacts), no other TOOLING
writer among active lanes (l77 cave, l78 reviews/handoff, l79 Kogane evidence).
Deployment is a clean `--ff-only` advance of the maintained checkout to
`fdb7e928` — reviewed tooling files only. See `completion.json` in
`output/workflow/throughput-workers/l76/` for the recorded commit and hashes.

## 5. Downstream enablement

`api-ready.json` (same output dir) publishes the exact
`scripts/reconcile_pikmin2_handoffs.py` command/API signature plus the
fencing contract, so l78 can apply the operation to muse-fuefuki/muse-bombsarai
once deployed. l75 integration bookkeeping (`muse-p2-reconcile` receipt) is
recorded via supported validated operations; species merge/build/export
authority remains with the existing P2 integrator.

Remaining work (not mine): l78 shared-review approvals via NEW versioned
handoffs + receipt with existing receipt files; l79 Kogane resubmission;
species-integrator promotion of wave lanes.
