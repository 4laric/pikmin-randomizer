# Native bounded entrance fixture (#114)

This batch supplies a real fenced native collision fixture around the source Emergence entrance. It is **not a player launcher** or a playable surface/cave roundtrip.

`stage_pikmin2_entrance.py` retains the original32 source triangles and adds64 clearly labeled engineering wall triangles in a32-sided ring of radius60. Walls extend fromY-1920 to4176, face inward and add no floor. Whole-source rendering stays aligned; the invisible walls intentionally prevent reaching visible unsupported terrain. All three source water boxes remain in the sidecar. There is no native water consumer; only the previously validated dry pocket is exercised.

`pikmin2_entrance_fixture.cpp` is a standalone test App linked against existing production objects, not a production source change. It verifies source groundY80 and20 live Red Pikmin, then runs864 actual native map traces across captain/Pikmin/cargo specimens, radii6/10/20, heights120/400/4000, and32 directions. Every trace reaches the wall and remains within the declared disk. It additionally runs120 real `Piki::moveNew` steps for an airborne specimen. This is collision integration evidence, not controller/throw animation or entry/return acceptance.

The tiny fixture has no hauling receiver/routes. Production preview setup still requires a cargo specimen; the custom fixture sets its carrying requirement to1000 immediately so nearby Pikmin cannot begin a haul to a missing Onion. The first test without this fixture-only restriction correctly hit the existing `aiTransport.cpp` missing-goal panic; production code was not altered. **Do not launch this staging directory with the ordinary game executable.**

Validated local run: `output/p2-lifecycle-batch/entrance-boundary/454104b7f9754804a3faa9c88ce5bd97/native2.log` (exit0). `fixture-provenance2.json` records exact executable path/hash before launch. Private build recipe and logs are in `output/p2-lifecycle-batch/entrance-fixture/commands.json` and `build.log`; compilation substituted the new fixture source/object/executable into the existing `build-randomizer` fixture recipe, without rebuilding shared objects. Run uses SDL dummy audio and a120-second timeout.

Nine focused tests passed: source preservation, manifold walls, inward/vertical geometry, body clearance, and entrance source/probe regressions. No CMake, per-Creature hooks, native production files, player saves or shared builds changed.

Stage command: `py -3.12 -m scripts.stage_pikmin2_entrance --assets <P1 assets> --source-import <Valley source import> --pocket <entrance-pocket output> --treasure <converted treasure.mod> --output <private output>`.
