#pragma once
// Co-op captain selection for the P2 enemy modules (#888 WP3).
//
// P2 enemy code never asks for "the" captain: EnemyFunc::getNearestNavi,
// flickNearbyNavi, attackNavi and isThereOlimar all walk Iterator<Navi>
// (enemyAction.cpp) in manager index order, and target code that the source
// writes against naviMgr->getActiveNavi() switches to the nearest captain in
// two-player mode (umiMushi.cpp:849-853, isTwoPlayerMode). The P1 host's
// naviMgr->getNavi() is captain 1 only, so the P2 modules walk a snapshot of
// every Navi instead.
//
// The core below is engine-free (templated on the navi type) so
// tools/p2_navi_select_test.cpp can drive it with fake captains. The engine
// wrappers at the bottom are compiled out with P2_NAVI_SELECT_NO_ENGINE.
//
// Single-captain contract: with one Navi the roster is exactly
// { naviMgr->getNavi() } (the Iterator's first entry is what getNavi()
// returns), nearest() falls back to it, and sourceActive() returns it, so every
// converted site behaves exactly as it did with getNavi(). Iteration order is
// the manager index order; nothing here reads a clock or an RNG.

namespace p2navisel {

// P2CaptainRoster::kSlots is 2; leave headroom without allocating.
constexpr int kMaxNavis = 4;

template <class N>
struct Roster {
    N* items[kMaxNavis] = {};
    int count = 0;

    void add(N* n)
    {
        if (n && count < kMaxNavis) items[count++] = n;
    }
    N* const* begin() const { return items; }
    N* const* end() const { return items + count; }
    int size() const { return count; }
    bool empty() const { return count == 0; }
    // Slot 0: what naviMgr->getNavi() returns.
    N* first() const { return count ? items[0] : nullptr; }
};

// Index of the nearest entry accepted by `eligible`, by XZ squared distance to
// (x, z), or -1. Strict '<' keeps the lowest index on ties (source
// getNearestNavi and NaviMgr::getNearestNavi use the same comparison).
template <class N, class Eligible, class Where>
int nearestIndex(const Roster<N>& r, float x, float z, Eligible eligible, Where where)
{
    int best = -1;
    float bestSq = 0.0f;
    for (int i = 0; i < r.count; ++i) {
        N* n = r.items[i];
        if (!eligible(n)) continue;
        float nx = 0.0f, nz = 0.0f;
        where(n, nx, nz);
        const float dx = nx - x, dz = nz - z;
        const float d = dx * dx + dz * dz;
        if (best < 0 || d < bestSq) {
            best = i;
            bestSq = d;
        }
    }
    return best;
}

// First entry in index order accepted by `pred`, or -1 (source loops that
// return on the first match, e.g. Demon::getAttackableTarget).
template <class N, class Pred>
int firstIndex(const Roster<N>& r, Pred pred)
{
    for (int i = 0; i < r.count; ++i)
        if (pred(r.items[i])) return i;
    return -1;
}

// Nearest eligible captain, else slot 0 (NaviMgr::getNearestNavi contract:
// never null while a Navi exists, so a caller's own alive check still sees
// captain 1 exactly as it did with getNavi()).
template <class N, class Eligible, class Where>
N* nearest(const Roster<N>& r, float x, float z, Eligible eligible, Where where)
{
    const int i = nearestIndex(r, x, z, eligible, where);
    return i >= 0 ? r.items[i] : r.first();
}

// Source naviMgr->getActiveNavi() under the P1 host: one captain -> slot 0;
// two-player (co-op) -> the nearest eligible captain (umiMushi.cpp:849-850);
// otherwise the controlled captain the roster reports, else slot 0.
template <class N, class Eligible, class Where>
N* sourceActive(const Roster<N>& r, bool twoPlayer, N* controlled, float x, float z, Eligible eligible, Where where)
{
    if (r.count <= 1) return r.first();
    if (twoPlayer) return nearest(r, x, z, eligible, where);
    return controlled ? controlled : r.first();
}

} // namespace p2navisel

#ifndef P2_NAVI_SELECT_NO_ENGINE
#include <cmath>
#include "NaviMgr.h"
#include "pc_coop.h"

using P2NaviRoster = p2navisel::Roster<Navi>;

// Snapshot of every Navi in manager (Iterator) order. A snapshot, not a live
// iterator, so a receiver that kills or removes a captain cannot invalidate
// the walk. Empty when naviMgr is null.
inline P2NaviRoster pc_p2_navis()
{
    P2NaviRoster r;
    if (naviMgr) {
        Iterator it(naviMgr);
        CI_LOOP(it) { r.add(static_cast<Navi*>(*it)); }
    }
    return r;
}

inline void pc_p2_navi_xz(Navi* n, float& x, float& z)
{
    x = n->mSRT.t.x;
    z = n->mSRT.t.z;
}

// Nearest alive captain to `pos` (XZ), else captain 1; null only without a Navi.
inline Navi* pc_p2_nearest_navi(const Vector3f& pos)
{
    return p2navisel::nearest(pc_p2_navis(), pos.x, pos.z, [](Navi* n) { return n->isAlive(); }, pc_p2_navi_xz);
}

// Replacement for a P2 source naviMgr->getActiveNavi() call site.
inline Navi* pc_p2_source_active_navi(const Vector3f& pos)
{
    const P2NaviRoster r = pc_p2_navis();
    Navi* controlled = r.size() > 1 && naviMgr ? naviMgr->getActiveNavi() : nullptr;
    return p2navisel::sourceActive(r, pc_coop_active(), controlled, pos.x, pos.z,
                                   [](Navi* n) { return n->isAlive(); }, pc_p2_navi_xz);
}

// Captain for a captor host (Demon/Sarai captain path): the one this host
// already holds (`owned`), else the first captain in index order that the
// source acquisition accepts (alive, not mouth-held, |bearing| <= view angle,
// XZ distance < sight; Demon.cpp:30-47), else the nearest alive free captain,
// else captain 1. With one Navi this is always captain 1.
template <class Owned>
inline Navi* pc_p2_captor_navi(const Vector3f& from, float face, float viewDeg, float sight, Owned owned)
{
    const P2NaviRoster r = pc_p2_navis();
    if (r.size() <= 1) return r.first();
    int i = p2navisel::firstIndex(r, owned);
    if (i >= 0) return r.items[i];
    auto freeNavi = [](Navi* n) { return n->isAlive() && !n->isStickToMouth(); };
    i = p2navisel::firstIndex(r, [&](Navi* n) {
        if (!freeNavi(n)) return false;
        const float dx = n->mSRT.t.x - from.x, dz = n->mSRT.t.z - from.z;
        float bearing = std::atan2(dx, dz) - face;
        while (bearing > 3.14159265358979323846f) bearing -= 6.28318530717958647692f;
        while (bearing < -3.14159265358979323846f) bearing += 6.28318530717958647692f;
        return std::fabs(bearing) <= viewDeg * 0.017453292519943295f && dx * dx + dz * dz < sight * sight;
    });
    if (i >= 0) return r.items[i];
    return p2navisel::nearest(r, from.x, from.z, freeNavi, pc_p2_navi_xz);
}

inline bool pc_p2_is_navi(Creature* c)
{
    return c && c->mObjType == OBJTYPE_Navi;
}
#endif
