# Original Watage81 human check

Use the private 20 Red Pikmin tutorial overlay and a qualified fixture executable.
Set `P2_ORIGINAL_FOLIAGE_BATCH=watage` and `P2_ORIGINAL_FOLIAGE_HUMAN=1`,
then launch `fixtures/pikmin_ci_fixture_original_foliage --experimental-pikmin2-surface tutorial`
from its private run directory. Keep the centered 960x540 window.

1. Walk the captain east from camp into the white Watage. Observe the plant sway
   and the small cream feather burst above it. Walk clear; do not inject callbacks.
2. While it sways, walk through again. Its current motion must continue without
   another burst. Once settled, touch again: a new burst should appear.
3. Turn the camera away and back while feathers remain. Observe culling, source
   crossed planes and alpha fade; a camera turn must not restart their lifetime.
4. Walk through the nearby yellow Tanpopo. Its five static spheres and plant sway
   must remain distinct; it must not emit Watage feathers.
5. Wait seven seconds. Feathers must disappear with no residual texture or scene
   corruption. Record the executable hash, source pin, observations and failures.

The automated `--batch watage --mode walk` supervisor uses normal SDL movement
through initialized, relocated literal surface plants, then generator-cache
reentry. `diagnostic` separately checks finite particles survive plant retirement
and drain through the ordinary manager clock. `effect-refusal` checks genuine
missing JPA/TEX1 refusal before any actor allocation. These are fixture evidence;
full campaign, original placement and disk save/resume remain unqualified.

Audited scope: genuine GPVE01 PID0x1e4 and IP2_watage2_ia bytes, source emitter
volume, finite lifetime, AIR/RANDOM/DRAG fields, rotated crossed planes, primary
and environment colors, alpha and sphere culling. The bounded renderer is not a
general JPA engine. Retail weather/global-color modulation, exact callback-bit
clipping semantics, split-view group policy and fully culled plant animator
lifecycle still require qualification. Models use sampled flattened poses and
approximate materials. No source77 appearance particle is substituted.
