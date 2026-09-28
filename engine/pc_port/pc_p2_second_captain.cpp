#include "pc_p2_second_captain.h"

#include "NaviMgr.h"

#include <cstdio>
#include <cstdlib>

// Lane 12 opt-in second-captain creation (#130). See the header for the
// request-gated live-spawn path.

namespace pc_p2_captain {

bool second_captain_requested()
{
    const char* env = std::getenv("PIKMIN_P2_SECOND_CAPTAIN");
    if (!env || env[0] == '\0') return false;
    if (env[0] == '0' && env[1] == '\0') return false;
    return true;
}

// Lane 12 (#130): the live spawn gate now defaults ON. The second captain
// renders (Navi::refresh no longer defers mNaviID != 0 and shares slot 0's
// PikiShapeObject) and its Kontroller poll is skipped when inactive, so a
// requested second captain is no longer invisible/input-mirroring. Default
// single-captain play still never spawns one: navi_capacity() only reaches 2
// when second_captain_requested() (PIKMIN_P2_SECOND_CAPTAIN) is set.
bool second_captain_live_allowed()
{
    return true;
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
