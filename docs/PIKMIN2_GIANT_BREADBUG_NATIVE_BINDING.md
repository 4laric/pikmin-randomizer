# Giant Breadbug isolated native display binding (#229)

Codex owns this native handoff; Kimi owns source/import #220. This adds an
optional visual-only Giant and nest display. It registers no Teki, collision,
cargo, rewards, boss flag or gameplay behavior. Small Breadbug code/config is
unchanged. A move display animates in place.

## Root integration

Copy `native-patches/giant-breadbug/pc_p2_giant_breadbug_visual.cpp` and `.h`
into native `pc_port`, then apply `native-patches/giant-breadbug/hooks.patch`
from the native root. The patch adds the CMake source plus independent
setup/draw/reset calls adjacent to existing small-Breadbug calls. No shared
native files were edited or built by this lane. The patch was generated
against the read-only original native source; root must review current
contexts before applying. Source models remain local and are not committed.

The binding only enables in room preview, with `p2-giant-breadbug-visual.txt`.
Missing config is a no-op after reset; malformed present config aborts.
Reset forgets all display/clip/heap-owned shape pointers and counters before
another setup; it does not delete shapes owned by the engine heap.

```
P2_GIANT_BREADBUG_VISUAL_1
wait <source-duration> <count> <strictly-increasing-frames...>
move <source-duration> <count> <strictly-increasing-frames...>
<display-count>
<unsigned-display-id> wait|move|nest <x> <y> <z> <yaw-degrees>
```

Source durations are 2..10000, samples 2..12 with both endpoints, display
count 1..8, unique uint32 IDs, finite XYZ within 100000 and yaw within 360.
Files are fixed by protocol: `lane_ootake_wait1_NNN.mod`,
`lane_ootake_move1_NNN.mod`, `lane_nest_nest.mod`. Maximum 2 MiB/model and
32 MiB/bank; existing MOD resource validator executes before engine load.
No arbitrary path/model tokens. Draw uses unit scale and source 30 fps display
clock, independent of actor AI. Texture-matrix animation remains the import's
static approximation. Native validates structure/bounds; the host verifies
source/staged/model/config hashes before install and rereads installed bytes.

## Host and local evidence

`experimental.pikmin2_giant_breadbug_visual.prepare(lane_import, lane_profile,
output, placements)` binds the exact #220 staged models to source duration,
pose and nest hashes. `install(profile, run)` copies only the 11 Giant/nest
models into a fresh private course directory and writes the separate config.
It refuses overwrite and does not replace small-Breadbug models/config.
The module CLI accepts --lane-import, --lane-profile, --output and --placements.

Real source: original root `output/p2-lifecycle-batch/breadbug-lane-03`;
lane profile: `breadbug-lane-install-01/profile`. Integration worktree outputs:

- `output/p2-giant-breadbug-binding/profile-a` and `profile-b`: identical profiles.
- `run-a` and `run-b`: verified private installations, not launchable stages.
- `compile/compile.json`, `compile/compile.log`, `compile/giant.o`: actual
  isolated native module compilation exit 0 using the current Ninja compile
  flags and read-only original native headers. Existing header warnings remain.
- Config SHA256: `c9ceaedaadd050ef4cc1241e5cc138ccad6c5f5114eeee1a6f68fc65f7285402`.

Example display IDs 229001..229003 are display identifiers, not generator
IDs. XYZ are explicit engineering proposals, not source placements or a
terrain-validated arena. Root runtime must stage a known collision scene.

Six focused tests pass: real byte reproducibility/install, no-write tamper
rejection, overwrite, invalid placement, source identity, metadata/config
agreement; an executable test extracts the actual native parser and runs nine
valid/malformed cases. No rendered-frame, reset/re-entry or runtime-load pass
is claimed by compilation. These remain next native acceptance gates.

## Actual Giant actor requirements still open

Use #220's `PIKMIN2_BREADBUG_LANE_AUDIT.md` and source PanModoki/OoPanModoki
implementations as authority. A display cannot satisfy these:

1. Register source species 40 with its own boss/variant identity. Never spawn
   alias39 or helper83 as independent enemies; preserve species38 small proxy.
2. Implement source Giant Purple-only press/stun eligibility and variant
   parameters; do not copy small-Breadbug damage rules by appearance.
3. Implement cargo owner/contest arbitration, pull strength and losing-contest
   transitions against native carriers, with explicit no-duplicate ownership.
4. Link a nest to its owner and model house type, digest/storage limits and
   defeat/recovery behavior. Persist stored treasure across save/day transitions;
   AP reward ownership must remain separate from moving or storing a model.
5. Validate actual combat, dragging, nest arrival, loss/recovery, death and save
   replay with correct receipts. Retain texture-matrix fidelity as a separate
   visual gate and avoid claiming a complete P2 FSM from a P1 proxy.
