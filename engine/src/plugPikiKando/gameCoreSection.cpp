#include "pc_p2_ship.h"
#include "pc_dev_console.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_purple.h"
#include "pc_p2_purple_motion.h"
#include "pc_p2_purple_flight.h"
#include "pc_p2_kurage_visual.h"
#if defined(PIKI_PC_PORT)
#include "netplay/pc_netplay_det.h"
#include "netplay/pc_netplay_present.h"
#include "timing/pc_render_phase.h"
#endif
#include "pc_p2_teki_lifetime.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_onikurage_teki.h"
#include "pc_p2_bombsarai_teki.h"
#include "pc_p2_groink_teki.h"
#include "pc_p2_breadbug_teki.h"
#include "pc_p2_bigtreasure_teki.h"
#include "pc_p2_king_teki.h"
#include "pc_p2_queen_teki.h"
#if defined(PIKI_PC_PORT)
#include "pc_p2_demon_drop_state.h"
#include "pc_p2_demon_bridge.h"
#endif
#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)
#include "pc_randomizer_campaign_catalog.h"
#endif
#include "BuildingItem.h"
#include "CPlate.h"
#include "KusaItem.h"
#include "Generator.h"
#include "WorkObject.h"
#include "GameCoreSection.h"
#include "pc_bbft.h"
#include "pc_p2_preview.h"
#include "pc_p2_enemy.h"
#include "pc_p2_demon_host.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_cave.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_captain.h"
#include "pc_p2_second_captain.h"
#include "pc_p2_breadbug_visual.h"
#include "pc_p2_giant_breadbug_visual.h"
#include "pc_p2_giant_breadbug_actor.h"
#include "pc_p2_breadbug_actor.h"
#include "pc_p2_bulblax_visual.h"
#include "pc_p2_queen.h"
#include "pc_p2_king.h"
#include "pc_p2_dweevil.h"
#include "pc_p2_bombotakara.h"
#include "pc_p2_tank.h"
#include "pc_p2_hiba.h"
#include "pc_p2_flora_actor.h"
#include "pc_p2_pom.h"
#include "pc_p2_candypop.h"
#include "pc_p2_plant.h"
#include "pc_p2_tamago.h"
#include "pc_p2_hardlanes.h"
#include "pc_p2_projectiles.h"
#include "pc_p2_kabuto_fsm.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_long_legs.h"
#include "pc_randomizer.h"
#include "MapCode.h"
#include <fstream>
#if defined(PIKI_PC_PORT)
#include <SDL.h>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <cmath>
#include <algorithm>
#endif
#if defined(PIKI_PC_PORT)
#include "settings/pc_settings.h"
#if defined(PIKI_PC_PORT)
#include "pc_photo_mode.h"
#include "pc_p2_skewer_cam.h"
#include "pc_coop.h"
#include "netplay/pc_coop_switch.h"
#include "mods/pc_vs_arena.h"
#include "pc_vs.h"
#include "BuildingItem.h"
#include "PikiAI.h"
#include "ItemObject.h"
#include "UfoItem.h"
#include "TekiPersonality.h"
#include "teki.h"
#include <algorithm>
#include <vector>
#include "pc_window.h"
#include "gl/pc_gfx.h"
#endif
#endif

#include "AIConstant.h"
#include "AIPerf.h"
#include "BombItem.h"
#include "MizuItem.h"
#include "TekiPersonality.h"
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
#include "PelletState.h"
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
#if defined(__linux__) && !defined(__ANDROID__)
#include <execinfo.h>
#endif
void GameCoreSection::startPause(u16 pause)
{
	pauseFlag = pause;
	// Traza de depuración del coop (solo glibc: backtrace no existe en MinGW/bionic).
#if defined(__linux__) && !defined(__ANDROID__)
	if (getenv("PIKMIN_COOP_TRACE")) {
		fprintf(stderr, "[COOP] startPause(%04x)\n", pause);
		void* frames[8];
		int n = backtrace(frames, 8);
		backtrace_symbols_fd(frames, n, 2);
	}
#endif
}
#endif
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
#if defined(PIKI_PC_PORT)
zen::DrawContainer* containerWindow2 = nullptr;
#endif
zen::DrawHurryUp* hurryupWindow;
zen::DrawAccount* accountWindow;


// VS: sin escena de extinción (se empieza sin Pikmin en el campo).
#if defined(PIKI_PC_PORT)
#define PC_NOT_VS && !pc_vs_active()
#else
#define PC_NOT_VS
#endif
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

