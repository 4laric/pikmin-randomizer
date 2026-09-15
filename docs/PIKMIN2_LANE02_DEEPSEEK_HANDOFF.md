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
eb04222 lane02: DeepSeek handoff (#438)
(review fix commit follows: evidence-ledger wording, consumer labelled test-only)
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
- Review note: `require_opt_in`/`opt_in_validation_cohort` currently have no non-test caller; the consumer is test-only until lane 03 wires `resolve_opt_in_layout`.
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
py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_seed_bridge.py -q
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

## Slice 2

Second bounded slice: **complete ledger coverage** (same worktrees, no GitHub
writes, no admission/seed-bridge change).

### Concrete source IDs and files owned

Expanded `docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` from 7 to **78 rows** (7
unchanged `candidate` rows preserved verbatim + 71 new `denied` rows). Every
identity with a native `pc_p2_*` module or a `docs/PIKMIN2_*_NATIVE.md` source
slice now carries a row with: exact source ID, native module, owning lane,
six-gate statuses (natural vs injected labelled in notes), `eligibility: denied`,
and a `source` list naming the doc(s) transcribed from. Nothing is admitted.

Files changed (lane 02 owned):
- `experimental/pikmin2_enemy_roster.py` — added `RosterEntry.source` tuple + parse.
- `docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` — 78 rows.
- `scripts/audit_pikmin2_roster.py` — `SHARED_MODULES`, `MODULE_ALIASES`,
  `native_source_docs()`, `coverage_gaps()`; `--review` now enforces completeness.
- `docs/PIKMIN2_ENEMY_ROSTER.md` — documented the `source` field + coverage audit.
- `tests/test_pikmin2_roster_coverage.py` — new audit-rule tests.

### Audit rules (--review exit code)

`--review` exits 1 when any of these hold, 0 on the completed ledger:
- a row cites a `source` doc that does not exist;
- a row cites a `native_module` that resolves to no `pc_p2_*.cpp`;
- a `docs/PIKMIN2_*_NATIVE.md` slice is cited by no row (renderer BILLBOARD and
  cave BEASTS_FLOOR3_FAILURE docs exempt);
- a non-shared native `pc_p2_*.cpp` module is referenced by no row (`SHARED_MODULES`
  allowlists provider/species/projectile/sub-module stems).

### Coverage table (modules found / rows / gaps)

- Native `pc_p2_*.cpp` modules found: **126** (engine/pc_port == native worktree).
- Evidence rows: **78** (71 denied, 7 candidate).
- Gaps: **0** — audit prints `ledger coverage complete: True`, exit 0,
  `admitted: 0`.
- SHARED_MODULES allowlist: 80 stems; MODULE_ALIASES: `pc_p2_snow -> pc_p2_enemy`.

### Not-done-as-intended gaps recorded (not audit gaps)

No dedicated native module yet for: Tobi=14, FireChappy=33, KumaChappy=35,
BlueChappy=42, YellowChappy=43, KumaKochappy=76, FminiHoudai=97, Rock=19,
Bomb=36, Egg=37, Stone=74, JigumoNest/PanModokiNest/PanHouse, UmiMushiBase=100,
and LeafChappy=67 (Bulbmin species, lane 11). These correctly carry no row and
default denied; they are not identity modules so no audit gap fires.

### Tests / evidence

```
py -3.12 -m pytest tests/test_pikmin2_roster_coverage.py tests/test_pikmin2_enemy_roster.py -q   # 31 passed
py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_roster.py \
    tests/test_pikmin2_roster_coverage.py tests/test_pikmin2_seed_bridge.py \
    tests/test_pikmin2_seed_generation.py tests/test_p2_placement.py -q                        # 113 passed, 17 subtests
py -3.12 -m pytest <roster/seed/placement/enemy suites> -q                                      # 125 passed, 17 subtests
py -3.12 scripts/audit_pikmin2_roster.py --review                                               # exit 0; coverage complete: True
py -3.12 scripts/generate_pikmin2_roster_revision.py --check (engine/ + native worktree)        # both match
```

### Assumptions

- `source` is a list (an identity is often covered by several docs), not a single
  filename; the review note that the opt-in consumer is test-only still holds.
- Six-gate values: only a doc's natural (real-GL) observation is transcribed as
  `PASS`; labeled injected/fixture results are `UNTESTED`/`BLOCKED` and explained
  in `notes`. Plant/hazard/helper rows exist (they have modules/slices) but can
  never be `admitted` (role check unchanged).
- Module-vs-row coverage is driven by `SHARED_MODULES`/`MODULE_ALIASES` curated
  from the native source; no changes to admission or the seed bridge.

### Subagent usage

- `explore` #1 (module->identity classification): used as-is; gave the full 126-module
  partition (30 shared / 96 identity) and the `pc_p2_snow -> pc_p2_enemy` alias.
- `explore` #2 (docs->identity + six-gate evidence): used as-is; drove the 78-row
  transcription and the `_NATIVE.md` citation map.
- `general` #3 (coverage tests): the test contract was incomplete (single-string
  `source` vs my list; doc-existence via `native_docs` vs on-disk). Rewritten by me
  against the final `coverage_gaps(..., existing_docs=)` signature; its skeleton and
  the 4-gap-list key names were retained. Net: the two explore agents saved most of
  the time; the general agent's tests needed a full rewrite (mild cost).

## Fix 2

Review corrections to slice 2 (blocking items 1-3 applied, 4-6 done).

### Rows changed (transcription rule: natural PASS only, else UNTESTED/BLOCKED)

Applied ONE rule across the whole ledger and re-scanned every PASS gate whose
notes (or source doc) claim proxy/injected/fixture/vehicle/display/P1-host.

- Row **20 (Hiba)**: `attacks_receivers` PASS -> `UNTESTED` (note kept: fire hit
  PASS injected; no natural claim).
- Row **0 (Pelplant)**: `death_corpse`/`cleanup_reentry` PASS -> `UNTESTED`
  (identity is an injected TEKI_Palm proxy).
- Row **1 (Kochappy)**: `identity_spawn`/`movement_animation` PASS -> `UNTESTED`
  (visual/vehicle-only P1-proxy).
- Row **38 (PanModoki)**: `identity_spawn`/`movement_animation` PASS -> `UNTESTED`
  (actor/proxy).
- Display/vehicle/P1-host rows downgraded to `UNTESTED` (were PASS A/B):
  9 Kogane, 10 Wealthy, 11 Fart, 12 UjiA, 13 UjiB, 16 Qurione, 18 MaroFrog,
  23 Sarai, 24 Tank, 28 ElecBug, 30 Queen, 32 Demon, 40 OoPanModoki, 41 Fuefuki,
  53 KingChappy, 56 Damagumo, 58 BombSarai, 66 Houdai, 69 BigFoot, 73 BigTreasure,
  75/95/96 Kabuto family, 78 MiniHoudai, 99 BlackMan.
- Partial/policy/variant fixes: 55 Hanachirashi (movement PARTIAL -> UNTESTED),
  72 OniKurage (only identity auto-bind natural; B/C/D -> UNTESTED),
  101 UmiMushiBlind (only bite natural; A/B -> UNTESTED),
  68 Tamago (Astonish/flick natural -> attacks_receivers PASS).

