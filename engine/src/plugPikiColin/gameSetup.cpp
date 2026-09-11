#include "GameSetupSection.h"
#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "pc_permadeath.h"
#include "jaudio/piki_scene.h"
#include "jaudio/verysimple.h"
#include <cstdio>
#include <cstdlib>

#include "BaseInf.h"
#include "DebugLog.h"
#include "Dolphin/os.h"
#include "FlowController.h"
#include "Generator.h"
#include "GlobalShape.h"
#include "KIO.h"
#include "Kontroller.h"
#include "MemStat.h"
#include "PlayerState.h"
#include "Shape.h"
#include "gameflow.h"
#include "sysNew.h"
#include "system.h"

/// Size of controller input recording buffer.
#define CONTROLLER_INPUT_BUFFER_SIZE (12 * 3000)

/**
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @note UNUSED Size: 0000F4
 */
DEFINE_PRINT("GameSetup");

/**
 * @brief Models and animations for number pellets, Pikmin, and Olimar that are always loaded.
 *
 * All Pikmin and Olimar share the same animation bundle (bluModel.anm).
 */
static immut char* shapeList[][2] = {
	{ "objects/pellets/white1.mod", "objects/pellets/white1.anm" }, ///< 1 pellet
	{ "objects/pellets/white2.mod", "objects/pellets/white2.anm" }, ///< 5 pellet
	{ "objects/pellets/white3.mod", "objects/pellets/white3.anm" }, ///< 10 pellet
	{ "objects/pellets/white4.mod", "objects/pellets/white4.anm" }, ///< 20 pellet
	{ "pikis/bluModel.mod", "pikis/bluModel.anm" },                 ///< Blue Pikmin
	{ "pikis/redModel.mod", nullptr },                              ///< Red Pikmin
	{ "pikis/yelModel.mod", nullptr },                              ///< Yellow Pikmin
	{ "pikis/kinModel.mod", nullptr },                              ///< Puffmin
	{ "pikis/nv3Model.mod", nullptr },                              ///< Olimar
	{ nullptr, nullptr },
};

/**
 * @brief Ship parts that attach to the S.S. Dolphin and thus should always be loaded.
 *
 * Soto - そと (Exterior) - Major cosmetic changes to S.S. Dolphin
 * Fuzoku - ふぞく (Attached) - Minor cosmetic changes to the S.S. Dolphin
 * Naka - なか  (Inside) - No cosmetic changes to the S.S. Dolphin (so don't get loaded here)
 */
static immut char* shapeList2[][2] = {
	{ "objects/ufo/ufo0705.mod", "objects/ufo/ufo0705.anm" },             ///< base Dolphin model and animation set.
	{ "objects/ufoparts/soto1.mod", "objects/ufoparts/soto1.anm" },       ///< Bowsprit
	{ "objects/ufoparts/soto2.mod", "objects/ufoparts/soto2.anm" },       ///< Gluon Drive
	{ "objects/ufoparts/soto3.mod", "objects/ufoparts/soto3.anm" },       ///< Anti-Dioxin Filter
	{ "objects/ufoparts/soto4.mod", "objects/ufoparts/soto4.anm" },       ///< Eternal Fuel Dynamo
	{ "objects/ufoparts/soto5.mod", "objects/ufoparts/soto5.anm" },       ///< Main Engine
	{ "objects/ufoparts/fuzoku1.mod", "objects/ufoparts/fuzoku1.anm" },   ///< Whimsical Radar
	{ "objects/ufoparts/fuzoku2.mod", "objects/ufoparts/fuzoku2.anm" },   ///< Interstellar Radio
	{ "objects/ufoparts/fuzoku3.mod", "objects/ufoparts/fuzoku3.anm" },   ///< Guard Satellite
	{ "objects/ufoparts/fuzoku4.mod", "objects/ufoparts/fuzoku4.anm" },   ///< Chronos Reactor
	{ "objects/ufoparts/fuzoku5.mod", "objects/ufoparts/fuzoku5.anm" },   ///< Radiation Canopy
	{ "objects/ufoparts/fuzoku6.mod", "objects/ufoparts/fuzoku6.anm" },   ///< Geiger Counter
	{ "objects/ufoparts/fuzoku7.mod", "objects/ufoparts/fuzoku7.anm" },   ///< Sagittarius
	{ "objects/ufoparts/fuzoku8.mod", "objects/ufoparts/fuzoku8.anm" },   ///< Libra
	{ "objects/ufoparts/fuzoku9.mod", "objects/ufoparts/fuzoku9.anm" },   ///< Omega Stabilizer
	{ "objects/ufoparts/fuzoku10.mod", "objects/ufoparts/fuzoku10.anm" }, ///< Ionium Jet #1
	{ "objects/ufoparts/fuzoku11.mod", "objects/ufoparts/fuzoku11.anm" }, ///< Ionium Jet #2
	{ nullptr, nullptr },
};

