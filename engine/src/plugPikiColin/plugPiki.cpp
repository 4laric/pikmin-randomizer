#include "App.h"

#include "AtxStream.h"
#include "DebugLog.h"
#include "Graphics.h"
#include "Interface.h"
#include "gameflow.h"
#include "sysMath.h"
#include "sysNew.h"
#include "timers.h"

#include <chrono>
#include <cstdlib>

#include "timing/pc_render_phase.h"
#include "timing/pc_tick_profiler.h"
#include "pc_gfx.h"
#if defined(PIKI_PC_PORT)
#include "netplay/pc_netplay_camlead.h"
#include "netplay/pc_netplay_det.h"
#include "netplay/pc_netplay_present.h"
#endif

#define TIMER_STATE_X           (32) ///< Horizontal position to start printing timer debug text from.
#define TIMER_STATE_Y           (32) ///< Vertical position to start printing timer debug text from.
#define TIMER_STATE_LINE_HEIGHT (12) ///< How far down to offset each line of timer debug text from the previous.

/**
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @note UNUSED Size: 0000F4
 */
DEFINE_PRINT("plugPiki")

/**
 * @brief Performs a full system reset, including timers and the overlay heap, intended for boot setup.
 */
void PlugPikiApp::hardReset()
{
	// use system heap for resetting game flow
	useHeap(SYSHEAP_Sys);

	gsys->mTimer = new Timers;
	gameflow.hardReset(this);

	AyuHeap* sysHeap    = gsys->getHeap(SYSHEAP_Sys);
	int overlayHeapSize = sysHeap->getMaxFree();

	// allocate space for overlay heap from the system heap
	int oldAlloc = sysHeap->setAllocType(AYU_STACK_GROW_UP);
#if defined(PIKI_PC_PORT)
	// Same shape as the app stack in GameFlow::softReset: on the console this
	// came out of the sys arena and was reclaimed by a cursor, while here it is
	// a C-heap block that nothing gives back. A hard reset would otherwise
	// abandon the whole overlay heap, which is most of the simulated arena.
	static u8* sPreviousOverlayHeap = nullptr;
	delete[] sPreviousOverlayHeap;
	sPreviousOverlayHeap = nullptr;
#endif
	u8* buf      = new u8[sysHeap->getMaxFree()];
#if defined(PIKI_PC_PORT)
	sPreviousOverlayHeap = buf;
#endif
	sysHeap->setAllocType(oldAlloc);

	// set up overlay heap using all remaining free space from system heap
	gsys->getHeap(SYSHEAP_Ovl)->init("ovl", AYU_STACK_GROW_UP, buf, overlayHeapSize);
	gsys->resetHeap(SYSHEAP_Ovl, AYU_STACK_GROW_DOWN);
	gsys->getHeap(SYSHEAP_Ovl)->setAllocType(AYU_STACK_GROW_DOWN);
	useHeap(SYSHEAP_Ovl);

	// force a transition to a game section
	gsys->softReset();
}

/**
 * @brief Performs a partial system reset, re-initialising sections and resources, and primes the app for drawing.
 */
void PlugPikiApp::softReset()
{
	BaseApp::softReset();
	gameflow.softReset();
	mIsReadyToDraw = TRUE;
}

/**
 * @brief Updates the game state by one frame, by iteratively updating its child nodes.
 *
 * `gameflow`'s `mFlowManager` is a child of this, and therefore gets updated by `Node::update`.
 * `mFlowManager` itself contains the current game section as a child node, which therefore gets updated,
 * causing everything else game-related to update.
 */
void PlugPikiApp::update()
{
	gameflow.mAppTickCounter++;
	gameflow.update();

	// iteratively update all our child nodes
	Node::update();
}

/**
 * @brief Draws the current frame, by iteratively drawing its child nodes. Also draws some debug text, if enabled.
 *
 * `gameflow`'s `mFlowManager` is a child of this, and therefore gets drawn by `Node::draw`.
 * `mFlowManager` itself contains the current game section as a child node, which therefore gets drawn,
 * causing everything else game-related to be rendered.
 *
 * @param gfx Graphics context for rendering.
 */