### Candidate six-gate blocks added (item 3)

2/17/45/54 all UNTESTED; 15 Armor and 79 Sokkuri A/B/C PASS (NATIVE natural) +
D/E/F UNTESTED; 44 BlueKochappy A PASS, B/C/D/E UNTESTED, cleanup BLOCKED.

### Audit + test changes (items 4-5)

- `main(argv=None)` so the CLI is directly callable; added
  `test_audit_review_exits_zero_on_real_ledger` and
  `test_audit_review_exits_one_on_missing_cited_doc` (temp overlay + monkeypatch).
- Added `test_shared_modules_subset_of_native_modules` (SHARED_MODULES and
  MODULE_ALIASES values <= native_modules(ENGINE_PORT)); made the `_gaps` helper
  build `modules` inside instead of as an import-time default.

### Result

```
128 passed, 17 subtests passed (roster/coverage/seed/placement/enemy suites)
py -3.12 scripts/audit_pikmin2_roster.py --review  # exit 0, ledger coverage complete: True, admitted 0
```

### Subagent lesson (item 6)

The slice-2 transcription errors came from accepting explore #2's doc table
without re-checking each PASS against a natural-vs-injected test. For this fix I
did not re-delegate the transcription; I re-derived every PASS gate myself against
the rule and added a check to the fix script (a PASS whose notes carry
inject/proxy/fixture/vehicle/visual/host/display is flagged). Future delegated
doc-audit output will be gated the same way before transcription.

## Slice 3

Third bounded slice: **first real admission chain, deny-by-default preserved**
(root-side; no native build required; no identity admitted).

### Deliverable

A documented, tested **admission contract** in `experimental/pikmin2_enemy_roster.py`
that admits an identity ONLY when its ledger row proves the full chain:

- natural PASS on `identity_spawn`, `movement_animation`, `attacks_receivers`,
  `death_corpse`, `cleanup_reentry` (gates 1-4 + 6), AND
- a cited `delivery_receipt` for `transport_reward` (gate 5) — a durable
  receipt citation, not a gate status.

API added:
- `ADMISSION_GATES` — the five natural-PASS gates.
- `RosterEntry.delivery_receipt` (`str | None`) + parsed from the overlay.
- `admission_requirements(entry)` — exact missing gates (or `[]`).
- `admission_contract(roster)` -> `{"admitted": [...], "blocking": {id: [missing]}}`.
- `admitted_ids` / `require_admitted` / `admission_set` now derive from the contract.
- `write_admission(roster, path)` persists `eligibility:"admitted"` (or demotes a
  stale `admitted` to `candidate`) into the evidence JSON lane 03 reads; it only
  mutates existing rows, never fabricates a row for an identity with no overlay.
- `validate_roster` rejects a hand-edited `eligibility:"admitted"` whose contract
  is unsatisfied, naming the exact gap.
- `scripts/audit_pikmin2_roster.py --admit` prints the admitted set + per-candidate
  blocking gates; `--write-admission` commits them.

### Files

- `experimental/pikmin2_enemy_roster.py`, `docs/PIKMIN2_ENEMY_ROSTER.md`,
  `docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` (delivery_receipt field doc),
  `scripts/audit_pikmin2_roster.py`, `tests/test_pikmin2_enemy_roster.py`
  (updated synthetic admitted tests), `tests/test_pikmin2_admission_contract.py` (new, 9 tests).

### Result

```
py -3.12 -m pytest <roster/admission/coverage/seed/placement/enemy suites> -q   # 137 passed, 17 subtests
py -3.12 scripts/audit_pikmin2_roster.py --review                              # exit 0 (coverage complete)
py -3.12 scripts/audit_pikmin2_roster.py --admit                               # admitted [], 64 candidates blocked w/ exact gates
admitted_ids(load_and_validate()) == []                                        # nothing admitted today (correct)
```

No real identity is admitted: the closest rows (Sokkuri 79 / Armor 15) still miss
`death_corpse`, `cleanup_reentry` and `transport_reward` (no durable Onion/AP
receipt exists per lane 06 ordinary-vs-Pod split).

### Assumptions / notes

- "Roster JSON lane 03 reads" === the evidence overlay read through
  `admitted_ids()`; `write_admission` writes `eligibility` there.
- Gate 5 is gated by `delivery_receipt` (a citation), not a `PASS` status, because
  the only `transport_reward: PASS` today (Shijimi 77) is an in-place nectar
  reward marker, not real transport; the ordinary surface is still unwired
  (PIKMIN2_REWARD_RECEIPTS.md).
- `admission_set` keeps its category/raise shape (candidates/excluded/denied from
  eligibility, `.admitted` from the contract) so lane 03's fail-closed reads are unchanged.

### Subagent usage

- `explore` #1 (admitted-set read-path consumers): used as-is; confirmed only lane 03's
  seed bridge + `seed.py` + audit `summarize` read `admitted_ids`, so deriving it
  from the contract is safe; produced the exact test list to update.
- `explore` #2 (delivery-receipt concept): used as-is; pinned the ordinary-vs-Pod
  receipt split and confirmed no identity has a real delivery receipt today, which
  shaped `delivery_receipt` as a citation (not a status).
- `general` #3 (contract tests): used nearly as-is; 9 tests landed and pass; I only
  corrected `write_admission` so the merge path never fabricates rows (the empty
  placeholder-row regression I caught when running `--write-admission`).
  Net: all three materially shortened the read-heavy work; the general agent's
  scaffold was kept and only lightly corrected.

## Fix 3

Review corrections to slice 3 (items 1-6; deny-by-default still holds, still no
identity admitted).

### API note (item 6)

The brief described the admission entry point as `admit(identity, evidence_row)`;
the delivered API is `admission_contract(roster)` (whole-ledger) plus
`admission_requirements(entry)` (single-identity gap report); the write side is
`write_admission(roster, path)`, with `admitted_ids`/`require_admitted` deriving
from the contract.

### Changes

- `--admit-check <id>` (int, repeatable) added to the audit: prints
  `admission_requirements(entry)` (or `["role"]`/`["excluded"]`/`["unknown"]`) and
  exits 1 when any checked id is blocked.
- `admission_requirements` now *enforces* natural PASS instead of assuming it:
  a PASS whose row notes/eligibility_reason match
  `inject|proxy|fixture-only|forced|vehicle|visual|host|display` is refused as
  `<gate>:injected`; the recipient probe (Sokkuri all-PASS + injected notes +
  `proxy: forced Onion suck` receipt) blocks instead of admitting.
- `delivery_receipt` is validated by shape: blank -> `transport_reward`, arbitrary
  string -> `transport_reward:invalid_receipt`; only an `onion:`/`corpse:`/`receipt:`
  key or a doc/log citation currently admits.
- Added module constants `NONNATURAL_MARKERS`, `RECEIPT_KEY_PREFIXES`,
  `RECEIPT_CITATION_MARKERS`, `EVIDENCE_FIELDS`.
- `write_admission` fresh path now copies the `EVIDENCE_FIELDS` schema block and
  the merge path drops the no-op `eligibility = entry.eligibility` rewrite.
- Removed the scaffold "does not exist yet" note from the admission-contract test
  docstring.

### Tests behind the 143

