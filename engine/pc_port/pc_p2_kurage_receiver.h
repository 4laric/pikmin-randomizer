#pragma once

class CollPart;
class Creature;
class Piki;

// Private P1 adapter for the Lesser Kurage receiver.  It owns only the Piki
// attachment and digest lifetime; collision detection remains an actor hook.
void pc_p2_kurage_receiver_reset();
bool pc_p2_kurage_receiver_setup(Creature* owner, CollPart* mouth);
bool pc_p2_kurage_receiver_capture(Piki* piki);
// Starts source-shaped mouth travel.  Direct capture remains the bounded
// stomach-entry helper used by lifecycle fixtures.
bool pc_p2_kurage_receiver_admit(Piki* piki);
// True while the receiver owns this Piki's mouth-travel or stomach lifecycle.
// Piki::doAI uses this to keep ordinary actions from replacing suction motion
// or detaching a swallowed Piki before the receiver releases it.
bool pc_p2_kurage_receiver_controls(const Piki* piki);
// `admitEligible` is an explicit deterministic fixture/host gate.  Retail
// per-candidate random chance belongs to the missing Kurage attack FSM.
int pc_p2_kurage_receiver_scan_admit(float verticalOffset, float attackRadius, int maxAdmissions, bool admitEligible);
// `ownerHasHealth` matches the source pause condition.  The caller owns the
// actual Kurage health state; this private receiver owns only the attachment.
void pc_p2_kurage_receiver_update(float delta, bool ownerAlive, bool ownerHasHealth, bool bittered);
void pc_p2_kurage_receiver_release_all();
void pc_p2_kurage_receiver_owner_invalidated(Creature* owner);
void pc_p2_kurage_receiver_piki_invalidated(Piki* piki);
int pc_p2_kurage_receiver_count();
int pc_p2_kurage_receiver_stomach_count();
