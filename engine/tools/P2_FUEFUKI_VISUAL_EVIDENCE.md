# Fuefuki converted-pose visual — real-GL runtime evidence (#245)

Status: **executed, PASS**. The `P2_FUEFUKI_VISUAL_*` markers below came from an
actual real-GL run of the lane fixture in a room staged with the converted
Fuefuki pose bank (`docs/PIKMIN2_FUEFUKI_ASSETS.md`, `experimental/
pikmin2_fuefuki_stage.py`).

## Scope

Real in this run:

- the frozen P1 host booted with `--experimental-pikmin2-room` on a real
  SDL2/OpenGL window (960×540, centred);
- `pc_p2_hardlanes_setup` parsed the staged `p2-fuefuki-visual.txt`
  (`P2_FUEFUKI_VISUAL_1`) and loaded all 8 converted clips as real `Shape`s
  through `gameflow.loadShape`;
- `pc_p2_hardlanes_draw` drew the active pose through the live camera
  (`P2_FUEFUKI_VISUAL_DRAW`), and the follow-locomotion phases still passed in
  the same run.

Not covered / limitations:

- **Vehicle:** the fixture moves a scripted anchor; a separate real-vehicle run
  is recorded below. Native Fuefuki **identity** (enemy 41) is still not
  registered — the vehicle is Napkid 11 (`native_identity` BLOCKED).
- `landing`/`landfail` are absent (singular source joint scale); the profile
  lists only the 8 converted clips.
- Baked rigid poses with approximate materials; no skeletal playback or
  key-event execution, no whistle effect ring, no audio and no camera-facing
  billboard orientation.
- No material/visual fidelity acceptance versus retail.

## Provenance

- Native branch `opencode/p2-lane28-fuefuki-follow`, HEAD
  `ca7f9da74eb5e2e38aa4dcd8fd5eb087884c8a3c` (visual module + hardlane draw +
  anchor API + state→clip mapping driven by the fixture).
- Private build `output/lane28-fuefuki-build`, Ninja Release, MinGW-w64 g++
  16.2.0, JAudio ON; `ninja pikmin_pc -n` => no work.
- Fixture `output/p2-lane28-follow-runtime-07/fixture.exe`, SHA-256
  `B2224121314D323C4BD111CF70D680B011A162F180E6BC8C259586F9990FECB2`
  (supersedes `…-05` `4CB86081…`).
- Stage `output/p2-fuefuki-stage-01` (`stage.json`: 8 clips, 31 poses,
  unsupported landing/landfail), overlaid onto the run room
  (`assets/dataDir/courses/pikmin2room/`).

## Marker output (verbatim from run.log)

```
P2_FUEFUKI_VISUAL_READY clips=8
P2_HARDLANES_READY family=Fuefuki visual=1 clips=8
P2_FUEFUKI_VISUAL_DRAW clip=wait pose=0
P2_FUEFUKI_VISUAL_STATE state=7 clip=whisle pose=0
P2_FUEFUKI_VISUAL_TRACK x=0.0 z=-115.0 clip=whisle pose=2
...
PASS FUEFUKI_FOLLOW_RUNTIME
```

The final run adds: FSM state 7 (Whisle) maps to the `whisle` clip
(`P2_FUEFUKI_VISUAL_STATE`); the visual anchor follows the scripted moving
beetle to z=-115.0; and the pose advances within the clip (`pose=2`) because
the clip is only re-selected on a change. The follow-locomotion phases pass in
the same run.

## Real-vehicle arena run

`experimental/pikmin2_fuefuki_arena.py` (cargo-free preview) + the overlaid pose
bank, run with `nectar.exe --experimental-pikmin2-room` at the same native HEAD:

```
P2_HARDLANES_READY family=Fuefuki vehicle=Napkid follow_locomotion=actteki_volatile_approx
P2_FUEFUKI_VISUAL_READY clips=8
P2_FUEFUKI_VISUAL_DRAW clip=wait pose=0 x=-150.0 y=30.0 z=1850.0
P2_FUEFUKI_FSM state=2 clip=wait
```

`(-150, 30, 1850)` is the arena's Napkid placement, so the converted Fuefuki
pose is drawn at the real placement vehicle.

## Motion bank drives the FSM (real vehicle)

`pc_p2_fuefuki_motion` loads the converted `P2_RETAIL_EVENTS_1` table
(`experimental/pikmin2_fuefuki_motion.py`) and `pc_p2_hardlanes` plays the clip
for the current FSM state through the vendored `p2retail::Player`, feeding
`KEYEVENT_2/3` and clip completion. On the real Napkid vehicle the FSM now
cycles and the visual clips follow:

```
P2_HARDLANES_READY family=Fuefuki motion=1 clips=10
P2_FUEFUKI_FSM state=2 clip=wait
P2_FUEFUKI_FSM state=3 clip=jump
P2_FUEFUKI_FSM state=1 clip=jump
P2_FUEFUKI_FSM state=2 clip=wait
...
```

It cycles `Land -> Jump -> Stay` rather than `Walk/Turn/Whisle` because a nearby
captain triggers the source jump-away (intruder) behaviour. The source Beetle
animation bank (#128) is still the eventual feed; this table is the host stand-in.

Material upload is fixed: every sampled pose attaches its own textures, dropping
the engine `[PC GX Warning] ... nunca se subió` (texture never uploaded) reports
from the 8-report cap to **0** in this run. Converter materials remain
approximate (provider 09).

## Next steps

- Provider 09 material fidelity and the whistle effect ring; audio (#128).
- Source Beetle animation bank (#128) to replace the event-table feed.
- Native Fuefuki identity (enemy 41) registration (`native_identity` BLOCKED).
