#include "pc_p2_onikurage_teki.h"
#include "pc_p2_onikurage_teki_policy.h"
#include "pc_p2_onikurage_mouth.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_kurage_visual.h"
#include "Collision.h"
#include "Generator.h"
#include "system.h"
#include "teki.h"
#include <cstdio>
#include <fstream>
#include <map>

namespace {
struct Binding {
    unsigned generator;
    int type;
    CollPart suck; // shared Pikmin suction coll part (OniKurage.cpp:568 'suck')
    p2onikurage::MouthSlots mouthSlots; // two captain mouth slots (OniKurage.cpp:251)
};
std::map<BTeki*, Binding> s;

void revoke(BTeki* t)
{
    auto i = s.find(t);
    if (i == s.end()) return;
    pc_p2_kurage_receiver_owner_invalidated(t);
    s.erase(i);
}

void refresh(BTeki* t, Binding& b)
{
    b.suck.mPartType = PART_BoundSphere;
    b.suck.mRadius = 15.0f;
    b.suck.mCentre = t->mSRT.t;
    b.suck.mJointMatrix.makeIdentity();
}
} // namespace

void pc_p2_onikurage_teki_reset()
{
    for (auto& x : s) pc_p2_kurage_receiver_owner_invalidated(x.first);
    s.clear();
}

void pc_p2_onikurage_teki_forget(BTeki* t)
{
    if (t) revoke(t);
}

bool pc_p2_onikurage_teki_is_bound(const BTeki* t)
{
    return t && s.count(const_cast<BTeki*>(t)) != 0;
}

void pc_p2_onikurage_teki_setup()
{
    pc_p2_onikurage_teki_reset();
    std::ifstream in("p2-onikurage-teki.txt");
    if (!in) return;
    p2onikurage::Binding cfg{};
    if (!p2onikurage::read(in, cfg) || !tekiMgr) std::abort();
    const unsigned gen = cfg.generator;
    const int type = cfg.type;
    Iterator it(tekiMgr);
    CI_LOOP(it)
    {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator || t->mGenerator->_70 != gen) continue;
        if (t->mTekiType != type || s.size()) std::abort();
        if (!pc_p2_kurage_visual_setup()) std::abort();
        auto inserted = s.emplace(static_cast<BTeki*>(t), Binding{gen, type, {}, {}});
        Binding& b = inserted.first->second;
        refresh(t, b);
        if (!pc_p2_kurage_receiver_setup(t, &b.suck)) std::abort();
        std::printf("P2_ONIKURAGE_TEKI_READY generator=%u type=%d variant=Greater mouth_slots=%d binding=private_adapter\n",
            gen, type, p2onikurage::kMouthSlotCount);
    }
}

void pc_p2_onikurage_teki_tick(BTeki* t)
{
    auto i = s.find(t);
    if (i == s.end()) return;
    if (!t->isAlive()) { revoke(t); return; }
    refresh(t, i->second);
    // Pikmin suction reuses the shared receiver: OniKurage's Pikmin loop is
    // Kurage's loop verbatim (interactPiki InteractSuikomi_Test on 'suck').
    pc_p2_kurage_receiver_update(gsys->getFrameTime(), true, t->mHealth > 0.0f, false);
    // Captain mouth slots settle toward the source rest pose while held. The
    // bounded fixture never attaches a Navi, so flickStickNavi/escapeCheckNavi
    // are exercised by the standalone mouth policy fixture instead.
    for (int slot = 0; slot < p2onikurage::kMouthSlotCount; ++slot)
        i->second.mouthSlots.advanceDefaultOffset(slot);
}

bool pc_p2_onikurage_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& matrix, bool corpse)
{
    if (!s.count(t)) return false;
    // No OniKurage-specific converted MOD exists yet; the bounded host reuses
    // the Kurage wait/attack shapes as the established visual stand-in.
    return pc_p2_kurage_visual_draw(t, gfx, matrix, corpse);
}

int pc_p2_onikurage_teki_mouth_slots()
{
    if (s.empty()) return 0;
    return p2onikurage::kMouthSlotCount;
}

int pc_p2_onikurage_teki_bound_count()
{
    return static_cast<int>(s.size());
}
