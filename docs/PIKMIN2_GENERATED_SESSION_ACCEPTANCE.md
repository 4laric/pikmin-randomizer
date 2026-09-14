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

Witness markers are operator-supplied because family marker vocabulary differs
(`P2_ENEMY_READY`, `P2_DWARF_ORANGE_DRAW`, family `DONE ...` lines, reward
receipts). Turnkey profiles for the first cohort are built in and can be
extended without changing code:

- `snow` — `install`: `PIKMIN_CONTENT_STAGED`; `natural_fight`:
  `P2_ENEMY_READY`, `P2_SNOW_DRAW corpse=0`, `P2_SNOW_DRAW corpse=1`.
- `dwarf_orange` — the above plus `P2_DWARF_ORANGE_DRAW corpse=0/1` and
  `DONE P2_DWARF_ORANGE_COMBAT`; `reward`: `P2_DWARF_ORANGE_P1_HAUL`.

These are derived from the documented family evidence (`PIKMIN2_SNOW_BULBORB.md`,
`PIKMIN2_DWARF_ORANGE_NATIVE.md`) and must be confirmed on the first pinned
generated-session run. Stages with no distinct documented generated-session
witness stay unmapped and report `BLOCKED`.

An explicit marker file overrides/extends a profile:

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
