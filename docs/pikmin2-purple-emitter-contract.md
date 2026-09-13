# Purple earthquake emitter contract

Source-only issue #113/#120 batch. No native edits. Reproduce using `python -m experimental.pikmin2_purple_emitter_reference --iso <local ISO> --research native/pikmin2-research --output <reference.json>`. Four tests cover parameter ambiguity, XZ boundaries, eligibility and callback ordering.

## Retail values and geometry

Actual user/Abe/piki/pikiParms.txt SHA256f22ae88fade54bf8f142ecc5aae4ce0c82078e6aed448d029f16b75e5a3d7996 contains P017=60 and P022=20. Header defaults are60 and100; using the default direct damage would be incorrect for this retail revision.

PikiHipDropState::earthquake creates a60-radius sphere at Pikmin position, sets mUseCustomRadius=1 and visits CellIterator candidates. CellIterator::satisfy uses target getPosition and target bounding-sphere radius. Its misleadingly named isWithinSphere returns true for OUTSIDE using XZ squared distance; satisfy rejects that. Therefore accept dx²+dz² <= (60+targetRadius)², inclusive boundary and no Y cutoff. Pass IDs avoid duplicate target visits. CustomRadius and default branches currently share the same geometric result in this source. Cell-grid membership remains an additional broadphase boundary, so a plain global enemy scan is a compatible engineered substitute only if labeled. EnemyBase::setParameters obtains target radius from collision-tree root sphere; do not substitute shadow radius100. P1 getCentreSize/radius mapping still requires an explicit native adapter audit.

## Events, eligibility, damage order

Ground/plat landing calls dosin unless substate2, starts a0.3second landing wait and emits earthquake. A descending collision against an enemy first dispatches Hipdrop (press callback then generic hipdrop fallback), then earthquake. It re-reads vertical velocity and dispatches direct Press if still descending, then leaves HipDrop when still active. Target Pikmin return before impact. This is not a generic damage sphere: earthquake itself adds no damage. Direct Hipdrop carries retail20, but Kochappy press handles live nonbitter Pikmin first, so neither20 nor generic50 may be blindly added as guaranteed dwarf damage.

InteractEarthquake first calls checkBirthTypeDropEarthquake: EBS_DropEarthquake actors transition to Appear, bypassing normal earthquake (a side effect, not simply ignored targets). Normal enemy callback requires floor triangle, alive/nondead/nonflying, no hard constraint, not bitter, not no-interrupt, not bitter-immune. Its return remainsfalse even after scheduling the state, so the native adapter cannot infer acceptance from that boolean alone. The previously audited bounce/Fit policy then applies30percent chance and10seconds for Red/5forSnow.

## Proposed native interface for review

NEW pc_p2_purple_earthquake.cpp/.h: receive a landing event containing source Piki identity, landing token and native XYZ; verify enabled source Purple, alive thrown state, and one dispatch for that event. Enumerate only registered supported family actors using explicit radius/eligibility adapters. Deliver a non-damaging earthquake event to the peractor receiver. Ground bounce and descending enemy collision are distinct audited hooks in PikiFlyingState; preserve all existing P1 callback order and ordinary colors. A simple P1 thrown-Purple emitter is an explicitly partial approximation to P2 HipDrop, whose homing/fall substates are still absent.

No native hooks are written in this batch. Requested future files: new emitter module/header, pc_p2_purple.cpp/.h for source-enabled identity/arming, pikiState.cpp for the two callback sites, family registry modules for peractor identity/radius and lifecycle cleanup. A damage-preserving TaiChappy stun receiver is a separate approval gate; never pause all BTeki AI to simulate Fit. Stun must remain interruptible by death, and P1 health/control/corpse paths must pass regressions. Do not enable emitter until a supported receiver exists, and do not infer unsupported P2 flags from unrelated native flags.

Next smallest useful native slice: an opt-in, instrumented registered-Red earthquake event receiver with exact60+radius XZ predicate and legal-eligibility reporting, private runtime fixture for boundary/duplicate/nonPurple/actorreuse checks. Then connect its bounce/Fit action after lethal-damage-during-stun is proven. This separates event correctness from claiming a completed Purple combat port. Current Purple setup also requires a Pod; arena fixture contract must be reviewed before adding it to the noPod Red arena.
