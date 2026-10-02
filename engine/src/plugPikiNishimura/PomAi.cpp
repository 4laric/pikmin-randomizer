#include "pc_p2_candypop.h"
#include "pc_p2_cave_bud_actor.h"
#include "pc_p2_purple.h"
#include "pc_p2_white.h"
#include "DebugLog.h"
#include "EffectMgr.h"
#include "Interactions.h"
#include "ItemMgr.h"
#include "NaviMgr.h"
#include "NsMath.h"
#include "Piki.h"
#include "PikiHeadItem.h"
#include "PikiState.h"
#include "PlayerState.h"
#include "Pom.h"
#include "RumbleMgr.h"
#include "SoundMgr.h"
#include "Stickers.h"

static u32 pomSE[] = {
	SE_KING_CHEEK, SE_PONGASHI_CLOSE, SE_PONGASHI_EAT, SE_PONGASHI_SHOT, SE_PONGASHI_DEAD, SE_PONGASHI_TOUCH,
};

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F0
 */
DEFINE_PRINT("PomAi");

/**
 * @todo: Documentation
 */
PomAi::PomAi(Pom* pom)
{
	mPom              = pom;
	mOpenStarCallBack = new PomGenOpenStarCallBack;
}

/**
 * @todo: Documentation
 */
void PomAi::initAI(Pom* pom)
{
	mPom = pom;
	if (C_POM_PARM(mPom, mOpenOnInteractionOnly) < 2) {
		mPom->setCurrentState(2);
		mPom->setNextState(2);
		mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Type1, this));
		mPom->enableStick();
		mPom->mAnimator.setCounter(28.0f);
	} else {
		mPom->setCurrentState(1);
		mPom->setNextState(1);
		mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Wait1, this));
		mPom->disableStick();
	}

	mPom->setAnimTimer(30.0f);
	mHasCollided        = true;
	mPlaySound          = false;
	mIsOpening          = false;
	mPrevStickPikiCount = 0;
	mReleasedSeedCount  = 0;

	// splitting this monstrosity up into temps would be better. however, that destroys the stack :')
	mMaxSeedCount  = C_POM_PARM(mPom, mMinCycles)
	               + NsMathI::getRand(NsLibMath<int>::abs(C_POM_PARM(mPom, mMaxCycles) - C_POM_PARM(mPom, mMinCycles) + 1));
	mCurrentDeform = 0.0f;
	mDeformAmount  = 0.0f;
    if(pc_p2_violet(mPom)) {
        mMaxSeedCount=5; // Violet counts non-Purple inputs; same-color slots refund.
    }
    if(int candypopBudget=pc_p2_cave_bud_body_profile() ? 0 : pc_p2_candypop_budget(mPom)) {
        // Lane-23 real-engine colour bud: source ip01 budget, fp01 close wait,
        // any-colour entry, and own-colour refund handled in createPikiHead.
        PomProp* props=static_cast<PomProp*>(mPom->mProps);
        props->mPomProps.mMaxPikiPerCycle.mValue=candypopBudget;
        props->mPomProps.mCloseWaitTime.mValue=1.f;
        props->mPomProps.mOpenOnInteractionOnly.mValue=0;
        props->mPomProps.mDoKillSameColorPiki.mValue=FALSE;
        mMaxSeedCount=candypopBudget;
    }
}

/**
 * @todo: Documentation
 */
void PomAi::animationKeyUpdated(immut PaniAnimKeyEvent& event)
{
	switch (event.mEventType) {
	case KEY_Action0:
	{
		keyAction0();
		break;
	}
	case KEY_Action1:
	{
		keyAction1();
		break;
	}
	case KEY_LoopEnd:
	{
		keyLoopEnd();
		break;
	}
	case KEY_Finished:
	{
		keyFinished();
		break;
	}
	case KEY_PlaySound:
	{
		playSound(event.mValue);
		break;
	}
	}
}

/**
 * @todo: Documentation
 */
void PomAi::keyAction0()
{
	if (mPom->getCurrentState() == 5) {
		createPikiHead();
	} else if (mPom->getCurrentState() == 2) {
		mPom->enableStick();
	}
}

/**
 * @todo: Documentation
 */
