# Long Legs family — batch 2 install + arena (#312, parent #173)

Batch 2 takes the lane's batch-1 bind-pose mesh profile (`long-legs-family.json`,
produced by `experimental/pikmin2_long_legs_assets.py` on branch
`codex/p2-longlegs-family`) into a private runtime layout and stages a private
original-map arena.

## Deliverables

- `experimental/pikmin2_long_legs_install.py` — hash-bound
  `plan`/`install`/`verify_install` over the lane manifest. Validates
  `schema == 1`, `family == "Long Legs"`, the exact `{66, 69}` profile set and
  per-profile `enemy_id`; requires the audited live/attack/death anchors
  (`Houdai` wait/attack/landing, `BigFoot` wait/flick/dead); binds each
  `BigFoot/`/`Houdai/ enemy.bmd` by its recorded `model_sha256`; refuses
  conflicting or changed sources before mutation; preserves the baseline when
  the mesh bank is absent; writes schema-1 profile/bank/actor configs plus a
  receipt.
- `experimental/pikmin2_long_legs_arena.py` — private original Impact Site
  staging via the shared `experimental/pikmin2_batch2_core.py` arena builder:
  Houdai (312001), BigFoot (312002) and one ordinary P1 control (312003), full
  expected XYZ, zero offset, source yaw unapplied.
- `tests/test_pikmin2_long_legs_install.py` — installed-artifact and
  arena-contract tests (synthetic mesh profile with real bytes and recorded
  hashes).

## Real-disc evidence

Install + verify round-trip against the lane decode
`output/p2-longlegs-family/output/long-legs-decode-1/long-legs-family.json`:

- **2 installed, 2 verified** (`Houdai_enemy.bmd`, `BigFoot_enemy.bmd`,
  SHA-256 bound to the manifest).
- Configs: `p2-long-legs-profile.txt`, `p2-long-legs-bank.txt`,
  `p2-long-legs-actors.txt`, `long-legs-install.json`.

Generated evidence stays under private `output/`; no disc assets or generated
meshes are committed.

## Status and non-claims

- Mesh + config staging level only. The bind-pose decode carries **no animation
  pose bank and no skeletal playback**; `animation_rows` are sampled key frames.
- Long Legs has **no teki type** in `engine/include/teki.h`, so the neutral
  Chappy (3, Dwarf Bulborb) placement vehicle is used and identity is not
  claimed. Every native gate (`native_identity`, `natural_AI`, `combat`,
  `death_corpse`, `ik_leg_stability`, `foot_crush`, `houdai_gun_callback`,
  `skeletal_playback`) is BLOCKED pending the hook request on #186.
- Shared IK skeleton, mouth/stickable/leg-tube runtime identities, foot
  crush/press and Man-at-Legs gun callbacks remain lane work under #173.
- Damagumo/Beady Long Legs (56) stays owned by the demon lane and is not staged
  here.

## Native registration (family-owned) — deferred

Workflow revision 2026-09-13
([#186](https://github.com/4laric/pikmin-randomizer/issues/186)): the Long Legs
family owner owns its narrow additive registration hooks. This pass does **not**
register a native draw: the lane installs bind-pose meshes, not the converted
`.mod` pose bank the shared `native/pc_port/pc_p2_batch2.cpp` unit consumes, so
there is nothing loadable for the current visual path yet. The bind-pose meshes
first need the #186 conversion path, after which a `TEKI_Chappy`-vehicle draw
hook (or a native Long Legs type) can be added. See
[Batch-2 native registration](PIKMIN2_BATCH2_NATIVE_REGISTRATION.md).
