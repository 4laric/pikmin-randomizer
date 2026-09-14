#include "pc_p2_kurage_teki.h"
#include "pc_p2_kurage_fsm.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_kurage_teki_policy.h"
#include "pc_p2_kurage_visual.h"
#include "pc_p2_retail_player.h"
#include "Camera.h"
#include "Collision.h"
#include "Generator.h"
#include "Graphics.h"
#include "Shape.h"
#include "MapMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "system.h"
#include "teki.h"
#include <cstdio>
#include <fstream>
#include <map>
namespace {
struct Binding {
    unsigned generator;
    int type;
    CollPart mouth;
    // Opt-in source flight-lifecycle authority.  Off by default so the
    // binding-only consumers keep the original draw + receiver behaviour.
    p2kurage::Fsm fsm;
    bool fsmEnabled = false;
    p2retail::Player attackPlayer;
    bool attackPlaying = false;
    bool sucking = false;
    p2kurage::KeyEvent pendingKey = p2kurage::KeyEvent::None;
    bool motionFinished = false;
    int motionTimer = 0;
    int autoAdmissions = 0;
    int fsmTicks = 0;
};
std::map<BTeki*, Binding> s;
int gTickCalls = 0;
// p2retail::Player timers are animation frames; attack.bca is a 30 fps clip.
constexpr float kAttackFramesPerSecond = 30.0f;
// Bounded animation-END stand-in until the #431 motion-event bridge exists.
constexpr int kFsmMotionFrames = 30;
// Kurage.h mAttackRadius (asset ProperParms value not yet imported) and ip11.
constexpr float kSourceAttackRadius = 35.0f;
constexpr int kMaxAutoAdmissions = 10;
// Retail Kurage attack.bca event table (enemyanimmgr.txt): 37=KEYEVENT_2 suck
// start, 60=loop, 67=KEYEVENT_1 suck end.
const p2retail::Motion kAttackMotion{
    "attack.bca", "302660c6ba9c86fee11cc6aca98bd514e201a80d8530be3a5cce867a9dc74a4e",
    120, 2, { { 37, 2 }, { 60, 0 }, { 67, 1 } }
};

void revoke(BTeki* t)
{
    auto i = s.find(t);
    if (i == s.end()) return;
    pc_p2_kurage_receiver_owner_invalidated(t);
    s.erase(i);
}

void refresh(BTeki* t, Binding& b)
{
    b.mouth.mPartType = PART_BoundSphere;
    b.mouth.mRadius = 15.0f;
    b.mouth.mCentre = t->mSRT.t;
    b.mouth.mJointMatrix.makeIdentity();
}

// getSearchedTarget approximation for the ordinary actor: first live Pikmin in
// the source vertical suction window and attack radius not already stuck here.
Piki* findSuctionTarget(BTeki* t)
{
    if (!pikiMgr || !t) return nullptr;
    ObjectMgr* manager = static_cast<ObjectMgr*>(pikiMgr);
    const float radiusSqr = kSourceAttackRadius * kSourceAttackRadius;
    for (int it = manager->getFirst(); !manager->isDone(it); it = manager->getNext(it)) {
        Piki* piki = static_cast<Piki*>(manager->getCreature(it));
        if (!piki || !piki->isAlive() || piki->getStickObject() == t || !piki->mayIstick()) continue;
        if (!p2kurage::inSuctionWindow(t->mSRT.t.y, 0.0f, piki->mSRT.t.y)) continue;
        const float dx = piki->mSRT.t.x - t->mSRT.t.x;
        const float dz = piki->mSRT.t.z - t->mSRT.t.z;
        if (dx * dx + dz * dz >= radiusSqr) continue;
        return piki;
    }
    return nullptr;
}

void tickAttack(Binding& b, float dt)
{
    if (!b.attackPlaying) return;
    const p2retail::Update result = b.attackPlayer.advance(dt, [&b](const p2retail::Event& event) {
        if (event.type == 2) {
            b.sucking = true;
            b.pendingKey = p2kurage::KeyEvent::Key2;
        } else if (event.type == 1 || event.type == 1000) {
            b.sucking = false;
            b.attackPlaying = false;
            b.attackPlayer.cancel();
            b.pendingKey = p2kurage::KeyEvent::Key1;
            b.motionFinished = true;
        }
    });
    if (result == p2retail::Update::Inactive || result == p2retail::Update::Invalid) b.attackPlaying = false;
}
} // namespace

void pc_p2_kurage_teki_reset()
{
    for (auto& x : s) pc_p2_kurage_receiver_owner_invalidated(x.first);
    s.clear();
}
void pc_p2_kurage_teki_forget(BTeki* t) { if (t) revoke(t); }
bool pc_p2_kurage_teki_is_bound(const BTeki* t) { return t && s.count(const_cast<BTeki*>(t)); }

