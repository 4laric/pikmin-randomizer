#include "DualCreature.h"
#if defined(PIKI_PC_PORT)
#include "pc_p2_dangomushi.h"
#include "netplay/pc_netplay_policy.h"
#include "netplay/pc_netplay_present.h"
#include "timing/pc_render_phase.h"
#else
#define pc_netplay_sim_visible(x) (x)
#endif
#include "DebugLog.h"
#include "Graphics.h"
#include "ItemMgr.h"
#include "Kontroller.h"
#include "MapMgr.h"
#include "NaviMgr.h"

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F0
 */
DEFINE_PRINT(nullptr);

/**
 * @todo: Documentation
 */
DualCreature::DualCreature()
{
	mIsCollisionInitialised = false;
	setCreatureFlag(CF_Unk1 | CF_DisableAutoFaceDir);
	mPrevAngularVelocity.set(0.0f, 0.0f, 0.0f);
	mAngularMomentum.set(0.0f, 0.0f, 0.0f);
	useRealDynamics();
	setDynamicsSimpleFixed(false);
}

/**
 * @todo: Documentation
 */
void DualCreature::doKill()
{
	DynCreature::doKill();
	mIsCollisionInitialised = false;
}

/**
 * @todo: Documentation
 */
bool DualCreature::isFrontFace()
{
	if (mIsRealDynamics) {
		Vector3f yVec;
		mRotationQuat.genVectorY(yVec);
		return yVec.y > 0.5f;
	}

	return true;
}

/**
 * @todo: Documentation
 */
f32 DualCreature::getY()
{
	if (mIsRealDynamics) {
		Vector3f yVec;
		mRotationQuat.genVectorY(yVec);
		return yVec.y;
	}

	return 1.0f;
}

/**
 * @todo: Documentation
 */
