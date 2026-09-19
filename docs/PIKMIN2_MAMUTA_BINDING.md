# Mamuta native-binding validation (batch 3, #221)

Implementation owner: Codex using shared account 4laric. Validates the
native-track binding unblocked at native `7faa644` / root `f9f0839`
(handoff docs: `output/p2-root-integration/docs/PIKMIN2_MAMUTA_RUNTIME.md`,
`PIKMIN2_KIMI_NATIVE_HANDOFF.md`). Continues
[PIKMIN2_MAMUTA_ARENA.md](PIKMIN2_MAMUTA_ARENA.md). No P2 planting,
population-cap or follower-lifecycle claims — those remain native
dependencies.

## Fixed launcher run

Launcher: `output/p2-lifecycle-batch/mamuta-kimi-01/Play.cmd` (copied
production `nectar.exe`, SHA-256
`978f77755b7574f7c7570daf4041243ede18100014bdc5ec29639e4406a82477`, verified
against `handoff.json` before launch). Session
`412c4bbc80af491b847a8af1d7d067fc`, run for 150 s then terminated
interactively; log `kimi-batch3.log` (60,350 bytes).

Evidence validated by `experimental/pikmin2_mamuta_binding.py`:

- **Exact identity/birth**: exactly one
  `P2_MAMUTA_READY generator=221001 native_type=24 xyz=-150.000000,30.000000,1850.000000 P1_proxy_static_anchors_no_P2_planting`
  marker; generator/type/XYZ match the batch-2 arena contract.
- **Native Miurin resources loaded**: `tekipara/miurin.bin`,
  `tekis/miurin/miurin.mod`, `tekis/miurin/miurin.anm`,
  `tekikeys/miurin.key`; memStat `miurin : 36.46 kbytes`.
- **Zero GX desync**: no DESYNC lines in 150 s; steady 30 FPS, no errors or
  asserts in the log tail.
- **Installed bytes unchanged**: all three session poses
  (`miulin_wait.mod`, `miulin_dead.mod`, `miulin_attack1.mod`) hash-match the
  batch-1 extraction — the binding consumed my install unmodified, as the
  handoff states.
- **Imported wait rendering / control / reset**: accepted from native
  evidence `output/p2-lifecycle-batch/mamuta-native-run-01/result.json`
  (fixture 300-update run: wait anchor drawn, Chappy control declined the
  binding, forget/reset declined subsequent drawing, zero GX desync) and the
  supplementary naturally-reached wait capture
  `mamuta-native-capture-03/.../mamuta-source-wait.png`.

## Visual/material fidelity audit (capture03, 1707x1067 + close crop)

- **Geometry/pose: PASS.** Recognizable Mamuta silhouette in the imported
  wait anchor — rounded upright body, visible facial features (dark eye),
  layered body segmentation; weighted bake shows no limb explosion or
  T-pose. Converted geometry: 401 vertices / 786 triangles / 2 shapes per
  pose, finite bounds, no discarded attributes.
- **Material fidelity: PARTIAL.** The body renders pale cream and flat;
  only small textured detail (eye region) reads through. This matches the
  converter's recorded policy "vertex color times identifiable UV0 diffuse
  texture (first texture fallback); original TEV not reproduced" — the
  source model carries 2 embedded textures and original TEV stages that the
  bank does not reproduce. Consistent with the native report: visible
  binding yes, material fidelity no.
- **Ground contact: NOT SIGNED OFF.** Feet are occluded by the arena tree
  rim in the capture (native report agrees).

## Gate updates (batch-2 arena.json, run 5c09e99b)

| Gate | Batch-3 status |
|---|---|
| native_identity | PASS (production READY marker + native fixture birth) |
| natural_AI | UNTESTED (proxy AI active, not visually scored) |
| bury_attack | BLOCKED — native dependency (P2 planting semantics) |
| flick_collateral | UNTESTED |
| territory_watchdog | UNTESTED |
| death_corpse | UNTESTED (swing/corpse anchors wired, not runtime-scored) |
| day_floor_reset | UNTESTED |
| save_load | UNTESTED |
| piklopedia_observation | BLOCKED — native dependency |
| imported wait rendering | PASS (fixture draw + natural capture) |
| control/reset | PASS (native fixture) |
| material fidelity | PARTIAL (TEV/texture approximation by converter policy) |

## Still open

- ShijimiChou owner-death cleanup hazard (batch-2 trace) remains an
  integration prerequisite before followers can be enabled; no Shijimi
  references are created by the binding.
- P2 planting semantics, 99 cap, CKILL_DontCountAsDeath, follower lifecycle:
  root-owned native dependencies.
- Material fidelity (original TEV reproduction) is a converter limitation
  shared with other lanes; raising it is integration-scope work.
- Swing/corpse anchor runtime scoring and interactive behavior gates remain
  for a later playtest or fixture pass.

## Tests

`tests/test_pikmin2_mamuta_binding.py` (9 tests): READY marker
acceptance/rejection, identity/XYZ mismatch, GX desync detection, missing
native resource rejection, material-profile acceptance/limits, installed
byte-identity and tamper detection. Validators were also executed against
the real session log, conversion sidecars and installed poses (results
above).
