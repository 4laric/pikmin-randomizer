# Regional metadata and catalog audit (#147)

Implementation owner: Codex through shared account `4laric`. This pass consumes
the #140 treasure ledger without changing its catalog, classification, or cargo
interfaces. It reconciles US source definitions with localized name IDs and
compares metadata carried on the US disc. It does not validate regional gameplay.

## Reproduce locally

First produce `treasure_ledger.json` with the #140 tool (delivered in Claude's
commit `47f60a5`, independently of this branch):

```powershell
py -3.12 -m experimental.pikmin2_treasure_ledger --iso <owned-US-disc.iso> --output <new-ledger-directory>
py -3.12 -m experimental.pikmin2_regional_audit --iso <owned-US-disc.iso> --ledger <ledger-directory>/treasure_ledger.json --output <new-private-directory>
py -3.12 -m unittest tests.test_pikmin2_regional_audit -v
```

The regional command needs the ledger JSON, not the ledger module installed on
its own branch. It uses the existing US GPVE01 revision 0 disc reader and refuses
an existing output directory. `--inventory` defaults to the checked-in
`docs/PIKMIN2_CONTENT_INVENTORY.json` and must match the ledger's inventory hash.
Every source hash recorded by the ledger is checked against the supplied disc;
the runtime catalog's identities, order, dictionary numbers, economy, models,
and unique flags are checked against ledger entries as well.

`regional_audit.json` contains source records, localized strings, catalog
differences, and input hashes. Keep it under ignored local `output/`; do not
commit or distribute it or the original assets. Only tooling, synthetic tests,
and this evidence summary belong in Git. The report is deterministic for the
same inputs and has no output-path or timestamp dependency.

## What the report means

Each treasure retains its source ID, pellet kind, config index, dictionary
number, #140 classification, campaign/mode scopes, and original placement
records. `ledger_placement_index` points into that entry's input placement list;
it is not a new persistent instance or receipt ID. Source definitions marked
`engine_loaded:false` go into a separate list. Active definitions are not actual
spawn counts: unique collectibles, optional populations, and repeated floor
definitions retain the semantics established by #140.

Regional comparisons join by source ID **within each pellet kind**. Dictionary
numbers, model filenames, dimensions, economy and other parameters are compared
fields, not join keys. Runtime archive members and loose config files are
compared separately. Neither a loose file nor a region-named directory proves
that the executable loads it in a particular configuration.

The cave inventory distinguishes:

- References from campaign, Challenge and Battle retail tables.
- References only from the alternate KFes Challenge table, selected by
  `mKFesVersion` in `src/plugProjectKandoU/vsGameSection.cpp:436`.
- Stage registrations outside the retail inventory, recorded without claiming
  that an active entrance exists.
- Files not referenced by either table set, whose status remains unresolved.

The report preserves overlapping retail/KFes references. A filename containing
`test`, `video`, `E3`, or `kfes` alone does not establish an unused/demo runtime
classification. Additional source paths must be traced before those unresolved
files can be classified more strongly. Non-treasure helper actors remain under
their enemy/system audits; this tool does not add them to the collectible count.

## Name and region provenance

Source examined: `projectPiki/pikmin2` revision
`632af93787b9c95b63f0c13be32b161375ce3a96`. Paths below refer to that checkout.

`src/plugProjectKandoU/pelletConfig.cpp:121` finds a config by its one-based
dictionary number; `:137` assigns its index from config order.
`src/plugProjectKandoU/gamePelletList.cpp:145` searches Otakara then Item for the
dictionary entry. `:160` returns the display offset: Otakara index, or Item index
plus the complete Otakara list length. Thus dictionary number is not message ID.

`src/plugProjectMorimuraU/zukan2D.cpp:3392` and `:3564`, together with
`mrUtil.cpp:61`, use that offset to form tag `0101_00` plus the decimal offset.
For this catalog the numeric message ID is `101 + display_offset`.
`src/plugProjectOgawaU/ogObjKantei.cpp:149` also constructs the `_01` appraisal
variant. Both variants are recorded independently.
`src/sysGCU/message.cpp:10` converts ASCII tags into message number and variant;
`src/JSystem/JMessage/resource.cpp:12` packs MID supplement 1 as
`(message_number << 8) | variant`. INF offsets point into DAT bytes, not entry
numbers (`include/JSystem/JMessage/data.h:55` and `TResource.h`).

The bounded BMG reader accepts the observed ordered MID form, group zero,
eight-byte INF entries and encoding 3 (Shift-JIS) or 1 (single-byte font).
Encoding 1 non-ASCII text remains unresolved without a font mapping. Missing,
empty and unrecognized-control names have explicit statuses. The cave-title
exception below retains known presentation controls separately. English line
breaks are preserved, not renamed.

