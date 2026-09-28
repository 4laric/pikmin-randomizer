# Small Breadbug visual-only arena prototype

Scope #168/#186. New `pc_p2_breadbug_visual.h/.cpp` is a world-model renderer,
not an enemy implementation. It creates no BTeki, collision body, health, AI,
cargo owner or receipt. A walking clip animates in place. Giant is excluded.

`experimental.pikmin2_breadbug_visual.prepare(imported, output, placements)`
validates the previous local extractor hashes, samples actual wait1/move1 BCA
poses, converts them to MOD and packages the static source nest. Placement
records use `display_id`, `kind` (wait/move/nest), position XYZ and explicit
visual yaw_degrees. Display IDs are not generator IDs; family assets and display
placements remain separate. These example coordinates are engineering display
coordinates, not source positions or validated arena terrain anchors.

`install(profile, private_run)` copies the verified files into a private
non-junction model directory and writes `p2-breadbug-visual.txt`. It rejects
existing targets and verifies every model before writing. It does not patch
any map, generator, native executable, live seed or shared asset directory.

Config `P2_BREADBUG_VISUAL_1` contains two fixed named clips. Each row supplies
source duration,2..12 monotonically increasing sample frames covering0 through
duration-1. It then lists1..8 displays with unique32-bit ID, kind, XYZ and yaw.
The native reader rejects malformed/trailing input, invalid bounds, missing or
oversized models and invalid MOD resource structure. Unknown kinds cannot opt
into Giant or a gameplay actor. The renderer loops sampled poses at30 source
frames/second using a visual wall clock, including while gameplay is paused;
it does not advance any simulation or execute source animation events.

Root-owned integration hooks requested and approved:

- `pc_p2_breadbug_visual_setup()` after assets/gameflow are ready. It resets
  previous state and requires the room-preview flag plus explicit config.
- `pc_p2_breadbug_visual_reset()` during stage cleanup before backing shape
  storage disappears. Shape allocation follows existing gameflow arena lifetime.
- `pc_p2_breadbug_visual_draw(Graphics&)` at the same world-overlay boundary as
  the existing cave transition model, after world rendering and before HUD.
  It restores camera perspective/material/depth, creates world SRT, multiplies
  camera look-at to view, then updates/draws each Shape. The caller resets state
  for subsequent UI, as with the existing transition reference.

Root owns CMake and all shared setup/draw/reset callsites. This lane did not edit
those files or run a shared native build. Until those hooks and a fixed private
runtime fixture are tested, `native_validated=false` stays set. Resource loading
success alone is insufficient: readiness logs must match exact display XYZ/yaw,
and a capture must verify both sampled motion and nest placement against the
control scene without corrupting HUD/depth. Native logs use
P2_BREADBUG_VISUAL_READY and P2_BREADBUG_VISUAL_DRAW with explicit visual-only
labels.

Local profile: `output/p2-lifecycle-batch/breadbug-visual-01`,17 models. Wait
source duration59, sampled frames0,8,17,25,33,41,50,58. Move duration54, frames
0,8,15,23,30,38,45,53. Materials remain the extractor's approximation and poses
are sampled rather than interpolated skeletal playback. No visual capture or
native execution is claimed in this batch.

Six Python tests pass across visual installer and asset reference. They cover
placement count/identity/kind/finite-coordinate validation, asset hash mismatch,
all-before-write validation and overwrite refusal. Source profiles and retail
assets stay local; no export or commit performed by this lane.
