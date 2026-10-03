#include "PikiMgr.h"
#if defined(PIKI_PC_PORT)
#include "settings/pc_settings.h"
#include "pc_vs.h"
#include "GoalItem.h"
#include "PikiHeadItem.h"
#include "pc_randomizer.h"
#endif
#include "AIConstant.h"
#include "DebugLog.h"
#include "GameStat.h"
#include "ItemMgr.h"
#include "MemStat.h"
#include "Navi.h"
#include "PikiAI.h"
#include "gameflow.h"
#include "sysNew.h"
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
#include "Piki.h"
#include "pc_p2_bulbmin.h"
#include "pc_p2_cave_campaign_party_engine.h"
#include "pc_p2_captain.h"
#include "pc_p2_captor_forget.h"
#include "pc_p2_original_piki_origin.h"
#endif

PikiMgr* pikiMgr;
bool PikiMgr::containerDebug;
bool PikiMgr::meBirthMode;
bool PikiMgr::meNukiMode;
bool PikiMgr::containerExitMode;

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F0
 */
DEFINE_PRINT("pikiMgr");

/**
 * @todo: Documentation
 */
Creature* PikiMgr::birth()
{
    return birthWithFieldLimit(AICONST.mMaxPikisOnField(), meBirthMode);
}
#if defined(PIKI_PC_PORT)
Creature* PikiMgr::birthOriginalP2()
{
    // Refuse a nested ordinary sprout/onion transaction. Never adjust its mode
    // or the global AP/AICONST field limit on behalf of the source factory.
    if (meBirthMode || containerExitMode) return nullptr;
    return birthWithFieldLimit(100, false);
}
Creature* PikiMgr::birthOriginalP2Container()
{
    if (!pc_randomizer_original_session() || !containerExitMode || meBirthMode
        || !itemMgr || itemMgr->getContainerExitCount() <= 0) return nullptr;
    return birthWithFieldLimit(100, false);
}
Creature* PikiMgr::birthOriginalP2Sprout()
{
    if (!pc_randomizer_original_session() || !meBirthMode || containerExitMode) return nullptr;
    return birthWithFieldLimit(100, true);
}
#endif
Creature* PikiMgr::birthWithFieldLimit(int fieldLimit, bool allowSproutExtra)
{
	int totalPikis = GameStat::mapPikis;
	if (itemMgr) {
		totalPikis += itemMgr->getContainerExitCount();
	}

	if (containerExitMode) {
		totalPikis--;
	}

	if (allowSproutExtra) {
		if (totalPikis >= fieldLimit + 1) {
			return nullptr;
		}
	} else if (totalPikis >= fieldLimit) {
		return nullptr;
	}

	Creature* born = MonoObjectMgr::birth();
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	// Lane-11 Bulbmin: a recycled slot must not inherit the previous
	// occupant's dependent id/leader. Lane 12 (#130): the same slot must not
	// inherit a stale captain-capture actor id. Both inert unless opted in.
	if (born) {
        pc_p2_cave_campaign_party_forget(static_cast<Piki*>(born));
		pc_p2_bulbmin_forget(static_cast<Piki*>(born));
		pc_p2_captain_forget_piki(static_cast<Piki*>(born));
		pc_p2_captor_forget_piki(static_cast<Piki*>(born)); // #886 captor mouths
		pc_p2_original_piki_origin_forget(static_cast<Piki*>(born));
	}
#endif
	return born;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00001C
 */
CPlate* PikiMgr::getFormationPikis()
{
	if (mNavi) {
		return mNavi->mPlateMgr;
	}

	return nullptr;
}

/**
 * @todo: Documentation
 */
PikiMgr::PikiMgr(Navi* navi)
{
	mNavi      = navi;
	mPikiParms = new PikiProp();

	mLeafModel[0] = gameflow.loadShape("pikis/happas/leaf.mod", true);
	mLeafModel[1] = gameflow.loadShape("pikis/happas/bud.mod", true);
	mLeafModel[2] = gameflow.loadShape("pikis/happas/flower.mod", true);

	PRINT("loading pikiMgr.bin ...\n");
	load("parms/", "pikiMgr.bin", 1);
	PRINT("done\n");

	memStat->start("piki mtable");
	mMotionTable = PaniPikiAnimator::createMotionTable();
	memStat->end("piki mtable");

	_58          = 0;
	_54          = 0;
	_5C          = 0;
	mUpdateFlag  = 0x1 | 0x2 | 0x4;
	mRefreshFlag = 0x1 | 0x2 | 0x4;
}

/**
 * @todo: Documentation
 */
void PikiMgr::init()
{
	AiTable::init();
	mDeadPikis           = 0;
	PikiMgr::meNukiMode  = false;
	PikiMgr::meBirthMode = false;
}

/**
 * @todo: Documentation
 */
Creature* PikiMgr::createObject()
{
	memStat->start("pikiNew");
	ViewPiki* piki = new ViewPiki(mPikiParms);
	piki->init(mPikiShape, mMapMgr, mNavi);
	memStat->end("pikiNew");
	return piki;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000054 (Matching by size)
 */
bool PikiMgr::lostAllPikis()
{
	if (_54 == 0 && _5C > 0 && pikiInfMgr.getTotal() == 0)
		return true;
	return false;
}

/**
 * @todo: Documentation
 */
void PikiMgr::update()
{
	MonoObjectMgr::update();
}

/**
 * @todo: Documentation
 */
void PikiMgr::refresh(Graphics& graphics)
{
	MonoObjectMgr::refresh(graphics);
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000114
 */
void PikiMgr::refresh2d(Graphics& gfx)
{
	Iterator iter(this);
	CI_LOOP(iter)
	{
		ViewPiki* piki = static_cast<ViewPiki*>(*iter);
		piki->refresh2d(gfx, 0);
	}
}

/**
 * @todo: Documentation
 */
void PikiMgr::read(RandomAccessStream& input)
{
	mPikiParms->read(input);
}

#if 0
void PikiMgr::write(RandomAccessStream& output)
{
	PRINT("writing pikiProp\n");
	mPikiParms->write(output);
	PRINT("done\n");
}
#endif

/**
 * @todo: Documentation
 */
void PikiMgr::dumpAll()
{
	Iterator iter(this);
	int pikiNum = 0;
	CI_LOOP(iter)
	{
		Creature* piki        = *iter;
		Matrix4f transformMtx = piki->mWorldMtx;
		PRINT("[%x] piki %d --------------------------\n", piki, pikiNum);
		for (int i = 0; i < 4; i++) {
			PRINT("   ( %.1f %.1f %.1f %.1f )\n", transformMtx.mMtx[i][0], transformMtx.mMtx[i][1], transformMtx.mMtx[i][2],
			      transformMtx.mMtx[i][3]);
		}
		piki->dump();
		pikiNum++;
	}
}

#if defined(PIKI_PC_PORT)
int pcVsFieldPikis(int player)
{
	int count = 0;
	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* piki = static_cast<Piki*>(*it);
		if (piki->isAlive() && piki->mPlayerId == player) count++;
	}
	Iterator heads(itemMgr->getPikiHeadMgr());
	CI_LOOP(heads)
	{
		Creature* c = *heads;
		if (c->mObjType == OBJTYPE_Pikihead && static_cast<PikiHeadItem*>(c)->mPcOwner == player) count++;
	}
	for (int color = PikiMinColor; color < PikiColorCount; color++) {
		GoalItem* goal = itemMgr->pcGetContainer(color, player);
		if (goal) count += goal->mPikisToExit;
	}
	return count;
}

int pcVsFieldLimit() { return pc_vs_rules().fieldLimit; }
#endif