void PlugPikiApp::draw(Graphics& gfx)
{
	if (!mIsReadyToDraw) {
		return;
	}

	gsys->mTimer->start("cpu draw", true);
	gsys->mDispCount        = 0;
	gsys->mMaterialCount    = 0;
	gsys->mPolygonCount     = 0;
	gsys->mActiveLightCount = 0;
	gsys->mLightCount       = 0;
	gsys->mAnimatedPolygons = 0;
	gsys->mLightingSkips    = 0;
	gsys->mLightingSets     = 0;
	gsys->mLightSetNum      = 0;

	// iteratively draw all our child nodes
	Node::draw(gfx);

	// draw any whole-game overlays
	Matrix4f orthoMtx;
	gfx.setOrthogonal(orthoMtx.mMtx, AREA_FULL_SCREEN(gfx));
	gfx.useTexture(nullptr, GX_TEXMAP0);

	// if timer is active, print a bunch of graphics trackables to the screen
	if (gsys->mTimerState != TS_Off) {
		gfx.setColour(COLOUR_WHITE, true);
		gfx.texturePrintf(gsys->mConsFont, TIMER_STATE_X, TIMER_STATE_Y + 0 * TIMER_STATE_LINE_HEIGHT, "%d polys = %d pps",
		                  gsys->mPolygonCount, int(gsys->mPolygonCount * gsys->getFrameRate()));
		gfx.texturePrintf(gsys->mConsFont, TIMER_STATE_X, TIMER_STATE_Y + 1 * TIMER_STATE_LINE_HEIGHT, "%d anims", gsys->mAnimatedPolygons);
		gfx.texturePrintf(gsys->mConsFont, TIMER_STATE_X, TIMER_STATE_Y + 2 * TIMER_STATE_LINE_HEIGHT, "%d mats", gsys->mMaterialCount);
		gfx.texturePrintf(gsys->mConsFont, TIMER_STATE_X, TIMER_STATE_Y + 3 * TIMER_STATE_LINE_HEIGHT, "%d disps", gsys->mDispCount);
		gfx.texturePrintf(gsys->mConsFont, TIMER_STATE_X, TIMER_STATE_Y + 4 * TIMER_STATE_LINE_HEIGHT, "%d mtxs",
		                  gsys->mDGXGfx->mNextFreeMatrixIdx);
		gfx.texturePrintf(gsys->mConsFont, TIMER_STATE_X, TIMER_STATE_Y + 5 * TIMER_STATE_LINE_HEIGHT, "%d / %d lighting skips / sets",
		                  gsys->mLightingSkips, gsys->mLightingSets);
		gfx.texturePrintf(gsys->mConsFont, TIMER_STATE_X, TIMER_STATE_Y + 6 * TIMER_STATE_LINE_HEIGHT, "%d light sets", gsys->mLightSetNum);
	}

	// PIKMIN_PERF_HUD=1: CPU and GPU milliseconds in the corner, so a phone
	// can be profiled without a logcat attached. Percentiles over the last
	// 120 ticks, refreshed twice a second: the eye wants "now", not the
	// minute-long window the console report uses.
	if (pc_tick_profiler_hud_enabled()) {
		static char hudLine[3][96] = { "perf hud: waiting for samples", "", "" };
		static int hudRefresh      = 0;
		if (++hudRefresh >= 30) {
			hudRefresh                  = 0;
			const double budget         = 1000.0 / 60.0;
			const size_t recent         = 120;
			const PcTickStats tick      = pc_tick_profiler_stats(kPcTickWhole, budget, recent);
			const PcTickStats update    = pc_tick_profiler_stats(kPcTickUpdate, budget, recent);
			const PcTickStats render    = pc_tick_profiler_stats(kPcTickRenderAll, budget, recent);
			const PcTickStats done      = pc_tick_profiler_stats(kPcTickDoneRender, budget, recent);
			const PcTickStats gpuScene  = pc_tick_profiler_stats(kPcTickGpuScene, budget, recent);
			const PcTickStats gpuBlit   = pc_tick_profiler_stats(kPcTickGpuBlit, budget, recent);
			const PcTickStats draws     = pc_tick_profiler_stats(kPcTickGfxDrawCount, budget, recent);
			const PcTickStats sim       = pc_tick_profiler_stats(kPcTickWorldSim, budget, recent);
			const PcTickStats uniforms  = pc_tick_profiler_stats(kPcTickGfxUniforms, budget, recent);
			const PcTickStats dl        = pc_tick_profiler_stats(kPcTickGfxDisplayList, budget, recent);
			const PcTickStats meshDraws = pc_tick_profiler_stats(kPcTickGfxMeshDraws, budget, recent);
			snprintf(hudLine[0], sizeof hudLine[0], "%.0f fps  cpu %.1f ms (p99 %.1f)  %.0f draws (%.0f mesh)", gsys->getFrameRate(),
			         tick.median, tick.p99, draws.mean, meshDraws.mean);
			// renderall includes the world simulation (see newPikiGame.cpp);
			// "gx" is what remains of it: the GX translation.
			snprintf(hudLine[1], sizeof hudLine[1], "sim %.1f  gx %.1f (dl %.1f uni %.1f)  ren %.1f/%.1f  done %.1f", sim.median,
			         render.median - sim.median, dl.median, uniforms.median, render.median, render.p99, done.median);
			(void)update;
			if (gpuScene.samples != 0) {
				snprintf(hudLine[2], sizeof hudLine[2], "gpu scene %.1f/%.1f  blit %.1f/%.1f", gpuScene.median, gpuScene.p99,
				         gpuBlit.median, gpuBlit.p99);
			} else {
				snprintf(hudLine[2], sizeof hudLine[2], "gpu: no timer queries");
			}
		}
		gfx.setColour(COLOUR_WHITE, true);
		for (int i = 0; i < 3; i++) {
			gfx.texturePrintf(gsys->mConsFont, 16, 400 + i * TIMER_STATE_LINE_HEIGHT, "%s", hudLine[i]);
		}
	}

	// print load text after we finish a section transition (only if it's meant to be visible, or is fading out)
	// NB: the code in retail and the DLL do all the preparation to print, but never actually print the text.
	if (gameflow.mCurrLoadTextAlpha > 0.0f || gameflow.mTargetLoadTextAlpha > 0.0f) {
#if defined(PIKI_PC_PORT)
		// M2b fix (review M2): the load-text timer is sim timing; the
		// presentation pass draws the overlay but must not advance it.
		if (pc_netplay_present_sim_side()) {
#endif
		gameflow.mLoadTextDisplayTimer -= gsys->getFrameTime();
		if (gameflow.mLoadTextDisplayTimer < 0.0f) {
			gameflow.mTargetLoadTextAlpha = 0.0f;
		}

		gameflow.mCurrLoadTextAlpha
		    += gsys->getFrameTime() * 1.0f * (gameflow.mTargetLoadTextAlpha - gameflow.mCurrLoadTextAlpha);
		if (quickABS(gameflow.mCurrLoadTextAlpha - gameflow.mTargetLoadTextAlpha) < 0.1f) {
			gameflow.mCurrLoadTextAlpha = gameflow.mTargetLoadTextAlpha;
		}
#if defined(PIKI_PC_PORT)
		}
#endif

		gfx.setColour(Colour(192, 255, 255, gameflow.mCurrLoadTextAlpha), true);
		gfx.setAuxColour(Colour(192, 192, 255, gameflow.mCurrLoadTextAlpha));
		char loadText[PATH_MAX];
		sprintf(loadText, "load took %.1f secs", gameflow.mLoadTimeSeconds);
#if defined(DEVELOP)
		// this doesn't exist in any build, but clearly something did at one stage.
		gfx.texturePrintf(gsys->mConsFont, 32, 10, loadText);
#endif
	}

	gfx.useTexture(nullptr, GX_TEXMAP0);

	// this is actually for allowing buffer time before transiting between sections, rather than fading anything
#if defined(PIKI_PC_PORT)
	// M2b fix (review M2): the global fade gates section exits (getFade() ==
	// 0.0f), so advancing it in both passes would run transitions at double
	// speed in det mode. Presentation draws the overlay; only the sim side
	// advances.
	if (pc_netplay_present_sim_side()) {
#endif
	if (gsys->mCurrentFade < gsys->mTargetFade) {
		// "fading in"
		gsys->mCurrentFade += gsys->getFrameTime() * gsys->mFadeRate;
		if (gsys->mCurrentFade > gsys->mTargetFade) {
			gsys->mCurrentFade = gsys->mTargetFade;
		}

	} else if (gsys->mCurrentFade > gsys->mTargetFade) {
		// "fading out"
		gsys->mCurrentFade = gsys->mTargetFade;
		gsys->mCurrentFade -= gsys->getFrameTime() * gsys->mFadeRate;
		if (gsys->mCurrentFade < gsys->mTargetFade) {
			gsys->mCurrentFade = gsys->mTargetFade;
		}
	}
#if defined(PIKI_PC_PORT)
	}
#endif

	// draw timers, if enabled
	if (gsys->mTimerState != TS_Off) {
		gsys->mTimer->draw(gfx, gsys->mConsFont);
	}

	gsys->mTimer->stop("cpu draw");
}