#if defined(PIKI_PC_PORT)
	// Cooperativo: los dos Olimar se congelan (DemoWait) durante el vídeo; el
	// que lo disparó (getMovieNavi) es el que la cinemática anima y mueve.
	for (int ni = 0; ni < naviMgr->getNaviCount(); ni++) {
	Navi* orima = naviMgr->getNavi(ni);
#else
	Navi* orima = naviMgr->getNavi();
#endif
	if (orima) {
		orima->mNaviLightEfx->changeEffect(EffectMgr::EFF_Navi_Light);
		orima->mNaviLightGlowEfx->changeEffect(EffectMgr::EFF_Navi_LightGlow);
		orima->applyPlayerLightTint();
		orima->mCursorTrailEfx->changeEffect(EffectMgr::EFF_Navi_LightGlow);
		orima->mCursorTrailEfx->scaleSize(kCursorTrailScale);
		orima->mCursorTrailEfx->setEmitting(false);
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
#if defined(PIKI_PC_PORT)
	}
#endif

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
#if defined(PIKI_PC_PORT)
	if (mNavi2) {
		mNavi2->mNaviLightEfx->restart();
		mNavi2->mNaviLightGlowEfx->restart();
	}
#endif
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
#if defined(PIKI_PC_PORT)
	// Issues #47/#48: la escena de fin de día termina después de exitStage(),
	// que ya ha puesto naviMgr a nullptr al desmontar la fase.
	if (naviMgr) {
		naviMgr->setMovieNavi(nullptr);
	}
#endif

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
            if (pc_p2_ship_special(piki)) { if (pc_p2_ship_deposit(piki)) ++entered; continue; }
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
						if (pc_p2_ship_special(piki)) { pc_p2_ship_deposit(piki); break; }
                        if (state == PIKISTATE_LookAt || state == PIKISTATE_Nukare || state == PIKISTATE_Absorb) {
							piki->mFSM->transit(piki, PIKISTATE_Normal);
						}
						piki->mFSM->transit(piki, PIKISTATE_Normal);
						navi->mGoalItem = itemMgr->getContainer(piki->mColor);
#if defined(PIKI_PC_PORT)
						// Co-op (#885 gap-fix K): the goal is on `navi` (P1), not on
						// the Pikmin's own captain; changeMode reads it from here.
						piki->changeMode(PikiMode::EnterMode, navi);
#else
						piki->changeMode(PikiMode::EnterMode, nullptr);
#endif
						goalSafe++;
						break;
					}

					UfoItem* ufo = itemMgr->getUfo();
					if (ufo) {
						Vector3f pos = ufo->getGoalPos();
						if (qdist2(pos.x, pos.z, piki->mSRT.t.x, piki->mSRT.t.z) <= pikiMgr->mPikiParms->mPikiParms.mSunsetSafetyRange()) {
							if (pc_p2_ship_special(piki)) { pc_p2_ship_deposit(piki); break; }
                        if (state == PIKISTATE_LookAt || state == PIKISTATE_Nukare || state == PIKISTATE_Absorb) {
								piki->mFSM->transit(piki, PIKISTATE_Normal);
							}
							piki->mFSM->transit(piki, PIKISTATE_Normal);
							navi->mGoalItem = itemMgr->getContainer(piki->mColor);
#if defined(PIKI_PC_PORT)
							piki->changeMode(PikiMode::EnterMode, navi); // #885 gap-fix K, as above
#else
							piki->changeMode(PikiMode::EnterMode, nullptr);
#endif
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
#if defined(PIKI_PC_PORT)
    if (bossMgr) bossMgr->endPrereleaseTrap();
#endif
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

#if defined(PIKI_PC_PORT)
	for (int ni = 0; ni < naviMgr->getNaviCount(); ni++) {
		if (Navi* navi = naviMgr->getNavi(ni)) {
			navi->mRippleEffect->kill();
		}
	}
#else
	if (naviMgr->getNavi()) {
		PRINT("********** KILL RIPPLE EFFECT****\n");
		Navi* navi = naviMgr->getNavi();
		navi->mRippleEffect->kill();
	}
#endif
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
    // The vanilla sunset safety pass above decides survivors. Store specials
    // before the Onion-only movie routing; they need no Red Onion actor.
    if (pc_randomizer_purple_campaign()) {
        Iterator survivors(pikiMgr);
        CI_LOOP(survivors) {
            Piki* piki = static_cast<Piki*>(*survivors);
            if (pc_p2_ship_special(piki) && piki->isAlive()) pc_p2_ship_deposit(piki);
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
#if defined(PIKI_PC_PORT)
	// Fin del día: los dos Olimar pasan al estado de vídeo.
	for (int ni = 0; ni < naviMgr->getNaviCount(); ni++) {
		Navi* navi = naviMgr->getNavi(ni);
		if (navi->getCurrState()->getID() == NAVISTATE_Dead) {
			continue; // caído: el cuerpo se queda durante el fin del día
		}
		navi->startMovieInf();
	}
#else
	naviMgr->getNavi()->startMovieInf();
#endif
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
#if defined(PIKI_PC_PORT)
	pc_demon_drop_scene_exit();
	pc_demon_scene_exit();
#endif
#if defined(PIKI_PC_PORT)
	// Stale focus would keep depth of field running on the file-select and
	// title screens: those frames have no HUD ortho, so the pass hits the UI.
	pc_gfx_set_dof_focus(0.0f);
	// Release while all stage creatures and managers are still valid.
	pc_p2_kurage_receiver_reset();
	pc_p2_kurage_teki_reset();
	pc_p2_onikurage_teki_reset();
	pc_p2_king_teki_reset();
	pc_p2_queen_teki_reset();
	pc_p2_kurage_visual_reset();
	// Actor-lifetime seam (#397/#186): clear every remaining P2 family
	// registration map so a finished stage cannot retain a stale BTeki* key
	// pointing into the TekiMgr that is about to be destroyed. Previously only
	// the kurage families were released here.
	pc_p2_purple_flight_reset(); // Restore live Pikmin flags before the stage heap is released.
	pc_p2_reset_all_teki();
#endif
	demoEventMgr = nullptr;
	// Lane 12 (#130): drop the live captain/squad binding before the NaviMgr and
	// stage-heap objects are destroyed, matching the shared lifetime seam.
	pc_p2_captain::teardown();
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
#if defined(PIKI_PC_PORT)
	// Fin de la partida (VS/cooperativo): la siguiente vuelve a leer lo pendiente.
	gameflow.mPauseAll = FALSE;
	pc_coop_end_run();
#endif
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
#if defined(PIKI_PC_PORT)
// ── VS: piezas ──────────────────────────────────────────────────────────────
// Se eligen entre las piezas de la nave del juego por lo que pesan (Pikmin
// mínimos para cargarlas): las tres más ligeras son las pequeñas, dos de
// entre 5 y 10 Pikmin las medianas y la más pesada la gorda. Cada pareja
// simétrica del mapa usa la misma pieza, así los dos cargan lo mismo.
static u32 sVsPieceIds[PC_VS_PIECE_KINDS];

static void pcVsChoosePieces()
{
	for (u32& id : sVsPieceIds) id = 0;
	pc_vs_set_missing_pieces(false);
	std::vector<PelletConfig*> parts;
	for (CoreNode* n = pelletMgr->pcFirstConfig(); n; n = n->mNext) {
		PelletConfig* c = static_cast<PelletConfig*>(n);
		if (c->mPelletType() == PELTYPE_UfoPart) parts.push_back(c);
	}
	if (parts.size() < PC_VS_PIECE_KINDS) {
		fprintf(stderr, "[VS] only %zu ship parts available\n", parts.size());
		pc_vs_set_missing_pieces(true);
		return;
	}
	std::stable_sort(parts.begin(), parts.end(), [](PelletConfig* a, PelletConfig* b) {
		if (a->mCarryMinPikis() != b->mCarryMinPikis()) return a->mCarryMinPikis() < b->mCarryMinPikis();
		return a->mCarryMaxPikis() < b->mCarryMaxPikis();
	});
	std::vector<bool> used(parts.size(), false);
	auto take = [&](size_t i, int kind, int points) {
		used[i]             = true;
		sVsPieceIds[kind]   = parts[i]->mPelletId.mId;
		pc_vs_set_piece_points(parts[i]->mPelletId.mId, points);
		fprintf(stderr, "[VS] piece kind %d = %s (carry %d-%d, %d pts)\n", kind, parts[i]->mPelletId.mStringID,
		        parts[i]->mCarryMinPikis(), parts[i]->mCarryMaxPikis(), points);
	};
	take(parts.size() - 1, PC_VS_PIECE_BIG, 5);
	for (int k = 0; k < 3; k++) take(k, PC_VS_PIECE_SMALL_A + k, 1);
	int medium = PC_VS_PIECE_GUARDED;
	for (size_t i = 0; i < parts.size() && medium <= PC_VS_PIECE_POND; i++) {
		if (!used[i] && parts[i]->mCarryMinPikis() >= 5 && parts[i]->mCarryMinPikis() <= 10) take(i, medium++, 2);
	}
	for (size_t i = 0; i < parts.size() && medium <= PC_VS_PIECE_POND; i++) {
		if (!used[i]) take(i, medium++, 2);
	}
}

static Pellet* pcVsSpawnPellet(MapMgr* map, u32 id, f32 x, f32 z)
{
	if (!id) return nullptr;
	Pellet* pellet = pelletMgr->newPellet(id, nullptr);
	if (!pellet) return nullptr;
	Vector3f pos(x, 0.0f, z);
	pos.y = map->getMinY(x, z, true);
	pellet->init(pos);
	pellet->startAI(0);
	return pellet;
}

// Reloj y eventos, cada fotograma de juego.
static void pcVsUpdate(MapMgr* map)
{
	const bool wasOver = pc_vs_match_over();
	pc_vs_match_update(gsys->getFrameTime());

	if (pc_vs_take_big_piece_event()) {
		Vector3f pos;
		pc_vs_arena_big_piece(pos);
		pcVsSpawnPellet(map, sVsPieceIds[PC_VS_PIECE_BIG], pos.x, pos.z);
		pc_vs_announce("BIG PIECE IN THE CRATER!", 4.0f);
	}
	if (pc_vs_take_pellet_event()) {
		// Solo si el sitio está libre, para que no se amontonen.
		PcVsPelletSpot spots[8];
		const int n = pc_vs_arena_pellet_spots(spots, 8);
		for (int i = 0; i < n; i++) {
			bool busy = false;
			Iterator it(pelletMgr);
			CI_LOOP(it)
			{
				Creature* c = *it;
				const f32 dx = c->mSRT.t.x - spots[i].x, dz = c->mSRT.t.z - spots[i].z;
				if (dx * dx + dz * dz < 80.0f * 80.0f) busy = true;
			}
			if (!busy) pcVsSpawnPellet(map, spots[i].pelletId, spots[i].x, spots[i].z);
		}
	}
	// Asedio: cada Pikmin rival libre junto a un cohete le quita vida y lo
	// golpea. Su IA libre se suspende mientras tanto (si no, vuelve a su
	// animación de espera cada fotograma) y se reanuda al dejar de asediar.
	const f32 dt = gsys->getFrameTime();
	int sieging[2] = { 0, 0 };
	int alive[2]   = { 0, 0 };
	const bool siegeOn = pc_vs_rules().rocketWin && !pc_vs_countdown_holding();
	UfoItem* ufos[2] = { itemMgr->pcGetUfo(0), itemMgr->pcGetUfo(1) };
	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* piki   = static_cast<Piki*>(*it);
		if (piki->isAlive() && (piki->mPlayerId == 0 || piki->mPlayerId == 1)) alive[piki->mPlayerId]++;
		const int target = 1 - piki->mPlayerId; // cohete rival
		bool siege   = siegeOn && !pc_vs_match_over() && piki->isAlive() && piki->mPlayerId >= 0 && ufos[target & 1]
		           && piki->mMode == PikiMode::FreeMode && piki->getState() == PIKISTATE_Normal;
		f32 dx = 0.0f, dz = 0.0f;
		if (siege) {
			dx    = ufos[target]->mSRT.t.x - piki->mSRT.t.x;
			dz    = ufos[target]->mSRT.t.z - piki->mSRT.t.z;
			siege = dx * dx + dz * dz <= PC_VS_SIEGE_RADIUS * PC_VS_SIEGE_RADIUS;
		}
		if (!siege) {
			if (piki->mPcSieging) {
				piki->mPcSieging                   = false;
				piki->mActiveAction->pcSetSuspended(false);
			}
			continue;
		}
		sieging[target]++;
		piki->mPcSieging                   = true;
		piki->mActiveAction->pcSetSuspended(true);
		piki->mFaceDirection               = atan2f(dx, dz);
		piki->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
		PaniPikiAnimator& upper = piki->mPikiAnimMgr.getUpperAnimator();
		// Job2: los golpes contra las compuertas.
		if (upper.getCurrentMotionIndex() != PIKIANIM_Job2 || upper.isFinished()) {
			piki->startMotion(PaniMotionInfo(PIKIANIM_Job2), PaniMotionInfo(PIKIANIM_Job2));
		}
	}
	// Refuerzos: un jugador sin ningún Pikmin (campo, brotes, cebollas) no
	// puede recuperarse; a los 3 s recibe 3 en cada una de sus cebollas.
	static int sVsSerial        = -1;
	static f32 sEmptyFor[2]     = { 0.0f, 0.0f };
	static f32 sReinforceCd[2]  = { 0.0f, 0.0f };
	if (sVsSerial != pc_vs_match_serial()) {
		sVsSerial = pc_vs_match_serial();
		sEmptyFor[0] = sEmptyFor[1] = sReinforceCd[0] = sReinforceCd[1] = 0.0f;
	}
	for (int player = 0; player < 2 && !pc_vs_match_over() && !pc_vs_countdown_holding(); player++) {
		if (sReinforceCd[player] > 0.0f) sReinforceCd[player] -= dt;
		if (pcVsFieldPikis(player) > 0) {
			sEmptyFor[player] = 0.0f;
			continue;
		}
		int stored = 0;
		for (int color = PikiMinColor; color < PikiColorCount; color++) {
			if (GoalItem* goal = itemMgr->pcGetContainer(color, player)) stored += goal->getTotalStorePikis();
		}
		if (stored > 0) {
			sEmptyFor[player] = 0.0f;
			continue;
		}
		sEmptyFor[player] += dt;
		if (sEmptyFor[player] < 3.0f || sReinforceCd[player] > 0.0f) continue;
		for (int color = PikiMinColor; color < PikiColorCount; color++) {
			GoalItem* goal = itemMgr->pcGetContainer(color, player);
			if (!goal) continue;
			for (int k = 0; k < 3; k++) {
				pikiInfMgr.incPiki(color, Leaf);
				goal->mHeldPikis[Leaf]++;
				GameStat::containerPikis.inc(color);
			}
		}
		GameStat::update();
		sEmptyFor[player]    = 0.0f;
		sReinforceCd[player] = 20.0f;
		SeSystem::playSysSe(SYSSE_CONTAINER_OK);
		pc_vs_announce(player == 0 ? "P1: REINFORCEMENTS IN YOUR ONIONS" : "P2: REINFORCEMENTS IN YOUR ONIONS", 4.0f);
	}

	// Daño fijo por Pikmin: con 20, la vida baja aguanta ~24 s, la normal
	// ~40 s y la alta ~60 s. Los dos a la vez: si caen en el mismo fotograma, empate.
	pc_vs_damage_rockets(sieging[0] * PC_VS_SIEGE_DPS * dt, sieging[1] * PC_VS_SIEGE_DPS * dt);
	for (int player = 0; player < 2; player++) pc_vs_set_alive(player, alive[player]);

	if (!wasOver && pc_vs_match_over()) {
		const int w = pc_vs_winner();
		const bool destroyed = pc_vs_rocket_hp(0) <= 0.0f || pc_vs_rocket_hp(1) <= 0.0f;
		const char* msg = w == 2 ? (destroyed ? "BOTH ROCKETS DESTROYED! DRAW" : "TIME! DRAW")
		                : destroyed ? (w == 0 ? "ROCKET DESTROYED! PLAYER 1 WINS" : "ROCKET DESTROYED! PLAYER 2 WINS")
		                            : (w == 0 ? "TIME! PLAYER 1 WINS" : "TIME! PLAYER 2 WINS");
		pc_vs_announce(msg, 600.0f);
	}
}

/// VS (fase 2): cada jugador recibe sus tres cebollas, 15 Pikmin (5 de cada
/// color) en su grupo, y aparecen las pastillas de prueba del mapa.
static void pcVsSetupBases(MapMgr* map)
{
	// Cuenta atrás 3, 2, 1, START con el mundo en pausa (la lleva el HUD).
	pc_vs_countdown_arm();
	if (pc_vs_missing_pieces()) pc_vs_announce("NO SHIP PARTS FOUND - CHECK GAME FILES", 60.0f);

	// Sin escenas de la historia: todas cuentan como ya vistas (descubrir
	// cebollas, primer motor, primeros amarillos/azules...). VS no guarda.
	for (int d = 0; d < DEMOFLAG_COUNT; d++) playerState->mDemoFlags.setFlagOnly(d);

	// Cebollas ya activas: sin la secuencia de despertar, listas desde el
	// principio y con su punto de camino abierto.
	for (int color = Blue; color <= Yellow; color++) {
		playerState->setContainer(color);
		playerState->setBootContainer(color);
	}
	for (int player = 0; player < 2; player++) {
		Navi* navi = naviMgr->getNavi(player);
		for (int color = Blue; color <= Yellow; color++) {
			Vector3f pos;
			pc_vs_arena_onion(player, color, pos);
			pos.y          = map->getMinY(pos.x, pos.z, true);
			GoalItem* goal = static_cast<GoalItem*>(itemMgr->birth(OBJTYPE_Goal));
			if (!goal) continue;
			goal->setColorType(color);
			goal->mPcOwner = player;
			goal->init(pos);
			goal->mFaceDirection = player == 0 ? 1.5707963f : -1.5707963f;
			goal->mSRT.r.set(0.0f, goal->mFaceDirection, 0.0f);
			goal->startAI(0);
			// startAI copia el recuento global de Pikmin guardados; en VS cada
			// cebolla tiene el suyo, y empieza vacía.
			goal->mHeldPikis[Leaf] = goal->mHeldPikis[Bud] = goal->mHeldPikis[Flower] = 0;

			// 5 Pikmin de este color en el grupo del capitán.
			for (int i = 0; navi && i < 5; i++) {
				Piki* piki = static_cast<Piki*>(pikiMgr->birth());
				if (!piki) break;
				GameStat::workPikis.inc(color);
				piki->init(navi);
				Vector3f at = navi->mSRT.t;
				at.x += (color - 1) * 25.0f;
				at.z += (i - 2) * 20.0f;
				at.y = map->getMinY(at.x, at.z, true);
				piki->Creature::init(at);
				piki->initColor(color);
				piki->mPlayerId = player;
				piki->changeMode(PikiMode::FormationMode, navi);
			}
		}
	}
	GameStat::update();

	PcVsPelletSpot spots[8];
	const int n = pc_vs_arena_pellet_spots(spots, 8);
	for (int i = 0; i < n; i++) {
		Pellet* pellet = pelletMgr->newPellet(spots[i].pelletId, nullptr);
		if (!pellet) continue;
		Vector3f pos(spots[i].x, 0.0f, spots[i].z);
		pos.y = map->getMinY(pos.x, pos.z, true);
		pellet->init(pos);
		pellet->startAI(0);
	}

	// Cohete de cada jugador: recibe las piezas.
	for (int player = 0; player < 2; player++) {
		Vector3f pos;
		f32 face;
		pc_vs_arena_rocket(player, pos, face);
		pos.y        = map->getMinY(pos.x, pos.z, true);
		UfoItem* ufo = static_cast<UfoItem*>(itemMgr->birth(OBJTYPE_Ufo));
		if (!ufo) continue;
		ufo->mPcOwner = player;
		ufo->init(pos);
		ufo->mFaceDirection = face;
		ufo->mSRT.r.set(0.0f, face, 0.0f);
		ufo->startAI(0);
	}

	// Piezas del principio (la gorda sale en el minuto 5).
	PcVsPieceSpot pieces[16];
	const int np = pc_vs_arena_piece_spots(pieces, 16);
	for (int i = 0; i < np; i++) {
		pcVsSpawnPellet(map, sVsPieceIds[pieces[i].kind], pieces[i].x, pieces[i].z);
	}

	// Compuerta de roca-bomba en cada base y un montón de bombas para abrirla.
	for (int player = 0; player < 2; player++) {
		Vector3f pos;
		f32 face;
		pc_vs_arena_gate(player, pos, face);
		pos.y = map->getMinY(pos.x, pos.z, true);
		if (BuildingItem* gate = static_cast<BuildingItem*>(itemMgr->birth(OBJTYPE_SluiceBomb))) {
			gate->mNumStages = 2;
			gate->init(pos);
			gate->mFaceDirection = face;
			gate->mSRT.r.set(0.0f, face, 0.0f);
			gate->startAI(0);
			// startAI no cierra el paso (solo lo hace al restaurar una partida):
			// cerrada, los caminos rodean por las salidas hasta que se rompa.
			if (gate->mWayPoint) gate->mWayPoint->setFlag(false);
		}
		pc_vs_arena_bomb_pile(player, pos);
		pos.y = map->getMinY(pos.x, pos.z, true);
		if (BombGenItem* pile = static_cast<BombGenItem*>(itemMgr->birth(OBJTYPE_BombGen))) {
			pile->init(pos);
			pile->startAI(0);
			pile->mCapacity = pile->mRemaining = 4;
			pile->mGrid.updateGrid(pile->mSRT.t);
		}
	}

	// Bulborbs grandes durmiendo junto a las medianas custodiadas.
	Vector3f guards[4];
	const int ng = pc_vs_arena_guard_spots(guards, 4);
	for (int i = 0; i < ng; i++) {
		Teki* teki = tekiMgr->newTeki(TEKI_Swallow);
		if (!teki) continue;
		TekiPersonality pers;
		pers.mPosition = guards[i];
		pers.mPosition.y = map->getMinY(guards[i].x, guards[i].z, true);
		pers.mNestPosition  = pers.mPosition;
		pers.mFaceDirection = i == 0 ? 1.5707963f : -1.5707963f;
		pers.setF(TekiPersonality::FLT_TerritoryRange, 250.0f);
		teki->mPersonality->input(pers);
		teki->reset();
		teki->startAI(0);
		teki->mSRT.r.set(0.0f, pers.mFaceDirection, 0.0f);
	}
}
#endif

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
#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)
	// lane-03 (#439): room generator-cache resume. Load the serialized cache
	// written by a prior PIKMIN_P2_CACHE_SAVE boot, then preload keyed by the
	// room's mStageID (STAGE_Practice = 0; the stage-list mStageIndex for chal0
	// has no GeneratorCache entry). The ramMode Generator::read here restores the
	// SLT1 spawn-slot uid that ordinary birth then re-resolves.
	if (pc_pikipelago_room_preview() && std::getenv("PIKMIN_P2_CACHE_RESUME")) {
		std::ifstream in("p2-gencache.bin", std::ios::binary | std::ios::ate);
		if (in) {
			std::streamsize size = in.tellg();
			in.seekg(0);
			static char card[0x8000];
			if (size > 0 && size <= (std::streamsize)sizeof(card)) {
				in.read(card, size);
				RamStream stream(card, static_cast<int>(size));
				generatorCache->loadCard(stream);
			}
			std::printf("P2_GENCACHE_RESUME stage_id=%u bytes=%lld bridge=%d bindings=%u\n",
			            flowCont.mCurrentStage->mStageID, (long long)size,
			            int(pc_randomizer_p2_bridge()), pc_randomizer_p2_binding_count());
		}
	}
#endif
	const u32 genCacheStage =
#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)
		(pc_pikipelago_room_preview() && std::getenv("PIKMIN_P2_CACHE_RESUME"))
			? flowCont.mCurrentStage->mStageID : flowCont.mCurrentStage->mStageIndex;
#else
		flowCont.mCurrentStage->mStageIndex;
#endif
	const bool hasAuthoritativeStageCache = generatorCache->preload(genCacheStage);
#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)
	if (pc_pikipelago_room_preview() && std::getenv("PIKMIN_P2_CACHE_RESUME")) {
		Generator* g;
		FOREACH_NODE_REUSE(Generator, generatorList->mGenListHead->mChild, g) {
			std::printf("P2_GENCACHE_DUMP _70=%u uid=%u alive=%d day=%d ram=%d\n",
			            unsigned(g->_70), pc_randomizer_generator_id(g),
			            int(g->mAliveCount), int(g->mLatestSpawnDay), int(g->readFromRam()));
		}
	}
#endif
	memStat->end("genCache");
	PRINT("--------------- GeneratorCache : preload done\n");

	GameStat::init();

	memStat->start("initStage");
	flowCont.mIsVersusMode = FALSE;
	PRINT("initStage start\n");
#if defined(PIKI_PC_PORT)
	// El constructor ya lo activó para el VS; la línea de arriba lo apaga.
	flowCont.mIsVersusMode = pc_vs_active() ? TRUE : FALSE;
#endif
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
#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)
	// lane-03 (#439): on a room cache-resume boot, the generator list already
	// came from preload; skipping the default.gen disk read avoids duplicate
	// room actors binding the same _70.
	const bool resumeRoomCache = pc_pikipelago_room_preview() && std::getenv("PIKMIN_P2_CACHE_RESUME");
#else
	const bool resumeRoomCache = false;
#endif
	sprintf(path2, "%sdefault.gen", path);
	// On a room cache-resume boot, skip the disk default.gen entirely (the
	// generator list already came from GeneratorCache::preload); do not even
	// open the stream, so it is neither leaked nor double-read.
	RandomAccessStream* data = resumeRoomCache ? nullptr : gsys->openFile(path2);
	if (data) {
		PRINT("DEFAULT GEN LOADED **********************************\n");
		generatorMgr->read(*data, false);
		data->close();
		generatorMgr->updateUseList();
		useDefault = true;
	} else if (!resumeRoomCache) {
		PRINT("*** NO GENERATOR FILE\n");
		mNavi->mSRT.t.set(0.0f, 0.0f, 0.0f);
		mNavi->mDayEndPosition = mNavi->mSRT.t;
		mNavi->mFaceDirection  = 0.0f;
		mNavi->mSRT.r.set(0.0f, 0.0f, 0.0f);
	}
	mNavi->reset();
#if defined(PIKI_PC_PORT)
	if (mNavi2) {
		// P2 aparece al lado de P1, mirando hacia el mismo sitio.
		Vector3f side(cosf(mNavi->mFaceDirection), 0.0f, -sinf(mNavi->mFaceDirection));
		mNavi2->mSRT.t         = mNavi->mSRT.t + side * 30.0f;
		mNavi2->mLastPosition  = mNavi2->mSRT.t;
		mNavi2->mDayEndPosition = mNavi2->mSRT.t;
		mNavi2->mFaceDirection = mNavi->mFaceDirection;
		mNavi2->mSRT.r         = mNavi->mSRT.r;
		mNavi2->reset();
	}
#endif

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

#if defined(PIKI_PC_PORT)
	// VS: la arena no tiene .gen, así que las pastillas que pone el modo se
	// registran aquí para que se carguen sus modelos.
	if (pc_vs_active()) {
		pc_settings_apply_vs_rules(); // reglas del menú previo
		pc_vs_match_reset();
		PcVsPelletSpot spots[8];
		const int n = pc_vs_arena_pellet_spots(spots, 8);
		for (int i = 0; i < n; i++) pelletMgr->addUseList(spots[i].pelletId);
		pcVsChoosePieces();
		for (u32 id : sVsPieceIds) {
			if (id) pelletMgr->addUseList(id);
		}
		tekiMgr->mUsingType[TEKI_Swallow] = true; // Bulborbs custodios
		itemMgr->addUseList(OBJTYPE_SluiceBomb);   // compuertas de roca-bomba
	}
#endif
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
	if (pc_randomizer_progg_traps()) tekiMgr->mUsingType[TEKI_Dororo] = true;
	// #942 dev console: load the P1 host vehicles of every dev-bound species.
	pc_dev_console_reserve_host_types();
	tekiMgr->startStage();
	gsys->setHeap(oldT);
	memStat->end("teki");

	memStat->start("boss");
	int oldB = gsys->setHeap(SYSHEAP_Teki);
	if (pc_randomizer_prerelease_traps())
        bossMgr->addUseCount(BOSS_Spider, bossMgr->getUseCount(BOSS_Pom) + bossMgr->getUseCount(BOSS_Geyzer));
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
	generatorCache->load(genCacheStage);
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

#if defined(PIKI_PC_PORT)
	// VS: cada capitán empieza en su base de la arena (no hay .gen).
	if (pc_vs_active()) {
		for (int i = 0; i < 2; i++) {
			Navi* navi = naviMgr->getNavi(i);
			if (!navi) continue;
			Vector3f pos;
			f32 face;
			pc_vs_arena_base(i, pos, face);
			pos.y                  = mMapMgr->getMinY(pos.x, pos.z, true);
			navi->mSRT.t           = pos;
			navi->mLastPosition    = pos;
			navi->mDayEndPosition  = pos;
			navi->mFaceDirection   = face;
			navi->mSRT.r.set(0.0f, face, 0.0f);
		}
		pcVsSetupBases(mMapMgr);
	}
#endif
	attentionCamera = new AttentionCamera;
	cameraMgr->startCamera(naviMgr->getActiveNavi());
	cameraMgr->update();
#if defined(PIKI_PC_PORT)
	if (mCameraMgr2) {
		mCameraMgr2->startCamera(mNavi2);
		mCameraMgr2->update();
	}
#endif
	mNavi->mIsCursorVisible = TRUE;
#if defined(PIKI_PC_PORT)
	if (mNavi2) {
		mNavi2->mIsCursorVisible = TRUE; // sin esto P2 no tiene cursor ni silbato
	}
#endif

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
                // init/setColor clear experimental identity; restore it afterward.
                if (pc_randomizer_purple_campaign()) a->doRestore(item);
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

	naviMgr->getActiveNavi()->startKontroller();
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

	if (playerState->mHasExtinctionDemoPlayed == false && !playerState->isTutorial() PC_NOT_VS
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
#if defined(PIKI_PC_PORT)
		if (mNavi2) {
			// P2 también sale de la nave, un poco a un lado para no solaparse.
			mNavi2->mStateMachine->transit(mNavi2, 23);
			if (UfoItem* ufo = itemMgr->getUfo()) {
				Vector3f side(cosf(ufo->mFaceDirection), 0.0f, -sinf(ufo->mFaceDirection));
				mNavi2->mSRT.t = mNavi2->mSRT.t + side * 30.0f;
				mNavi2->mSRT.t.y = mMapMgr->getMinY(mNavi2->mSRT.t.x, mNavi2->mSRT.t.z, true);
				mNavi2->mLastPosition = mNavi2->mSRT.t;
			}
		}
#endif
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
#if defined(PIKI_PC_PORT)
	if (mCameraMgr2) {
		mCameraMgr2->mCamera->startCamera(mNavi2, 1, 0);
	}
#endif

	// Lane 12 (#130): finish the second captain's live setup now that the first
	// captain's spawn position, the shared camera and every stage manager exist.
	// The second Navi was birthed (create(2)) during initStage; here it is
	// init'd and reset beside the active captain (the same sequence the first
	// captain goes through), so the survivor path can rebind active/camera/
	// whistle/throw to it when slot 0 goes down.
	if (naviMgr->hasSecondNavi()) {
		Navi* firstNavi = naviMgr->getActiveNavi();
		Navi* secondNavi = naviMgr->getOtherNavi(firstNavi);
		if (firstNavi && secondNavi) {
			secondNavi->init(firstNavi->mSRT.t);
			secondNavi->mSRT.r = firstNavi->mSRT.r;
			secondNavi->mFaceDirection = firstNavi->mFaceDirection;
			secondNavi->reset();
			// reset() clears the cursor flag, which initStage() had already set TRUE for both
			// captains. Without it the second captain has no cursor and its whistle (Walk state
			// needs mIsCursorVisible) does nothing.
			secondNavi->mIsCursorVisible = TRUE;
			secondNavi->mNaviCamera = mNavi->mNaviCamera;
			secondNavi->mStateMachine->transit(secondNavi, NAVISTATE_Starting);
			// Lane 12 (#130): NaviStartingState::init re-centres the Navi on the
			// ship, so apply the slot offset AFTER the Starting transition or the
			// two captains stack at the same point.
			secondNavi->mSRT.t.x += 40.0f;
			secondNavi->mSRT.t.z += 40.0f;
			secondNavi->startKontroller();
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

	pc_p2_kurage_teki_setup();
	pc_p2_onikurage_teki_setup();
	pc_p2_bombsarai_teki_setup();
	pc_p2_groink_teki_setup();
	pc_p2_breadbug_teki_setup();
	pc_p2_bigtreasure_teki_setup();
	pc_p2_king_teki_setup();
	pc_p2_queen_teki_setup();
	pc_p2_demon_manager_setup();
	pc_p2_sarai_manager_setup();
	pc_p2_preview_setup();
    if (pc_randomizer_purple_campaign()) {
        pc_p2_purple_setup();
        pc_p2_purple_motion_setup();
        pc_p2_purple_flight_setup();
        std::printf("P2_SHIP_READY stored=%d controls=F10_withdraw_ShiftF10_deposit near_ship=180\n", p2ship::stock.total());
    }
	pc_p2_snow_campaign_setup();
	// Actor-lifetime (#397): mark the new scene ready for lifecycle fixtures.
	pc_p2_scene_begin();
	PRINT("====================== FINAL SETUP DONE ======================\n");
}

#if defined(PIKI_PC_PORT)
// Netplay M0: true when any PIKMIN_NETPLAY* environment variable is set.
// Scans the process environment so future PIKMIN_NETPLAY_* flags also arm
// the [NETPLAY] marker without touching this call site.
static bool pc_netplay_marker_env_set()
{
#if defined(_WIN32)
	// _environ comes from <stdlib.h> (via <cstdlib> above); it must not be
	// redeclared here because under UCRT headers it is a macro over a
	// static inline accessor, not a plain exported variable.
	char** env = _environ;
#else
	extern char** environ;
	char** env = environ;
#endif
	if (!env) return false;
	for (; *env; ++env) {
		if (std::strncmp(*env, "PIKMIN_NETPLAY", 14) == 0 && (*env)[14] != '\0') return true;
	}
	return false;
}
#endif
/**
 * @todo: Documentation
 */
GameCoreSection::GameCoreSection(Controller* controller, MapMgr* mgr, Camera& camera)
    : Node("gamecore")
{
#if defined(PIKI_PC_PORT)
	// M1 deterministic netplay: reseed the sim stream (and the cosmetic one)
	// from hash(PIKMIN_NETPLAY_SEED, day index, stage id) so every peer and
	// every replay of the day draws the same sequence. gameflow carries the
	// 1-based day; flowCont carries the stage. No-op with the switch off.
	pc_netplay_det_reseed_for_new_day(gameflow.mWorldClock.mCurrentDay,
	    flowCont.mCurrentStage != nullptr ? static_cast<int>(flowCont.mCurrentStage->mStageID) : 0);
#endif
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
#if defined(PIKI_PC_PORT)
	containerWindow2 = nullptr; // se crea más abajo, cuando ya existe mNavi2
#endif
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
	// 0 means the original value: 27 min per 24h, 13.5 min of play.
	const int dayMinutes = pc_settings_get_day_minutes();
	gameflow.mParameters->mRealMinutesPerGameDay(dayMinutes ? f32(dayMinutes) * 2.0f : 27.0f);
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
#if defined(PIKI_PC_PORT)
	pc_coop_begin_run();
	// VS: reaprovecha el modo versus que Nintendo dejó a medias (Pikmin con
	// dueño, rivales como enemigos). Se puso a FALSE justo arriba.
	flowCont.mIsVersusMode = pc_vs_active() ? TRUE : FALSE;
	// Lane 12 (#130): opt-in P2 second captain. navi_capacity() is 1 unless
	// PIKMIN_P2_SECOND_CAPTAIN is set; normal single-captain play is unchanged
	// because the request defaults off. Upstream local co-op owns the second
	// Navi slot when it is active, so the P2 opt-in path only runs without it.
	const bool pcCoop = pc_coop_active();
	int naviCapacity  = pcCoop ? 2 : pc_p2_captain::navi_capacity();
	if (!pcCoop && naviCapacity > 1 && !pc_p2_captain::prepare_second_captain_assets(naviMgr)) {
		naviCapacity = 1;
	}
	naviMgr->create(naviCapacity);
	mNavi = static_cast<Navi*>(naviMgr->birth());
	// mNaviID 1 -> Kontroller(2) -> pad 1 (segundo mando, fase 0).
	mNavi2 = pcCoop ? static_cast<Navi*>(naviMgr->birth()) : nullptr;
	if (!pcCoop && naviCapacity > 1) pc_p2_captain::birth_second_captain(naviMgr);
	// Lane 12 (#130): bind the live slot-0 captain/squad adapter now that the
	// Navi object exists, so a captor family can resolve target identity and
	// claim/release through pc_p2_captain against the real NaviMgr/PikiMgr.
	// Idempotent; with one Navi the zero-control guard keeps only-captain
	// capture refused, exactly as the source refuses to strand the player.
	pc_p2_captain::setup_from_navi_mgr();
	// Netplay M0: single co-op marker line. It prints only when the co-op
	// switch armed this run or some PIKMIN_NETPLAY* env var is set, so
	// ordinary single-player logs are unchanged.
	if (pc_coop_switch_active() || pc_netplay_marker_env_set()) {
		std::printf("[NETPLAY] coop_active=%d navis=%d\n", pc_coop_active() ? 1 : 0,
		            naviMgr->getNaviCount());
	}
#else
	naviMgr->create(1);
	mNavi = static_cast<Navi*>(naviMgr->birth());
#endif
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
#if defined(PIKI_PC_PORT)
	if (mNavi2) {
		// Fase 1: cámara única que sigue a P1; P2 comparte la misma cámara.
		mNavi2->mNaviCamera = &camera;
		mNavi2->init();
	}
#endif
	camera.mPosition.x = 500.0f * sinf(camera.mRotation.x);
	camera.mPosition.y = 140.0f;
	camera.mPosition.z = 500.0f * cosf(camera.mRotation.x);
	gsys->setFade(1.0f);
	cameraMgr = new PcamCameraManager(&camera, mNavi->mKontroller);
	gameflow.addGenNode("cameraMgr", cameraMgr);
#if defined(PIKI_PC_PORT)
	cameraMgrP1 = cameraMgr;
	if (mNavi2) {
		mGameCamera2 = new Camera();
		mGameCamera2->mRotation = camera.mRotation;
		mGameCamera2->mPosition = camera.mPosition;
		mGameCamera2->mFov      = camera.mFov;
		mNavi2->mNaviCamera     = mGameCamera2;
		mCameraMgr2 = new PcamCameraManager(mGameCamera2, mNavi2->mKontroller);
		cameraMgrP2 = mCameraMgr2;
	} else {
		cameraMgrP2 = nullptr;
	}
#endif
	memStat->end("gamecore");

	mDrawGameInfo = new zen::DrawGameInfo(!gameflow.mIsChallengeMode ? zen::DrawGameInfo::MODE_Story : zen::DrawGameInfo::MODE_Challenge);
#if defined(PIKI_PC_PORT)
	if (mNavi2) {
		containerWindow2 = new zen::DrawContainer(2);
		mDrawGameInfo2 = new zen::DrawGameInfo(!gameflow.mIsChallengeMode ? zen::DrawGameInfo::MODE_Story : zen::DrawGameInfo::MODE_Challenge, 1);
	}
#endif
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
 * without sitting through it. F7 ends the day with the Main Engine recovered
 * and 20 Pikmin banked, so testing anything past the first level does not mean
 * playing the first level again.
 */
// VS (fase 1): F8 apunta dónde está cada capitán en vs_positions.txt, para
// colocar bases y piezas del mapa VS paseando por él.
static void pcVsMarkKey()
{
	if (!pc_vs_active() || !naviMgr) {
		return;
	}
	const Uint8* keys = SDL_GetKeyboardState(nullptr);
	static bool wasDown = false;
	const bool isDown   = keys != nullptr && keys[SDL_SCANCODE_F8] != 0;
	if (isDown && !wasDown) {
		static int mark = 0;
		mark++;
		FILE* out = fopen("vs_positions.txt", "a");
		for (int i = 0; i < 2; i++) {
			Navi* navi = naviMgr->getNavi(i);
			if (!navi) continue;
			const Vector3f& p = navi->mSRT.t;
			fprintf(stderr, "[VS] marca %d  P%d  %.1f %.1f %.1f\n", mark, i + 1, p.x, p.y, p.z);
			if (out) fprintf(out, "marca %d  P%d  %.1f %.1f %.1f\n", mark, i + 1, p.x, p.y, p.z);
		}
		if (out) fclose(out);
	}
	wasDown = isDown;
}

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
		fprintf(stderr, "[DEBUG] clock -> %02d:00 (day is %d min of play, 0 = original)\n",
		        clock.mCurrentGameHour, pc_settings_get_day_minutes());
		fflush(stderr);
	}
	hourWasDown = hourDown;

	// F7 finishes the day outright: the Main Engine counted as recovered and
	// the Onion topped up to 20 red Pikmin. Only the trigger is set here --
	// NewPikiGameModeState picks it up and runs the real end-of-day path, so
	// the cutscene, the results screen and the save prompt all behave as if
	// the day had ended on its own.
	static bool skipWasDown = false;
	const bool skipDown     = keys != nullptr && keys[SDL_SCANCODE_F7] != 0;
	if (skipDown && !skipWasDown) {
		if (gameflow.mIsDayEndActive || gameflow.mIsDayEndTriggered) {
			fprintf(stderr, "[DEBUG] the day is already ending\n");
		} else {
			// Keyed by model ID, and PlayerState refuses a duplicate itself.
			// "Invisible" because the part is granted rather than carried in,
			// which is also what keeps this quiet in stages that have no
			// Main Engine pellet to register.
			if (!playerState->hasUfoParts(UFOID_MainEngine)) {
				playerState->getUfoParts(UFOID_MainEngine, true);
			}

			// The same three places F5 touches, for the same reasons.
			GoalItem* onion = itemMgr ? itemMgr->getContainer(Red) : nullptr;
			if (onion == nullptr) {
				fprintf(stderr, "[DEBUG] no red Onion here; ending the day without stocking\n");
			} else {
				const int limit   = pc_settings_get_piki_limit();
				const int already = int(GameStat::allPikis);
				int added         = 20 - already; // top up to 20, do not add 20
				if (already + added > limit) {
					added = limit - already;
				}
				if (added > 0) {
					pikiInfMgr.mPikiCounts[Red][Leaf] += added;
					onion->mHeldPikis[Leaf] += added;
					GameStat::containerPikis.add(Red, added);
					GameStat::update();
				}
			}

			gameflow.mIsDayEndTriggered = TRUE;
			fprintf(stderr, "[DEBUG] tutorial skipped: Main Engine recovered, ending the day\n");
		}
		fflush(stderr);
	}
	skipWasDown = skipDown;
}
#endif

void GameCoreSection::update()
{
	STACK_PAD_VAR(2);
#if defined(PIKI_PC_PORT)
	if (pc_vs_active()) {
		pcVsUpdate(mMapMgr);
	}
#endif
#if defined(PIKI_PC_PORT) && PIKI_DEBUG_KEYS
	pcDebugKeys();
	pcVsMarkKey();
#endif
#if defined(PIKI_PC_PORT)
	// #942 dev console: runs queued/script commands on the gameplay thread.
	pc_dev_console_update();
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
	pc_p2_hardlanes_update();
	pc_p2_projectiles_update();
	pc_p2_queen_teki_frame();
	pc_p2_kabuto_fsm_update_stones();
	pc_p2_bombsarai_teki_update_bombs();
	pc_p2_long_legs_update_all();

	if (GameStat::allPikis == 0 && (!pc_randomizer_purple_campaign() || p2ship::stock.total() == 0) && GameStat::maxPikis > 0) {
#if defined(PIKI_PC_PORT)
		// Cooperativo: la secuencia de extinción la hace un Olimar vivo, no
		// un cuerpo caído. Si el vivo ya está en ella, no se repite.
		Navi* navi = naviMgr->getMovieNavi();
		int id     = navi->getCurrState()->getID();
		if (mNavi2) {
			bool anyInPikiZero = false;
			for (int ni = 0; ni < naviMgr->getNaviCount(); ni++) {
				if (naviMgr->getNavi(ni)->getCurrState()->getID() == NAVISTATE_PikiZero) anyInPikiZero = true;
			}
			if (anyInPikiZero) id = NAVISTATE_PikiZero;
		}
#else
		Navi* navi = mNavi;
		int id     = navi->getCurrState()->getID();
#endif
		if (id != NAVISTATE_PikiZero && id != NAVISTATE_DemoSunset && id != NAVISTATE_DemoWait && id != NAVISTATE_DemoInf
		    && id != NAVISTATE_Dead) {
			PRINT("**** PIKI ZERO GAME OVER *******\n");
			PRINT("deadpikis %d pellets %d killtekis %d maxpikis %d" MISSING_NEWLINE, static_cast<int>(GameStat::deadPikis),
			      static_cast<int>(GameStat::getPellets), static_cast<int>(GameStat::killTekis), GameStat::maxPikis);
			navi->mStateMachine->transit(navi, NAVISTATE_PikiZero);
			playerState->mResultFlags.setOn(zen::RESFLAG_PikminExtinction);
		}
	}

	if (!gameflow.mMoviePlayer->mIsActive) {
		cameraMgr->update();
#if defined(PIKI_PC_PORT)
		updateCoopCameras();
#endif
	}
#if defined(PIKI_PC_PORT)
	// Los textos de tutorial muestran los controles del jugador que los
	// disparó (setMovieNavi se fija en cada disparador, fase 2).
	Navi* promptNavi = (mNavi2 && naviMgr) ? naviMgr->getMovieNavi() : nullptr;
	pc_window_set_prompt_player(promptNavi ? promptNavi->mNaviID : -1);

	// Issue #40: con una escena, un texto (la nave, un tutorial) o la pausa en
	// pantalla, Navi no lee el ratón y su movimiento se acumula. Al volver, el
	// cursor salía disparado todo lo acumulado. Se descarta mientras dura.
	if (gameflow.mMoviePlayer->mIsActive || gameflow.mIsUIOverlayActive || gameflow.mPauseAll) {
		pc_window_clear_mouse_cursor_delta();
	}
#endif


#if defined(PIKI_PC_PORT)
	fillHudInfo(mDrawGameInfo->info(), mNavi);
	if (mNavi2 && mDrawGameInfo2) {
		fillHudInfo(mDrawGameInfo2->info(), mNavi2);
	}
	Node::update();
}

int GameCoreSection::countFormationPikis(Navi* navi)
{
	int count = 0;
	Iterator iter(pikiMgr);
	CI_LOOP(iter)
	{
		Piki* piki = static_cast<Piki*>(*iter);
		if (piki->isAlive() && piki->mMode == PikiMode::FormationMode && piki->mNavi == navi) {
			count++;
		}
	}
	return count;
}

void GameCoreSection::fillHudInfo(zen::GameInfo* info, Navi* navi)
{
	// Lane 12 (#130): with the opt-in P2 second captain (no co-op second HUD),
	// the single HUD follows whichever captain is currently controlled.
	if (!mNavi2 && navi == mNavi) {
		if (Navi* active = naviMgr->getActiveNavi()) navi = active;
	}
	Piki* nextThrowPiki = navi->mNextThrowPiki;
#else
	Navi* activeThrowNavi = naviMgr->getActiveNavi();
	if (!activeThrowNavi) activeThrowNavi = naviMgr->getNavi();
	Piki* nextThrowPiki = activeThrowNavi->mNextThrowPiki;
#endif
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
#if defined(PIKI_PC_PORT)
	info->mEncodedNextThrowType = encodedNextThrowType;
	info->mTotalPikiNum         = GameStat::allPikis;
	info->mMapPikiNum           = GameStat::mapPikis;
	info->mFormationPikiNum     = mNavi2 ? countFormationPikis(navi) : (short)GameStat::formationPikis;
	// VS: cada HUD cuenta solo lo de su jugador (campo y, en total, también
	// lo guardado en sus cebollas).
	if (pc_vs_active() && navi) {
		const int player = navi->mNaviID;
		int map          = 0;
		Iterator it(pikiMgr);
		CI_LOOP(it)
		{
			Piki* piki = static_cast<Piki*>(*it);
			if (piki->isAlive() && piki->mPlayerId == player) map++;
		}
		int stored = 0;
		for (int color = PikiMinColor; color < PikiColorCount; color++) {
			if (GoalItem* goal = itemMgr->pcGetContainer(color, player)) stored += goal->getTotalStorePikis();
		}
		info->mMapPikiNum   = short(map);
		info->mTotalPikiNum = short(map + stored);
	}
}
#else
	zen::pGameInfo->mEncodedNextThrowType = encodedNextThrowType;
	zen::pGameInfo->mTotalPikiNum         = GameStat::allPikis;
	zen::pGameInfo->mMapPikiNum           = GameStat::mapPikis;
	zen::pGameInfo->mFormationPikiNum     = GameStat::formationPikis;
	pc_p2_queen_update();
	pc_p2_king_update();
	pc_p2_hiba_update();
	pc_p2_dweevil_update();
	pc_p2_bombotakara_update();
	Node::update();
}
#endif

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

// Netplay gapfix C4 (#885): the randomizer steps both paths share. The
// single-captain path (randomizerApplyBenefits and the else branch in
// GameCoreSection::updateAI) and the co-op branch (randomizerUpdateCoop,
// randomizerApplyBenefitsCoop, randomizerApplyDeathLinkCoop) call these same
// functions, so a gate or a fix lands once for both. The gates they carry:
// randomizerTickOpen (no movie, pause or UI overlay); simReady
// (pc_randomizer_ready(), checked by both benefit steps and inside every
// pc_randomizer_* call below); B1's outbox (inside
// pc_randomizer_consume_benefit, _check, _observe_* and _deathlink_*). A
// synchronized HOLD freezes the whole sim, so no updateAI runs while held.
// Each helper is the statement sequence it replaced, moved unchanged (the
// placements gained only the log-only sPlaceWhy detail and a result code).
#include "pc_coop_policy.h"

namespace {
// Log-only detail of the last failed placement (why a co-op captain was
// skipped); never read by the sim.
char sPlaceWhy[48] = "";
}

// Movies, pauses and UI overlays stop the randomizer tick.
static bool randomizerTickOpen()
{
    return !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive;
}

// The prerelease trap ends at day end or when no captain stands, and runs
// down while the randomizer tick is active.
static void randomizerPrereleaseClock(bool captainsDown, bool active)
{
    if (bossMgr) {
        if (playerState->mInDayEnd || captainsDown) bossMgr->endPrereleaseTrap();
        else if (active) bossMgr->tickPrereleaseTrap(gsys->getFrameTime());
    }
}

// Bomb trap: five lit bombs on a ring around the captain. FAILED when the
// ring does not fit (the co-op branch then tries the other captain), STOP
// when a spawn or the consume fails, CONSUMED (cooldown set) otherwise.
static PcCoopPlaceResult randomizerBombTrapAt(Navi* navi, MapMgr* map, float& cooldown)
{
    Vector3f positions[5];
    int found = 0;
    for (int i = 0; i < 5; ++i) {
        const float angle = navi->mFaceDirection + i * (2.0f * PI / 5.0f);
        Vector3f pos = navi->mSRT.t + Vector3f(65.0f * sinf(angle), 0, 65.0f * cosf(angle));
        CollTriInfo* ground = map->getCurrTri(pos.x, pos.z, true);
        if (!ground || MapCode::getAttribute(ground) == ATTR_Water) {
            std::snprintf(sPlaceWhy, sizeof(sPlaceWhy), "ring-%s found=%d", ground ? "water" : "no-ground", found);
            break;
        }
        pos.y = map->getMinY(pos.x, pos.z, true);
        if (std::fabs(pos.y - navi->mSRT.t.y) > 25.0f) {
            std::snprintf(sPlaceWhy, sizeof(sPlaceWhy), "ring-height found=%d dy=%.1f", found, pos.y - navi->mSRT.t.y);
            break;
        }
        pos.y += 3.0f;
        positions[found++] = pos;
    }
    if (found != 5) return PC_COOP_PLACE_FAILED;
    BombItem* spawned[5] = {};
    int count = 0;
    for (; count < 5; ++count) {
        spawned[count] = static_cast<BombItem*>(itemMgr->birth(OBJTYPE_Bomb));
        if (!spawned[count]) break;
        spawned[count]->init(positions[count]);
        spawned[count]->startAI(0);
    }
    if (count == 5 && pc_randomizer_consume_benefit(PC_BENEFIT_BOMB_TRAP)) {
        float longestFuse = 0.0f;
        for (int i = 0; i < 5; ++i) {
            C_SAI(spawned[i])->start(spawned[i], BombAI::BOMB_Set);
            longestFuse = std::max(longestFuse, spawned[i]->mSAICtx.mCurrentItemHealth);
        }
        cooldown = std::max(5.0f, longestFuse + 2.0f);
        std::printf("[Pikmin Randomizer] BOMB_AMBUSH count=5 state=lit fuse=%.2f cooldown=%.2f\n", longestFuse, cooldown);
        std::fflush(stdout);
        return PC_COOP_PLACE_CONSUMED;
    }
    for (int i = 0; i < count; ++i) spawned[i]->kill(false);
    return PC_COOP_PLACE_STOP;
}

// A Progg ambush waits while a Progg still lives.
static bool randomizerProggAlive()
{
    Iterator enemies(tekiMgr);
    CI_LOOP(enemies) {
        Teki* enemy = static_cast<Teki*>(*enemies);
        if (enemy && enemy->mTekiType == TEKI_Dororo && enemy->isAlive()) return true;
    }
    return false;
}

// Progg ambush: one Progg on a 250-unit ring behind the captain, only near
// an Onion. Results as for randomizerBombTrapAt.
static PcCoopPlaceResult randomizerProggAt(Navi* navi, MapMgr* map, float& cooldown)
{
    if (!itemMgr->getNearestContainer(navi->mSRT.t, 12800.0f)) {
        std::snprintf(sPlaceWhy, sizeof(sPlaceWhy), "no-onion-near");
        return PC_COOP_PLACE_FAILED;
    }
    for (int sample = 0; sample < 12; ++sample) {
        const float angle = navi->mFaceDirection + PI + sample * (2.0f * PI / 12.0f);
        Vector3f pos = navi->mSRT.t + Vector3f(250.0f * sinf(angle), 0, 250.0f * cosf(angle));
        CollTriInfo* ground = map->getCurrTri(pos.x, pos.z, true);
        if (!ground || MapCode::getAttribute(ground) == ATTR_Water) continue;
        pos.y = map->getMinY(pos.x, pos.z, true);
        if (std::fabs(pos.y - navi->mSRT.t.y) > 25.0f) continue;
        Teki* progg = tekiMgr->newTeki(TEKI_Dororo);
        if (!progg) return PC_COOP_PLACE_STOP;
        progg->mGenerator = nullptr;
        progg->mPersonality->reset();
        progg->mPersonality->mPosition = pos;
        progg->mPersonality->mNestPosition = pos;
        progg->mPersonality->mFaceDirection = angle + PI;
        progg->reset();
        if (pc_randomizer_consume_benefit(PC_BENEFIT_PROGG)) {
            progg->startAI(0);
            cooldown = 30.0f;
            std::printf("[Pikmin Randomizer] PROGG_AMBUSH count=1 x=%.1f z=%.1f\n", pos.x, pos.z);
            std::fflush(stdout);
            return PC_COOP_PLACE_CONSUMED;
        }
        progg->kill(false);
        return PC_COOP_PLACE_STOP;
    }
    std::snprintf(sPlaceWhy, sizeof(sPlaceWhy), "no-spot");
    return PC_COOP_PLACE_FAILED;
}

// Flower Shower: five nectar drops on a ring around the captain. Results as
// for randomizerBombTrapAt.
static PcCoopPlaceResult randomizerFlowersAt(Navi* navi, MapMgr* map, float& cooldown)
{
    Vector3f positions[5];
    int found = 0;
    for (int i = 0; i < 5; ++i) {
        const float angle = navi->mFaceDirection + i * (2.0f * PI / 5.0f);
        Vector3f pos = navi->mSRT.t + Vector3f(50.0f * sinf(angle), 0, 50.0f * cosf(angle));
        CollTriInfo* ground = map->getCurrTri(pos.x, pos.z, true);
        if (!ground || MapCode::getAttribute(ground) == ATTR_Water) {
            std::snprintf(sPlaceWhy, sizeof(sPlaceWhy), "ring-%s found=%d", ground ? "water" : "no-ground", found);
            break;
        }
        pos.y = map->getMinY(pos.x, pos.z, true);
        if (std::fabs(pos.y - navi->mSRT.t.y) > 25.0f) {
            std::snprintf(sPlaceWhy, sizeof(sPlaceWhy), "ring-height found=%d dy=%.1f", found, pos.y - navi->mSRT.t.y);
            break;
        }
        positions[found++] = pos;
    }
    if (found != 5) return PC_COOP_PLACE_FAILED;
    MizuItem* spawned[5] = {};
    int count = 0;
    for (; count < 5; ++count) {
        // Native nectar appearance/drinking, with no deferred second allocation.
        spawned[count] = static_cast<MizuItem*>(itemMgr->birth(OBJTYPE_Water));
        if (!spawned[count]) break;
        spawned[count]->init(positions[count]);
        spawned[count]->startAI(0);
    }
    if (count == 5 && pc_randomizer_consume_benefit(PC_BENEFIT_FLOWERS)) {
        cooldown = 5.0f;
        std::puts("[Pikmin Randomizer] FLOWER_SHOWER nectar=5");
        std::fflush(stdout);
        return PC_COOP_PLACE_CONSUMED;
    }
    for (int i = 0; i < count; ++i) spawned[i]->kill(false);
    return PC_COOP_PLACE_STOP;
}

// BOMBS: three loose, unlit bombs at the first owned Onion once a yellow
// Pikmin is on the field. Onion-anchored: no captain.
static void randomizerBombDelivery(MapMgr* map)
{
    bool yellowOnField = false;
    if (pc_randomizer_benefit_pending(PC_BENEFIT_BOMBS)) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (piki && piki->isAlive() && piki->mColor == Yellow) {
                yellowOnField = true;
                break;
            }
        }
    }
    if (map && yellowOnField && pc_randomizer_benefit_pending(PC_BENEFIT_BOMBS)) {
        GoalItem* landing = nullptr;
        const char* names[] = {"Blue Onion", "Red Onion", "Yellow Onion"};
        for (int color = 0; color < 3 && !landing; ++color)
            if (pc_randomizer_has(names[color]) && playerState->hasBootContainer(color)) landing = itemMgr->getContainer(color);
        if (landing) {
            Vector3f positions[3];
            int found = 0;
            for (int sample = 0; sample < 12 && found < 3; ++sample) {
                const float angle = sample * (2.0f * PI / 12.0f);
                Vector3f pos = landing->mSRT.t + Vector3f(40.0f * sinf(angle), 0, 40.0f * cosf(angle));
                CollTriInfo* ground = map->getCurrTri(pos.x, pos.z, true);
                if (!ground || MapCode::getAttribute(ground) == ATTR_Water) continue;
                pos.y = map->getMinY(pos.x, pos.z, true);
                if (std::fabs(pos.y - landing->mSRT.t.y) > 25.0f) continue;
                pos.y += 3.0f;
                positions[found++] = pos;
            }
            if (found == 3) {
                BombItem* spawned[3] = {};
                int count = 0;
                for (; count < 3; ++count) {
                    spawned[count] = static_cast<BombItem*>(itemMgr->birth(OBJTYPE_Bomb));
                    if (!spawned[count]) break;
                    spawned[count]->init(positions[count]);
                    spawned[count]->startAI(0); // Unlit, loose and available for normal pickup.
                }
                if (count == 3 && pc_randomizer_consume_benefit(PC_BENEFIT_BOMBS))
                    std::puts("[Pikmin Randomizer] BOMB_DELIVERY count=3 state=unlit");
                else for (int i = 0; i < count; ++i) spawned[i]->kill(false);
            }
        }
    }
}

// DELIVERY: ten Pikmin into the owned Onion that has the fewest. Returns that
// Onion's colour, or -1 when nothing was delivered.
static int randomizerPikminDelivery()
{
    if (pc_randomizer_benefit_pending(PC_BENEFIT_DELIVERY)) {
        int selected = -1;
        const char* onions[] = {"Blue Onion", "Red Onion", "Yellow Onion"};
        for (int color = 0; color < 3; ++color)
            if (pc_randomizer_has(onions[color]) && playerState->hasBootContainer(color) && itemMgr->getContainer(color)
                && (selected < 0 || GameStat::allPikis[color] < GameStat::allPikis[selected])) selected = color;
        if (selected >= 0 && pc_randomizer_consume_benefit(PC_BENEFIT_DELIVERY)) {
            itemMgr->getContainer(selected)->mHeldPikis[Leaf] += 10;
            pikiInfMgr.mPikiCounts[selected][Leaf] += 10;
            GameStat::containerPikis.add(selected, 10);
            GameStat::update();
            std::printf("[Pikmin Randomizer] PIKMIN_DELIVERY color=%d count=10\n", selected);
            return selected;
        }
    }
    return -1;
}

// A received DeathLink takes up to one unit of living field Pikmin through
// the ordinary dying animation. Onion stock and the captains are untouched.
// Returns -1 when no link is pending, else the number killed (one consume per
// link, whatever the count). squad (optional) counts the victims by leader:
// [0] followed p1, [1] followed p2.
static int randomizerApplyDeathLink(Navi* p1, Navi* p2, int squad[2])
{
    const int casualties = pc_randomizer_deathlink_casualties();
    if (!casualties) return -1;
    int killed = 0;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        if (killed >= casualties) break;
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive() || piki->isKinoko()) continue;
        const int mode = piki->mMode, state = piki->getState();
        if (mode == PikiMode::EnterMode || mode == PikiMode::ExitMode || mode == PikiMode::KinokoMode) continue;
        if (state == PIKISTATE_Dying || state == PIKISTATE_Dead || state == PIKISTATE_Swallowed
            || state == PIKISTATE_Drown || state == PIKISTATE_Fired || state == PIKISTATE_Bubble) continue;
        if (squad) {
            if (piki->mNavi == p1) ++squad[0];
            else if (piki->mNavi == p2) ++squad[1];
        }
        pc_randomizer_deathlink_induce(piki);
        piki->changeMode(PikiMode::FreeMode, piki->mNavi);
        piki->mFSM->transit(piki, PIKISTATE_Dying);
        ++killed;
    }
    pc_randomizer_deathlink_consume(killed);
    return killed;
}

