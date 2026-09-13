# Long Legs family — bind-pose native draw path (#312, parent #173)

Batch 4 ([docs/PIKMIN2_FAMILY_BATCHES.md](PIKMIN2_FAMILY_BATCHES.md)) resolves
the native-registration blocker recorded in
[PIKMIN2_LONG_LEGS_INSTALL.md](PIKMIN2_LONG_LEGS_INSTALL.md): the lane installs
bind-pose meshes, not a converted `.mod` pose bank, so it had nothing for the
shared `pc_p2_batch2.cpp` visual path to load. This slice adds a family-owned
conversion and a matching family-owned native draw path.

## Converter gap and resolution

The strict shared converter (`experimental/pikmin2_convert.py`) rejects both
owned models as delivered:

| Species | Enemy id | `enemy.bmd` | Strict-path failure |
|---|---|---|---|
| Houdai (Man-at-Legs) | 66 | 80224 B, 22 joints, 0 envelopes | `Only single-stage materials supported` |
| BigFoot (Raging Long Legs) | 69 | 82336 B, 15 joints, 4 envelopes | `Skinned envelopes not supported` |

Both are resolved with **family opt-in tolerances only** (strict defaults stay
unchanged elsewhere, per #186):

- `approximate_materials=True` for Houdai's multi-stage `MAT3` materials.
- an explicit bind `draw_matrices` table from
  `experimental.pikmin2_skinning.draw_matrices` for BigFoot's `EVP1` matrix
  envelopes (the authored inverse-bind blend evaluated at the bind pose).

`experimental/pikmin2_long_legs_visual.py` owns this conversion. It reads the
staged `Houdai_enemy.bmd` / `BigFoot_enemy.bmd` from a private run room, writes
one static engine shape per species (`longlegs_<species>_bind_00.mod`), and
records source/output SHA-256 in `long-legs-visual.json`. It refuses to
overwrite and preserves the baseline when the mesh bank is absent.

## Real-disc evidence (US GPVE01 rev 0)

Private `output/p2-batch4-ll/{run1,run2}/...` — two fresh extractions and
conversions are byte-identical across all five files:

| Species | Source (`enemy.bmd`) SHA-256 | Output `.mod` | Bytes | Vertices / tris / shapes / textures |
|---|---|---|---|---|
| Houdai | `018f7acabd870d8a8023c83678ff910e0e3d04da2afb5fa625887968bd00f01a` | `longlegs_Houdai_bind_00.mod` | 120288 | 1161 / 1871 / 4 / 6 |
| BigFoot | `71a4c73c6e94c65014ac2bca30dd8d75e22bd843bc7b0d9c086ce59b98638f38` | `longlegs_BigFoot_bind_00.mod` | 98528 | 1098 / 2020 / 3 / 6 |

Recorded approximations: materials use the converter's
`vertex color times identifiable UV0 diffuse` policy (original TEV not
reproduced); BigFoot drops one texture-matrix attribute (`[3]`), reported in
the receipt. No generated models are committed.

## Native registration (family-owned)

New TUs `native/pc_port/pc_p2_long_legs.cpp` / `.h`, following the
`pc_p2_batch2.*` registration precedent:

- **Build**: added to the `pikmin_pc` source list in `native/CMakeLists.txt`.
- **Setup**: `pc_p2_long_legs_setup()` called from `pc_p2_preview_setup()` after
  `pc_p2_batch2_setup()`. Gated on `pc_pikipelago_room_preview()` and `tekiMgr`;
  an absent `p2-long-legs-actors.txt` is a no-op P1 fallback.
- **Config**: reads `p2-long-legs-actors.txt` (`P2_LONG_LEGS_ACTORS_1`,
  `<generator> <Species>`), matches the arena's P1 placement vehicles by
  generator ID, verifies `TEKI_Chappy`, rejects duplicate generators / missing
  actors, and loads `assets/dataDir/courses/pikmin2room/longlegs_<species>_bind_00.mod`.
  There is **no pose bank and no animation selection**; each species draws its
  single bind shape.
- **Draw**: `pc_p2_long_legs_draw` appended to both the corpse and live fallback
  chains in `src/plugPikiNakata/tekibteki.cpp`; it returns false for any actor it
  does not own, so ordinary controls and other families keep the existing
  fallback.
- **Reset/teardown**: `pc_p2_long_legs_reset()` added to every family reset /
  teardown / stage point in `src/plugPikiNakata/tekimgr.cpp`, and
  `pc_p2_long_legs_forget(teki)` on actor reuse.

Runtime identity is reported as `P2_LONG_LEGS_BIND` (per actor) and pose
selection as `P2_LONG_LEGS_DRAW`; native identity is confirmed from the log
line, not a screenshot.

## Non-claims

Visual-only P1 proxy anchor. No source P2 FSM, IK leg stability, foot
crush/press, Man-at-Legs gun callback, damage receivers, rewards or collisions
are ported; the blend shows the bind pose, not source behavior. Every runtime
gate (`native_identity`, `natural_AI`, `combat`, `death_corpse`,
`ik_leg_stability`, `foot_crush`, `houdai_gun_callback`, `skeletal_playback`)
remains BLOCKED/UNTESTED until a supplied-asset runtime pass. Damagumo/Beady
Long Legs (56) stays with the demon lane.

## Validation performed

- `experimental/pikmin2_long_legs_visual` + lane install + batch-2 suites:
  `py -3.12 -m pytest tests/test_pikmin2_long_legs_visual.py
  tests/test_pikmin2_long_legs_install.py tests/test_pikmin2_batch2.py` →
  109 passed.
- `pc_p2_long_legs.cpp`, `pc_p2_preview.cpp`, `tekibteki.cpp`, `tekimgr.cpp`
  compiled `-fsyntax-only` exit 0 with the exact `pikmin_pc` translation-unit
  flags (Ninja Release, `PIKMIN_NATIVE_JAUDIO=ON`).
- Private full `pikmin_pc` build in the isolated batch-4 worktree (recorded in
  the session issue update).
