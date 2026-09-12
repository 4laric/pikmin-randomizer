# Emergence Cave import, batch 1 (#110)

Implementation owner: Codex using shared 4laric account. Experimental, outside v0.1. Tracking: [#110](https://github.com/4laric/pikmin-randomizer/issues/110). Overall [implementation plan](PIKMIN2_IMPLEMENTATION_PLAN.md).

## Implemented

`experimental/pikmin2_cave.py` reads the US revision 0 disc directly and builds a local manifest from Emergence's cave and unit definitions. It parses parameter blocks, weighted actor/treasure rosters, unit dimensions, doors and waypoint references. Packed weights and spawn classes remain source data, not an invented final actor list.

Both floor definitions and all eight referenced unit candidates now import: the entrance room, the large Purple room and six cap/corridor pieces. Each has a converted MOD, rebuilt P1 collision, unchanged directed routes, source hashes, placement candidates, destination reachability and terrain probes. The importer refuses to overwrite an existing output directory and writes its manifest only after every selected asset converts.

The static converter now supports the unpaletted GX intensity/alpha/color texture formats through P1's different format enumeration. Base mip bytes retain GX tiling. Extra UV/color channels are accepted only in explicit material-approximation mode, consumed correctly from display lists and reported as discarded. Strict mode still rejects them. The second-floor model has 4,108 triangles and 21 textures; its extra UV channel and BTK texture animation are disclosed approximations.

P2 dry surface attributes 1, 6 and 7 join the previously audited 2/5 mapping. P2 navi.cpp uses these attributes for footstep selection, and HoudaiShotGun.cpp treats attribute 6 separately from water-volume lookup. P1 has no matching surface palette, so this preview uses solid collision while retaining slip/bald bits. The importer rejects nonempty water volumes. Exact surface sound/impact behavior is not implemented.

## Engineering preview

`scripts/preview_pikmin2_emergence.py` creates a private entrance-room overlay using the existing native preview executable. It has twenty Reds, a P1 Dwarf Bulborb, an Onion receiver and the previous bolt treasure. These are test actors, not the actual Emergence roster. The open doorway is capped for this isolated room. Every launch gets a fresh directory; there is no campaign save or AP connection.

The old concrete-room Onion placement was inside the new room's raised bank. The preview moves it onto flat ground near source waypoint 1. All source route links are retained. Every waypoint can reach the start destination in both main rooms: waypoint 1 in the entrance room, waypoint 0 in the Purple room. Most second-floor links are intentionally directed toward that destination; absence of reverse reachability is not by itself a bug.

Reproduce locally from the repository root:

```powershell
python -m experimental.pikmin2_cave --iso "PATH/PIKMIN2.iso" --output output/emergence-new
python -m scripts.preview_pikmin2_emergence --assets "PATH/pikmin/assets" --imported output/emergence-new --treasure "PATH/room105/treasure.mod" --exe "PATH/nectar-p2-room.exe"
```

The preview currently depends on the earlier room105 bolt conversion and experimental executable. It is not a redistributable playtest package. On this workstation, `output/pikmin2-emergence110/Play.cmd` selects the imported entrance room.

## Validation and limits

Thirty focused Python tests pass under Python 3.12: definition framing, malformed counts/paths/door references, directed reachability, texture format mapping/tile sizes, strict extra-UV rejection and the earlier room regressions. The local disc pass converted all eight candidates. No extracted asset or binary is checked in.

The native fixture was extended to read optional decoded terrain heights rather than requiring four flat-zero points. Its free recruitment observation now falls back to explicit transport assignment when fewer than the corpse's required carriers recruit, not only when none recruit. This remains a route/delivery fixture, not proof of natural recruitment from player input.

Initial native evidence confirmed room rendering, live actors and engine ground matching the source bank height (14.865 at the old Onion coordinate). The first fixture stopped on its obsolete zero-height assertion. The next run passed movement but stalled on the misplaced receiver; it was stopped to correct the preview placement. With the receiver moved, treasure delivery and combat passed. One Pikmin naturally recruited to the corpse, insufficient for carrying, exposing the fixture's zero-only fallback condition.

Visual inspection shows the imported snow terrain with live actors, but first-texture shading and missing cave presentation remain apparent. Render/collision probes use a ceiling ten units above collision to exclude overhead decorative geometry. Local deltas vary, so no universal vertical offset is applied. Probe results are diagnostics, not blanket floor-alignment sign-off.

## Still required in #110

- Assemble floor one's rooms and connectors with consistent geometry/collision/door/route transforms. Its source definition requests two rooms; importing its main unit alone is not a complete floor.
- Validate seam corridors, final start/exit placement and carrying across the assembled floor.
- Validate the second-floor room natively, including slopes, material approximations and destination approach heights.
- Resolve local visual/collision discrepancies where they affect play; do not apply the concrete prototype's -1 offset globally.
- Replace scaffold actors through the subsequent Research Pod/treasure, cave lifecycle and Purple batches (#111–#114).

The importer reports `assembled: false` and `native_validated: false`. Native evidence for one separate preview must not mark every imported unit or the complete cave as validated.

## Final native evidence

Run `output/pikmin2-emergence-preview/da025222e1cb446f854f48e90a2146cc` exited 0. Controller movement covered 229.01 units; the bolt receipt recorded one collection with repairs unchanged and no seeds. Actual attack AI killed the Dwarf; transport AI carried its corpse over 242 units and completed Onion delivery. Static geometry and display-list hashes matched between start and finish; the final render matrix matched the stationary camera exactly. Start/final screenshots were inspected. The fixture uses explicit AI assignment and remains distinct from manual controller sign-off.

The Windows fixture build passed against the existing production build. Native fixture source commit: `f292a0286aeafae3a6ce548a89beaf6e1a5b710b`; no production engine behavior changed. Final local manifest: `output/pikmin2-emergence110/import-03/manifest.json`.
