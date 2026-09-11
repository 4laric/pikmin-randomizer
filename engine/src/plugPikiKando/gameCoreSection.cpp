#include "BuildingItem.h"
#include "KusaItem.h"
#include "Generator.h"
#include "WorkObject.h"
#include "GameCoreSection.h"
#include "pc_bbft.h"
#include "pc_randomizer.h"
#if defined(PIKI_PC_PORT)
#include <SDL.h>
#include <cstdlib>
#include <cstdio>
#include <cmath>
#endif
#if defined(PIKI_PC_PORT)
#include "settings/pc_settings.h"
#if defined(PIKI_PC_PORT)
#include "pc_photo_mode.h"
#include "gl/pc_gfx.h"
#endif
#endif

#include "AIConstant.h"
#include "AIPerf.h"
#include "BombItem.h"
#include "Boss.h"
#include "CodeInitializer.h"
#include "DayMgr.h"
#include "DebugLog.h"
#include "Demo.h"
#include "Dolphin/pad.h"
#include "DynParticle.h"
#include "FlowController.h"
#include "Font.h"
#include "GameStat.h"
#include "Generator.h"
#include "GlobalShape.h"
#include "GoalItem.h"
#include "Graphics.h"
#include "Interface.h"
#include "ItemMgr.h"
#include "KeyConfig.h"
#include "Kontroller.h"
#include "MemStat.h"
#include "Menu.h"
#include "MoviePlayer.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Omake.h"
#include "Pcam/Camera.h"
#include "Pcam/CameraManager.h"
#include "Pellet.h"
#include "PikiHeadItem.h"
#include "PikiInfo.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "PikiState.h"
#include "PlantMgr.h"
#include "PlayerState.h"
#include "RadarInfo.h"
#include "RumbleMgr.h"
#include "SoundMgr.h"
#include "UfoItem.h"
#include "UpdateMgr.h"
#include "UtEffect.h"
#include "WorkObject.h"
#include "bugprint.h"
#include "gameflow.h"
#include "sysNew.h"
#if defined(PIKI_PC_PORT)
#include "timing/pc_render_phase.h"
#endif
#include "teki.h"
#include "timers.h"
#include "zen/DrawAccount.h"
#include "zen/DrawContainer.h"
#include "zen/DrawGameInfo.h"
#include "zen/DrawHurryUp.h"
#include "zen/ogTutorial.h"
#include <stddef.h>

static bool lastDamage;
static bool currDamage;
static u32 damageParm;
u16 GameCoreSection::pauseFlag;
#if defined(PIKI_PC_PORT)
// What the pause gates held before photo mode took them, so leaving restores
// whatever the game was doing rather than assuming it was unpaused.
static BOOL sPhotoModeSavedPauseAll = FALSE;
static BOOL sPhotoModeSavedOverlay  = FALSE;
static f32 sPhotoModeSavedRoll      = 0.0f;
#endif
int GameCoreSection::textDemoState;
u16 GameCoreSection::textDemoTimer;
int GameCoreSection::textDemoIndex;
PcamCameraManager* cameraMgr;
zen::DrawContainer* containerWindow;
zen::DrawHurryUp* hurryupWindow;
zen::DrawAccount* accountWindow;

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F4
 */
DEFINE_PRINT("gameCoreSection")

/**
 * @todo: Documentation
 */
void GameCoreSection::startTextDemo(Creature*, int textDemoID)
{
	gameflow.mGameInterface->message(MOVIECMD_TextDemo, textDemoID);
}

/**
 * @todo: Documentation
 */
void GameCoreSection::updateTextDemo()
{
	if (gameflow.mIsUIOverlayActive) {
		return;
	}
	switch (textDemoState) {
	case 2:
	{
		textDemoTimer = 60;
		attentionCamera->finish();
		textDemoState = 3;
		break;
	}
	case 1:
	{
		textDemoTimer--;
		attentionCamera->update();
		if (textDemoTimer == 0) {
			gameflow.mGameInterface->message(MOVIECMD_TextDemo, textDemoIndex);
			textDemoState = 2;
		}
		break;
	}
	case 3:
	{
		textDemoTimer--;
		attentionCamera->update();
		if (textDemoTimer == 0) {
			textDemoState = 0;
		}
		break;
	}
	}
}

/**
 * @todo: Documentation
 */
void GameCoreSection::startMovie(u32 flags, bool useMovieBackCamera)
{
	// Uses CinePlayerFlags

	mUseMovieBackCamera    = useMovieBackCamera;
	GoalItem::demoHideFlag = GoalItem::ShowAll;
	if (flags & CinePlayerFlags::HideRedCont) {
		GoalItem::demoHideFlag = GoalItem::HideRedOnyon;
	}

	if (pelletMgr) {
		pelletMgr->setMovieFlags(PELMOVIE_Unk1 | PELMOVIE_Unk3);
	}

	PRINT("+ movie start : flags=%x\n", flags);

	if (tekiMgr) {
		tekiMgr->setVisibleTypeTable(false);
		tekiMgr->setVisibleType(TEKI_Palm, true);
	}

	pikiMgr->hideAll();
	if (flags & CinePlayerFlags::ShowFreePiki) {
		pikiMgr->setRefreshFlag(PMREF_FreePiki);
	}

	if (flags & CinePlayerFlags::UpdateFreePiki) {
		pikiMgr->setUpdateFlag(PMUPDATE_FreePiki);
	}

	if (flags & CinePlayerFlags::ShowFormPiki) {
		pikiMgr->setRefreshFlag(PMREF_FormationPiki);
	}

	if (flags & CinePlayerFlags::UpdateFormPiki) {
		pikiMgr->setUpdateFlag(PMUPDATE_FormationPiki);
	}

	if (flags & CinePlayerFlags::ShowWorkPiki) {
		pikiMgr->setRefreshFlag(PMREF_WorkPiki);
	}

	if (flags & CinePlayerFlags::UpdateWorkPiki) {
		pikiMgr->setUpdateFlag(PMUPDATE_WorkPiki);
	}

	if (pikiMgr->isUpdating(PMUPDATE_FreePiki)) {
		PRINT("+ update free piki\n");
	}
	if (pikiMgr->isUpdating(PMUPDATE_FormationPiki)) {
		PRINT("+ update formation piki\n");
	}
	if (pikiMgr->isUpdating(PMUPDATE_WorkPiki)) {
		PRINT("+ update work piki\n");
	}

	if (pikiMgr->isRefreshing(PMREF_FreePiki)) {
		PRINT("+ refresh free piki\n");
	}
	if (pikiMgr->isRefreshing(PMREF_FormationPiki)) {
		PRINT("+ refresh formation piki\n");
	}
	if (pikiMgr->isRefreshing(PMREF_WorkPiki)) {
		PRINT("+ refresh work piki\n");
	}

	if (flags & CinePlayerFlags::PikiNearUfo) {
		pikiMgr->setUpdateFlag(PMUPDATE_Unk4);
	}

	{
		Iterator it(pikiMgr);
		CI_LOOP(it)
		{
			Piki* piki = (Piki*)(*it);
			if (piki->isAlive()) {
				piki->startDemo();
			}
		}
	}

	Navi* orima = naviMgr->getNavi();
	if (orima) {
		orima->mNaviLightEfx->changeEffect(EffectMgr::EFF_Navi_Light);
		orima->mNaviLightGlowEfx->changeEffect(EffectMgr::EFF_Navi_LightGlow);
		if (orima->mDamageEfxA) {
			orima->mDamageEfxA->invisible();
		}
		if (orima->mDamageEfxB) {
			orima->mDamageEfxB->invisible();
		}
		if (orima->mDamageEfxC) {
			orima->mDamageEfxC->invisible();
		}
		if (orima->isDamaged()) {
			orima->finishDamage();
		}
		int state = orima->mStateMachine->getCurrID(orima);
		if (useMovieBackCamera) {
			PRINT("++++++++++ KILL ANTENNA\n");
			orima->mNaviLightEfx->stop();
			orima->mNaviLightGlowEfx->stop();
		}
		orima->mRippleEffect->stop();
		if (state != NAVISTATE_DemoInf && state != NAVISTATE_Starting) {
			PRINT("************ NAVI => DEMO_WAIT STATE \n");
			orima->mStateMachine->transit(orima, NAVISTATE_DemoWait);
		}
	}

	{
		Iterator it(pikiMgr);
		CI_LOOP(it)
		{
			Piki* piki = (Piki*)(*it);
			int color  = piki->mColor;
			if ((color == Blue && flags & CinePlayerFlags::HideBluePiki) || (color == Red && flags & CinePlayerFlags::HideRedPiki)
			    || (color == Yellow && flags & CinePlayerFlags::HideYellowPiki)) {
				piki->mFreeLightEffect->stop();
			}
		}
	}

	if (flags & CinePlayerFlags::ShowTekis) {
		mHideFlags |= GameHideFlags::ShowTeki;
	}
}

#if defined(VERSION_PIKIDEMO)
/**
 * @todo: Documentation
 */
void GameCoreSection::endMovie()
#else
/**
 * @todo: Documentation
 */
void GameCoreSection::endMovie(int movieIdx)
#endif
{
	GoalItem::demoHideFlag = GoalItem::ShowAll;
	if (tekiMgr) {
		tekiMgr->setVisibleTypeTable(true);
	}
	if (pelletMgr) {
		pelletMgr->setMovieFlags(PELMOVIE_Unk1 | PELMOVIE_Unk2 | PELMOVIE_Unk3);
	}
	PRINT("+ movie done\n");
	PRINT("+ reset PikiMgr update/refresh flags\n");
	pikiMgr->setUpdateFlag(PMUPDATE_FreePiki | PMUPDATE_FormationPiki | PMUPDATE_WorkPiki);
	pikiMgr->setRefreshFlag(PMREF_FreePiki | PMREF_FormationPiki | PMREF_WorkPiki);

	{
		Iterator it(pikiMgr);
		CI_LOOP(it)
		{
			Piki* piki = (Piki*)(*it);
			piki->mFreeLightEffect->restart();
			piki->finishDemo();
		}
	}

	mNavi->mNaviLightEfx->restart();
	mNavi->mNaviLightGlowEfx->restart();
	mHideFlags = 0;

	if (mNavi) {
		f32 angle;
		if (mUseMovieBackCamera) {
			angle = mNavi->mFaceDirection + PI;
			PRINT("use navi back camera\n");
		} else {
			angle = cameraMgr->mCamera->mPolarDir.mAzimuth;
			PRINT("using previous camera" TERNARY_BUGFIX("\n", "\\n"));
		}
		angle = cameraMgr->mCamera->mPolarDir.mAzimuth;
#if defined(VERSION_PIKIDEMO)
#else
		if (movieIdx == DEMOID_FindRedOnyon || movieIdx == DEMOID_FindYellowOnyon || movieIdx == DEMOID_FindBlueOnyon
		    || movieIdx == DEMOID_DiscoverMainEngine) {
			Vector3f diff = gameflow.mMoviePlayer->mTargetViewpoint - gameflow.mMoviePlayer->mLookAtPos;
			diff.y        = 0.0f;
			diff.normalise();
			angle = atan2f(diff.x, diff.z);
		}
#endif
		cameraMgr->mCamera->makeCurrentPosition(angle);
		cameraMgr->update();
	}

	STACK_PAD_VAR(6);
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000034
 */
bool GameCoreSection::hideTeki()
{
	return gameflow.mMoviePlayer->mIsActive && !(mHideFlags & GameHideFlags::ShowTeki);
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000034
 */
bool GameCoreSection::hideAllPellet()
{
	return gameflow.mMoviePlayer->mIsActive && !(mHideFlags & GameHideFlags::ShowPellets);
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000034
 */
bool GameCoreSection::hidePelletExceptSucked()
{
	return gameflow.mMoviePlayer->mIsActive && !(mHideFlags & GameHideFlags::ShowPelletsExceptSucked);
}

/**
 * @todo: Documentation
 */
void GameCoreSection::exitDayEnd()
{
	int entered = 0;
	int killed  = 0;
	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* piki = (Piki*)*it;
		if (piki->isAlive()) {
			GoalItem* item = itemMgr->getContainer(piki->mColor);
			if (item) {
				item->enterGoal(piki);
				entered++;
			} else {
				piki->kill(false);
				killed++;
			}
		}
	}
	PRINT("((EXITDAYEND)) ***** FORCE ENTERPIKIS %d / killed %d \n", entered, killed);
}

/**
 * @todo: Documentation
 */
void GameCoreSection::forceDayEnd()
{
	PRINT("*********** FORCE DAY END =====================================\n");
	seSystem->resetSystem();
	playerState->setDayEnd(true);
	PRINT("------------ forceDayEnd --------------\n");
	mIsTimePastQuarter3 = true;
	mIsTimePastNoon     = true;
	mIsTimePastQuarter1 = true;
	mDoneSundownWarn    = true;
	clearDeadlyPikmins();
	enterFreePikmins();

	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* piki = (Piki*)*it;
		piki->forceFinishLook();
	}
}

/**
 * @todo: Documentation
 */
void GameCoreSection::clearDeadlyPikmins()
{
	int killed = 0;
	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* piki = (Piki*)*it;
		int state  = piki->getState();
		bool kill  = false;
		switch (state) {
		case PIKISTATE_Dying:
		case PIKISTATE_Swallowed:
		case PIKISTATE_WaterHanged:
		case PIKISTATE_Kinoko:
		case PIKISTATE_Drown:
		{
			kill = true;
			break;
		}
		}
		if (piki->isKinoko()) {
			kill = true;
		}

		if (kill || !piki->isAlive()) {
			piki->kill(false);
			killed++;
		}
	}

	BUGPRINT("clearDeadlyPikmins %d", killed);
}

/**
 * @todo: Documentation
 */