// Population, colour and obstacle observations (sim-side check triggers).
static void randomizerObserveWorld()
{
    const int field = int(GameStat::formationPikis) + int(GameStat::freePikis) + int(GameStat::workPikis);
    pc_randomizer_observe_population(field, true);
    pc_randomizer_observe_total_population(int(GameStat::allPikis) + (pc_randomizer_purple_campaign() ? p2ship::stock.total() : 0), true);
    int specialAliases[3] = {};
    if (pc_randomizer_purple_campaign()) {
        Iterator live(pikiMgr);
        CI_LOOP(live) {
            Piki* p = static_cast<Piki*>(*live);
            if (p && p->isAlive() && (p->mP2Purple || p->mP2White)) ++specialAliases[p->mColor];
        }
        Iterator sprouts(itemMgr->getPikiHeadMgr());
        CI_LOOP(sprouts) {
            PikiHeadItem* p = static_cast<PikiHeadItem*>(*sprouts);
            if (p && (p->mP2Purple || p->mP2White)) ++specialAliases[p->mSeedColor];
        }
    }
    for (int color = PikiMinColor; color < PikiColorCount; ++color)
        pc_randomizer_observe_color_population(color, std::max(0, GameStat::allPikis[color] - specialAliases[color]), true);
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
}

// Exploration (Land checks), anchored on one captain.
static void randomizerObserveExploration(Navi* navi)
{
    UfoItem* ship = itemMgr ? itemMgr->getUfo() : nullptr;
    if (ship && flowCont.mCurrentStage) {
        const Vector3f base = ship->getGoalPos();
        pc_randomizer_observe_exploration(flowCont.mCurrentStage->mStageID,
            navi->getPosition().x - base.x, navi->getPosition().z - base.z, navi->mGroundTriangle != nullptr, true);
    }
}

