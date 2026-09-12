# Pikmin 2 room in Open Nectar (experimental)

Tracking: [#105](https://github.com/4laric/pikmin-randomizer/issues/105). This is a post-v0.1 content-conversion experiment, separate from Pikipelago seeds and the Pikmin 2 executable build.

The preview imports `room_4x4a_4_conc` and a rigid bolt treasure into the Pikmin 1 engine. It uses Pikmin 1 captain, Pikmin, enemy, collision, route and carrying systems. The private generator supplies one red Onion, 20 red Pikmin, one Dwarf Bulborb and one five-carrier treasure. Delivery writes `treasure-receipt.txt` without adding repairs or Onion seeds. This does not implement a Pikmin 2 campaign, procedural caves, two captains or new Pikmin species.

## Local inputs

Use an owned US Pikmin 2 GPVE01 revision 0 disc image and an existing extracted Pikmin 1 asset directory. Extracted assets and converted models stay under ignored `output/`; they are not part of the source distribution.

```powershell
python -m experimental.pikmin2_assets --iso "PATH/PIKMIN2.iso" --output output/pikmin2-extract105
python -m experimental.pikmin2_convert output/pikmin2-extract105/arc/view.bmd output/pikmin2-room105/render.mod --y-offset -1
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

## Carry-route and footing follow-up

Player testing found that distant corpses attached but stalled, while the nearby bolt still delivered. The source cave graph's points 7 and 8 only had outgoing edges; P1 selected these as delivery destinations. The private preview now adds only the audited approaches 4-to-7 and 4-to-8 in both embedded and external routes. Every original point and edge is preserved, and the reusable P2 collision exporter retains the original graph. Every point can now reach either goal; sampled carry corridors are dry and level.

The source room's visible interior floor is Y=1 while collision is Y=0. The preview room conversion uses `--y-offset -1` for render geometry only (not the treasure or collision). All 164 sampled interior points now match exactly; the original model differed by one unit at every sample. Normals, texture coordinates, topology and collision stay unchanged.

The earlier native fixture assigned transport to the bolt beside the Onion, so its pass did not cover the inaccessible far side of the route graph. The follow-up fixture adds actual enemy-corpse delivery from across the room.

Follow-up validation: fifteen focused converter/collision/preview tests pass. Native run `8356c998ccb240e2b2f96bf1f975cee5` exited 0: the actual Dwarf corpse moved over 360 units with carriers, entered the Onion goal state and was consumed. The fixture first tried free-AI recruitment; that did not recruit, so it explicitly assigned Transport after five seconds without moving actors. This validates the route from the user-confirmed attachment stage, not automatic recruitment. Production executable changes were unnecessary; relaunch rebuilds the private asset overlay with corrected routes and floor.
