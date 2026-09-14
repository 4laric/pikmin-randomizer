#include "NaviMgr.h"
#include "DebugLog.h"
#include "Dolphin/os.h"
#include "MemStat.h"
#include "gameflow.h"
#include "pc_p2_captain.h" // lane 12 (#130) inactive-captain follow hook
#include "sysNew.h"

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F4
 */
DEFINE_PRINT("naviiMgr"); // epic typo

NaviMgr* naviMgr;

/**
 * @todo: Documentation
 */
NaviMgr::NaviMgr()
{
	memStat->start("naviparms");
	mNaviParms = new NaviProp();
	load("parms/", "naviMgr.bin", 1);
	memStat->end("naviparms");

	memStat->start("navi shape anim");

	memStat->start("navi mtable");
	mMotionTable = PaniPikiAnimator::createMotionTable();
	memStat->end("navi mtable");

	memStat->start("navi shape");
	mNaviShape = gameflow.loadShape("pikis/nv3Model.mod", true);
	memStat->end("navi shape");

	memStat->start("navi shapeobject");
	mNaviShapeObject[0] = new PikiShapeObject(mNaviShape);
	memStat->end("navi shapeobject");

	memStat->start("navi animmgr");
	mNaviShapeObject[0]->mAnimMgr = PikiShapeObject::getAnimMgr();
	memStat->end("navi animmgr");

	mNaviID = 0;
	mCaptainRoster.reset();
	memStat->end("navi shape anim");
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000004
 */
void NaviMgr::init()
{
}

/**
 * @todo: Documentation
 */
Creature* NaviMgr::createObject()
{
	Navi* navi = new Navi(mNaviParms, mNaviID);
	mNaviID++;
	return navi;
}

/**
 * @todo: Documentation
 */
void NaviMgr::update()
{
	MonoObjectMgr::update();

	// Lane 12 two-captain follow-up (#130): drive the inactive captain's follow
	// state. update_inactive_captain_follow() returns immediately unless a real
	// second Navi exists, and the guard here keeps the call out of the
	// single-captain path entirely, so default play is unchanged.
	if (mNumObjects > 1) {
		pc_p2_captain::update_inactive_captain_follow();
	}
}

/**
 * @todo: Documentation
 */
Navi* NaviMgr::getNavi()
{
	Iterator iter(this);
	iter.first();
	return static_cast<Navi*>(*iter);
}

/**
 * @todo: Documentation
 */
Navi* NaviMgr::getNavi(int idx)
{
	if (idx < 0 || idx >= mNumObjects) {
		// Given this is a bounds-check, you might think this should be be an `ERROR`.   Unfortunately,
		// leftover multiplayer code brazenly requests out-of-bounds indices, so this must be a `PRINT`.
		PRINT("err : getNavi(%d) : numNavis=%d\n", idx, mNumObjects);
		return nullptr;
	}
	return static_cast<Navi*>(mObjectList[idx]);
}

// ---------------------------------------------------------------------------
// Lane 12 second-captain primitives (#130). Additive: the object list is
// untouched and every query degrades to slot 0 when only one Navi exists, so
// the single-captain campaign behaves exactly as before.
// ---------------------------------------------------------------------------

/**
 * @brief The other live Navi, or null unless exactly two Navis exist.
 */
Navi* NaviMgr::getOtherNavi(Navi* navi)
{
	if (!navi) {
		return nullptr;
	}
	int other = P2CaptainRoster::otherIndex(navi->getNaviIndex());
	if (other < 0 || other >= mNumObjects) {
		return nullptr;
	}
	return getNavi(other);
}

/**
 * @brief The currently controlled Navi, falling back to the first alive slot.
 */
Navi* NaviMgr::getActiveNavi()
{
	int index = mCaptainRoster.active(mNumObjects);
	return index < 0 ? nullptr : getNavi(index);
}

/**
 * @brief First Navi that is not down, or null when all are down.
 */
Navi* NaviMgr::getAliveOrima()
{
	int index = mCaptainRoster.firstAlive(mNumObjects);
	return index < 0 ? nullptr : getNavi(index);
}

/**
 * @brief First down Navi, or null when none are down.
 */
Navi* NaviMgr::getDeadOrima()
{
	int index = mCaptainRoster.firstDead(mNumObjects);
	return index < 0 ? nullptr : getNavi(index);
}

/**
 * @brief Mark `navi` as the controlled captain (source getActiveNavi switch).
 */
void NaviMgr::setActiveNavi(Navi* navi)
{
	if (navi) {
		mCaptainRoster.setActiveIndex(navi->getNaviIndex());
	}
}

/**
 * @brief Source NaviMgr::informOrimaDead: flag the captain down and, when it
 * was active, hand control to the first surviving captain.
 */
void NaviMgr::informOrimaDead(Navi* navi)
{
	if (!navi) {
		return;
	}
	int index = navi->getNaviIndex();
	mCaptainRoster.markDead(index);
	if (mCaptainRoster.activeIndex() == index) {
		int survivor = mCaptainRoster.firstAlive(mNumObjects);
		if (survivor >= 0) {
			mCaptainRoster.setActiveIndex(survivor);
		}
	}
}

/**
 * @brief Whether `navi` is flagged down (source mNaviDeadFlags).
 */
bool NaviMgr::isNaviDead(Navi* navi)
{
	return navi && mCaptainRoster.isDead(navi->getNaviIndex());
}

/**
 * @brief Whether a second Navi is currently live.
 */
bool NaviMgr::hasSecondNavi() const
{
	return mNumObjects > 1;
}

/**
 * @brief Number of live Navis (0 or 1 on the current port).
 */
int NaviMgr::getNaviCount() const
{
	return mNumObjects;
}

/**
 * @brief Clear per-scene active/dead selection (scene reload / teardown).
 */
void NaviMgr::resetCaptainRoster()
{
	mCaptainRoster.reset();
}

/**
 * @brief Build mNaviShapeObject[1] from a fresh, uncached captain model so a
 * second Navi can index it without clobbering [0]'s animator overrides.
 *
 * Additive: does not create, activate or update any Navi. On the default
 * single-captain port this is never called. A second Navi also needs
 * follow-AI, split camera, control routing and survivor-gated game over before
 * it can be spawned safely, so the live opt-in path stays closed for now.
 */
bool NaviMgr::ensureSecondNaviShapeObject()
{
	if (mNaviShapeObject[1]) {
		return true;
	}
	Shape* shape = gameflow.loadShape("pikis/nv3Model.mod", false);
	if (!shape) {
		return false;
	}
	PikiShapeObject* shapeObject = new PikiShapeObject(shape);
	if (!shapeObject) {
		return false;
	}
	shapeObject->mAnimMgr = PikiShapeObject::getAnimMgr();
	mNaviShapeObject[1]   = shapeObject;
	return true;
}

/**
 * @todo: Documentation
 */
void NaviMgr::refresh2d(Graphics& gfx)
{
	Iterator iter(this);
	CI_LOOP(iter)
	{
		(*iter)->refresh2d(gfx);
	}
}

/**
 * @todo: Documentation
 */
void NaviMgr::renderCircle(Graphics& gfx)
{
	Iterator iter(this);
	CI_LOOP(iter)
	{
		static_cast<Navi*>(*iter)->renderCircle(gfx);
	}
}

/**
 * @todo: Documentation
 */
void NaviMgr::drawShadow(Graphics& gfx)
{
	Iterator iter(this);
	CI_LOOP(iter)
	{
		(*iter)->drawShadow(gfx);
	}
}

/**
 * @todo: Documentation
 */
void NaviMgr::read(RandomAccessStream& input)
{
	mNaviParms->read(input);
}

#if 0
void NaviMgr::write(RandomAccessStream& output)
{
	PRINT("writing naviProp\n");
	mNaviParms->write(output);
	PRINT("done\n");
}
#endif
