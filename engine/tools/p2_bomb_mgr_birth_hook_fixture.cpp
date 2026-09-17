#undef NDEBUG
// Guarded fixture proving the engine Bomb birth hook plus #616 provider
// membership and the #577 source-93 payload binding (issue #677).
//
// Build (no engine, no lease):
//   g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port -DP2_BOMB_MGR_BIRTH_NO_HOST
//       tools/p2_bomb_mgr_birth_hook_fixture.cpp -o p2_bomb_mgr_birth_hook_fixture
// Unity-includes the engine-free manager core + #577 payload TU (neither is in
// the main build object list for this TU, so no duplicate symbols arise).
// Captain safety (#632): this proof is engine-free (no captain, no Navi, no
// HP); the guard predicate below mirrors scripts/p2_fixture_captain_guard.h
// (orimaDead/NaviDead/HP<=1/nonfinite -> BLOCKED) and is asserted as a pure
// check. Any future runtime consumer must adopt that header before launch;
// its hash is recorded in the lane packet, not claimed as a runtime run.
// P2_BOMB_MGR_BIRTH_NO_HOST comes from the build command line.
#include "pc_p2_bomb_mgr_birth.cpp"
#include "pc_p2_bomb_payload_actor.cpp"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>

// ---- Strong engine-hook notifier (the hook generalEnemyMgr.cpp calls) ----
static std::vector<int> g_hook_notifications;

void pc_p2_bomb_birth_hook_notify(int enemyID)
{
    g_hook_notifications.push_back(enemyID);
    std::printf("P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=%d\n", enemyID);
    std::fflush(stdout);
}

// Source IDs routed through the hook (Bomb 36, BombOtakara family).
static const int kEnemyID_Bomb = 36;
static const int kEnemyID_BombOtakara = 93;

// Mirrors the two hooked createEnemyMgr arms: notify only for Bomb-family IDs.
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
        engine_create_arm(kEnemyID_Bomb);
        engine_create_arm(kEnemyID_BombOtakara);
        engine_create_arm(10);
        engine_create_arm(0);
        assert(g_hook_notifications.size() == 2);
        assert(g_hook_notifications[0] == kEnemyID_Bomb);
        assert(g_hook_notifications[1] == kEnemyID_BombOtakara);
        std::puts("PASS hook-selective");
    }
    // 2. Provider membership + birth + #577 payload handoff (source 93 path).
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
        std::puts("PASS birth-and-payload-handoff");
    }
    // 3. Forget/reset clear without stale handles.
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
        std::puts("PASS forget-reset-clean");
    }
    // 4. Captain-guard predicate mirror (no captain here; pure check).
    {
        assert(!captain_down(false, false, 100.0f));
        assert(captain_down(true, false, 100.0f));
        assert(captain_down(false, true, 100.0f));
        assert(captain_down(false, false, 1.0f));
        assert(captain_down(false, false, 0.0f));
        assert(captain_down(false, false, std::nanf("")));
        std::puts("PASS captain-guard-mirror");
    }
    std::puts("ALL_FIXTURE_PASS");
    return 0;
}
