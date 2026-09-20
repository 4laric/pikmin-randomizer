// P2 general-enemy-manager bomb-birth call site (lane
// bomb-birth-hook-callsite-native, #732; consumer #573).
//
// Problem (#726 done but never invoked): pc_p2_bomb_birth_hook_notify is
// strong-defined only inside test/fixture TUs, so no production engine
// caller exists, the manager TUs have no pikmin_pc membership, and this
// research-mirror path has no TU in the port build. This TU closes all
// three: it strong-defines the notifier IN the production build, it ports
// the two retail createEnemyMgr Bomb-family arms as the engine call site,
// and it is listed explicitly in PC_PORT_SOURCES (no GLOB covers this
// path).
//
// Retail anchors (read-only native/pikmin2-research, never reimplemented):
//   * GeneralEnemyMgr::createEnemyMgr, case EnemyID_Bomb (36):
//     `mgr = new Bomb::Mgr(limit, viewNum);`
//     (generalEnemyMgr.cpp:322-323)
//   * case EnemyID_BombOtakara (93):
//     `mgr = new BombOtakara::Mgr(limit, viewNum);`
//     (generalEnemyMgr.cpp:421-422)
//   * EnemyID values from include/Game/enemyInfo.h:95,152
//     (EnemyID_Bomb = 36, EnemyID_BombOtakara = 93)
//   * GeneralEnemyMgr::birth(int enemyID, EnemyBirthArg&) routes a retail
//     enemy ID to its manager birth (generalEnemyMgr.cpp:688-701).
//
// Port mapping: the P1 host roster has no Bomb type, so the port birth seam
// is pc_p2_bomb_engine_birth_poll(Teki*) (Section 3 of
// pc_port/pc_p2_bomb_mgr_birth.cpp, #616/#691): it births ONLY on a live
// engine-spawned actor whose generator the p2-bomb-mgr-birth.txt sidecar
// registered. This call site routes the retail Bomb-family IDs (36/93) to
// that seam and invokes the notifier on a real birth. Every other ID is
// refused fail-closed with an explicit marker; nothing is staged.
//
// Captain safety (#632): this TU touches no captain/Navi/HP state and
// performs no pause/movie action, so the guard is N/A on the engine path;
// the callsite fixture adopts scripts/p2_fixture_captain_guard.h (vendored
// truth table, hash recorded in the lane packet).
#include "pc_p2_bomb_mgr_birth.h"

#include "teki.h"

#include <cstdio>

// Free-function seam declarations (defined at namespace scope in
// pc_port/pc_p2_bomb_mgr_birth.cpp; declared here rather than edited into
// the #726 header, which stays read-only for this lane).
class Teki;
bool pc_p2_bomb_engine_birth_poll(Teki* actor);

// Retail Bomb-family IDs routed through this call site.
static const int kGeneralEnemyID_Bomb = 36;
static const int kGeneralEnemyID_BombOtakara = 93;

// Strong engine-hook notifier (#726 contract). Defined HERE, in the
// production pikmin_pc graph, so a real bomb birth fires it. Same contract
// line the engine-free fixtures emit, so the #573 consumer matches one
// marker regardless of build.
void pc_p2_bomb_birth_hook_notify(int enemyID)
{
    std::printf("P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=%d\n", enemyID);
    std::fflush(stdout);
}

// Port of the retail createEnemyMgr Bomb-family arms + birth route: accept
// only Bomb (36) / BombOtakara (93), drive the real engine birth seam on the
// LIVE actor the engine spawned, and notify on a real birth. Returns true
// only when the poll birthed and the hook fired.
bool pc_p2_general_enemy_mgr_birth(int enemyID, Teki* actor)
{
    if (enemyID != kGeneralEnemyID_Bomb && enemyID != kGeneralEnemyID_BombOtakara) {
        std::printf("P2_GENERAL_ENEMY_MGR_REFUSE enemyID=%d reason=not_bomb_family\n", enemyID);
        std::fflush(stdout);
        return false;
    }
    if (!pc_p2_bomb_engine_birth_poll(actor)) {
        return false;
    }
    // In-band engine-caller proof: this line is emitted from the production
    // call-site TU (never from a test TU) immediately before the notify.
    std::printf("P2_GENERAL_ENEMY_MGR_BIRTH_CALLSITE enemyID=%d\n", enemyID);
    std::fflush(stdout);
    pc_p2_bomb_birth_hook_notify(enemyID);
    return true;
}
