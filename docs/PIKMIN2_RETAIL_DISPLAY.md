# Retail timing in a native sampled display

Issue #268, Codex implementation owner using shared GitHub account 4laric.

The Bulblax display now accepts optional `p2-bulblax-retail-Queen.txt`,
`p2-bulblax-retail-Baby.txt` and `p2-bulblax-retail-KingChappy.txt` in its private
working directory. These use the event protocol in PIKMIN2_MOTION_EVENTS.md.
Only selected display clips load a player. Clip filename and duration must
match the sampled display profile; invalid tables or missing selected motions
fail explicitly. No table retains the existing looping display clock.

The renderer selects the nearest sampled pose using the retail player's source
frame. Authored loops and one-shot completion now control that frame, rather
than always looping the entire clip. Since #272, retail playback uses 30 source
frames per active simulation second. The GameCore update hook shares the Teki
update's pause, UI, movie and inPause gates. Drawing does not advance retail
players, so paused wall time is not accumulated and replayed on resume. Legacy
displays without retail tables retain their decorative wall-clock behavior.
Events are logged, never sent to actors or reward logic. Logging is capped at
64 events per loaded clip per setup. Reset clears all players and log counters;
reload starts them fresh. Materials, transforms and mesh loading are unchanged.

The fixture stages tables from local source imports and records each table's
SHA-256 in bulblax-stage.json. The table embeds registry/BCA hashes. Native
binding checks name/duration, not cryptographic identity against pose geometry;
this is a diagnostic pairing, not a new production asset-integrity guarantee.
Original source assets and generated event tables are not committed.

Use the existing private runtime builder, then opt in when running:

```text
py -3.12 -m experimental.pikmin2_bulblax_runtime run --assets <local-assets> --profile <validated-display-profile> --output <fresh-output> --exe <private-fixture.exe> --retail-sources <import-root>
```

The import root contains Queen, Baby and KingChappy directories with their BCA
files and enemyanimmgr.txt. Omitting --retail-sources preserves the legacy
fixture. The disabled case stages a table but no display, testing the opt-in
boundary. Acceptance checks include matching source events, events after reload,
sample changes, reset, stable actor/cargo/repair counts and disabled GX baseline.

This is native renderer integration of timing with existing sampled meshes.
Boss AI, combat receivers, interpolated skeletal animation and mesh blending
remain outside this batch.

The read-only `pc_p2_bulblax_visual_frame(displayId, frame)` query returns false
for absent, legacy or reset displays. `pc_p2_bulblax_visual_update(seconds)` is
called once from the active GameCore path; callers must not also tick it from
draw or a second actor hook. It does not dispatch gameplay effects. Since #277,
each retail display has its own player and event log budget keyed by display
ID; displays share only loaded pose meshes. `pc_p2_bulblax_visual_seek(id, frame)`
changes one instance, returning false for missing/reset IDs or invalid frames.
Event diagnostics include the display ID. Legacy decorative clocks stay shared.

The retail fixture now adds a synthetic second display of the same clip, with
a new ID and x+80 offset. It seeks that instance and verifies the sibling frame
is unchanged, while continuing pause/resume and reset tests. This duplicate is
fixture content, not a new source placement or enemy actor.

Validation at native c541b0ff: production Release build and private fixture
build passed; 15 focused test methods passed. Queen, Baby, KingChappy and the
disabled control all passed the native fixture, including source-event matching
and reload events, with no additional GX warnings against the disabled case.
A separate Queen run without event tables passed the legacy display checks and
emitted no retail diagnostics. The inspected Queen reload capture retains the
known black/silver material appearance; this timing change does not fix it.

Local evidence (private engine root worktree):
`output/retail-display268/validation/result.json`,
`output/retail-display268/legacy-result.json`, and
`output/retail-display268/build/provenance.json`.
Fixture SHA-256:
`07c0631a2f78d710861343fbf55c882735a4f77012a1f0f73ab11ee788c78934`.

Simulation follow-up #272 at native f2173b51: production and fixture builds
passed, as did 15 focused test methods. Queen, Baby and KingChappy each passed
real-engine pause-all and UI-overlay freeze checks across multiple idle/draw
cycles, followed by resumed position movement. All existing retail event,
reset/reload and unchanged actor/reward checks passed. Disabled and separate
legacy Queen controls passed; no additional GX warnings were recorded. Movie
and inPause suppression are covered by placement under the existing update
gates, not by a synthetic movie runtime test. No gameplay parity is claimed.

Evidence: `output/simulation272/validation/result.json`,
`output/simulation272/legacy-result.json`, and
`output/simulation272/build/provenance.json` in the private engine root worktree.

Instance follow-up #277 at native bef5232e: production and fixture builds
passed; 15 focused tests passed. Queen, Baby and KingChappy each passed the
two-display independent-seek assertion, pause/resume, source events and
reset/reload. Disabled and legacy Queen controls passed. The duplicate shares
the existing per-clip mesh cache; no additional bank load path was introduced.
The fixture asserts playback independence and unchanged gameplay counts, not
enemy AI or physical collision independence. Evidence is under
`output/instance277/validation/result.json`, `output/instance277/legacy-result.json`
and `output/instance277/build/provenance.json` in the private engine root.
