# Canonical P2 enemy roster and eligibility ledger (lane 02, #438)

This is the per-source-ID ledger frozen by the [fan-out guide](PIKMIN2_IMPLEMENTATION_FANOUT.md)
lane 02. Lanes 03 (seed/native bridge), 04 (placement), 05 (content install) and
06 (rewards) consume this schema; family lanes attach gate evidence to it. This
document is the agreed interface; do not fork a competing representation.

## Provenance and regeneration

Numeric identities and per-enemy facts come from the projectPiki/pikmin2
decompilation, inspected read-only:

- `include/Game/enemyInfo.h` → `EnemyTypeID::EEnemyTypeID` (IDs 0–101, common names)
- `src/plugProjectYamashitaU/enemyInfo.cpp` → `Game::gEnemyInfo[]` (parent, flags,
  resource names, child birth dependency, bitter drop type)

The committed snapshot `docs/PIKMIN2_ENEMY_ROSTER.json` is **generated**; never
hand-edit it. Regenerate after the source revision changes and commit the diff:

```powershell
py -3.12 scripts/generate_pikmin2_enemy_roster.py
py -3.12 scripts/generate_pikmin2_enemy_roster.py --enemyinfo-h <path> --enemyinfo-cpp <path> --source-revision <rev>
```

The audit verifies the committed snapshot against a live checkout, cross-checks
`docs/PIKMIN2_CONTENT_INVENTORY.json` and the native modules, and can write a
machine-readable report:

```powershell
py -3.12 scripts/audit_pikmin2_roster.py --source native/pikmin2-research --output output/lane02/roster-audit.json
py -3.12 -m pytest tests/test_pikmin2_enemy_roster.py -q
```

## Snapshot schema (`p2-enemy-roster-1`)

One record per source ID, including aliases, helpers and non-spawnable bases:

| Field | Meaning |
|---|---|
| `source_id` | decomp `EnemyTypeID` (stable, 0–101) |
| `enum_name` | decomp enum suffix, e.g. `Sokkuri`, `Rkabuto` |
| `common_name` | retail English name from the header comment |
| `parent_name`/`parent_id` | manager/base identity this ID shares a bank with, or null |
| `spawnable` | `EFlag_CanBeSpawned` |
| `use_own_id` | `EFlag_UseOwnID` (distinct manager ID rather than the parent) |
| `has_no_info` | `EFlag_HasNoInfo` (not tracked in Piklopedia/bestiary) |
| `day_end_max` | day-end takeoff cap (1/2/4), else null |
| `drop_type` | `BDT_*` bitter drop tier |
| `child_name`/`child_id`/`child_count` | dependent birth (e.g. Queen→Baby×50, Kabuto→Stone×5) |
| `assets` | `model`/`anim`/`anim_mgr`/`texture`/`param`/`collision`/`stone` resource names |
| `in_info_table` | whether `gEnemyInfo[]` has a row (2 enum IDs do not) |

Classification is **computed on load**, not stored, so regeneration cannot drift:
`enemy`, `boss`, `boss_helper`, `plant`, `hazard`, `projectile`, `nest`,
`manager_base`, `non_spawnable`.

## Eligibility overlay (`p2-enemy-roster-1-evidence`)

`docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json` holds one key per source ID. Absent
identities are **denied** by default — source facts never imply gameplay PASS.

```json
{
  "schema": "p2-enemy-roster-1-evidence",
  "entries": {
    "79": {
      "native_module": "pc_p2_sokkuri",
      "owner_lane": "14",
      "gates": {"identity_spawn": "PASS", "movement_animation": "PASS", "attacks_receivers": "UNTESTED", "death_corpse": "BLOCKED", "transport_reward": "BLOCKED", "cleanup_reentry": "UNTESTED"},
      "eligibility": "candidate",
      "eligibility_reason": "native FSM present; lifecycle gates open"
    }
  }
}
```

Rules enforced by `validate_roster()`:

- `eligibility` ∈ `denied | candidate | admitted | excluded`.
- Gate keys are exactly the six arena gates; statuses ∈ `PASS | FAIL | BLOCKED | UNTESTED | N/A`.
- `admitted` requires a non-`FAIL`/non-`BLOCKED`/non-`UNTESTED` status for **all six** gates.
- Parent/child references must resolve; IDs and enum names are unique.

The six gates are `identity_spawn`, `movement_animation`, `attacks_receivers`,
`death_corpse`, `transport_reward`, `cleanup_reentry`. Family-complete and
production-eligible remain separate columns: an identity can be mechanically
complete but still `denied` for the randomizer pool until placement/content/reward
contracts (lanes 04/05/06) are satisfied.

Each row also carries a `source` list — the `docs/PIKMIN2_*.md` filenames its gate
statuses were transcribed from — with natural observations distinguished from
labeled injected/fixture observations in `notes`. An injected-only observation is
recorded as `UNTESTED`/`BLOCKED`, never as a natural `PASS`.

### Ledger coverage audit

`scripts/audit_pikmin2_roster.py --review` additionally enforces **complete ledger
coverage** and exits non-zero on any gap: every row must cite an existing source
doc and an existing native module (alias-aware), every `docs/PIKMIN2_*_NATIVE.md`
source slice must be cited (renderer/cave plumbing docs are exempt), and every
non-shared native `pc_p2_*.cpp` module must be referenced by a row (provider,
Pikmin-species, projectile/hazard primitive and family sub-modules are allowlisted
in `SHARED_MODULES`). The audit prints `ledger coverage complete: True` only when
all four gap lists are empty.


