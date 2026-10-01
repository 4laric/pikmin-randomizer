# P2 pose fidelity: density, interpolation, crossfade (#895)

This note covers the `pose` track of #895. Imported P2 actors looked choppy for
three reasons:

- Clips were baked with only 3 or 4 whole-mesh poses, and some frames of
  death, hide and burrow clips could not be converted at all.
- Dedicated family draw paths snapped to one pose, with no interpolation.
- Every change of clip was a hard cut.

The track changes the bake, every native pose-bank loader and every
pose-bank draw path in the campaign pool. The P1 host clock still owns
gameplay, events and timing throughout.

The colour and brightness half of #895 is a separate track on
`claude/p2-colour-grade`; nothing on this branch changes lighting or colour.

## Tunables, all in one place

### Bake side: `experimental/pikmin2_animation.py`

| Constant | Value | Meaning |
|---|---|---|
| `POSE_LIMIT_MAX` | 64 | Native bank row cap (every native loader accepts up to 64 poses per clip). |
| `DEFAULT_POSE_LIMIT` | 24 | Campaign density for every family (Chappy rows included; proxy rows still declare 16). Raised from 16 in #943 after the 2026-09-29 smoke test: 24 is the ceiling shared by the own-behaviour loaders (Groink, Breadbug, BombSarai, Fuefuki, BigTreasure visual). |
| `LEGACY_POSE_LIMIT` | = `DEFAULT_POSE_LIMIT` | Kept as an alias. There is no sparser legacy tier: Blue Kochappy, Miulin, Frog, Tank and Kabuto are on the compact loader. |
| `FALLBACK_SHAPES` | 4 | Full Shapes native keeps per clip (mirror of `p2motion::Tunables::fallbackShapes`). |
| `RESIDENT_CLIP_BYTES` | 1 MiB | Per-clip budget, resident (owner-approved raise from 512 KiB; see below). |
| `RESIDENT_TOTAL_BYTES` | 48 MiB | Approved per-setup budget, resident. |

`scripts/p2_prepare_content.py` exposes `--pose-limit` (default 24, range
2..64). `--legacy-pose-limit` is now only an optional override for those five
families (default: the `--pose-limit` value). The Groink per-clip table
(`pikmin2_groink_stage.POSE_LIMITS`) is 24 for every clip, Kogane, BombSarai,
Fuefuki and BigTreasure follow `--pose-limit` clamped to their native 24-pose
bound, Breadbug thins its uniform samples so samples plus key-event frames
stay within 24, and Sarai adds the
dense uniform samples to its event and capture-window frames.

### Runtime side: `pc_port/pc_p2_pose_motion.h`

These are read once per process from environment variables:

| Variable | Default | Effect |
|---|---|---|
| `PIKMIN_P2_INTERPOLATION=0` | on | Draw the nearest baked pose with no lerp. Use this for A/B comparison. |
| `PIKMIN_P2_CROSSFADE_MS` | 150 | Length of the clip-change and loop-seam crossfade, eased with smoothstep. `0` turns it off. |
| `PIKMIN_P2_MOVE_ENTER` | 1.0 | Horizontal speed² above which an actor switches to its move clip. This is the legacy `speed2 > 1` threshold. |
| `PIKMIN_P2_MOVE_LEAVE` | 0.5 | Speed² below which a moving actor falls back to its wait clip. The 0.5..1.0 band is the only behaviour change: a slow actor that is already moving keeps its move clip instead of flickering between clips. |
| `PIKMIN_P2_CLIP_DWELL_MS` | 250 | Minimum time an actor stays in move or wait before switching again. |
| `PIKMIN_P2_FALLBACK_SHAPES` | 4 | Number of full Shapes kept per clip whose vectors decode. |
| `PIKMIN_FRAME_DUMP_EVERY` / `_FROM` / `_TO` | 15 / all | Frame-dump interval and window (motion evidence). |

## Bake

- `sample_frames` accepts up to 64 poses. Every extractor in the pool takes its cap from `POSE_LIMIT_MAX`. That includes aquatic, cannon/Kabuto, dweevil, flora, flying, ground inverts, snagret, waterwraith, uji, minihoudai, proxy, sokkuri, dangomushi, elecbug, tamago, frog, tank, mamuta, sarai and dwarf orange.
- **Collapsed frames.** Several retail clips scale joints, or the whole body, to zero: Sokkuri hide1, dead1 and pdead1, UmiMushi dead1 and type5, and SnakeCrow and SnakeWhole dead. Their draw matrix is singular, so those frames used to be dropped as "unsupported". That left e.g. Sokkuri pdead1 with 4 poses over 90 frames, and in the old staged bank with 1.

  `pikmin2_animation.decode_pose` now retries such a frame once:

  - `bca_pose(..., singular_scale='clamp')` replaces a near-zero axis scale with 1e-4.
  - The `transpose-adjugate` normal policy is used for the retry.

  The collapsed geometry stays a sub-visible point, and its normals keep the rotation's direction. Frames that decode normally are byte-identical to before. A retried frame records `normal_policy.collapsed_joint` in its pose report.
