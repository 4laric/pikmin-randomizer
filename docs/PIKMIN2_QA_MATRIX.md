# P2 mixed-scene and seeded-run QA matrix

Lane 33 of [the P2 implementation fan-out](PIKMIN2_IMPLEMENTATION_FANOUT.md)
(dispatch #435, coordination #186, audit #434). Child issue
[#444](https://github.com/4laric/pikmin-randomizer/issues/444).

Implementation owner: Codex via shared account `4laric`. Executing
agent/session: opencode (deepseek-v4.1-flash), started 2026-09-13.

This lane owns QA tools and reports, not production fixes. It consumes pinned,
immutable builds and family evidence; it never edits the artifact under test.

## Purpose

The matrix makes the independent acceptance surface explicit and keeps
"harness passed" separate from "real seed passed". It is the cross product of a
pipeline stage and a scenario class. Every cell defaults to `UNTESTED`.

Stages:

1. `generate` — a real seed generates with the P2 cohort selected and content
   resolved.
2. `install` — content is staged automatically with no manual sidecar copying.
3. `natural_fight` — natural combat through death/corpse with no injected
   state.
4. `reward` — exactly-once reward/cargo receipt on the real reward path.
5. `revisit` — the seed is re-entered with the same roster/rewards and no
   duplicate grant.
6. `restart` — a process restart restores the same session without stale
   references.

Scenario classes: `baseline_cohort`, `adversarial_density`,
`ownership_conflict`, `weak_stats`, `strong_stats`, `minimum_cap`,
`paused_events`, `scheduled_births`, `interrupted_capture`, `address_reuse`,
`missing_assets`, `frame_budget`, `memory_budget`.

## Evidence and PASS rule

A cell becomes `PASS` only when a pinned record supplies **all** of:

- a `root_commit` (and optionally `native_commit`) identifying the source,
- a `build_sha256` (or `executable_sha256`) identifying the binary/fixture,
- at least one `evidence_paths` entry on disk, and
- admissible evidence kind for that cell.

Evidence kinds:

| kind | may satisfy | notes |
|---|---|---|
| `natural` | any cell | real seeded/input run |
| `fixture` | non-natural-only cells | private native runtime fixture |
| `injected` | never on its own | controlled injected state; label it |
| `synthetic` | never | generated/scaffolded data |
| `mocked` | never | a mocked scene is not a real seed |

`natural_fight`, `reward`, `revisit`, `restart`, `baseline_cohort`,
`adversarial_density`, `ownership_conflict`, `weak_stats` and `strong_stats`
require a natural run. Boundary and negative scenarios (`minimum_cap`,
`paused_events`, `scheduled_births`, `interrupted_capture`, `address_reuse`,
`missing_assets`, `frame_budget`, `memory_budget`) may be exercised by a
private runtime fixture, but never by a mock.

If any pinned record for a cell is `FAIL`, the cell is `FAIL`. A `PASS`
attempt with inadmissible evidence or incomplete provenance resolves to
`BLOCKED`, with the reason recorded.

### Pinned-baseline enforcement

`report` accepts the pinned baseline under test via `--root-commit`,
`--native-commit` and `--build-sha256`. When a pin is supplied, a record must
match it to pass: a record from a different root/native commit or executable
hash is resolved to `BLOCKED` (`... does not match the pinned baseline`), never
green. This keeps evidence from an older or unrelated artifact from satisfying a
cell on the current build. An empty pin disables the check (diagnostic use).

## Record schema

A record is a JSON object (or a list, or `{"records": [...]}`):

```json
{
  "id": "bt-fsm-phase-01",
  "stage": "natural_fight",
  "scenario": "baseline_cohort",
  "kind": "natural",
  "status": "PASS",
  "root_commit": "06cae25...",
  "native_commit": "9735870c...",
  "build_sha256": "8B9CCAFEE...",
  "evidence_paths": ["output/run/verification.json"],
  "notes": "natural combat, no injected state"
}
```

`status` is one of `PASS`, `FAIL`, `BLOCKED`.

## Usage

```powershell
py -3.12 -m experimental.pikmin2_qa_matrix validate --records output/lane33-records
py -3.12 -m experimental.pikmin2_qa_matrix import-run --manifest <verification.json> `
    --id bt-run-01 --stage install --scenario missing_assets --kind fixture `
    --root-commit <root head> --out output/lane33-records/bt-run-01.json
py -3.12 -m experimental.pikmin2_qa_matrix report --records output/lane33-records `
    --output output/lane33-qa-baseline `
    --root-commit <root head> --native-commit <native head>
```

`import-run` converts a run manifest (`verification.json`, `arena.json`, ...) into
a validated record. The operator supplies the stage/scenario/kind classification;
the tool extracts the manifest status, the fixture executable hash and the
evidence path, and refuses an invalid classification. A private fixture record
satisfies a boundary cell but the report still resolves a natural-required cell
to `BLOCKED` with `fixture evidence cannot satisfy this cell` — the guardrail
that keeps a harness run from being reported as a real seed.

The `report` command writes `qa-matrix.json` (machine-readable) and
`qa-matrix.md` (human table) and exits non-zero on any invalid record.

## Current baseline status

The reproducible generated-session runner is
[`experimental.pikmin2_generated_session_acceptance`](PIKMIN2_GENERATED_SESSION_ACCEPTANCE.md).
It drives the real product generator with the live lane 02 admission set,
verifies a pinned combined build before anything runs, and emits records for
this matrix. It never monkeypatches admission and never labels a fixture run as
natural.

Pinned pair under test: **root `569c5e2`** (`origin/codex/p2-main-review`,
"Publish validated P2 cohort baseline and runtime acceptance") and combined
**native `1531c0ba`** (clean), production executable SHA-256
`11311EE536C7438B0B68BA5A0C469C8A7DEAA547B57CF7C3C75504E5E6A3F324`. The live
lane 02 admission set is empty, so the generated-session chain cannot start and
the runner reports `BLOCKED: generate: no admitted P2 identities` - the correct
fail-closed result.

There is still no admitted cohort, so every matrix cell is `UNTESTED` against
the pinned baseline. Private fixture evidence may satisfy the boundary/negative
cells as it is produced; those records must carry `kind: fixture` and full
provenance.

The `frame_budget` and `memory_budget` cells additionally require an **accepted**
budget policy. `experimental.pikmin2_performance_budget` resolves them from a
measured mixed-scene manifest, but the existing `PROPOSED_BUDGETS` are
`proposed_not_accepted`, so any evaluation (and record) is `BLOCKED` until the
user/integration accepts a policy.

## Tests

`tests/test_pikmin2_qa_matrix.py` covers the full cross product, default
`UNTESTED`, the natural/fixture/injected acceptance rules, provenance gating,
fail precedence, record validation and duplicate detection, file/directory
loading, markdown output and the CLI. Run:

```powershell
py -3.12 -m pytest tests/test_pikmin2_qa_matrix.py -q
```
