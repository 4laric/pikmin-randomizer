# Pikmin 2 room in Open Nectar (experimental)

Tracking: [#105](https://github.com/4laric/pikmin-randomizer/issues/105). This is a post-v0.1 content-conversion experiment, separate from Pikipelago seeds and the Pikmin 2 executable build.

The preview imports `room_4x4a_4_conc` and a rigid bolt treasure into the Pikmin 1 engine. It uses Pikmin 1 captain, Pikmin, enemy, collision, route and carrying systems. The private generator supplies one red Onion, 20 red Pikmin, one Dwarf Bulborb and one five-carrier treasure. Delivery writes `treasure-receipt.txt` without adding repairs or Onion seeds. This does not implement a Pikmin 2 campaign, procedural caves, two captains or new Pikmin species.

## Local inputs

Use an owned US Pikmin 2 GPVE01 revision 0 disc image and an existing extracted Pikmin 1 asset directory. Extracted assets and converted models stay under ignored `output/`; they are not part of the source distribution.

```powershell
python -m experimental.pikmin2_assets --iso "PATH/PIKMIN2.iso" --output output/pikmin2-extract105
python -m experimental.pikmin2_convert output/pikmin2-extract105/arc/view.bmd output/pikmin2-room105/render.mod
python -m experimental.pikmin2_convert output/pikmin2-extract105/treasure/bolt.bmd output/pikmin2-room105/treasure.mod --approximate-materials
```

Complete the collision export and launch using a built preview-enabled executable:

```powershell
python -m experimental.pikmin2_collision --texts output/pikmin2-extract105/texts --mod output/pikmin2-room105/render.mod --output output/pikmin2-room105/room.mod --cap-exits
Copy-Item output/pikmin2-room105/room.route.ini output/pikmin2-room105/room.ini
python scripts/preview_pikmin2_room.py --assets "PATH/pikmin/assets" --exe "PATH/nectar.exe"
```

The collision converter appends its own vertices to the render stream, reconstructs P1 collision acceleration and exports the original directed route graph. The source collision has 82 triangles; eight additional invisible perimeter triangles bound this single-room experiment. P2 material attributes are explicitly translated for this dry concrete room rather than copied as P1 bits.

## Isolation and limitations

`--experimental-pikmin2-room` selects a private Challenge 0 layout and rejects AP/BBFT session arguments. The overlay launcher creates a unique run directory and replaces only private stage/generator/model files; untouched assets are linked read-only by convention and must never be edited through the overlay. Do not recursively delete its directory junctions using tools that follow links.

Materials use vertex color multiplied by the first texture. Original multistage TEV shading on the bolt is approximated explicitly. The treasure retains the physical bounds of a five-Pikmin pellet; only its rigid visual and collection result are replaced. The room has prototype invisible boundaries, no cave exits or persistence, and no Pikmin 2 environment/audio/lighting recreation.

The standalone fixture builds with `engine/tools/verify_p2_room_windows.py` against a completed native Windows build. It samples actual engine ground, checks live actors, injects controller movement, assigns live Pikmin transport actions without moving them, and waits for actual delivery. Automated assignment does not substitute for manual throwing, combat or camera usability sign-off.

## Validation (2026-09-12)

Twelve focused Python tests pass (rigid conversion, collision/route export and experimental layout registration). The Windows production build passes. Native command-line checks reject AP-session arguments and multiple preview selectors with exit 2.

The final live fixture exited 0 after loading the converted room, verifying twenty live red Pikmin and one Dwarf Bulborb, sampling four native ground positions at Y=0, and moving Olimar 281.99 units with controller input while remaining on the floor. Actual transport AI delivered the imported bolt; the receipt recorded count=1, repairs=1 unchanged, and seeds=0. Twenty Pikmin then killed the Dwarf Bulborb through actual attack AI without forced damage or teleportation. The one starting repair comes from the inherited tutorial-skipped boot state, not the treasure.

Local evidence: `output/pikmin2-room-preview/25e03db572bd40bab335332dd03d212f/native.log`, `treasure-receipt.txt` and `p2-room.ppm`. Native source commit: `e89a09066bf1329646e20992628471d181fc26d9`. Manual throwing, controls and camera usability remain for playtesting; automated AI assignment does not cover those interactions.

The first visual validation exposed a converter error: a MOD matrix entry of -1 selects envelope 0, but these rigid models have no envelopes. This read past the model's animation matrices and made terrain move or disappear as other objects rendered. The exporter now writes direct joint 0, with a native-format regression assertion. Preview treasure buffers are explicitly allocated on the App heap so movie-heap resets cannot invalidate them.

After the matrix correction, startup/movement/final screenshots retain the floor, geometry/display-list hashes remain identical, and the actual render matrix matches the stationary camera. Room-edge camera occlusion and the black surroundings are still prototype presentation limitations.
