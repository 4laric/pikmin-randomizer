# Treasure catalog validation ledger (#140)

This batch adds `experimental.pikmin2_treasure_ledger`, a validation pass over the
US runtime treasure catalogs. It classifies every `otakara` and `item` entry by the
source placements that can produce it and reconciles those placements against the
counts the game itself declares. It changes no cargo runtime interface and copies
no disc data.

```powershell
py -3.12 -m experimental.pikmin2_treasure_ledger --iso <local-US-disc.iso> --output <new-directory>
```

The importer rejects an existing output directory and writes `treasure_ledger.json`.
`--inventory` defaults to `docs/PIKMIN2_CONTENT_INVENTORY.json`; the run fails if the
inventory's catalog names or dictionary numbers differ from the disc.

## Source semantics

- **Catalogs.** `user/Abe/Pellet/us/pelletlist_us.szs` holds `otakara_config.txt`
  (188 entries) and `item_config.txt` (13 entries). Every entry is `unique yes`. The
  `dictionary` number is the Treasure Hoard slot resolved by
  `PelletConfigList::getPelletConfig_ByDictionaryNo` (`src/plugProjectKandoU/pelletConfig.cpp`).
  `code` bit 1 disables the resting shadow and Breadbug carrying
  (`Pellet::panmodokiCarryable`); bit 2 loads the model with `J3DMLF_UsePostTexMtx`.
- **Declared counts.** `user/Abe/stages.txt` (`gameStages.cpp CourseInfo::read`) lists
  per course the `LimitGenInfo` day windows, each cave with its treasure count, and a
  "Ground Otakara" count. The four retail courses declare 7+7+7+5 ground treasures and
  14 caves declare 175, which is the 201-entry catalog.
- **Surface placements.** Generator files under the course `abe_folder` follow
  `Generator::read` in disc mode: version tag, reserved short, resurrection days,
  32 Shift-JIS name bytes, position, offset, object tag. `{pelt}` blocks
  (`GenPellet::doRead`) carry the manager id (3 otakara, 4 item) and the config index.
  `{teki}` blocks of object version 3 to 5 carry a `PelletMgr::OtakaraItemCode`
  (kind byte, index byte) for an enemy-held treasure.
- **Engine count limit.** `GeneratorMgr::read` loads exactly the declared generator
  count. `user/Abe/map/last/nonloop/0-1.txt` declares zero generators above twenty
  leaf/acorn pellet blocks and `yakushima/nonloop/20-29.txt` declares one above two.
  The ledger records such blocks with `engine_loaded: false`; they never classify an
  entry. Without this rule Wistful Wild would over-count by nine dead treasures.
- **Cave placements.** `caveinfo` rosters are read with the same framing as the cave
  catalog lane: loose treasures, enemy tokens with a carried-treasure suffix
  (`TekiInfo::read` split rule) and cap enemies. A floor listing `BigTreasure` also
  places `elec`, `fire`, `gas`, `water` and `loozy`, which `BigTreasureMgr::Mgr` and
  `BigTreasure::Obj::setupTreasure` create without any roster entry.
- **Counting rule.** Because every entry is unique, a cave's declared count is the
  number of distinct treasure ids across its floors. `yakushima_4` lists
  `BlackMan_fue_pullout` on five floors and declares it once.

## Result on the local GPVE01 revision 0 disc

| Check | Result |
|---|---|
| Catalog entries classified | 201 of 201 (`campaign` 201, `mode_only` 0, `unused` 0) |
| Course ground counts | tutorial 7/7, forest 7/7, yakushima 7/7, last 5/5 |
| Cave counts | 14 of 14 reconcile; `last_3` 21 includes the five Titan Dweevil drops |
| Dictionary numbers | 1 to 201, contiguous, no duplicates |
| Placement records | 619 (surface, story cave, Challenge, Battle) |

Every catalog entry is a campaign collectible: the 26 surface pellets and held
treasures, 170 story-cave treasures, and the five boss drops. 119 of them are also
placed in Challenge or Battle definitions (`mode_scopes`), which is metadata for the
mode lanes, not a second collectible. Surface pellets that the engine loads all live
in `initgen.txt`; enemy-held surface treasures are the Creeping Chrysanthemum
(`donguri`), Toady Bloyster (`turi_uki`), Fiery Bulblax (`watch`) and Orange Bulborb
(`kuri`). The Key is held by Beady Long Legs in `yakushima_1` and appears in many
Challenge caves.

## Limits

- Placements are definitions, not spawned pellets, receipts or runtime cargo state.
- Models, materials, carry slots, digging, enemy-held release and delivery receipts
  remain runtime acceptance items on #140 for the cargo and animation lanes.
- English names are not guessed; source ids and dictionary numbers are kept.
- `test_map`, `caveinfo.txt` test caves and the `zukan` folders are outside the count.

Tests: `tests/test_pikmin2_treasure_ledger.py` uses synthetic fixtures and needs no disc.