static void randomizerApplyMaturity()
{
    // Progressive maturity is a level, not a consumable: keep every Pikmin of a
    // color at or above its received tier. Field Pikmin grow only in ordinary
    // states (never mid-pluck, eaten, dying or mushroomed) and are caught on a
    // later sweep; Onion stock moves up in both counters the withdrawal uses.
    static float maturitySweep = 0.0f;
    maturitySweep = std::max(0.0f, maturitySweep - gsys->getFrameTime());
    if (maturitySweep == 0.0f) {
        maturitySweep = 0.25f;
        int grown = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (!piki || !piki->isAlive() || piki->mColor < 0 || piki->mColor > 2) continue;
            const int tier = pc_randomizer_maturity(piki->mColor);
            if (piki->mHappa >= tier || !piki->getCurrState()) continue;
            const int state = piki->getCurrState()->getID();
            if (state != PIKISTATE_Normal && state != PIKISTATE_LookAt && state != PIKISTATE_Emotion) continue;
            piki->setFlower(tier);
            if (grown++ == 0) seSystem->playPikiSound(SEF_PIKI_GROW4, piki->mSRT.t);
        }
        for (int color = 0; color < 3; ++color) {
            const int tier = pc_randomizer_maturity(color);
            GoalItem* onion = itemMgr->getContainer(color);
            for (int happa = Leaf; happa < tier; ++happa) {
                grown += pikiInfMgr.mPikiCounts[color][happa];
                pikiInfMgr.mPikiCounts[color][tier] += pikiInfMgr.mPikiCounts[color][happa];
                pikiInfMgr.mPikiCounts[color][happa] = 0;
                if (onion) {
                    onion->mHeldPikis[tier] += onion->mHeldPikis[happa];
                    onion->mHeldPikis[happa] = 0;
                }
            }
        }
        if (grown) {
            std::printf("[Pikmin Randomizer] MATURITY_APPLIED count=%d\n", grown);
            std::fflush(stdout);
        }
    }
}

static void randomizerApplyBenefits(Navi* navi, MapMgr* map)
{
    if (!pc_randomizer_ready() || !navi || !navi->isAlive() || !itemMgr || !pikiMgr) return;
    // Active gameplay time only: never empty a backlog of traps in one frame.
    static float bombTrapCooldown = 0.0f;
    bombTrapCooldown = std::max(0.0f, bombTrapCooldown - gsys->getFrameTime());
    if (map && bombTrapCooldown == 0.0f && pc_randomizer_benefit_pending(PC_BENEFIT_BOMB_TRAP))
        randomizerBombTrapAt(navi, map, bombTrapCooldown);
    static float proggCooldown = 0.0f;
    proggCooldown = std::max(0.0f, proggCooldown - gsys->getFrameTime());
    if (map && tekiMgr && proggCooldown == 0.0f && pc_randomizer_benefit_pending(PC_BENEFIT_PROGG) && !randomizerProggAlive())
        randomizerProggAt(navi, map, proggCooldown);
    if (bossMgr && navi->getCurrState() && navi->getCurrState()->getID() == NAVISTATE_Walk) bossMgr->beginPrereleaseTrap();
    randomizerBombDelivery(map);
    randomizerPikminDelivery();
    static float nectarCooldown = 0.0f;
    nectarCooldown = std::max(0.0f, nectarCooldown - gsys->getFrameTime());
    if (map && nectarCooldown == 0.0f && pc_randomizer_benefit_pending(PC_BENEFIT_FLOWERS))
        randomizerFlowersAt(navi, map, nectarCooldown);
    randomizerApplyMaturity();
    if (navi->mHealth < C_NAVI_PARM(navi, mHealth) && pc_randomizer_consume_benefit(PC_BENEFIT_HEAL))
        navi->mHealth = C_NAVI_PARM(navi, mHealth);
}

// Netplay M4 D-policy (issue #885): the owner's co-op randomizer policy.
// Everything from here to GameCoreSection::updateAI runs only in co-op
// (pc_coop_active() with a second captain); single-captain play keeps
// randomizerApplyBenefits above and its updateAI statements. The decisions
// themselves are pure functions in pc_port/pc_coop_policy; the grant,
// DeathLink and observation steps are the shared helpers above.
// All state below is sim state: it changes only inside updateAI, uses no RNG
// and no wall clock, so both lockstep peers hold identical values. The
// per-tick state hash folds it while co-op is active
// (pc_coop_policy_state_hash, gapfix C).

namespace {
struct CoopPolicyState {
    bool started = false;
    PcCoopStageKey key = {-1, -1, 0.0f}; // stage, day, time of day at the last co-op tick
    unsigned tick = 0; // co-op randomizer updateAI calls since the stage started (1-based)
    PcCoopCursors cursors = {{1, 1, 1, 1}};
    float prevHp[PC_COOP_CAPTAINS] = {};
    bool prevValid[PC_COOP_CAPTAINS] = {};
    // Last decisions, read back by the coop-policy fixture.
    PcCoopHealPick lastHeal = {0, PC_COOP_HEAL_NONE};
    int anchors[32][2] = {}; // (kind, captain) per successful anchored grant
    int anchorCount = 0;
    int deathLinks = 0, lastKilled = 0, lastSquad[PC_COOP_CAPTAINS] = {}, lastLive[PC_COOP_CAPTAINS] = {};
    int deliveries = 0, lastDeliveryColor = -1;
};
CoopPolicyState sCoopPolicy;
// The co-op cooldowns, one per kind with a cooldown, as in single-captain
// play. Like the single-captain function statics they persist across
// stages (sCoopPolicy resets per stage; these do not). Namespace scope so
// the state hash can read them.
float sCoopBombTrapCooldown = 0.0f;
float sCoopProggCooldown = 0.0f;
float sCoopNectarCooldown = 0.0f;
}

// Live captain: the pcIsLastNaviStanding predicate (navi.cpp). A downed
// co-op captain (health at most 1, NaviDeadState survivor branch) is not live.
static bool coopNaviLive(Navi* navi)
{
    return navi && navi->mHealth > 1.0f && navi->getCurrState() && navi->getCurrState()->getID() != NAVISTATE_Dead;
}

static void coopFillCaptains(Navi* const navis[PC_COOP_CAPTAINS], PcCoopCaptain caps[PC_COOP_CAPTAINS])
{
    for (int i = 0; i < PC_COOP_CAPTAINS; ++i) {
        caps[i].id = i + 1;
        caps[i].live = coopNaviLive(navis[i]);
        caps[i].hp = navis[i] ? navis[i]->mHealth : 0.0f;
        caps[i].maxHp = navis[i] ? C_NAVI_PARM(navis[i], mHealth) : 0.0f;
    }
}

// Rule 1 bookkeeping: the previous co-op tick's HP, sampled on every active
// co-op tick whether or not a heal is pending.
static void coopSampleHp(Navi* p1, Navi* p2)
{
    Navi* const navis[PC_COOP_CAPTAINS] = {p1, p2};
    for (int i = 0; i < PC_COOP_CAPTAINS; ++i) {
        sCoopPolicy.prevValid[i] = navis[i] != nullptr;
        sCoopPolicy.prevHp[i] = navis[i] ? navis[i]->mHealth : 0.0f;
    }
}

// Knocks a captain down the way Navi::finishDamage does, refusing when it is
// the last one standing (a test must never reach the game-over path).
static bool coopDownCaptain(Navi* navi)
{
    if (!coopNaviLive(navi) || pcIsLastNaviStanding(navi)) return false;
    navi->mHealth = 0.5f;
    navi->resetStateDamaged();
    navi->mStateMachine->restart(navi);
    navi->mStateMachine->transit(navi, NAVISTATE_Dead);
    return true;
}

// PIKMIN_NETPLAY_TEST_COOP_EVENTS=<file>: scripted test events (grammar in pc_coop_policy.h) at fixed
// co-op ticks, inert when unset. It is honoured only by the netplay build in
// hidden test runs (pc_coop_events_knob_path). It changes sim state, so the
// session folds the file's FNV-1a into the handshake config hash
// (`coopEvents`, gapfix C): a pair whose peers pass different files, or only
// one of them, is refused on config. The file is parsed once per process;
// the tick restarts on every stage entry, so the schedule re-arms each
// stage/day (logged as "armed").
static void coopRunTestEvents(Navi* p1, Navi* p2)
{
    static bool loaded = false;
    static PcCoopEvent events[PC_COOP_EVENTS_MAX];
    static int count = 0;
    if (!loaded) {
        loaded = true;
        if (const char* path = pc_coop_events_knob_path()) {
            const char* why = nullptr;
            int bad = 0;
            count = pc_coop_events_load(path, events, PC_COOP_EVENTS_MAX, &why, &bad);
            if (count < 0) std::printf("[coop-policy] TEST events rejected file=%s reason=%s line=%d\n", path, why ? why : "?", bad);
            else std::printf("[coop-policy] TEST events loaded count=%d\n", count);
            if (count < 0) count = 0;
            std::fflush(stdout);
        }
    }
    if (count > 0 && sCoopPolicy.tick == 1) {
        std::printf("[coop-policy] TEST events armed stage=%d day=%d count=%d\n", sCoopPolicy.key.stage, sCoopPolicy.key.day, count);
        std::fflush(stdout);
    }
    Navi* const navis[PC_COOP_CAPTAINS] = {p1, p2};
    for (int i = 0; i < count; ++i) {
        const PcCoopEvent& ev = events[i];
        if (ev.tick != sCoopPolicy.tick) continue;
        std::printf("[coop-policy] TEST event tick=%u %s\n", sCoopPolicy.tick, ev.text);
        const char* refused = nullptr;
        // Gap-fix K fix1 (#885): the day end sets the clock back, which resets
        // the policy (reason=clock) and re-arms this schedule inside the
        // day-end sequence. The day-end kinds set that sequence up, so they
        // must not mutate it: refuse them until the next stage entry.
        const bool dayEndKind = ev.kind == PC_COOP_EVENT_SQUAD || ev.kind == PC_COOP_EVENT_DISMISS
                             || ev.kind == PC_COOP_EVENT_HOME || ev.kind == PC_COOP_EVENT_SUNSET;
        if (dayEndKind && playerState->inDayEnd()) {
            std::printf("[coop-policy] TEST refused tick=%u %s reason=day-end\n", sCoopPolicy.tick, ev.text);
            std::fflush(stdout);
            continue;
        }
        // A day end started before the captains leave the stage-start
        // sequence (the opening movie, NAVISTATE_Starting) never gives them
        // control: every squad then falls out of formation and is left behind
        // (fix1 probe), which real play cannot reach. Refuse SUNSET there.
        const bool stageStart = gameflow.mMoviePlayer->mIsActive || (p1 && p1->getCurrState()->getID() == NAVISTATE_Starting)
                             || (p2 && p2->getCurrState()->getID() == NAVISTATE_Starting);
        if (ev.kind == PC_COOP_EVENT_SUNSET && stageStart) {
            std::printf("[coop-policy] TEST refused tick=%u %s reason=stage-start\n", sCoopPolicy.tick, ev.text);
            std::fflush(stdout);
            continue;
        }
        if (ev.kind == PC_COOP_EVENT_SUNSET) {
            // Gap-fix K (#885): jump to the day's end hour; RunningModeState::update
            // then runs the ordinary time-expiry day end (cleanupDayEnd, the
            // sunset movie and its Fue event) on both peers from this sim tick.
            gameflow.mWorldClock.setTime(gameflow.mParameters->mEndHour());
            // What the day-end enter paths will see: each captain's stored
            // Onion (-1 = none) and the Pikmin it owns, in its squad or free;
            // near = free ones within the sunset safety range of an Onion or
            // the ship, which enterFreePikmins sends in at cleanupDayEnd.
            int squad[PC_COOP_CAPTAINS] = {}, loose[PC_COOP_CAPTAINS] = {}, near[PC_COOP_CAPTAINS] = {};
            const f32 range = pikiMgr->mPikiParms->mPikiParms.mSunsetSafetyRange();
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* piki = static_cast<Piki*>(*it);
                if (!piki || !piki->isAlive()) continue;
                for (int c = 0; c < PC_COOP_CAPTAINS; ++c) {
                    if (!navis[c] || piki->mNavi != navis[c]) continue;
                    if (piki->mMode == PikiMode::FormationMode) ++squad[c];
                    else if (piki->mMode == PikiMode::FreeMode) {
                        ++loose[c];
                        bool safe = false;
                        for (int color = 0; color < PikiColorCount && !safe; ++color) {
                            GoalItem* goal = itemMgr->getContainer(color);
                            safe = goal && qdist2(goal->mSRT.t.x, goal->mSRT.t.z, piki->mSRT.t.x, piki->mSRT.t.z) <= range;
                        }
                        if (!safe && itemMgr->getUfo()) {
                            const Vector3f pos = itemMgr->getUfo()->getGoalPos();
                            safe = qdist2(pos.x, pos.z, piki->mSRT.t.x, piki->mSRT.t.z) <= range;
                        }
                        if (safe) ++near[c];
                    }
                }
            }
            std::printf("[coop-policy] TEST sunset tick=%u p1goal=%d p2goal=%d squad=%d,%d free=%d,%d near=%d,%d\n",
                sCoopPolicy.tick, (p1 && p1->mGoalItem) ? int(p1->mGoalItem->mOnionColour) : -1,
                (p2 && p2->mGoalItem) ? int(p2->mGoalItem->mOnionColour) : -1, squad[0], squad[1], loose[0], loose[1], near[0],
                near[1]);
            std::fflush(stdout);
            continue;
        }
        Navi* navi = navis[ev.captain - 1];
        if (!coopNaviLive(navi)) refused = "not-live";
        else if (ev.kind == PC_COOP_EVENT_HP) {
            const float hp = ev.fraction * C_NAVI_PARM(navi, mHealth);
            if (hp <= 1.0f) refused = "hp-at-most-1";
            else navi->mHealth = hp;
        } else if (ev.kind == PC_COOP_EVENT_SQUAD) {
            // Gap-fix K (#885): the first <count> Pikmin (pikiMgr order) in the
            // other captain's squad join this one; they then follow and belong
            // to it. Fix1: the squad action is abandoned while mNavi is still
            // the old captain, so ActCrowd::cleanup decrements that captain's
            // plate count (it reads mPiki->mNavi) as it releases the slot, the
            // order pc_p2_captain.cpp live_prepare_capture keeps. Changing
            // mNavi first left the old plate's count too high and the new
            // one's at 0 with slots taken, so the new captain's plate walked
            // nobody (Navi::releasePikis, the Fue enter).
            Navi* from = navis[2 - ev.captain];
            int moved = 0;
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                if (moved >= ev.count) break;
                Piki* piki = static_cast<Piki*>(*it);
                if (!from || !piki || !piki->isAlive() || piki->mNavi != from || piki->mMode != PikiMode::FormationMode) continue;
                piki->mActiveAction->abandon(nullptr);
                piki->mNavi = navi;
                piki->changeMode(PikiMode::FormationMode, navi);
                ++moved;
            }
            std::printf("[coop-policy] TEST squad tick=%u captain=%d moved=%d\n", sCoopPolicy.tick, ev.captain, moved);
            if (!moved) refused = "no-squad";
        } else if (ev.kind == PC_COOP_EVENT_DISMISS) {
            // The captain's squad goes free where it stands (FreeMode, still
            // owned by it), through the game's own dismiss (Navi::releasePikis,
            // which walks the captain's formation plate). released = squad
            // members owned by it before minus after.
            auto squadOf = [](Navi* owner) {
                int n = 0;
                Iterator it(pikiMgr);
                CI_LOOP(it) {
                    Piki* piki = static_cast<Piki*>(*it);
                    if (piki && piki->isAlive() && piki->mNavi == owner && piki->mMode == PikiMode::FormationMode) ++n;
                }
                return n;
            };
            const int before = squadOf(navi);
            navi->releasePikis();
            const int kept = squadOf(navi);
            std::printf("[coop-policy] TEST dismiss tick=%u captain=%d released=%d kept=%d\n", sCoopPolicy.tick, ev.captain, before - kept,
                kept);
            if (before - kept <= 0) refused = "none-released";
        } else if (ev.kind == PC_COOP_EVENT_HOME) {
            // The captain's free Pikmin stand by the Onion of their colour (the
            // ship when that Onion is absent), 60 units out, well inside the
            // sunset safety range, so enterFreePikmins picks them up.
            static const f32 ringX[8] = {60.0f, 0.0f, -60.0f, 0.0f, 42.0f, -42.0f, 42.0f, -42.0f};
            static const f32 ringZ[8] = {0.0f, 60.0f, 0.0f, -60.0f, 42.0f, 42.0f, -42.0f, -42.0f};
            int placed = 0;
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* piki = static_cast<Piki*>(*it);
                if (!piki || !piki->isAlive() || piki->mNavi != navi || piki->mMode != PikiMode::FreeMode) continue;
                Vector3f base;
                if (GoalItem* goal = itemMgr->getContainer(piki->mColor)) base = goal->mSRT.t;
                else if (itemMgr->getUfo()) base = itemMgr->getUfo()->getGoalPos();
                else continue;
                Vector3f pos(base.x + ringX[placed % 8], 0.0f, base.z + ringZ[placed % 8]);
                pos.y = mapMgr->getMinY(pos.x, pos.z, true);
                piki->resetPosition(pos);
                ++placed;
            }
            std::printf("[coop-policy] TEST home tick=%u captain=%d placed=%d\n", sCoopPolicy.tick, ev.captain, placed);
            if (!placed) refused = "none-free";
        } else if (!coopDownCaptain(navi)) refused = "last-standing";
        if (refused) std::printf("[coop-policy] TEST refused tick=%u %s reason=%s\n", sCoopPolicy.tick, ev.text, refused);
        std::fflush(stdout);
    }
}

