#include "pc_p2_captain.h"

#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"

#include <unordered_map>

// Lane 12 engine glue (#130): binds P2CaptainAdapter to the live P1
// Navi/NaviMgr/PikiMgr. This is the only translation unit that needs engine
// headers; the adapter logic is header-only and engine-free.
//
// Captain slot N is the live `naviMgr->getNavi(N)` (Navi::mNaviID == N). Slot 1
// binds when a second Navi exists (see pc_p2_second_captain.h); on the default
// single-captain port getNavi(1) is null and slot 1 stays absent. The adapter's
// P2CaptainPolicy is the source of truth for active/captured bookkeeping; it
// mirrors Piki::mNavi writes and now routes active/knockout selection into the
// additive NaviMgr helpers (setActiveNavi / informOrimaDead).

namespace {

// Stable nonzero actor ids for live Piki pointers. The registry is cleared by
// teardown(). A freed-then-reused pointer inside one scene can inherit an id;
// captor families must release a captive before its actor is destroyed (the
// same lifetime rule the source captor FSMs follow).
std::unordered_map<void*, std::uint32_t> g_actorIds;
std::uint32_t g_nextActorId = 1;

std::uint32_t actor_id_for(void* actor)
{
    if (!actor) return 0;
    auto it = g_actorIds.find(actor);
    if (it != g_actorIds.end()) return it->second;
    std::uint32_t id = g_nextActorId++;
    if (!id) id = g_nextActorId++; // never hand out 0, the free/unowned sentinel
    g_actorIds[actor] = id;
    return id;
}

void* live_captain_at(void*, int slot)
{
    if (!naviMgr || !P2CaptainOwnershipTable::isCaptain(slot)) return nullptr;
    return static_cast<void*>(naviMgr->getNavi(slot));
}

float live_get_health(void*, void* captain)
{
    if (!captain) return 0.0f;
    return static_cast<Navi*>(captain)->mHealth;
}

void live_set_health(void*, void* captain, float health)
{
    if (!captain) return;
    static_cast<Navi*>(captain)->mHealth = health;
}

std::uint32_t live_actor_id(void*, void* actor) { return actor_id_for(actor); }

int live_owner_slot(void* context, void* actor)
{
    (void)context;
    if (!actor) return P2CaptainInvalid;
    Navi* owner = static_cast<Piki*>(actor)->mNavi;
    if (!owner) return P2CaptainInvalid;
    return P2CaptainOwnershipTable::isCaptain(owner->getNaviIndex()) ? owner->getNaviIndex()
                                                                    : P2CaptainInvalid;
}

void live_set_owner_slot(void* context, void* actor, int slot)
{
    (void)context;
    if (!actor || !naviMgr) return;
    Piki* piki = static_cast<Piki*>(actor);
    piki->mNavi = P2CaptainOwnershipTable::isCaptain(slot) ? naviMgr->getNavi(slot) : nullptr;
}

// Route the adapter's active/knockout selection into NaviMgr's additive
// second-captain bookkeeping. With one Navi these simply touch slot 0/false.
void live_notify_active(void*, int slot)
{
    if (!naviMgr) return;
    Navi* navi = naviMgr->getNavi(slot);
    if (navi) naviMgr->setActiveNavi(navi);
}

void live_notify_knockout(void*, int slot)
{
    if (!naviMgr) return;
    Navi* navi = naviMgr->getNavi(slot);
    if (navi) naviMgr->informOrimaDead(navi);
}

int live_enumerate(void*, P2PikiHandle* out, int capacity)
{
    if (!pikiMgr || !out || capacity <= 0) return 0;
    int count = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it)
    {
        if (count >= capacity) break;
        out[count++] = static_cast<void*>(static_cast<Piki*>(*it));
    }
    return count;
}

P2CaptainHostOps live_ops()
{
    P2CaptainHostOps ops;
    ops.captainAt    = &live_captain_at;
    ops.getHealth    = &live_get_health;
    ops.setHealth    = &live_set_health;
    ops.actorId      = &live_actor_id;
    ops.ownerSlot    = &live_owner_slot;
    ops.setOwnerSlot = &live_set_owner_slot;
    ops.enumerate    = &live_enumerate;
    ops.notifyActive   = &live_notify_active;
    ops.notifyKnockout = &live_notify_knockout;
    return ops;
}

