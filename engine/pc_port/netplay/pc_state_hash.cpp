// Curated per-tick simulation hash (issue #878). See pc_state_hash.h for the
// exact format and field list.

#include "netplay/pc_state_hash.h"

#include "netplay/pc_input_log.h"

#include "Boss.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "MapMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "NaviMgr.h"
#include "ObjType.h"
#include "Pellet.h"
#include "PikiMgr.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "teki.h"

#include <SDL2/SDL.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

// The m1-det lane owns these (pc_port/netplay/pc_netplay_det.*,
// pc_port/netplay/pc_sim_rng.*). Declared weak here so this TU links without
// that lane; each use is guarded by a null check.
#if defined(__GNUC__)
__attribute__((weak)) bool pc_netplay_deterministic(void);
__attribute__((weak)) unsigned pc_sim_rng_state(void);
__attribute__((weak)) int pc_sim_rand(void);
// Netplay M4 lane A (issue #885): canonical hash of the sim-visible
// randomizer state. Null when the randomizer TU is not linked.
__attribute__((weak)) uint64_t pc_randomizer_hash(void);
#else
bool pc_netplay_deterministic(void);
unsigned pc_sim_rng_state(void);
int pc_sim_rand(void);
uint64_t pc_randomizer_hash(void);
#endif
// Netplay gapfix C (issue #885): the co-op randomizer policy's sim state
// (gameCoreSection.cpp). False when co-op is not active, so single-captain
// hashes are unchanged. Declared weak so this TU links without the game.
#if defined(__GNUC__)
__attribute__((weak)) bool pc_coop_policy_state_hash(uint64_t* out);
#else
bool pc_coop_policy_state_hash(uint64_t* out);
#endif