// PIKMIN_NETPLAY_TEST_COOP_PERTURB=<tick> (pc_coop_perturb_knob_tick: netplay
// build, hidden test runs only; deliberately not in the config hash): at
// that co-op tick this peer alone flips its Flower Shower cursor. Nothing
// else reads the cursor until the next Flower Shower, so only the state-hash
// fold can see the difference: the desync-detection proof (gapfix C).
static void coopTestPerturb()
{
    static const unsigned perturbTick = pc_coop_perturb_knob_tick();
    if (!perturbTick || sCoopPolicy.tick != perturbTick) return;
    int& next = sCoopPolicy.cursors.next[PC_COOP_ANCHOR_FLOWERS];
    const int before = next;
    next = before == 1 ? 2 : 1;
    std::printf("[coop-policy] TEST perturb tick=%u kind=FLOWERS cursor=%d->%d\n", sCoopPolicy.tick, before, next);
    std::fflush(stdout);
}

// Rule 2: try the cursor's captain, then the other live captain in the same
// tick; after a successful consume the cursor moves past the captain used.
// The loop itself is pc_coop_anchor_try (unit-tested); this adapter only
// maps captain ids to Navis and logs. When a grant lands on a captain other
// than the cursor's, the captains passed over are logged first as
// ANCHOR_SKIP (not-live, or placement with the failure detail), so every
// fallback is provable from the log. An attempt where nobody could be placed
// logs nothing (it retries next tick, which would flood the log).
template <typename Place>
static bool coopAnchored(PcCoopAnchorKind kind, Navi* const navis[PC_COOP_CAPTAINS], const bool live[PC_COOP_CAPTAINS], Place place)
{
    struct Ctx {
        Navi* const* navis;
        Place* place;
        char why[PC_COOP_CAPTAINS][sizeof(sPlaceWhy)];
    };
    Ctx ctx = {navis, &place, {}};
    const PcCoopAnchorAttempt attempt = pc_coop_anchor_try(sCoopPolicy.cursors, kind, live,
        [](int captain, void* raw) -> PcCoopPlaceResult {
            Ctx& c = *static_cast<Ctx*>(raw);
            sPlaceWhy[0] = '\0';
            const PcCoopPlaceResult result = (*c.place)(c.navis[captain - 1]);
            if (result == PC_COOP_PLACE_FAILED) std::snprintf(c.why[captain - 1], sizeof(c.why[0]), "%s", sPlaceWhy);
            return result;
        },
        &ctx);
    if (attempt.captain <= 0) return false;
    for (int i = 0; i < attempt.skipCount; ++i) {
        const int skipped = attempt.skipCaptain[i];
        Navi* navi = navis[skipped - 1];
        if (attempt.skipReason[i] == PC_COOP_SKIP_PLACEMENT)
            std::printf("[coop-policy] ANCHOR_SKIP kind=%s captain=%d reason=placement why=%s x=%.1f z=%.1f\n", pc_coop_anchor_name(kind),
                skipped, ctx.why[skipped - 1][0] ? ctx.why[skipped - 1] : "?", navi ? navi->mSRT.t.x : 0.0f, navi ? navi->mSRT.t.z : 0.0f);
        else
            std::printf("[coop-policy] ANCHOR_SKIP kind=%s captain=%d reason=not-live\n", pc_coop_anchor_name(kind), skipped);
    }
    if (sCoopPolicy.anchorCount < 32) {
        sCoopPolicy.anchors[sCoopPolicy.anchorCount][0] = kind;
        sCoopPolicy.anchors[sCoopPolicy.anchorCount][1] = attempt.captain;
        ++sCoopPolicy.anchorCount;
    }
    std::printf("[coop-policy] ANCHOR kind=%s captain=%d next=%d live=%d%d\n", pc_coop_anchor_name(kind), attempt.captain, attempt.next,
        int(live[0]), int(live[1]));
    std::fflush(stdout);
    return true;
}

// Rule 1: heal target. The last step of randomizerApplyBenefitsCoop, split
// out so the coop-policy fixture can drive the heal decision on its own
// without re-running the anchored grants (and their cooldowns) in the same
// tick. It keeps no state besides the fixture read-back.
static void coopApplyHeal(Navi* p1, Navi* p2)
{
    Navi* const navis[PC_COOP_CAPTAINS] = {p1, p2};
    if (!pc_randomizer_ready()) return;
    PcCoopCaptain caps[PC_COOP_CAPTAINS];
    coopFillCaptains(navis, caps);
    const PcCoopHealPick heal = pc_coop_pick_heal(caps, sCoopPolicy.prevHp, sCoopPolicy.prevValid);
    if (heal.captain && pc_randomizer_consume_benefit(PC_BENEFIT_HEAL)) {
        Navi* target = navis[heal.captain - 1];
        const float before = target->mHealth;
        target->mHealth = C_NAVI_PARM(target, mHealth);
        sCoopPolicy.lastHeal = heal;
        std::printf("[coop-policy] HEAL captain=%d reason=%s hp=%.1f->%.1f\n", heal.captain,
            pc_coop_heal_reason_name(heal.reason), before, target->mHealth);
        std::fflush(stdout);
    }
}

// Co-op counterpart of randomizerApplyBenefits: rule 3 (any live captain),
// rule 2 (round-robin anchors) and rule 1 (heal target). Cooldowns stay one
// per kind, as in single-captain play. The placements, BOMBS and DELIVERY are
// the shared helpers.
static void randomizerApplyBenefitsCoop(Navi* p1, Navi* p2, MapMgr* map)
{
    Navi* const navis[PC_COOP_CAPTAINS] = {p1, p2};
    const bool live[PC_COOP_CAPTAINS] = {coopNaviLive(p1), coopNaviLive(p2)};
    if (!pc_randomizer_ready() || !(live[0] || live[1]) || !itemMgr || !pikiMgr) return;
    sCoopBombTrapCooldown = std::max(0.0f, sCoopBombTrapCooldown - gsys->getFrameTime());
    if (map && sCoopBombTrapCooldown == 0.0f && pc_randomizer_benefit_pending(PC_BENEFIT_BOMB_TRAP))
        coopAnchored(PC_COOP_ANCHOR_BOMB_TRAP, navis, live, [&](Navi* navi) { return randomizerBombTrapAt(navi, map, sCoopBombTrapCooldown); });
    sCoopProggCooldown = std::max(0.0f, sCoopProggCooldown - gsys->getFrameTime());
    if (map && tekiMgr && sCoopProggCooldown == 0.0f && pc_randomizer_benefit_pending(PC_BENEFIT_PROGG) && !randomizerProggAlive())
        coopAnchored(PC_COOP_ANCHOR_PROGG, navis, live, [&](Navi* navi) { return randomizerProggAt(navi, map, sCoopProggCooldown); });
    if (bossMgr && pc_randomizer_benefit_pending(PC_BENEFIT_PRERELEASE) && bossMgr->prereleaseSeconds() <= 0.0f)
        coopAnchored(PC_COOP_ANCHOR_PRERELEASE, navis, live, [](Navi* navi) {
            if (!navi->getCurrState() || navi->getCurrState()->getID() != NAVISTATE_Walk) {
                std::snprintf(sPlaceWhy, sizeof(sPlaceWhy), "not-walking");
                return PC_COOP_PLACE_FAILED;
            }
            return bossMgr->beginPrereleaseTrap() ? PC_COOP_PLACE_CONSUMED : PC_COOP_PLACE_STOP;
        });
    // BOMBS and DELIVERY are Onion-anchored (no captain), so only rule 3 applies.
    randomizerBombDelivery(map);
    const int delivered = randomizerPikminDelivery();
    if (delivered >= 0) {
        ++sCoopPolicy.deliveries;
        sCoopPolicy.lastDeliveryColor = delivered;
    }
    sCoopNectarCooldown = std::max(0.0f, sCoopNectarCooldown - gsys->getFrameTime());
    if (map && sCoopNectarCooldown == 0.0f && pc_randomizer_benefit_pending(PC_BENEFIT_FLOWERS))
        coopAnchored(PC_COOP_ANCHOR_FLOWERS, navis, live, [&](Navi* navi) { return randomizerFlowersAt(navi, map, sCoopNectarCooldown); });
    randomizerApplyMaturity();
    coopApplyHeal(p1, p2);
}

// Rule 4: a received DeathLink takes one unit from the combined field pool,
// whichever captain the Pikmin follow; one consume per link (the shared
// randomizerApplyDeathLink), logged with the split by owner.
static void randomizerApplyDeathLinkCoop(Navi* p1, Navi* p2)
{
    int squad[PC_COOP_CAPTAINS] = {};
    const int killed = randomizerApplyDeathLink(p1, p2, squad);
    if (killed < 0) return;
    sCoopPolicy.lastLive[0] = coopNaviLive(p1);
    sCoopPolicy.lastLive[1] = coopNaviLive(p2);
    sCoopPolicy.lastKilled = killed;
    sCoopPolicy.lastSquad[0] = squad[0];
    sCoopPolicy.lastSquad[1] = squad[1];
    ++sCoopPolicy.deathLinks;
    std::printf("[coop-policy] DEATHLINK killed=%d p1=%d p2=%d squadP1=%d squadP2=%d\n", killed,
        sCoopPolicy.lastLive[0], sCoopPolicy.lastLive[1], squad[0], squad[1]);
    std::fflush(stdout);
}

// The co-op randomizer block of GameCoreSection::updateAI. It runs the same
// shared steps as the single-captain block (tick gate, prerelease clock,
// BOMBS, DELIVERY, DeathLink, observations, exploration); only the
// captain-dependent decisions differ (anchors, heal target, any-live).
static void randomizerUpdateCoop(Navi* p1, Navi* p2, MapMgr* map)
{
    const PcCoopStageKey key = {flowCont.mCurrentStage ? int(flowCont.mCurrentStage->mStageID) : -1,
        int(gameflow.mWorldClock.mCurrentDay), gameflow.mWorldClock.mTimeOfDay};
    const char* resetReason = nullptr;
    if (pc_coop_stage_changed(sCoopPolicy.started, sCoopPolicy.key, key, &resetReason)) {
        // A new stage entry: every cursor back on P1, no HP sample yet, tick 0.
        // "clock" covers a repeated day 29 on the same stage and a same-day
        // reload, where stage and day do not change.
        sCoopPolicy = CoopPolicyState();
        pc_coop_cursors_reset(sCoopPolicy.cursors);
        sCoopPolicy.started = true;
        std::printf("[coop-policy] RESET stage=%d day=%d reason=%s\n", key.stage, key.day, resetReason);
        std::fflush(stdout);
    }
    sCoopPolicy.key = key;
    ++sCoopPolicy.tick;
    coopRunTestEvents(p1, p2);
    coopTestPerturb();
    const bool anyLive = coopNaviLive(p1) || coopNaviLive(p2);
    const bool active = randomizerTickOpen() && anyLive;
    randomizerPrereleaseClock(!anyLive, active);
    if (!active || playerState->mInDayEnd) return;
    randomizerApplyBenefitsCoop(p1, p2, map);
    coopSampleHp(p1, p2);
    randomizerApplyDeathLinkCoop(p1, p2);
    randomizerObserveWorld();
    // Exploration stays anchored to P1 and needs P1 live, so a downed P1's
    // position never produces a Land check.
    if (coopNaviLive(p1)) randomizerObserveExploration(p1);
}

// Netplay gapfix C (#885): the co-op policy's sim state for the per-tick
// state hash, which folds it into its rand sub-hash (pc_state_hash.cpp calls
// this through a weak reference). False, with nothing to fold, unless co-op
// is active and the co-op branch has run, so single-captain hashes are
// unchanged. Rollback or a late join would restore exactly these fields.
bool pc_coop_policy_state_hash(uint64_t* out)
{
    if (!out || !pc_coop_active() || !sCoopPolicy.started) return false;
    PcCoopHashState state;
    std::memset(&state, 0, sizeof(state));
    state.started = sCoopPolicy.started;
    state.key = sCoopPolicy.key;
    state.tick = sCoopPolicy.tick;
    state.cursors = sCoopPolicy.cursors;
    for (int i = 0; i < PC_COOP_CAPTAINS; ++i) {
        state.prevHp[i] = sCoopPolicy.prevHp[i];
        state.prevValid[i] = sCoopPolicy.prevValid[i];
    }
    state.cooldown[0] = sCoopBombTrapCooldown;
    state.cooldown[1] = sCoopProggCooldown;
    state.cooldown[2] = sCoopNectarCooldown;
    *out = pc_coop_state_hash(state);
    return true;
}

#if defined(PIKMIN_RANDOMIZER_TEST_HOOKS)
// M4 D-policy coop-policy fixture (PIKMIN_RANDOMIZER_TEST_SCRIPT=coop-policy,
// PIKMIN_COOP_POLICY_CASE=<case>, launched with --coop). Isolated fixture
// process: sets captain HP / down states directly, drives the co-op heal
// step (coopApplyHeal) directly and lets the production co-op tick make the
// anchored and DeathLink decisions, aborts on any
// violation and exits 0 after printing TEST_ONLY coop_policy_pass.
// Runner protocol: `TEST_ONLY coop_policy_phase case=<c> n=<k>` asks the
// runner to write phase k's state line (tools/netplay/coop_policy_native.py).
static void coopFixtureRequire(bool ok, const char* what)
{
    if (ok) return;
    std::printf("TEST_ONLY coop_policy_fail %s tick=%u\n", what, sCoopPolicy.tick);
    std::fflush(stdout);
    std::abort();
}

static void coopFixtureHp(Navi* navi, float fraction) { navi->mHealth = C_NAVI_PARM(navi, mHealth) * fraction; }

static bool coopFixtureFull(Navi* navi) { return navi->mHealth == C_NAVI_PARM(navi, mHealth); }

static void coopFixturePhase(const char* name, int n)
{
    std::printf("TEST_ONLY coop_policy_phase case=%s n=%d\n", name, n);
    std::fflush(stdout);
}

static int coopFixtureAnchors(int kind, char* out, size_t size)
{
    int n = 0;
    size_t used = 0;
    out[0] = '\0';
    for (int i = 0; i < sCoopPolicy.anchorCount; ++i) {
        if (sCoopPolicy.anchors[i][0] != kind) continue;
        used += std::snprintf(out + used, used < size ? size - used : 0, "%s%d", n ? "," : "", sCoopPolicy.anchors[i][1]);
        ++n;
    }
    if (!n) std::snprintf(out, size, "-");
    return n;
}

static void coopFixtureHealOnce(Navi* p1, Navi* p2, MapMgr* map, int captain, PcCoopHealReason reason, const char* what)
{
    (void)map; // the heal step alone: no anchored grant or cooldown runs twice in this tick
    sCoopPolicy.lastHeal = {0, PC_COOP_HEAL_NONE};
    randomizerApplyMaturity();
    coopApplyHeal(p1, p2);
    coopFixtureRequire(sCoopPolicy.lastHeal.captain == captain && sCoopPolicy.lastHeal.reason == reason, what);
}

