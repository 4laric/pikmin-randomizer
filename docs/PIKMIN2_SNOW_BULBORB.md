# Snow Bulborb enemy preview (#120)

This is the first opt-in Pikmin 2 enemy asset pipeline. It imports the actual
Kochappy model, Snow texture and sampled BCA poses from a local retail disc.
The native actor still uses P1 Dwarf Bulborb AI, collision, attacks, sounds,
health and animation-event timing. It is not a completed port of the P2 FSM.
Ordinary P1 enemies are unchanged unless explicitly listed in a private preview.

## Source mapping

Emergence Cave's `user/Mukki/mapunits/caveinfo/tutorial_1.txt` selects
`YellowKochappy`, not `BlueKochappy`. The internal color name is not a safe
English-species lookup. `YellowKochappyMgr.cpp` loads
`enemy/data/YellowKochappy/kochappy_body_s3tc.2.bti`; `YellowKochappy.cpp`
replaces texture image zero. `KochappyBaseMgr.cpp` shares the Kochappy model
and animations across the color variants. These files are in the local P2
source reference under `src/plugProjectYamashitaU/`.

The importer reproduces image-zero replacement using `enemy/data/Kochappy/model.szs`
and `anim.szs`, preserving other images. Five motions (wait1, move1, attack,
dead, flick) each use up to 12 immutable sampled meshes. Nonuniform BCA scale
is explicitly enabled only for this importer; normals use inverse-transpose
transforms. This is a rigid pose-bank renderer, with no blending, source event
translation, or general J3D material fidelity. Normalized P1 motion progress
selects the source pose; corpses hold the final death pose.

## Reproduce locally

Run from the root checkout:

```powershell
py -3.12 -m experimental.pikmin2_enemy --iso C:/path/to/PIKMIN2.iso --output output/snow-import
```

The import records source SHA256s in `snow.json`. Extracted files stay local.
After preparing a private Pod preview, call
`experimental.pikmin2_enemy.install(imported, run, generator_ids)` with an
explicit list of existing native Chappy generator IDs. It copies model files
into the private room and writes `p2-snow.txt` and `p2-snow-actors.txt`.
No default campaign, seed, or shared base-asset directory is changed.

Native setup rejects missing, duplicate and wrong-family IDs. The actual
species identity is separate from the reused native family, logged as
`species=YellowKochappy native_family=Chappy behavior=P1`.
The existing floor-scoped corpse receipt remains authoritative; its title is
Snow Bulborb, and Pod delivery retains its no-seeds/no-repairs behavior.
The integration owner must include the optional assets in the content fingerprint
before enabling them in a durable cave profile. This track does not edit the
checkpoint schema, cave placement generator or active player bundle.

## Remaining work

Translate P2 KochappyBase states, parameters and events; align collision and
mouth/attachment joints to the new skeleton; validate stomp/flick/attack timing,
source scale compensation and every animation; then integrate the complete
source cave placement roster. P1 animation phases can visibly differ from P2.
The reusable module is bounded to explicitly opted-in existing Chappy actors.

## Validation

Thirteen focused importer, BCA, rigid conversion and assembly tests pass; eight
existing local-asset tests skip because this isolated worktree has no prior
imports. Retail extraction produced all 60 pose meshes. Changed native objects
compile with the Windows production flags; the private fixture links against
the completed game objects without changing the active game build.

The real native room fixture passed treasure transport, native Pikmin attack AI
killing the opted-in actor, then corpse transport and delivery: 180 treasure
Pokos plus 2 corpse Pokos, unchanged repairs and no Onion seeds. As in the
existing route fixture, corpse free recruitment needed direct transport-action
assignment; positions were not teleported for that gameplay test. This is a
P1-behavior regression, not proof of authentic P2 enemy behavior.


Native increment: `a705749e`. The synthetic close-up capture verifies a white
body with blue spots using the imported mesh. `P2_SNOW_DRAW corpse=0` confirms
the opt-in draw hook ran. The first private link accidentally retained the
legacy archive's original drawing member; this was caught by the screenshot,
corrected in the private link, and is not counted as Snow-render validation.
A regular CMake build compiles the modified legacy source directly.
