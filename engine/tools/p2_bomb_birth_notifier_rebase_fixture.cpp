#undef NDEBUG
// Guarded fixture proving the rebased port Bomb birth hook-notifier (#726).
//
// Rebases the reviewed #715 fixture shape onto the current wave line: links the
// REAL notifier TU (no local redefinition) and the REAL wave-tip manager core +
// payload TU, and mirrors the two hooked generalEnemyMgr create arms
// (Bomb/BombOtakara cases only). Labeled mimic: the engine filter lives in the
// rebased generalEnemyMgr.cpp reference, proven by the engine link, not here.
//
// Build (no engine): g++ -std=c++17 -Ipc_port -DP2_BOMB_MGR_BIRTH_NO_HOST
//   tools/p2_bomb_birth_notifier_rebase_fixture.cpp pc_port/pc_p2_bomb_notifier.cpp
//   pc_port/pc_p2_bomb_mgr_birth.cpp pc_port/pc_p2_bomb_payload_actor.cpp
// Captain safety (#632): engine-free proof (no captain, no Navi, no HP); the
// guard predicate below mirrors scripts/p2_fixture_captain_guard.h
// (orimaDead/NaviDead/HP<=1/nonfinite -> BLOCKED) and is asserted as a pure
// check. Any future runtime consumer must adopt that header before launch; its
// hash is recorded in the lane packet, not claimed as a runtime run.
#include "pc_p2_bomb_notifier.h"
#include "pc_p2_bomb_mgr_birth.h"

#include <cassert>
#include <cmath>
#include <cstdio>

// Source IDs routed through the hook (Bomb 36, BombOtakara family).
static const int kEnemyID_Bomb = 36;
static const int kEnemyID_BombOtakara = 93;

// Mirrors the two hooked generalEnemyMgr create arms (Bomb/BombOtakara cases
// only); calls the REAL linked notifier. Labeled mimic: the engine filter
// lives in generalEnemyMgr.cpp, proven by the engine link, not here.
static void engine_create_arm(int enemyID)
{
    if (enemyID == kEnemyID_Bomb || enemyID == kEnemyID_BombOtakara) {
        pc_p2_bomb_birth_hook_notify(enemyID);
    }
}

static P2BombSaraiVec3 joint(float x, float y, float z)
{
    P2BombSaraiVec3 v;
    v.x = x;
    v.y = y;
    v.z = z;
    return v;
}

// Captain-guard predicate mirror (scripts/p2_fixture_captain_guard.h).
static bool captain_down(bool orimaDead, bool deadState, float hp)
{
    return orimaDead || deadState || !std::isfinite(hp) || hp <= 1.0f;
}

int main()
{
    // 1. Hook fires exactly for Bomb-family manager creation, nothing else.
    {
        p2_bomb_notifier_reset();
        engine_create_arm(kEnemyID_Bomb);
        engine_create_arm(kEnemyID_BombOtakara);
        engine_create_arm(10);
        engine_create_arm(0);
        assert(p2_bomb_notifier_count() == 2);
        assert(p2_bomb_notifier_last() == kEnemyID_BombOtakara);
        std::puts("PASS rebase-hook-selective");
    }
    // 2. The notifier pipe is faithful (no invented filtering inside it).
    {
        p2_bomb_notifier_reset();
        pc_p2_bomb_birth_hook_notify(10);
        assert(p2_bomb_notifier_count() == 1);
        assert(p2_bomb_notifier_last() == 10);
        std::puts("PASS rebase-notifier-pipe-faithful");
    }
    // 3. Provider membership + birth + #577 payload handoff (source 93 path).
    {
        P2BombMgr mgr(2);
        P2BombPayloadConfig config;
        P2BombMgrHandle bad = mgr.birth(7, joint(0, 0, 0), config);
        assert(!p2_bomb_mgr_handle_valid(bad));
        mgr.registerCarrier(7);
        P2BombMgrHandle h = mgr.birth(7, joint(1, 2, 3), config);
        assert(p2_bomb_mgr_handle_valid(h));
        assert(mgr.isLive(h));
        assert(p2_bomb_payload_handle_valid(mgr.payloadHandle(h)));
        assert(mgr.findLive(7).slot == h.slot);
        std::puts("PASS rebase-birth-and-payload-handoff");
    }
    // 4. Forget/reset clear without stale handles.
    {
        P2BombMgr mgr(2);
        mgr.registerCarrier(9);
        P2BombPayloadConfig config;
        P2BombMgrHandle h = mgr.birth(9, joint(0, 0, 0), config);
        assert(p2_bomb_mgr_handle_valid(h));
        assert(mgr.onCarrierGone(h));
        assert(!mgr.isLive(h));
        mgr.reset();
        assert(mgr.activeCount() == 0);
        assert(mgr.registeredCount() == 0);
        std::puts("PASS rebase-forget-reset-clean");
    }
    // 5. Captain-guard predicate mirror (no captain here; pure check).
    {
        assert(!captain_down(false, false, 100.0f));
        assert(captain_down(true, false, 100.0f));
        assert(captain_down(false, true, 100.0f));
        assert(captain_down(false, false, 1.0f));
        assert(captain_down(false, false, 0.0f));
        assert(captain_down(false, false, std::nanf("")));
        std::puts("PASS rebase-captain-guard-mirror");
    }
    std::puts("ALL_FIXTURE_PASS");
    return 0;
}