P2CaptainAdapter& live_adapter()
{
    static P2CaptainAdapter instance;
    return instance;
}

// Inactive-captain follow state. Engine-free policy; this file only feeds it
// the live distance and applies the decision. Persistent across frames.
P2SquadFollowPolicy g_secondCaptainFollow;
P2FollowPhase g_secondCaptainFollowPhase = P2FollowPhase::Idle;

} // namespace

namespace pc_p2_captain {

bool setup_from_navi_mgr()
{
    P2CaptainAdapter& adapter = live_adapter();
    if (adapter.bound()) return true;
    if (!naviMgr || !naviMgr->getActiveNavi()) return false;
    if (!adapter.bind(live_ops())) return false;
    if (!adapter.setup()) {
        adapter.teardown();
        return false;
    }
    return true;
}

void teardown()
{
    P2CaptainAdapter& adapter = live_adapter();
    adapter.teardown();
    g_actorIds.clear();
    g_nextActorId = 1;
}

P2CaptainAdapter* adapter() { return live_adapter().bound() ? &live_adapter() : nullptr; }

float health(int captain) { return live_adapter().health(captain); }

bool set_health(int captain, float value) { return live_adapter().setHealth(captain, value); }

bool capture_captain(int captain, std::uint64_t captorEpoch)
{
    return live_adapter().captureCaptain(captain, captorEpoch);
}

bool release_captain(int captain, std::uint64_t captorEpoch)
{
    return live_adapter().releaseCaptain(captain, captorEpoch);
}

bool switch_active(int captain) { return live_adapter().switchActive(captain); }

bool reload() { return live_adapter().reload(); }

int adopt_squad() { return live_adapter().adoptSquad(); }

bool capture_actor(std::uint64_t captorEpoch, P2PikiHandle piki)
{
    return live_adapter().captureActor(captorEpoch, piki);
}

bool release_actor(std::uint64_t captorEpoch, P2PikiHandle piki, int toCaptain)
{
    return live_adapter().releaseActor(captorEpoch, piki, toCaptain);
}

std::vector<std::uint32_t> drop_captured(std::uint64_t captorEpoch)
{
    return live_adapter().dropAllCaptured(captorEpoch);
}

std::vector<std::uint32_t> split_squad(int from, int to, std::size_t count)
{
    return live_adapter().splitSquad(from, to, count);
}

void update_inactive_captain_follow()
{
    // Narrow hook: inert unless a real second Navi exists. On the default
    // single-captain port hasSecondNavi() is false, so this never runs and
    // default play is byte-identical.
    if (!naviMgr || !naviMgr->hasSecondNavi()) {
        return;
    }

    Navi* active = naviMgr->getActiveNavi();
    Navi* inactive = active ? naviMgr->getOtherNavi(active) : nullptr;
    if (!active || !inactive || !inactive->isAlive()) {
        return;
    }

    Vector3f delta = active->getPosition() - inactive->getPosition();
    delta.y = 0.0f;
    f32 distance = delta.length();
    const bool leaderMoving = active->mVelocity.length() > 20.0f;

    P2FollowPhase phase = g_secondCaptainFollow.update(distance, leaderMoving);
    g_secondCaptainFollowPhase = phase;

    // Approximate NaviFollowState::exec (source naviState.cpp:1501-1551): walk
    // toward the controlled captain, halt inside the stop radius. Full
    // state-machine parity (idle goofs, autopluck, push-away) remains open.
    if (phase == P2FollowPhase::Follow && distance > 0.0001f) {
        delta.normalise();
        f32 speed = P2SquadFollowPolicy::followSpeed(distance, C_NAVI_PARM(inactive, mMoveSpeed));
        inactive->mTargetVelocity = delta * speed;
        inactive->mFaceDirection = atan2f(delta.x, delta.z);
    } else if (phase == P2FollowPhase::Idle) {
        inactive->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
    }
}

P2FollowPhase inactive_captain_follow_phase()
{
    return g_secondCaptainFollowPhase;
}

bool has_second_captain()
{
    return naviMgr && naviMgr->hasSecondNavi();
}

int other_captain(int captain)
{
    return p2_other_captain(captain);
}

} // namespace pc_p2_captain
