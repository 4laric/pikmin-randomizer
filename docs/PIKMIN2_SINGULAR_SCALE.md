# Singular animation-scale policy (#405, parent #128)

The restricted J3D rigid converter historically rejected any animated joint
axis whose scale was zero (`Singular animation scale`) and any bake whose draw
matrix was singular (`Singular normal transform`). #233 added an opt-in normal
fallback but deliberately kept zero/annihilated *directions* rejecting. This
note records the separate, bounded capability added in #405: accepting an
authored zero (or near-zero) **scale**.

## Reproduction

On GPVE01 US rev 0, `experimental.pikmin2_flora_assets.extract` reported
Pelplant at 0/10 clips and HikariKinoko at 0/1. Every Pelplant clip failed in
`bca_pose` with `ValueError: Singular animation scale`; frames that cleared the
scale guard then failed in the rigid bake with `Singular normal transform`
(evidence: `output/p2-lane-verify/flora-run2/flora.json`).

## Root cause

Pelplant (`enemy/data/Pelplant/enemy.bmd`) has 8 joints and 3 weighted
envelopes. Its BCA clips author a zero scale for hidden / grow-from-nothing
segments:

| Clip | Zero-scale joint | Frames |
|---|---|---|
| `wait1`, `grow1` | joint 5 | all |
| `damage3`, `dead3` | joint 7 | all |
| `grow2` | joint 7 | 20-29 |
| `grow2` | joint 5 (≈1e-5) | all |

Joint 5 participates in envelope 1 (weight 0.65) and joint 7 is a terminal
child, so a zero scale is an authored transform (a collapsed or hidden
segment), not corrupt data. A collapsed draw matrix is rank-deficient, which is
why the normal transform becomes singular.

## Capability

Two opt-in knobs, both defaulting to the strict behavior:

- `experimental.pikmin2_purple.bca_pose(..., singular_scale='allow')` accepts an
  authored zero axis scale. It only has an effect together with
  `allow_scale=True`; without it a zero scale still raises
  `Scaled animation not supported`. Any other mode value is rejected. The
  default `'error'` is unchanged, and `'allow'` leaves the authored zero in the
  local matrix rather than fabricating a clamped value.
- `experimental.pikmin2_convert.decode(..., singular_normal='transpose-adjugate-zero')`
  (#419 integration) retains the cofactor transform, but explicitly emits a zero
  normal when a singular transform annihilates the direction. This is a collapsed
  geometry approximation, not a source lighting-parity claim. The existing
  `transpose-adjugate` policy still rejects annihilated directions.

`singular_scale='allow'` must be paired with a compatible `singular_normal`
policy; a zero-scale pose baked with the strict default normal check still
raises. The flora lane wires the pair for Pelplant only through its existing
per-species tolerance hooks (`POSE_TOLERANCES`, `TOLERANCES`); all other flora
identities stay on strict defaults. Each clip records the applied
`pose_conversion_policy` / `decode_conversion_policy`, and each pose report
records `singular_normal` when it is not the strict default.

## Clips and species unlocked

At `--pose-limit 6`, Pelplant goes from **0/10 to 10/10** converted clips
(60 poses):

`damage3`, `dead3`, `grow1`, `grow2`, `wait1`, `wait2`, `wait3`, `bgrow1`,
`bdamage1`, `bdead1`.

No other species' output changes. The six Candypop colour buds
(BluePom..RandPom), Tanpopo, Clover, Ooinu_s/Ooinu_l and Wakame_s/Wakame_l were
already converted and remain byte-identical.

**Not unlocked:** HikariKinoko (Common Glowcap) still fails with
`Unsupported shape matrix type`. Its `enemy.bmd` mixes shape matrix type 1
(billboard) with type 3 (skin); billboard semantics are a native/renderer
capability, not a static-converter tolerance, so it stays blocked here.

## Evidence

Private, uncommitted, under `output/`:

- `output/p2-converter-evidence/baseline/` — unmodified converter, pose-limit 6.
- `output/p2-converter-evidence/run1/`, `run2/` — fixed converter, two runs.
- `run1` and `run2`: 282 `.mod` files and 110 raw assets byte-identical.
- `baseline` vs `run1`: 222 non-Pelplant `.mod` files, 0 changed; Pelplant
  0/10 -> 10/10.

Focused tests: `tests/test_pikmin2_purple.py` (scale modes),
`tests/test_pikmin2_flora_assets.py` (species-scoped tolerances),
`tests/test_pikmin2_convert_normals.py` (existing normal policy).

## Non-claims

This is conversion correctness for sampled rigid/weighted poses, not playback
or gameplay. It does not add native hooks, actor install, arena placement,
billboard rendering, BTK/material playback, or runtime/visual/gameplay
acceptance. Collapsed segments bake to a point and their normals follow the
cofactor fallback; no claim is made that the sampled result matches every
rendered source frame.

## Maintained-line integration (#419)

The worker base accepted zero normals implicitly. On maintained base `50332f9`,
cherry-picking #405 alone yielded only 3/10 Pelplant clips (14 poses): 46 poses
failed with `Singular transform annihilates normal`. Integration therefore adds
`transpose-adjugate-zero` as a separate opt-in normal policy. Strict defaults,
existing cofactor semantics, determinant-sign handling, skeletal bindings and
seam-aware computed normals remain intact. Only Pelplant selects the new mode.
The maintained deterministic manifest omits extraction timing and is preserved.

Integrated extraction evidence: `output/p2-converter-integration-evidence/`.
`run1` is the failed pre-reconciliation extraction; `run2` and `run3` exercise
the explicit policy. Runtime adoption requires a newly generated and hash-bound
bank; earlier worker runtime evidence does not certify this combined build.
