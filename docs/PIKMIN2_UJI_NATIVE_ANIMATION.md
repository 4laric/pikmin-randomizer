# Native Sheargrub visual opt-in

The family renderer accepts an optional p2-sheargrub-animation.txt. Without it, existing static rendering remains unchanged. The exact format is P2_UJI_ANIMATION_1, UjiA, seven ordered clip rows, UjiB, nine ordered clip rows. Each row contains name, pose count, source duration, and exactly count increasing frame numbers from zero to duration minus one. UjiA order: dead dead_p appear dive move attack1 type5. UjiB adds attack2 eat before type5. Bounds: 1-12 poses, duration1-10000,256KiB per clip,2MiB total MOD bytes. Unexpected or trailing tokens fail closed.

Files are courses/pikmin2room/uji_SPECIES_CLIP_NN.mod. Both species banks are required even if the scene registers only one species. All model bytes/resources are checked before animated model loading; immutable materials/textures are shared per species after equality checks. The original static models remain required for unknown-motion fallback. Native state, events, collision and receipts are unchanged.

Visual selection uses the source-backed motion map in PIKMIN2_SHEARGRUB_ANIMATION.md and native normalized motion progress. Both native Waiting state IDs are1, which freezes visual phase0; corpse rendering selects final dead pose. Source type5 is loaded but unmapped. No visual events cause gameplay actions.

Validation: isolated family translation-unit syntax compilation passes; standalone C++ policy test passes valid bank plus truncated, trailing, excessive-count, invalid-first-frame and wrong-species cases. No shared game build or runtime validation was performed in this batch. A host installer and fresh-build private runtime fixture are required before playable opt-in validation.
