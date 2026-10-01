// Shared P2 body collision for P2 meshes drawn on a P1 host (branch
// claude/p2-stick-surface). See pc_p2_body_fit.h for the why.
//
// A registered P2 actor swaps the host's collision tree for spheres fitted to
// the drawn rest-pose mesh (P2FlyerColl mechanism), so Pikmin latch on the
// visible surface. Species rest poses are registered by the draw families at
// bank load; the tree is bound on the actor's first tick and given back at
// death. PIKMIN_P2_BODY_COLL=0 keeps every host tree (A/B evidence).
#pragma once

#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_blend.h"

#include <string>

class BTeki;
class Creature;
class CollPart;

// Opts a species key (for example "snagret|Bloyster") into the shared body collision. The
// key must match the draw family's actor key that calls pc_p2_body_coll_assign(). The
// species' rest pose is registered with pc_p2_body_coll_register_pose() or
// pc_p2_body_coll_register_bank() when its bank loads. `drawUnscaled` is true when the
// species draw normalises the host scale away (pc_p2_queen_teki.cpp sourceScale).
void pc_p2_body_coll_manage(const std::string& key, bool drawUnscaled = false);
void pc_p2_body_coll_reset();
void pc_p2_body_coll_forget(BTeki* actor);
// Fits and stores the species rest pose (mesh units). Returns true when a fit
// table was stored. Keys the module does not manage are ignored.
bool pc_p2_body_coll_register_pose(const std::string& key, const p2pose::Pose& rest);
// Names the species key of a registered actor (idempotent, cheap).
void pc_p2_body_coll_assign(BTeki* actor, const std::string& key);
// Per-tick hook (BTeki::update, after the species ticks): binds, follows and
// releases the tree. No-op for actors with no assigned key.
void pc_p2_body_coll_update(BTeki* actor);
bool pc_p2_body_coll_bound(const BTeki* actor);
// Stick probe (Creature::startStickObject): logs where a Pikmin latched
// relative to the part it stuck to. Bounded output; no-op for non-P2 targets.
void pc_p2_body_coll_note_stick(Creature* sticker, Creature* target, CollPart* part);

// Registers the rest pose of a loaded bank (first pose of the wait clip, else of
// any clip). `baked` is a map<string, vector<p2pose::Baked>>. Idempotent.
template <class BakedMap>
inline void pc_p2_body_coll_register_bank(const std::string& key, const BakedMap& baked)
{
    static const char* const rest[] = {"wait1", "wait2", "wait", "wait3", "waitact1", "waitact2"};
    const p2pose::Pose* pick = nullptr;
    for (const char* clip : rest) {
        auto it = baked.find(std::string(clip));
        if (it != baked.end() && !it->second.empty()) {
            pick = &it->second.front().pose;
            break;
        }
    }
    if (!pick) {
        for (const auto& entry : baked) {
            if (!entry.second.empty()) {
                pick = &entry.second.front().pose;
                break;
            }
        }
    }
    if (pick) pc_p2_body_coll_register_pose(key, *pick);
}