/// Archive-Directory pairs for various object types, to load into the system file list.
static immut char* arambundleList[][2] = {
	{ "archives/tekis.dir", "dataDir/archives/tekis.arc" },
	{ "archives/bosses.dir", "dataDir/archives/bosses.arc" },
	{ "archives/tekipara.dir", "dataDir/archives/tekipara.arc" },
	{ "archives/tekikey.dir", "dataDir/archives/tekikey.arc" },
#if defined(VERSION_GPIP01)
#else
	{ "archives/plants.dir", "dataDir/archives/plants.arc" },
#endif
	{ "archives/ufopartsbin.dir", "dataDir/archives/ufopartsbin.arc" },
	{ "archives/bridges.dir", "dataDir/archives/bridges.arc" },
	{ "archives/gates.dir", "dataDir/archives/gates.arc" },
	{ "archives/bomb.dir", "dataDir/archives/bomb.arc" },
	{ "archives/rope.dir", "dataDir/archives/rope.arc" },
	{ "archives/water.dir", "dataDir/archives/water.arc" },
	{ "archives/fl_water.dir", "dataDir/archives/fl_water.arc" },
	{ "archives/pelletsbin.dir", "dataDir/archives/pelletsbin.arc" },
	{ "archives/pikihead.dir", "dataDir/archives/pikihead.arc" },
	{ "archives/effshapes.dir", "dataDir/archives/effshapes.arc" },
	{ "archives/weeds.dir", "dataDir/archives/weeds.arc" },
#if defined(VERSION_G98E01_PIKIDEMO)
#else
	{ "archives/goal.dir", "dataDir/archives/goal.arc" },
#endif
	{ nullptr, nullptr },
};

/**
 * @brief Loads arc/dir file pairs and model/animation pairs to populate the system file lists.
 */
void GameSetupSection::preCacheShapes()
{
	// grab the remaining space in the aram allocator to cache models and animations
	gsys->mShapeAramAllocator.init(gsys->mBaseAramAllocator.mNextFreeAddress, gsys->mBaseAramAllocator.getFreeSize());
	gsys->setActiveAramAllocator(&gsys->mShapeAramAllocator);

	gsys->mAramRoot.initCore("");
	gsys->mFileList = &gsys->mAramRoot;

	// load in all the arc/dir file pairs to cache in the file list.
	immut char** bundlePair;
	for (bundlePair = arambundleList[0]; bundlePair[0]; bundlePair += 2) {
		gsys->parseArchiveDirectory(bundlePair[0], bundlePair[1]);
	}

	// Colin: "lemme yell at you real quick"
	BOOL print         = gsys->mTogglePrint;
	gsys->mTogglePrint = TRUE;
#if defined(VERSION_PIKIDEMO)
	_Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
	_Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
	_Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
	AramAllocator* alloc = &gsys->mShapeAramAllocator;
	_Print("!!!!!!!!!!!!!!!!! %d bytes still in aramHeap\n", alloc->getFreeSize());
	_Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
	_Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
	_Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
	_Print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n");
#endif
	gsys->mTogglePrint = print; // "back to regularly scheduled programming"

	// load in pikmin models/anims (and some seemingly unused pellet ones)
	for (bundlePair = shapeList[0]; bundlePair[0]; bundlePair += 2) {
		Shape* shape = gameflow.loadShape(bundlePair[0], true);
		if (bundlePair[1]) {
			gsys->mCurrentShape = shape;
			gsys->loadBundle(bundlePair[1], false); // don't load as cache texture
		}
	}

	// load in model/anim pairs for ship (and ship parts that modify they ship)
	for (bundlePair = shapeList2[0]; bundlePair[0]; bundlePair += 2) {
		Shape* shape = gameflow.loadShape(bundlePair[0], true);
		if (bundlePair[1]) {
			gsys->mCurrentShape = shape;
			gsys->loadBundle(bundlePair[1], false); // don't load as cache texture
		}
	}
}

/**
 * @brief Constructs the single-player setup section to initialise before gameplay.
 */