namespace {
constexpr uint64_t kFnvOffset = 14695981039346656037ULL;
constexpr uint64_t kFnvPrime  = 1099511628211ULL;

uint64_t fnvMix(uint64_t h, const void* data, size_t len)
{
	const uint8_t* p = (const uint8_t*)data;
	for (size_t i = 0; i < len; ++i) {
		h ^= (uint64_t)p[i];
		h *= kFnvPrime;
	}
	return h;
}

void mixU64(uint64_t& h, uint64_t v)
{
	uint8_t b[8];
	for (int i = 0; i < 8; ++i) b[i] = (uint8_t)((v >> (i * 8)) & 0xFF);
	h = fnvMix(h, b, 8);
}

void mixU32(uint64_t& h, uint32_t v)
{
	uint8_t b[4];
	for (int i = 0; i < 4; ++i) b[i] = (uint8_t)((v >> (i * 8)) & 0xFF);
	h = fnvMix(h, b, 4);
}

void mixS32(uint64_t& h, int32_t v) { mixU32(h, (uint32_t)v); }

void mixF32(uint64_t& h, float v)
{
	uint32_t bits = 0;
	std::memcpy(&bits, &v, sizeof(bits));
	mixU32(h, bits);
}

void mixVec(uint64_t& h, const Vector3f& v)
{
	mixF32(h, v.x);
	mixF32(h, v.y);
	mixF32(h, v.z);
}

uint64_t sTick          = 0;
bool sInitialised       = false;
bool sLogActive         = false;
FILE* sLogFile          = nullptr;
uint64_t sExitAfter     = 0;
bool sExitAfterSet      = false;
bool sExitRequested     = false;
uint64_t sExitTick      = 0;
bool sPrerollDone       = false;
const char* sArgvLog    = nullptr;
const char* sArgvExit   = nullptr;
// Netplay M3 lockstep capture (issue #880): last computed hashes, even with
// no log file open. Written only by pc_state_hash_tick_end().
bool sNetplayCapture    = false;
bool sNetplayHaveHash   = false;
uint64_t sLastTotal     = 0;
uint64_t sLastSubs[7]   = { 0, 0, 0, 0, 0, 0, 0 };
uint64_t sLastTick      = 0;

uint64_t parseU64(const char* text, bool& ok)
{
	ok = false;
	if (text == nullptr || *text == '\0') return 0;
	char* end = nullptr;
	unsigned long long v = std::strtoull(text, &end, 10);
	if (end == text || *end != '\0') return 0;
	ok = true;
	return (uint64_t)v;
}

const char* argvValue(int argc, char** argv, const char* flag)
{
	for (int i = 1; i + 1 < argc; ++i) {
		if (std::strcmp(argv[i], flag) == 0) return argv[i + 1];
	}
	return nullptr;
}

uint64_t hashNavi(void)
{
	// No live stage: exitStage reliably nulls naviMgr while the other
	// manager globals may still point at the released stage. Hash 0
	// instead of walking stale objects.
	if (naviMgr == nullptr) return 0;
	uint64_t h = kFnvOffset;
	Iterator it(naviMgr);
	CI_LOOP(it)
	{
		Navi* n = static_cast<Navi*>(*it);
		if (n == nullptr) continue;
		mixS32(h, (int32_t)n->mNaviID);
		mixVec(h, n->mSRT.t);
		mixVec(h, n->mSRT.r);
		mixVec(h, n->mVelocity);
		mixVec(h, n->mTargetVelocity);
		mixF32(h, n->mFaceDirection);
		mixF32(h, n->mHealth);
		AState<Navi>* st = n->getCurrState();
		mixS32(h, st != nullptr ? (int32_t)st->getID() : (int32_t)-1);
	}
	return h;
}

uint64_t hashPiki(void)
{
	if (naviMgr == nullptr || pikiMgr == nullptr) return 0;
	uint64_t h = kFnvOffset;
	Iterator it(pikiMgr);
	CI_LOOP(it)
	{
		Piki* p = static_cast<Piki*>(*it);
		if (p == nullptr) continue;
		mixU32(h, (uint32_t)p->mColor);
		mixS32(h, (int32_t)p->mHappa);
		uint32_t species = (p->mP2Purple ? 1u : 0u) | (p->mP2White ? 2u : 0u) | (p->mP2Bulbmin ? 4u : 0u);
		mixU32(h, species);
		mixVec(h, p->mSRT.t);
		mixVec(h, p->mSRT.r);
		mixVec(h, p->mVelocity);
		mixVec(h, p->mTargetVelocity);
		mixF32(h, p->mFaceDirection);
		mixF32(h, p->mHealth);
		AState<Piki>* st = p->getCurrState();
		mixS32(h, st != nullptr ? (int32_t)st->getID() : (int32_t)-1);
	}
	return h;
}

uint64_t hashTeki(void)
{
	if (naviMgr == nullptr || tekiMgr == nullptr) return 0;
	uint64_t h = kFnvOffset;
	Iterator it(tekiMgr);
	CI_LOOP(it)
	{
		Teki* t = static_cast<Teki*>(*it);
		if (t == nullptr) continue;
		mixS32(h, (int32_t)t->mTekiType);
		mixVec(h, t->mSRT.t);
		mixVec(h, t->mSRT.r);
		mixVec(h, t->mVelocity);
		mixVec(h, t->mTargetVelocity);
		mixF32(h, t->mFaceDirection);
		mixF32(h, t->mHealth);
		mixS32(h, (int32_t)t->mStateID);
	}
	return h;
}

uint64_t hashItem(void)
{
	if (naviMgr == nullptr) return 0;
	if (itemMgr == nullptr && pelletMgr == nullptr && bossMgr == nullptr) return 0;
	uint64_t h = kFnvOffset;
	if (itemMgr != nullptr) {
		Iterator it(itemMgr);
		CI_LOOP(it)
		{
			Creature* c = *it;
			if (c == nullptr) continue;
			mixS32(h, (int32_t)c->mObjType);
			mixVec(h, c->mSRT.t);
			mixVec(h, c->mSRT.r);
			mixVec(h, c->mVelocity);
			mixVec(h, c->mTargetVelocity);
			mixF32(h, c->mFaceDirection);
			// Goal check uses the same mObjType test as
			// ItemMgr::getContainer (itemMgr.cpp), then a static_cast:
			// no dynamic_cast, so no vptr chase through stale objects.
			if (c->mObjType == OBJTYPE_Goal) {
				GoalItem* goal = static_cast<GoalItem*>(c);
				mixU32(h, (uint32_t)goal->mOnionColour);
				mixU32(h, goal->mHeldPikis[0]);
				mixU32(h, goal->mHeldPikis[1]);
				mixU32(h, goal->mHeldPikis[2]);
			}
		}
		// Onion/container counts per colour, via the colour-indexed lookup
		// (0 when that colour has no Onion).
		for (int color = PikiMinColor; color <= PikiMaxColor; ++color) {
			GoalItem* onion = itemMgr->getContainer(color);
			if (onion == nullptr) {
				mixU32(h, 0);
				mixU32(h, 0);
				mixU32(h, 0);
			} else {
				mixU32(h, onion->mHeldPikis[0]);
				mixU32(h, onion->mHeldPikis[1]);
				mixU32(h, onion->mHeldPikis[2]);
			}
		}
	}
	if (pelletMgr != nullptr) {
		Iterator it(pelletMgr);
		CI_LOOP(it)
		{
			Pellet* p = static_cast<Pellet*>(*it);
			if (p == nullptr) continue;
			if (p->mConfig != nullptr) {
				mixU32(h, p->mConfig->mPelletId.mId);
				mixS32(h, (int32_t)p->mConfig->mPelletType());
			} else {
				mixU32(h, 0);
				mixS32(h, 0);
			}
			mixVec(h, p->mSRT.t);
			mixVec(h, p->mSRT.r);
			mixVec(h, p->mVelocity);
			mixVec(h, p->mTargetVelocity);
			mixF32(h, p->mFaceDirection);
			AState<Pellet>* st = p->getCurrState();
			mixS32(h, st != nullptr ? (int32_t)st->getID() : (int32_t)-1);
			mixS32(h, (int32_t)p->getState());
			mixU32(h, (uint32_t)p->mCarrierCount);
		}
	}
	if (bossMgr != nullptr) {
		Iterator it(bossMgr);
		CI_LOOP(it)
		{
			Boss* b = static_cast<Boss*>(*it);
			if (b == nullptr) continue;
			mixS32(h, (int32_t)b->getCurrentState());
			mixS32(h, (int32_t)b->getNextState());
			mixF32(h, b->getCurrentLife());
			mixVec(h, b->mSRT.t);
			mixVec(h, b->mSRT.r);
			mixVec(h, b->mVelocity);
			mixVec(h, b->mTargetVelocity);
			mixF32(h, b->mFaceDirection);
		}
	}
	return h;
}

uint64_t hashWorld(void)
{
	uint64_t h = kFnvOffset;
	mixF32(h, gameflow.mWorldClock.mTimeOfDay);
	mixS32(h, (int32_t)gameflow.mWorldClock.mCurrentDay);
	if (playerState != nullptr) {
		mixS32(h, (int32_t)playerState->mLivingPikiNum);
		mixS32(h, (int32_t)playerState->mTotalBornPikiNum);
		mixS32(h, (int32_t)playerState->mTotalDeadPikiNum);
		mixS32(h, (int32_t)playerState->mTotalPluckedPikiCount);
	} else {
		mixS32(h, 0);
		mixS32(h, 0);
		mixS32(h, 0);
		mixS32(h, 0);
	}
	return h;
}

uint64_t hashRng(void)
{
#if defined(__GNUC__)
	if (pc_sim_rng_state != nullptr) return (uint64_t)pc_sim_rng_state();
#else
	(void)0;
#endif
	return 0;
}

uint64_t hashRand(void)
{
	// M4a: 0 when the randomizer TU is not linked or the randomizer is off
	// (pc_randomizer_hash returns 0 then); identical on both peers either
	// way, and divergent exactly when the sim-visible randomizer state is.
	uint64_t h = 0;
#if defined(__GNUC__)
	if (pc_randomizer_hash != nullptr) h = (uint64_t)pc_randomizer_hash();
#else
	if (pc_randomizer_hash != nullptr) h = (uint64_t)pc_randomizer_hash();
#endif
	// Gapfix C (#885): while co-op is active, the co-op policy state (its
	// cursors, tick, HP samples and cooldowns decide who gets each grant) is
	// folded in. Single-captain play folds nothing: the column is unchanged.
	uint64_t coop = 0;
	if (pc_coop_policy_state_hash != nullptr && pc_coop_policy_state_hash(&coop)) mixU64(h, coop);
	return h;
}

void initOnce(void)
{
	sInitialised = true;
	const char* logPath = sArgvLog;
	const char* exitText = sArgvExit;
	if (logPath == nullptr) logPath = std::getenv("PIKMIN_STATE_HASH_LOG");
	if (exitText == nullptr) exitText = std::getenv("PIKMIN_NETPLAY_EXIT_AFTER_TICKS");
	if (logPath != nullptr && *logPath != '\0') {
		sLogFile = std::fopen(logPath, "w");
		if (sLogFile != nullptr) {
			std::setvbuf(sLogFile, nullptr, _IOFBF, 64 * 1024);
			sLogActive = true;
			std::printf("[netplay] state hash log: %s\n", logPath);
			std::fflush(stdout);
		} else {
			std::printf("[netplay] state hash log: cannot open %s\n", logPath);
			std::fflush(stdout);
		}
	}
	if (exitText != nullptr && *exitText != '\0') {
		bool ok = false;
		uint64_t n = parseU64(exitText, ok);
		if (ok && n > 0) {
			sExitAfter    = n;
			sExitAfterSet = true;
		}
	}
}
} // namespace

