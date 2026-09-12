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

- First-floor geometry is now assembled in an authored arrangement (see below). Original P2 layout generation and actual floor content remain unimplemented.
- Replace the scaffold start/receiver/content with the actual floor start, exit and roster; preserve the validated seam paths.
- Validate the second-floor room natively, including slopes, material approximations and destination approach heights.
- Resolve local visual/collision discrepancies where they affect play; do not apply the concrete prototype's -1 offset globally.
- Replace scaffold actors through the subsequent Research Pod/treasure, cave lifecycle and Purple batches (#111–#114).

The importer reports `assembled: false` and `native_validated: false`. Native evidence for one separate preview must not mark every imported unit or the complete cave as validated.

## Final native evidence

Run `output/pikmin2-emergence-preview/da025222e1cb446f854f48e90a2146cc` exited 0. Controller movement covered 229.01 units; the bolt receipt recorded one collection with repairs unchanged and no seeds. Actual attack AI killed the Dwarf; transport AI carried its corpse over 242 units and completed Onion delivery. Static geometry and display-list hashes matched between start and finish; the final render matrix matched the stationary camera exactly. Start/final screenshots were inspected. The fixture uses explicit AI assignment and remains distinct from manual controller sign-off.

The Windows fixture build passed against the existing production build. Native fixture source commit: `f292a0286aeafae3a6ce548a89beaf6e1a5b710b`; no production engine behavior changed. Final local manifest: `output/pikmin2-emergence110/import-03/manifest.json`.


## Authored first-floor assembly

`experimental/pikmin2_assembly.py` joins two entrance-room instances with an allowed straight snow connector. The second room is rotated 180 degrees, with centers at Z=0 and Z=1020 and the connector at Z=510. This is a deterministic engineering arrangement from the source floor pool, not a recreation of the original map generator.

One shared transform handles render positions, normals, collision, waypoints and placement headings. Materials/textures and mesh indices are merged into one rigid MOD. Matched, oppositely facing door nodes are welded into shared route points, preserving all original directed links and avoiding zero-length seam edges. Missing, reused, misaligned or unsealed doors fail validation. No perimeter caps close the connected corridor.

Offline coverage includes 195 ground samples across both seams in a 60-unit-wide strip, complete directed route reachability, deterministic binary output and byte-identical conversion of a single untransformed unit. Thirty-five focused tests pass. The assembly has 1,336 rendered triangles. The scene still uses the documented material approximations.

```powershell
python -m experimental.pikmin2_assembly --imported output/emergence-new --output output/emergence-floor1-new
python -m scripts.preview_pikmin2_emergence --assets "PATH/pikmin/assets" --imported output/emergence-new --assembled output/emergence-floor1-new --treasure "PATH/room105/treasure.mod" --exe "PATH/nectar-p2-room.exe"
```

The optional assembly does not change the single-room preview. Its bolt and Dwarf are placed in the far room so transport must cross both joins to the temporary Onion. The fixture steers actual controller input through the corridor using camera-relative axes, then exercises actual attack and transport AI without teleporting actors. Explicit Pikmin AI assignment is still a fixture limitation.


Assembly native evidence: `output/pikmin2-emergence-preview/8ace34256aa84af6b47194d9fe29e552` exited 0. Olimar walked 753.57 units from the starting room across both seams into the far room using controller input. The bolt returned from that room with repairs unchanged and seeds=0. Native combat killed the distant Dwarf, then carriers moved its corpse over 1,259 units back across both joins and completed Onion delivery. Source actor positions were not teleported by the fixture. Sampled vertex and complete display-list hashes stayed stable; the final render matrix matched the stationary camera. Movement and final screenshots were inspected. The visual approximations are still apparent and this is not a manual gameplay sign-off.

Windows fixture build passed; native fixture source `34f2760ef5c9ffa701da676d4b4cb04f8acf5fd8`. Local `floor1-03` adds source-hash provenance to the manifest; its MOD is byte-identical to the tested `floor1-02`. Use `output/pikmin2-emergence110/Play-floor1.cmd` for the assembled engineering layout. The earlier single-room launcher remains available.

## Second-floor terrain and carrying

The standalone `--floor 2` preview uses `room_purple14x14_snow`. Actors are projected onto decoded collision, including the starting platform at Y=25 and the test cargo at approximately Y=-69.6. Four native ground probes compare against those actual positions. The controller follows the slope route out to the lower section; the original directed route graph remains unchanged, including its source waypoint heights.

Native run `output/pikmin2-emergence-preview/2674c283e9044211adbe2ef47601e82d` exited 0: controller traversal covered 1,773.18 units and native carriers returned the bolt to the starting platform. Repairs remained unchanged and the treasure produced no seeds. Start and moved screenshots were inspected. Rendering still has the documented material approximations and exposed room boundaries; the starting camera can be obscured by the temporary ship. This is terrain/transport evidence, not full second-floor gameplay: its real roster, Purple Candypops, heavy treasure requirements and exit belong to later batches.

The next increment adds an optional [Research Pod preview](PIKMIN2_RESEARCH_POD.md) to these same isolated layouts.