Config archive selection is in `gamePelletList.cpp:78`: PAL uses its PAL
archive; the non-PAL Japanese/English branches select Japanese/US archives.
Asset archive selection is separate in `pelletMgr.cpp:4675` and `:4769`.
Message archive names and language selection are in
`src/sysGCU/messageMgr.cpp:20` and `:44`. This report probes every onboard
language table using the **US display offsets**. It does not certify foreign
regional dictionary/UI joins or treat all onboard language files as complete.

## Campaign cave name follow-up

`campaign_cave_names` joins each stable inventory cave ID to the filename/tag
triples in `user/Abe/stages.txt`, following `CourseInfo::read` framing in
`src/plugProjectKandoU/gameStages.cpp:206` and `CaveOtakaraInfo::read` at `:47`.
It then uses the 14 campaign entries from
`src/plugProjectOgawaU/ogObjAnaDemo.cpp:12` to obtain BMG message numbers.
Unknown tags, duplicate joins, and missing campaign references fail validation.
The Challenge placeholder entries in that title table are not used as names.

English cave titles contain presentation tags. For this lookup only, the reader
recognizes `FF0001` (font size, two-byte payload), `030004` (reset font height,
no payload), and `030005` (set font height, two-byte payload). Their behavior is
in `src/sysGCU/messageRendering.cpp:409` and `:506`; length-prefixed framing is
in `src/JSystem/JMessage/processor.cpp:260`. They change sizing, not character
content. Embedded NUL payload bytes are not mistaken for string terminators.
The result status is `resolved_with_presentation_controls`, with tags and exact
payload hex retained beside the literal title. Other controls remain unresolved;
this is not a general BMG renderer and treasure-name behavior stays unchanged.

`stage_cave_references` also retains all 26 source registrations, including nine
extensionless references on `test_map` that do not name existing disc files.
No extension or replacement filename is guessed. Three retail-course `test`
tags explicitly register `caveinfo.txt`; it now has the separate
`stage_registered_outside_retail_inventory` classification. Registration alone
does not prove an entrance is active or change the 14-cave campaign inventory.
Only the regional audit files changed in this follow-up, based on integration
`feb8f31324f69a80c731616caa55560f41aa07a7`.

## Local validation results

Validated against the local US GPVE01 revision 0 disc using a freshly generated
#140 ledger from `47f60a5`, based on randomizer integration commit
`186d23284d786afbc9265888c7cfb9f361b15194`:

- 201 catalog entries, all classified campaign by #140; 599 loaded source
  definitions and 20 unloaded generator definitions preserved separately.
- All 201 English normal-name lookups resolve. Japanese resolves 200; the
  `g_futa_daisen` normal name contains control codes and remains unresolved.
  The French, German, Dutch, Italian and Spanish archives each have 201 empty
  normal-name slots at these US offsets. Archive presence is insufficient.
- All 14 campaign cave message IDs reconcile. English resolves all 14 with
  sizing controls retained; Japanese resolves all 14 directly. The other five
  onboard language tables have 14 empty cave-title slots each.
- Across 85 cave-definition files: 54 retail referenced, five KFes-only, one
  registered outside the retail inventory, and 25 unresolved/unreferenced.
- Each onboard regional runtime archive has 188 Otakara, 13 Item, 51 Carcass,
  four NumberPellet and one Fruit entries. Source IDs and order match the US
  lists. Japanese differs in 131 Otakara and two Item records; PAL differs in
  129 Otakara and two Item records. Across those cargo records, each comparison
  changes 123 dictionary fields. Regional differences also include models,
  money, carry strength and dimensions, so equal IDs do not mean equal content.
- Loose US and PAL carcass configs differ from their runtime archive members
  for `Sokkuri` and `UmiMushiBlind`. The report retains the field differences;
  it does not substitute loose data into runtime results.

Nineteen synthetic tests cover index/dictionary separation, message variants,
Shift-JIS, empty/control/unsupported-font names, malformed BMG tables,
regional key movement, stale provenance, catalog drift, unloaded records and
table-backed KFes classification, stage framing, cave-name joins, absent names,
non-retail registrations and bounded presentation control handling. Local US
disc runs validate all joins. No native build or gameplay test is claimed.

## Remaining acceptance

Keep #147 open. Actual PAL/JPN discs and revisions, localized UI rendering,
regional asset availability, generated placement instances, natural collection
and save/load need validation. The 25 unreferenced cave files and the separate
non-retail registration need further reachability/classification evidence.
Controlled Japanese treasure text and broader localized mode/enemy names remain
additional work. This source audit does not
enable regional support or close runtime acceptance in #140.