static void coopPolicyFixture(Navi* p1, Navi* p2, MapMgr* map, int initialColor)
{
    static const char* name = std::getenv("PIKMIN_COOP_POLICY_CASE");
    static int step = 0;
    static unsigned waitTick = 0, deadline = 0;
    static int stock = 0;
    const float max1 = C_NAVI_PARM(p1, mHealth), max2 = C_NAVI_PARM(p2, mHealth);
    coopFixtureRequire(name != nullptr, "PIKMIN_COOP_POLICY_CASE unset");
    const std::string c = name;
    if (step == 0) {
        std::printf("TEST_ONLY coop_policy_ready case=%s tick=%u color=%d p1_hp=%.1f/%.1f p2_hp=%.1f/%.1f p1_live=%d p2_live=%d\n", name,
            sCoopPolicy.tick, initialColor, p1->mHealth, max1, p2->mHealth, max2, int(coopNaviLive(p1)), int(coopNaviLive(p2)));
        std::fflush(stdout);
        coopFixtureRequire(coopNaviLive(p1) && coopNaviLive(p2) && coopFixtureFull(p1) && coopFixtureFull(p2), "both captains live at full HP");
    }
    if (c == "heal-p2-only") {
        // P1 full, P2 at 50% -> P2 healed, P1 untouched. Legacy (mNavi only) would not heal.
        coopFixtureRequire(pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "heal pending");
        coopFixtureHp(p2, 0.5f);
        const bool legacyWouldHeal = p1->mHealth < max1;
        randomizerApplyMaturity();
    coopApplyHeal(p1, p2);
        coopFixtureRequire(sCoopPolicy.lastHeal.captain == 2, "heal went to P2");
        coopFixtureRequire(coopFixtureFull(p1) && coopFixtureFull(p2), "P2 full again, P1 untouched");
        coopFixtureRequire(!pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "exactly one heal consumed");
        std::printf("TEST_ONLY coop_policy_pass case=%s captain=2 reason=%s p1_hp=%.1f p2_hp=%.1f legacy_would_heal=%d\n", name,
            pc_coop_heal_reason_name(sCoopPolicy.lastHeal.reason), p1->mHealth, p2->mHealth, int(legacyWouldHeal));
    } else if (c == "heal-lowest") {
        // Both hurt, no trigger this tick (HP sampled after setting it).
        coopFixtureRequire(pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "heal pending");
        coopFixtureHp(p1, 0.3f); coopFixtureHp(p2, 0.6f); coopSampleHp(p1, p2);
        coopFixtureHealOnce(p1, p2, map, 1, PC_COOP_HEAL_LOWEST, "P1 30% P2 60% -> P1 lowest");
        coopFixtureRequire(coopFixtureFull(p1) && p2->mHealth == 0.6f * max2, "P1 healed, P2 unchanged");
        coopFixtureHp(p1, 0.6f); coopFixtureHp(p2, 0.3f); coopSampleHp(p1, p2);
        coopFixtureHealOnce(p1, p2, map, 2, PC_COOP_HEAL_LOWEST, "P1 60% P2 30% -> P2 lowest");
        coopFixtureRequire(coopFixtureFull(p2) && p1->mHealth == 0.6f * max1, "P2 healed, P1 unchanged");
        coopFixtureHp(p1, 0.5f); coopFixtureHp(p2, 0.5f); coopSampleHp(p1, p2);
        coopFixtureHealOnce(p1, p2, map, 1, PC_COOP_HEAL_LOWEST, "tie -> P1");
        coopFixtureRequire(coopFixtureFull(p1) && p2->mHealth == 0.5f * max2, "tie healed P1 only");
        coopFixtureRequire(!pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "three heals consumed");
        std::printf("TEST_ONLY coop_policy_pass case=%s p1_30_p2_60=1 p1_60_p2_30=2 tie=1 reason=lowest\n", name);
    } else if (c == "heal-trigger") {
        coopFixtureRequire(pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "heal pending");
        sCoopPolicy.lastHeal = {0, PC_COOP_HEAL_NONE};
        randomizerApplyMaturity();
    coopApplyHeal(p1, p2);
        coopFixtureRequire(sCoopPolicy.lastHeal.captain == 0 && pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "full HP: heal stays pending");
        coopFixtureHp(p2, 0.5f); // P2 takes damage since the last sample
        coopFixtureHealOnce(p1, p2, map, 2, PC_COOP_HEAL_TRIGGER, "P2 damaged -> P2 trigger");
        coopFixtureRequire(coopFixtureFull(p1) && coopFixtureFull(p2), "P2 healed");
        // Discriminating variant: P1 steady at 30%, P2 drops to 60% -> P2 by trigger, not P1 by lowest.
        coopFixtureHp(p1, 0.3f); coopSampleHp(p1, p2);
        coopFixtureHp(p2, 0.6f);
        coopFixtureHealOnce(p1, p2, map, 2, PC_COOP_HEAL_TRIGGER, "P2 dropped while P1 lower -> P2 trigger");
        coopFixtureRequire(coopFixtureFull(p2) && p1->mHealth == 0.3f * max1, "P2 healed, P1 left at 30%");
        coopFixtureRequire(!pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "two heals consumed");
        std::printf("TEST_ONLY coop_policy_pass case=%s full_pending=1 p2_damaged=2 p2_dropped_p1_lower=2 reason=trigger\n", name);
    } else if (c == "heal-p1-down") {
        if (step == 0) {
            coopFixtureRequire(pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "heal pending");
            coopFixtureRequire(coopDownCaptain(p1), "P1 knocked down");
            step = 1; waitTick = sCoopPolicy.tick + 10;
            return;
        }
        if (sCoopPolicy.tick < waitTick) return;
        coopFixtureRequire(!coopNaviLive(p1) && coopNaviLive(p2), "P1 downed, P2 live");
        coopFixtureRequire(pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "downed P1 was not healed by the live path");
        const float p1Hp = p1->mHealth;
        coopFixtureHp(p2, 0.5f);
        randomizerApplyMaturity();
    coopApplyHeal(p1, p2);
        coopFixtureRequire(sCoopPolicy.lastHeal.captain == 2 && coopFixtureFull(p2), "heal went to P2");
        coopFixtureRequire(p1->mHealth == p1Hp && !coopNaviLive(p1), "P1 never healed");
        coopFixtureRequire(!pc_randomizer_benefit_pending(PC_BENEFIT_HEAL), "one heal consumed");
        std::printf("TEST_ONLY coop_policy_pass case=%s captain=2 reason=%s p1_hp=%.1f p1_live=0 p2_hp=%.1f\n", name,
            pc_coop_heal_reason_name(sCoopPolicy.lastHeal.reason), p1->mHealth, p2->mHealth);
    } else if (c == "anchors" || c == "any-alive") {
        const bool anyAlive = c == "any-alive";
        auto onionStock = []() {
            int total = 0;
            for (int color = 0; color < 3; ++color)
                if (GoalItem* onion = itemMgr->getContainer(color)) total += onion->getTotalStorePikis();
            return total;
        };
        if (step == 0) {
            stock = onionStock();
            // First-bomb, first-nectar and low-health (a blast below 25% HP)
            // tutorials are modal text windows that would hold a headless run.
            playerState->mDemoFlags.setFlagOnly(DEMOFLAG_FirstBombExplode);
            playerState->mDemoFlags.setFlagOnly(DEMOFLAG_FirstNectar);
            playerState->mDemoFlags.setFlagOnly(DEMOFLAG_OlimarLowHealth);
            if (anyAlive) coopFixtureRequire(coopDownCaptain(p1), "P1 knocked down");
            step = 1; waitTick = sCoopPolicy.tick + 10;
            return;
        }
        // Keep live captains topped up so a bomb blast never downs one (P2 is
        // the last one standing in any-alive: a down would end the stage).
        if (coopNaviLive(p1)) p1->mHealth = max1;
        if (coopNaviLive(p2)) p2->mHealth = max2;
        if (step == 1) {
            if (sCoopPolicy.tick < waitTick) return;
            coopFixtureRequire(coopNaviLive(p2) && coopNaviLive(p1) != anyAlive, anyAlive ? "P1 downed, P2 live" : "both live");
            coopFixtureRequire(sCoopPolicy.anchorCount == 0, "no grant before the phase");
            coopFixturePhase(name, 1);
            step = 2; deadline = sCoopPolicy.tick + 2400;
            return;
        }
        char bomb[64], flowers[64], progg[64], pre[64];
        const int nb = coopFixtureAnchors(PC_COOP_ANCHOR_BOMB_TRAP, bomb, sizeof(bomb));
        const int nf = coopFixtureAnchors(PC_COOP_ANCHOR_FLOWERS, flowers, sizeof(flowers));
        const int np = coopFixtureAnchors(PC_COOP_ANCHOR_PROGG, progg, sizeof(progg));
        const int nr = coopFixtureAnchors(PC_COOP_ANCHOR_PRERELEASE, pre, sizeof(pre));
        const int added = onionStock() - stock;
        if (sCoopPolicy.tick >= deadline) {
            std::printf("TEST_ONLY coop_policy_timeout case=%s bomb_trap=%s flowers=%s progg=%s prerelease=%s stock_added=%d pending=%d%d%d%d%d\n",
                name, bomb, flowers, progg, pre, added, int(pc_randomizer_benefit_pending(PC_BENEFIT_BOMB_TRAP)),
                int(pc_randomizer_benefit_pending(PC_BENEFIT_FLOWERS)), int(pc_randomizer_benefit_pending(PC_BENEFIT_PROGG)),
                int(pc_randomizer_benefit_pending(PC_BENEFIT_PRERELEASE)), int(pc_randomizer_benefit_pending(PC_BENEFIT_DELIVERY)));
            coopFixtureRequire(false, "grants did not all land in time");
        }
        if (anyAlive) {
            if (nb < 1 || nf < 1 || sCoopPolicy.deliveries < 1) return;
            coopFixtureRequire(!std::strcmp(bomb, "2") && !std::strcmp(flowers, "2"), "any-alive anchors on P2");
            coopFixtureRequire(sCoopPolicy.deliveries == 1 && !pc_randomizer_benefit_pending(PC_BENEFIT_DELIVERY), "one delivery with P1 down");
            coopFixtureRequire(!coopNaviLive(p1), "P1 still downed");
            std::printf("TEST_ONLY coop_policy_pass case=%s p1_live=0 delivery=1 delivery_color=%d onion_stock_delta=%d flowers=%s bomb_trap=%s\n",
                name, sCoopPolicy.lastDeliveryColor, added, flowers, bomb);
        } else {
            // FoH has no Candypop/Geyser for the prerelease trap; the runner
            // sets PIKMIN_COOP_POLICY_PRERELEASE=1 on a stage that has them.
            const char* wantPre = std::getenv("PIKMIN_COOP_POLICY_PRERELEASE");
            const bool needPre = wantPre && !std::strcmp(wantPre, "1");
            if (nb < 3 || nf < 2 || np < 1 || (needPre && nr < 1)) return;
            coopFixtureRequire(!std::strcmp(bomb, "1,2,1"), "bomb traps alternate 1,2,1");
            coopFixtureRequire(!std::strcmp(flowers, "1,2"), "flowers alternate 1,2");
            coopFixtureRequire(coopNaviLive(p1) && coopNaviLive(p2), "both captains still live");
            std::printf("TEST_ONLY coop_policy_pass case=%s bomb_trap=%s flowers=%s progg=%s prerelease=%s next=%d,%d,%d,%d\n", name,
                bomb, flowers, progg, pre, sCoopPolicy.cursors.next[0], sCoopPolicy.cursors.next[1], sCoopPolicy.cursors.next[2],
                sCoopPolicy.cursors.next[3]);
        }
    } else if (c == "deathlink-p1-down") {
        if (step == 0) {
            // Split the field squad: every other Pikmin in P1's squad moves to P2.
            // Gap-fix K fix1 (#885): abandon the squad action while mNavi is
            // still P1, so ActCrowd::cleanup decrements P1's plate count, not
            // P2's (as the SQUAD test event does).
            int moved = 0, index = 0;
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* piki = static_cast<Piki*>(*it);
                if (!piki || !piki->isAlive() || piki->mNavi != p1 || piki->mMode != PikiMode::FormationMode) continue;
                if (index++ % 2) continue;
                piki->mActiveAction->abandon(nullptr);
                piki->mNavi = p2;
                piki->changeMode(PikiMode::FormationMode, p2);
                ++moved;
            }
            coopFixtureRequire(moved >= 2, "moved Pikmin into P2's squad");
            coopFixtureRequire(coopDownCaptain(p1), "P1 knocked down");
            step = 1; waitTick = sCoopPolicy.tick + 10;
            return;
        }
        int owned[PC_COOP_CAPTAINS] = {}, dying = 0;
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (!piki) continue;
            if (piki->getState() == PIKISTATE_Dying) { ++dying; continue; }
            if (!piki->isAlive()) continue;
            if (piki->mNavi == p1) ++owned[0];
            else if (piki->mNavi == p2) ++owned[1];
        }
        if (step == 1) {
            if (sCoopPolicy.tick < waitTick) return;
            coopFixtureRequire(!coopNaviLive(p1) && coopNaviLive(p2), "P1 downed, P2 live");
            coopFixtureRequire(owned[0] >= 2 && owned[1] >= 2, "Pikmin in both squads");
            coopFixtureRequire(pc_randomizer_deathlink_casualties() == 0 && sCoopPolicy.deathLinks == 0, "no link pending yet");
            std::printf("TEST_ONLY coop_policy_squads p1=%d p2=%d\n", owned[0], owned[1]);
            coopFixturePhase(name, 1);
            step = 2; deadline = sCoopPolicy.tick + 2400;
            return;
        }
        if (sCoopPolicy.tick >= deadline) coopFixtureRequire(false, "DeathLink never applied");
        if (sCoopPolicy.deathLinks == 0) return;
        coopFixtureRequire(sCoopPolicy.deathLinks == 1, "exactly one link applied");
        coopFixtureRequire(sCoopPolicy.lastKilled == 3, "killed = unit 3 from the combined pool");
        coopFixtureRequire(sCoopPolicy.lastLive[0] == 0 && sCoopPolicy.lastLive[1] == 1, "applied while P1 down");
        coopFixtureRequire(sCoopPolicy.lastSquad[0] + sCoopPolicy.lastSquad[1] == 3 && sCoopPolicy.lastSquad[1] >= 1,
            "casualties include P2-owned Pikmin");
        coopFixtureRequire(pc_randomizer_deathlink_casualties() == 0, "pending link consumed (pending 1 -> 0)");
        coopFixtureRequire(dying >= 3, "three Pikmin in the dying state");
        std::printf("TEST_ONLY coop_policy_pass case=%s killed=%d p1=0 p2=1 squadP1=%d squadP2=%d dying=%d left_p1=%d left_p2=%d pending=0\n", name,
            sCoopPolicy.lastKilled, sCoopPolicy.lastSquad[0], sCoopPolicy.lastSquad[1], dying, owned[0], owned[1]);
    } else {
        coopFixtureRequire(false, "unknown PIKMIN_COOP_POLICY_CASE");
    }
    std::fflush(stdout);
    // Isolated fixture process; never continue a synthetic session. _Exit skips
    // static destructors, which crashed one exit(0) mid-frame (0xC0000005).
    std::_Exit(0);
}
#endif

// TEST_ONLY (issue #1034): PIKMIN_TEST_ONLY_PELLET_BONUS=1 spawns, around every Onion that
// exists, a matching-colour and a non-matching-colour number pellet of each size (1/5/10/20)
// and sends them through the normal absorb path (Pellet::startGoal -> PelletGoalState ->
// GoalItem::suckMe), which logs "[pellet] onion=... seeds=... matching=...". Inert unless set.
static void pelletBonusTestTick()
{
    static const char* const modeEnv = std::getenv("PIKMIN_TEST_ONLY_PELLET_BONUS");
    static const bool enabled = modeEnv != nullptr;
    // "carry": use real carriers (the full carry path incl. ActTransport::decideGoal) instead of startGoal.
    static const bool carryMode = modeEnv && !std::strcmp(modeEnv, "carry");
    static int readyFrames = 0;
    static bool done = false;
    if (!enabled || done || !itemMgr || !pelletMgr || !mapMgr || gameflow.mMoviePlayer->mIsActive || gameflow.mPauseAll) return;
    bool any = false;
    for (int c = 0; c < 3; ++c) any = any || itemMgr->getContainer(c);
    if (!any) return;
    if (++readyFrames < 120) return;
    done = true;
    if (modeEnv && !std::strcmp(modeEnv, "show")) {
        // Visual check: every colour x size laid out on the ground around the first captain (pellet colour
        // as drawn vs the data logged here), never delivered.
        Navi* navi = naviMgr ? naviMgr->getNavi(0) : nullptr;
        if (!navi) return;
        for (int pcolor = 0; pcolor < 3; ++pcolor) {
            for (int size = 0; size < 4; ++size) {
                Pellet* pelt = pelletMgr->newNumberPellet(pcolor, size);
                if (!pelt) continue;
                const f32 x = navi->mSRT.t.x + 60.0f * f32(size - 1.5f);
                const f32 z = navi->mSRT.t.z + 70.0f + 55.0f * f32(pcolor);
                pelt->init(Vector3f(x, mapMgr->getMinY(x, z, true) + 5.0f, z));
                pelt->startAI(0);
                const f32 scale = pelt->mConfig->mPelletScale();
                pelt->mSRT.s.set(scale, scale, scale);
                pelt->mStateMachine->transit(pelt, 0);
                std::printf("[pellet-test] show pcolor=%d size=%d model=%s cfg_type=%d cfg_pcolor=%d\n", pcolor, size,
                    pelt->mConfig->mModelId.mStringID, int(pelt->mConfig->mPelletType()), int(pelt->mConfig->mPelletColor()));
            }
        }
        std::fflush(stdout);
        return;
    }
    if (carryMode) {
        // One 1-pellet per (carrier colour, pellet colour); one Pikmin recoloured to the carrier colour
        // carries it to the Onion ActTransport::decideGoal picks (Onions that do not exist are skipped).
        Piki* crew[16];
        int available = 0;
        Iterator pikis(pikiMgr);
        CI_LOOP(pikis) {
            Piki* piki = static_cast<Piki*>(*pikis);
            if (piki && piki->isAlive() && available < 16) crew[available++] = piki;
        }
        int next = 0;
        for (int carrier = 0; carrier < 3; ++carrier) {
            GoalItem* home = itemMgr->getContainer(carrier);
            if (!home) {
                std::printf("[pellet-test] carry carrier=%d no-onion-skipped\n", carrier);
                continue;
            }
            for (int pcolor = 0; pcolor < 3; ++pcolor) {
                if (next >= available) {
                    std::printf("[pellet-test] carry carrier=%d pcolor=%d no-free-piki\n", carrier, pcolor);
                    continue;
                }
                Pellet* pelt = pelletMgr->newNumberPellet(pcolor, 0);
                if (!pelt) continue;
                const f32 ang = f32(next) * 1.0471976f;
                const f32 x = home->mSRT.t.x + 260.0f * cosf(ang);
                const f32 z = home->mSRT.t.z + 260.0f * sinf(ang);
                pelt->init(Vector3f(x, mapMgr->getMinY(x, z, true) + 5.0f, z));
                pelt->startAI(0);
                const f32 scale = pelt->mConfig->mPelletScale();
                pelt->mSRT.s.set(scale, scale, scale);
                pelt->mStateMachine->transit(pelt, 0);
                Piki* piki = crew[next++];
                piki->initColor(carrier);
                piki->mActiveAction->abandon(nullptr);
                piki->mActiveAction->mCurrActionIdx = PikiAction::Transport;
                piki->mActiveAction->mChildActions[PikiAction::Transport].initialise(pelt);
                piki->mMode = PikiMode::TransportMode;
                // The Pikmin starts beside the pellet and runs the ordinary go/wait/lift/move/goal states.
                piki->mSRT.t = Vector3f(x + 18.0f, mapMgr->getMinY(x + 18.0f, z, true) + 2.0f, z);
                std::printf("[pellet-test] carry carrier=%d pcolor=%d model=%s home_onion=%d\n", carrier, pcolor,
                    pelt->mConfig->mModelId.mStringID, carrier);
            }
        }
        std::fflush(stdout);
        return;
    }
    for (int c = 0; c < 3; ++c) {
        GoalItem* goal = itemMgr->getContainer(c);
        if (!goal) {
            std::printf("[pellet-test] onion=%d absent\n", c);
            continue;
        }
        int slot = 0;
        for (int match = 1; match >= 0; --match) {
            const int pcolor = match ? c : (c + 1) % 3;
            for (int size = 0; size < 4; ++size, ++slot) {
                Pellet* pelt = pelletMgr->newNumberPellet(pcolor, size);
                if (!pelt) {
                    std::printf("[pellet-test] onion=%d pcolor=%d size=%d spawn-failed\n", c, pcolor, size);
                    continue;
                }
                const f32 ang = f32(slot) * 0.7853982f;
                const f32 x = goal->mSRT.t.x + 70.0f * cosf(ang);
                const f32 z = goal->mSRT.t.z + 70.0f * sinf(ang);
                pelt->init(Vector3f(x, mapMgr->getMinY(x, z, true) + 5.0f, z));
                pelt->startAI(0);
                const f32 scale = pelt->mConfig->mPelletScale();
                pelt->mSRT.s.set(scale, scale, scale);
                pelt->mStateMachine->transit(pelt, 0);
                pelt->mTargetGoal = goal;
                pelt->startGoal();
                std::printf("[pellet-test] onion=%d spawn pcolor=%d size=%d match_expected=%d model=%s cfg_type=%d cfg_pcolor=%d\n", c, pcolor,
                    size, match, pelt->mConfig->mModelId.mStringID, int(pelt->mConfig->mPelletType()), int(pelt->mConfig->mPelletColor()));
            }
        }
    }
    std::fflush(stdout);
}

