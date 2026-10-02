#pragma once

// Netplay co-op issue #1033: changing which captain owns a Pikmin that is
// still in a squad action.
//
// ActCrowd::init saves the plate it joined (mPlateMgr), and cleanup releases
// the slot on that plate. Piki::mNavi is read at several other places during
// the action, so it has to name the same captain for as long as the action is
// live. Every ownership write therefore runs in this order, the order the
// gap-fix K co-op test events and pc_p2_captain.cpp live_prepare_capture use:
//
//   1. abandon the squad action while mNavi still names the plate owner,
//   2. write mNavi,
//   3. changeMode / transit (which start the new action on the new plate).
//
// With a single captain (or when the Pikmin is not in a squad action) this is
// a no-op, so single-player behaviour is unchanged.

#include "Navi.h"
#include "Piki.h"
#include "PikiAI.h"

namespace pc_crowd_handover {

// Call before `piki->mNavi = to`. Abandons a live squad action when the
// captain is about to change; does nothing otherwise.
inline void abandonSquadBeforeHandover(Piki* piki, const Navi* to)
{
	if (!piki || !piki->mActiveAction || piki->mNavi == to) return;
	if (piki->mActiveAction->mCurrActionIdx != PikiAction::Crowd) return;
	piki->mActiveAction->abandon(nullptr);
}

} // namespace pc_crowd_handover
