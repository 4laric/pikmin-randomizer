#pragma once
class Piki;
class Creature;

// P2 InteractAstonish receiver (source interactPiki.cpp:473, PikiPanicState with
// PIKIPANIC_Panic): the target Pikmin freezes, notices (KIZUKU), panic-runs for the
// Pikmin panic time and then returns to the ordinary walking state. Non-lethal.
// First producer: Mitite (TamagoMushi, #992). The Antenna Beetle owner-death
// release keeps its own registry (pc_p2_fuefuki_teki); PikiPanicState honours both.
//
// pc_p2_astonish_request returns true when the Pikmin was accepted (alive, not
// Purple, not in an untransittable state, not already panicking).
bool pc_p2_astonish_request(Piki* piki, Creature* source, unsigned token, const char* who);
// PikiPanicState seams: true while this Panic was requested through this module.
bool pc_p2_astonish_pending(const Piki*);
void pc_p2_astonish_end(Piki*, bool timedOut);
void pc_p2_astonish_reset();
// Counters for the fixture log and the headless verifier.
unsigned pc_p2_astonish_started();
unsigned pc_p2_astonish_ended();
