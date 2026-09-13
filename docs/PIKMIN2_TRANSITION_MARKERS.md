# Cave transition marker integration (#112)

Codex implementation owner through shared account 4laric; scoped in issue #112 comment 5647032536. This is a bounded increment on the experimental cave lifecycle, not a complete surface round trip or imported hole/geyser actor.

## Contract

`experimental.pikmin2_campaign --transitions <directory>` optionally reads both `floor1.txt` and `floor2.txt` before opening the session. Their exact bytes enter the content fingerprint and are staged as `p2-cave-transition.txt` on each floor. Editing marker positions therefore requires a new session; old no-marker sessions retain their original content fingerprint. Files are read once so a concurrent edit cannot change the staged geometry after hashing.

Format (six whitespace-separated fields):

```
P2_CAVE_TRANSITION_1
hole 100 0 -200 60
```

The example is a format illustration, **not an audited location**. Fields are kind, world X/Y/Z and activation radius. Floor 1 requires `hole`; floor 2 requires `geyser`. Coordinates must be finite and within ±100000; radius is 20–150 engine units. Native validation independently rejects malformed/trailing data. Content integration must pick grounded, accessible positions from its final layout.

With a marker configured, F6 and the shared checkpoint guard require the captain inside its horizontal ring and within 40 vertical units, in walking state. Without the config, F6 retains the original Pod interaction. Failure/extinction still commits without requiring the captain to reach an exit. Pauses, movies, converting/swallowed Pikmin, planted sprouts and duplicate transitions retain existing guards.

Native integration exposes:

- `pc_p2_cave_draw_transition(Graphics&)`: invoke once after world actors and before HUD setup. Draws an amber ring/down arrow for a hole or cyan ring/up arrow for a geyser. This is deliberately an engineering marker. It leaves the camera-view matrix selected; subsequent UI must establish its own matrix. It restores the basic color, texture, lighting-enabled and line-width settings, not arbitrary material/GX state.
- `pc_p2_cave_interact(x,y,z)`: a future physical actor/input hook can queue the same request. Both the actor position and captain must be inside the configured anchor. Tick rechecks checkpoint guards before writing. A true return means queued, not committed.

This track does not modify the shared world-render callsite or content placement generator; the integration owner wires those. It also does not replace A's existing grab/pluck behavior. F6 remains the tested input path until a contextual controller hook is integrated and playtested.

## Source audit and limits

The local Pikmin 2 decomp's `src/plugProjectKandoU/navi.cpp::Navi::update` checks hole and geyser proximity on A before ordinary navigation, and checks the geyser's opened state. `singleGameSection.cpp::openCaveMoreMenu` opens a confirmation menu and pauses gameplay. `singleGS_CaveGame.cpp::onNextFloor` targets the physical hole for the descent movie; its movie callbacks save the next floor and survivors. The escape movie uses the geyser position and later saves survivors.

Our marker follows the location → confirmation → boundary handoff structure. It does **not** implement source collision actors, geyser break/open state, movies, two captains or return to the surface. Checkpoint schema 1, fresh token and exit code 42 are unchanged. The saved result after floor 2 is still terminal.

## Validation

Focused Python validation: 9 tests and 9 subtests passed, including the existing lifecycle contract, optional configuration, immutable staged bytes, invalid layouts and coordinate-sensitive content identity. A standalone C++ test covers kind/floor matching, geometry boundaries, vertical separation, nonfinite input, trailing tokens and no partial mutation on failed parsing.

The native cave module and the updated real-engine fixture both pass syntax compilation with the Windows port defines/includes. The fixture now understands optional anchors and checks distance, wrong-height and foreign-actor guards before its existing transfer test. It has **not yet been linked/run with these new markers** in this isolated track. No new player binary is published by this track; combined native build, rendered marker inspection, controller playtest and floor handoff are integration gates.

Standalone parser test (MinGW runtime on PATH):

```
g++ -std=c++17 -Inative/pc_port native/tools/test_p2_cave_anchor.cpp -o output/test-anchor.exe
output/test-anchor.exe
py -3.12 -m pytest tests/test_pikmin2_campaign.py tests/test_pikmin2_transitions.py -q
```
