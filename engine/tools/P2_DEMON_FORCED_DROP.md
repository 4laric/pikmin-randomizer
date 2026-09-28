# Demon forced-drop receiver contract (#236)

Source revision: projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96.
Read-only source under native/pikmin2-research. This is a source contract only;
no P1 damage/state translation or live drop acceptance is claimed.

## Enemy dispatch

Inherited SaraiState.cpp StateFallMeck::exec calls setHeightVelocity, then gates
all animation events on mIsPlaying. KEYEVENT2 enables NoInterrupt; KEYEVENT3 calls
fallMeckGround; KEYEVENT4 disables NoInterrupt; END transitions Move. Cleanup
clears NoInterrupt and resets the attackable timer to zero. Owner death/flick
uses a separate InteractFlick path and must not be relabeled as forced drop.

Sarai.cpp:228 fallMeckGround iterates the owner's Stickers, filters mouth-stuck
creatures, and stimulates InteractFallMeck(owner, retail attackDamage). Only an
accepted receiver receives a virtual setVelocity call with
(0, -retail FallMeckSpeed, 0). Use the Demon parameter block, not header defaults.
Do not infer ownership merely from being stuck to some other owner's mouth.
Releasing during traversal requires source-equivalent safe sticker iteration.

## Captain receiver and ordering

interactNavi.cpp:102 unconditionally transits NSID_FallMeck with the damage arg
and returns true. NaviFallMeckState::init (naviState.cpp:3627) stores damage,
starts FALL, ends stick ownership, and initializes actual AND target vertical
velocity to -400 for positive damage or -100 otherwise. Horizontal components
are not changed by that init. The caller then invokes virtual setVelocity. Navi.h:127 overrides this to assign
mTargetVelocity only: final target velocity is (0,-retail FallMeckSpeed,0),
while actual vertical velocity remains the receiver-initialized -400 or -100.
Do not reverse these operations or accidentally overwrite the final fall speed
with the escape bridge's zero-velocity release helper.

FallMeck is distinct from SaraiExit (#231). It does not use SaraiExit's
setAtari(false) contract. It exits to Walk if FALL motion is lost while still in
its falling substate. Its cleanup is empty. The source GetUp/Finished key-event
branches exist, but this bounce path transitions to KokeDamage or Walk rather
than entering those branches; do not invent a forced in-state get-up sequence.

## Landing and delayed damage

NaviFallMeckState::bounceCallback:3690 creates water/smoke feedback. While falling:
positive damage calls addDamage(0,true), then transits KokeDamage with timer1,
null attacker and stored damage. Nonpositive damage gives a nudge rumble and
transits Walk. This is not a direct subtraction of stored damage at impact.

NaviKokeDamageState::init:3812 starts JKOKE. Its first END event while in Fall
changes substate to Lay and calls addDamage(storedDamage, playSound). This is
the point where the stored positive damage is delivered. Lay decrements the
1-second timer using simulation delta; expiry starts GETUP; its completion
returns Walk or the saved backup state. Movie/inactive-world exec exits early.
Do not convert the source's zero-damage impact call plus delayed real damage
into two positive damage calls, or apply pending damage after interruption.

## P1 integration gates

Keep voluntary escape, forced drop, and owner flick as separate transitions.
A P1 bridge needs explicit release ordering, gravity/terrain motion, animation
event ownership, delayed damage/recovery and cancellation on state interruption
or scene teardown. Clear source-owner slot occupancy when the receiver detaches.
Do not route a forced drop through pc_demon_landed: that currently resumes Walk
and would bypass knockdown. Current #226/#231 modules do not implement this path.

Required future runtime evidence: accepted/rejected receiver ordering, final
actual versus target velocity, floor and water landing, exactly one positive
damage delivery at the knockdown event, repeated bounce/event resilience,
interruption before damage, and cleanup followed by a new captain/owner instance.
