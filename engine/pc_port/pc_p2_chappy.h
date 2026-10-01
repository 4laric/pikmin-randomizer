#pragma once
#include <string>
class BTeki;
class Creature;
class CollPart;
class PelletView;
class Graphics;
struct Matrix4f;

// Own-identity Chappy family (inst-chappy, #871): Red Bulborb (2),
// Fiery Bulblax (33), Spotty Bulbear (35), Hairy Bulborb (43), Emperor
// Bulblax (53), Bulbmin (67) and Dwarf Bulbear (76).
//
// Source: P2 ChappyBase/KumaChappy/KumaKochappy/KingChappy FSMs, parms and
// anims (see pc_p2_chappy_policy.h / pc_p2_chappy_fsm.h). Each actor keeps
// its proven P1 host vehicle for the body/corpse pellet only; the P2 FSM
// ported here drives movement/targeting/attacks every tick and the P1 host
// AI is suppressed via pc_p2_chappy_suppress_ai (doAI early-return) plus
// host blinding in pc_p2_chappy_param_f. The module binds the P2 identity
// (retail health, species name), draws the staged P2 pose bank from the FSM
// clip/phase, tracks damage/death, leaves the natural carriable corpse
// pellet with the P2 corpse drawn, and binds the ordinary-delivery source
// so the Onion receipt lands as onion:p2:<source_id>. Opt-in: only actors
// claimed by the generated-placement bridge (seed source) or listed in
// `p2-chappy-actors.txt` are registered. Every hook is a no-op for
// unregistered actors.
void pc_p2_chappy_setup();
void pc_p2_chappy_reset();
void pc_p2_chappy_forget(BTeki*);
void pc_p2_chappy_update(BTeki*);
float pc_p2_chappy_max_health(const BTeki*, float fallback);
float pc_p2_chappy_param_f(const BTeki*, int idx, float fallback);
bool pc_p2_chappy_suppress_ai(const BTeki*);
bool pc_p2_chappy_probe(const BTeki*, const char** state, const char** clip, float* phase);
// Kumako Press trigger (source pressCallBack -> Press -> Dead). No in-engine
// P1-vehicle press callback is wired to this P2 actor, so this stays a
// bounded manual trigger for completeness; hp<=0 still reaches Dead.
void pc_p2_chappy_press(BTeki* actor);
// #884: source KingChappy::damageCallBack acceptance for the Emperor Bulblax
// (kingChappy.cpp:824-848), evaluated by InteractAttack::actTeki on the hit's
// owner and collision part before the host sees it. Returns < 0 for any actor
// that is not a live registered King (no change), 0 when the source refuses
// the hit (no damage, no flick), else the source damage rate (1.0 stuck
// attacker with a part, 0.2 partless attacker low within 40 XZ).
float pc_p2_chappy_king_damage_rate(BTeki* actor, Creature* owner, CollPart* part);
// #884 round 3: source EnemyBase::addDamage flickSpeed for the Emperor
// Bulblax. Called by InteractAttack::actTeki with its accept result, only for
// hits pc_p2_chappy_king_damage_rate passed; adds 1.0 to the King's flick
// timer per accepted hit. No-op for every other actor.
void pc_p2_chappy_attacked(BTeki* actor, bool accepted);
// Emperor Bulblax bombCallBack (kingChappy.cpp:875-880): a bomb blast that reaches a Teki.
// Returns true when `actor` is a registered Emperor (0.25 x damage, flick +1.0; nothing
// while buried or dead); false leaves the host path unchanged.
bool pc_p2_chappy_king_bomb(BTeki* actor, float damage);
const char* pc_p2_chappy_name(PelletView*);
bool pc_p2_chappy_registered(const BTeki*);
bool pc_p2_chappy_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
unsigned long pc_p2_chappy_count();
// Preview (room) corpse receipt: corpse:<prefix>chappy:<generator>.
bool pc_p2_chappy_receipt(PelletView*, unsigned& generator);

// Generated-placement bridge: claim the spawned actor for its seeded
// Chappy-family source id and bind the P2 identity.
bool pc_p2_chappy_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned sourceId);
