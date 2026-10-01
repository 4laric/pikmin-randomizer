# P2 reproducible generated-session acceptance (lane 33, #444)

Independent acceptance lane 33 of
[the P2 implementation fan-out](PIKMIN2_IMPLEMENTATION_FANOUT.md). Assignment 4
of [the next-wave dispatch](PIKMIN2_NEXT_WAVE.md). Coordination
[#186](https://github.com/4laric/pikmin-randomizer/issues/186); child issue
[#444](https://github.com/4laric/pikmin-randomizer/issues/444). Implementation
owner: Codex via shared account `4laric`.

This lane owns QA tooling and reports. It consumes immutable builds and family
evidence; it never edits the artifact under test and never reports a run that
did not happen.

## Purpose

The dispatch defines one product chain:

> Generate seed -> automatic content staging -> ordinary native spawn -> natural
> interaction/combat -> death/drop -> actual transport/reward -> revisit ->
> process restart.

`experimental/pikmin2_generated_session_acceptance.py` prepares and records that
chain on a pinned combined build. It is deliberately separate from the lane
02/03/05 wiring probe (`scripts/test_p2_generated_session.py`). That probe
monkeypatches the lane 02 admission set and uses a synthetic content manifest to
exercise the plumbing. This harness never does: it drives the **real** product
generator with the **live** lane 02 admission set, verifies an immutable build
pin before anything runs, and refuses to emit `natural` evidence for a run that
did not launch the pinned executable.

| Stage | Real observation |
|---|---|
| `generate` | The product generator (`randomizer.seed.generate`, `p2_enemies=True`) emits a schema-9 manifest with a validated `p2_layout`. |
| `install` | The launcher stages session content automatically (no manual sidecar copying); witness `PIKMIN_CONTENT_STAGED`. |
| `natural_fight` | Ordinary spawn and combat through death/corpse; operator-declared witness markers. |
| `reward` | Exactly-once reward/cargo receipt on the real reward path; operator-declared markers. |
| `revisit` | Same seed re-entered with the same roster/rewards and no duplicate grant. |
| `restart` | Process restart restores the same session without stale references. |

## Fail-closed rules

- **No admission override.** `generate_pinned_session` accepts only the live
  admission set. Tests may inject a reviewed cohort, but such a run is never
  classified as natural evidence.
- **Pin before run.** `Pin.verify()` must succeed (root commit, native commit,
  executable present and SHA-256 matching) before `prepare` writes a session or
  a `natural` record is emitted.
- **A stage with no declared witness markers is `BLOCKED`**, never a silent
  pass. `natural` classification is refused unless the pinned executable was
  launched, so the QA matrix's
  [guardrail](PIKMIN2_QA_MATRIX.md) still resolves a fixture run to `BLOCKED` on
  a natural-required cell.
- **Content is preflighted offline** (`verify_manifest`): missing or stale
  sources fail before a session is written, mirroring the launcher.

## Evidence contract

A run produces one JSON document per step:

- `plan.json` — the pinned runbook plus a live dependency probe (no launch).
- `prepared.json` — verified pin, real `ENEMY_P2` bootstrap, bound identities,
  content coverage report and the exact launch command.
- `observations.json` — per-stage PASS/FAIL/BLOCKED against declared markers.
- `lane33-<stage>-<scenario>.json` — QA-matrix records for `report`.

Built-in `snow` and `dwarf_orange` profiles witness automatic installation with
`PIKMIN_CONTENT_STAGED` only. They leave natural fight, reward, revisit and
restart BLOCKED. Draw/corpse/haul markers also occur in controlled fixtures and
cannot prove those gameplay stages. Supply reviewed witnesses from the actual
generated-session path, including identity and intervention checks, before
classifying a natural result.

An explicit marker file extends a profile:

```json
{
  "install": ["PIKMIN_CONTENT_STAGED"],
  "natural_fight": ["ENEMY_P2", "P2_ENEMY_READY"],
  "reward": ["<family reward receipt witness>"],
  "revisit": ["<revisit spawn/receipt witness>"],
  "restart": ["<restart identity witness>"]
}
```

## Commands

```powershell
py -3.12 -m experimental.pikmin2_generated_session_acceptance verify-pin `
    --root-commit <root> --native-commit <native> `
    --executable <exe> --executable-sha256 <64-hex>

py -3.12 -m experimental.pikmin2_generated_session_acceptance plan `
    --root-commit <root> --native-commit <native> `
    --executable <exe> --executable-sha256 <64-hex> `
    --seed <seed> --placement <placement.json> --output <run>/plan.json

py -3.12 -m experimental.pikmin2_generated_session_acceptance prepare `
    ... --seed <seed> --placement <placement.json> `
    --session-dir <run> --content-manifest <content.json> --output <run>/prepared.json

# Operator launches the prepared session with the printed command, then:
py -3.12 -m experimental.pikmin2_generated_session_acceptance observe `
    --log <run>/runs/<token>/native.log --profile snow `
    --output <run>/observations.json

py -3.12 -m experimental.pikmin2_generated_session_acceptance records `
    ... --prepared <run>/prepared.json --observations <run>/observations.json `
    --kind natural --scenario baseline_cohort --output output/lane33-records
```

The `plan` command exits `2` while a dependency is blocked, `0` when the seed
generates on the pinned build.

## Current baseline status (2026-09-14)

- Pinned pair under test: **root `4fccf41`** (`origin/codex/p2-main-review`) and
  **native `b805d9c6`** (approved native baseline, clean).
- Lane 01 has not yet published an integrated executable for this pair, and the
  live lane 02 admission set is **empty** (`admitted_ids == []`). The
  generated-session chain therefore cannot start: `plan` reports

  ```text
  BLOCKED: generate: no admitted P2 identities; refusing to seed an unadmitted
  pool (lane 02 admission set is empty)
  ```

  This is the correct fail-closed result, not a missing test. It names the two
  dependencies the chain is waiting on: an admitted identity (assignment 1/2)
  and the integrated executable (lane 01).
- Snow Bulborb is the first cohort target, Dwarf Orange the second, per the
  dispatch. Neither identity is admitted by this document.

### Integration probe and current handoff, 2026-09-14

The earlier probe at native `1531c0ba` correctly found no ordinary generated
Snow binding. Its assertion that no baseline was published was stale: root
`569c5e2` already published that tested pair. Fetch the explicit downstream
`origin/codex/p2-main-review` branch and read
[the current sweep ledger](PIKMIN2_SWEEP_COHORT_437.md).

The follow-up integrates assignment 1 native `5a7329c5` and root `df32243`:
exact generator identity lookup, Snow host selection and content staging.
Protected generators and simultaneous blanket campaign overrides fail closed.
The native parser/binding probe is distinct from an ordinary gameplay run.
The admitted roster remains empty pending that gameplay acceptance.

## Tests

`tests/test_pikmin2_generated_session_acceptance.py` covers pin verification
(success, hash mismatch, missing commit/executable), the live admission block,
the reviewed-cohort success path (test-only injection), real bootstrap
preparation, content coverage rejection, marker classification, record
guardrails (natural requires a verified pin; fixture cannot satisfy a natural
cell) and the CLI.

```powershell
py -3.12 -m pytest tests/test_pikmin2_generated_session_acceptance.py tests/test_pikmin2_qa_matrix.py -q
```

## Integration correction (#437)

Built-in Snow and Dwarf Orange profiles witness automatic staging only. Draw,
corpse and haul markers do not prove natural combat or durable reward delivery;
those stages remain BLOCKED until reviewed generated-session markers are supplied.
A native commit pin also rejects evidence with a missing native commit. Earlier
profile descriptions listing fight/reward markers are superseded by this rule.
## Mixed-scene performance and actor budgets

Assignment 4 also requires the two P2 identities to be tested together with
recorded frame-time, memory and actor budgets.
`experimental/pikmin2_performance_budget.py` owns the acceptance side of that: it
consumes a measured manifest (`mixed-scene-validation.json` from
`experimental.pikmin2_mixed_scene_behavior`) plus an explicit budget policy and
resolves the `frame_budget` and `memory_budget` QA-matrix cells. It never
measures and never invents a threshold.

- **Nothing passes on a proposed policy.** The existing
  `PROPOSED_BUDGETS` are marked `proposed_not_accepted`; while the policy status
  is not `accepted`, every budget metric and cell resolves to `BLOCKED` with
  `budget policy is proposed, not accepted`. A proposed 16.7 ms target can
  therefore never be reported as an accepted PASS.
- **Metrics → cells.** `frame_budget` = `mean_frame_ms`,
  `slowest_window_mean_ms`; `memory_budget` = `tracked_texture_peak_mib`,
  `total_pose_bank_bytes`, `actor_count`. A missing measurement or an
  incomplete capture is `BLOCKED`; an exceeded budget is `FAIL`.
- **Records.** `records` emits `frame_budget`/`memory_budget` records for the
  matrix. These are boundary scenarios, so a private fixture run may satisfy
  them (`kind: fixture`, stage `install`); `natural` still requires a verified
  pin.

```powershell
py -3.12 -m experimental.pikmin2_performance_budget evaluate `
    --manifest <run>/mixed-scene-validation.json --budgets budgets.json `
    --output <run>/budget-evaluation.json
py -3.12 -m experimental.pikmin2_performance_budget records `
    --report <run>/budget-evaluation.json --kind fixture --stage install `
    --root-commit <root> --executable <exe> --executable-sha256 <64-hex> `
    --output output/lane33-records
```

An accepted policy is a JSON document: `schema` `p2-performance-budgets-v1`,
`status` `accepted`, and numeric
`target_mean_frame_ms_max`, `slowest_window_mean_ms_max`,
`tracked_texture_peak_mib_max`, `total_pose_bank_bytes_max` and optional
`actor_count_max`. No accepted policy exists yet, so the budget cells are
`BLOCKED` today. For reference, the last mixed-scene worker baseline was 12
species + one control at mean 33.45 ms and slowest-window mean 33.93 ms against
the proposed 16.7 ms / 20.0 ms — which, if those budgets were accepted, would be
a FAIL on `frame_budget` rather than a PASS.

`tests/test_pikmin2_performance_budget.py` covers policy validation, metric
extraction, the accepted/proposed/missing/invalid-capture outcomes, actor-budget
gating, record emission and the CLI exits.
