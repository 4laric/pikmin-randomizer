# Native Snow tracing receiver fixture (#120)

experimental.pikmin2_snow_chase_fixture instruments a private copy of the native
room fixture and calls actual TaiTracingAction::act on native Snow actors.
It does not change production source, live seeds or shared binaries.

The fixture explicitly starts a nonmatching Wait1 motion to test the motion guard,
then starts Move1 with no target to test the null-target guard. Both must leave
sentinel velocity/facing unchanged. Regular cases use a real captain as the target,
with position temporarily changed between direct calls and restored before exit.
The action uses a diagnostic fallback speed37, making the fixed source speed50
distinguishable from accidental use of the action's speed argument.

Five cases cover right/left targets, straight ahead, small yaw and359-to1 wrap.
Each runs across registered Snow, ordinary same-family actor, nonliving flag,
forgotten registry, reloaded bank and reset registry. The enabled profile must
turn first, produce horizontal target speed50 and preserve the prior Y component.
Other actors/configurations must retain the original moveTowardStatic output and
leave facing unchanged. The fixture records each direction and velocity result.

These are direct action calls. No movement tick runs between cases. Explicit
motion starts and a temporarily cleared ALIVE flag are fixture setup, not natural
P2 state selection or a physical corpse test. Physics, slopes, collision, full
chase locomotion and source animation timing remain outside this evidence.

## Running

```powershell
py -3.12 -m experimental.pikmin2_snow_chase_fixture instrument --source native/tools/preview_p2_room.cpp --output output/my-chase-fixture/preview_p2_room.cpp
```

Compile/link only after the production build completes, using current Ninja
objects and private source/object/executable/import-library outputs. Add
native/tools to the include path. Do not overwrite generic fixtures. Set PATH to
include C:/msys64/mingw64/bin and SDL_AUDIODRIVER=dummy.

Run with `run --assets PATH --converted PATH --pod PATH --snow PATH --exe PATH
--output NEW_DIRECTORY`; supply `--policy PATH` for the extracted chase profile
and omit it for the P1 baseline. Output includes native.log, capture metadata,
measured velocity/direction cases and evidence.json. Executable identity is
captured before launch and checked against capture provenance.

Ten harness tests reject missing guards/cases/actors, duplicate evidence, wrong
mode and mismatched direction or velocity. There are26 tests together with the
chase policy suite. Native runtime results are recorded below.


## Runtime evidence

Fresh native2dcced12 production objects compiled/linked successfully into the
private fixture using the current Ninja object list. Recipe:
output/p2-chase-runtime/fixture/commands.json.
Executable SHA256:
`5ef5692165cacdd1019cbbae1e84e7c96a4331bd096d4d26aab026ada8b77eb4`.

Both output/p2-chase-runtime/opted/evidence.json and baseline/evidence.json pass
with exit0 and matching captured executable identity. Each run verifies30 measured
regular action calls plus the motion and missing-target guard calls. The opted
right-angle case measures9.999999 degrees and target velocity
(8.6824093,7,49.2403870). The absent policy produces unchanged facing and the
original diagnostic speed37 vector(37,0,0). Ordinary/nonliving/forgotten/reset
actors preserve that P1 path; reload restores configured chase behavior.

Small yaw and wrap cases use the native target-angle calculation, so their
measured steering can differ slightly from ideal trigonometric reference angles.
No physical displacement or natural chase state transition was exercised by this
fixture, and no visual/physics parity claim is made.