void pc_state_hash_notify_argv(int argc, char** argv)
{
	if (argv == nullptr) return;
	sArgvLog  = argvValue(argc, argv, "--state-hash-log");
	sArgvExit = argvValue(argc, argv, "--netplay-exit-after-ticks");
}

void pc_state_hash_before_first_tick(void)
{
	if (sPrerollDone) return;
	sPrerollDone = true;
	const char* text = std::getenv("PIKMIN_NETPLAY_TEST_PREROLL_RAND");
	if (text == nullptr || *text == '\0') return;
	bool ok     = false;
	uint64_t n  = parseU64(text, ok);
	if (!ok) return;
	for (uint64_t i = 0; i < n; ++i) {
		(void)std::rand();
#if defined(__GNUC__)
		if (pc_sim_rand != nullptr) (void)pc_sim_rand();
#endif
	}
}

uint64_t pc_state_hash_tick(void) { return sTick; }

void pc_state_hash_set_netplay_capture(bool on) { sNetplayCapture = on; }

bool pc_state_hash_current(uint64_t* total, uint64_t subs[7], uint64_t* tick)
{
	if (!sNetplayHaveHash) return false;
	if (total != nullptr) *total = sLastTotal;
	if (subs != nullptr) {
		for (int i = 0; i < 7; ++i) subs[i] = sLastSubs[i];
	}
	if (tick != nullptr) *tick = sLastTick;
	return true;
}