## Identity roles and aliases

`identity_role(entry)` derives, never stores, how an identity may participate:

| Role | Meaning |
|---|---|
| `source` | standalone randomizable enemy/boss with its own manager |
| `variant` | randomizable identity sharing a parent manager/base (`UmiMushi`, `UmiMushiBlind`) |
| `helper` | boss helper or dependent birth; never seeded independently (`Baby`, `Tyre`) |
| `plant`/`hazard`/`projectile`/`nest`/`manager_base`/`non_spawnable` | non-actor classification |

`resolve_alias(token, roster)` classifies a content-inventory `enemy_ids` token as
`exact`, `generator_variant` (`$N`-prefixed), `treasure_carrier`
(`Enum_suffix` carrier) or `unknown`, returning the resolved identity. A carrier
alias never becomes a new source ID.

## Admission set (deny by default)

`admission_set(roster)` materializes the explicit seedable pool referenced by the
gate ledger. An identity enters `admitted` only when the overlay sets
`eligibility: admitted` **and** its role is `source`/`variant`; a helper, plant,
hazard, projectile, nest, manager base or non-seedable alias is rejected even if
marked admitted. Everything else remains in `candidate`, `excluded` or `denied`.
`admitted_ids(roster)` is the ordered allowlist lane 03 consumes;
`require_admitted(roster, source_id)` is the fail-closed check. The pool is empty
until a family supplies complete six-gate evidence, which is the correct starting
state — native module presence, source facts and taxonomy membership are not
eligibility.

### Private candidate validation path (opt-in, deny by default)

Lane 03's ordinary product entry point seeds only `admitted_ids(roster)` and
fails closed while that set is empty. For the Snow/Dwarf Orange cohort, a caller
may run a *private* validation of the generated-session chain through
`opt_in_validation_cohort(roster, source_ids)` — an ordered allowlist that only
accepts explicitly reviewed identities (`candidate`/`admitted`) whose role is
`source`/`variant`. Denied, excluded, unknown, helper, plant, hazard, projectile,
nest and manager-base IDs are rejected, so the path can never opt a previously
un-reviewed identity into a run.

`require_opt_in(roster, source_id)` is the per-identity fail-closed check. Neither
function mutates the roster or the admission set: `admitted_ids(roster)` stays
empty, `require_admitted` still raises, and normal seed generation is unaffected.
The Snow (`YellowKochappy` 45) and Dwarf Orange (`BlueKochappy` 44) siblings are
distinct *source* identities (never helpers or aliases); each is reviewed
independently, and neither is admitted by this document.

## Current coverage

Generated from source revision `632af93787b9c95b63f0c13be32b161375ce3a96`:

- **102 identities**, **64 randomizable candidates** (51 `enemy`, 13 `boss`).
- Non-candidates: 24 `plant`, 2 `boss_helper` (Baby, Tyre), 3 `nest`, 3 `hazard`,
  4 `projectile`, 2 `manager_base` (Pom, UmiMushiBase), 2 enum-only (`JigumoNest`,
  `PanModokiNest` have no `gEnemyInfo[]` row).
- `docs/PIKMIN2_CONTENT_INVENTORY.json` yields 149 `enemy_ids` tokens; the audit
  resolves every one — 77 exact IDs, 9 `$N` generator variants, 58 treasure-carrier
  aliases (`Enum_suffix`) — and 0 unrecognized tokens.

## Consumer contract

- **03 (seed/native bridge)** keys saved choices on `source_id` and stores the
  roster schema/revision with the seed; unknown or `manager_base`/`non_spawnable`
  IDs are rejected, never silently substituted.
- **04 (placement)** records legal slots/terrain per `source_id` and may only emit
  IDs whose `classification` is `enemy` or `boss`.
- **05 (install)** stages assets by `enum_name`/`source_id` and must not stage
  `manager_base`/`non_spawnable` identities as independent actors.
- **06 (rewards)** reads `drop_type`/`child_*` rather than hard-coding corpses.

## Candidate review and source-backed encounters

`inventory_encounters(payload, roster)` resolves every identity across
`docs/PIKMIN2_CONTENT_INVENTORY.json` `story_caves`/floors through `resolve_alias`,
so aliases are attributed to their real identity (62/64 candidates have at least
one cave-floor encounter). This is inventory evidence, not placement approval —
lane 04 still owns legal slots/terrain. `candidate_review(roster, encounters)`
emits one readiness row per randomizable candidate:

```
source_id, enum_name, common_name, classification, role, owner_lane,
native_module, gates, missing_gates, eligibility, encounters
```

`scripts/audit_pikmin2_roster.py --review` prints those rows, and the report flags
any `native_module` declared in the overlay that is absent from
`engine/pc_port`.

The first reviewed cohort (overlay `candidate`, not admitted) records the reported
evidence and named blockers for Sokkuri (79), Armor (15), Red Bulborb (2), Snow
Bulborb (45), Dwarf Orange Bulborb (44), Wollywog (17) and Mamuta/Miulin (54). No
gate is marked PASS without pinned root/native/executable, inputs and observed
result, so the seedable admission set remains empty.

## Ownership

- Schema, generator, audit and tests: lane 02 (#438).
- Evidence overlay rows: the owning family/shared lane updates only its own IDs and
  requests review for any shared-semantics change; lane 01 reconciles.
- Regeneration is lane 02's; other lanes may open a PR but must not hand-edit the
  snapshot.
