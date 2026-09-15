#pragma once

// Lane 12 opt-in second-captain creation path (#130).
//
// The port is a single-captain Pikmin-1 engine: one live Navi, one camera, one
// controller, single-captain follow/whistle/knockout and a global
// GAMEEND_NaviDown. The second captain now renders: it shares slot 0's
// PikiShapeObject (see NaviMgr::ensureSecondNaviShapeObject) and its Kontroller
// poll is skipped while inactive. The remaining P2 parity work (full follow-AI,
// split camera, control routing, survivor-gated game over) is still tracked in
// docs/PIKMIN2_CAPTAIN_SQUAD_CONTRACT.md.
//
//   * second_captain_requested() reads PIKMIN_P2_SECOND_CAPTAIN (default off).
//   * second_captain_live_allowed() now defaults true; the live spawn is open
//     and gated by second_captain_requested().
//   * navi_capacity() is the count to pass to NaviMgr::create(): 1 normally,
//     2 only when requested (and allowed).
//   * prepare_second_captain_assets() and birth_second_captain() are the two
//     halves of the spawn; they refuse only if the request/gate or assets fail.
//
// Nothing here runs unless the environment variable is set, so default
// single-captain play is unchanged.

class NaviMgr;
class Navi;

namespace pc_p2_captain {

// True when PIKMIN_P2_SECOND_CAPTAIN is set to a non-empty value (not "0").
bool second_captain_requested();

// Whether this build may actually birth a live second Navi. Defaults true now
// that the second captain renders and its input is skipped when inactive;
// default play still never spawns one (request-gated by
// second_captain_requested()).
bool second_captain_live_allowed();

// Object-manager capacity for NaviMgr::create(): 1, or 2 when the live gate is
// open. This is the single value the scene initialiser consults.
int navi_capacity();

// Prepare the second captain's shape object (mNaviShapeObject[1]) before
// NaviMgr::create(2) constructs the second Navi (Navi::Navi indexes
// mNaviShapeObject[mNaviID]). Idempotent; returns false when slot 0's shape is
// not prepared.
bool prepare_second_captain_assets(NaviMgr* mgr);

// Birth the second Navi after the first. Only meaningful after
// create(navi_capacity()) with assets prepared; refuses if the request/gate or
// the shape object is unavailable.
Navi* birth_second_captain(NaviMgr* mgr);

} // namespace pc_p2_captain