- **Frames trailer.** Bank writers append the `frames f0,f1,...` trailer (`P2_BANK_FRAMES_1`) from each pose's real source frame. `frames_trailer` emits it only when the list satisfies the native validator: first frame 0, last frame `duration-1`, strictly increasing, at most 64 entries. With the collapsed frames converted, every row has its end frames. The DangoMushi snagret rows now carry the trailer as well.
- **Budgets.** Budgets are measured the way native pays for them, as resident bytes (`resident_clip_bytes`):
  - Each clip keeps `FALLBACK_SHAPES` spread poses as full Shapes, which cost their file size.
  - Every other pose costs 12 bytes per position or normal.
  - The limits are:
    - 1 MiB per clip (the repo owner approved raising it from 512 KiB).
    - 48 MiB per native setup.
    - 8 MiB per proxy species (`pikmin2_proxy_assets`).
    - 1 MiB per clip and 10 MiB per bank for the Frog, Tank and Kabuto installers, which previously used on-disk limits.
  - On-disk bytes are still reported but no longer gate the bake. Each pose file is a full MOD, so a 16-pose clip is larger on disk (up to 1.1 MiB, for DangoMushi) than resident (at most 490 KiB). A vector-only on-disk pose format would shrink the disk footprint, but no budget needs it; it is listed as a follow-up.
- **No sparse fallback.** `p2_proxy_sweep` has no retry at fewer poses. A species over budget is recorded as a failure (`budget_failure`) at its row limit.

## Loops (retail data, not an assumption)

`scripts/p2_loop_seam_audit.py` compares every retail clip's frame 0 with frame
`duration-1`, and both with an ordinary one-frame step. Across 260 clips of
the pool:

- Only 6 clips end on a copy of frame 0.
- The cyclic clips (wait, move, walk, run, fly, swim) are almost all authored so that `duration-1 -> 0` is one more ordinary step. That is 70 of 77, with a seam no larger than 3x a per-frame step. A P1 wrap that shows the last pose and then pose 0 is therefore continuous for them.
- The rest jump at the seam. These are one-shot acts such as Chappy/FireChappy/LeafChappy `waitact2`, the Jigumo `wait1` pose change and the DangoMushi `fly` root motion. So do most death, appear and attack clips, which are not meant to loop.

Native mirrors this:

- `p2motion::seamContinuous` classifies each baked clip at load: the last→first distance must be at most 3x the largest per-source-frame step between adjacent poses.
- A P1 wrap (the same clip's frame jumps back by more than half the clip) of a discontinuous seam begins a crossfade from the displayed pose. A continuous seam is left alone.
- This is covered by `p2_pose_motion_test`.

## Native loaders (`pc_port/pc_p2_pose_loader.h`)

`loadStem` is shared by every pose-bank loader:

- batch2 (dweevil, flora, ground, uji, cannon, waterwraith, proxy)
- batch3 (aquatic, flying, snagret)
- Chappy (7 species)
- Frog, Tank, Kabuto, Sheargrub
- Dwarf Orange (Blue Kochappy)
- Mamuta (Miulin)
- Groink (78 and 97)

Sarai decodes its own sampled meshes (below).

- **Transactional.** Every pose file is read, resource-checked and decoded before the first Shape is created. A rejected clip creates no Shapes and never becomes the material owner. A later failure restores the shared owner, reference and topology.
- Each clip keeps `fallbackShapes` evenly spread poses as Shapes. Pose 0 is always one of them, because it owns the materials and textures and is the private-geometry base. Every pose is decoded to positions and normals.
- **Loud fallback.** A clip whose vectors do not decode loads every pose as a Shape if the budget allows, otherwise as many evenly spread Shapes as fit. It prints `P2_POSE_LOADER_FALLBACK`. It no longer quietly drops to 4 poses.
- Budgets: `PoseFileBytes` 1 MiB per file (the `decodeBaked` cap), `ClipBytes` 1 MiB (owner-approved) and `TotalBytes` 48 MiB, all resident.

## Draw (`pc_p2_pose_shape.h`, `pc_p2_pose_family.h`)

`p2motion::Presenter` is engine-free and unit-tested. It:

- brackets the two poses around the current source frame and lerps positions (renormalising normals), or picks the nearest pose when interpolation is off;
- crossfades from the last displayed geometry on a clip change or across a discontinuous loop seam;
- never fades from a stale display. A display older than 0.25 s means the actor was not drawn, and a fade already in flight is dropped.

`p2pose::present` writes the result into the actor's private Shape. Fade time and staleness advance from `BTeki::update` (`pc_p2_batch{2,3}_update`, `pc_p2_pose_family_tick`), or from the Sarai host's own update.

`p2posefamily::Actors::clear()` and `forget()` also clear the private-Shape failure set, so a recycled actor address never inherits "interpolation disabled".

**Death clips** (`dead*`, `pdead*`) play up to their last visible pose and the
corpse holds that pose. The last visible pose is the last one whose extent is
at least 20% of the clip's largest. The reason:

- P2 ends several death animations fully collapsed and hands the carcass to a separate pellet.
- The P1 port keeps the actor's own body as the corpse.
- The old sparse bake kept corpses visible only because it could not convert the collapsed frames.

Hiding clips, such as Sokkuri hide1, still play their collapse.

Markers:

- `P2_<FAMILY>_INTERPOLATION_READY`
- `P2_<FAMILY>_BLEND ... poses= seam=`
- `P2_<FAMILY>_CROSSFADE ... cause=clip_change|loop_seam`
- `P2_POSE_LOADER_FALLBACK`

`<FAMILY>` is one of BATCH2, BATCH3, CHAPPY, FROG, TANK, KABUTO, SHEARGRUB, DWARF_ORANGE, MAMUTA, GROINK or SARAI.

**Sarai.** The host decodes every sampled mesh of its pose profiles. The natural route lerps between the bracketing samples, with a crossfade on a profile change, into a private Shape. The mouth transforms still come from the sampled frame, so capture timing is unchanged.

## Evidence tools

- `scripts/p2_pose_density_audit.py RUN [--stage CONTENT --assets ASSETS]` stages every identity through the production installer, then reports per clip:
  - poses, frames and the largest sample gap;
  - whether the trailer is present;
  - on-disk and resident bytes.

  It flags density (fewer than 12 poses and a gap over 5 source frames), trailer and budget violations.
- `scripts/p2_loop_seam_audit.py`: the retail loop-seam table above.
- `scripts/p2_pose_motion_evidence.py` replays native bracket and lerp offline from two staged runs, one source frame per 30 fps display frame. For each clip it writes:
  - a before/after GIF: baseline nearest, baseline lerp and dense lerp;
  - a per-frame motion plot (pops are spikes);
  - the projected path of the most-moving vertex.

## Not changed (follow-ups)

- **Timing:** pose phase still follows the P1 host animator (`counter/(frames-1)`). A separate P2-native clock would let the pose drift from P1 event and damage timing.
- **UmiMushi `sturn1`** (fixed in #995): the retail BCA carries 26 tracks for the 25-joint model; the 26th is a trailing track with no joint, and the first 25 line up with the skeleton (run1/sturn1 frame 0 agree on every static joint). J3D applies track i to joint i and ignores the extra one, so `bca_pose(..., extra_tracks=True)` (opt-in, used only by the aquatic extractor) decodes the first 25 tracks. The clip now bakes 24 poses. Re-extract UmiMushi (71) and UmiMushiBlind (101) to pick it up.
- **Long Legs** (BigFoot, Damagumo): the native draw is a single bind-pose mesh (`longlegs_<species>_bind_00.mod`); only the body translates, and the legs stay in bind pose. It has no sampled pose bank, so there is nothing to densify. Animating it needs a skeletal leg path, which is separate work.
- **Families outside the campaign pool:** bulblax King/Queen, kurage, BigTreasure, fuefuki, qurione, kogane, shijimi, Snow and Kochappy keep their own loaders.
- **On-disk size:** a vector-only pose file format would shrink dense clips on disk. No budget needs it.
- **Skeletal playback** (`p2attach` + `p2skin`, per-joint slerp) is still Snow-only. Linear vertex lerp can still shorten a limb that rotates fast between two samples. Dense sampling (about 2 to 6 source frames between poses) keeps that error small.
- **Root `engine/` snapshot:** it carries only the engine-free pose headers (`pc_p2_pose_motion.h`, `pc_p2_batch2_clock.h`, `pc_p2_animation.h`) and `tools/p2_pose_motion_test.cpp`, which the root test compiles. The engine-dependent loader and family headers and the changed .cpp files arrive with the integration lead's full export from the native branch, so the snapshot never carries headers that its own .cpp files do not use.