void PomAi::keyAction1()
{
	if (mPom->getCurrentState() == 2) {
		mIsOpening = false;
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000004
 */
void PomAi::keyAction2()
{
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000004
 */
void PomAi::keyAction3()
{
}

/**
 * @todo: Documentation
 */
void PomAi::keyLoopEnd()
{
	mPom->addLoopCounter(1);
}

/**
 * @todo: Documentation
 */
void PomAi::keyFinished()
{
	if (mPom->getCurrentState() == 0) {
		mPom->setIsAlive(false);
		mPom->setIsAtari(false);
		effectMgr->create(EffectMgr::EFF_Teki_DeathSmokeS, mPom->mSRT.t, nullptr, nullptr);
		effectMgr->create(EffectMgr::EFF_Teki_DeathGlowS, mPom->mSRT.t, nullptr, nullptr);
		effectMgr->create(EffectMgr::EFF_Teki_DeathWaveS, mPom->mSRT.t, nullptr, nullptr);

		playSound(0);
		if(!pc_p2_violet(mPom) && !pc_p2_ivory(mPom))mPom->createPellet(mPom->mSRT.t, 150.0f, true);
	}

	mPom->setMotionFinish(1);
}

/**
 * @todo: Documentation
 */
void PomAi::playSound(int pomSoundID)
{
	if (mPom->mSeContext) {
		mPom->mSeContext->playSound(pomSE[pomSoundID]);
	}
}

/**
 * @todo: Documentation
 */
void PomAi::killCallBackEffect(bool forceFinish)
{
	PomGenOpenStarCallBack* cb = mOpenStarCallBack;
	effectMgr->kill(cb, nullptr, forceFinish);
}

/**
 * @todo: Documentation
 */
void PomAi::collidePetal(Creature* collider)
{
	if (mHasCollided) {
		return;
	}

	if (mPom->getCurrentState() == 2 && mPom->mAnimator.mAnimationCounter > 27.0f && collider->mVelocity.length() > 75.0f) {
		setCollideSound(collider);
	}

	if (mPom->getMotionFinish() && mPom->getCurrentState() == 3 && collider->mVelocity.length() > 75.0f) {
		setCollideSound(collider);
	}
}

/**
 * @todo: Documentation
 */
void PomAi::setCollideSound(Creature* collider)
{
	mHasCollided = true;

	// don't trigger collision sound for pikis flying into flower
	if (collider->mObjType == OBJTYPE_Piki) {
		if (static_cast<Piki*>(collider)->getState() != PIKISTATE_Flying) {
			mPlaySound = true;
		}
	} else {
		mPlaySound = true;
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000044
 */
void PomAi::setEveryFrame()
{
	checkSwayAndScale();
	calcSwayAndScale();
	setInitPosition();
	resultFlagOn();
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000A8
 */
void PomAi::checkSwayAndScale()
{
	int stickPikiCount = mPom->getStickPikiCount();
	if (stickPikiCount > mPrevStickPikiCount) {
		mDeformAmount -= C_POM_PARM(mPom, mSquashAmount);
		effectMgr->create(EffectMgr::EFF_CloudOfDust_1, mPom->mSRT.t, nullptr, nullptr);
		playSound(5);
		resultFlagSeen();
	}

	mPrevStickPikiCount = stickPikiCount;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000084
 */
void PomAi::calcSwayAndScale()
{
	mCurrentDeform += mDeformAmount;
	mPom->mSRT.s.x = 1.0f - mCurrentDeform;
	mPom->mSRT.s.y = 1.0f + mCurrentDeform;
	mPom->mSRT.s.z = 1.0f - mCurrentDeform;

	mDeformAmount *= C_POM_PARM(mPom, mSquashPersistence);

	mDeformAmount += C_POM_PARM(mPom, mSquashMultiplier) * -mCurrentDeform;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00002C
 */
void PomAi::setInitPosition()
{
	Vector3f* pos  = mPom->getInitPosition();
	mPom->mSRT.t.x = pos->x;
	mPom->mSRT.t.y = pos->y;
	mPom->mSRT.t.z = pos->z;
}

/**
 * @todo: Documentation
 */
int PomAi::killStickPiki()
{
	int seedCount = 0;
	Stickers stickers(mPom);

	Iterator iter(&stickers);
	CI_LOOP(iter)
	{
		Creature* stuck = *iter;
		if (stuck && stuck->isAlive() && stuck->mObjType == OBJTYPE_Piki) {
			Piki* piki = static_cast<Piki*>(*iter);
			if (!pc_p2_violet(mPom) && C_POM_PARM(mPom, mDoKillSameColorPiki) && piki->mColor == mPom->mColor) {
				piki->kill(false);
			} else {
				piki->setEraseKill();
				piki->kill(false);
				seedCount++;
			}

			iter.dec();
		}
	}

	return seedCount;
}

/**
 * @todo: Documentation
 */
void PomAi::createPikiHead()
{
    if (pc_p2_cave_bud_body_profile()) {
        const int species = pc_p2_cave_bud_body_species(mPom);
        const int remaining = pc_p2_cave_bud_body_remaining(mPom);
        if (species == 3) pc_p2_convert_violet(mPom,remaining);
        else if (species == 4) pc_p2_convert_ivory(mPom,remaining);
        // Never fall through to a legacy conversion on an unbound body.
        if (species == 3 || species == 4) playSound(3);
        return;
    }
    // Lane-23 real-engine colour Candypop takes precedence when this Pom is a
    // sidecar-bound BluePom/RedPom/YellowPom; returns -1 for every other Pom.
    int candypopUsed=pc_p2_convert_candypop(mPom,mMaxSeedCount-mReleasedSeedCount);
    if(candypopUsed>=0){mReleasedSeedCount+=candypopUsed;playSound(3);return;}
    // Retail Pom ProperParms ip01=5 counts non-refunded lifetime slots.
    // Binding is queried here: Generator attaches mGenerator after Pom::init.
    int whiteConverted=pc_p2_convert_ivory(mPom,5-mReleasedSeedCount);
    if(whiteConverted>=0){mReleasedSeedCount+=whiteConverted;playSound(3);return;}
    int converted=pc_p2_convert_violet(mPom,5-mReleasedSeedCount);
    if(converted>=0){mReleasedSeedCount+=converted;playSound(3);return;}
	int seedCount = killStickPiki();
	Navi* player  = naviMgr->getNearestNavi(mPom->mSRT.t);
	f32 baseAngle = atan2f(mPom->mSRT.t.x - player->mSRT.t.x, mPom->mSRT.t.z - player->mSRT.t.z);

	f32 spreadAngle = PI * (C_POM_PARM(mPom, mDischargeAngle) / 360.0f);
	f32 minAngle    = baseAngle - spreadAngle;
	f32 angleRange  = 2.0f * spreadAngle;

	for (int i = 0; i < seedCount; i++) {
		PikiHeadItem* sprout = static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));
		if (sprout) {
			Vector3f spawnPos = mPom->mSRT.t;
			spawnPos.y += 50.0f;
			sprout->init(spawnPos);

			sprout->setColor(mPom->mColor);

			f32 randAngle = NsMathF::getRand(angleRange) + minAngle;
			sprout->mVelocity.set(200.0f * sinf(randAngle), 800.0f, 200.0f * cosf(randAngle));

			sprout->startAI(0);
			C_SAI(sprout)->start(sprout, PikiHeadAI::PIKIHEAD_Flying);
		}
	}

	rumbleMgr->start(RUMBLE_Unk10, 0, mPom->mSRT.t);
	playSound(3);
	mReleasedSeedCount++;
	STACK_PAD_VAR(1);
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00006C
 */
void PomAi::emitPomOpenEffect(u32 collPartID)
{
	CollPart* part               = mPom->mCollInfo->getSphere(collPartID);
	zen::particleGenerator* ptcl = effectMgr->create(EffectMgr::EFF_SD_Sparkle, mPom->mSRT.t, mOpenStarCallBack, nullptr);
	if (ptcl) {
		ptcl->setEmitPosPtr(&part->mCentre);
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000198
 */
void PomAi::createPomOpenEffect()
{
	mIsOpening = true;
	mOpenStarCallBack->set(&mIsOpening);
	emitPomOpenEffect('pom1');
	emitPomOpenEffect('pom2');
	emitPomOpenEffect('pom3');
	emitPomOpenEffect('pom4');
	emitPomOpenEffect('pom5');
}

/**
 * @todo: Documentation
 */
void PomAi::calcPetalStickers()
{
	if (mPom->mIsPikiOrPlayerTouching) {
		mPom->addWalkTimer(gsys->getFrameTime());
	}

	// if swallow setting is enabled
	if (C_POM_PARM(mPom, mStickOrSwallow)) {
		CollPart* slotPart = mPom->mCollInfo->getSphere('slot');
		Stickers stuckList(mPom);
		Iterator iter(&stuckList);
		CI_LOOP(iter)
		{
			Creature* stuck = *iter;
			if (stuck && stuck->isAlive() && !stuck->isStickToMouth()) {
				CollPart* childPart = slotPart->getChildAt(0);
				InteractSwallow swallow(mPom, childPart, 0);
				stuck->stimulate(swallow);
			}
		}
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00003C
 */
void PomAi::resultFlagOn()
{
	if (mPom->insideAndInSearch()) {
		playerState->mResultFlags.setOn(zen::RESFLAG_Pom);
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00002C
 */
void PomAi::resultFlagSeen()
{
	playerState->mResultFlags.setSeen(zen::RESFLAG_Pom);
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 00000C
 */
bool PomAi::isMotionFinishTransit()
{
	return mPom->getMotionFinish();
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000020
 */
bool PomAi::deadTransit()
{
    if (pc_p2_cave_bud_body_profile())
        return pc_p2_cave_bud_body_species(mPom) >= 0 && pc_p2_cave_bud_body_remaining(mPom) == 0;
	return mReleasedSeedCount >= ((pc_p2_violet(mPom) || pc_p2_ivory(mPom)) ? 5 : mMaxSeedCount);
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000024
 */
bool PomAi::petalOpenTransit()
{
	if (C_POM_PARM(mPom, mOpenOnInteractionOnly)) {
		return mPom->mIsPikiOrPlayerTouching;
	}

	return true;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000008
 */
bool PomAi::petalShakeTransit()
{
	return mHasCollided;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000070
 */
bool PomAi::petalCloseTransit()
{
	f32 closeWait = pc_p2_cave_bud_body_profile() ? 1.0f : (pc_p2_ivory(mPom) ? 1.0f : (pc_p2_violet(mPom) ? 5.0f : C_POM_PARM(mPom, mCloseWaitTime)));
    const int capacity = (pc_p2_cave_bud_body_profile() || pc_p2_violet(mPom) || pc_p2_ivory(mPom)) ? 5 : C_POM_PARM(mPom, mMaxPikiPerCycle);
#if defined(PIKI_PC_PORT)
	// Retail waits 30 seconds; keep short/custom and disabled timers intact.
	if (closeWait > 5.0f) closeWait = 5.0f;
#endif
	if (capacity != 0) {
		if (mPrevStickPikiCount >= capacity) {
			return true;
		}
		if (closeWait > 0.0f && mPom->getWalkTimer() > closeWait) {
			return true;
		}
	} else if (mPom->getWalkTimer() > closeWait) {
		return true;
	}

	return false;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 0001BC
 */
bool PomAi::dischargeTransit()
{
	Stickers stuckList(mPom);
	Iterator iter(&stuckList);
	CI_LOOP(iter)
	{
		Creature* stuck = *iter;
		if (stuck->isAlive() && stuck->mObjType == OBJTYPE_Piki) {
			Piki* stuckPiki = static_cast<Piki*>(*iter);
			if (pc_p2_violet(mPom) || pc_p2_ivory(mPom) || !C_POM_PARM(mPom, mDoKillSameColorPiki) || stuckPiki->mColor != mPom->mColor) {
				return true;
			}
		}
	}
	return false;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000068
 */
void PomAi::initDie(int nextState)
{
	mPom->setNextState(nextState);
	mPom->setMotionFinish(false);
	mPom->setAttackTimer(0.0f);
	mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Dead, this));
}

/**
 * @todo: Documentation
 */
void PomAi::initWait(int nextState)
{
	mPom->setNextState(nextState);
	mPom->setMotionFinish(false);
	mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Wait1, this));

	Stickers stuckList(mPom);
	Iterator iter(&stuckList);
	CI_LOOP(iter)
	{
		Creature* stuck = *iter;
		if (stuck && stuck->isAlive() && stuck->mObjType == OBJTYPE_Piki) {
			Piki* stuckPiki = static_cast<Piki*>(*iter);
			if (stuckPiki->mColor == mPom->mColor) {
				stuck->kill(false);
				iter.dec();
			}
		}
	}
	mPom->mIsPikiOrPlayerTouching = false;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 0001E4
 */
void PomAi::initPetalOpen(int nextState)
{
	mPom->setNextState(nextState);
	mPom->setMotionFinish(false);
	mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Type1, this));
	createPomOpenEffect();
	mPom->setWalkTimer(0.0f);
	mHasCollided = false;
	mPlaySound   = false;
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000098
 */
void PomAi::initPetalShake(int nextState)
{
	mPom->setNextState(nextState);
	mPom->setMotionFinish(false);
	mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Type4, this));
	mHasCollided = false;
	if (mPlaySound) {
		mPlaySound = false;
		playSound(0);
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000078
 */
void PomAi::initPetalClose(int nextState)
{
	mPom->setNextState(nextState);
	mPom->setMotionFinish(false);
	mPom->setLoopCounter(0);
	mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Type2, this));
	mPom->disableStick();
	mIsOpening = false;
}

/**
 * @todo: Documentation
 */
void PomAi::initDischarge(int nextState)
{
	mPom->setNextState(nextState);
	mPom->setMotionFinish(false);
	mPom->mAnimator.startMotion(PaniMotionInfo(TekiMotion::Type3, this));

	CollPart* slotPart = mPom->mCollInfo->getSphere('slot');
	Stickers stuckList(mPom);
	Iterator iter(&stuckList);
	CI_LOOP(iter)
	{
		Creature* stuck = *iter;
		if (stuck && stuck->isAlive()) {
			CollPart* childPart = slotPart->getChildAt(0);
			InteractSwallow swallow(mPom, childPart, 0);
			stuck->stimulate(swallow);
		}
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000070
 */
void PomAi::dieState()
{
	if (mPom->getMotionFinish()) {
		if (mPom->getAttackTimer() > 1.0f) {
            const bool bodyProfile = pc_p2_cave_bud_body_profile();
            if (bodyProfile) pc_p2_cave_bud_body_retire(mPom);
			mPom->doKill();
            if (bodyProfile) return; // The manager has returned this body to its free pool.
		}
		mPom->addAttackTimer(gsys->getFrameTime());
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000004
 */
void PomAi::waitState()
{
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000020
 */
void PomAi::openState()
{
	calcPetalStickers();
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000020
 */
void PomAi::shakeState()
{
	calcPetalStickers();
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000060
 */
void PomAi::closeState()
{
	if (mPom->getLoopCounter() >= C_POM_PARM(mPom, mDoAnimLoopWhenClosed)) {
		mPom->mAnimator.finishMotion(PaniMotionInfo(PANI_NO_MOTION, this));
	}
}

/**
 * @todo: Documentation
 * @note UNUSED Size: 000004
 */
void PomAi::dischargeState()
{
}

/**
 * @todo: Documentation
 */
void PomAi::update()
{
    // Bodies exist before generator attachment and scene activation. They may
    // not run legacy capture/death/output while the explicit profile is fenced.
    if (pc_p2_cave_bud_body_profile() && pc_p2_cave_bud_body_species(mPom) < 0) return;
	setEveryFrame();
	switch (mPom->getCurrentState()) {
	case 0:
	{
		dieState();
		break;
	}
	case 1:
	{
		waitState();
		if (petalOpenTransit()) {
			initPetalOpen(2);
		}
		break;
	}
	case 2:
	{
		openState();
		if (petalCloseTransit()) {
			initPetalClose(4);
		} else if (petalShakeTransit()) {
			initPetalShake(3);
		}
		break;
	}
	case 3:
	{
		shakeState();
		if (petalCloseTransit()) {
			initPetalClose(4);
		} else if (petalShakeTransit()) {
			initPetalShake(3);
		}
		break;
	}
	case 4:
	{
		closeState();
		if (isMotionFinishTransit()) {
			if (dischargeTransit()) {
				initDischarge(5);
			} else {
				initWait(1);
			}
		}
		break;
	}
	case 5:
	{
		dischargeState();
		if (isMotionFinishTransit()) {
			if (deadTransit()) {
				initDie(0);
			} else {
				initWait(1);
			}
		}
		break;
	}
	}
}
