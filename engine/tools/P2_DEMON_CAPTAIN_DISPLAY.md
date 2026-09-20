# Demon captain-shape pose display (#222/#224)

Successor to6564cc5f. This private fixture draws two additional copies of the
existing P1 Navi shape using the source attachment matrices, one at each mouth.
The ordinary live captain remains a separate actor, pinned for observation.
These are display copies, not captured captains. Their animation is the
ordinary live captain animation, not a translated P2 FALL state.

The fixture now reads full mouth matrices rather than center-only rows.
Use its matching p2_demon_visual_run.py; earlier runner profiles are incompatible.
Both model and matrix are selected from the same attack0/17 manifest pose.
The source local quarter-turn is applied after world translationY100.
No extra hand offset is introduced. The source mouth matrix scale is retained;
P1/P2 captain model scale compatibility remains a visual acceptance question.

Build uses the private snapshot helper against stable native756515d5; output
demon-captain-display-fixture-01. Run with existing Demon assets03 and room105
through tools/p2_demon_visual_run.py into a fresh session directory. Exact
command flags are the same as P2_DEMON_VISUAL.md with the new fixture path.

P1 host audit: Navi::doAI executes its state machine at navi.cpp:1471;
Navi::update performs independent physics/status work. Navi::draw at2370
rebuilds its world matrix from SRT unless actually on a rope. Therefore a
one-time matrix assignment cannot implement mouth attachment. Never spoof
mRope with a fake pointer to enter its constrained-matrix branch. Dedicated
capture state/update/draw hooks are needed and remain integration-owned.
P2 NSID_Sarai recommendations cannot be treated as existing P1 states.

Private fixture01 built with checked provenance and ran successfully in fresh
session dc5a476c837f47b7b12e3e83fd7287bd. Both frame0/frame17 captures were
inspected. Two captain shapes appear beneath the hands in frame0; frame17
changes their orientation/position with the attack pose, with some overlap.
This explains the low center markers without adding a hand offset. It is
visual plausibility for the P1 model, not exact P2 FALL animation or natural
capture acceptance. The ground captain remains visible and independent.
