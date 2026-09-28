# P2 pose fidelity: density, interpolation, crossfade (#895)

This note covers the `pose` track of #895. Imported P2 actors looked choppy for
three reasons:

- Clips were baked with only 3 or 4 whole-mesh poses.
- Dedicated family draw paths snapped to one pose, with no interpolation.
- Every change of clip was a hard cut.

The track changes the bake, the batch loaders and the dedicated family draws.
The P1 host clock still owns gameplay, events and timing throughout.

## Tunables, all in one place

### Bake side: `experimental/pikmin2_animation.py`

| Constant | Value | Meaning |
|---|---|---|
| `POSE_LIMIT_MAX` | 64 | Native bank row cap (`pc_p2_batch2` parseBank, `p2sampled::Clip::valid`). |
| `DEFAULT_POSE_LIMIT` | 16 | Campaign default for families on the compact loader and for proxy/Chappy rows. |
| `LEGACY_POSE_LIMIT` | 3 | Families whose dedicated loader still holds every pose as a full Shape: Blue Kochappy, Miulin, Frog (at least 6), Tank, Kabuto. |

`scripts/p2_prepare_content.py` exposes `--pose-limit` (default 16, range
2..64) and `--legacy-pose-limit` (default 3). `scripts/p2_play.py` also uses
`--pose-limit`. Proxy declarations (`randomizer/p2_proxy/*.json`) and
`CHAPPY_ROWS` declare 16.

### Runtime side: `pc_port/pc_p2_pose_motion.h`

These are read once per process from environment variables:

| Variable | Default | Effect |
|---|---|---|
| `PIKMIN_P2_INTERPOLATION=0` | on | Draw the nearest baked pose with no lerp. Use this for A/B comparison. |
| `PIKMIN_P2_CROSSFADE_MS` | 150 | Length of the clip-change crossfade, eased with smoothstep. `0` turns it off. |
| `PIKMIN_P2_MOVE_ENTER` | 1.5 | Horizontal speed² at which an actor switches to its move clip. |
| `PIKMIN_P2_MOVE_LEAVE` | 0.5 | Speed² at which an actor falls back to its wait clip. |
| `PIKMIN_P2_CLIP_DWELL_MS` | 250 | Minimum time an actor stays in move or wait before switching again. |
| `PIKMIN_P2_FALLBACK_SHAPES` | 4 | Number of full Shapes kept per clip for the fallback path. |

## Bake

- `sample_frames` accepts up to 64 poses. The batch-family extractors (aquatic, cannon, dweevil, flora, flying, ground inverts, snagret, waterwraith, uji, minihoudai and proxy) take their caps from `POSE_LIMIT_MAX`.
- Proxy on-disk guards are now 4 MiB per clip and 64 MiB per species. The native budget counts resident bytes instead (see below).
- `p2_proxy_sweep` never falls below 12 poses on a byte-guard retry.
- Bank writers append the optional `frames f0,f1,...` trailer (`P2_BANK_FRAMES_1`) from each manifest pose's real source frame. `frames_trailer` only emits it when the list satisfies the native validator: first frame 0, last frame `duration-1`, strictly increasing, at most 64 entries. This fixes two problems:
  - Python's `round()` and native `floor(v+.5)` could disagree.
  - When a pose failed to convert, every later pose was misaligned.

  Writers updated: `batch2_core`, `aquatic_install`, `proxy_content`, `chappy_content`, `sokkuri_content`, `uji_content`, `elecbug_content`, `tamago_content`, `snagret_content`, `snakejoint_behavior`, `dangomushi_behavior` and `flying_install`. The merge parsers carry the trailer through (`ground_species_content`, `dangomushi_content`).
- **Loops:** dense uniform sampling keeps both frame 0 and frame `duration-1`. A P1 loop wrap (last frame back to frame 0) is therefore continuous without a special wrap bracket. Loop-aware sampling that drops the duplicate end frame would need a native row flag, so it was not adopted.

## Native loaders (`pc_p2_pose_loader.h`, batch2/batch3)

Each clip keeps at most `fallbackShapes` evenly spread poses as Shapes. Pose 0
is always one of them; it owns the materials and textures and is the base for
private geometry. Every pose is decoded to positions and normals with
`p2pose::decodeBaked`. Topology is compared across all clips, then dropped for
every pose after the first.

Budgets count resident bytes:

- **Shape slot:** costs its file size.
- **Decoded pose:** costs 12 bytes per vector.

The limits are:

- `PoseFileBytes`: 1 MiB per file.
- `ClipBytes`: 1 MiB per clip.
- `TotalBytes`: 48 MiB per setup.

`P2_BATCH2_BANK total_mod_bytes` / `P2_BATCH3_BANK` now report resident bytes.

Draws always go through the actor's private Shape via `p2pose::present`:

- Bracket the two poses around the current frame and lerp positions (normals are renormalised), or pick the nearest pose when interpolation is off.
- On a clip change, crossfade from the last displayed geometry.
- Corpses hold the final pose.

The Shape slots are the fallback, with every pose index aliased to its nearest
slot. Crossfade time and move/wait hysteresis advance in
`pc_p2_batch{2,3}_update` (from `BTeki::update`), not in draw.

Markers:

- `P2_BATCH{2,3}_INTERPOLATION_READY ... lerp= crossfade_ms=`
- `P2_BATCH{2,3}_BLEND ... poses=`
- `P2_BATCH{2,3}_CROSSFADE` (at most 64 per session)

## Dedicated families (`pc_p2_pose_family.h`)

Frog, Tank, Kabuto and Sheargrub decode the same pose files they already load.
They draw the lerped pose with a crossfade through a private Shape.

Chappy (all 7 species) goes further:

- It moves to the compact loader, so it is densified to 16 poses per clip.
- It accepts the `frames` trailer.
- It falls back to legacy per-pose Shapes, clip by clip, if the compact loader rejects a clip (`P2_CHAPPY_POSE_FALLBACK`).

Any decode, topology or private-Shape failure disables the helper, and the
module keeps its nearest-pose draw (`P2_<FAMILY>_INTERPOLATION_DISABLED`).

Markers: `P2_<FAMILY>_INTERPOLATION_READY`, `P2_<FAMILY>_BLEND` and
`P2_<FAMILY>_CROSSFADE`. The fade ticks through `pc_p2_pose_family_tick`.

The non-interpolated fallback `p2animation::Clip::index` (v1, uniform) now
rounds to the nearest pose instead of truncating.

## Not changed (follow-ups)

- **Timing:** pose phase still follows the P1 host animator (`counter/(frames-1)`). A separate P2-native clock would let the pose drift from P1 event and damage timing, so it was deferred.
- **Families without the interpolated draw:**
  - Frog, Tank and Kabuto stay at legacy density until their loaders adopt `pc_p2_pose_loader.h`, although they now interpolate.
  - Mamuta, Blue Kochappy/Kochappy and bulblax still use their own opt-in interpolation flag files.
  - Sarai, king/queen, kurage, bigtreasure, fuefuki, qurione, kogane and shijimi were not ported.
  - Groink still draws a static frame, and Long Legs draws its bind pose.
- **Skeletal playback** (`p2attach` + `p2skin`, per-joint slerp) is still Snow-only. Linear vertex lerp can still shorten a limb that rotates fast between two samples. Dense sampling (about 4–13 source frames between poses) keeps that error small.