void pc_state_hash_flush(void)
{
	if (sLogFile != nullptr) std::fflush(sLogFile);
}

// TEST_ONLY (issue #1037): PIKMIN_NETPLAY_TEST_TELEPORT="tick:navi:x:z;tick:navi:x:z..."
// moves captain <navi> (0 = P1, 1 = P2) and every Pikmin it owns next to (x, z) once the
// deterministic tick reaches <tick> (applied at the end of that tick, so the same on both
// peers when both get the same value). Lets a scripted pair reach a boss (the Final Trial
// Emperor Bulblax is about x=17 z=2450) without a long walk. Inert unless set; it changes sim
// state, so give it to both peers (run_pair scrubs it from the inherited environment). Gated behind
// PIKMIN_RANDOMIZER_TEST_BACKGROUND=1 (hidden test runs), so it is inert in normal play.
static void pcTestTeleport(uint64_t tick)
{
	static bool init = false;
	struct Tp { unsigned long long tick; int navi; float x, z; bool done; };
	static Tp tps[16];
	static int ntp = 0;
	if (!init) {
		init = true;
		// Hidden test runs only (PIKMIN_RANDOMIZER_TEST_BACKGROUND=1), like the desync nudge knob:
		// inert in normal play even if the variable is set in the environment.
		const char* bg = std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND");
		const char* e  = (bg != nullptr && std::strcmp(bg, "1") == 0) ? std::getenv("PIKMIN_NETPLAY_TEST_TELEPORT") : nullptr;
		while (e && *e && ntp < 16) {
			unsigned long long t = 0;
			int n = 0, used = 0;
			float x = 0, z = 0;
			if (std::sscanf(e, "%llu:%d:%f:%f%n", &t, &n, &x, &z, &used) < 4) break;
			tps[ntp++] = { t, n, x, z, false };
			e += used;
			while (*e == ';' || *e == ' ') ++e;
		}
	}
	if (ntp == 0 || naviMgr == nullptr || mapMgr == nullptr) return;
	for (int i = 0; i < ntp; ++i) {
		if (tps[i].done || tick != tps[i].tick) continue;
		tps[i].done = true;
		Navi* nv = naviMgr->getNavi(tps[i].navi);
		if (!nv) continue;
		const float y = mapMgr->getMinY(tps[i].x, tps[i].z, true);
		nv->mSRT.t.set(tps[i].x, y + 2.0f, tps[i].z);
		nv->mVelocity.set(0.0f, 0.0f, 0.0f);
		int k = 0;
		if (pikiMgr != nullptr) {
			Iterator it(pikiMgr);
			CI_LOOP(it)
			{
				Piki* pk = static_cast<Piki*>(*it);
				if (!pk || pk->mNavi != nv) continue;
				const float ang = (float)(k++) * 0.61803f * 6.2831853f;
				const float px = tps[i].x + 30.0f * std::cos(ang), pz = tps[i].z + 30.0f * std::sin(ang);
				pk->mSRT.t.set(px, mapMgr->getMinY(px, pz, true) + 2.0f, pz);
				pk->mVelocity.set(0.0f, 0.0f, 0.0f);
			}
		}
		std::printf("[netplay-test] teleport tick=%llu navi=%d to (%.1f %.1f %.1f), %d pikmin\n", tick, tps[i].navi,
		            tps[i].x, y, tps[i].z, k);
		std::fflush(stdout);
	}
}