void pc_p2_kurage_teki_setup()
{
    pc_p2_kurage_teki_reset();
    std::ifstream in("p2-kurage-teki.txt");
    if (!in) return;
    p2kurage::Binding cfg{};
    if (!p2kurage::read(in, cfg) || !tekiMgr) std::abort();
    unsigned gen = cfg.generator;
    int type = cfg.type;
    Iterator it(tekiMgr);
    CI_LOOP(it)
    {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator || t->mGenerator->_70 != gen) continue;
        if (t->mTekiType != type || s.size()) std::abort();
        if (!pc_p2_kurage_visual_setup()) std::abort();
        auto inserted = s.emplace(static_cast<BTeki*>(t), Binding{ gen, type, {} });
        Binding& b = inserted.first->second;
        refresh(t, b);
        if (!pc_p2_kurage_receiver_setup(t, &b.mouth)) std::abort();
        std::printf("P2_KURAGE_TEKI_READY generator=%u type=%d binding=private_adapter\n", gen, type);
    }
}

void pc_p2_kurage_teki_tick(BTeki* t)
{
    ++gTickCalls;
    auto i = s.find(t);
    if (i == s.end()) return;
    if (!t->isAlive()) { revoke(t); return; }
    Binding& b = i->second;
    const float dt = gsys->getFrameTime();
    if (!b.fsmEnabled) {
        refresh(t, b);
        pc_p2_kurage_receiver_update(dt, true, t->mHealth > 0.0f, false);
        return;
    }

    // Source flight lifecycle authority for the ordinary generated actor.
    p2kurage::In in;
    in.deltaTime = dt;
    in.health = t->mHealth;
    // Mouth-travel Pikmin are not body-stuck; only stomach-attached ones count
    // toward the source fall/flick threshold.
    in.stuckPikminCount = pc_p2_kurage_receiver_stomach_count();
    in.isFlying = true;
    in.mapY = mapMgr ? mapMgr->getMinY(t->mSRT.t.x, t->mSRT.t.z, false) : 0.0f;
    in.positionY = t->mSRT.t.y;
    in.targetFound = findSuctionTarget(t) != nullptr || pc_p2_kurage_receiver_count() > 0;
    in.suckTarget = in.targetFound;
    in.suckAny = in.targetFound;
    in.motionFrame = b.attackPlaying ? b.attackPlayer.frame() : 0.0f;
    bool motionEnd = false;
    if (!b.attackPlaying && ++b.motionTimer >= kFsmMotionFrames) { b.motionTimer = 0; motionEnd = true; }
    in.motionFinished = b.motionFinished || motionEnd;
    in.keyEvent = b.pendingKey;
    b.pendingKey = p2kurage::KeyEvent::None;
    b.motionFinished = false;

    const p2kurage::Out out = b.fsm.tick(in);
    ++b.fsmTicks;
    t->mSRT.t.y += out.heightVelocity * dt;
    if (out.state == p2kurage::State::Attack && out.motionChanged && !b.attackPlaying) {
        if (b.attackPlayer.start(kAttackMotion)) {
            b.attackPlaying = true;
            b.autoAdmissions = 0;
            b.motionTimer = 0;
        }
    }
    tickAttack(b, dt * kAttackFramesPerSecond);
    refresh(t, b);
    if ((out.isSucking || b.sucking)
        && pc_p2_kurage_receiver_scan_admit(0.0f, kSourceAttackRadius, kMaxAutoAdmissions, true) > 0)
        ++b.autoAdmissions;
    pc_p2_kurage_receiver_update(dt, true, t->mHealth > 0.0f, false);
}

bool pc_p2_kurage_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& matrix, bool corpse)
{
    auto i = s.find(t);
    if (i == s.end()) return false;
    if (i->second.fsmEnabled) {
        Shape* shape = pc_p2_kurage_visual_shape(
            pc_p2_kurage_visual_motion_for_state((int)i->second.fsm.state()));
        if (shape) {
            shape->updateAnim(gfx, matrix, nullptr, t);
            shape->drawshape(gfx, *gfx.mCamera, nullptr);
            return true;
        }
    }
    return pc_p2_kurage_visual_draw(t, gfx, matrix, corpse);
}

void pc_p2_kurage_teki_fsm_enable(bool enable)
{
    for (auto& x : s) {
        x.second.fsmEnabled = enable;
        if (enable) { x.second.fsm = p2kurage::Fsm(); x.second.fsm.spawn(); }
    }
}
bool pc_p2_kurage_teki_fsm_enabled(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i != s.end() && i->second.fsmEnabled;
}
int pc_p2_kurage_teki_fsm_state(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? -1 : (int)i->second.fsm.state();
}
int pc_p2_kurage_teki_auto_admissions(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? 0 : i->second.autoAdmissions;
}
int pc_p2_kurage_teki_fsm_ticks(const BTeki* t)
{
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? -1 : i->second.fsmTicks;
}
int pc_p2_kurage_teki_tick_calls()
{
    return gTickCalls;
}