void GameCoreSection::enterFreePikmins()
{
	if (playerState->isEnding()) {
		return;
	}

	int goalSafe = 0;
	int ufoSafe  = 0;

	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* piki = (Piki*)*it;
		u32 mode   = piki->mMode;
		if (!piki->isKinoko() && !piki->isHolding() && piki->isAlive() && (int)mode != PikiMode::FormationMode && (1 < mode - 11)) {
			int state = piki->getState();
			if (state != PIKISTATE_Dead && state != PIKISTATE_Drown && state == PIKISTATE_Normal) {
				for (int i = 0; i < 3; i++) {
					Navi* navi     = naviMgr->getNavi();
					GoalItem* goal = itemMgr->getContainer(i);
					if (goal
					    && qdist2(goal->mSRT.t.x, goal->mSRT.t.z, piki->mSRT.t.x, piki->mSRT.t.z)
					           <= pikiMgr->mPikiParms->mPikiParms.mSunsetSafetyRange()) {
						if (state == PIKISTATE_LookAt || state == PIKISTATE_Nukare || state == PIKISTATE_Absorb) {
							piki->mFSM->transit(piki, PIKISTATE_Normal);
						}
						piki->mFSM->transit(piki, PIKISTATE_Normal);
						navi->mGoalItem = itemMgr->getContainer(piki->mColor);
						piki->changeMode(PikiMode::EnterMode, nullptr);
						goalSafe++;
						break;
					}

					UfoItem* ufo = itemMgr->getUfo();
					if (ufo) {
						Vector3f pos = ufo->getGoalPos();
						if (qdist2(pos.x, pos.z, piki->mSRT.t.x, piki->mSRT.t.z) <= pikiMgr->mPikiParms->mPikiParms.mSunsetSafetyRange()) {
							if (state == PIKISTATE_LookAt || state == PIKISTATE_Nukare || state == PIKISTATE_Absorb) {
								piki->mFSM->transit(piki, PIKISTATE_Normal);
							}
							piki->mFSM->transit(piki, PIKISTATE_Normal);
							navi->mGoalItem = itemMgr->getContainer(piki->mColor);
							piki->changeMode(PikiMode::EnterMode, nullptr);
							ufoSafe++;
							break;
						}
					}
				}
			}
		}
	}

	PRINT("enterFreePikmins %d + %d = %d" MISSING_NEWLINE, goalSafe, ufoSafe, goalSafe + ufoSafe);
}

/**
 * @todo: Documentation
 */
void GameCoreSection::cleanupDayEnd()
{
	finishPause();
	clearDeadlyPikmins();
	enterFreePikmins();
	PRINT("________ CLEANUP DAYEND ____________________________\n");
	rumbleMgr->stop();

	switch (flowCont.mCurrentStage->mStageID) {
	case STAGE_Practice:
	{
		playerState->mResultFlags.setOn(zen::RESFLAG_EndFirstDay);
		playerState->mResultFlags.setOn(zen::RESFLAG_UnusedControls2);
		break;
	}
	case STAGE_Forest:
	{
		playerState->mResultFlags.setOn(zen::RESFLAG_FirstVisitForest);
		break;
	}
	case STAGE_Yakushima:
	{
		playerState->mResultFlags.setOn(zen::RESFLAG_FirstVisitYakushima);
		break;
	}
	case STAGE_Last:
	{
		break;
	}
	}
	if (playerState->getCurrDay() + 1 == playerState->getTotalDays() - 1) {
		playerState->mResultFlags.setOn(zen::RESFLAG_FinalDay);
	}
	if (playerState->getCurrParts() >= 11 && playerState->getCurrDay() >= 9) {
		playerState->mResultFlags.setOn(zen::RESFLAG_Collect10Parts);
	}
	int day = playerState->getCurrDay();
	playerState->setDayCollectCount(day, playerState->getCurrParts());
	playerState->setDayPowerupCount(day, playerState->getNextPowerupNumber());

	int goalColor; // Gets reused way later in the function
	for (goalColor = 0; goalColor < PikiColorCount; goalColor++) {
		GoalItem* goal = itemMgr->getContainer(goalColor);
		if (goal) {
			goal->setSpotActive(false);
		}
	}
	playerState->setDayEnd(true);

	if (naviMgr->getNavi()) {
		PRINT("********** KILL RIPPLE EFFECT****\n");
		Navi* navi = naviMgr->getNavi();
		navi->mRippleEffect->kill();
	}
	seSystem->resetSystem();

	if (!playerState->isChallengeMode() && !playerState->isGameCourse()) {
		PRINT("** SKIP CLEANUPDAYEND\n");
		return;
	}

	PRINT("STEP (1) : Save Generators\n");
	if (!playerState->isChallengeMode()) {
		generatorCache->beginSave(flowCont.mCurrentStage->mStageIndex);
		int gens      = 0;
		int creatures = 0;
		int ufoParts  = 0;

		Generator* gen;
		FOREACH_NODE_REUSE(Generator, generatorList->mGenListHead->mChild, gen)
		{
			if (gen->mCarryOverFlags & GENCARRY_SaveGenerator) {
				generatorCache->saveGenerator(gen);
				gens++;
			}
		}
		FOREACH_NODE_REUSE(Generator, generatorList->mGenListHead->mChild, gen)
		{
			if ((gen->mCarryOverFlags & GENCARRY_SaveGenerator) && (gen->mCarryOverFlags & GENCARRY_SaveCreature)) {
				generatorCache->saveGeneratorCreature(gen);
				creatures++;
			}
		}

		Iterator it(pelletMgr);
		CI_LOOP(it)
		{
			Pellet* pelt = (Pellet*)*it;
			if (pelt->mConfig->mPelletType() == PELTYPE_UfoPart) {
				generatorCache->saveUfoParts(pelt);
				ufoParts++;
			}
		}

		PRINT("****************** SAVED %d GENERATORS *****************\n", gens);
		PRINT("****************** SAVED %d CREATURES *****************\n", creatures);
		PRINT("****************** SAVED %d UFOPARTS *****************\n", ufoParts);
		generatorCache->endSave();
		generatorCache->dump();
	}

	PRINT("STEP (2) : remove objects (teki/boss/pellet/free pikis)\n");
	int killed = 0;
	if (!playerState->isChallengeMode() && !playerState->isTutorial() && !playerState->isEnding()) {
		Iterator it(pikiMgr);
		CI_LOOP(it)
		{
			Piki* piki = (Piki*)*it;
			int mode   = piki->mMode;

			if (piki->isKinoko()) {
				GameStat::victimPikis.inc(piki->mColor);
#if defined(VERSION_PIKIDEMO) || defined(VERSION_GPIJ01_01) || defined(WIN32)
#else
				GameStat::deadPikis.inc(piki->mColor);
#endif
				piki->setEraseKill();
				piki->kill(false);
				it.dec();
				killed++;
				continue;
			}

			if (piki->isHolding()) {
				InteractRelease act(piki, 1.0f);
				Creature* obj = piki->getHoldCreature();
				obj->stimulate(act);
				BombItem* bomb = (BombItem*)obj;
				C_SAI(bomb)->start(bomb, BombAI::BOMB_Mizu);
				PRINT("BOMB KILL!\n");
			}

			int state = piki->getState();
			if (mode == PikiMode::FormationMode) {
				if (state == PIKISTATE_Drown || state == PIKISTATE_Fired || state == PIKISTATE_Dead || state == PIKISTATE_Swallowed
				    || state == PIKISTATE_Bubble || state == PIKISTATE_Dying || state == PIKISTATE_Flick || !piki->isAlive()) {
					// do nothing
				} else {
					continue;
				}
			}
			if (mode == PikiMode::ExitMode || mode == PikiMode::EnterMode) {
				continue;
			} else if (state == PIKISTATE_LookAt) {
				continue;
			}

			bool isNearOnyonShip = false;
			if (piki->mMode == PikiMode::FreeMode) {
				for (int i = 0; i < PikiColorCount; i++) {
					GoalItem* goal = itemMgr->getContainer(i);
					if (goal) {
						if (qdist2(goal->mSRT.t.x, goal->mSRT.t.z, piki->mSRT.t.x, piki->mSRT.t.z)
						    <= pikiMgr->mPikiParms->mPikiParms.mSunsetSafetyRange()) {
							isNearOnyonShip = true;
							break;
						}
					}
					UfoItem* ufo = itemMgr->getUfo();
					if (ufo) {
						Vector3f pos = ufo->getGoalPos();
						if (qdist2(pos.x, pos.z, piki->mSRT.t.x, piki->mSRT.t.z) <= pikiMgr->mPikiParms->mPikiParms.mSunsetSafetyRange()) {
							isNearOnyonShip = true;
							break;
						}
					}
				}
			}

			if (!isNearOnyonShip) {
				GameStat::victimPikis.inc(piki->mColor);
#if defined(VERSION_PIKIDEMO) || defined(VERSION_GPIJ01_01) || defined(WIN32)
#else
				GameStat::deadPikis.inc(piki->mColor);
#endif
				piki->setEraseKill();
				piki->kill(false);
				it.dec();
				killed++;
			}
		}
		if (GameStat::victimPikis > 0) {
			playerState->mResultFlags.setOn(zen::RESFLAG_PikminLeftBehind);
		}
	}
	PRINT("++++++ %d PIKIS KILLED\n", killed);
	tekiMgr->killAll();
	bossMgr->killAll();
	pelletMgr->killAll();

	Iterator it(itemMgr);
	CI_LOOP(it)
	{
		Creature* obj = *it;
		if (obj->mObjType != OBJTYPE_Pikihead && obj->mObjType != OBJTYPE_Goal && obj->mObjType != OBJTYPE_Fulcrum
		    && obj->mObjType != OBJTYPE_Rope) {
			obj->kill(false);
		}
	}

	Iterator ph_it(itemMgr->getPikiHeadMgr());
	CI_LOOP(ph_it)
	{
		PikiHeadItem* obj = (PikiHeadItem*)*ph_it;
		obj->setPermanentEffects(false);
	}

	effectMgr->killAll();

	for (goalColor = 0; goalColor < PikiColorCount; goalColor++) {
		GoalItem* goal = itemMgr->getContainer(goalColor);
		if (goal && playerState->hasContainer(goal->mOnionColour)) {
			goal->mSpotModelEff = effectMgr->create((EffectMgr::modelTypeTable)goalColor, goal->mSRT.t, Vector3f(1.0f, 1.0f, 1.0f),
			                                        Vector3f(0.0f, 0.0f, 0.0f));
		}
	}

	UfoItem* ufo = itemMgr->getUfo();
	if (ufo) {
		ufo->mRingFx = nullptr;
		ufo->setSpotActive(true);
	}

	{
		Iterator ph_it(itemMgr->getPikiHeadMgr());
		CI_LOOP(ph_it)
		{
			PikiHeadItem* obj = (PikiHeadItem*)*ph_it;
			obj->setPermanentEffects(true);
		}
	}

	PRINT("STEP(3) : clear tekiMgr/bossMgr pointer\n");
	tekiMgr = nullptr;
	bossMgr = nullptr;
	mMapMgr->mCollShapeList->initCore("");
	if (!playerState->isChallengeMode()) {
		playerState->update();
	}
	naviMgr->getNavi()->startMovieInf();
	if (!playerState->isChallengeMode()) {
		playerState->mResultFlags.dump();
	}

	PRINT("STEP (4) : record me pikis\n");

	if (!playerState->isChallengeMode()) {
		StageInf* inf = &flowCont.mCurrentStage->mStageInf;
		Iterator ph_it(itemMgr->getPikiHeadMgr());
		CI_LOOP(ph_it)
		{
			Creature* obj = *ph_it;
			if (obj->mObjType == OBJTYPE_Pikihead) {
				PikiHeadItem* sprout = (PikiHeadItem*)obj;
				int id               = sprout->getCurrState()->getID();
				if (id != PikiHeadAI::PIKIHEAD_Flying && id != PikiHeadAI::PIKIHEAD_Unk1 && id != PikiHeadAI::PIKIHEAD_Dead
				    && id != PikiHeadAI::PIKIHEAD_Unk13) {
					BaseInf* bInf = inf->mBPikiInfMgr.getFreeInf();
					if (bInf) {
						PRINT("store PIKIHEAD !\n");
						bInf->store(sprout);
					} else {
						PRINT("no free inf for PikiHead ***\n");
					}
					PRINT(">>> @@@@ FREE = %d ACTIVE = %d\n", inf->mBPikiInfMgr.getFreeNum(), inf->mBPikiInfMgr.getActiveNum());
				}
			}
			obj->kill(false);
			ph_it.dec();
		}
		playerState->updateFinalResult();
	} else {
		PRINT("MECK IS SLEEPY\n"); // lol
	}

	playerState->mSproutedNum += GameStat::bornPikis;
	int lostBattlePikis = GameStat::deadPikis - GameStat::victimPikis;
	lostBattlePikis     = (lostBattlePikis < 0) ? 0 : lostBattlePikis;
	playerState->mLostBattlePikis += lostBattlePikis;
	playerState->mLeftBehindPikis += GameStat::victimPikis;
}

/**
 * @todo: Documentation
 */
void GameCoreSection::prepareBadEnd()
{
	Iterator ph_it(itemMgr->getPikiHeadMgr());
	CI_LOOP(ph_it)
	{
		PikiHeadItem* obj = (PikiHeadItem*)*ph_it;
		obj->setPermanentEffects(false);
		obj->kill(false);
		ph_it.dec();
	}
}

/**
 * @todo: Documentation
 */