GameSetupSection::GameSetupSection()
{
	Node::init("<GameSetupSection>");

	// set heap to grow down
	AyuHeap* heap = gsys->getHeap(SYSHEAP_App);
	int allocType = heap->setAllocType(AYU_STACK_GROW_DOWN);

	// set up memory monitor before anything else
	memStat = new MemStat();

	memStat->start("setup");

	// initialise basic game flow parameters
	gameflow.mPlayState.Initialise();
	gameflow.mWorldClock.mCurrentDay = 1;
	flowCont.mClearStatePikiCount    = 0; // basically unused
	flowCont._254                    = 0; // unused
	flowCont._258                    = 0; // unused
	flowCont.mNaviSeedCount          = 0; // basically unused
	flowCont._250                    = 0; // unused

	// load all stages
	flowCont.readMapList("stages/stages.ini");
	flowCont.mEndingType = ENDING_None;

	// cache info on some important arc/dir and model/anim pairs
	preCacheShapes();

	// set up the generator cache, to store generator info between days
	memStat->start("genCache");
	generatorCache = new GeneratorCache();
	generatorCache->initGame();
	memStat->end("genCache");

	// set up player info, to track player-induced changes
	memStat->start("playerInfo");
	playerState = new PlayerState();
	playerState->initGame();
	memStat->end("playerInfo");

	// set up input recording (!!)
	kio = new KIO();
	kio->initialise();
	int saveSize     = Kontroller::getSaveSize(CONTROLLER_INPUT_BUFFER_SIZE / 12);
	void* saveBuffer = new (PIKI_ALIGNED(0x20)) u8[saveSize];
	controllerBuffer = new RamStream(saveBuffer, saveSize);

	// load pikmin head and whistle models
	GlobalShape::init();

	memStat->end("setup");
	heap->setAllocType(allocType);

	// remove any buffered pikmin information
	pikiInfMgr.clear();

	// initialise the play state (to then load/save from/to memory card)
	gameflow.mPlayState.Initialise();
}

/**
 * @brief Performs any frame-by-frame required setup of single-player game state, then transits to card select.
 *
 * Demo version uses this to force setup of Forest of Hope challenge mode stage, other versions just transit straight to card select.
 */
