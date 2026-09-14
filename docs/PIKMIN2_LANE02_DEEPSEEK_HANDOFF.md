# Lane 02 — Roster/admission — DeepSeek handoff (#438)

Lane 02 / session `dsw/l02` / worker DeepSeek (executing agent: opencode,
`deepseek-v4-pro`) / implementation owner: Codex through shared `4laric` (per
AGENTS.md; no separate GitHub identity is implied). Parent issue #437, child
issue #438, coordination #186. Focused assignment slot: none of the five dispatch
slots claim roster work; this session continues lane 02's own schema/admission
ledger under its existing ownership.

## Concrete source IDs and the missing slice

The roster schema, audit and deny-by-default admission set were already integrated
(see `docs/PIKMIN2_ENEMY_ROSTER.md` and `docs/PIKMIN2_ROSTER_READINESS_SWEEP_437.md`).
This slice closes the one interface the next-wave guide names but the ledger did
not yet provide: **a fail-closed private candidate-validation path** so the
Snow / Dwarf Orange cohort can run the full generated-session chain without those
identities entering the global admission set.

- Source identities exercised (real consumer = the Snow/Dwarf Orange cohort through
  lane 03's seed bridge):
  - Snow Bulborb = `YellowKochappy`, `source_id 45`, module `pc_p2_snow`.
  - Dwarf Orange Bulborb = `BlueKochappy`, `source_id 44`, module `pc_p2_dwarf_orange`.
- Both are distinct **source** identities (never helpers or aliases); the two
  siblings are reviewed independently and neither is admitted.

## Root/native pins and ordered commits

- Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91` (branch `deepseek/p2-l02`).
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (branch `deepseek/p2-l02-native`).
- Root head after commit: `5e9d674f5eeca4be2befdd04aff6e7c206e360db`, clean.
- Native head: unchanged `b805d9c626e4f4558c95aef7cac311a5d9a2068f`, clean
  (see "No native commit" below).

Ordered commits (root only):

```
5e9d674 lane02: candidate opt-in validation path + Dwarf Orange cohort row (#438)
```

No native commit: this slice is entirely root-side (roster/schema/evidence/test).
Verified `scripts/generate_pikmin2_roster_revision.py --check` matches BOTH
`engine/pc_port/pc_randomizer_p2_roster.h` and the native worktree
`pc_port/pc_randomizer_p2_roster.h`, so the roster revision constant and the
native bindable-ID set are unchanged. I did not create an empty native commit.

## Owned files / interface changed and why

Owned by lane 02 (edited):

- `experimental/pikmin2_enemy_roster.py` — added `require_opt_in(roster, id)` and
  `opt_in_validation_cohort(roster, ids)`.
- `docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` — added Dwarf Orange (44) candidate row.
- `docs/PIKMIN2_ENEMY_ROSTER.md` — documented the private candidate-validation path.
- `tests/test_pikmin2_enemy_roster.py` — updated the candidate set and added
  opt-in cohort/consumer tests.

No shared-file (teki/CMake/native) edit; no lane 03 seed-bridge edit. The seed
bridge is only *exercised* read-only in a test via its existing `resolve_layout(...
admitted=...)` and `resolve_admitted_layout(...)` entry points.

Why: the next-wave guide (§"Experimental admission ... A private candidate
validation path must not enable unaccepted identities in normal generation")
requires an explicit opt-in path that cannot flip normal generation on. Today
lane 03's product entry (`resolve_admitted_layout`/`resolve_placement_layout`)
only seeds `admitted_ids(roster)` and fails closed while that is empty; the only
way to exercise a candidate was `resolve_layout`'s explicit-cohort diagnostic
API, which checks enemy/boss classification but not review state. The two new
functions add the missing review gate: only `candidate`/`admitted` identities with
a `source`/`variant` role may be opt-in validated.

## Build evidence

No native build or export was required for a root-side schema/audit slice, so I
did not queue the `build_lane.py` wrapper (a heavy build would consume a shared
slot with no changed C++ to validate). There is no `l02-build-evidence.txt` for
this slice. The native roster revision header is unchanged and was re-verified
with `--check` (both roots). Rather than a gameplay PASS, the deliverable is the
fail-closed ledger interface, matching lane 02's documented non-goal.

## Fixture baseline adoption

Not performed: this lane does no real-GL runtime acceptance this slice (roster/
admission is a root-side schema/tooling lane). The starting-Pikmin overlay and
960x540 centred-window startup remain lane 13/33 runtime obligations, not lane 02.
No environment variable or fixture evidence is claimed here.

## Six-gate table (roster/admission deliverable; gameplay gates are out of scope)

The fan-out "six arena gates" belong to family lane 13 + providers 03/04/05/06/07/08/10.
For this roster slice they are honestly reported against the *ledger*, not runner:

| Gate | Roster slice status | Note |
|---|---|---|
| exact identity & spawn | source-backed N/A (ledger PASS) | `identity_role` resolves 44/45 as distinct `source`; runtime spawn is lane 13/03 |
| autonomous movement/animation | N/A | lane 13 (`docs/PIKMIN2_DWARF_ORANGE_NATIVE.md`, family contract) |
| attacks & receivers | N/A | lane 13/10 |
| death & corpse | N/A | lane 13/06 |
| actual transport & reward | N/A | lane 13/06 |
| cleanup & re-entry | N/A (lane 13 reports E/G open) | lifetime/product gates remain lane 07/13 |

Roster-ledger deliverable gates (this slice's actual scope), all natural (no
injected state):

| Ledger gate | Result |
|---|---|
| Deny-by-default admission set empty (`admitted_ids == []`) | PASS |
| Candidate/alias/variant/helper distinction (`identity_role`, `resolve_alias`) | PASS |
| Opt-in validation path rejects denied/unknown/manager_base/plant/coerced/dup/empty | PASS |
| Opt-in validation never mutates admission; normal generation stays fail-closed | PASS |
| Consumer (seed bridge) fails closed when admission empty; binds private cohort only | PASS |

## Tests run

```
py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py -q                              # 21 passed
py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_seed_bridge.py -q   # 40 passed
py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_roster.py \
    tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py \
    tests/test_p2_placement.py -q                                                     # 103 passed, 17 subtests
py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_seed_bridge.py \
    tests/test_pikmin2_seed_generation.py tests/test_p2_placement.py \
    tests/test_pikmin2_roster.py tests/test_enemy_layout.py tests/test_enemy_slots.py -q   # 112 passed, 17 subtests
py -3.12 scripts/audit_pikmin2_roster.py --review                                      # admitted: 0 []
py -3.12 scripts/generate_pikmin2_roster_revision.py --check \
    --output engine/pc_port/pc_randomizer_p2_roster.h                                  # matches
```

## Assumptions

- Lane 02 owns `experimental/pikmin2_enemy_roster.py`, the two doc JSON/MD files,
  and `tests/test_pikmin2_enemy_roster.py`; the seed bridge remains lane 03's and
  is only consumed read-only in a test.
- Adding Dwarf Orange as `candidate` changes only *eligibility*, not
  classification or source IDs, so the roster revision and native header are
  unchanged; no native commit is warranted and none was made (empty commits
  avoided).
- "One real consumer" is the seed bridge's explicit-cohort path fed by
  `opt_in_validation_cohort`, demonstrating end-to-end that a private validation
  run is possible while `resolve_admitted_layout` stays fail-closed.
- No runtime/build was attempted because lane 02's deliverable ("new roster/schema
  module and audit tooling; does not claim gameplay PASS") is root-side and the
  audit already reports `pc_p2_snow` as `pc_p2_enemy.cpp` (pre-existing; unchanged).

## Remaining blockers (named provider lane)

- The admitted roster remains empty by design; admission is gated on lane 01
  accepting an integrated root/native pair and lane 33 reproducing the generated
  session — not on lane 02.
- Snow/Dwarf Orange natural gameplay gates (combat/death/transport/cleanup) remain
  lane 13 with providers 03/04/05/06/07/08/10.
- The opt-in path returns a Python list; if lane 03 wants to promote the cohort
  through a *manifest/serialization* field, that contract is lane 03's to propose
  (lane 02 supplies `opt_in_validation_cohort`/`require_opt_in` as the gate).

## Exact reproduction command

```
cd C:/Users/alari/pikmin-randomizer/output/dsw/l02-root && py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_seed_bridge.py -q
```

## Subagent usage

Three subagents were launched in parallel (staggered; never more than three).

1. `explore` — source audit of Snow (45) vs Dwarf Orange (44) identities and per-ID
   six-gate evidence in docs/native. Result used as-is; confirmed the
   `YellowKochappy`=Snow / `BlueKochappy`=Dwarf Orange enumeration quirk and the
   canonical native module names (`pc_p2_snow` inside `pc_p2_enemy.cpp`,
   `pc_p2_dwarf_orange`), plus which gates each identity had reported. Time saved:
   ~the whole enum/ID pinning exercise.
2. `explore` — inventory of every consumer/import of the roster admission interface
   and of the Snow/Dwarf files. Result used as-is; confirmed no existing
   "private candidate validation path" function exists and enumerated the exact
   two assertions to update. Time saved: avoided reimplementing a path already
   present via `resolve_layout(admitted=...)`.
3. `general` — green pytest baseline + grep for hard-coded candidate-set literals.
   Result used as-is; gave exact line numbers (`tests/test_pikmin2_enemy_roster.py:83,167`)
   and correct `64` is unaffected (it counts classification, not eligibility), which
   corrected that subagent's own misreading.

Net: the three reports materially shortened the audit phase and let me keep my own
context on the native/build/handoff work. Negative note: no fast way to delegate
the actual implementation, which I retained as required.
