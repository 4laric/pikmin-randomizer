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