void GameSetupSection::update()
{
	PRINT("reset!\n");

    if (pc_bbft_enabled()) {
        // The title scene loads shared JAudio banks and its completion callback
        // sets first_load. Intro/Course wait forever without this native setup.
        // Keep the audio initialization while bypassing the title UI.
        pc_bbft_milestone("BOOT_AUDIO_TITLE_BEGIN");
        Jac_BackDVDBuffer();
        Jac_SceneSetup(SCENE_Title, 0);
        Jac_SceneExit(SCENE_Exit, 0);
        pc_bbft_milestone("BOOT_AUDIO_TITLE_READY");
        // Same fresh-story setup as CardSelectSection, without its menus.
        // Legacy mode keeps that story state; the optional day-two starter
        // state is applied below after the normal resets.
        gameflow.mIsChallengeMode = FALSE;
        flowCont.mCurrentStage = nullptr;
        playerState->initGame();
        generatorCache->initGame();
        pikiInfMgr.initGame();
        FOREACH_NODE(StageInfo, flowCont.mStageList.mChild, stage) {
            stage->mHasInitialised = FALSE;
            stage->mStageInf.initGame();
        }
        gameflow.mGamePrefs.mMemCardSaveIndex = 0;
        gameflow.mGamePrefs.mMostRecentFileSlot = 0;
        gameflow.mGamePrefs.mHasSaveGame = false;
        gameflow.mPlayState.Initialise();
        pc_permadeath_set_pending(false);
        pc_permadeath_begin_new_run();
        StageInfo* stage = static_cast<StageInfo*>(flowCont.mStageList.mChild);
        if (pc_bbft_skip_tutorial()) {
            const int selected = pc_randomizer_enabled() ? pc_randomizer_start_stage() : STAGE_Forest;
            while (stage && stage->mStageID != selected) stage = static_cast<StageInfo*>(stage->mNext);
        }
        if (!stage) { std::fprintf(stderr, "BBFT: requested starting stage missing\n"); std::abort(); }
        flowCont.mCurrentStage = stage;
        std::sprintf(flowCont.mCurrStageFilePath, "%s", stage->mFileName);
        std::sprintf(flowCont.mDoorStageFilePath, "%s", stage->mFileName);
        gameflow.mWorldClock.mCurrentDay = 1;
        gameflow.mWorldClock.setTime(TUTORIAL_TIME_OF_DAY);
        if (pc_bbft_skip_tutorial()) {
            playerState->mIsTutorialMode = false;
            const int initialColor = pc_randomizer_enabled() ? pc_randomizer_start_color() : Red;
            playerState->setContainer(initialColor);
            playerState->setBootContainer(initialColor);
            playerState->setDisplayPikiCount(initialColor);
            const int completedTutorials[] = {
                DEMOFLAG_DiscoverRedOnyon, DEMOFLAG_ApproachSeed, DEMOFLAG_PluckRedPikmin,
                DEMOFLAG_NoPikminTimeout, DEMOFLAG_CameraInfo, DEMOFLAG_CollectFirstPellet,
                DEMOFLAG_ApproachEngine, DEMOFLAG_CollectEngine, DEMOFLAG_StartBoxPush,
                DEMOFLAG_FinishBoxPush, DEMOFLAG_OnyonMenuInfo, DEMOFLAG_Pluck15thPikmin
            };
            for (int flag : completedTutorials) playerState->mDemoFlags.setFlagOnly(flag);
            // Equivalent persisted campaign state to finishing day one. The
            // actual part's visibility is restored when its model registers.
            playerState->mCurrParts = 1;
            playerState->mRequiredUfoPartCount = 1;
            playerState->mShipUpgradeLevel = 1;
            playerState->mStagePartsCollected[STAGE_Practice] = 1;
            playerState->setDayCollectCount(0, 1);
            gameflow.mPlayState.openStage(stage->mStageID);
            pikiInfMgr.mPikiCounts[initialColor][Leaf] = 20;
            playerState->mTotalBornPikiNum = 20;
            playerState->mLivingPikiNum = 20;
            playerState->mTotalPluckedPikiCount = 20;
            gameflow.mWorldClock.mCurrentDay = 2;
            gameflow.mWorldClock.setTime(gameflow.mParameters->mStartHour());
        }
        gameflow.mCurrentStageID = -1;
        if (pc_randomizer_enabled()) std::printf("[Pikmin Randomizer] START_STAGE %d day=2 color=%d stored=20\n", stage->mStageID, pc_randomizer_start_color());
        gameflow.mPendingStageUnlockID = -1;
        // The intro's existing BBFT skip executes normal teardown before
        // entering gameplay, preserving the engine's setup sequence.
        gameflow.mNextOnePlayerSectionID = pc_bbft_skip_tutorial() ? ONEPLAYER_NewPikiGame : ONEPLAYER_IntroGame;
        std::printf("[BBFT] Direct boot: %s; save root %s\n", pc_bbft_skip_tutorial() ? "Forest of Hope day 2, 20 reds" : "Impact Site, fresh story", pc_bbft_save_root());
        gsys->softReset();
        return;
    }

#if defined(VERSION_PIKIDEMO)
	// the only thing the demo will load into is the Forest of Hope challenge mode

	STACK_PAD_VAR(1);
	flowCont.mCurrentStage = nullptr;
	playerState->initGame();
	generatorCache->initGame();
	pikiInfMgr.initGame();

	// reset all our story mode stages to be re-initialised
	StageInfo* stage;
	for (stage = static_cast<StageInfo*>(flowCont.mStageList.mChild); stage; stage = static_cast<StageInfo*>(stage->mNext)) {
		stage->mHasInitialised = FALSE;
		stage->mStageInf.initGame();
	}

	gameflow.mGamePrefs.mMemCardSaveIndex = 0;
	gameflow.mGamePrefs.mHasSaveGame      = false;

	// put us in challenge mode
	playerState->setChallengeMode();

	for (stage = static_cast<StageInfo*>(flowCont.mStageList.mChild); stage; stage = static_cast<StageInfo*>(stage->mNext)) {
		if ((int)stage->mChalStageID == CHALSTAGE_Forest) {
			// if we have it, load into Forest of Hope challenge mode!
			flowCont.mCurrentStage = stage;
			sprintf(flowCont.mCurrStageFilePath, "%s", stage->mFileName);
			sprintf(flowCont.mDoorStageFilePath, "%s", stage->mFileName);
			gameflow.mNextOnePlayerSectionID = ONEPLAYER_NewPikiGame;
			gameflow.mWorldClock.setTime(gameflow.mParameters->mStartHour());
			break;
		}
	}
#else
	// queue up card select as the next section (either for story mode or challenge mode, doesn't matter)
	gameflow.mNextOnePlayerSectionID = ONEPLAYER_CardSelect;
#endif

	// force transit to new subsection
	gsys->softReset();
}