void pc_state_hash_tick_end(void)
{
	if (!sInitialised) initOnce();
	// COMMON rule 3: with no netplay switch set, return before walking
	// any manager. No hashes, no files, no timing change. (The M3 lockstep
	// session opts into per-tick hashing via sNetplayCapture even when no
	// log file is open, so Save events and desync dumps have checksums.)
	if (!sLogActive && !sExitAfterSet && !sNetplayCapture) return;
	if (sExitRequested) {
		// The quit event is already queued; the main loop breaks on its
		// next pc_window_should_close() check. Fall back to a direct
		// exit only if the loop is stuck.
		if (sTick >= sExitTick + 600) {
			pc_state_hash_flush();
			pc_input_log_flush();
			pc_input_log_close();
			std::fflush(stdout);
			std::exit(0);
		}
		return;
	}
	++sTick;

	uint64_t navi  = 0;
	uint64_t piki  = 0;
	uint64_t teki  = 0;
	uint64_t item  = 0;
	uint64_t world = 0;
	uint64_t rng   = 0;
	uint64_t rand  = 0;
	uint64_t total = 0;
	// M3 lockstep: hash every tick when capturing, even with no log file.
	if (sLogActive || sNetplayCapture) {
		navi  = hashNavi();
		piki  = hashPiki();
		teki  = hashTeki();
		item  = hashItem();
		world = hashWorld();
		rng   = hashRng();
		rand  = hashRand();
		total = kFnvOffset;
		mixU64(total, navi);
		mixU64(total, piki);
		mixU64(total, teki);
		mixU64(total, item);
		mixU64(total, world);
		mixU64(total, rng);
		mixU64(total, rand);

		sLastTotal    = total;
		sLastSubs[0]  = navi;
		sLastSubs[1]  = piki;
		sLastSubs[2]  = teki;
		sLastSubs[3]  = item;
		sLastSubs[4]  = world;
		sLastSubs[5]  = rng;
		sLastSubs[6]  = rand;
		sLastTick     = sTick;
		sNetplayHaveHash = true;
		pcTestTeleport(sTick);

		if (sLogActive) {
			std::fprintf(sLogFile, "%llu %016llx %016llx %016llx %016llx %016llx %016llx %016llx %016llx\n",
			             (unsigned long long)sTick, (unsigned long long)total, (unsigned long long)navi,
			             (unsigned long long)piki, (unsigned long long)teki, (unsigned long long)item,
			             (unsigned long long)world, (unsigned long long)rng, (unsigned long long)rand);
			if (sTick % 300 == 0) std::fflush(sLogFile);
		}
	}

	if (sExitAfterSet && sTick >= sExitAfter) {
		pc_state_hash_flush();
		pc_input_log_flush();
		pc_input_log_close();
		std::fflush(stdout);
		// Clean quit through the same route as normal play: queue SDL_QUIT
		// so System::run breaks on pc_window_should_close() and main
		// returns through "[PC Port] Game exited normally.". Stop hashing
		// further ticks; the counter above is the fallback if the loop
		// never drains the event.
		sExitRequested = true;
		sExitTick      = sTick;
		SDL_Event ev;
		std::memset(&ev, 0, sizeof(ev));
		ev.type = SDL_QUIT;
		SDL_PushEvent(&ev);
	}
}
