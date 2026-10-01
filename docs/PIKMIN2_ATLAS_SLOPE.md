# Atlas source-position hauling candidate (#123)

Implementation owner: Codex, using the shared GitHub account `4laric`.
Private cave lane: `codex/p2-cave-lane`; root base `52cfbb3`, native base
`2c08d6b8`, native candidate `839c9f5ae0ed0dfc75d64b0054b07de4a9aaa20b`.
This is an experimental candidate for focused engine review. It has not been
integrated into the maintained checkout or player packages. Placement policy 2
remains unchanged. Independent natural-gameplay QA remains with #184.

## Problem and change

The original Atlas projection is `(0,10,640)`, with required strength 101.
Fresh baseline hauling with ten Purples and ten Reds (strength 110) repeatedly
stalls near `(-251,21,513)` on the real floor-2 ramp. This is distinct from the
already-fixed coplanar seam near the Pod.

`Creature::update` moves temporary velocity and ordinary velocity in two
passes. Both previously applied gravity, even when temporary velocity was
zero. The first pass retains its downhill positional displacement before its
velocity is discarded. Separately, grounded cargo replaces horizontal velocity
with the carry command but retains downward vertical velocity from previous
physics. Those effects can overwhelm this slow load's uphill progress.

The candidate changes only supported, registered P2 treasure:

- `Creature::moveNew` accepts `applyGravity`, defaulting to true. Existing
  callers retain that default. The temporary pass suppresses its extra gravity
  for lifted P2 cargo with sufficient Pikmin carriers on the static map. Both
  movement/contact passes and nonzero impulses still execute. The normal pass
  still applies gravity. No temporary mutation of the creature's gravity flags.
- In `Pellet::update`, an uphill carry command gets the vertical component
  required by the contacted floor plane: `vy = -(nx*vx+nz*vz)/ny`, when this
  exceeds its current vertical velocity. Horizontal speed and route remain
  unchanged. Flat/downhill commands, upward impulses, nonfinite values and
  normals at or below the floor cutoff retain their vertical velocity.
- Both gates exclude unregistered/P1 cargo, non-Pikmin carriers, insufficient
  strength and platform/unsupported contacts. No changes to topology, speed
  profiles, collision conversion, gravity constants, saves or rewards.

Six native files are exported into this private root branch: `Creature.h`,
`creature.cpp`, `creatureMove.cpp`, `pelletMgr.cpp`, the small
`pc_p2_cargo_ground.h` helper, and the cargo fixture include. Each existing
exported file was checked against the native base before replacement. Other
family source changes are not part of this export.

## Evidence and limits

The fixture stages a fresh private generator at the source projection. It
supplies synthetic Purple identity, assigns real transport AI, removes enemies
without reward credit and parks the captain out of the route. It does not
teleport cargo/carriers, force delivery or alter the carry route. An every-frame
assertion rejects any drop after initial lift while the cargo remains in its
ordinary transport state; normal Pod intake releases carriers afterward.
Tutorial suppression is fixture-only, after normal startup. This is controlled
native transport evidence, not physical player input or full campaign acceptance.

Two strict source hauls passed on the pre-final combined candidate, each with
one 200-Poko Atlas receipt and unchanged repairs. The final helper also rejects
overflowed nonfinite tangent results; all observed runtime inputs were finite.

Final rebuilt fixture SHA-256:
`608822a1e198ab86b2fbade3a7baa78df3553dbd01d1a08fadf38c3640df561a`.
Build: private MinGW/GCC Release, JAudio on, IPO off, test hooks off, three
compile workers. Full production build and fixture build passed. Fixture
provenance records native `839c9f5a`, empty tracked diff, local untracked build
logs, all inputs and compiler/link commands. Both freshness checks report
`ninja: no work to do.` No shared build outputs were reused.

All following paths are under
`C:/Users/alari/pikmin-randomizer/output/p2-cave-lane/output/atlas-reviewed`.
The directory name is a local test label, **not an engine-review approval**.

| Final-build case | Run directory | Result |
|---|---|---|
| Source Atlas, strict uninterrupted haul | `source/75e685c2cba94e9980463d2a248cf8fc` | Pass; 200 Pokos |
| Existing flat Atlas placement | `flat/2e081f0ad6f24c78995efbaca7616dfa` | Pass; 200 Pokos |
| Floor-1 tape treasure | `floor1/3442890afaaa490799363a36353c9c5d` | Pass; 100 Pokos |
| P1 scaffold first run | `p1-control/c5c380cf4cc546efbf6c391b9763d950` | Treasure passed; corpse observation failed |
| P1 scaffold strict repeat | `p1-repeat/15e7c5a7bdcd4e4faabdab889e50e27b` | Complete control passed |

Each run has `native.log` and `evidence.json`; P2 runs also preserve generator,
roster and `p2-economy.txt`. The P1 control uses ordinary P1 actors/transport in
an imported concrete room with no Pod, cargo registry or Purple opt-in. It is
not a full ordinary-map/P1-campaign regression.

The unchanged-gameplay baseline also passed the complete P1 control in
`output/atlas-baseline/p1-control/e6400d1865ae4bf58c45868fa42f02bd`.
The intermittent corpse-observation failure remains unclassified and tracked
in [#253](https://github.com/4laric/pikmin-randomizer/issues/253); a passing
repeat does not erase that finding. The P2 cargo gates are disabled in this
control. Broader natural P1/corpse acceptance remains open.

Twenty-five focused tests pass, covering the executed production movement gate,
analytic plane alignment and exclusions, strict evidence validation, source
cargo, Purple profiles, build provenance, roster, Pod, generator pose and
collision helpers. The movement-gate test records both actual production call
sites with a stub receiver; the game runs supply real collision/hauling evidence.

Rejected experiments and failed runs remain local. Vertical-velocity adjustment
alone and particle-correction changes failed and were removed. Native
`83b6e08f` (skip an empty temporary pass) and gravity-only variants each had an
apparently successful trip but failed strict repeats; they are not candidates
for standalone integration. A floor-1 runner initially looked for the
primary-only `treasure-receipt.txt`; it was corrected to validate the actual
`p2-economy.txt` entry for secondary cargo. Original failed evidence is preserved.

## Reproduce

Use a private native worktree at the candidate and its own completed CMake
build. From the root cave worktree:

```powershell
$native = 'C:/Users/alari/pikmin-randomizer/output/native-cave-lane'
python -m scripts.build_pikmin2_fixture --source $native --build "$native/build-cave" --fixture "$native/tools/preview_p2_room.cpp" --output output/new-atlas-fixture --expected-native-head 839c9f5ae0ed0dfc75d64b0054b07de4a9aaa20b
python -m scripts.test_pikmin2_atlas_slope --root C:/Users/alari/pikmin-randomizer --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets --output output/new-atlas-source --exe output/new-atlas-fixture/fixture.exe --timeout 300
```

The explicit `--assets` path is a read-only input. All staging, saves and logs
go under a new output directory. Existing local imports under `--root/output`
are required; no disc assets, binaries or runtime state are committed. Repeat
the run with `--flat`, `--floor 1`, or `--p1-control` for controls. Never run it
against an existing player/QA session. The script creates a fresh UUID directory
and times out only its own child process.

Focused review remains required for the new `moveNew` parameter and supported
cargo gravity/velocity semantics before shared integration. Natural hauling
with normal Purple acquisition, enemies present, broader map/platform/impulse
gameplay and restoring player placement policy remain open. This work does not
complete #129 retail topology, #193 marker visibility, or #184 return/restart
and reward-duplication acceptance.
