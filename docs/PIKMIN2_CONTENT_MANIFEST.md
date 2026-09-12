# Emergence content preparation (#110)

This experimental content stage prepares the complete treasure catalog and source
roster for integration. It does **not** replace the playable checkpoint launcher:
its native receiver still supports one selected treasure. `native_ready: false`
is intentional. No native files, player saves, or production seeds are changed.

Run locally with a US GPVE01 revision 0 disc and an existing Emergence import:

```powershell
py -3.12 -m experimental.pikmin2_content --iso <local.iso> --imported <import-directory> --output <new-directory>
```

The output contains `content.json` and three independently usable existing
`P2_POD_1` asset directories under `treasures/`. Copyrighted models, textures,
source definitions and generated outputs remain local. Only tooling is committed.
Each output directory must be new; failures cannot silently reuse old assets.

## Disc roster

Source: `user/Mukki/mapunits/caveinfo/tutorial_1.txt`.

| Floor | Catalog ID | Count | Kind |
| --- | --- | --- | --- |
| 1 | YellowKochappy | 4 | Enemy, placement type 0 |
| 1 | tape_yellow | 1 | Treasure |
| 1 | dia_a_red | 1 | Treasure |
| 2 | YellowKochappy | 7 | Enemy, placement type 0 |
| 2 | BlackPom | 2 | Violet Candypop, placement type 1 |
| 2 | KareOoinu_s | 6 | Plant |
| 2 | KareOoinu_l | 4 | Plant |
| 2 | Clover | 2 | Plant |
| 2 | map01 | 1 | Treasure |

The second floor is **not enemy-free**. Internal enemy IDs are preserved without
inferring English names from their color prefixes. Floor two's maximum enemy
parameter is nine: seven ordinary enemies plus the two flowers.

`RandEnemyUnit.cpp` and `RandItemUnit.cpp` decode guaranteed counts as weight / 10,
with weight % 10 selecting optional weighted populations. `RandPlantUnit.cpp`
uses the entire weight as the plant count. Optional weighted populations are
explicitly rejected by this narrow preparation tool, rather than approximated.

Source economy comes from `user/Abe/Pellet/us/otakara_config.txt` and
`item_config.txt`, using the existing model converter:

| Catalog ID | Pokos | Required strength | Physical slots |
| --- | --- | --- | --- |
| tape_yellow | 100 | 4 | 8 |
| dia_a_red | 180 | 15 | 25 |
| map01 | 200 | 101 | 101 |

Total treasure value is 480 Pokos, before enemy corpses. Atlas's 101 is strength,
not a requirement for 101 individual carriers.

## Identity and placement contract

A catalog ID identifies a model/type; an instance ID identifies one collectible
or actor on one floor. Example: `tutorial_1:floor2:treasure:map01:0`. Do not use the
catalog ID as a general receipt key: different floors or future duplicate items
must remain distinct. This is a proposed content interface, not a checkpoint
migration. Existing `P2_POD_1` configs deliberately retain their legacy catalog IDs.

Every source layout slot is retained with its source index, type, position,
heading, radius, min/max group count, room instance, and assembly transform.
Positions and headings use the same quarter-turn conventions as the existing
assembly. Source heights are retained; runtime ground projection must be explicit.
The first-floor arrangement remains the existing authored two-room engineering
assembly, not a reproduction of the original map-generation algorithm.

Only the single final-room treasure slot is resolved automatically, because it
has exactly one corresponding treasure. Other entries keep null placements.
Source candidates are not final actor coordinates: enemy groups have random
radial offsets, item and plant slots require selection, and holes/geysers require
lifecycle-specific placement rules. The manifest retains candidates instead of
inventing canonical positions. No enemy is silently replaced with a P1 stand-in.

## Integration still required

- Native multi-treasure model/config registry, per-instance receipt ownership and
  receiver dispatch; remove the one-selected-treasure assumption.
- Checkpoint allowed-receipt validation and content fingerprint must consume all
  treasure instances/models. Existing profiles must not be silently migrated.
- Source enemy implementation and an explicit deterministic placement policy,
  with route, collision and capacity validation at generated positions.
- Hole/geyser/Pod actor binding and complete physical cave roundtrip.

## Validation

Four focused tests cover packed versus plant counts, floor-scoped identity,
unsupported weighted populations, non-mutating source transforms and unique-slot
resolution. Local extraction prepared all three converted models successfully.
A second independent extraction produced byte-identical content manifest and
three model files. This is content preparation evidence, not native multi-item
collection or complete cave gameplay acceptance.