void GameCoreSection::updateAI()
{
    pelletBonusTestTick();
    pc_p2_cave_tick();
    pc_p2_giant_breadbug_actor_tick();
    pc_p2_breadbug_actor_tick();
    Navi* shipNavi = naviMgr ? naviMgr->getActiveNavi() : nullptr;
    const bool shipActive = !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll
        && !gameflow.mIsUIOverlayActive && !playerState->mInDayEnd && shipNavi && shipNavi->mHealth > 1.0f;
    pc_p2_ship_tick(shipNavi, shipActive);
    if (pc_randomizer_thelynk()) {
        // These are current followers, excluding Onion stock, sprouts and workers.
        const bool active = pc_randomizer_ready() && mNavi && mNavi->isAlive() && !playerState->mInDayEnd
            && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive;
        AICONST.mMaxPikisOnField(100);
        if (active && pikiMgr && itemMgr) {
            int followers[3] = {};
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* piki = static_cast<Piki*>(*it);
                if (piki && piki->isAlive() && piki->mNavi == mNavi && piki->mMode == PikiMode::FormationMode
                    && piki->mColor >= 0 && piki->mColor < 3) ++followers[piki->mColor];
            }
            for (int color = 0; color < 3; ++color) pc_randomizer_thelynk_squad(color, followers[color], true);
            for (int kind = 0; kind < 18; ++kind) {
                const int amount = pc_randomizer_thelynk_bonus(kind);
                if (!amount) continue;
                const int c = kind / 6, color = c == 0 ? Red : c == 1 ? Yellow : Blue, stage = (kind % 6) / 2;
                // Persistent stock may arrive before an Onion is discovered.
                pikiInfMgr.mPikiCounts[color][stage] += amount;
                if (GoalItem* onion = itemMgr->getContainer(color)) onion->mHeldPikis[stage] += amount;
                GameStat::containerPikis.add(color, amount);
                playerState->mTotalBornPikiNum += amount;
                playerState->mLivingPikiNum += amount;
                pc_randomizer_thelynk_consume(kind);
                GameStat::update();
            }
        }
    }
    if (pc_randomizer_expanded()) {
        AICONST.mMaxPikisOnField(pc_randomizer_field_capacity());
        if (pc_coop_active() && mNavi && mNavi2) {
            // Netplay M4 D-policy (#885): owner co-op policy. Both branches run
            // the shared randomizer steps defined above randomizerApplyBenefits
            // (gapfix C4), so a gate or a fix applied there covers single-captain
            // play, local co-op and every netplay session at once. Only the
            // captain-dependent decisions (anchors, heal target, any-live) are
            // co-op specific.
            randomizerUpdateCoop(mNavi, mNavi2, mMapMgr);
        } else {
            const bool active = randomizerTickOpen() && mNavi && mNavi->mHealth > 0.0f;
            randomizerPrereleaseClock(mNavi && mNavi->mHealth <= 0, active);
            if (active && !playerState->mInDayEnd) {
                randomizerApplyBenefits(mNavi, mMapMgr);
                randomizerApplyDeathLink(nullptr, nullptr, nullptr);
                randomizerObserveWorld();
                randomizerObserveExploration(mNavi);
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
    // Grants are once per campaign unlock; restored boot flags prevent replay.
    static bool bbftColorGranted[3] = {};
    static bool initialColorRegistered = false;
    const int initialColor = pc_randomizer_enabled() ? pc_randomizer_start_color() : Red;
    if (!initialColorRegistered) {
        if (pc_randomizer_resumed()) {
            for (int color=0; color<3; ++color) bbftColorGranted[color] = playerState->hasBootContainer(color);
        } else bbftColorGranted[initialColor] = true;
        initialColorRegistered = true;
    }
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
    if (pc_bbft_skip_tutorial() && !pc_randomizer_resumed() && !gameflow.mMoviePlayer->mIsActive
        && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive && itemMgr) {
        GoalItem* redOnion = itemMgr->getContainer(initialColor);
        // Real play keeps the 20 starting Pikmin in the Onion, as vanilla does:
        // Olimar withdraws them himself. Auto-withdrawing dropped them next to
        // whatever a randomized seed placed by the start area, on the wrong side
        // of its wall. The scripted/headless harnesses (TEST_BACKGROUND) still
        // withdraw so their field=N readiness markers keep their meaning.
        const bool manualStart = pc_randomizer_enabled()
            && (!std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND") || std::getenv("PIKMIN_RANDOMIZER_MANUAL_START"));
        const int initialField = bbftRedsQueued ? bbftInitialField : manualStart ? 0 : pc_randomizer_enabled() && pc_randomizer_field_capacity() < 20 ? pc_randomizer_field_capacity() : 20;
        if (!bbftRedsQueued && redOnion && redOnion->getTotalStorePikis() >= 20) {
            // Use normal Onion withdrawal: initialized actors descend the legs
            // and join Olimar through their native exit state, no fake count.
            bbftInitialField = initialField;
            if (initialField > 0) redOnion->exitPikis(initialField);
            else std::printf("[Pikmin Randomizer] START_ONION_HELD stage=%d color=%d stored=%d\n", flowCont.mCurrentStage->mStageID, initialColor, redOnion->getTotalStorePikis());
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
    // lane-03 (#439): room generator-cache writer. Serializes the live room
    // generators through the real day-end cache path (beginSave/saveGenerator/
    // endSave) and writes the whole cache via saveCard to p2-gencache.bin, then
    // exits. TEST_HOOKS + room-preview + env-gated so no exit path ships in a
    // production build.
    if (pc_pikipelago_room_preview() && std::getenv("PIKMIN_P2_CACHE_SAVE") && generatorList) {
        static bool saved = false;
        if (!saved) {
            saved = true;
            const u32 stage = flowCont.mCurrentStage->mStageID;  // 0 = STAGE_Practice for the room
            generatorCache->beginSave(stage);
            int gens = 0;
            Generator* gen;
            FOREACH_NODE_REUSE(Generator, generatorList->mGenListHead->mChild, gen)
            {
                std::printf("P2_GENCACHE_SCAN generator=%u flags=%u dayLimit=%d currentDay=%d\n",
                            unsigned(gen->_70), unsigned(gen->mCarryOverFlags),
                            int(gen->mDayLimit), int(gameflow.mWorldClock.mCurrentDay));
                if (gen->mCarryOverFlags & GENCARRY_SaveGenerator) {
                    generatorCache->saveGenerator(gen);
                    ++gens;
                }
            }
            generatorCache->endSave();
            // saveCard writes 4 + 4 + GENCACHE_HEAP_SIZE + STAGE_COUNT*(1+9*4)
            // bytes; bound the buffer so a growth cannot silently overflow it.
            static char card[0x8000];
            RamStream stream(card, sizeof(card));
            generatorCache->saveCard(stream);
            if (stream.getPosition() <= 0 || stream.getPosition() >= (int)sizeof(card)) {
                std::fprintf(stderr, "[PC Generator] gen-cache record %d bytes does not fit the %zu-byte buffer\n",
                             stream.getPosition(), sizeof(card));
                std::abort();
            }
            std::ofstream out("p2-gencache.bin", std::ios::binary | std::ios::trunc);
            out.write(card, stream.getPosition());
            out.close();
            std::printf("P2_GENCACHE_SAVE stage=%u generators=%d bytes=%d\n", stage, gens, stream.getPosition());
            std::fflush(stdout);
            std::exit(gens ? 0 : 1);
        }
    }
    const char* scripted = std::getenv("PIKMIN_RANDOMIZER_TEST_SCRIPT");
    const char* background = std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND");
    if (pc_randomizer_ready() && scripted && !std::strcmp(scripted, "spawn-audit")
        && background && !std::strcmp(background, "1") && bbftRedsReady) {
        const char* folders[] = {"practice", "stage1", "stage2", "stage3", "last"};
        const int stage = flowCont.mCurrentStage->mStageID;
        std::ifstream files("audit-files.txt"); std::string file;
        if (!files) std::abort();
        int records = 0;
        struct AuditCache : GeneratorCache { int used() const { return mUsedSize; } int freeBytes() const { return mFreeSize; } } auditCache;
        auditCache.initGame();
        auditCache.beginSave(stage);
        int cachedAdults = 0;
        while (files >> file) {
            char path[256]; std::snprintf(path, sizeof(path), "stages/%s/%s", folders[stage], file.c_str());
            RandomAccessStream* input = gsys->openFile(path);
            if (!input) std::abort();
            const int version = input->readInt();
            for (int i = 0; i < (version == 0x312e3076 ? 4 : 3); ++i) input->readFloat();
            const int count = input->readInt();
            if (count < 0 || count > 1000) std::abort();
            for (int i = 0; i < count; ++i) {
                const int offset = input->getPosition();
                Generator* gen = new Generator(); gen->read(*input);
                pc_randomizer_bind_generator(gen, stage, file.c_str(), offset, gen->_70);
                if (!gen->mGenObject) continue;
                const bool teki = gen->mGenObject->mID == 'teki', boss = gen->mGenObject->mID == 'boss';
                if (!teki && !boss) continue;
                if (pc_randomizer_spawn_slots() && !pc_randomizer_generator_id(gen)) std::abort();
                if (!gen->mGenArea || !gen->mGenType) {
                    std::fprintf(stderr, "SPAWN_AUDIT invalid enemy components file=%s offset=%d\n", file.c_str(), offset); std::abort();
                }
                const int species = teki ? static_cast<GenObjectTeki*>(gen->mGenObject)->mTekiType : static_cast<GenObjectBoss*>(gen->mGenObject)->mBossID;
                const bool group = pc_randomizer_group_slots() && teki && (species == 3 || species == 31 || species == 18 || species == 19)
                    && static_cast<GenObjectTeki*>(gen->mGenObject)->mPersonality->mID.mId == 'none'
                    && static_cast<GenObjectTeki*>(gen->mGenObject)->mPersonality->getI(TekiPersonality::INT_Parameter0) == 0;
                if (group) {
                    gen->mAliveCount = gen->mGenType->getMaxCount() - 1;
                    gen->mLatestSpawnDay = gameflow.mWorldClock.mCurrentDay;
                }
                bool campaignCandidate = false;
                if (std::getenv("PIKMIN_RANDOMIZER_TEST_CAMPAIGN") && teki)
                    for (const auto& row : randomizerCampaignSlots)
                        if (row.uid == pc_randomizer_generator_id(gen)) campaignCandidate = true;
                if (pc_randomizer_spawn_slots() && teki && (std::getenv("PIKMIN_RANDOMIZER_TEST_CAMPAIGN") ? campaignCandidate : (species == 4 || species == 32 || group))) {
                    auditCache.saveGenerator(gen);
                    ++cachedAdults;
                }
                TekiPersonality* personality = teki ? static_cast<GenObjectTeki*>(gen->mGenObject)->mPersonality : nullptr;
                const bool protectedSpawn = !teki || personality->mID.mId != 'none' || personality->getI(TekiPersonality::INT_Parameter0) != 0;
                const int x = int(int(gen->mGenPosition.x) + gen->mGenOffset.x);
                const int y = int(int(gen->mGenPosition.y) + gen->mGenOffset.y);
                const int z = int(int(gen->mGenPosition.z) + gen->mGenOffset.z);
                const Vector3f pos = gen->getPos();
                CollTriInfo* anchor = mMapMgr->getCurrTri(pos.x, pos.z, true);
                const int terrain = anchor ? MapCode::getAttribute(anchor) : -1;
                char data[2048] = {};
                RamStream saved(data, sizeof(data));
                Generator::ramMode = true; gen->write(saved);
                if (pc_randomizer_spawn_slots() && std::getenv("PIKMIN_RANDOMIZER_TEST_BAD_SLOT_CACHE"))
                    data[saved.getPosition() - 8] = 0;
                saved.setPosition(0);
                Generator* restored = new Generator(); restored->read(saved); Generator::ramMode = false;
                const int restoredSpecies = teki ? static_cast<GenObjectTeki*>(restored->mGenObject)->mTekiType : static_cast<GenObjectBoss*>(restored->mGenObject)->mBossID;
                if (restoredSpecies != species || restored->mGenPosition.x != x || restored->mGenPosition.y != y || restored->mGenPosition.z != z
                    || restored->mCarryOverFlags != gen->mCarryOverFlags || restored->getRebirthDay() != gen->getRebirthDay()
                    || pc_randomizer_generator_id(restored) != pc_randomizer_generator_id(gen) || restored->mAliveCount != gen->mAliveCount) {
                    std::fprintf(stderr, "SPAWN_AUDIT cache mismatch file=%s offset=%d\n", file.c_str(), offset); std::abort();
                }
                std::printf("SPAWN_AUDIT stage=%d file=%s offset=%d kind=%s species=%d cache=%d,%d,%d count=%d respawn=%d flags=%u protected=%d terrain=%d\n",
                    stage, file.c_str(), offset, teki ? "teki" : "boss", species, x, y, z, gen->mGenType->getMaxCount(), gen->getRebirthDay(),
                    gen->mCarryOverFlags, int(protectedSpawn), terrain);
                ++records;
                delete restored;
                delete gen;
            }
            if (input->getPending() != 0) std::abort();
            input->close();
        }
        auditCache.endSave();
        GeneratorList* liveList = generatorList;
        generatorList = new GeneratorList();
        if (!auditCache.preload(stage)) std::abort();
        int restoredAdults = 0;
        for (Generator* gen = static_cast<Generator*>(generatorList->mGenListHead->mChild); gen; gen = static_cast<Generator*>(gen->mNext)) {
            GenObjectTeki* object = static_cast<GenObjectTeki*>(gen->mGenObject);
            int actual = pc_randomizer_enemy_for_generator(object->mTekiType, false, gen);
            std::printf("CACHE_SLOT uid=%u actual=%d\n", pc_randomizer_generator_id(gen), actual);
            if (!std::getenv("PIKMIN_RANDOMIZER_TEST_CAMPAIGN") && (object->mTekiType == 3 || object->mTekiType == 31 || object->mTekiType == 18 || object->mTekiType == 19)) {
                int survivors = gen->mAliveCount;
                if (std::getenv("PIKMIN_RANDOMIZER_TEST_GROUP_RESPAWN")) {
                    gen->mLatestSpawnDay -= gen->getRebirthDay();
                    survivors = gen->mGenType->getMaxCount();
                }
                Generator::ramMode = true; gen->init(); Generator::ramMode = false;
                if (gen->mAliveCount != survivors) std::abort();
                std::printf("GROUP_SURVIVORS uid=%u count=%d\n", pc_randomizer_generator_id(gen), survivors);
            }
            ++restoredAdults;
        }
        generatorList = liveList;
        if (restoredAdults != cachedAdults || auditCache.freeBytes() <= 0) std::abort();
        std::printf("TEST_ONLY spawn_cache_pass stage=%d adults=%d bytes=%d\n", stage, cachedAdults, auditCache.used());
        std::printf("TEST_ONLY spawn_audit_pass stage=%d records=%d\n", stage, records); std::fflush(stdout); std::exit(0);
    }
    if (pc_randomizer_ready() && scripted && !std::strcmp(scripted, "benefits")
        && background && !std::strcmp(background, "1") && bbftRedsReady
        && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive) {
        static bool baseline = false;
        static int stock = 0, field = 0;
        GoalItem* onion = itemMgr->getContainer(initialColor);
        if (!baseline) {
            stock = onion->getTotalStorePikis();
            field = int(GameStat::formationPikis) + int(GameStat::freePikis) + int(GameStat::workPikis);
            mNavi->mHealth = C_NAVI_PARM(mNavi, mHealth) / 2.0f;
            baseline = true;
            std::puts("TEST_ONLY benefits_ready"); std::fflush(stdout);
        } else if (pc_randomizer_benefit_multiplier(PC_BENEFIT_WHISTLE) == 1.5f) {
            int flowers = 0;
            Iterator it(pikiMgr);
            CI_LOOP(it) {
                Piki* piki = static_cast<Piki*>(*it);
                if (piki && piki->isAlive()) {
                    ++flowers; // Count bodies; flowering now requires drinking nectar.
                }
            }
            int nectar = 0;
            Iterator drops(itemMgr);
            CI_LOOP(drops) {
                Creature* drop = *drops;
                if (drop && drop->mObjType == OBJTYPE_Water && drop->isAlive()) ++nectar;
            }
            if (nectar < 5 || pc_randomizer_benefit_pending(PC_BENEFIT_FLOWERS)) std::abort();
            if (onion->getTotalStorePikis() != stock + 10 || flowers != field
                || mNavi->mHealth != C_NAVI_PARM(mNavi, mHealth)
                || pc_randomizer_benefit_multiplier(PC_BENEFIT_PLUCK) != 1.5f
                || pc_randomizer_field_capacity() != 10) std::abort();
            for (int color = 0; color < 3; ++color)
                if (color != initialColor && GameStat::allPikis[color] != 0) std::abort();
            // No duplicate effects on a second application, including at full health.
            randomizerApplyBenefits(mNavi, mMapMgr);
            if (onion->getTotalStorePikis() != stock + 10) std::abort();
            std::printf("TEST_ONLY benefits_pass color=%d stock_added=10 field_bodies=%d nectar=5 heal=full whistle=150 pluck=150\n", initialColor, flowers);
            std::fflush(stdout); std::exit(0);
        }
    }
    // Netplay M4 D-policy (#885) co-op fixture; see coopPolicyFixture.
    // bbftRedsReady never latches on this base (the direct boot already has 20
    // reds on the field, so the Onion withdrawal stalls); settle 90 co-op ticks.
    if (pc_randomizer_ready() && scripted && !std::strcmp(scripted, "coop-policy")
        && background && !std::strcmp(background, "1") && sCoopPolicy.tick >= 90
        && !gameflow.mMoviePlayer->mIsActive && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive
        && pc_coop_active() && mNavi && mNavi2) {
        coopPolicyFixture(mNavi, mNavi2, mMapMgr, initialColor);
    }
    if (scripted && !std::strcmp(scripted, "boss-params") && background && !std::strcmp(background, "1")
        && pc_randomizer_ready() && bbftRedsReady && !gameflow.mMoviePlayer->mIsActive) {
        const u32 retail[] = {0xc4, 0x08, 0x09, 0x45, 0x85, 0x1b5c0};
        auto check = [](u32 word) {
            char data[16] = {};
            RamStream stream(data, sizeof(data)); stream.writeInt(word); stream.setPosition(0);
            GenObjectBoss obj; obj.readParameters(stream);
            if (obj.mBossID != (word & 15) || obj.mItemIndex != ((word >> 4) & 3)
                || obj.mItemColour != ((word >> 6) & 3) || obj.mItemCount != ((word >> 8) & 15)
                || obj.mPelletConfigIdx != static_cast<int>(word >> 12) - 1) std::abort();
            stream.setPosition(0); obj.writeParameters(stream); stream.setPosition(0);
            if (static_cast<u32>(stream.readInt()) != word) std::abort();
        };
        for (u32 word : retail) check(word);
        const u32 payloads[] = {0, 1, 0xfffff};
        for (u32 id = 0; id < 10; ++id) for (u32 item = 0; item < 4; ++item)
            for (u32 color = 0; color < 4; ++color) for (u32 count = 0; count < 16; ++count)
                for (u32 payload : payloads) check(id | (item << 4) | (color << 6) | (count << 8) | (payload << 12));
        std::puts("TEST_ONLY boss_params_pass cases=7686"); std::fflush(stdout); std::exit(0);
    }
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
    // bot-v7 (wf10): dump every corpse pellet config's carry data (min/max
    // carriers per PelletConfig p01/p02) so the haul wall can be attributed to
    // content/data (min > max, or max 1-4) vs bot behaviour. TEST_ONLY: gated
    // by PIKMIN_RANDOMIZER_TEST_SCRIPT=corpse-weights, prints once, exits 0.
    if (scripted && !std::strcmp(scripted, "corpse-weights") && background && !std::strcmp(background, "1")
        && pc_randomizer_ready() && pelletMgr) {
        static bool dumped = false;
        if (!dumped && pelletMgr->getNumConfigs() > 0) {
            dumped = true;
            for (int type = 0; type < TEKI_TypeCount; ++type) {
                PelletConfig* config = pelletMgr->getConfig(TekiMgr::getTypeId(type));
                if (!config || config->mPelletType() != PELTYPE_Corpse) continue;
                std::printf("[Pikmin Randomizer] TEST_ONLY corpse_weight teki_type=%d name=%s min=%d max=%d\n",
                            type, TekiMgr::getTypeName(type),
                            config->mCarryMinPikis(), config->mCarryMaxPikis());
            }
            std::fflush(stdout);
            std::exit(0);
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
	// Netplay (#1029): entering photo mode sets mPauseAll / mIsUIOverlayActive,
	// which stop the sim on THIS peer only, so a local F3 (or touch button)
	// desyncs the pair. In deterministic mode the request is drained and
	// ignored; outside it the line is unchanged.
	if (!gameflow.mMoviePlayer->mIsActive && pc_photo_mode_poll_toggle() && !pc_netplay_deterministic()) {
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

	// TEST-ONLY (PIKMIN_P2_SKEWER_CAM, #1020): frame a held Pikmin up close for photo evidence.
	static f32 sSkewerFocus = 0.0f;
	bool skewerCam          = false;
	{
		f32 e[3], l[3];
		PcamCamera* pcam = cameraMgr ? cameraMgr->mCamera : nullptr;
		if (pcam && pc_p2_skewer_cam_pose(e, l, &sSkewerFocus)) {
			Vector3f eye(e[0], e[1], e[2]);
			Vector3f look(l[0], l[1], l[2]);
			pcam->inputViewpoint(eye);
			pcam->inputWatchpoint(look);
			pcam->makeMatrix();
			pcam->makeCamera();
			skewerCam = true;
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
		pc_gfx_set_dof_focus(skewerCam ? sSkewerFocus : (focus > 0.0f ? focus : 0.0f));
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
#if defined(PIKI_PC_PORT)
					pc_p2_bulblax_visual_update(gsys->getFrameTime());
#endif
					tekiMgr->update();
				}
				gsys->mTimer->stop("teki");
				pelletMgr->update();
				pc_p2_flora_tick();
				pc_p2_pom_tick();
				pc_p2_candypop_tick();
				pc_p2_plant_tick();
				pc_p2_tamago_tick();
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

#if defined(PIKI_PC_PORT)
static PcamCameraManager* sCameraMgrP1 = nullptr;

void GameCoreSection::updateCoopCameras()
{
	if (!mCameraMgr2) {
		return;
	}
	// La cámara de P2 se actualiza con el singleton apuntando a ella, porque
	// PcamCamera y sus eventos leen `cameraMgr` por dentro.
	setActiveView(1);
	mCameraMgr2->update();
	setActiveView(0);
	updateDynamicSplit(gsys->getFrameTime());
}

// Cámara unificada: foco en el punto medio de los dos focos, orientación de
// la cámara de J1 y distancia media más un extra proporcional a la
// separación, para que quepan los dos Olimar.
void GameCoreSection::updateDynamicSplit(f32 dt)
{
	Camera* own[2] = { mNavi->mNaviCamera, mGameCamera2 };
	// M2b (issue #879): force upstream merged/dynamic co-op camera off in
	// det mode. Each peer draws its own captain; both captains (and both
	// cameras' sim-relevant state) are still simulated.
	if (pc_netplay_present_two_pass_active() || !pc_settings_get_coop_merge_camera()) {
		// Pantalla partida fija: J1 izquierda/arriba, cámaras propias.
		mSplitBlend = 1.0f;
		mP1Side     = 0;
		mNavi->mControlCamera = nullptr;
		if (mNavi2) mNavi2->mControlCamera = nullptr;
		return;
	}
	if (!own[0] || !own[1] || !mNavi2 || !sCameraMgrP1 && !cameraMgr) {
		return;
	}
	// NCamera::makeCamera solo escribe mPosition; el foco hay que sacarlo
	// del watchpoint de cada PcamCamera.
	PcamCameraManager* mgrs[2] = { sCameraMgrP1 ? sCameraMgrP1 : cameraMgr, mCameraMgr2 };
	for (int i = 0; i < 2; i++) {
		NVector3f& wp = mgrs[i]->mCamera->getWatchpoint();
		own[i]->mFocus.set(wp.x, wp.y, wp.z);
	}
	Vector3f p0 = mNavi->mSRT.t, p1 = mNavi2->mSRT.t;
	const f32 sep = p0.distance(p1);
	Vector3f dir[2];
	f32 dist[2];
	for (int i = 0; i < 2; i++) {
		dir[i]  = own[i]->mPosition - own[i]->mFocus;
		dist[i] = dir[i].length();
		if (dist[i] > 0.001f) dir[i].scale(1.0f / dist[i]);
	}
	const f32 dAvg = 0.5f * (dist[0] + dist[1]);
	// Orientación: la de J1 (promediar las dos se anula cuando miran en
	// sentidos opuestos y la cámara gira sola).
	Vector3f dirU = dir[0];
	mUnifiedCam = *own[0];
	mUnifiedCam.mFocus.set(0.5f * (own[0]->mFocus.x + own[1]->mFocus.x), 0.5f * (own[0]->mFocus.y + own[1]->mFocus.y),
	                       0.5f * (own[0]->mFocus.z + own[1]->mFocus.z));
	mUnifiedCam.mPosition = mUnifiedCam.mFocus + dirU * (dAvg + 0.7f * sep);
	mUnifiedCam.mFov      = 0.5f * (own[0]->mFov + own[1]->mFov);
	mUnifiedCam.calcLookAt(mUnifiedCam.mPosition, mUnifiedCam.mFocus, nullptr);
	mUnifiedCam.update(1.0f, mUnifiedCam.mFov, mUnifiedCam.mNear, mUnifiedCam.mFar);

	// Umbral con histéresis relativo a la distancia de cámara propia.
	const f32 target = sep > 0.6f * dAvg ? 1.0f : (sep < 0.4f * dAvg ? 0.0f : (mSplitBlend > 0.5f ? 1.0f : 0.0f));
	const f32 step   = dt / 0.45f;
	if (mSplitBlend < target) {
		mSplitBlend = mSplitBlend + step > target ? target : mSplitBlend + step;
	} else if (mSplitBlend > target) {
		mSplitBlend = mSplitBlend - step < target ? target : mSplitBlend - step;
	}

	// Lado por posición en pantalla, solo mientras está unificada y con
	// margen para que el HUD no salte cuando los dos se cruzan.
	if (mSplitBlend <= 0.0f) {
		const bool horizontal = pc_settings_get_coop_split() == 1;
		immut Vector3f& axis  = horizontal ? mUnifiedCam.mViewYAxis : mUnifiedCam.mViewXAxis;
		const f32 a0 = (p0 - mUnifiedCam.mPosition).dot(axis);
		const f32 a1 = (p1 - mUnifiedCam.mPosition).dot(axis);
		const f32 d  = horizontal ? a1 - a0 : a0 - a1; // < 0: P1 a la izquierda / arriba.
		if (d < -12.0f) mP1Side = 0;
		else if (d > 12.0f) mP1Side = 1;
	}

	// Cámaras de cada vista: lerp unificada -> propia.
	const f32 b = mSplitBlend;
	for (int i = 0; i < 2; i++) {
		Camera& c = mViewCam[i];
		c         = *own[i];
		c.mPosition.set(mUnifiedCam.mPosition.x + (own[i]->mPosition.x - mUnifiedCam.mPosition.x) * b,
		                mUnifiedCam.mPosition.y + (own[i]->mPosition.y - mUnifiedCam.mPosition.y) * b,
		                mUnifiedCam.mPosition.z + (own[i]->mPosition.z - mUnifiedCam.mPosition.z) * b);
		c.mFocus.set(mUnifiedCam.mFocus.x + (own[i]->mFocus.x - mUnifiedCam.mFocus.x) * b,
		             mUnifiedCam.mFocus.y + (own[i]->mFocus.y - mUnifiedCam.mFocus.y) * b,
		             mUnifiedCam.mFocus.z + (own[i]->mFocus.z - mUnifiedCam.mFocus.z) * b);
		c.mFov = mUnifiedCam.mFov + (own[i]->mFov - mUnifiedCam.mFov) * b;
		c.calcLookAt(c.mPosition, c.mFocus, nullptr);
		// update() rehace mPlanePointers, que tras la copia apuntan a los
		// planos de la cámara origen.
		c.update(1.0f, c.mFov, c.mNear, c.mFar);
	}
	// Los controles siguen a la vista mostrada (con la cámara unificada, la
	// orientación de J1), no a la cámara propia de cada uno.
	mNavi->mControlCamera  = &mViewCam[0];
	mNavi2->mControlCamera = &mViewCam[1];
}

// HUD en la misma mitad que la vista 3D del jugador (lado y orientación).
void GameCoreSection::setViewSubrect(int view)
{
	const int side = viewSide(view);
	if (pc_settings_get_coop_split() == 1) {
		pc_gfx_set_view_subrect(0.0f, side == 0 ? 0.5f : 0.0f, 1.0f, side == 0 ? 1.0f : 0.5f);
	} else {
		pc_gfx_set_view_subrect(side == 0 ? 0.0f : 0.5f, 0.0f, side == 0 ? 0.5f : 1.0f, 1.0f);
	}
}

void GameCoreSection::setActiveView(int view)
{
	if (!mCameraMgr2) {
		return;
	}
	if (view == 1) {
		if (!sCameraMgrP1) {
			sCameraMgrP1 = cameraMgr;
		}
		cameraMgr = mCameraMgr2;
	} else if (sCameraMgrP1) {
		cameraMgr    = sCameraMgrP1;
		sCameraMgrP1 = nullptr;
	}
}

Camera* GameCoreSection::getViewCamera(int view)
{
	// M5c lane A (issue #887): in det two-pass mode updateDynamicSplit never
	// builds the merged views (each peer shows its own captain), so a peer
	// with coopMergeCamera on used to present the never-updated mViewCam.
	// The authoritative pass does ask for view cameras (postRender's split
	// 2D loop: beginView, endViews), so the change is gated on the
	// presentation pass and the authoritative pass keeps exactly what it
	// did before M5c (fix round 1, review m1).
	if (!pc_settings_get_coop_merge_camera()
	    || (pc_netplay_present_two_pass_active() && !pc_render_is_authoritative())) {
		return view == 1 ? mGameCamera2 : mNavi->mNaviCamera;
	}
	return &mViewCam[view == 1 ? 1 : 0];
}

void GameCoreSection::drawGameInfoHud(Graphics& gfx)
{
#if defined(PIKI_PC_PORT)
	// M2b fix (review M6): in det co-op each peer shows only its local
	// captain's HUD fullscreen, not the split layout.
	// M2b fix2 (review M6 observation): the authoritative pass does no HUD
	// draw work at all, so it stays view-independent (null_attempted matches
	// between LOCAL_PLAYER 0 and 1). HUD widgets animate view state per draw
	// (life-circle tri counts chase health with frame-time steps): drawing in
	// both passes advances the local HUD twice per tick and the other once,
	// so auth submission differs per followed captain. Presentation draws the
	// local single view below.
	if (pc_netplay_present_two_pass_active() && pc_render_is_authoritative()) {
		return;
	}
	if (pc_netplay_present_two_pass_active() && !pc_render_is_authoritative() && isSplitScreen()
	    && !gameflow.mMoviePlayer->mIsActive) {
		const int local = pc_netplay_present_local_player();
		zen::DrawGameInfo* hud = (local == 1 && mDrawGameInfo2) ? mDrawGameInfo2 : mDrawGameInfo;
		hud->draw(gfx);
		return;
	}
#endif
	if (!isSplitScreen() || !mDrawGameInfo2 || gameflow.mMoviePlayer->mIsActive) {
		mDrawGameInfo->draw(gfx);
		return;
	}
	// Parte de cada jugador dentro de su mitad: el espacio GX 640x480 se
	// mapea al sub-rectángulo (pc_gfx_set_view_subrect) y el ancho virtual
	// del HUD sale del aspecto de la mitad.
	const f32 windowAspect = pc_gfx_get_window_aspect_ratio();
	const f32 viewAspect   = pc_settings_get_coop_split() == 1 ? windowAspect * 2.0f : windowAspect * 0.5f;
	zen::DrawGameInfo* huds[2] = { mDrawGameInfo, mDrawGameInfo2 };
	for (int view = 0; view < 2; view++) {
		// Sub-rectángulo normalizado con origen abajo-izquierda (GL).
		setViewSubrect(view);
		pc_gfx_set_view_aspect_override(viewAspect);
		// El HUD de J2 con el tinte de distinción de su capitán (suavizado
		// hacia blanco para no apagar la fuente); sin tinte si van distintos.
		const bool hudTinted = view == 1 && pc_coop_p2_tinted();
		if (hudTinted) {
			unsigned char r, g, b;
			pc_coop_p2_tint(&r, &g, &b);
			pc_gfx_set_out_tint(1.0f - (1.0f - r / 255.0f) * 0.4f, 1.0f - (1.0f - g / 255.0f) * 0.4f,
			                    1.0f - (1.0f - b / 255.0f) * 0.4f);
		}
		huds[view]->drawPlayer(gfx);
		drawDownedLabel(gfx, view == 0 ? mNavi : mNavi2, viewAspect);
		if (hudTinted) pc_gfx_clear_out_tint();
	}
	pc_gfx_set_view_aspect_override(0.0f);
	pc_gfx_clear_view_subrect();
	gfx.setViewport(AREA_FULL_SCREEN(gfx));
	gfx.setScissor(AREA_FULL_SCREEN(gfx));
	mDrawGameInfo->drawShared(gfx);
}

// Menú de cebolla/nave: en pantalla partida cada jugador ve el suyo dentro
// de su mitad, con el mismo espacio virtual que su HUD.
void GameCoreSection::drawContainerWindows(Graphics& gfx)
{
#if defined(PIKI_PC_PORT)
	// M2b fix (review M6): det co-op shows only the local player's menu
	// window fullscreen (mirrors drawGameInfoHud above).
	// M2b fix2 (review M6 observation): no container draw work in the
	// authoritative pass (see above).
	if (pc_netplay_present_two_pass_active() && pc_render_is_authoritative()) {
		return;
	}
	if (pc_netplay_present_two_pass_active() && !pc_render_is_authoritative() && isSplitScreen()
	    && !gameflow.mMoviePlayer->mIsActive) {
		const int local = pc_netplay_present_local_player();
		zen::DrawContainer* win = (local == 1 && containerWindow2) ? containerWindow2 : containerWindow;
		win->draw(gfx);
		return;
	}
#endif
	if (!isSplitScreen() || !containerWindow2 || gameflow.mMoviePlayer->mIsActive) {
		containerWindow->draw(gfx);
		return;
	}
	const f32 windowAspect = pc_gfx_get_window_aspect_ratio();
	const f32 viewAspect   = pc_settings_get_coop_split() == 1 ? windowAspect * 2.0f : windowAspect * 0.5f;
	int virtW = int(lroundf(480.0f * viewAspect));
	int virtH = 480;
	if (virtW < 640) {
		virtW = 640;
		virtH = int(lroundf(640.0f / viewAspect));
	}
	zen::DrawContainer* wins[2] = { containerWindow, containerWindow2 };
	for (int view = 0; view < 2; view++) {
		setViewSubrect(view);
		pc_gfx_set_view_aspect_override(viewAspect);
		pc_gfx_set_hud_virtual_size(virtW, virtH);
		wins[view]->draw(gfx);
	}
	pc_gfx_set_hud_virtual_size(0, 0);
	pc_gfx_set_view_aspect_override(0.0f);
	pc_gfx_clear_view_subrect();
	gfx.setViewport(AREA_FULL_SCREEN(gfx));
	gfx.setScissor(AREA_FULL_SCREEN(gfx));
}

// Rótulo en la vista de un Olimar caído (fase 5). Mismo espacio virtual que
// el HUD de esa mitad, para que no salga estirado.
void GameCoreSection::drawDownedLabel(Graphics& gfx, Navi* navi, f32 viewAspect)
{
	if (!navi || !gsys->mConsFont || navi->getCurrState()->getID() != NAVISTATE_Dead) {
		return;
	}
	int virtW = int(lroundf(480.0f * viewAspect));
	int virtH = 480;
	if (virtW < 640) {
		virtW = 640;
		virtH = int(lroundf(640.0f / viewAspect));
	}
	pc_gfx_set_hud_virtual_size(virtW, virtH);
	pc_gfx_set_hud_wide(1);
	Matrix4f ortho;
	gfx.setOrthogonal(ortho.mMtx, RectArea(0, 0, virtW, virtH));
	gfx.setViewport(RectArea(0, 0, virtW, virtH));
	gfx.setScissor(RectArea(0, 0, virtW, virtH));
	gfx.setFog(false);
	gfx.useTexture(nullptr, GX_TEXMAP0);
	const char* text = "OLIMAR DOWN";
	const int textW  = gsys->mConsFont->stringWidth(text);
	const int x      = (virtW - textW) / 2;
	const int y      = virtH / 2 - gsys->mConsFont->mCharHeight / 2;
	gfx.setColour(Colour(0, 0, 0, 200), true);
	gfx.setAuxColour(Colour(0, 0, 0, 200));
	gfx.texturePrintf(gsys->mConsFont, x + 2, y + 2, "%s", text);
	gfx.setColour(Colour(255, 90, 90, 255), true);
	gfx.setAuxColour(Colour(255, 90, 90, 255));
	gfx.texturePrintf(gsys->mConsFont, x, y, "%s", text);
	pc_gfx_set_hud_wide(0);
	pc_gfx_set_hud_virtual_size(0, 0);
}

RectArea GameCoreSection::splitViewRect(Graphics& gfx, int view)
{
	const int w = gfx.mScreenWidth, h = gfx.mScreenHeight;
	const int side = viewSide(view);
	if (pc_settings_get_coop_split() == 1) {
		return side == 0 ? RectArea(0, 0, w, h / 2) : RectArea(0, h / 2, w, h);
	}
	return side == 0 ? RectArea(0, 0, w / 2, h) : RectArea(w / 2, 0, w, h);
}

RectArea GameCoreSection::currentViewRect(Graphics& gfx)
{
	return mViewRectActive ? splitViewRect(gfx, mActiveViewIndex) : AREA_FULL_SCREEN(gfx);
}

void GameCoreSection::beginView(Graphics& gfx, int view, f32 farClip)
{
	Camera* cam = getViewCamera(view);
	setActiveView(view);
	mActiveViewIndex = view;
	mViewRectActive  = true;
	// Frustum de pantalla completa corrido en NDC hacia el lado de la vista
	// y recortado a su mitad: con blend 0 las dos mitades componen una sola
	// imagen; con blend 1 cada Olimar queda centrado en la suya.
	const bool horizontal = pc_settings_get_coop_split() == 1;
	const f32 shift       = 0.5f * mSplitBlend * (viewSide(view) == 0 ? 1.0f : -1.0f);
	pc_gfx_set_proj_offset(horizontal ? 0.0f : -shift, horizontal ? shift : 0.0f);
	gfx.setCamera(cam);
	cam->update(pc_gfx_get_window_aspect_ratio(), cam->mFov, pc_first_person_active() ? 3.0f : 100.0f, farClip);
	gfx.setViewport(AREA_FULL_SCREEN(gfx));
	gfx.setScissor(currentViewRect(gfx));
	// initRender() vacía luces y shapes cacheadas una vez por frame; cada
	// pasada vuelve a añadir las mismas Light (DayMgr::refresh) y encola sus
	// translúcidos. Sin esto la lista de luces se vuelve circular y la
	// segunda vista repinta los cascos de la primera con matrices ajenas.
	if (view > 0) {
		gfx.mActiveLightMask = 0;
		gfx.mLight.initCore("");
		gfx.resetCacheBuffer();
		gfx.resetMatrixBuffer();
	}
}

void GameCoreSection::endViews(Graphics& gfx, Camera* mainCamera)
{
	pc_gfx_set_proj_offset(0.0f, 0.0f);
	mViewRectActive  = false;
	mActiveViewIndex = 0;
	setActiveView(0);
	gfx.setCamera(mainCamera);
	gfx.setViewport(AREA_FULL_SCREEN(gfx));
	gfx.setScissor(AREA_FULL_SCREEN(gfx));
}
#endif

/**
 * @todo: Documentation
 */
void GameCoreSection::draw(Graphics& gfx)
{
#if defined(PIKI_PC_PORT)
	// Day-end teardown (slice lane, issue #880): the results screen exits to
	// the quitter, whose postUpdate runs exitStage() and softReset(). A stale
	// draw of this section can still run afterwards with the stage managers
	// released (exitStage() nulls naviMgr; the other managers are heap
	// objects). Drawing that state dereferences released memory
	// (e.g. naviMgr->refresh below). There is nothing meaningful to draw, so
	// return early. Only reachable post-teardown, otherwise behaviour is
	// unchanged. Same class as the #47/#48 setMovieNavi guard above.
	if (naviMgr == nullptr) {
		return;
	}
#endif
	gfx.mCamera->mProjectionMatrix = gfx.mCamera->mPerspectiveMatrix;
	gfx.mCamera->mProjectionMatrix.multiply(gfx.mCamera->mLookAtMtx);
	bool advanceState = true;
#if defined(PIKI_PC_PORT)
	advanceState = pc_render_is_authoritative();
#endif
#if defined(PIKI_PC_PORT)
	// Segunda vista de la frame: solo dibujar, no avanzar sonido.
	if (mRenderPass != 0) advanceState = false;
#endif
	gsys->mTimer->start("se updt", true);
#if defined(PIKI_PC_PORT)
	// M2b (issue #879): audio runs in the presentation pass with the
	// listener at the local captain. Authoritative (sim) never touches it.
	if (pc_netplay_present_two_pass_active()) {
		if (!pc_render_is_authoritative()) {
			if (gameflow.mMoviePlayer->mIsActive) {
				Vector3f pos;
				gameflow.mMoviePlayer->getLookAtPos(pos);
				seSystem->update(gfx, pos);
			} else if (mNavi2 && mNavi2->isAlive()) {
				const int local = pc_netplay_present_local_player();
				Navi* listener = (local == 1) ? mNavi2 : mNavi;
				if (!listener) {
					listener = mNavi;
				}
				seSystem->update(gfx, listener->mSRT.t);
			} else {
				seSystem->update(gfx, mNavi->mSRT.t);
			}
		}
	} else if (advanceState && gameflow.mMoviePlayer->mIsActive) {
#else
	if (advanceState && gameflow.mMoviePlayer->mIsActive) {
#endif
		Vector3f pos;
		gameflow.mMoviePlayer->getLookAtPos(pos);
		seSystem->update(gfx, pos);
	} else if (advanceState) {
#if defined(PIKI_PC_PORT)
		// Pantalla partida: el escuchador va al punto medio entre los dos.
		if (mNavi2 && mNavi2->isAlive()) {
			seSystem->update(gfx, (mNavi->mSRT.t + mNavi2->mSRT.t) * 0.5f);
		} else
#endif
		seSystem->update(gfx, mNavi->mSRT.t);
	}
	gsys->mTimer->stop("se updt");

	gfx.useMatrix(Matrix4f::ident, 0);
	gfx.calcLighting(1.0f);
	pc_p2_hardlanes_draw(gfx);
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
#if defined(PIKI_PC_PORT)
	// Con sombras proyectadas (shadow map) las manchas originales sobran.
	if (pc_settings_get_shadows() == 0)
#endif
	{
		if (AIPerf::optLevel <= 1) {
			pikiMgr->drawShadow(gfx, mShadowTexture);
		}
		itemMgr->drawShadow(gfx, mShadowTexture);
		pelletMgr->drawShadow(gfx, mShadowTexture);
		if (tekiMgr && !hideTeki()) {
			tekiMgr->drawShadow(gfx, mShadowTexture);
		}
		naviMgr->drawShadow(gfx);
	}

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
	pc_p2_cave_draw_transition(gfx);
	pc_p2_breadbug_visual_draw(gfx);
	pc_p2_breadbug_teki_draw_nests(gfx);
	pc_p2_giant_breadbug_visual_draw(gfx);
	pc_p2_bulblax_visual_draw(gfx);
	pc_p2_queen_draw(gfx);
	pc_p2_king_draw(gfx);
	pc_p2_tank_draw_water(gfx);
	pc_p2_kabuto_fsm_draw_stones(gfx);
	pc_p2_bombsarai_teki_draw_bombs(gfx);
	pc_p2_dangomushi_draw_rain(gfx);
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
			pc_p2_bombsarai_teki_draw_bomb_gauges(gfx); // #1027 Dirigibug bomb life gauges
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
#if defined(PIKI_PC_PORT)
			drawGameInfoHud(gfx);
#else
			mDrawGameInfo->draw(gfx);
#endif
		}
		gfx.setOrthogonal(orthoMtx.mMtx, AREA_FULL_SCREEN(gfx));
#if defined(PIKI_PC_PORT)
		drawContainerWindows(gfx);
#else
		containerWindow->draw(gfx);
#endif
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
