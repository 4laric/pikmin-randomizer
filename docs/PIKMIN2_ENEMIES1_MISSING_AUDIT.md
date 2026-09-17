# Enemies-1 missing audit: unowned identities 14/22/39/47/80/89 (#653)

Implementation owner: Codex through shared account `4laric`. Lane
`enemies-1-missing-audit` (tooling P0 only). These are the enemies-1 roster
identities no lane owns. Parent/child group ownership is preserved by
reference: 39 resolves into the PanModoki group (#168), 22 into the Hiba
group, 47/80/89 into the plant group (#171). No sibling-partition file was
read for implementation or edited.

## Method

`experimental/pikmin2_enemies1_missing_audit.py` decodes each identity from
the live decomp checkout (`native/pikmin2-research`) and
`docs/PIKMIN2_CONTENT_INVENTORY.json`: enum identity, `gEnemyInfo` row
presence, entity/shared-family source presence, and inventory token hits.
It fails closed on any drift from the baselines below instead of inventing
values. Machine packet: `packet.json` beside `run.log` in the lane output
directory (schema `p2-enemies1-missing-audit-v1`).

## Per-identity rows (decomp revision as checked out; header hashes in run.log)

| ID | Internal | Class | Owner | Source anchors | Inventory hits | P1 blockers |
|---|---|---|---|---|---|---|
| 14 | Tobi (Shearwig) | creature, ground | #165 | `enemyInfo.h:73`; info row `enemyInfo.cpp:33` (spawnable+ownID); `Tobi.cpp`/`Tobi.h` | 6 cave-floor refs | Ground-family receiver/combat (#165); P1 host actor binding |
| 22 | ElecHiba (wire) | fixed_hazard, elemental | #170 | `enemyInfo.h:81`; info row `enemyInfo.cpp:43` (HasNoInfo+spawnable); `ElecHiba.cpp`/`ElecHiba.h` | 15 cave-floor refs | Hazard/elemental receiver contract (#170); explicit bestiary handling |
| 39 | PanModokiNest (Breadbug Nest) | helper_alias, scavengers | #168 | `enemyInfo.h:98`; **no** info row (enum-only); `getEnemyResName` remaps to `PanHouse83` | 1 (alias ref) | None for this ID; P1 work belongs to the PanHouse83 actor |
| 47 | Clover | flora | #171 | `enemyInfo.h:106`; info row `enemyInfo.cpp:72`; shared `Hana.cpp` + `pelplant.cpp` + headers | 19 cave-floor refs | Flora conversion contract (#171); absorb-never-haul reward path |
| 80 | Tukushi (Horsetail) | flora | #171 | `enemyInfo.h:139`; info row `enemyInfo.cpp:80`; shared `Hana.cpp` + `pelplant.cpp` + headers | 3 cave-floor refs | Flora conversion contract (#171); absorb-never-haul reward path |
| 89 | Chiyogami (paper) | scenery_usage_unconfirmed | #171 | `enemyInfo.h:148`; info row `enemyInfo.cpp:85` (HasNoInfo+factory); shared `Hana.cpp`/`Hana.h` | 3 token refs, **zero confirmed cave-floor encounters** | Missing prerequisite: retail placement audit first; then flora contract (#171) |

## Explicit unsupported references

- 89 Chiyogami retail placement is unaudited (`scenery_usage_unconfirmed`);
  the adapter records it as a missing prerequisite, never as unused.
- 39 PanModokiNest has no entity, bank, or info row of its own; anything
  claiming a separate nest actor would contradict the remap.
- Inventory hit counts are token references, not confirmed placements; cave
  weighted rows stay definitions, never spawn instances.

## Validation

- `tests/test_pikmin2_enemies1_missing_audit.py`: 17 passed (enum/info
  decode, alias handling, drift/missing-input rejections, packet schema and
  gate discipline, end-to-end synthetic run).
- Real run: 6/6 rows validated, all gates UNTESTED; see `run.log`.
- No runtime, no playability claim, no ADMIT.
