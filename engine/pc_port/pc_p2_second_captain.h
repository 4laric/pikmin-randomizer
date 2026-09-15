#pragma once

// Lane 12 strictly opt-in second-captain creation path (#130).
//
// The port is a single-captain Pikmin-1 engine: one live Navi, one camera, one
// controller, single-captain follow/whistle/knockout and a global
// GAMEEND_NaviDown. Creating a second Navi without porting all of that would
// add an uncontrollable, uncameraed actor that the game-over and squad paths do
// not understand. So this slice ships the *hook* and the additive asset
// preparation but keeps the live spawn closed:
//
//   * second_captain_requested() reads PIKMIN_P2_SECOND_CAPTAIN (default off).
//   * second_captain_live_allowed() is deliberately false until follow-AI,
//     split camera, control routing and survivor-gated game over exist. See
//     docs/PIKMIN2_CAPTAIN_SQUAD_CONTRACT.md for the file:line plan.
//   * navi_capacity() is the count to pass to NaviMgr::create(): 1 normally,
//     2 only when requested AND allowed.
//   * prepare_second_captain_assets() and birth_second_captain() are the two
//     halves of the spawn and refuse unless the gate is open.
//
// Nothing here runs unless a caller invokes it, and the game-core call site is
// inert while the gate is closed, so default single-captain play is unchanged.

class NaviMgr;
class Navi;

namespace pc_p2_captain {

// True when PIKMIN_P2_SECOND_CAPTAIN is set to a non-empty value (not "0").
bool second_captain_requested();

// True only when a fixture/test explicitly requests the live spawn via
// PIKMIN_P2_SECOND_CAPTAIN_LIVE. Deliberately closes the gate for normal play
// until the second captain's rendering (Navi::refresh) and per-captain
// controller routing are finished.
bool second_captain_live_requested();

// Whether this build may actually birth a live second Navi. Defaults false;
// a fixture flips it on via second_captain_live_requested().
bool second_captain_live_allowed();

// Object-manager capacity for NaviMgr::create(): 1, or 2 when the live gate is
// open. This is the single value the scene initialiser consults.
int navi_capacity();

// Prepare mNaviShapeObject[1] before NaviMgr::create(2) constructs the second
// Navi (Navi::Navi indexes mNaviShapeObject[mNaviID]). Idempotent and inert on
// its own; returns false when the asset is unavailable.
bool prepare_second_captain_assets(NaviMgr* mgr);

// Birth the second Navi after the first. Only meaningful after
// create(navi_capacity()) with assets prepared; refuses when the gate is shut.
Navi* birth_second_captain(NaviMgr* mgr);

} // namespace pc_p2_captain