`tests/test_pikmin2_admission_contract.py` (15), `tests/test_pikmin2_enemy_roster.py`
(21), `tests/test_pikmin2_roster_coverage.py` (14), `tests/test_pikmin2_roster.py`
(3), `tests/test_pikmin2_seed_bridge.py` (16), `tests/test_pikmin2_seed_generation.py`
(~9), `tests/test_p2_placement.py`, `tests/test_enemy_layout.py`,
`tests/test_enemy_slots.py`, `tests/test_pikmin2_enemy.py` — 143 passed, 17 subtests,
plus `scripts/audit_pikmin2_roster.py --review` exit 0 and `--admit` `[]`.

```
py -3.12 scripts/audit_pikmin2_roster.py --admit-check 79   # ['death_corpse','cleanup_reentry','transport_reward'], exit 1
py -3.12 scripts/audit_pikmin2_roster.py --admit-check 0    # ['role'], exit 1
py -3.12 scripts/audit_pikmin2_roster.py --admit-check 99999# ['unknown'], exit 1
```

## Slice 4

Fourth bounded slice: **the admission contract gating a real seed** (root-side;
no native build; no identity admitted; deny-by-default preserved end-to-end).

### What was already wired vs. what this slice did

`admitted_ids` was made contract-derived in slice 3 (`admission_contract` ->
`admission_requirements(entry) == []` plus a `source`/`variant` role and not
`excluded`). Lane 03's seed bridge and the schema-9 generator already read that
same `admitted_ids` for the product path:

- `experimental/pikmin2_seed_bridge.resolve_admitted_layout()` derives its cohort
  from `admitted_ids(roster)` and fails closed when it is empty.
- `resolve_placement_layout()` (the `generate(..., p2_enemies=True)` entry) and
  `randomizer.seed.validate()` (loaded-seed re-validation) both re-derive the
  admitted cohort via `admitted_ids(roster)`.

So the "seedable P2 identity pool lane 03's bridge reads" was already the
admission contract through the evidence file (`docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json`);
no lane 03 file edit was needed. Slice 4 *verifies* that gate end-to-end and pins
it with a seed-pool test on a synthetic ledger, because nothing previously proved
an identity passed into an actual generated `p2_layout` only on the contract (the
existing seed-generation tests injected a fake `admitted_ids` via monkeypatch).

### Deliverable (exact command)

```
py -3.12 scripts/audit_pikmin2_roster.py --admit
```

prints `admission contract: admitted []` followed by the exact per-candidate
blocking gates for all 64 candidates (e.g. `Armor (15):
blocking=death_corpse,cleanup_reentry,transport_reward`, `Sokkuri (79):
blocking=death_corpse,cleanup_reentry,transport_reward`, and `BlueKochappy (44):
blocking=identity_spawn:injected,...`).

A seed on the current ledger is actually generated with:

```
py -3.12 -c "from randomizer.seed import generate; from tests.test_pikmin2_seed_generation import placement_document; generate('s', p2_enemies=True, p2_placement=placement_document())"
```