bool DualCreature::onGround()
{
	if (mIsRealDynamics) {
		if (isCreatureFlag(CF_IsOnGround)) {
			return true;
		}
		if (getGroundFlag()) {
			return true;
		}

		return false;
	}

	return isCreatureFlag(CF_IsOnGround) != 0;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000078
 */
void DualCreature::createCollisions(Graphics& gfx)
{
	if (!mIsCollisionInitialised) {
		releaseAllParticles();
		mIsCollisionInitialised = true;
		mMass                   = 0.0f;
		doCreateColls(gfx);
		initialiseSystem();
	}
}

/**
 * @todo: Documentation
 */
void DualCreature::useRealDynamics()
{
	if (!mIsDynamicsSimpleFixed) {
		_43E            = true;
		mIsRealDynamics = true;
		mRotationQuat.fromEuler(mSRT.r);
	} else {
		useSimpleDynamics();
	}
}

/**
 * @todo: Documentation
 */
void DualCreature::useSimpleDynamics()
{
	_43E            = true;
	mIsRealDynamics = false;
	mPrevAngularVelocity.set(0.0f, 0.0f, 0.0f);
	mAngularMomentum.set(0.0f, 0.0f, 0.0f);
}

/**
 * @todo: Documentation
 */
void DualCreature::rotateY(f32 rotY)
{
	if (mIsRealDynamics) {
		Quat q1;
		q1.fromEuler(Vector3f(0.0f, rotY, 0.0f));
		q1.multiply(mRotationQuat);
		mRotationQuat = q1;
		mRotationQuat.normalise();
	} else {
		mFaceDirection = roundAng(mFaceDirection + rotY);
		mSRT.r.set(0.0f, mFaceDirection, 0.0f);
	}
}

/**
 * @todo: Documentation
 */
void DualCreature::update()
{
	if (mIsRealDynamics) {
		DynCreature::update();
	} else {
		Creature::update();
	}
}

/**
 * @todo: Documentation
 */
void DualCreature::refresh(Graphics& gfx)
{
	Matrix4f mtx;
#if defined(PIKI_PC_PORT)
	// M2b: dynamics mode, world matrix and collisions are sim (authoritative
	// only). Presentation re-renders with the stored mode/matrix and the
	// local camera. Culling/policy reads stay authoritative-consistent.
	f32 p2DrawCullRadius = 2.0f * getBoundingSphereRadius();
	const f32 p2CullRadius = pc_p2_dangomushi_cull_radius(this);
	if (p2CullRadius > p2DrawCullRadius) p2DrawCullRadius = p2CullRadius;
	const bool authDual = !pc_netplay_present_two_pass_active() || pc_render_is_authoritative();
	if (authDual) {
#endif
#if defined(VERSION_PIKIDEMO) || defined(VERSION_GPIJ01_01)
	// I don't enjoy splitting this difference in two, but syntax highlighting really hates extra opening braces.
#else
#if defined(PIKI_PC_PORT)
	// Deterministic visibility policy retains the actual P2 body bounds.
	bool isPointVisible = pc_netplay_sim_visible(gfx.mCamera->isPointVisible(mSRT.t, p2DrawCullRadius));
#else
	bool isPointVisible = gfx.mCamera->isPointVisible(mSRT.t, 2.0f * getBoundingSphereRadius());
#endif

	if (isPointVisible) {
		disableAICulling();
	} else {
		enableAICulling();
	}
#endif

	if (!_43E) {
#if defined(VERSION_PIKIDEMO) || defined(VERSION_GPIJ01_01)
		if (!mIsDynamicsSimpleFixed && pc_netplay_sim_visible(gfx.mCamera->isPointVisible(mSRT.t, 2.0f * getBoundingSphereRadius())))
#else
		if (!mIsDynamicsSimpleFixed && isPointVisible)
#endif
		{
			if (!mIsRealDynamics) {
				useRealDynamics();
			}
		} else if (mIsRealDynamics) {
			useSimpleDynamics();
		}
	}

	if (mIsRealDynamics) {
		mWorldMtx.makeVQS(mSRT.t, mRotationQuat, mSRT.s);
	} else {
		mWorldMtx.makeSRT(mSRT.s, mSRT.r, mSRT.t);
	}

#if defined(PIKI_PC_PORT)
	}
#endif
	gfx.mCamera->mLookAtMtx.multiplyTo(mWorldMtx, mtx);
#if defined(PIKI_PC_PORT)
	// M2b fix (review M5, resolves m2a open item m1): the presentation pass
	// submits only what the real local frustum sees, from the stored
	// authoritative mode/matrix. AI flags and dynamics above stay
	// authoritative.
	const bool m2bDualCulled = pc_netplay_present_two_pass_active() && !pc_render_is_authoritative()
	                        && !gfx.mCamera->isPointVisible(mSRT.t, p2DrawCullRadius);
	if (!m2bDualCulled) {
		doRender(gfx, mtx);
	}
#else
	doRender(gfx, mtx);
#endif
#if defined(PIKI_PC_PORT)
	// M2b: collision creation is sim-only.
	if (authDual && mIsRealDynamics) {
#else
	if (mIsRealDynamics) {
#endif
		createCollisions(gfx);
	}

	_43E = false;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000140
 */
PelCreature::PelCreature(int objType, ItemShapeObject* shape, CreatureProp* props, MapMgr* mgr)
    : mItemCollInfo(0)
{
	mObjType   = (EObjType)objType;
	mItemShape = shape;
	mProps     = props;
	mapMgr     = mgr;
}

/**
 * @todo: Documentation
 */
void PelCreature::init(immut Vector3f& pos)
{
	Creature::init(pos);
	if (mItemShape) {
		mItemAnimator.init(&mItemShape->mAnimContext, mItemShape->mAnimMgr, itemMgr->mItemMotionTable);
	}
}

/**
 * @todo: Documentation
 */
f32 PelCreature::getiMass()
{
	return 10.0f;
}

/**
 * @todo: Documentation
 */
bool PelCreature::isAlive()
{
	return true;
}

/**
 * @todo: Documentation
 */
void PelCreature::startAI(int)
{
	mCollInfo = &mItemCollInfo;
	mCollInfo->initInfo(mItemShape->mShape, mItemParts, mPartIDs);
	mItemAnimator.startMotion(PaniMotionInfo(0));
}

/**
 * @todo: Documentation
 */
void PelCreature::doRender(Graphics& gfx, Matrix4f& mtx)
{
	Navi* navi = naviMgr->getNavi(); // debug: solo P1
	if (navi->mKontroller->keyClick(KBBTN_B)) {
		mVelocity.y += 400.0f;
		if (mIsRealDynamics) {
			useSimpleDynamics();
		} else {
			mSRT.r.set(PI / 10.0f, 0.0f, 0.0f);
			useRealDynamics();
		}
	}

	gfx.setLighting(true, nullptr);
	gfx.useMatrix(Matrix4f::ident, 0);
	mItemAnimator.updateContext();
	mItemShape->mShape->updateAnim(gfx, mtx, nullptr, this);
	mItemShape->mShape->drawshape(gfx, *gfx.mCamera, nullptr);
	mCollInfo->updateInfo(gfx, false);
}

/**
 * @todo: Documentation
 */
void PelCreature::doCreateColls(Graphics& gfx)
{
	f32 size          = getCentreSize();
	f32 firstPtclSize = 4.0f;
	for (int i = 0; i < 4; i++) {
		f32 angle = HALF_PI * i;
		Vector3f particlePos(size * cosf(angle), 0.0f, size * sinf(angle));
		addParticle(firstPtclSize, particlePos);

		angle = HALF_PI * i + QUARTER_PI;
		particlePos.set(size * cosf(angle), 0.0f, size * sinf(angle));
		particlePos.y += 25.0f;
		addParticle(2.0f, particlePos);
	}
}