/**
 * @brief Base "idle" loop of the game application, initiating all updating, drawing, and transitions.
 *
 * @return Always returns 1.
 */
int PlugPikiApp::idle()
{
	gsys->setHeap(mHeapIndex);
	gsys->mTimer->newFrame();
	gsys->mTimer->_start("all", false);

	gsys->mIsRendering; // ok.

	// if we have a transition queued, do partial reset without updating
	if (gsys->mSoftResetPending) {
		gsys->detachObjs();
		gsys->mTimer->reset();
		gsys->mSoftResetPending = false;

#if defined(PIKI_PC_PORT)
		// M2b fix (review M3): a soft-reset idle returns before
		// pc_render_begin_authoritative_tick, so make sure section
		// construction below runs as authoritative, never as a stale
		// presentation phase from the previous tick.
		pc_render_end_presentation();
#endif
		softReset();

		// re-attach everything
		PRINT("idle attach\n");
		gsys->attachObjs();
		PRINT("done attaching objs!\n");
		return 1;
	}

	// Begin authoritative tick
	pc_render_begin_authoritative_tick();

	// Cost of the work a 60 Hz gameplay mode would have to run twice as often.
	// waitRetrace below is deliberately outside every span: it is the wait, not
	// the work, and counting it would make every tick look exactly like the
	// frame period no matter how cheap it really was.
	const bool profiling = pc_tick_profiler_enabled();
	const auto clockNow  = [] {
		return std::chrono::duration<double, std::milli>(
		           std::chrono::steady_clock::now().time_since_epoch())
		    .count();
	};
	const double tickStart = profiling ? clockNow() : 0.0;

	const double updateStart = profiling ? clockNow() : 0.0;
	update();
	if (profiling) {
		pc_tick_profiler_record(kPcTickUpdate, clockNow() - updateStart);
	}

	gsys->beginRender();

#if defined(PIKI_PC_PORT)
	// M2b two-pass frame (issue #879), det mode only. Non-det stays exactly
	// as today: one pass. The m3 lane can set skip-presentation for future
	// rollback resimulation (authoritative only).
	if (pc_netplay_present_two_pass_active() && !pc_netplay_present_skip_presentation()) {
		// 1. Authoritative pass: today's draw body with SimCamera + null GX.
		pc_netplay_present_begin_authoritative(*gsys->mDGXGfx);
		const double authStart = profiling ? clockNow() : 0.0;
		renderall();
		if (profiling) {
			pc_tick_profiler_record(kPcTickRenderAll, clockNow() - authStart);
		}
		// Drop any batched geometry while null is still on (the null-gated
		// flush clears the batch without touching GL); the presentation pass
		// must not draw the sim pass's vertices.
		pc_gfx_flush_batch();
		pc_netplay_present_end_authoritative(*gsys->mDGXGfx);

		// 2. Presentation pass: local view only, real camera + real GL.
		// Sim blocks are skipped via pc_render_is_authoritative() == false.
		pc_render_begin_presentation(1.0);
		gsys->mDGXGfx->resetPresentBuffer();
		pc_netplay_present_begin_presentation(*gsys->mDGXGfx);
		// Issue #1031: the authoritative pass's 2D screens (end-of-day countdown)
		// leave the wide-HUD mapping set; start the presentation pass clean.
		pc_gfx_reset_ui_state();
		// M2b fix (review M1): initRender runs once per idle before the auth
		// pass. Without a reset here the auth pass's lights, cached
		// (translucent) shapes and lens flares leak into presentation:
		// re-adding an already-listed Light truncates the list at itself and
		// links it into a self-loop (the old DayMgr "stall"), cached shapes
		// re-flush sim-pool matrices under the real camera, and the cache /
		// flare counts accumulate toward fatal overflow. Mirror what
		// beginView(view>0) does, plus flares. The sim matrix pool is
		// deliberately untouched (presentation allocates separately).
		gsys->mDGXGfx->mActiveLightMask = 0;
		gsys->mDGXGfx->mLight.initCore("");
		gsys->mDGXGfx->resetCacheBuffer();
		gsys->resetLFlares();
		// Capture the presented (local) view, not the null pass.
		pc_gfx_begin_capture(pc_render_tick_serial());
		const double presentStart = profiling ? clockNow() : 0.0;
		renderall();
		if (profiling) {
			// Presentation cost rides in Whole; keep RenderAll as the sim
			// pass so world-sim comparisons stay meaningful. Flush stats
			// once for the presented frame.
			pc_gfx_flush_submit_stats();
			(void)presentStart;
		}
		pc_gfx_end_capture();
		pc_netplay_present_restore_all_shapes();
		pc_netplay_present_end_presentation(*gsys->mDGXGfx);
		// M5c lane A (issue #887): put gfx.mCamera back to the sim camera
		// if the lead camera was presented (and log its trace line).
		pc_netplay_camlead_end_presentation(*gsys->mDGXGfx);
		// M2b fix (review M3): back to authoritative so doneRender,
		// parseMessages, hashing and any soft-reset idle run as sim, and the
		// next presentation starts from a clean save list.
		pc_render_end_presentation();
		// M2b acceptance evidence: null-GX counters, one line per 3000
		// ticks on stdout (native.log). Real GL issued while null was
		// active must stay 0; attempted counts the skipped submissions.
		{
			const unsigned tick = pc_netplay_tick();
			if (tick % 3000 == 0) {
				printf("[m2b] tick=%u null_attempted=%llu null_gl=%llu saved_shapes=%llu\n", tick,
				       pc_netplay_present_null_attempted(), pc_netplay_present_null_gl_calls(),
				       pc_netplay_present_saved_shapes());
				fflush(stdout);
			}
		}
	} else if (pc_netplay_present_two_pass_active() && pc_netplay_present_skip_presentation()) {
		// M2b helper for m3 resim: authoritative only, null GX, no capture.
		// Contract note for m3 (review m4): this still runs beginRender (a
		// real clear), doneRender and waitRetrace below, so a resim tick
		// would swap a blank frame and throttle. No driver calls this yet;
		// gate present/retrace here once m3 wires resimulation in (taking
		// care with the retrace count, which sim timing reads).
		pc_netplay_present_begin_authoritative(*gsys->mDGXGfx);
		const double authStart = profiling ? clockNow() : 0.0;
		renderall();
		if (profiling) {
			pc_tick_profiler_record(kPcTickRenderAll, clockNow() - authStart);
			pc_gfx_flush_submit_stats();
		}
		pc_gfx_flush_batch();
		pc_netplay_present_end_authoritative(*gsys->mDGXGfx);
	} else {
		// Begin capture for immutable render packets
		pc_gfx_begin_capture(pc_render_tick_serial());

		const double renderStart = profiling ? clockNow() : 0.0;
		renderall();
		if (profiling) {
			pc_tick_profiler_record(kPcTickRenderAll, clockNow() - renderStart);
			pc_gfx_flush_submit_stats();
		}

		pc_gfx_end_capture();
	}
#else
	// Begin capture for immutable render packets
	pc_gfx_begin_capture(pc_render_tick_serial());

	const double renderStart = profiling ? clockNow() : 0.0;
	renderall();
	if (profiling) {
		pc_tick_profiler_record(kPcTickRenderAll, clockNow() - renderStart);
		pc_gfx_flush_submit_stats();
	}

	pc_gfx_end_capture();
#endif

	if (gsys->mDvdErrorCallback) {
		gsys->mDvdErrorCallback->invoke(*gsys->mDGXGfx);
	}
	gsys->mTimer->start("render", true);
	const double doneStart = profiling ? clockNow() : 0.0;
	gsys->doneRender();
	if (profiling) {
		pc_tick_profiler_record(kPcTickDoneRender, clockNow() - doneStart);
		pc_tick_profiler_record(kPcTickWhole, clockNow() - tickStart);
	}
	gsys->mTimer->stop("render");

	// process any messages that have built up this frame
	if (gameflow.mGameInterface) {
		gameflow.mGameInterface->parseMessages();
	}

	gsys->mTimer->_stop("all");

	gsys->waitRetrace();
	gsys->setHeap(SYSHEAP_NULL);

	return 1;
}