which fails closed, verbatim:

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "…\randomizer\seed.py", line 209, in generate
    result['p2_layout'] = resolve_placement_layout(result['seed'], slot, p2_placement, load_and_validate())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "…\experimental\pikmin2_seed_bridge.py", line 157, in resolve_placement_layout
    raise SeedBridgeError(
experimental.pikmin2_seed_bridge.SeedBridgeError: no admitted P2 identities; refusing to seed an unadmitted pool (lane 02 admission set is empty)
```

That is the exact set the admission report prints: `generate` ->
`resolve_placement_layout` derives its cohort from `admitted_ids`
(contract-derived), so deny-by-default is enforced at the real seed path.

### Files

- `tests/test_pikmin2_admission_seed.py` (new, 4 tests).

No source/scripts/docs/JSON edits and no native commit: the wiring is verified,
not re-implemented.

### The tests

Synthetic two-source ledger (Frog=17 fully passed, Snek=41 with `death_corpse`
open), built solely via `parse_enum_header`/`parse_info_table`/`build_entries`/
`resolve_ids`/`snapshot_payload`/`entries_from_payload`:

- `test_fully_passed_identity_is_the_whole_seed_pool` — Frog's natural PASS on
  gates 1-4 + 6 plus a `corpse:` receipt makes `admitted_ids == [17]`; the real
  seed path (`resolve_placement_layout` against a Frog-accepting lane-04 document)
  binds only Frog (every binding `source_id == 17`).
- `test_partial_sibling_never_reaches_the_seed_pool` — Snek (41) is blocked on
  `death_corpse` and never appears in `admitted_ids`.
- `test_stripping_receipt_drops_identity_from_seed_pool` — with Frog's
  `delivery_receipt` removed, `admitted_ids == []` and gate 5 is reported as
  `transport_reward`; `resolve_placement_layout` raises `SeedBridgeError` (fails
  closed).
- `test_real_ledger_seed_pool_is_deny_by_default` — `admitted_ids(load_and_validate())
  == []` and `generate("seed", p2_enemies=True, p2_placement=...)` raises
  `SeedBridgeError` (no monkeypatch).

### Tests run

```
py -3.12 -m pytest tests/test_pikmin2_admission_seed.py -q                                             # 4 passed
py -3.12 -m pytest tests/test_pikmin2_admission_seed.py tests/test_pikmin2_admission_contract.py \
    tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py \
    tests/test_pikmin2_roster.py tests/test_pikmin2_roster_coverage.py -q                             # 86 passed
py -3.12 scripts/audit_pikmin2_roster.py --admit                                                       # admitted [] + per-candidate gates
```

### Build / fixture evidence

Not applicable: this is a root-side ledger/seed-gate slice with no native C++
change, so no `build_lane.py` queue and no real-GL fixture were run (lane 02
roster/admission is a schema/tooling lane; gameplay gates remain lane 13 +
providers). No `l02-build-evidence.txt` is claimed.

### Six-gate table

| Gate | Status | Note |
|---|---|---|
| identity_spawn | natural-PASS *required* (ledger) | refused as `<gate>:injected` on proxy/vehicle/injected rows |
| movement_animation | natural-PASS *required* (ledger) | same |
| attacks_receivers | natural-PASS *required* (ledger) | same |
| death_corpse | natural-PASS *required* (ledger) | closest rows (Armor 15, Sokkuri 79) still UNTESTED |
| transport_reward | cited `delivery_receipt` required | no durable Onion/corpse receipt exists today (lane 06) |
| cleanup_reentry | natural-PASS *required* (ledger) | nothing admitted |

Gate 2/4/5/6 runtime gameplay still belongs to family lanes, not lane 02.

### Assumptions

- The "seedable P2 identity pool" is the `p2_layout` binding cohort, which lane
  03's bridge derives from `admitted_ids`; that derivation was already present in
  the base and was made contract-gated in slice 3, so slice 4 adds a proof/test
  rather than new wiring.
- "One exact command" is the audit `--admit` line above; it is the admission
  evaluation the seed path consumes.
- No identity is admitted; the ledger stays deny-by-default until a family
  supplies the full generated-session chain (lane 13 + providers 03/04/05/06/07/08).

### Remaining blockers (named provider lane)

- Nothing is admitted because no identity yet has natural PASS on death/corpse +
  cleanup/re-entry and a durable transport receipt; that is lane 13/03/06, not
  lane 02.

### Subagent usage

The `task` tool was not available in this execution environment (the agent's tool
set has no subagent spawner), so the three read-heavy tasks from the brief were
done inline with direct file/grep passes instead of delegated:

1. *Source audit* (would-be `explore` #1): traced the seed-bridge read path
   (`grep admitted_ids/resolve_admitted_layout/resolve_placement_layout`) to
   confirm `generate`/`validate` consume contract-derived `admitted_ids`.
2. *Existing-candidate inventory* (would-be `explore` #2): confirmed there was no
   test that pushed a natural synthetic-ledger identity all the way into a
   `p2_layout` (existing seed tests monkeypatch `admitted_ids`).
3. *Tests/harness* (would-be `general` #3): wrote `tests/test_pikmin2_admission_seed.py`
   and ran it.

Net: no time saved versus delegating, but also no reconcilation rework; honest
negative result on the subagent experiment for this lane.

## Fix 4

Review corrections to slice 4 (items 1-6; root-side, still no identity admitted).

### Test path now drives the real seed entry

The three seed-pool assertions drove `resolve_admitted_layout`, which no product
code calls. They now drive the real path `randomizer.seed.generate` ->
`experimental.pikmin2_seed_bridge.resolve_placement_layout` (where
deny-by-default is enforced at `seed_bridge.py` lines 155-159):

- `tests/test_pikmin2_admission_seed.py` `resolve_admitted_layout` calls replaced
  with `resolve_placement_layout(seed, slot, placement_document_accepting_frog(), roster)`;
  added a local `placement_document_accepting_frog()` (same shape as
  `tests/test_pikmin2_seed_generation.py::placement_document`, identity `Frog`).
- `test_real_ledger_seed_pool_is_deny_by_default` now calls
  `generate("seed", p2_enemies=True, p2_placement=placement_document_accepting_frog())`
  with no monkeypatch and expects `SeedBridgeError` (a `ValueError` subclass).
- Fixed the `Froghas` -> `Frog has` typo.

### Deliverable command actually generates a seed

The "exact command" now pastes a real seed-generation call and its verbatim
`SeedBridgeError` output (see the Slice 4 "Deliverable" section), and the
`cd <lane-path> &&` prefix was dropped there and in the slice-1 reproduction
command (no lane paths in docs).

### Lane 03 ask (not edited here)

`experimental/pikmin2_seed_bridge.py` lines 91-93 label `resolve_admitted_layout`
"the product entry point", which contradicts `randomizer/seed.py` lines 202-204
(the product path calls `resolve_placement_layout`). Lane 03 owns that docstring;
please reword it (or mark `resolve_admitted_layout` as the legacy/diagnostic
entry). No lane 03 file was edited in this fix.

### Tests run

```
py -3.12 -m pytest tests/test_pikmin2_admission_seed.py -q                                            # 4 passed
py -3.12 -m pytest tests/test_pikmin2_admission_seed.py tests/test_pikmin2_admission_contract.py \
    tests/test_pikmin2_enemy_roster.py tests/test_pikmin2_seed_bridge.py tests/test_pikmin2_seed_generation.py \
    tests/test_pikmin2_roster.py tests/test_pikmin2_roster_coverage.py -q                            # 86 passed
py -3.12 -m pytest tests/test_pikmin2_seed_generation.py -q                                          # 9 passed (unchanged)
```

### Subagent usage

The `task` tool is still not present in this session's tool set (only
`bash`/`read`/`grep`/`glob`/`edit`/`write`/`web*`), so no subagents ran; the
read-heavy work was again done inline. One line: task tool genuinely absent.

## Slice 5

Fifth bounded slice: **evidence ingestion from lane handoffs into the ledger**
(root-side; no native build; no identity admitted).

### Deliverable

`scripts/ingest_p2_handoff_gates.py` parses a family lane's six-gate table out of
its `docs/PIKMIN2_LANE<NN>_DEEPSEEK_HANDOFF.md`, normalizes each row to the lane-02
status vocabulary, and runs the result through `admission_requirements`; it prints,
per identity, the gates a handoff *would advance* and the gates that *remain
blocking*. It writes nothing unless `--apply` is given, and refuses any PASS that
is labelled injected/proxy (reusing `NONNATURAL_MARKERS`) or uncited (reusing
`RECEIPT_CITATION_MARKERS` / the receipt shape). `--apply` merges only gate
PASS values into existing evidence rows — it never fabricates a row and never
touches `eligibility` or `delivery_receipt`, so a handoff cannot admit anyone.

The table format lanes must follow is documented in `docs/PIKMIN2_ENEMY_ROSTER.md`
(new "Family-lane six-gate handoff table (ingest contract)" section); the parser
is the contract.

### Files

- `scripts/ingest_p2_handoff_gates.py` (new).
- `tests/test_pikmin2_handoff_ingest.py` (new, 7 tests).
- `docs/PIKMIN2_ENEMY_ROSTER.md` (table-format contract).

### Real-handoff run (lanes 29, 31, 22)

Read via `git show claude/p2-deepseek-wave:docs/PIKMIN2_LANE<NN>_DEEPSEEK_HANDOFF.md`:

```
# LANE29.md
57 Kurage (role=source):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
72 OniKurage (role=source):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
# LANE31.md
98 Tyre (role=helper): skipped (non-seedable role)
99 BlackMan (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, cleanup_reentry:uncited, death_corpse:uncited, identity_spawn:injected, movement_animation:injected
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
# LANE22.md
59 FireOtakara (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, identity_spawn:uncited, movement_animation:uncited
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
60 WaterOtakara (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, identity_spawn:uncited, movement_animation:uncited
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
61 GasOtakara (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, identity_spawn:uncited, movement_animation:uncited
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
62 ElecOtakara (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, identity_spawn:uncited, movement_animation:uncited
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
93 BombOtakara (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, identity_spawn:uncited, movement_animation:uncited
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
```

Reading: lane 29 reports only PARTIAL/BLOCKED/N-A rows, so nothing advances; lane 31
labels its identity-spawn and movement as "Injected placement"/"host-driven route"
(refused as injected) and cites native log markers rather than doc/log files for the
other three (refused as uncited); lane 22's PASSes cite log markers too (uncited).
No identity is admitted anywhere, and `--apply` on these handoffs is a no-op
(nothing advances).

### Tests run

```
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py -q                                             # 7 passed
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py tests/test_pikmin2_admission_seed.py \
    tests/test_pikmin2_admission_contract.py tests/test_pikmin2_enemy_roster.py \
    tests/test_pikmin2_roster_coverage.py -q                                                          # 60 passed
py -3.12 scripts/ingest_p2_handoff_gates.py <lane29 lane31 lane22 handoff files>                       # pasted above
```

### Assumptions / notes

- A gate PASS is "cited" only when the Evidence cell carries a `docs/PIKMIN2_*.md`
  / `.log` / `.txt` / `.json` filename or a file path (the `/`/`\` markers of
  `RECEIPT_CITATION_MARKERS` only count between non-space segments, so a
  "frame=12 / frame=20" event clock is not a citation). Native log *markers*
  (`P2_*`) are evidence but not a durable citation; lanes should cite the doc/log
  file that records them.
- Injected detection reuses `NONNATURAL_MARKERS` as-is, so "host-driven route"
  (lane 31) reads as injected via the `host` marker. That is the same over-broad
  rule `admission_requirements` applies; it errs toward denying, which is the
  safe direction for an ingest gate.
- The gate table is applied to every seedable (`source`/`variant`) identity named
  in the handoff; helpers (`Tyre` 98) are reported as skipped, and a handoff
  naming several siblings (lane 22) gets the same table on each lead identity.
- `--apply` persists gate PASSes only; transport/reward receipts and eligibility
  remain manual, so deny-by-default survives ingestion.

### Remaining blockers (named provider lane)

- Still nothing admits: the ingested handoffs are partial or cite no durable doc/log.
  Natural receipt + full gate evidence stays with the family lanes (13/16/29/31/etc.)
  and reward/persistence with lane 06/07; lane 02 only transcribes.

## Fix 5

Review corrections to slice 5 (items 1-8; blocking items 1-2 applied). The
parser now refuses every injected/unevidenced PASS and scopes a gate table to a
single owning identity, so nothing leaks to the ledger under `--apply`.

- Non-natural markers are now searched across `Result + label + Evidence`, not
  just `Result`+`label` (`_gate_verdict`). A plain `PASS` whose evidence says
  "forced health write" is refused as `<gate>:injected`. Covered by
  `test_plain_pass_with_injected_evidence_marker_is_refused`.
- A gate table is bound to the identity named in the nearest preceding "Source ID"
  line (or identity-naming heading). Siblings named in the handoff but without
  their own table are printed `(shared table, excluded)` (all gates `UNTESTED`)
  and are never applied. Covered by
  `test_multi_identity_binds_table_to_named_owner_only`.
- `--apply` additionally skips `shared` rows (`apply_ingested_gates`).
- Citation detection is now an extension at a token boundary
  (`\S+\.(md|log|txt|json)\b`) or a path rooted at `docs/`/`output/`/`tests/` with
  at least two segments; a bare `12/16` no longer counts.
- `_status_token` matches `^(PASS|PARTIAL|FAIL|BLOCKED|UNTESTED|N/A)\b` at the
  start of the stripped Result cell, so `FAIL (was PASS earlier)` -> `FAIL` and
  `BYPASSED` -> `UNTESTED`. Covered by `test_status_token_is_start_anchored`.
- `_split_row` splits on `(?<!\)\|` and unescapes `\|`, so lane 22's
  `key=dweevil\|FireOtakara` no longer truncates the Evidence cell. Covered by
  `test_escaped_pipe_is_not_a_cell_boundary`.
- `docs/PIKMIN2_ENEMY_ROSTER.md` contract updated for all of the above.

Corrected real-handoff run (paste):

```
# LANE29.md
57 Kurage (role=source):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
72 OniKurage (role=source) (shared table, excluded):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
# LANE31.md
98 Tyre (role=helper): skipped (non-seedable role)
99 BlackMan (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, cleanup_reentry:uncited, death_corpse:uncited, identity_spawn:injected, movement_animation:injected
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
# LANE22.md
59 FireOtakara (role=source):
  advances: (none)
  refused PASS: attacks_receivers:uncited, identity_spawn:uncited, movement_animation:uncited
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
60 WaterOtakara (role=source) (shared table, excluded):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
61 GasOtakara (role=source) (shared table, excluded):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
62 ElecOtakara (role=source) (shared table, excluded):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
93 BombOtakara (role=source) (shared table, excluded):
  advances: (none)
  blocking (admission_requirements): identity_spawn, movement_animation, attacks_receivers, death_corpse, cleanup_reentry, transport_reward
```

The lane-22 siblings (60/61/62/93) no longer inherit FireOtakara's table: they
are `shared table, excluded` and `--apply` cannot touch them. Nothing admits, and
`--apply` remains a no-op on all three real handoffs.

### Tests run

```
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py -q                                             # 11 passed
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py tests/test_pikmin2_admission_seed.py \
    tests/test_pikmin2_admission_contract.py tests/test_pikmin2_enemy_roster.py \
    tests/test_pikmin2_roster_coverage.py -q                                                          # 64 passed
py -3.12 scripts/ingest_p2_handoff_gates.py <lane29 lane31 lane22 handoff files>                       # pasted above
```

## Slice 6

Sixth bounded slice: **the wave-wide dry-run advance report** (root-side; no
native build; no identity admitted; deny-by-default holds wave-wide).

### Advisory fixes (folded in, each with a test)

- `_owner_from_line` now accepts the `Name (NN)` form (roster-filtered via
  `_NAME_PAREN_RE`), so a table under `## WaterOtakara (60)` binds 60.
- The bound-table walk-back loop itself is unchanged (it already stops at the
  nearest identity-naming heading or "Source ID" line and skips non-naming
  headings); the `Name (NN)` fix above is what now resolves that heading, so it
  is no longer skipped. `test_table_binds_to_nearest_identity_heading` renders
  this behavior.
- `_PLAIN_PATH_RE` now requires a known root plus one segment (two segments
  counting the root), matching the doc; a bare `12/16` still does not count.
- Bonus for the wave-wide run: `_extract_gate_table` accepts a `Status` column
  as the result column (lanes 27/28 use `| Gate | Status | ... |`), and
  `build_advance_report` only marks an identity `shared` when *no* handoff binds
  a table for it.

Tests added: `test_citation_requires_extension_or_known_root_path`,
`test_table_binds_to_nearest_identity_heading`,
`test_report_generator_is_deterministic`.

### Report generator + exact command

`scripts/generate_p2_advance_report.py` reads every
`docs/PIKMIN2_LANE<NN>_DEEPSEEK_HANDOFF.md` from `claude/p2-deepseek-wave` (via
`git ls-tree`/`git show`), dry-runs the ingestion against the committed roster,
and writes `docs/PIKMIN2_ROSTER_ADVANCE_REPORT.md`. Lane 01 / the integrator
re-run it after each merge so the report tracks the wave:

```
py -3.12 scripts/generate_p2_advance_report.py
```

The generator is deterministic (byte-identical on repeat runs; covered by the
determinism test on synthetic handoffs).

### Report result (current wave)

15 seedable (`source`/`variant`) identities named across the lane handoffs; none
advance a single gate:

```
| Gates away from admission | Identities |
|---:|---:|
| 0..5 | 0 |
| 6    | 15 |
```

Per identity the report lists the gates the handoff(s) would advance, the PASSes
refused (`uncited` / `injected`) and the blocking gates. 15 identities remain 6
gates away; 0 are admitted. Notables: FireOtakara (59) gates 1-3 are refused
`uncited`, BlackMan (99) refused `identity_spawn:injected`/`movement_animation:injected`,
Hana (84) refused `attacks_receivers:injected`; several identities (Armor 15,
Sokkuri 79, the Otakara siblings) are `shared table, excluded`.

### Assumptions / notes

- The wave-wide run confirms the downstream note from fix 5: FireOtakara's gates
  1-3 no longer advance because their Evidence cells cite bare `P2_*` log lines
  rather than doc/log files — the intended data-quality outcome.
- Owner binding covers the "Source ID"/"Source enemy ID"/"Concrete source ID"
  lines and identity-naming headings. Two lanes phrase their owner differently
  ("Source IDs owned / inspected: Sokkuri 79" with a bare number, and
  "Source enemy: ... EnemyID 41" with no `id` token); those identities report
  `shared table, excluded` — benign and deny-safe under-attribution, since none
  of their PASSes would advance anyway. Recorded here for lane 01, not chased in
  this slice.

### Tests run

```
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py -q                                             # 14 passed
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py tests/test_pikmin2_admission_seed.py \
    tests/test_pikmin2_admission_contract.py tests/test_pikmin2_enemy_roster.py \
    tests/test_pikmin2_roster_coverage.py tests/test_pikmin2_seed_bridge.py \
    tests/test_pikmin2_seed_generation.py -q                                                          # 100 passed
py -3.12 scripts/generate_p2_advance_report.py                                                         # writes docs/PIKMIN2_ROSTER_ADVANCE_REPORT.md (deterministic)
```

### Subagent usage

The `task` tool remains absent from this session's tool set, so slice 6 was done
solo (direct file/git reads); no subagent results to reconcile.

## Fix 6

Review corrections to slice 6 (items 1-5; report coverage claim was wrong).

- `parse_identities` now accepts the roster-filtered `Name NN` ("DangoMushi 94",
  "Houdai 66", "Kabuto 75, Rkabuto 95, Fkabuto 96") and `NN Name` ("73
  BigTreasure") forms, plus `enemy NN`/`enemy ID NN` ("enemy 30", "enemy 53"),
  "source id NN" ("source id **44**") and "P2 id NN" ("P2 id 72"). 24 of 26
  handoffs now yield at least one identity; lanes 03 ("source 45/44" slash pair)
  and 11 (Bulbmin is the P1 `species 5`, not a P2 roster id) report `(none)`.
  Covered by `test_identity_parse_accepts_cited_real_forms`.
- The report now carries a `## Handoffs read` section (handoff -> identities
  found, or `(none)`), so gaps are visible; the determinism test asserts every
  input label appears and `shared is False`.
- `_split_row` is a proper tokeniser: a backslash escapes exactly one character,
  so `\|` is a literal pipe and `\\|` is a literal backslash + separator. Covered
  by `test_double_backslash_before_pipe_is_a_separator`.
- Flip tests added for the `Status` column (`test_status_column_is_accepted_as_result`)
  and the shared-only-when-no-handoff-binds rule
  (`test_shared_flag_is_false_when_any_handoff_binds`).
- `scripts/generate_p2_advance_report.py` runs `git` with `cwd=ROOT` and passes
  `--branch` through (the rendered command and header now carry the branch).

Per-lane citation note: every identity stays 6 gates away because PASS
rows are `uncited` (Evidence cites a bare `P2_*` log marker, not a doc/log file)
or `shared`. The integrator can tell each lane to add the citation its PASS rows
need — a `docs/PIKMIN2_*.md` / `.log` / `.txt` / `.json` filename or a
`docs/`/`output/`/`tests/` path in the Evidence cell:

| Lane | Identity | Gates refused `uncited` (would advance on citation) |
|---|---|---|
| 22 | FireOtakara 59 | identity_spawn, movement_animation, attacks_receivers |
| 31 | BlackMan 99 | attacks_receivers, death_corpse, cleanup_reentry |
| 08 | Hana 84 | identity_spawn, movement_animation |
| 14 | Sokkuri 79 | identity_spawn, movement_animation, cleanup_reentry |
| 26 | Houdai 66 | identity_spawn, attacks_receivers, cleanup_reentry |
| 32 | BigTreasure 73 | movement_animation |
| 20 | Kabuto 75 | identity_spawn, attacks_receivers, cleanup_reentry |
| 25 | DangoMushi 94 | identity_spawn, movement_animation |
| 17 | Kogane 9 | identity_spawn, movement_animation, death_corpse, cleanup_reentry |

For each, cite the lane's recorded natural run (e.g. the `output/<lane>/...` log
or the lane's `docs/PIKMIN2_*` evidence doc) instead of the bare marker, e.g.
`docs/PIKMIN2_DWEEVIL_NATIVE.md` / `.../dweevil-run.stdout.txt`.

### Tests run

```
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py -q                                             # 18 passed
py -3.12 -m pytest <roster / admission / seed suites> -q                                              # 104 passed
py -3.12 scripts/generate_p2_advance_report.py --branch claude/p2-deepseek-wave                          # deterministic
```

### Subagent usage

The `task` tool is still absent; fix 6 was done solo.

## Fix 7

Review corrections to fix 6 (identity regexes conjured phantom identities; solo).

- `parse_identities` / `_owner_from_line` now require
  `by_name[name].source_id == sid` for every name form (`Name NN`, `NN Name`,
  `Name (N)`, `NN`Name``), so a number that does not belong to the named identity
  is dropped instead of renaming the entry that owns that number. `_bound_tables`
  passes `by_name` as a name->entry dict (was a name set).
- The leading `\b` on those forms is now `(?<![\w/-])`, so `-`/`/` no longer
  detach a number (`batch-2 Chappy`, `wave/3 Frog`).
- `_SOURCE_ID_RE` (and `_ID_ENUM_RE` in `_owner_from_line`) are roster-filtered:
  a bare `source_id`/`EnemyID` number that is not a roster source id (e.g. a spawn
  uid `219002`) no longer parses as an identity.
- Flip tests: "54 Queen poses", "batch-2 Chappy host", "Pikmin 2 Frog",
  "tick 80 Kogane", "wave/3 Frog" -> `[]` (plus the pre-existing real-form cases
  still pass).
- Regenerated `docs/PIKMIN2_ROSTER_ADVANCE_REPORT.md`: seedable count 52 -> 50;
  phantoms "54 Miulin" (L09) and "2 Chappy" (L23, now `(none)`) removed.
- Handoff typos: `\|` separator wording and "item 8" -> "note".

```
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py -q                 # 19 passed
py -3.12 -m pytest <handoff/admission/roster/seed/placement suites> -q     # 159 passed, 17 subtests
py -3.12 scripts/generate_p2_advance_report.py --branch claude/p2-deepseek-wave  # deterministic, seedable 50
```

## Slice 7

Bounded slice (solo): **make the citation gap actionable and checkable.**

### Deliverables

- `scripts/check_p2_handoff_gates.py` — checks one handoff doc and prints, per
  gate row, `accepted` (cited natural PASS), `refused` (`uncited` / `injected` /
  `shared table` / `bad status`) or `ignored`, with the exact edit for each refused
  row; exits 1 when any PASS row is refused, 2 on a missing file.
- `docs/PIKMIN2_ENEMY_ROSTER.md` — new 'Paste-able gate table template' block with
  the citation regex and a natural-PASS example row plus an injected row.
- Per-lane action list below (run over every merged handoff on
  `claude/p2-deepseek-wave`); the integrator can forward these row edits to the lanes.
- Tests: `tests/test_pikmin2_handoff_ingest.py` gains the checker on the two
  synthetic handoffs, CLI exit codes and a bad-status flip.

### Fix legend (what a refused row needs)

- `uncited` -> add a citation to the Evidence cell: a `.md`/`.log`/`.txt`/`.json`
  token or a `docs/`·`output/`·`tests/` path; for `transport_reward`, an
  `onion:`/`corpse:`/`receipt:` key.
- `injected` -> mark `Injected vs natural = injected` and set Result `UNTESTED`,
  or supply a natural citation (an injected PASS never advances).
- `bad status` -> begin the Result cell with
  `PASS`/`PARTIAL`/`FAIL`/`BLOCKED`/`UNTESTED`/`N/A`.
- `shared` -> give the identity its own `Source ID` line + six-gate table (its
  PASS rows are currently attributed to another identity), or drop it from the
  handoff's identity list when it is genuinely out of scope.

The `shared` rows are mostly lanes mentioning sibling identities without claiming
a table for them (e.g. lane 02 names the whole roster); the *citation* gap to fix
is the `uncited`/`injected`/`bad status` rows on the identities that already have
a table:

| Lane | Refused rows (identity: gate:reason …; shared: named-no-table) |
|---|---|
| 02 | shared: 2 Chappy, 9 Kogane, 10 Wealthy, 11 Fart, 12 UjiA, 13 UjiB, 15 Armor, 16 Qurione, 18 MaroFrog, 23 Sarai, 24 Tank, 28 ElecBug, 30 Queen, 32 Demon, 40 OoPanModoki, 41 Fuefuki, 44 BlueKochappy, 45 YellowKochappy, 53 KingChappy, 54 Miulin, 55 Hanachirashi, 56 Damagumo, 57 Kurage, 58 BombSarai, 59 FireOtakara, 60 WaterOtakara, 61 GasOtakara, 62 ElecOtakara, 66 Houdai, 69 BigFoot, 72 OniKurage, 73 BigTreasure, 75 Kabuto, 78 MiniHoudai, 79 Sokkuri, 84 Hana, 93 BombOtakara, 94 DangoMushi, 95 Rkabuto, 96 Fkabuto, 99 BlackMan, 101 UmiMushiBlind |
| 04 | shared: 44 BlueKochappy, 45 YellowKochappy |
| 05 | shared: 44 BlueKochappy, 45 YellowKochappy |
| 06 | shared: 44 BlueKochappy |
| 07 | shared: 44 BlueKochappy |
| 08 | 84 Hana (identity_spawn:uncited movement_animation:uncited attacks_receivers:injected transport_reward:bad status) |
| 09 | shared: 30 Queen |
| 12 | shared: 72 OniKurage |
| 13 | shared: 44 BlueKochappy |
| 14 | 79 Sokkuri (identity_spawn:uncited movement_animation:uncited attacks_receivers:bad status death_corpse:injected cleanup_reentry:uncited)<br>shared: 15 Armor, 28 ElecBug, 65 Imomushi, 68 TamagoMushi, 84 Hana |
| 16 | shared: 17 Frog, 18 MaroFrog, 26 Catfish, 27 Tadpole, 63 Jigumo, 101 UmiMushiBlind |
| 17 | 9 Kogane (identity_spawn:uncited movement_animation:uncited attacks_receivers:injected death_corpse:uncited cleanup_reentry:uncited)<br>shared: 10 Wealthy |
| 18 | shared: 38 PanModoki |
| 20 | 75 Kabuto (identity_spawn:uncited movement_animation:bad status attacks_receivers:uncited cleanup_reentry:uncited)<br>shared: 95 Rkabuto, 96 Fkabuto, 97 FminiHoudai |
| 21 | shared: 78 MiniHoudai, 97 FminiHoudai |
| 22 | 59 FireOtakara (identity_spawn:uncited movement_animation:uncited attacks_receivers:uncited death_corpse:bad status cleanup_reentry:bad status)<br>shared: 60 WaterOtakara, 61 GasOtakara, 62 ElecOtakara, 93 BombOtakara |
| 24 | shared: 53 KingChappy |
| 25 | 94 DangoMushi (identity_spawn:uncited movement_animation:uncited attacks_receivers:injected transport_reward:bad status)<br>shared: 34 SnakeCrow, 70 SnakeWhole |
| 26 | 66 Houdai (identity_spawn:uncited attacks_receivers:uncited death_corpse:bad status cleanup_reentry:uncited)<br>shared: 56 Damagumo, 69 BigFoot |
| 27 | 58 BombSarai (identity_spawn:bad status death_corpse:bad status transport_reward:bad status) |
| 28 | shared: 41 Fuefuki |
| 29 | 57 Kurage (movement_animation:bad status attacks_receivers:bad status)<br>shared: 72 OniKurage |
| 31 | 99 BlackMan (identity_spawn:injected movement_animation:injected attacks_receivers:uncited death_corpse:uncited cleanup_reentry:uncited) |
| 32 | 73 BigTreasure (movement_animation:uncited attacks_receivers:bad status transport_reward:bad status cleanup_reentry:bad status) |
| 33 | shared: 44 BlueKochappy, 45 YellowKochappy |

### Tests

```
py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py -q                 # 23 passed
py -3.12 -m pytest <handoff/admission/roster/seed/placement suites> -q     # 166 passed, 17 subtests
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE22_DEEPSEEK_HANDOFF.md  # exit 1 (uncited/bad status)
```

## Fix 8

Review corrections to slice 7 (checker would exit 1 on every lane; solo).

- **Template** (`docs/PIKMIN2_ENEMY_ROSTER.md`): gate-6 example row is now
  `UNTESTED (injected)` (not `PASS (injected)`), and the natural rows cite
  `docs/PIKMIN2_FROG_IMPORT.md ...` instead of the `output/<lane-out>/<run>/...`
  placeholder; dropped the "at least two path segments" parenthetical.
- **Checker** (`scripts/check_p2_handoff_gates.py`):
  - `shared table` is now a *warning* (a lane naming a sibling in prose no longer
    exits 1); `had_refusal` is set only by a refused PASS row.
  - `bad status` is split: a misplaced `PASS` token is a refusal (exit 1), a
    misplaced non-PASS token (or no token) is a warning; the offending cell is
    shown via `ascii(result[:40])` (cp1252-safe) and the hint says "move `N/A` to
    the start".
  - `CITATION_HINT` reworded (no paste-able `output/<lane-out>/<run>/native.log:NNN`).
  - Cosmetic: unused `label` param dropped, needless f-string removed, `sys.stdout.flush()`
    before the stderr summary, an ASCII hyphen instead of an em-dash (cp1252-safe
    wording in both scripts).
- **Ingest** (`scripts/ingest_p2_handoff_gates.py`): `_has_citation` rejects evidence
  containing `<` or `NNN` (a pasted placeholder no longer counts); `_owner_from_line`
  now roster-filters its `_SOURCE_ID_RE` branch; em-dashes in the docstring and the
  rendered "shared table" header replaced with `-`.

### Re-run (checker)

```
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_ENEMY_ROSTER.md   # template -> exit 0 (17 Frog all accepted, gate 6 UNTESTED; 15/79 shared-warning)
L29 (Kurage/OniKurage):  exit 0  (movement/attacks "source-backed N/A" -> warning; 72 OniKurage shared-warning)
L22 (FireOtakara 59):    exit 1  (identity_spawn/movement/attacks refused:uncited; death_corpse/cleanup -> warning bad-status "Injected damage applied 135\u21920")
L31 (BlackMan 99):       exit 1  (identity_spawn/movement refused:injected; attacks/death/cleanup refused:uncited)
L26 (Houdai 66):         exit 1  (identity_spawn/attacks/cleanup refused:uncited; death_corpse refused:bad status "proxy artifact" is not a PASS)
```

`py -3.12 -m pytest tests/test_pikmin2_handoff_ingest.py -q` -> 24 passed;
full lane-02 suites -> 167 passed, 17 subtests. Advance report left at its
committed state (lane 01 regenerates after merge).

## Fix 9

The engine refresh (wave `5071d6f`) re-exported `engine/`, adding seven `pc_p2_*.cpp`
modules the ledger did not cover, which broke the coverage audit (`uncovered_identity_modules`,
`LEDGER COVERAGE FAIL`). Merged `claude/p2-deepseek-wave` (fast-forward) to reproduce.

- Added the seven modules to `SHARED_MODULES` in `scripts/audit_pikmin2_roster.py` —
  each is a sub-module or provider of an already-covered identity, never a new
  source identity, so no gate row is fabricated and deny-by-default is unchanged:

  | Module | Kind | Owning lane |
  |---|---|---|
  | `pc_p2_bigtreasure_receiver` | Titan Dweevil (73) elemental receiver sub-module | 32 |
  | `pc_p2_breadbug_contest_host` | Breadbug (38/40) contest bridge | 18 |
  | `pc_p2_groink_carcass` | Groink (78) carcass/revival | 21 |
  | `pc_p2_otakara` | Dweevil family (59-62) source FSM | 22 |
  | `pc_p2_placement_probe` | placement terrain probe (provider) | 04 |
  | `pc_p2_projectile_engine_receiver` | projectile engine receiver (primitive) | 20 |
  | `pc_p2_rock_host` | Rock (19) projectile host primitive | 20 |

- Coverage failure message now annotates each uncovered module with its owning lane
  via a new `MODULE_LANE_HINTS` table + `_lane_of_module` (mirrors the family->lane
  map in PIKMIN2_IMPLEMENTATION_FANOUT.md / PIKMIN2_LANE_COMPLETION.md), e.g.
  `identity modules without a row: ['pc_p2_x (lane 32)', ...]`.
- Added `test_lane_of_module_routes_to_owning_lane`.

Result on a `engine/` matching the wave (133 modules):

```
py -3.12 scripts/audit_pikmin2_roster.py --review                       # exit 0, ledger coverage complete: True
py -3.12 -m pytest tests/test_pikmin2_roster_coverage.py -q             # 14 passed
py -3.12 -m pytest <roster/admission/handoff/seed suites> -q            # 107 passed
```

## Fix 10

The wave engine re-export added one more `pc_p2_*.cpp` module the ledger did not
cover, which broke the coverage audit on the merged tree (`test_real_ledger_is_fully_covered`
failed with `['pc_p2_bombsarai_teki']`, `test_audit_review_exits_zero_on_real_ledger`
exit 1). No new source identity is involved.

- Source identities touched: none. `pc_p2_bombsarai_teki` is the BombSarai
  (EnemyID 58) carrier sidecar: it binds a generated P1 TEKI_Napkid vehicle and
  feeds lane 27's existing `pc_p2_bombsarai_*` policy (13-state FSM, hover, bomb
  pool, capture joint, blast) plus shared receivers. It is a family-27 submodule
  of identity 58's vehicle, covered by row 58 (`native_module pc_p2_bombsarai_fsm`),
  so it joins `SHARED_MODULES` — no gate row fabricated, deny-by-default unchanged.
- `tests/test_pikmin2_roster_coverage.py`: added `_lane_of_module("pc_p2_bombsarai_teki")
  == "27"` to the routing test, and `test_review_lists_uncovered_module_with_lane`,
  which injects a fake `pc_p2_sokkuri_probe.cpp` via a monkeypatched `ENGINE_PORT`
  and asserts `--review` exits 1 with `pc_p2_sokkuri_probe (lane 14)` in stdout.
  Tmp-dir + monkeypatch only; no lane paths, no shared state.

## Root/native pins and ordered commits (Fix 10)

- Root branch `deepseek/p2-l02`, head `5c27b950` at start; dirty: the two files below.
- Native branch `deepseek/p2-l02-native`, head `b805d9c6`, clean, no lane02 commits
  (unchanged by design — see "No native commit").

Ordered commits (root only): the Fix 10 commit below. No native commit: this slice
is entirely root-side (audit allowlist + tests). Verified
`scripts/generate_pikmin2_roster_revision.py --check` matches BOTH
`engine/pc_port/pc_randomizer_p2_roster.h` and the native worktree header, so the
roster revision constant and native bindable-ID set are unchanged. No empty native
commit created.

## Owned files / interface (Fix 10)

- `scripts/audit_pikmin2_roster.py` — one-line `SHARED_MODULES` addition
  (`pc_p2_bombsarai_teki`).
- `tests/test_pikmin2_roster_coverage.py` — routing assertion + failure-message test.
- No shared C++ hooks, no seed-bridge/ingest/report changes. Real consumer unchanged:
  lane 03 reads `admitted_ids()`; the suite proves the real pool
  `[23, 44, 59, 60, 61, 62]` flows and unadmitted stays out.

## Build / fixture evidence (Fix 10)

- No native build invoked: no C++ changed, so no shared build slot was consumed.
- No GL/runtime fixture: roster audit work involves no runtime acceptance run, so
  the 960x540 centred-window + starting-Pikmin adoption rule does not trigger;
  lane 02 claims no gameplay PASS in this slice.

## Six-gate table (Fix 10)

All six gates source-backed N/A for this slice: no enemy behavior, spawn binding,
damage, corpse, transport, or lifetime path was touched. No injected state was
introduced (the new test uses a synthetic ledger fixture and tmp files only).

## Tests run (Fix 10)

```
py -3.12 -m pytest tests/test_pikmin2_roster_coverage.py -q             # 15 passed
py -3.12 -m pytest <11 roster/admission/handoff/seed/placement files> -q  # 143 passed, 2 skipped
py -3.12 scripts/audit_pikmin2_roster.py --review                       # exit 0, coverage complete: True
```

Failure-before proof (stashed Fix 10, reran): `test_real_ledger_is_fully_covered`
failed with `['pc_p2_bombsarai_teki']` and `--review` exited 1; fix restored green.
Stash popped cleanly, no other files touched.

## Assumptions / remaining blockers (Fix 10)

- Assumes the wave's refreshed `engine/` is the input to cover; the coverage test
  plus the lane-annotated failure message is the standing guard, so the next
  refresh that adds a module fails loudly with its owning lane attached.
- No blockers from other lanes for this slice. Admission stays as the ledger
  reports it (`[23, 44, 59, 60, 61, 62]`); family evidence remains family-owned.

## Reproduction (Fix 10)

```
py -3.12 -m pytest tests/test_pikmin2_roster_coverage.py -q
```

## Subagent usage (Fix 10)

No subagents: this environment exposes no `task` tool (consistent with lane 02's
prior report that the tool is absent here), so all investigation, edits and
verification were done directly by the primary session. The read-heavy steps
(module classification from its header, audit semantics from the committed code)
were short enough that delegation would not have saved wall-clock.
