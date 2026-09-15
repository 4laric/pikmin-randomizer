#include "pc_p2_second_captain.h"

#include "NaviMgr.h"

#include <cstdio>
#include <cstdlib>

// Lane 12 opt-in second-captain creation (#130). See the header for why the
// live spawn is gated shut on this port.

namespace pc_p2_captain {

bool second_captain_requested()
{
    const char* env = std::getenv("PIKMIN_P2_SECOND_CAPTAIN");
    if (!env || env[0] == '\0') return false;
    if (env[0] == '0' && env[1] == '\0') return false;
    return true;
}

// Lane 12 (#130): the live spawn gate is OPEN only for a fixture/test that
// explicitly requests it. Normal play stays single-captain until the second
// captain's model/plate/cursor rendering (Navi::refresh) and per-captain
// controller routing are finished, so a live second Navi (whose collision is
// active but whose model is skipped) is never born in a normal run.
bool second_captain_live_requested()
{
    const char* env = std::getenv("PIKMIN_P2_SECOND_CAPTAIN_LIVE");
    if (!env || env[0] == '\0') return false;
    if (env[0] == '0' && env[1] == '\0') return false;
    return true;
}

bool second_captain_live_allowed()
{
    return second_captain_live_requested();
}

int navi_capacity()
{
    return (second_captain_requested() && second_captain_live_allowed()) ? 2 : 1;
}

bool prepare_second_captain_assets(NaviMgr* mgr)
{
    if (!mgr) return false;
    if (!second_captain_live_allowed()) return false;
    return mgr->ensureSecondNaviShapeObject();
}

Navi* birth_second_captain(NaviMgr* mgr)
{
    if (!mgr || !second_captain_live_allowed()) return nullptr;
    if (!mgr->ensureSecondNaviShapeObject()) return nullptr;
    Navi* first = mgr->getNavi();
    if (!first) return nullptr;
    // NaviMgr::create(2) already constructed the second Navi object; birth()
    // simply activates the next free slot. The full live setup (init, reset,
    // shared camera, spawn placement) is finished by GameCoreSection::finalSetup
    // once the stage managers all exist (effectMgr, mapMgr, etc.), matching how
    // the first captain is initialised.
    Navi* navi = static_cast<Navi*>(mgr->birth());
    if (navi) {
        std::printf("[Pikmin Randomizer] second captain spawned at slot %d\n", navi->getNaviIndex());
        std::fflush(stdout);
    }
    return navi;
}

} // namespace pc_p2_captain