/**
 * @brief Constructs the root game app and initiates boot setup.
 */
PlugPikiApp::PlugPikiApp()
{
	setName("Piki the Game"); // you sure are buddy

	// initial boot-up - hard reset app
	gsys->setHeap(SYSHEAP_Sys);
	hardReset();

	// set up command stream for linking between "services"
	// (this is unused in the DOL version, but is used in the DLL)
	mCommandStream = new AtxCommandStream(this);
	if (mCommandStream->open(ATX_SERVICE_APP, 3)) {
		mCommandStream->mPath = Name();
	} else {
		mCommandStream = nullptr;
	}

#if defined(PIKI_PC_PORT)
	// Direct gameplay launches skip the title screen that normally hides these
	// counters, and the PC build has no legacy debug menu to turn them off.
	gsys->mTimerState = TS_Off;
#else
	// Original sections disable the startup debug timers when entered.
	gsys->mTimerState = TS_On;
#endif

	// also do system hard reset
	gsys->hardReset();

	PRINT("*--------------- <%s> after all system setup %.2fk free \n", gsys->getHeap(gsys->mActiveHeapIdx)->mName,
	      gsys->getHeap(gsys->mActiveHeapIdx)->getFree() / 1024.0f);
	gsys->mForcePrint = FALSE;

	// unset heap index - it will be set fresh next frame
	gsys->setHeap(SYSHEAP_NULL);
}
