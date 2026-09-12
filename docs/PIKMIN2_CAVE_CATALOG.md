# General cave definition catalog (#129 / #154)

This batch adds `experimental.pikmin2_cave_catalog` alongside the unchanged
Emergence-only parser. It inventories source definitions; it does not generate
maps or promote weighted roster rows into actual actor placements.

```powershell
py -3.12 -m experimental.pikmin2_cave_catalog --iso <local-US-disc.iso> --source native/pikmin2-research --output <new-directory>
```

The local `catalog.json` contains fourteen retail campaign caves, their floor
parameter blocks, enemy/treasure/gate/cap definitions, referenced unit pools with
doors and links, source hashes, and an explicit `generated: false`. Original
assets are not copied. The importer rejects an existing output directory.

## Source semantics

`src/plugProjectKandoU/gameCaveInfo.cpp` defines the ordered stream. Version zero
floor blocks contain enemies, treasures and gates. Version one and later also
contain caps. Floor ranges are retained as inclusive one-based metadata;
overlapping or inverted ranges are rejected. Source parameter strings remain
available while scalar framing, type, finite values and referenced names are
validated. Unknown parameter IDs fail closed rather than silently disappear.

`TekiInfo::read` handles `$` drop prefixes and enemy-held treasure suffixes.
The splitter recognizes the first underscore whose exact prefix is a registered
enemy name. This preserves underscores inside IDs such as `KareOoinu_s`.
Final lookup in `src/plugProjectYamashitaU/enemyInfo.cpp` is case-insensitive:
the disc's `RKabuto` resolves to `Rkabuto`. Suffix splitting itself is deliberately
case-sensitive, matching the source's different comparison operation.

Enemy and treasure weights retain both their original integer and decoded
minimum-count/selection-weight portions. Plant placement type6 instead interprets
the entire integer as a target count, following `RandPlantUnit.cpp`. These are
requests to the generation algorithm; available slots, caps, floor limits and
random selection still determine actual births. Gate weights are direct selection
weights and gate life is a finite nonnegative float. Cap entries preserve the
source empty byte and, when nonempty, a complete nested enemy definition.

Drop modes0–5 have named source semantics. The reader accepts source syntax6–9
but labels them unmapped rather than inventing behavior. Unknown enemy or treasure
references, malformed counts/blocks, unsupported parameter types, unsafe asset
names, missing unit resources and trailing data are rejected.

The existing `unit_definition` decoder validates the referenced unit pools; this
batch inventories their doors/links and verifies both model/text archive paths
exist. It does not load every unit's collision or prove traversability.

## Real disc audit

US GPVE01 revision0 audit:

- 14 campaign caves,105 floors and96 referenced unit pools.
- 167 unique unit IDs; both archive paths exist for every unit.
- 671 enemy definition rows,112 loose-treasure rows,27 gate rows,130 cap rows.
- Hole of Beasts (`forest_1`) has five floor definitions. Its second and fourth
  floors exercise nonempty cap rosters, including Egg and TamagoMushi.

The row totals are not enemy populations or campaign treasure counts; held
items and repeated/random definitions must not be double-counted. All fourteen
retail definitions happen to use individual floor ranges; a synthetic regression
covers a multi-floor range without claiming one appears in this disc inventory.

Eighteen focused catalog/legacy-Emergence tests and thirteen malformed-input
subtests pass. Two complete local audit runs produced byte-identical metadata.
Evidence: `output/p2-cave-catalog-batch/audit-final/catalog.json` and
`audit-repeat/catalog.json`. No native build/gameplay validation is claimed.

## Remaining generation work

Room choice/rotation, seam joining, gates/caps placement, weighted selection,
enemy-held and buried item instantiation, hazard/fountain/hole rules, water,
collision and carry navigation, seed identity and topology persistence remain
#129. Hole of Beasts runtime content remains #154. Neither issue is complete.
