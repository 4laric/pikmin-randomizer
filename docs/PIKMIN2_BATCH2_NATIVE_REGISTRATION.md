# Batch-2 native registration (family-owned)

Workflow revision 2026-09-13 ([#186](https://github.com/4laric/pikmin-randomizer/issues/186)):
family owners implement their own narrow additive registration hooks. This
document covers the five batch-2 pose-bank families and the shared additive unit
that registers them:

| Family | Issue | Parent | Pose prefix |
|---|---|---|---|
| Dweevil family | #349 | #170 | `ota_` |
| Flora / Candypop | #353 | #171 | `flora_` |
| Ground invertebrates | #346 | #165 | `ginv_` |
| Cannon Beetle / projectile | #350 | #169 | `cannon_` |
| Waterwraith / Tyre | #352 | #175 | `ww_` |

Long Legs (#312, parent #173) installs bind-pose meshes (`<Species>_enemy.bmd`),
**not** a converted `.mod` pose bank, so it has no native draw path in this
pass; its bind-pose meshes still need the #186 conversion path before a native
display can be claimed.

## Implementation

One shared, additive translation unit registers all five pose-bank families,
which keeps the shared-file footprint to a single include/setup/draw/reset/
forget hook per file instead of fifteen.

- **Build**: `pc_port/pc_p2_batch2.cpp` (+`pc_p2_batch2.h`) added to the
  `pikmin_pc` source list in `native/CMakeLists.txt`, following the
  `pc_p2_qurione.cpp` family registration; no new third-party dependencies.
- **Setup**: `pc_p2_batch2_setup()` called once from `pc_p2_preview_setup()` in
  `pc_port/pc_p2_preview.cpp`, after `pc_p2_qurione_setup()`. Gated on
  `pc_pikipelago_room_preview()` and `tekiMgr`; an absent family config is a
  no-op P1 fallback, so ordinary P1 play is unaffected.
- **Config**: reads the install-written `p2-<family>-actors.txt`
  (`P2_<FAMILY>_ACTORS_1`, `<generator> <Species>`) and `p2-<family>-bank.txt`
  (`species`/`clip` rows with pose counts), then loads
  `assets/dataDir/courses/pikmin2room/<prefix>_<species>_<clip>_NN.mod`.
  Duplicate generators, missing arena actors, native-type mismatches, mixed
  render resources and byte-budget overruns abort before any draw.
- **Draw**: `pc_p2_batch2_draw` added to both the corpse and live fallback
  chains in `src/plugPikiNakata/tekibteki.cpp`. It returns false for any actor
  it does not own, so unconfigured actors keep the existing fallback, including
  ordinary controls.
- **Reset/teardown**: `pc_p2_batch2_reset()` added to every family reset /
  teardown / stage-constructor point in `src/plugPikiNakata/tekimgr.cpp`, and
  `pc_p2_batch2_forget(teki)` on actor reuse, so no recycled pointer is assumed
  live.

## Native type expectations

Verified per species before a single pose is loaded:

| Family | Species | Native teki type |
|---|---|---|
| Dweevil / Flora / Ground / Waterwraith | all | `TEKI_Chappy` (3, Dwarf Bulborb vehicle) |
| Cannon | Kabuto, Rkabuto, Fkabuto | `TEKI_Beatle` (17, P1 Armored Cannon Beetle) |
| Cannon | Rock, Stone | `TEKI_Iwagon` (2, P1 Rolling Boulder) |
| Cannon | Bomb, Egg | `TEKI_Chappy` (3) |

## Visual-only, P1-proxy non-claims

This registration is a **visual anchor only**. It does not port source P2 FSM,
damage/elemental receivers, capture/ownership, projectile, boss-phase or reward
semantics; those remain on the family issues and #186. The blend selects a
sampled pose bank by the P1 animator's motion and phase, so it proves pose
selection, not source behavior. All runtime gates
(`native_identity`, `natural_AI`, `combat`, `death_corpse`, `carrier_recovery`
and the per-family extras) remain BLOCKED or UNTESTED until a runtime pass with
supplied assets; native identity is confirmed from the `P2_BATCH2_BIND` log line
rather than a screenshot.

## Validation performed

- `pc_p2_batch2.cpp` compiled `-fsyntax-only` against the real engine headers
  (exit 0), using the exact `pikmin_pc` translation-unit flags.
- The three edited shared translation units (`pc_p2_preview.cpp`,
  `tekibteki.cpp`, `tekimgr.cpp`) also compile `-fsyntax-only` (exit 0) with the
  additive hooks in place.
- No maintained build/export was run: the shared checkout/build/export stays
  serialized by #186, and another worker had uncommitted native edits at the
  time. The maintained `pikmin_pc` rebuild and `scripts/export_native_source.py`
  handoff remain the integration step.
