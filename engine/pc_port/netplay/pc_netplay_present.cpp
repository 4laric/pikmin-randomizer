// Netplay M2b two-pass present module (issue #879). See header for contract.
//
// Engine-free core (skip flag, null-GX counters, local player) lives here
// without engine includes so host tests can link it. Engine helpers
// (SimCamera + pass begin/end + shape-pointer save/restore) are guarded by
// PIKI_PC_PORT.

#include "netplay/pc_netplay_present.h"

#include <cmath>
#include <cstdlib>
#include <cstring>
#include <utility>
#include <vector>

#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST)
#include "Camera.h"
#include "Graphics.h"
#include "Matrix4f.h"
#include "netplay/pc_netplay_det.h"
#include "timing/pc_render_phase.h"
#else
#include "netplay/pc_netplay_det.h"
#endif

namespace {
bool sSkipPresentation = false;
bool sNullGx = false;
unsigned long long sNullReal = 0;
unsigned long long sNullAttempted = 0;
unsigned long long sSavedShapes = 0;
int sLocalPlayerCached = 0;
bool sLocalPlayerInit = false;
#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST)
Camera* sSimCamera = nullptr;
Graphics* sSavedGfx = nullptr;
Camera* sSavedCamera = nullptr;
// Per-presentation shape-pointer save list. A vector of (shape, simPtr)
// pairs: append-only during the pass, indexed restore after it. n is tiny
// (~33 shapes), so a linear "already saved" scan beats a node-allocating
// map through the tick allocator every frame.
std::vector<std::pair<void*, void*>> sSavedPtrs;
#endif
} // namespace

extern "C" {

void pc_netplay_present_set_skip_presentation(int skip)
{
	sSkipPresentation = skip != 0;
}

int pc_netplay_present_skip_presentation(void)
{
	return sSkipPresentation ? 1 : 0;
}

int pc_netplay_present_two_pass_active(void)
{
#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST)
	if (!pc_netplay_deterministic()) {
		return 0;
	}
	return 1;
#else
	return 0;
#endif
}

int pc_netplay_present_sim_side(void)
{
#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST)
	if (pc_netplay_present_two_pass_active()) {
		return pc_render_is_authoritative() ? 1 : 0;
	}
	return 1;
#else
	return 1;
#endif
}

int pc_netplay_present_sim_pass(void)
{
#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST)
	return (pc_netplay_present_two_pass_active() && pc_render_is_authoritative()) ? 1 : 0;
#else
	return 0;
#endif
}

void pc_netplay_present_set_null_gx(int on)
{
	sNullGx = on != 0;
}

int pc_netplay_present_null_active(void)
{
	return sNullGx ? 1 : 0;
}

unsigned long long pc_netplay_present_null_gl_calls(void)
{
	return sNullReal;
}

unsigned long long pc_netplay_present_null_attempted(void)
{
	return sNullAttempted;
}

void pc_netplay_present_note_attempt(void)
{
	++sNullAttempted;
}

void pc_netplay_present_note_real(void)
{
	++sNullReal;
}

void pc_netplay_present_reset_counters(void)
{
	sNullReal = 0;
	sNullAttempted = 0;
	sSavedShapes = 0;
}

static int sLocalPlayerDefault = 0;

int pc_netplay_present_local_player(void)
{
	if (!sLocalPlayerInit) {
		sLocalPlayerInit = true;
		const char* v = std::getenv("PIKMIN_NETPLAY_LOCAL_PLAYER");
		if (v && (v[0] == '0' || v[0] == '1') && v[1] == '\0')
			sLocalPlayerCached = v[0] - '0';
		else
			sLocalPlayerCached = sLocalPlayerDefault;
	}
	return sLocalPlayerCached;
}

void pc_netplay_present_set_local_player_default(int player)
{
	sLocalPlayerDefault = (player == 1) ? 1 : 0;
	sLocalPlayerInit    = false;
}

void pc_netplay_present_reset_local_player(void)
{
	sLocalPlayerInit = false;
	sLocalPlayerCached = 0;
	sLocalPlayerDefault = 0;
}

unsigned long long pc_netplay_present_saved_shapes(void)
{
	return sSavedShapes;
}

} // extern "C"

#if defined(PIKI_PC_PORT) && !defined(PC_NETPLAY_PRESENT_HOST) && defined(__cplusplus)
Camera* pc_netplay_present_sim_camera(void)
{
	if (!sSimCamera) {
		sSimCamera = new Camera();
	}
	return sSimCamera;
}