void GameCoreSection::exitStage()
{
	demoEventMgr = nullptr;
	naviMgr      = nullptr;
	playerState->exitCourse();
	seSystem->exitCourse();
	PRINT(" clean up singleton pattern\n");
	GenObjectFactory::factory = nullptr;
	GenTypeFactory::factory   = nullptr;
	GenAreaFactory::factory   = nullptr;
	AIConstant::_instance     = nullptr;
	KeyConfig::_instance      = nullptr;
	GlobalShape::exitCourse();
	PikiShapeObject::exitCourse();
	seMgr->setPikiNum(0);
	PADControlMotor(0, 0);
	effectMgr->exit();
	memStat->reset();
	flowCont.mIsVersusMode = FALSE;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000024
 */
ASM void ps_vec3f_add(Vector3f&, Vector3f&) {
#ifdef __MWERKS__ // clang-format off
	nofralloc
	trap  // TRAP_UNIMPLEMENTED
	blr
#endif
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000024
 */
ASM void ps_vec3f_sub(Vector3f&, Vector3f&)
{
#ifdef __MWERKS__ // clang-format off
	nofralloc
	trap  // TRAP_UNIMPLEMENTED
	blr
#endif
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000020
 */
ASM void ps_vec3f_multiply(Vector3f&, f32&)
{
#ifdef __MWERKS__ // clang-format off
	nofralloc
	trap  // TRAP_UNIMPLEMENTED
	blr
#endif
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000018
 */
ASM void asmTest(f32, f32)
{
#ifdef __MWERKS__ // clang-format off
	nofralloc
	trap  // TRAP_UNIMPLEMENTED
	blr
#endif
}

/**
 * @todo: Documentation
 */
void GameCoreSection::initStage()
{
#if defined(VERSION_PIKIDEMO)
#else
	STACK_PAD_VAR(2);
#endif
	playerState->setDayEnd(false);
	if (playerState->isChallengeMode()) {
		pikiInfMgr.initGame();
	}

	lastDamage          = false;
	currDamage          = false;
	damageParm          = 0;
	mIsTimePastQuarter3 = false;
	mIsTimePastNoon     = false;
	mIsTimePastQuarter1 = false;

	if (playerState->isTutorial()) {
		mIsTimePastQuarter3 = true;
		mIsTimePastNoon     = true;
		mIsTimePastQuarter1 = true;
	}

	// hmm. not sure how to get the orphaned cmpwi x2 to spawn in the middle of
	// this switch
	switch (flowCont.mCurrentStage->mStageID) {
	case STAGE_Practice:
	{
		break;
	}
	case STAGE_Forest:
	{
		break;
	}
	case STAGE_Last:
	{
		break;
	}
	case STAGE_Cave:
	{
		playerState->mResultFlags.setOn(zen::RESFLAG_FirstVisitCave);
		break;
	}
	case STAGE_Yakushima:
	{
		playerState->mResultFlags.setOn(zen::RESFLAG_FirstVisitYakushima);
		break;
	}
	}

	if (gameflow.mWorldClock.mCurrentDay >= 10 && gameflow.mWorldClock.mCurrentDay <= 20) {
		playerState->mResultFlags.setOn(zen::RESFLAG_OlimarDaydream);
	} else if (gameflow.mWorldClock.mCurrentDay > 20) {
		playerState->mResultFlags.setSeen(zen::RESFLAG_OlimarDaydream);
	}

	playerState->initCourse();

	PRINT("--------------- GeneratorCache : preload start\n");
	memStat->start("genCache");
	const bool hasAuthoritativeStageCache = generatorCache->preload(flowCont.mCurrentStage->mStageIndex);
	memStat->end("genCache");
	PRINT("--------------- GeneratorCache : preload done\n");

	GameStat::init();

	memStat->start("initStage");
	flowCont.mIsVersusMode = FALSE;
	PRINT("initStage start\n");
	seMgr->setPikiNum(0);
	mNavi->_730 = flowCont._250;
	mNavi->mSeedCollectionCount = flowCont.mNaviSeedCount;

	memStat->start("routeMgr");
	routeMgr = new RouteMgr;
	routeMgr->construct(mMapMgr);
	if (routeMgr->getPathFinder('test') == nullptr) {
		PRINT("finder is NULL\n");
	}
	memStat->end("routeMgr");
	PRINT("done\n");

	memStat->start("piki");
	pikiMgr = new PikiMgr(mNavi);
	pikiMgr->init();
	pikiMgr->mPikiShape = mPikiShape;
	pikiMgr->mMapMgr    = mMapMgr;

	memStat->start("pikiCreate");
#if defined(PIKI_PC_PORT)
	// The object pool, and the real ceiling on how many Pikmin can exist: ask
	// for one past it and birth fails outright. 102 in the original, the field
	// limit plus a small margin, so keep that relationship to the configured
	// limit instead of the default.
	pikiMgr->create(pc_settings_get_piki_limit() + 2);
#else
	pikiMgr->create(MAX_PIKI_ON_FIELD + 2); // This has a capacity of 102 for some reason.
#endif
	memStat->end("pikiCreate");

	memStat->end("piki");

	gameflow.addGenNode("pikiMgr", pikiMgr);
	PRINT("done2\n");

	char path[PATH_MAX];
	strcpy(path, flowCont.mCurrStageFilePath);
	u8* tmp;
	for (tmp = (u8*)path; *tmp != (u32)'.'; tmp++) { }
	*++tmp = 'g';
	*++tmp = 'e';
	*++tmp = 'n';
	*++tmp = '\0';
#if defined(VERSION_PIKIDEMO)
	gsys->openFile(path, true, true); // bruh
#endif
	PRINT("---------- auto load generator file : <%s>\n", path);
	for (tmp = (u8*)path; *tmp != (u32)'.'; tmp++) { }
	*tmp++ = '/';
	*tmp++ = '\0';
	char path2[PATH_MAX];
	bool useDefault = false;
	bool useDay     = false;
	bool useInit    = false;
	bool usePlant   = false;
	sprintf(path2, "%sdefault.gen", path);
	RandomAccessStream* data = gsys->openFile(path2);
	if (data) {
		PRINT("DEFAULT GEN LOADED **********************************\n");
		generatorMgr->read(*data, false);
		data->close();
		generatorMgr->updateUseList();
		useDefault = true;
	} else {
		PRINT("*** NO GENERATOR FILE\n");
		mNavi->mSRT.t.set(0.0f, 0.0f, 0.0f);
		mNavi->mDayEndPosition = mNavi->mSRT.t;
		mNavi->mFaceDirection  = 0.0f;
		mNavi->mSRT.r.set(0.0f, 0.0f, 0.0f);
	}
	mNavi->reset();

	sprintf(path2, "%s%d.gen", path, (gameflow.mWorldClock.mCurrentDay - 1) % MAX_DAYS);
	data = gsys->openFile(path2);
	if (data) {
		PRINT("** FILE %s READING\n", path2);
		dailyGeneratorMgr->read(*data, true);
		data->close();
		dailyGeneratorMgr->updateUseList();
		useDay = true;
	} else {
		PRINT("** FILE %s NOT FOUND\n", path2);
	}

	// init.gen is a one-shot source. A validated cache proves that the stage has
	// persistent state and is authoritative even if a legacy save's separate
	// mHasInitialised flag disagrees. Mixing both sources duplicates or suppresses
	// entities, so disk is used only when no usable cache exists.
	if (!hasAuthoritativeStageCache) {
		if (flowCont.mCurrentStage->mHasInitialised != FALSE && !hasAuthoritativeStageCache) {
			PRINT("[PC Port] Stage cache unavailable; rebuilding one-shot generators from init.gen\n");
		}
		flowCont.mCurrentStage->mHasInitialised = TRUE;

		sprintf(path2, "%sinit.gen", path);
		data = gsys->openFile(path2);
		if (data) {
			PRINT("** FILE %s READING\n", path2);
			onceGeneratorMgr->read(*data, true);
			data->close();
			onceGeneratorMgr->updateUseList();
			useInit = true;
		}
	}

	sprintf(path2, "%splants.gen", path);
	data = gsys->openFile(path2);
	if (data) {
		PRINT("** FILE %s READING\n", path2);
		plantGeneratorMgr->read(*data, true);
		data->close();
		plantGeneratorMgr->updateUseList();
		usePlant = true;
	}

	GenFileInfo* gfInfo;
	int i  = 0;
	int j  = 0;
	u8 day = gameflow.mWorldClock.mCurrentDay - 1;
	for (gfInfo = (GenFileInfo*)flowCont.mCurrentStage->mGenFileList.mChild; gfInfo; gfInfo = (GenFileInfo*)gfInfo->mNext) {
		if (day >= gfInfo->mFirstSpawnDay && day <= gfInfo->mLastSpawnDay && playerState->checkLimitGenFlag(i) == 0) {
			sprintf(path2, "%s%s", path, gfInfo->mName);
			data = gsys->openFile(path2);
			if (data) {
				GeneratorMgr* gen = new GeneratorMgr;
				gen->setName(gfInfo->mName);
				limitGeneratorMgr->add(gen);
				gen->read(*data, true);
				data->close();
				playerState->setLimitGenFlag(i);
				gen->setDayLimit(gfInfo->mDayLimit + 1);
				gen->updateUseList();
				j++;
			}
		}
		i++;
	}

	generatorList->updateUseList();
	memStat->start("item");
	itemMgr->initialise();
	memStat->end("item");

	memStat->start("mapMgr");
	memStat->start("plant");
	plantMgr->initialise();
	memStat->end("plant");
	memStat->end("mapMgr");

	memStat->start("teki");
	int oldT = gsys->setHeap(SYSHEAP_Teki);
	tekiMgr->startStage();
	gsys->setHeap(oldT);
	memStat->end("teki");

	memStat->start("boss");
	int oldB = gsys->setHeap(SYSHEAP_Teki);
	bossMgr->constructBoss();
	gsys->setHeap(oldB);
	memStat->end("boss");

	if (!preloadUFO) {
		memStat->start("pellet");
		pelletMgr->initShapeInfos();
		memStat->end("pellet");
		pelletMgr->registerUfoParts();
	}

	memStat->start("mapMgr");
	memStat->start("workobj");
	workObjectMgr->loadShapes();
	memStat->end("workobj");
	memStat->end("mapMgr");

	memStat->start("bobby");
	playerState->reconcileBbftParts(); // Before generators/cache can recreate checked parts.
	if (useDefault) {
		PRINT("*** GEN1\n");
		generatorMgr->init();
	}
	generatorList->createRamGenerators();

	memStat->start("genCache");
	generatorCache->load(flowCont.mCurrentStage->mStageIndex);
	memStat->end("genCache");

	if (useDay) {
		PRINT("*** GEN2\n");
		dailyGeneratorMgr->init();
	}
	if (useInit) {
		PRINT("*** GEN3\n");
		onceGeneratorMgr->init();
	}
	if (usePlant) {
		PRINT("*** GEN4\n");
		plantGeneratorMgr->init();
	}

	FOREACH_NODE(GeneratorMgr, limitGeneratorMgr->mChild, gen)
	{
		gen->init();
	}
	memStat->end("bobby");

	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* piki = (Piki*)*it;
		piki->initColor(piki->mColor);
	}

	attentionCamera = new AttentionCamera;
	cameraMgr->startCamera(naviMgr->getNavi());
	cameraMgr->update();
	mNavi->mIsCursorVisible = TRUE;

#if defined(VERSION_PIKIDEMO)
#else
	if (!playerState->isChallengeMode())
#endif
	{
		StageInf* inf = &flowCont.mCurrentStage->mStageInf;
		PRINT("@@@@ FREE = %d ACTIVE = %d\n", inf->mBPikiInfMgr.getFreeNum(), inf->mBPikiInfMgr.getActiveNum());
		BaseInf* a = (BaseInf*)inf->mBPikiInfMgr.mActiveList.mChild;
		while (a) {
			PikiHeadItem* item = static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
			if (item) {
				a->restore(item);
				item->mSRT.t.y = mMapMgr->getMinY(item->mSRT.t.x, item->mSRT.t.z, true);
				item->init(item->mSRT.t);
				item->setColor(item->mSeedColor);
				item->startAI(0);
				C_SAI(item)->start(item, PikiHeadAI::PIKIHEAD_Wait);
				PRINT(" NEW PIKIHEAD ****\n");
				BaseInf* b = a; // why
				a          = (BaseInf*)a->mNext;
				inf->mBPikiInfMgr.delInf(b);
				PRINT("::::::: FREE = %d ACTIVE = %d\n", inf->mBPikiInfMgr.getFreeNum(), inf->mBPikiInfMgr.getActiveNum());
			} else {
				PRINT("no room for pikihead! ****\n");
				a = (BaseInf*)a->mNext;
			}
		}
	}

	PRINT("*** INIT TEKI NAKA PARTS ******\n");
	pelletMgr->initTekiNakaParts();
	PRINT("*******************************\n");
	PRINT("initStage::end\n");
	memStat->end("initStage");

	PRINT("Creature size is %d\n", sizeof(Creature));
	PRINT("Pellet size is %d\n", sizeof(Pellet));
	PRINT("DynParticle size is %d\n", sizeof(DynParticle));
	PRINT("Piki size is %d\n", sizeof(Piki));
	PRINT("Navi size is %d\n", sizeof(Navi));
	PRINT("Teki size is %d\n", sizeof(Teki));
	PRINT("CollPart size is %d\n", sizeof(CollPart));

	GameStat::containerPikis.add(Blue, pikiInfMgr.getColorTotal(Blue));
	GameStat::containerPikis.add(Red, pikiInfMgr.getColorTotal(Red));
	GameStat::containerPikis.add(Yellow, pikiInfMgr.getColorTotal(Yellow));
	GameStat::update();
	GameStat::minPikis = GameStat::allPikis;
	PRINT("*** START WITH %d PIKIS\n", GameStat::minPikis);

	RandomAccessStream* data2 = gsys->openFile("ghost/record.gst");
	if (data2) {
		data2->getPending();
		// int pend = ;
		data2->read(controllerBuffer->mBufferAddr, data2->getPending());
		data2->close();
		DCFlushRange(controllerBuffer->mBufferAddr, data2->getLength());
	}

	naviMgr->getNavi(0)->startKontroller();
	PRINT("init stage done\n");
}

/**
 * @todo: Documentation
 */
void GameCoreSection::finalSetup()
{
	PRINT("======================= FINAL SETUP ==============================\n");
	BUGPRINT("final setup!\n");
	routeMgr->initLinks();

	Iterator it(pelletMgr);
	CI_LOOP(it)
	{
		Creature* pellet = *it;
		if (pellet) {
			pellet->mSRT.t.y = mMapMgr->getMinY(pellet->mSRT.t.x, pellet->mSRT.t.z, true);
		}
	}

	for (int i = 0; i < 3; i++) {
		GoalItem* goal = itemMgr->getContainer(i);
		if (goal) {
			GameStat::containerPikis.set(goal->mHeldPikis[Leaf] + goal->mHeldPikis[Bud] + goal->mHeldPikis[Flower], goal->mOnionColour);
			GameStat::update();
		}
	}

	GameStat::update();
	PRINT("********* BONUS PIKI CHECK\n");
	GameStat::dump();

	if (playerState->mHasExtinctionDemoPlayed == false && !playerState->isTutorial()
	    && ((GameStat::allPikis[Blue] == 0 && playerState->hasContainer(Blue))
	        || (GameStat::allPikis[Red] == 0 && playerState->hasContainer(Red))
	        || (GameStat::allPikis[Yellow] == 0 && playerState->hasContainer(Yellow)))) {
		if (!playerState->mDemoFlags.isFlag(DEMOFLAG_PostExtinctionSeed)) {
			playerState->mDemoFlags.setFlag(DEMOFLAG_PostExtinctionSeed, nullptr);
			playerState->mHasExtinctionDemoPlayed = true;
		} else {
			gameflow.mGameInterface->movie(DEMOID_Unk64Cat, 0, nullptr, nullptr, nullptr, CAF_AllVisibleMask, true);
			playerState->mHasExtinctionDemoPlayed = true;
		}
	}

	if (!playerState->isTutorial() && !playerState->isChallengeMode()) {
		PRINT("========== NAVI STARTING STATE START \n");
		Navi* navi = naviMgr->getNavi();
		if (navi) {
			navi->mStateMachine->transit(navi, 23);
			itemMgr->getUfo();
			cameraMgr->mCamera->startCamera(navi, 1, 0);
		}
	} else {
		if (playerState->isTutorial()) {
			cameraMgr->mCamera->startCamera(mNavi, 0, 0);
			if (playerState->isTutorial() && playerState->mShipEffectPartFlag & 8) {
				cameraMgr->mCamera->startMotion(cameraMgr->mCamera->mAttentionInfo);
				cameraMgr->mCamera->mControlsEnabled = false;
			}
		} else {
			cameraMgr->mCamera->startCamera(mNavi, 1, 0);
		}
	}

	UfoItem* ufo = itemMgr->getUfo();
	if (ufo) {
		if (!playerState->isTutorial()) {
			ufo->setSpotActive(true);
		} else {
			ufo->setSpotActive(false);
		}
	}

	if (bossMgr) {
		bossMgr->finalSetup();
	}

	if (itemMgr && itemMgr->getMeltingPotMgr()) {
		itemMgr->getMeltingPotMgr()->finalSetup();
	}

	if (workObjectMgr) {
		workObjectMgr->finalSetup();
	}

	PRINT("====================== FINAL SETUP DONE ======================\n");
}

/**
 * @todo: Documentation
 */
GameCoreSection::GameCoreSection(Controller* controller, MapMgr* mgr, Camera& camera)
    : Node("gamecore")
{
	mDrawHideType = 0;
	textDemoState = 0;
	finishPause();
#if defined(WIN32)
	// Player 2 controller responsible for additional debug controls
	/* DAT_104c2340 = */ new Controller(2);
	bugPrintBuffer = new BugPrintBuffer();
#endif
	mHideFlags       = 0;
	demoEventMgr     = new DemoEventMgr();
	radarInfo        = new RadarInfo();
	_34              = 0;
	mDoneSundownWarn = false;

	memStat->start("gamecore");
	seSystem      = new SeSystem();
	generatorList = new GeneratorList();

	mController = controller;
	mMapMgr     = mgr;

	memStat->start("gui");
	containerWindow = new zen::DrawContainer();
	hurryupWindow   = new zen::DrawHurryUp();
	accountWindow   = new zen::DrawAccount();
	memStat->end("gui");

	FastGrid::initAIGrid(7);
	_70.mDistancedRange = 500.0f;
	NakataCodeInitializer::init();

	if (!preloadUFO) {
		memStat->start("pellet");
		pelletMgr = new PelletMgr(mMapMgr);
		gameflow.addGenNode("ペレットマネージャ", pelletMgr); // 'pellet manager'
		memStat->end("pellet");
	}

	memStat->start("mapMgr");

	memStat->start("workobj");
	workObjectMgr = new WorkObjectMgr();
	gameflow.addGenNode("仕事オブジェマネージャ",
	                    workObjectMgr); // 'work object manager'
	memStat->end("workobj");

	memStat->end("mapMgr");

	mPikiShape                = nullptr;
	mShadowTexture            = gsys->loadTexture("effects/shadow.txe", true);
	mShadowTexture->mTexFlags = (Texture::TEX_CLAMP_S | Texture::TEX_Unk2 | Texture::TEX_CLAMP_T);
	mBigFont                  = new Font();
	mBigFont->setTexture(gsys->loadTexture("bigFont.bti", true), 21, 36);

	memStat->start("dynamics");
#if defined(VERSION_PIKIDEMO) || defined(VERSION_GPIJ01_01)
	particleHeap = new DynParticleHeap(0x200);
#else
	particleHeap = new DynParticleHeap(0x400);
#endif
	memStat->end("dynamics");

	mAiPerfDebugMenu                     = new Menu(mController, gsys->mConsFont);
	mAiPerfDebugMenu->mCenterPoint.mMinX = glnWidth / 2;
	mAiPerfDebugMenu->mCenterPoint.mMinY = glnHeight / 2;
	AIPerf p;
	p.addMenu(mAiPerfDebugMenu);
	GlobalShape::init();

	pikiUpdateMgr = new UpdateMgr();
	pikiUpdateMgr->create(10);

	searchUpdateMgr = new UpdateMgr();
	searchUpdateMgr->create(9);

	pikiLookUpdateMgr = new UpdateMgr();
	pikiLookUpdateMgr->create(20);

	pikiOptUpdateMgr = new UpdateMgr();
	pikiOptUpdateMgr->create(2);

	tekiOptUpdateMgr = new UpdateMgr();
	tekiOptUpdateMgr->create(3);

	seMgr = new SeMgr();

	AIConstant::createInstance();
#if defined(PIKI_PC_PORT)
	// Field limit, straight after the constants exist. AICONST dereferences
	// AIConstant::_instance, which is null until this point and is set back to
	// null on teardown, so this cannot be done from the game's own start-up
	// message handler.
	//
	// Every consumer reads the value through AICONST.mMaxPikisOnField(), so
	// writing it once here covers the spawn gates in pikiMgr and itemMgr as
	// well as the HUD counter.
	AICONST.mMaxPikisOnField(pc_randomizer_expanded() ? pc_randomizer_field_capacity() : pc_settings_get_piki_limit());

	// Day length. The menu shows minutes of play, and a day runs 7am to 7pm --
	// half the 24-hour cycle this parameter describes -- so double it. The
	// clock recomputes its speed from here every tick, and each stage's own
	// day_multiply still applies on top, as designed.
	gameflow.mParameters->mRealMinutesPerGameDay(f32(pc_settings_get_day_minutes()) * 2.0f);
#endif
	gameflow.addGenNode("AI定数", AIConstant::_instance); // 'AI Constants'

	KeyConfig::createInstance();
	gameflow.addGenNode("Key Setting", KeyConfig::_instance);

	mSearchSystem = new SearchSystem();

	PikiShapeObject::init();
	SAIEventInit();

	pikiInfo = new PikiInfo();

	PRINT("================== NAVI ===================\n");
	memStat->start("navi");
	naviMgr = new NaviMgr();
	naviMgr->create(1);
	mNavi = static_cast<Navi*>(naviMgr->birth());
	PRINT("********* navi ==== %x\n", mNavi);
	gameflow.addGenNode("naviMgr", naviMgr);
	memStat->end("navi");

	utEffectMgr = new UtEffectMgr();

	memStat->start("generator");
	generatorMgr = new GeneratorMgr();
	generatorMgr->setName("default");
	gameflow.addGenNode("ジェネレータ(default)",
	                    generatorMgr); // 'generator (default)'

	GenObjectDebug::initialise();
	GenObjectItem::initialise();
	GenObjectPellet::initialise();
	GenObjectWorkObject::initialise();
	GenObjectPlant::initialise();
	GenObjectMapParts::initialise(mMapMgr);
	GenObjectTeki::initialise();
	GenObjectBoss::initialise();
	GenObjectMapObject::initialise(mMapMgr);
	GenObjectNavi::initialise();
	GenObjectActor::initialise();

	onceGeneratorMgr = new GeneratorMgr();
	onceGeneratorMgr->setName("init");
	gameflow.addGenNode("ジェネレータ(init)",
	                    onceGeneratorMgr); // 'generator (init)'

	dailyGeneratorMgr = new GeneratorMgr();
	dailyGeneratorMgr->setName("daily");
	gameflow.addGenNode("ジェネレータ(daily)",
	                    dailyGeneratorMgr); // 'generator (daily)'

	plantGeneratorMgr = new GeneratorMgr();
	plantGeneratorMgr->setName("plant");
	gameflow.addGenNode("ジェネレータ(plants)",
	                    plantGeneratorMgr); // 'generator (plants)'

	limitGeneratorMgr = new GeneratorMgr();
	limitGeneratorMgr->setLimitGenerator(true);
	limitGeneratorMgr->setName("limit");
	gameflow.addGenNode("ジェネレータ(limit)",
	                    limitGeneratorMgr); // 'generator (limit)'
	memStat->end("generator");

	memStat->start("boss");
	int prevBossHeap = gsys->setHeap(SYSHEAP_Teki);
	bossMgr          = new BossMgr();
	gsys->setHeap(prevBossHeap);
	memStat->end("boss");
	gameflow.addGenNode("bossMgr", bossMgr);

	memStat->start("teki");
	int prevTekiHeap = gsys->setHeap(SYSHEAP_Teki);
	tekiMgr          = new TekiMgr();
	gsys->setHeap(prevTekiHeap);
	memStat->end("teki");
	gameflow.addGenNode("tekiMgr", tekiMgr);

	if (!preloadUFO) {
		memStat->start("item");
		itemMgr = new ItemMgr();
		memStat->end("item");
	}

	memStat->start("mapMgr");
	memStat->start("plant");
	plantMgr = new PlantMgr(mMapMgr);
	memStat->end("plant");
	memStat->end("mapMgr");

	mNavi->mNaviCamera = &camera;
	mNavi->init();
	camera.mPosition.x = 500.0f * sinf(camera.mRotation.x);
	camera.mPosition.y = 140.0f;
	camera.mPosition.z = 500.0f * cosf(camera.mRotation.x);
	gsys->setFade(1.0f);
	cameraMgr = new PcamCameraManager(&camera, mNavi->mKontroller);
	gameflow.addGenNode("cameraMgr", cameraMgr);
	memStat->end("gamecore");

	mDrawGameInfo = new zen::DrawGameInfo(!gameflow.mIsChallengeMode ? zen::DrawGameInfo::MODE_Story : zen::DrawGameInfo::MODE_Challenge);
}

/**
 * @todo: Documentation
 */
#if defined(PIKI_PC_PORT) && PIKI_DEBUG_KEYS
/**
 * @brief Debug shortcuts for the Mods settings, switched on in that menu.
 *
 * F5 stocks 20 red Pikmin in the Onion, up to the configured limit: reaching a
 * few hundred the honest way takes far too long to iterate on. F6 pushes the
 * clock on by an in-game hour, so a change to the day length can be judged
 * without sitting through it.
 */
static void pcDebugKeys()
{
	// Off unless asked for: a stray F5 would otherwise fill someone's Onion
	// mid-game. Enable with PIKMIN_DEBUG_KEYS=1.
	// Read every frame, so the switch in the Mods menu takes effect at once.
	if (!pc_settings_get_debug_keys()) {
		return;
	}

	const Uint8* keys = SDL_GetKeyboardState(nullptr);
	static bool wasDown = false;
	const bool isDown   = keys != nullptr && keys[SDL_SCANCODE_F5] != 0;
	if (isDown && !wasDown) {
		// GoalItem::enterGoal touches three things when a Pikmin walks into the
		// Onion, and all three matter: pikiInfMgr is the stock carried between
		// days, mHeldPikis is what the withdrawal screen actually counts, and
		// GameStat feeds the HUD. Updating fewer just moves the number on
		// screen without putting anything in the Onion.
		GoalItem* onion = itemMgr ? itemMgr->getContainer(Red) : nullptr;
		if (onion == nullptr) {
			fprintf(stderr, "[DEBUG] no red Onion in this stage\n");
			fflush(stderr);
		} else {
			// Do not stock past the configured limit: the pools are sized
			// from it, and going over just trades this shortcut for a birth
			// failure later.
			const int limit   = pc_settings_get_piki_limit();
			const int already = int(GameStat::allPikis);
			int added         = 20;
			if (already + added > limit) {
				added = limit - already;
			}
			if (added <= 0) {
				fprintf(stderr, "[DEBUG] already at the %d limit\n", limit);
				fflush(stderr);
				wasDown = isDown;
				return;
			}
			pikiInfMgr.mPikiCounts[Red][Leaf] += added;
			onion->mHeldPikis[Leaf] += added;
			GameStat::containerPikis.add(Red, added);
			GameStat::update();
			fprintf(stderr, "[DEBUG] +%d red Pikmin in the Onion (holding %d)\n",
			        added, onion->getTotalStorePikis());
			fflush(stderr);
		}
	}
	wasDown = isDown;

	// F6 pushes the clock on by an in-game hour, so a change to the day length
	// can be judged in seconds instead of by sitting through it.
	static bool hourWasDown = false;
	const bool hourDown     = keys != nullptr && keys[SDL_SCANCODE_F6] != 0;
	if (hourDown && !hourWasDown) {
		WorldClock& clock = gameflow.mWorldClock;
		const f32 next    = clock.mTimeOfDay + 1.0f;
		clock.setTime(next >= clock.mHoursInDay ? clock.mHoursInDay - 0.01f : next);
		fprintf(stderr, "[DEBUG] clock -> %02d:00 (day is %d min of play)\n",
		        clock.mCurrentGameHour, pc_settings_get_day_minutes());
		fflush(stderr);
	}
	hourWasDown = hourDown;
}
#endif

void GameCoreSection::update()
{
	STACK_PAD_VAR(2);
#if defined(PIKI_PC_PORT) && PIKI_DEBUG_KEYS
	pcDebugKeys();
#endif
	if (!gameflow.mMoviePlayer->mIsActive && !mDoneSundownWarn && gameflow.mWorldClock.mTimeOfDay >= gameflow.mParameters->mNightWarning()
	    && (flowCont.mGameEndFlag != GAMEEND_PikminExtinction || flowCont.mGameEndFlag != GAMEEND_NaviDown)) {
		if (playerState->inDayEnd()) {
			PRINT("======== IN DAY END *** \n");
		} else {
			startSundownWarn();
		}
	}

	if (!gameflow.mMoviePlayer->mIsActive && hurryupWindow->update()) {
		PRINT("ZAMA*HURRY!!\n");
	}
	accountWindow->update();
	routeMgr->update();

	if (!gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
		playerState->update();
#if defined(WIN32)
		bugPrintBuffer->update();
#endif
	}

	if (GameStat::allPikis == 0 && GameStat::maxPikis > 0) {
		Navi* navi = mNavi;
		int id     = navi->getCurrState()->getID();
		if (id != NAVISTATE_PikiZero && id != NAVISTATE_DemoSunset && id != NAVISTATE_DemoWait && id != NAVISTATE_DemoInf) {
			PRINT("**** PIKI ZERO GAME OVER *******\n");
			PRINT("deadpikis %d pellets %d killtekis %d maxpikis %d" MISSING_NEWLINE, static_cast<int>(GameStat::deadPikis),
			      static_cast<int>(GameStat::getPellets), static_cast<int>(GameStat::killTekis), GameStat::maxPikis);
			navi->mStateMachine->transit(navi, NAVISTATE_PikiZero);
			playerState->mResultFlags.setOn(zen::RESFLAG_PikminExtinction);
		}
	}

	if (!gameflow.mMoviePlayer->mIsActive) {
		cameraMgr->update();
	}


	Piki* nextThrowPiki = naviMgr->getNavi()->mNextThrowPiki;
	int encodedNextThrowType;
	if (nextThrowPiki) {
		int color = nextThrowPiki->mColor;
		int happa = nextThrowPiki->mHappa;
		BOOL isHolding;
		if (nextThrowPiki->isHolding()) {
			isHolding = TRUE;
		} else {
			isHolding = FALSE;
		}
		if (color > PikiMaxColor) {
			color = Blue;
		}
		if (happa > PikiMaxHappa) {
			happa = Flower;
		}

		// well this sure is a way to do this.

		// 1-3 = leaf/bud/flower, no bomb, blue
		// 4-6 = leaf/bud/flower, bomb, blue
		// 7-12 = ", ", red
		// 13-18 = ", ", yellow
		encodedNextThrowType = (PikiHappaCount * 2) * color + PikiHappaCount * isHolding + happa + 1;
	} else {
		// 0 = no next throw piki
		encodedNextThrowType = 0;
	}
	zen::pGameInfo->mEncodedNextThrowType = encodedNextThrowType;
	zen::pGameInfo->mTotalPikiNum         = GameStat::allPikis;
	zen::pGameInfo->mMapPikiNum           = GameStat::mapPikis;
	zen::pGameInfo->mFormationPikiNum     = GameStat::formationPikis;
	Node::update();
}

/**
 * @todo: Documentation
 */
void GameCoreSection::startContainerDemo()
{
	_34 = 2;
}

/**
 * @todo: Documentation
 */
void GameCoreSection::startSundownWarn()
{
	mDoneSundownWarn = true;
	PRINT("***** START HURRY UP WINDOW\n");
	hurryupWindow->start(zen::DrawHurryUp::MesgType1);
	seSystem->playSysSe(SYSSE_EVENING_ALERT);
}

/**
 * @todo: Documentation
 */

#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)

void pc_randomizer_test_work_damage()
{
    auto require = [](bool ok, const char* why) {
        if (!ok) { std::printf("WORK_TEST_FAIL %s\n", why); std::fflush(stdout); std::abort(); }
    };
    Piki* sample = nullptr;
    Iterator pikis(pikiMgr);
    CI_LOOP(pikis) { Piki* p = static_cast<Piki*>(*pikis); if (p && p->isAlive()) { sample = p; break; } }
    BuildingItem* wall = nullptr; BuildingItem* bomb = nullptr; KusaItem* stick = nullptr; Bridge* bridge = nullptr;
    Iterator items(itemMgr->mMeltingPotMgr);
    CI_LOOP(items) {
        Creature* obj = *items;
        if (obj->mObjType == OBJTYPE_SluiceSoft) wall = static_cast<BuildingItem*>(obj);
        if (obj->mObjType == OBJTYPE_SluiceBomb || obj->mObjType == OBJTYPE_SluiceBombHard) bomb = static_cast<BuildingItem*>(obj);
        if (obj->mObjType == OBJTYPE_Kusa) stick = static_cast<KusaItem*>(obj);
    }
    Iterator works(workObjectMgr);
    CI_LOOP(works) { WorkObject* obj = static_cast<WorkObject*>(*works); if (obj->isBridge()) bridge = static_cast<Bridge*>(obj); }
    require(sample && wall && bomb && stick && stick->mBaseItem && bridge, "real Navel objects");
    sample->mActiveAction->abandon(nullptr);
    ActBreakWall wallAction(sample); wallAction.init(wall); wallAction.mWorkTimer = 0;
    ActBridge bridgeAction(sample); bridgeAction.init(bridge); bridgeAction.mStageID = 0;
    ActBoMake stickAction(sample); stickAction.mBuildObject = stick->mBaseItem;
    wall->mMaxHealth = wall->mHealth = 100.0f; wall->mCurrStage = 0;
    bridge->mMaxHealth = 100.0f; bridge->mStageProgressList[0] = 0.0f; bridge->setStageFinished(0, false);
    stick->mMaxHealth = 1000.0f; stick->mHealth = 0.0f;
    for (int color = 0; color < 3; ++color) {
        sample->initColor(color);
        const f32 damage = sample->getAttackPower();
        const int intervals[] = {0, 1, 59};
        for (int elapsed : intervals) {
            const f32 beforeWall = wall->mHealth;
            wallAction.mStartAttackTime = gameflow.mWorldClock.mCurrentGameMinute - elapsed;
            wallAction.animationKeyUpdated(PaniAnimKeyEvent(KEY_Action0)); wallAction.breakWall();
            require(std::fabs(beforeWall - wall->mHealth - damage / 600.0f) < 0.0001f, "wall damage independent of time");
            const f32 afterWall = wall->mHealth;
            wallAction.breakWall();
            require(wall->mHealth == afterWall, "wall event consumed once");
            const f32 beforeBridge = bridge->mStageProgressList[0];
            bridgeAction.animationKeyUpdated(PaniAnimKeyEvent(KEY_LoopEnd)); bridgeAction.doWork(elapsed);
            require(std::fabs(bridge->mStageProgressList[0] - beforeBridge - damage / 600.0f) < 0.0001f, "bridge damage independent of time");
            require(!bridgeAction.mIsAttackReady, "bridge event consumed");
            const f32 beforeStick = stick->mHealth;
            stickAction.animationKeyUpdated(PaniAnimKeyEvent(KEY_Action0));
            require(std::fabs(stick->mHealth - beforeStick - damage * 0.04f) < 0.0001f, "stick damage");
        }
        sample->mMode = PikiMode::BreakwallMode;
        const int motions[] = {PIKIANIM_Kuttuku, PIKIANIM_Job2};
        for (int motion : motions) {
            sample->startMotion(PaniMotionInfo(motion), PaniMotionInfo(motion));
            f32 before = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter;
            sample->mPikiAnimMgr.updateAnimation(30.0f);
            f32 baseStep = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter - before;
            sample->startMotion(PaniMotionInfo(motion), PaniMotionInfo(motion));
            before = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter;
            sample->doAnimation();
            f32 step = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter - before;
            require(baseStep > 0 && std::fabs(step - baseStep * pc_randomizer_color_multiplier(color, PC_PIKI_ATTACK_RATE)) < 0.01f, "work animation speed");
        }
        const f32 bombHealth = bomb->mHealth;
        InteractAttack attack(sample, nullptr, damage, false);
        require(!bomb->stimulate(attack) && bomb->mHealth == bombHealth, "bomb wall rejects ordinary damage");
        std::printf("TEST_ONLY work_damage color=%d damage=%.3f elapsed=0,1,59 animations=Kuttuku,Job2\n", color, damage);
    }
    std::puts("TEST_ONLY work_damage_pass"); std::fflush(stdout); std::exit(0);
}

void pc_randomizer_test_color_stats()
{
    auto require = [](bool ok, const char* why) {
        if (!ok) { std::printf("[Pikmin Randomizer] STATS_TEST_FAIL %s\n", why); std::fflush(stdout); std::abort(); }
    };
    require(pc_randomizer_color_stats(), "profiles missing");
    Piki* crew[10]; int available = 0;
    Iterator pikis(pikiMgr);
    CI_LOOP(pikis) {
        Piki* piki = static_cast<Piki*>(*pikis);
        if (piki && piki->isAlive() && piki->mColor == Red && available < 10) crew[available++] = piki;
    }
    require(available == 10, "initial field count");
    Piki* sample = crew[0];
    for (int color = 0; color < 3; ++color) {
        sample->initColor(color);
        const f32 base = color == Blue ? pikiMgr->mPikiParms->mPikiParms.mBlueAttackPower()
            : color == Red ? pikiMgr->mPikiParms->mPikiParms.mRedAttackPower() : pikiMgr->mPikiParms->mPikiParms.mYellowAttackPower();
        require(std::fabs(sample->getAttackPower() - base * pc_randomizer_color_multiplier(color, PC_PIKI_DAMAGE)) < 0.001f, "damage hook");
        const f32 speed = pikiMgr->mPikiParms->mPikiParms.mMaxLeafMoveSpeed() * pc_randomizer_color_multiplier(color, PC_PIKI_MOVEMENT);
        Vector3f direction(1.0f, 0.0f, 0.0f);
        sample->setSpeed(1.0f, direction);
        require(std::fabs(sample->mTargetVelocity.x - speed) < 0.001f && std::fabs(sample->getSpeed(1.0f) - speed) < 0.001f, "movement hook");
        sample->startMotion(PaniMotionInfo(PIKIANIM_Kuttuku), PaniMotionInfo(PIKIANIM_Kuttuku));
        f32 before = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter;
        sample->mPikiAnimMgr.updateAnimation(30.0f);
        f32 baseStep = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter - before;
        sample->startMotion(PaniMotionInfo(PIKIANIM_Kuttuku), PaniMotionInfo(PIKIANIM_Kuttuku));
        before = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter;
        sample->doAnimation();
        f32 step = sample->mPikiAnimMgr.getUpperAnimator().mAnimationCounter - before;
        require(baseStep > 0.0f && std::fabs(step - baseStep * pc_randomizer_color_multiplier(color, PC_PIKI_ATTACK_RATE)) < 0.01f, "attack animation hook");
        std::printf("[Pikmin Randomizer] TEST_ONLY stats_actor color=%d damage=%.3f speed=%.3f attack_ratio=%.3f\n", color, sample->getAttackPower(), speed, step/baseStep);
    }
    sample->initColor(Blue);
    const int redStrength = pc_randomizer_carry_strength(Red), blueStrength = pc_randomizer_carry_strength(Blue);
    Pellet* pellet = nullptr; int bodies = 0;
    Iterator pellets(pelletMgr);
    CI_LOOP(pellets) {
        Pellet* candidate = static_cast<Pellet*>(*pellets);
        if (!candidate || !candidate->isAlive() || !candidate->isUfoParts() || !candidate->mConfig) continue;
        int weight = candidate->mConfig->mCarryMinPikis();
        int count = 1 + (weight - blueStrength + redStrength - 1) / redStrength;
        if (weight >= 15 && count >= 2 && count <= available && count < weight && count <= candidate->mConfig->mCarryMaxPikis()) {
            pellet = candidate; bodies = count; break;
        }
    }
    require(pellet != nullptr, "eligible real ship part");
    ActTransport* actions[10];
    for (int i = 0; i < bodies; ++i) {
        Piki* piki = crew[i];
        piki->mActiveAction->abandon(nullptr);
        piki->mActiveAction->mCurrActionIdx = PikiAction::Transport;
        piki->mActiveAction->mChildActions[PikiAction::Transport].initialise(pellet);
        piki->mMode = PikiMode::TransportMode;
        actions[i] = static_cast<ActTransport*>(piki->mActiveAction->getCurrAction());
        actions[i]->mSlotIndex = i;
        piki->mSRT.t = pellet->getSlotGlobalPos(i, 0.0f);
        piki->startStickObject(pellet, nullptr, i, 0.0f);
        actions[i]->mIsLiftActionDone = true; // Fixture skips the lifting animation only.
        require(!pellet->isSlotFree(i), "one physical slot per carrier");
    }
    const int expected = blueStrength + (bodies - 1) * redStrength;
    require(actions[0]->calcCarryStrength() == expected, "mixed attached strength");
    pellet->update();
    require(pellet->mCarrierCounter == expected, "pellet aggregate strength");
    ActTransport* leader = nullptr;
    for (int i = 0; i < bodies; ++i) if (actions[i]->isStickLeader()) leader = actions[i];
    require(leader != nullptr, "carry leader");
    leader->doLift();
    require(leader->mState == ActTransport::STATE_Move && pellet->getPickOffset() != 0.0f, "native weighted lift");
    Vector3f direction(10.0f, 0.0f, 0.0f);
    pellet->doCarry(crew[0], direction, expected);
    const f32 expectedMove = (pc_randomizer_color_multiplier(Blue, PC_PIKI_MOVEMENT)
        + (bodies - 1) * pc_randomizer_color_multiplier(Red, PC_PIKI_MOVEMENT)) / bodies;
    require(std::fabs(pellet->mCarryDirection.x - 10.0f * expectedMove) < 0.001f, "crew average hauling speed");
    crew[bodies - 1]->endStickObject();
    require(pellet->isSlotFree(bodies - 1), "released body slot");
    pellet->update();
    require(actions[0]->calcCarryStrength() == expected - redStrength, "remaining crew strength");
    require(pellet->mCarrierCounter == 0 && pellet->mPikiCarrier == nullptr && pellet->getPickOffset() == 0.0f, "put down below weight");
    std::printf("[Pikmin Randomizer] TEST_ONLY stats_carry_pass bodies=%d strength=%d weight=%d slots=%d\n", bodies, expected, pellet->mConfig->mCarryMinPikis(), bodies);
    std::fflush(stdout);
    std::exit(0); // Isolated fixture process; never continue a synthetic session.
}
#endif

void GameCoreSection::updateAI()
{
    if (pc_randomizer_expanded()) {
        AICONST.mMaxPikisOnField(pc_randomizer_field_capacity());
        const bool active = !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll
            && !gameflow.mIsUIOverlayActive && mNavi && mNavi->mHealth > 0.0f;
        if (active) {
            const int field = int(GameStat::formationPikis) + int(GameStat::freePikis) + int(GameStat::workPikis);
            pc_randomizer_observe_population(field, true);
            pc_randomizer_observe_total_population(int(GameStat::allPikis), true);
            if (flowCont.mCurrentStage) {
                auto observe = [](Creature* obj, int kind, bool complete) {
                    if (!obj || !obj->mGenerator) return;
                    const Vector3f pos = obj->mGenerator->mGenPosition + obj->mGenerator->mGenOffset;
                    pc_randomizer_observe_obstacle(flowCont.mCurrentStage->mStageID, kind, pos.x, pos.z, complete, true);
                };
                if (itemMgr) {
                    Iterator it(itemMgr->mMeltingPotMgr);
                    CI_LOOP(it) {
                        Creature* obj = *it;
                        if (!obj) continue;
                        if (obj->isSluice()) observe(obj, obj->mObjType, static_cast<BuildingItem*>(obj)->isCompleted());
                        else if (obj->mObjType == OBJTYPE_Kusa) observe(obj, 100, obj->mMaxHealth > 0 && obj->mHealth >= obj->mMaxHealth);
                    }
                }
                if (workObjectMgr) {
                    Iterator it(workObjectMgr);
                    CI_LOOP(it) {
                        WorkObject* obj = static_cast<WorkObject*>(*it);
                        if (obj && (obj->isBridge() || obj->isHinderRock())) observe(obj, obj->isBridge() ? 101 : 102, obj->isFinished());
                    }
                }
            }
            UfoItem* ship = itemMgr ? itemMgr->getUfo() : nullptr;
            if (ship && flowCont.mCurrentStage) {
                const Vector3f base = ship->getGoalPos();
                pc_randomizer_observe_exploration(flowCont.mCurrentStage->mStageID,
                    mNavi->getPosition().x - base.x, mNavi->getPosition().z - base.z, mNavi->mGroundTriangle != nullptr, true);
            }
        }
    }
    static bool randomizerWeightsLogged = false;
    if (pc_randomizer_enabled() && pelletMgr && !randomizerWeightsLogged) {
        for (int part = 0; part < 30; ++part) {
            PelletConfig* config = pelletMgr->getConfig(PelletMgr::getUfoIDFromIndex(part));
            pc_randomizer_validate_part_weight(part, config ? config->mCarryMinPikis() : -1);
            if (config) std::printf("[Pikmin Randomizer] PART_WEIGHT id=%d min=%d max=%d\n",
                part, config->mCarryMinPikis(), config->mCarryMaxPikis());
        }
        randomizerWeightsLogged = true;
    }
    playerState->reconcileBbftParts(); // Also handles a checked snapshot received after boot.
    static int bbftBombAccess = -1;
    if (pc_bbft_shared_capabilities() && bbftBombAccess != int(pc_bbft_bomb_rocks())) {
        bbftBombAccess = int(pc_bbft_bomb_rocks());
        pc_bbft_milestone(bbftBombAccess ? "PIKMIN_BOMB_ROCKS enabled=1" : "PIKMIN_BOMB_ROCKS enabled=0");
    }
    static int bbftAreaMask = -1;
    if (pc_bbft_progression()) {
        int mask = 0;
        for (int stage = STAGE_Practice; stage < STAGE_COUNT; ++stage)
            if (playerState->courseOpen(stage)) mask |= 1 << stage;
        if (mask != bbftAreaMask) {
            char message[128];
            std::sprintf(message, "PIKMIN_AREA_ACCESS impact=%d forest=%d navel=%d spring=%d trial=%d",
                !!(mask & 1), !!(mask & 2), !!(mask & 4), !!(mask & 8), !!(mask & 16));
            pc_bbft_milestone(message);
            bbftAreaMask = mask;
        }
    }
    // Grants are once per fresh BBFT session, never once per stage or refill.
    static bool bbftColorGranted[3] = {};
    static bool initialColorRegistered = false;
    const int initialColor = pc_randomizer_enabled() ? pc_randomizer_start_color() : Red;
    if (!initialColorRegistered) { bbftColorGranted[initialColor] = true; initialColorRegistered = true; }
    if (pc_bbft_progression() && itemMgr && !gameflow.mMoviePlayer->mIsActive) {
        for (int color = 0; color < 3; ++color) {
            if (bbftColorGranted[color] || !pc_bbft_color_access(color)) continue;
            GoalItem* onion = itemMgr->getContainer(color);
            const bool booted = playerState->hasBootContainer(color);
            playerState->setContainer(color);
            if (onion && !booted) onion->startBoot();
            playerState->setBootContainer(color);
            playerState->setDisplayPikiCount(color);
            pikiInfMgr.mPikiCounts[color][Leaf] += 5;
            if (onion) onion->mHeldPikis[Leaf] += 5;
            for (int i = 0; i < 5; ++i) GameStat::containerPikis.inc(color);
            playerState->mTotalBornPikiNum += 5;
            playerState->mLivingPikiNum += 5;
            GameStat::update();
            char stockMessage[128];
            std::sprintf(stockMessage, "PIKMIN_COLOR_STOCK color=%s stored=%d actor=%d",
                color == Blue ? "Blue" : color == Red ? "Red" : "Yellow", pikiInfMgr.mPikiCounts[color][Leaf], onion != nullptr);
            pc_bbft_milestone(stockMessage);
            bbftColorGranted[color] = true;
            pc_bbft_milestone(color == Blue ? "PIKMIN_BLUE_ONION_GRANTED starter=5" : color == Red ? "PIKMIN_RED_ONION_GRANTED starter=5" : "PIKMIN_YELLOW_ONION_GRANTED starter=5");
        }
    }
    static bool bbftRedsQueued = false, bbftRedsReady = false;
    static int bbftInitialField = 20;
    if (pc_bbft_skip_tutorial() && !gameflow.mMoviePlayer->mIsActive
        && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive && itemMgr) {
        GoalItem* redOnion = itemMgr->getContainer(initialColor);
        const int initialField = bbftRedsQueued ? bbftInitialField : pc_randomizer_enabled() && pc_randomizer_field_capacity() < 20 ? pc_randomizer_field_capacity() : 20;
        if (!bbftRedsQueued && redOnion && redOnion->getTotalStorePikis() >= 20) {
            // Use normal Onion withdrawal: initialized actors descend the legs
            // and join Olimar through their native exit state, no fake count.
            bbftInitialField = initialField;
            redOnion->exitPikis(initialField);
            bbftRedsQueued = true;
        }
        if (bbftRedsQueued && !bbftRedsReady && redOnion && redOnion->getTotalStorePikis() == 20 - initialField
            && GameStat::allPikis[initialColor] - GameStat::containerPikis[initialColor] == initialField) {
            if (initialColor == Red && initialField == 20) pc_bbft_milestone("PIKMIN_FOH_READY day=2 field_red=20 main_engine_ap_check=0");
            if (pc_randomizer_enabled()) {
                std::printf("[Pikmin Randomizer] START_COLOR_READY stage=%d color=%d field=%d\n", flowCont.mCurrentStage->mStageID, initialColor, initialField);
                if (initialColor == Red) std::printf("[Pikmin Randomizer] START_READY stage=%d field_red=%d\n", flowCont.mCurrentStage->mStageID, initialField);
            }
            bbftRedsReady = true;
        }
    }
#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)
    const char* scripted = std::getenv("PIKMIN_RANDOMIZER_TEST_SCRIPT");
    const char* background = std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND");
    if (scripted && !std::strcmp(scripted, "bestiary-v2") && background && !std::strcmp(background, "1")
        && pc_randomizer_ready() && bbftRedsReady && pc_bbft_color_access(Blue) && pc_bbft_color_access(Yellow)
        && !gameflow.mMoviePlayer->mIsActive) {
        GoalItem* onion = itemMgr->getContainer(pc_randomizer_start_color());
        Pellet* sample = nullptr;
        Iterator pellets(pelletMgr);
        CI_LOOP(pellets) { sample = static_cast<Pellet*>(*pellets); if (sample) break; }
        if (!sample || !onion) std::abort();
        const int species[] = {31, 25, 32, 0, 11, 8, 9, 17, 13, 24};
        for (int type : species) {
            PelletConfig* config = pelletMgr->getConfig(TekiMgr::getTypeId(type));
            if (!config || config->mPelletType() != PELTYPE_Corpse || config->mPelletColor() != -1) {
                std::printf("BESTIARY_FAIL config type=%d\n", type); std::fflush(stdout); std::abort();
            }
            std::printf("TEST_ONLY bestiary_config type=%d weight=%d\n", type, config->mCarryMinPikis());
            sample->mConfig = config; // Isolated fixture substitutes real loaded configs, not carry physics.
            onion->suckMe(sample); onion->suckMe(sample);
        }
        Iterator enemies(tekiMgr);
        Teki* victim = nullptr;
        CI_LOOP(enemies) { victim = static_cast<Teki*>(*enemies); if (victim && !victim->mDeadState) break; }
        if (!victim) std::abort();
        victim->mTekiType = TEKI_Mar; victim->mHealth = 0; victim->die();
        if (!pc_randomizer_checked("Bestiary: Defeat Puffy Blowhog")) std::abort();
        std::puts("TEST_ONLY bestiary_v2_pass"); std::fflush(stdout); std::exit(0);
    }
    if (scripted && !std::strcmp(scripted, "collection") && background && !std::strcmp(background, "1")
        && pc_randomizer_collection_checks() && bbftRedsReady && !gameflow.mMoviePlayer->mIsActive) {
        static bool prepared = false, delivered = false;
        static Teki* victim = nullptr;
        GoalItem* onion = itemMgr->getContainer(pc_randomizer_start_color());
        if (!prepared && onion && tekiMgr) {
            const int species[] = {3, 4, 18, 19, 20, 15, 30, 33};
            for (int type : species) {
                PelletConfig* config = pelletMgr->getConfig(TekiMgr::getTypeId(type));
                if (!config || config->mPelletType() != PELTYPE_Corpse || config->mPelletColor() != -1
                    || config->mCarryMinPikis() < 1 || config->mCarryMinPikis() > 20) std::abort();
                std::printf("[Pikmin Randomizer] CORPSE_CONFIG type=%d minimum=%d\n", type, config->mCarryMinPikis());
            }
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                Teki* enemy = (Teki*)*it;
                if (enemy->mTekiType == 3 && enemy->mHealth > 0) { victim = enemy; break; }
            }
            if (!victim) std::abort();
            const int color = pc_randomizer_start_color();
            pikiInfMgr.mPikiCounts[color][Leaf] += 480;
            onion->mHeldPikis[Leaf] += 480;
            GameStat::containerPikis.add(color, 480);
            GameStat::update();
            Vector3f nearNavi = mNavi->mSRT.t;
            nearNavi.x += 100.0f;
            victim->resetPosition(nearNavi);
            victim->mHealth = 0;
            prepared = true;
            std::puts("[Pikmin Randomizer] TEST_ONLY collection_stock=480 field=20");
        }
        if (prepared && !delivered && victim->mPellet && victim->mDeadState == 2) {
            if (pc_randomizer_checked("Bestiary: Deliver Dwarf Bulborb")) std::abort();
            onion->suckMe(victim->mPellet); // Exercise real Onion callback, not carrying physics.
            if (!pc_randomizer_checked("Bestiary: Deliver Dwarf Bulborb")) std::abort();
            if (!pc_randomizer_checked("Population: 500 total Pikmin") || pc_randomizer_field_capacity() != 20) std::abort();
            delivered = true;
            std::puts("[Pikmin Randomizer] TEST_ONLY corpse_delivered_after_death_no_kill_check");
        }
    }
    if (scripted && !std::strcmp(scripted, "save") && background && !std::strcmp(background, "1") && bbftRedsReady) {
        static bool tested = false;
        if (!tested) {
            tested = true;
            PlayerState* originalPlayer = playerState;
            auto* originalCache = generatorCache;
            static u8 originalData[CARD_DATA_SIZE];
            std::memcpy(originalData, cardData, CARD_DATA_SIZE);
            const int invalidSlots[] = {0, 5, 255};
            for (int slot : invalidSlots) {
                gameflow.mGamePrefs.mSpareMemCardSaveIndex = slot;
                gameflow.mMemoryCard.saveCurrentGame();
                if (!gameflow.mMemoryCard.didSaveFail() || playerState != originalPlayer || generatorCache != originalCache
                    || std::memcmp(originalData, cardData, CARD_DATA_SIZE)) std::abort();
            }
            std::puts("[Pikmin Randomizer] TEST_ONLY invalid_save_slots_rejected");
            gameflow.mMemoryCard.getMemoryCardState(true);
            gameflow.mMemoryCard.makeDefaultFile();
            while (!gameflow.mMemoryCard.hasCardFinished()) OSYieldThread();
            gameflow.mMemoryCard.getMemoryCardState(true);
            gameflow.mPlayState.mSaveSlot = 0;
            gameflow.mGamePrefs.mMemCardSaveIndex = 0;
            gameflow.mGamePrefs.mSpareMemCardSaveIndex = 4;
            gameflow.mMemoryCard.saveCurrentGame();
            if (gameflow.mMemoryCard.didSaveFail() || playerState != originalPlayer || generatorCache != originalCache) std::abort();
            if (gameflow.mGamePrefs.mSpareMemCardSaveIndex < 1 || gameflow.mGamePrefs.mSpareMemCardSaveIndex > 4
                || gameflow.mGamePrefs.mSpareMemCardSaveIndex == gameflow.mGamePrefs.mMemCardSaveIndex) std::abort();
            gameflow.mMemoryCard.saveCurrentGame();
            if (gameflow.mMemoryCard.didSaveFail() || playerState != originalPlayer || generatorCache != originalCache) std::abort();
            CardQuickInfo infos[4];
            gameflow.mMemoryCard.getQuickInfos(infos);
            if (infos[0].mCurrentDay != gameflow.mWorldClock.mCurrentDay || infos[0].mSaveStatus != PlayState::ReadyToSave) std::abort();
            std::puts("[Pikmin Randomizer] TEST_ONLY native_save_written_and_read_back consecutive=2");
        }
    }
    if (pc_randomizer_enabled() && scripted && !std::strcmp(scripted, "permanent")
        && background && !std::strcmp(background, "1") && bbftRedsReady
        && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
        static int phase = 0;
        if (phase == 0 || (phase == 1 && pc_randomizer_repairs() >= 1)) {
            const bool full = phase == 1;
            auto change = [full](Creature* obj, int kind) {
                if (!obj || !obj->mGenerator) return;
                if (kind == 0) {
                    BuildingItem* wall = static_cast<BuildingItem*>(obj);
                    wall->mCurrStage = wall->mNumStages - (full ? 0 : 1);
                } else if (kind == 1) obj->mHealth = obj->mMaxHealth - (full ? 0.0f : 1.0f);
                else if (kind == 2) {
                    Bridge* bridge = static_cast<Bridge*>(obj);
                    for (int i = 0; i < bridge->getStage(); ++i) {
                        const bool done = full || (i == 0 && bridge->getStage() > 1);
                        bridge->mStageProgressList[i] = done ? bridge->mMaxHealth : 0.0f;
                        bridge->setStageFinished(i, done);
                    }
                } else static_cast<HinderRock*>(obj)->mState = full ? 2 : 0;
                if (full) {
                    char buffer[4096] = {};
                    RamStream stream(buffer, sizeof(buffer));
                    obj->doSave(stream); stream.setPosition(0); obj->doLoad(stream);
                }
            };
            Iterator items(itemMgr->mMeltingPotMgr);
            CI_LOOP(items) {
                Creature* obj = *items;
                if (obj->isSluice()) change(obj, 0);
                else if (obj->mObjType == OBJTYPE_Kusa) change(obj, 1);
            }
            Iterator works(workObjectMgr);
            CI_LOOP(works) {
                WorkObject* obj = static_cast<WorkObject*>(*works);
                if (obj->isBridge()) change(obj, 2);
                else if (obj->isHinderRock()) change(obj, 3);
            }
            ++phase;
            std::puts(full ? "[Pikmin Randomizer] TEST_ONLY permanent_complete_loaded" : "[Pikmin Randomizer] TEST_ONLY permanent_partial_ready");
        }
    }
    if (pc_randomizer_ready() && scripted && !std::strcmp(scripted, "work-damage")
        && background && !std::strcmp(background, "1") && bbftRedsReady
        && pc_bbft_color_access(Blue) && pc_bbft_color_access(Yellow)
        && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive)
        pc_randomizer_test_work_damage();
    if (pc_randomizer_color_stats() && scripted && !std::strcmp(scripted, "progressive-stats")
        && background && !std::strcmp(background, "1") && bbftRedsReady
        && pc_bbft_color_access(Blue) && pc_bbft_color_access(Yellow)
        && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
        static bool baseline = false;
        if (!baseline) {
            if (pc_randomizer_carry_strength(Red) != 1 || pc_randomizer_color_multiplier(Red, PC_PIKI_DAMAGE) != 1.0f) std::abort();
            std::puts("[Pikmin Randomizer] TEST_ONLY progressive_baseline_live");
            baseline = true;
        }
        if (pc_randomizer_carry_strength(Red) == 3 && pc_randomizer_carry_strength(Blue) == 2)
            pc_randomizer_test_color_stats();
    }
    if (pc_randomizer_color_stats() && scripted && !std::strcmp(scripted, "stats")
        && background && !std::strcmp(background, "1") && bbftRedsReady
        && pc_bbft_color_access(Blue) && pc_bbft_color_access(Yellow)
        && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive)
        pc_randomizer_test_color_stats();
    if (pc_randomizer_expanded() && scripted && !std::strcmp(scripted, "capacity")
        && background && !std::strcmp(background, "1") && bbftRedsReady
        && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
        static bool supplied = false, killed = false;
        static int lastCapacity = -1, lastField = -1;
        GoalItem* onion = itemMgr->getContainer(Red);
        if (onion && !supplied) {
            pikiInfMgr.mPikiCounts[Red][Leaf] += 80;
            onion->mHeldPikis[Leaf] += 80;
            GameStat::containerPikis.add(Red, 80);
            playerState->mTotalBornPikiNum += 80;
            playerState->mLivingPikiNum += 80;
            GameStat::update(); supplied = true;
            std::puts("[Pikmin Randomizer] TEST_ONLY stock=80");
        }
        const int capacity = pc_randomizer_field_capacity();
        if (onion && lastCapacity != capacity) {
            onion->exitPikis(100); // Deliberately too many: exercise the real queue clamp.
            std::printf("[Pikmin Randomizer] TEST_WITHDRAW cap=%d queued=%d\n", capacity, itemMgr->getContainerExitCount());
            lastCapacity = capacity;
        }
        const int field = int(GameStat::formationPikis) + int(GameStat::freePikis) + int(GameStat::workPikis);
        if (field != lastField) {
            std::printf("[Pikmin Randomizer] TEST_FIELD actual=%d cap=%d\n", field, capacity);
            lastField = field;
        }
        if (!killed && tekiMgr) {
            Iterator it(tekiMgr);
            CI_LOOP(it) {
                Teki* enemy = (Teki*)*it;
                if (enemy->mTekiType == TEKI_Chappy && enemy->mHealth > 0) {
                    enemy->mHealth = 0; // Let native AI perform its death lifecycle.
                    killed = true;
                    std::puts("[Pikmin Randomizer] TEST_ONLY dwarf_health=0");
                    break;
                }
            }
        }
    }
#endif
    static bool bbftReady = false;
    if (!bbftReady && pc_bbft_enabled() && !gameflow.mMoviePlayer->mIsActive
        && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive && mNavi && mMapMgr) {
        pc_bbft_milestone("PIKMIN_GAMEPLAY_READY");
        bbftReady = true;
    }
	STACK_PAD_VAR(2);
#if defined(PIKI_PC_PORT)
	// Photo mode. This lives in updateAI rather than in update() because
	// update() is reached through Node::update(), and newPikiGame guards that
	// call with
	//     if (!gameflow.mPauseAll && !gameflow.mIsUIOverlayActive)
	// -- the very flags photo mode raises. Putting the toggle there killed the
	// code that reads it, so the mode could be entered and never left.
	// updateAI is called outside that guard and keeps running while frozen.
	//
	// The toggle is ignored during a cutscene: the movie player drives the
	// camera itself, and fighting it would only produce a mess.
	//
	// The camera is driven through NCamera's own viewpoint/watchpoint pair
	// rather than by writing Camera::mPosition afterwards. makeMatrix() is what
	// builds mLookAtMtx, and that matrix is what the renderer actually uses --
	// setting mPosition after update() changes the reported position without
	// moving the view at all.
	if (!gameflow.mMoviePlayer->mIsActive && pc_photo_mode_poll_toggle()) {
		PcamCamera* pcam = cameraMgr->mCamera;
		if (pc_photo_mode_active()) {
			pc_photo_mode_exit();
			gameflow.mPauseAll          = sPhotoModeSavedPauseAll;
			gameflow.mIsUIOverlayActive = sPhotoModeSavedOverlay;
			if (pcam) {
				pcam->mRotationAngle = sPhotoModeSavedRoll;
			}
		} else if (pcam) {
			sPhotoModeSavedPauseAll = gameflow.mPauseAll;
			sPhotoModeSavedOverlay  = gameflow.mIsUIOverlayActive;
			sPhotoModeSavedRoll     = pcam->mRotationAngle;
			// mPauseAll freezes every manager; mIsUIOverlayActive is what holds
			// the captain and the day clock. Both, or the world is only half
			// still.
			gameflow.mPauseAll          = TRUE;
			gameflow.mIsUIOverlayActive = TRUE;

			// Carry on from wherever the gameplay camera was, so entering photo
			// mode does not snap the view somewhere else.
			Vector3f eye, look;
			pcam->getViewpoint().output(eye);
			pcam->getWatchpoint().output(look);
			Vector3f dir(look.x - eye.x, look.y - eye.y, look.z - eye.z);
			f32 pitch = 0.0f, yaw = 0.0f;
			pc_photo_mode_angles_from_forward(dir.x, dir.y, dir.z, &pitch, &yaw);
			pc_photo_mode_enter(eye.x, eye.y, eye.z, pitch, yaw);
		}
	}

	if (pc_photo_mode_active()) {
		PcamCamera* pcam = cameraMgr->mCamera;
		if (pcam) {
			f32 px = 0.0f, py = 0.0f, pz = 0.0f, pitch = 0.0f, yaw = 0.0f, roll = 0.0f;
			pc_photo_mode_update(gsys->getFrameTime(), &px, &py, &pz, &pitch, &yaw, &roll);

			f32 fx = 0.0f, fy = 0.0f, fz = 0.0f;
			pc_photo_mode_forward_vector(pitch, yaw, &fx, &fy, &fz);

			// The watchpoint is a point along the look direction. Its distance
			// only has to be far enough not to lose precision in the look-at.
			const f32 kLookDistance = 100.0f;
			Vector3f eye(px, py, pz);
			Vector3f look(px + fx * kLookDistance, py + fy * kLookDistance, pz + fz * kLookDistance);

			pcam->inputViewpoint(eye);
			pcam->inputWatchpoint(look);
			// makeMatrix rolls the up vector about the look axis by this, which
			// is where the tilt actually comes from -- Camera::mRotation.z is
			// not read by anything.
			pcam->mRotationAngle = roll;
			pcam->makeMatrix();
			pcam->makeCamera();
		}
	}

	// Where depth of field focuses: on the captain, every frame.
	//
	// The distance handed over is measured along the camera's forward axis,
	// not the straight line to him. The shader compares it against the depth
	// buffer, and that buffer holds view depth -- the distance to the plane
	// through the camera, not to the camera itself. Using the straight line
	// would put the focus slightly too far away, and increasingly so the
	// further the captain sits from the centre of the screen.
	{
		PcamCamera* pcam = cameraMgr ? cameraMgr->mCamera : nullptr;
		Navi* navi       = naviMgr ? naviMgr->getNavi() : nullptr;
		f32 focus        = 0.0f;
		// Not during a cutscene. The camera goes wherever the scene wants it and
		// the captain is often not in the shot at all, so his distance stops
		// describing anything on screen: the whole frame ends up outside the
		// sharp band, which is what put Olimar out of focus in his own close-up.
		const bool inCutscene = gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive;
		if (pcam && navi && !inCutscene) {
			Vector3f eye, look;
			pcam->getViewpoint().output(eye);
			pcam->getWatchpoint().output(look);
			Vector3f forward(look.x - eye.x, look.y - eye.y, look.z - eye.z);
			const f32 len = std::sqrt(forward.x * forward.x + forward.y * forward.y
			                          + forward.z * forward.z);
			if (len > 1e-4f) {
				forward.x /= len;
				forward.y /= len;
				forward.z /= len;
				const Vector3f& p = navi->mSRT.t;
				focus = (p.x - eye.x) * forward.x + (p.y - eye.y) * forward.y
				      + (p.z - eye.z) * forward.z;
			}
		}
		// A captain behind the camera gives a negative projection, which is not
		// a focus distance at all. Zero stands the effect down for the frame
		// rather than blurring the whole screen around a nonsense plane.
		pc_gfx_set_dof_focus(focus > 0.0f ? focus : 0.0f);
	}
#endif

	int pikis = GameStat::mapPikis;
	if (pikis > 50) {
		if (AIPerf::optLevel != 2)
			PRINT("________________________________________ opt level 2!\n");
		AIPerf::optLevel = 2;
	} else if (pikis > 30) {
		if (AIPerf::optLevel != 1)
			PRINT("________________________________________ opt level 1!\n");
		AIPerf::optLevel = 1;
	} else {
		if (AIPerf::optLevel != 0)
			PRINT("________________________________________ opt level 0!\n");
		AIPerf::optLevel = 0;
	}

	if (textDemoState != 0) {
		updateTextDemo();
		return;
	}

	attentionCamera->update();

	int start     = playerState->getStartHour();       // 7am
	int dayLength = playerState->getEndHour() - start; // 12 hrs

	int timeQuarter1 = start + (dayLength / 4);     // 10am
	int timeQuarter2 = start + (dayLength / 2);     // 1pm
	int timeQuarter3 = start + (dayLength / 4) * 3; // 4pm

	if (!mIsTimePastQuarter1 && gameflow.mWorldClock.mCurrentGameHour >= timeQuarter1) {
		// play first quarter bell
		mIsTimePastQuarter1 = true;
		seSystem->playSysSe(SYSSE_TIME_SMALLSIGNAL);
	} else if (!mIsTimePastNoon && gameflow.mWorldClock.mCurrentGameHour >= timeQuarter2) {
		// play "noon" (second quarter) bell (at 1pm, go figure)
		mIsTimePastNoon = true;
		seSystem->playSysSe(SYSSE_TIME_SIGNAL);
		if (!playerState->mDemoFlags.isFlag(DEMOFLAG_FirstNoon)) {
			playerState->mDemoFlags.setFlagOnly(DEMOFLAG_FirstNoon);
			gameflow.mGameInterface->message(MOVIECMD_TextDemo, zen::ogScrTutorialMgr::TUT_InfoDisplay);
		}
	} else if (!mIsTimePastQuarter3 && gameflow.mWorldClock.mCurrentGameHour >= timeQuarter3) {
		// play third quarter bell
		mIsTimePastQuarter3 = true;
		seSystem->playSysSe(SYSSE_TIME_SMALLSIGNAL);
	}

	gsys->mTimer->start("GameCore", true);
	AIPerf::clearCounts();
	pikiUpdateMgr->update();
	searchUpdateMgr->update();
	pikiLookUpdateMgr->update();
	pikiOptUpdateMgr->update();
	tekiOptUpdateMgr->update();
	mMapMgr->update();
	if (!gameflow.mIsUIOverlayActive) {
		naviMgr->update();
	}

	if (!gameflow.mIsUIOverlayActive) {
		if (tekiMgr) {
			gsys->mTimer->start("search", true);
			if (AIPerf::insQuick) {
				naviMgr->invalidateSearch();
				pikiMgr->invalidateSearch();
				if (tekiMgr) {
					tekiMgr->invalidateSearch();
				}
				if (bossMgr) {
					bossMgr->invalidateSearch();
				}
				itemMgr->invalidateSearch();
				plantMgr->invalidateSearch();
				workObjectMgr->invalidateSearch();
				itemMgr->mMeltingPotMgr->invalidateSearch();
				mSearchSystem->update();
			} else {
				mSearchSystem->update();
			}
			gsys->mTimer->stop("search");
		}

		if (!gameflow.mPauseAll) {
			if (!inPause() && bossMgr) {
				if (!hideTeki()) {
					bossMgr->update();
				}
			}

			gsys->mTimer->start("ai", true);
			if (!inPause()) {
				pikiMgr->update();
			}
			gsys->mTimer->stop("ai");
			itemMgr->update();
			if (!inPause()) {
				workObjectMgr->update();
				plantMgr->update();
				gsys->mTimer->start("teki", true);
				if (tekiMgr && !gameflow.mMoviePlayer->mIsActive) {
					tekiMgr->update();
				}
				gsys->mTimer->stop("teki");
				pelletMgr->update();
			}
		}
	}
	if (tekiMgr) {
		f32 deltaTime = gsys->getFrameTime();
		MATCHING_START_TIMER("post", true);
		if (!gameflow.mIsUIOverlayActive) {
			naviMgr->postUpdate(0, deltaTime);
		}

		if (!gameflow.mIsUIOverlayActive && !inPause() && !gameflow.mPauseAll) {
			pikiMgr->postUpdate(0, deltaTime);
			itemMgr->postUpdate(0, deltaTime);
			pelletMgr->postUpdate(0, deltaTime);
			plantMgr->postUpdate(0, deltaTime);
			if (tekiMgr && !hideTeki()) {
				tekiMgr->postUpdate(0, deltaTime);
			}
			if (bossMgr && !hideTeki()) {
				bossMgr->postUpdate(0, deltaTime);
			}
		}
		MATCHING_STOP_TIMER("post");
#if defined(BUGFIX)
#else
		gsys->mTimer->stop("GameCore");
#endif
	}
	// Wrong scope, Kando.
#if defined(BUGFIX)
	gsys->mTimer->stop("GameCore");
#endif
}

/**
 * @todo: Documentation
 */
void GameCoreSection::draw(Graphics& gfx)
{
	gfx.mCamera->mProjectionMatrix = gfx.mCamera->mPerspectiveMatrix;
	gfx.mCamera->mProjectionMatrix.multiply(gfx.mCamera->mLookAtMtx);
	bool advanceState = true;
#if defined(PIKI_PC_PORT)
	advanceState = pc_render_is_authoritative();
#endif
	gsys->mTimer->start("se updt", true);
	if (advanceState && gameflow.mMoviePlayer->mIsActive) {
		Vector3f pos;
		gameflow.mMoviePlayer->getLookAtPos(pos);
		seSystem->update(gfx, pos);
	} else if (advanceState) {
		seSystem->update(gfx, mNavi->mSRT.t);
	}
	gsys->mTimer->stop("se updt");

	gfx.useMatrix(Matrix4f::ident, 0);
	gfx.calcLighting(1.0f);
	if (mDrawHideType != 8) {
		mMapMgr->refresh(gfx);
	}
	mMapMgr->mDayMgr->setFog(gfx, nullptr);

	if (!AIPerf::generatorMode) {
		if (mDrawHideType != 2 && tekiMgr && !hideTeki()) {
			tekiMgr->refresh(gfx);
		}
		gsys->mTimer->start("piki draw", true);
		if (mDrawHideType != 1) {
			pikiMgr->refresh(gfx);
		}
		gsys->mTimer->stop("piki draw");
	}

	gameflow.mMoviePlayer->refresh(gfx);
	naviMgr->refresh(gfx);

	if (!AIPerf::generatorMode && mDrawHideType != 4 && bossMgr && !hideTeki()) {
		bossMgr->refresh(gfx);
	}

	if (mDrawHideType != 3) {
		itemMgr->refresh(gfx);
	}

	if (mDrawHideType != 6) {
		workObjectMgr->refresh(gfx);
	}

	if (!AIPerf::generatorMode) {
		if (mDrawHideType != 5) {
			pelletMgr->refresh(gfx);
		}

		if (mDrawHideType != 7) {
			plantMgr->refresh(gfx);
		}
	}

	// This code snippet is imitating a development feature that exists in the
	// DLLs, but this might not be where the equivalent code from the DLL exists.
	// TODO: Figure that out.
#ifdef DEVELOP
	generatorMgr->render(gfx);
	plantGeneratorMgr->render(gfx);
	dailyGeneratorMgr->render(gfx);
	onceGeneratorMgr->render(gfx);
	for (GeneratorMgr* limitGenChild = (GeneratorMgr*)limitGeneratorMgr->Child(); limitGenChild;
	     limitGenChild               = (GeneratorMgr*)limitGenChild->Child()) {
		limitGenChild->render(gfx);
	}
#endif

	naviMgr->renderCircle(gfx);
	mMapMgr->drawXLU(gfx);
	MATCHING_START_TIMER("shadow draw", true);
	mMapMgr->mDayMgr->setFog(gfx, stack_new(Colour)(0, 0, 0, 0));
	Matrix4f mtx;
	gfx.calcViewMatrix(Matrix4f::ident, mtx);
	gfx.useMatrix(mtx, 0);
	int blend = gfx.setCBlending(BLEND_Subtractive);
	gfx.setDepth(false);
	gfx.setLighting(false, nullptr);
	gfx.useTexture(mShadowTexture, GX_TEXMAP0);
	gfx.setColour(Colour(255, 255, 255, 128), true);
	if (AIPerf::optLevel <= 1) {
		pikiMgr->drawShadow(gfx, mShadowTexture);
	}
	itemMgr->drawShadow(gfx, mShadowTexture);
	pelletMgr->drawShadow(gfx, mShadowTexture);
	if (tekiMgr && !hideTeki()) {
		tekiMgr->drawShadow(gfx, mShadowTexture);
	}
	naviMgr->drawShadow(gfx);

	gfx.setCBlending(blend);
	gfx.setDepth(true);
	MATCHING_STOP_TIMER("shadow draw");
	mMapMgr->postrefresh(gfx);
    static bool bbftWorldDrawn = false;
    if (!bbftWorldDrawn && pc_bbft_enabled()) {
        pc_bbft_milestone("PIKMIN_WORLD_RENDERED");
        bbftWorldDrawn = true;
    }
	if (AIPerf::soundDebug) {
		seSystem->draw3d(gfx);
	}
	Node::draw(gfx);
	if (AIPerf::showRoute) {
		routeMgr->refresh(gfx);
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000374
 */
void drawRectangle(Graphics& gfx, RectArea& p2, RectArea& p3, Vector3f* p4)
{
	// we need the magic int-to-float conversion value to generate before the 1.0f
	// in draw2D, so here makes sense.
	p4->z = p2.mMaxX;
}

/**
 * @todo: Documentation
 */
void GameCoreSection::draw1D(Graphics& gfx)
{
	if (mDrawHideType == 9) {
		return;
	}

	Matrix4f orthoMtx;
	gfx.setOrthogonal(orthoMtx.mMtx, AREA_FULL_SCREEN(gfx));

	if (!AIPerf::generatorMode) {
		if (bossMgr && !hideTeki()) {
			bossMgr->refresh2d(gfx);
		}
		if (tekiMgr && !hideTeki()) {
			tekiMgr->refresh2d(gfx);
		}
	}
	naviMgr->refresh2d(gfx);

	if (gsys->mToggleDebugExtra) {
		gfx.setColour(COLOUR_WHITE, true);
		gfx.setAuxColour(COLOUR_WHITE);
		gfx.useTexture(nullptr, GX_TEXMAP0);
		char str[PATH_MAX];
		sprintf(str, "culled:ai %d view %d/%d shape %d (%d tekis)", AIPerf::aiCullCnt, AIPerf::viewCullCnt, AIPerf::outsideViewCnt,
		        AIPerf::drawshapeCullCnt, tekiMgr ? tekiMgr->getSize() : 0);
		gfx.texturePrintf(gsys->mConsFont, 60, 90, str);
	}

	attentionCamera->refresh(gfx);
	pelletMgr->refresh2d(gfx);
	itemMgr->refresh2d(gfx);
}

/**
 * @todo: Documentation
 */
void GameCoreSection::draw2D(Graphics& gfx)
{
	static immut char* triNames[] = {
		"", "HIDE PIKI", "HIDE TEKI", "HIDE ITEM", "HIDE BOSS", "HIDE PELLET", "HIDE WORK", "HIDE PLANTS", "HIDE MAP", "HIDE 2D",
	};
	Matrix4f orthoMtx;
	gfx.setOrthogonal(orthoMtx.mMtx, AREA_FULL_SCREEN(gfx));
	gfx.setColour(COLOUR_WHITE, true);
	gfx.setAuxColour(COLOUR_WHITE);
	gfx.useTexture(nullptr, GX_TEXMAP0);
	gfx.texturePrintf(gsys->mConsFont, 60, 120, triNames[mDrawHideType]);

	if (AIPerf::soundDebug) {
		seSystem->draw2d(gfx);
	}

	if (AIPerf::moveType != 0) {
		gfx.useTexture(mMapMgr->mBlurResultTexture, GX_TEXMAP0);
		GXSetTevSwapModeTable(GX_TEV_SWAP0, GX_CH_RED, GX_CH_GREEN, GX_CH_BLUE, GX_CH_ALPHA);
		GXSetTevSwapModeTable(GX_TEV_SWAP1, GX_CH_RED, GX_CH_RED, GX_CH_RED, GX_CH_ALPHA);
		GXSetTevSwapModeTable(GX_TEV_SWAP2, GX_CH_RED, GX_CH_RED, GX_CH_RED, GX_CH_ALPHA);
		GXSetTevSwapModeTable(GX_TEV_SWAP3, GX_CH_RED, GX_CH_RED, GX_CH_RED, GX_CH_ALPHA);

		GXSetNumTevStages(4);
		GXSetTevOrder(GX_TEVSTAGE0, GX_TEXCOORD0, GX_TEXMAP0, GX_COLOR0A0);
		GXSetTevOrder(GX_TEVSTAGE1, GX_TEXCOORD0, GX_TEXMAP0, GX_COLOR0A0);
		GXSetTevOrder(GX_TEVSTAGE2, GX_TEXCOORD0, GX_TEXMAP0, GX_COLOR0A0);
		GXSetTevOrder(GX_TEVSTAGE3, GX_TEXCOORD0, GX_TEXMAP0, GX_COLOR0A0);

		GXSetTevSwapMode(GX_TEVSTAGE0, GX_TEV_SWAP1, GX_TEV_SWAP1);
		GXSetTevColorIn(GX_TEVSTAGE0, GX_CC_ZERO, GX_CC_ZERO, GX_CC_ZERO, GX_CC_TEXC);
		GXSetTevAlphaIn(GX_TEVSTAGE0, GX_CA_ZERO, GX_CA_ZERO, GX_CA_ZERO, GX_CA_KONST);
		GXSetTevColorOp(GX_TEVSTAGE0, GX_TEV_ADD, GX_TB_ZERO, GX_CS_SCALE_1, GX_TRUE, GX_TEVPREV);
		GXSetTevAlphaOp(GX_TEVSTAGE0, GX_TEV_ADD, GX_TB_ZERO, GX_CS_SCALE_1, GX_TRUE, GX_TEVPREV);

		GXSetTevSwapMode(GX_TEVSTAGE1, GX_TEV_SWAP2, GX_TEV_SWAP2);
		GXSetTevColorIn(GX_TEVSTAGE1, GX_CC_CPREV, GX_CC_ZERO, GX_CC_ZERO, GX_CC_TEXC);
		GXSetTevAlphaIn(GX_TEVSTAGE1, GX_CA_ZERO, GX_CA_ZERO, GX_CA_ZERO, GX_CA_KONST);
		GXSetTevColorOp(GX_TEVSTAGE1, GX_TEV_COMP_RGB8_GT, GX_TB_ZERO, GX_CS_SCALE_1, GX_TRUE, GX_TEVPREV);

		GXSetTevSwapMode(GX_TEVSTAGE2, GX_TEV_SWAP3, GX_TEV_SWAP3);
		GXSetTevColorIn(GX_TEVSTAGE2, GX_CC_CPREV, GX_CC_ZERO, GX_CC_ZERO, GX_CC_TEXC);
		GXSetTevAlphaIn(GX_TEVSTAGE2, GX_CA_ZERO, GX_CA_ZERO, GX_CA_ZERO, GX_CA_KONST);
		GXSetTevColorOp(GX_TEVSTAGE2, GX_TEV_COMP_RGB8_GT, GX_TB_ZERO, GX_CS_SCALE_1, GX_TRUE, GX_TEVPREV);
		static int timer = 1;
		GXColor color;
		timer   = 0;
		color.r = 220;
		color.g = 160;
		color.b = 160;
		color.a = 255;
		GXSetTevKColorSel(GX_TEVSTAGE3, GX_TEV_KCSEL_K0);
		GXSetTevKColor(GX_KCOLOR0, color);
		GXSetTevColorIn(GX_TEVSTAGE3, GX_CC_ZERO, GX_CC_CPREV, GX_CC_KONST, GX_CC_ZERO);
		GXSetTevAlphaIn(GX_TEVSTAGE3, GX_CA_ZERO, GX_CA_ZERO, GX_CA_ZERO, GX_CA_KONST);
		GXSetTevColorOp(GX_TEVSTAGE3, GX_TEV_ADD, GX_TB_ZERO, GX_CS_SCALE_1, GX_TRUE, GX_TEVPREV);

		f32 scale = 1.0f;
		gfx.drawRectangle(RectArea(0, 0, (f32)gfx.mScreenWidth * scale, (f32)gfx.mScreenHeight * scale),
		                  RectArea(0, 0, 0.5f * (f32)gfx.mScreenWidth, 0.5f * (f32)gfx.mScreenHeight), nullptr);

		GXSetTevSwapMode(GX_TEVSTAGE0, GX_TEV_SWAP0, GX_TEV_SWAP0);
		GXSetTevSwapMode(GX_TEVSTAGE1, GX_TEV_SWAP0, GX_TEV_SWAP0);
		GXSetTevSwapMode(GX_TEVSTAGE2, GX_TEV_SWAP0, GX_TEV_SWAP0);

	} else {
		Navi* navi      = naviMgr->getNavi();
		AState<Navi>* s = navi->getCurrState();
		int state       = s->getID();
		if (state != NAVISTATE_DemoSunset) {
			mDrawGameInfo->draw(gfx);
		}
		gfx.setOrthogonal(orthoMtx.mMtx, AREA_FULL_SCREEN(gfx));
		containerWindow->draw(gfx);
		if (!gameflow.mMoviePlayer->mIsActive && !gameflow.mIsUIOverlayActive) {
			hurryupWindow->draw(gfx);
		}
		accountWindow->draw(gfx);
	}

	// this function requires an UNGODLY amount of stack from inlines, plus some
	// from temps. ternaries in the stripped out PRINT function generate inline
	// stack. forgive my sins please, this combo lets it match.
	STACK_PAD_VAR(48);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 10);
	STACK_PAD_TERNARY(triNames, 9);
}
