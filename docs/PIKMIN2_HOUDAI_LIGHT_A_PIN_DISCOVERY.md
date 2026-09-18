# Houdai_light_a pin-discovery/ownership packet (#782, downstream #747)

Bounded root-only pin-discovery for issue #782. Downstream consumer:
p2-cave-tutorial_2-p1-later-floors (#747), blocked on floor 9
`Houdai_light_a unknown_cargo` per the gen-13 reconcile evidence
(`tutorial2-later-floors/out/validation-gen3.log:18`).

## Verdict: FOUND and CLASSIFIED — enemy-carried-item compound

`Houdai_light_a` = `<enemy Houdai>` + `<carried item light_a>`: a Man-at-Legs
carrying the `light_a` item. It is NOT a standalone treasure, enemy, or fixture
ID. No invention: every half resolves to a cataloged source entry below.

## Location (tutorial_2 floor 9)

- Cave source: `user/Mukki/mapunits/caveinfo/tutorial_2.txt`
  (`docs/PIKMIN2_CONTENT_INVENTORY.json:67`).
- Floor-9 row (`docs/PIKMIN2_CONTENT_INVENTORY.json:231-233`):
  unit_pool `1_units_houdai_metal.txt`,
  enemy_ids `["Houdai_light_a", "DaiodoRed", "DaiodoGreen"]`, treasure_ids `[]`.
- Same row mirrored in `docs/PIKMIN_CONTENT_IMPORT_LANES.json` (p2-cave-tutorial_2
  cave block, floor first/last 9).

## Classification evidence

- Base `Houdai`: `native/pikmin2-research/include/Game/enemyInfo.h:125`,
  `EnemyID_Houdai = 66, // Man-at-Legs`; inventory enemies entry id 66,
  classification `source_boss`.
- Cargo `light_a`: `docs/PIKMIN2_CONTENT_INVENTORY.json:5746-5753`,
  catalog `us/runtime/item` (source `user/Abe/Pellet/us/pelletlist_us.szs`
  family): archive `light_a.szs`, model `eq_flashlight.bmd`, money 100,
  min 5 / max 10, dictionary 190.
- Compound convention corroborated in the same cave: floor 3 `Fkabuto_bolt`
  (Fkabuto + cataloged treasure `bolt`), floor 7 `FminiHoudai_sinkukan_b`
  (FminiHoudai + cataloged treasure `sinkukan_b`).

## Placement-catalog binding for #747

- Consumer `p2-cave-tutorial_2-p1-later-floors` (#747) stages floor 9 with one
  `Houdai` (enemy id 66) spawn carrying item `light_a` (`light_a.szs` /
  `eq_flashlight.bmd`) inside unit pool `1_units_houdai_metal.txt`, alongside
  `DaiodoRed` + `DaiodoGreen`. No separate treasure spawn: floor-9
  treasure_ids is empty.
- Ownership: classification evidence only; spawn wiring stays with the #747
  owner. No engine/family/shared edits made here.

## Machine check

`experimental/pikmin2_houdai_light_a_pin_discovery.py` reproduces this packet
from the canonical sources read-only and refuses fail-closed (missing input,
malformed JSON, absent cave/row/token, unclassifiable qualifier).
`tests/test_pikmin2_houdai_light_a_pin_discovery.py`: 8 passed, including a
live canonical-source classification test.

All six runtime gates UNTESTED. No ADMIT. No gameplay claim.