void pc_netplay_present_begin_authoritative(Graphics& gfx)
{
	// Route pose math through identity: lookAt * world * joint becomes
	// world-space. The SimCamera carries a fixed session-constant projection
	// (16:9, gameplay default FOV/clip); it never reads the live camera,
	// whose FOV follows zoom and whose near clip is 3 in first person versus
	// 100 otherwise. Always installed, even when gfx.mCamera is still null
	// (first stage frame).
	Camera* sim = pc_netplay_present_sim_camera();
	sSavedGfx = &gfx;
	sSavedCamera = gfx.mCamera;
	sim->mFov = 60.0f;
	sim->mNear = 100.0f;
	sim->mFar = 10000.0f;
	sim->mAspectRatio = 16.0f / 9.0f;
	// Fixed CPU-side perspective (row-major transpose of gluPerspective
	// with glScalef(1,1,1)), matching OGLGraphics::setPerspective's output
	// layout without touching GL.
	{
		const float fovRad = sim->mFov * 3.141592653589793f / 180.0f;
		const float f = 1.0f / tanf(fovRad * 0.5f);
		const float zn = sim->mNear > 0.0f ? sim->mNear : 1.0f;
		const float zf = sim->mFar > zn ? sim->mFar : zn + 1000.0f;
		sim->mPerspectiveMatrix.makeIdentity();
		sim->mPerspectiveMatrix.mMtx[0][0] = f / sim->mAspectRatio;
		sim->mPerspectiveMatrix.mMtx[1][1] = f;
		sim->mPerspectiveMatrix.mMtx[2][2] = (zf + zn) / (zn - zf);
		sim->mPerspectiveMatrix.mMtx[2][3] = (2.0f * zf * zn) / (zn - zf);
		sim->mPerspectiveMatrix.mMtx[3][2] = -1.0f;
		sim->mPerspectiveMatrix.mMtx[3][3] = 0.0f;
	}
	sim->mProjectionMatrix = sim->mPerspectiveMatrix;
	gfx.mCamera = sim;
	sim->mLookAtMtx.makeIdentity();
	sim->mInverseLookAtMtx.makeIdentity();
	pc_netplay_present_set_null_gx(1);
}

void pc_netplay_present_end_authoritative(Graphics& gfx)
{
	pc_netplay_present_set_null_gx(0);
	// Restore the pre-pass camera even when it was null (first stage frame).
	if (sSavedGfx == &gfx) {
		gfx.mCamera = sSavedCamera;
	}
	sSavedGfx = nullptr;
	sSavedCamera = nullptr;
}

void pc_netplay_present_begin_presentation(Graphics& gfx)
{
	(void)gfx;
	// A previous presentation that never reached the driver's restore (for
	// example section construction during a soft-reset idle, which runs as
	// presentation) may have left shapes pointing into the present pool.
	// Restore those before dropping the list; otherwise they keep pointers
	// the next presentation overwrites with camera-space data.
	if (!sSavedPtrs.empty()) {
		pc_netplay_present_restore_all_shapes();
	}
	if (sSavedPtrs.capacity() == 0) {
		sSavedPtrs.reserve(256);
	}
	sSavedPtrs.clear();
	sSavedShapes = 0;
	// Presentation matrix pool is reset in Graphics::resetPresentBuffer by
	// the driver (needs gfx). Kept here for symmetry; actual reset below.
}

void pc_netplay_present_end_presentation(Graphics& gfx)
{
	(void)gfx;
	// Actual pointer restore runs in shapeBase.cpp
	// (pc_netplay_present_restore_all_shapes) so it can write
	// BaseShape::mAnimMatrices directly. The sim pool was never touched
	// (presentation allocates from the separate present pool), so restoring
	// pointers restores the exact authoritative matrix state.
}

bool pc_netplay_present_save_shape_ptr(void* shape, void* savedPtr)
{
	if (!shape) {
		return false;
	}
	for (const auto& kv : sSavedPtrs) {
		if (kv.first == shape) {
			return false;
		}
	}
	if (sSavedPtrs.capacity() == 0) {
		sSavedPtrs.reserve(256);
	}
	sSavedPtrs.emplace_back(shape, savedPtr);
	++sSavedShapes;
	return true;
}

size_t pc_netplay_present_saved_count(void)
{
	return sSavedPtrs.size();
}

void* pc_netplay_present_saved_shape_at(size_t i, void** outSaved)
{
	if (i < sSavedPtrs.size()) {
		if (outSaved) {
			*outSaved = sSavedPtrs[i].second;
		}
		return sSavedPtrs[i].first;
	}
	if (outSaved) {
		*outSaved = nullptr;
	}
	return nullptr;
}

void pc_netplay_present_clear_saved(void)
{
	sSavedPtrs.clear();
}
#endif
