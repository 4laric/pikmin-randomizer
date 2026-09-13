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
than always looping the entire clip. This diagnostic display continues to use
30 source frames per wall-clock second; it is not a gameplay simulation clock.
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
