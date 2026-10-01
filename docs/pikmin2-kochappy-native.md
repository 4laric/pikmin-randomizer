# Dwarf Red visuals and health (#120 / #186)

This increment adds a separate `pc_p2_kochappy` native family module and `experimental.pikmin2_kochappy_bank` builder/installer. It supports source identity `Kochappy` (ID 1), Red texture and sampled source poses, and per-actor initial/max health 200. It continues using P1 Chappy AI, collision and animation event timing. Purple stun duration 10 seconds is recorded in the source reference but is not implemented here.

## Interfaces

The integration lead adds `pc_port/pc_p2_kochappy.cpp` to CMake and calls `pc_p2_kochappy_setup()` after existing Snow/Sheargrub setup from the preview/arena setup path. No configuration means no effect. Partial configuration aborts before allocation. The module requires three separate files:

```text
p2-kochappy-profile.txt:
P2_KOCHAPPY_PROFILE_1
species Kochappy
health 200

p2-kochappy-actors.txt:
P2_KOCHAPPY_ACTORS_1 <count>
<unsigned-generator-id> ...
```

`p2-kochappy-bank.txt` starts with `P2_KOCHAPPY_BANK_1`, followed by ordered wait1/move1/attack/dead/flick rows containing pose count, source duration and source frame indices. It uses the shared animation timing parser internally, but rejects a Snow header at its external boundary and never registers an actor as Snow.

Native setup resolves the entire unique actor roster, rejects wrong native types, unknown/duplicate IDs and existing family bindings, and validates every bank file/resource budget before loading Shapes. Each binding logs source identity, generator ID, effective native XYZ and health. Profile files contain no placement or yaw. The installer takes IDs allocated by the arena owner and writes no generator records.

Small central delegates handle max-health lookup, live/corpse drawing, display name and manager reset/slot reuse. Normal P1 actors retain their original health. Reset and forget clear both health and visual identity; death alone does not erase identity before corpse rendering/collection. Family health is stored per actor, without editing shared Chappy parameters. Snow setup also rejects an already-bound Red actor, making overlap rejection work in either setup order.

## Asset and memory boundary

The builder verifies source model/clip hashes, requires the audited reference profile, and defaults to 12 poses per clip. Local extraction produced 60 poses and 960,000 MOD bytes in about 0.25 seconds. Each clip is capped at 512 KiB and the bank at 2 MiB; 24 poses are allowed within those caps. Source-frame endpoints include the final death pose.

Before sharing resources, native loading verifies the texture/material chunks are byte-identical across poses. Geometry stays per pose; one material/texture set is used for drawing and GPU texture attachment. As with the Snow path, `loadShape` still allocates CPU resource copies on the scene heap. Native load cost and actual render/lifecycle safety require runtime validation; extraction timing is not a frame-rate measurement.

## Validation and remaining gates

- 44 focused bank/profile/health tests pass, including a compiled native helper test for health 200, ordinary fallback, null/duplicate bind, forget/reset/reused address, invalid profile and unsigned/duplicate/trailing binding inputs.
- Four changed native translation units compiled successfully into private `output/p2-dwarf-red-native/objects`: new family module, central enemy-name dispatcher, BTeki and TekiMgr. No shared production build or export was performed by the worker.
- Retail bank generation and installation into a fresh private prepared directory passed. See `output/p2-dwarf-red-native/install.json` for the staged directory and input generator identity. This is staging evidence only, not native full-XYZ spawn acceptance.
- Root integration must add the setup/build delegates, then build and validate a fixed arena with Red plus an ordinary P1 control. Autonomous movement/attack, natural defeat, corpse transport/value, duplicate receipt and subsequent stage/slot reuse remain untested for Red.

The first arena must follow [the full XYZ and identity contract](PIKMIN2_ENEMY_ARENA.md), with exact binary/profile hashes and a fresh private session. No source yaw is applied by this installer. No live playtest seed was changed.
