#include "PikiAI.h"
#include <cassert>
#include <cstdio>
RouteMgr* routeMgr=nullptr;
System systemStub;System* gsys=&systemStub;
static void ready(ActRescue& rescue,Piki& victim) {
 rescue.init(&victim);rescue.initRescue();rescue.animationKeyUpdated({KEY_Action0});
}
int main() {
 Piki blue,red;ActRescue rescue(&blue);
 // Reusing an action cannot carry the prior survivor/animation state forward.
 rescue.mTargetSurviveTimer=65535;rescue.mGotAnimationAction=true;
 rescue.mAnimationFinished=true;rescue.mThrowReady=true;
 rescue.init(&red);
 assert(rescue.mTargetSurviveTimer==0&&!rescue.mGotAnimationAction
        &&!rescue.mAnimationFinished&&!rescue.mThrowReady);
 ready(rescue,red);assert(rescue.exec()==ACTOUT_Fail);
 assert(red.state==PIKISTATE_Drown&&red.fsm.calls==0);
 assert(red.mVelocity.length()==0&&red.mSRT.t.length()==0);
 RouteMgr manager;routeMgr=&manager;
 ready(rescue,red);assert(rescue.exec()==ACTOUT_Fail);
 assert(manager.queries==1&&manager.dry&&red.fsm.calls==0);
 WayPoint dry;dry.mPosition={50,0,0};manager.waypoint=&dry;
 ready(rescue,red);assert(rescue.exec()==ACTOUT_Continue);
 assert(rescue.mState==ActRescue::STATE_Go&&red.state==PIKISTATE_WaterHanged&&red.fsm.calls==1);
 assert(std::fabs(rescue.mRescueTargetPosition.x-42)<.001f&&rescue.mRescueTargetPosition.y==30);
 assert(rescue.exec()==ACTOUT_Continue&&rescue.mState==ActRescue::STATE_Throw);
 rescue.mGotAnimationAction=true;rescue.mThrowReady=false;
 assert(rescue.exec()==ACTOUT_Continue&&red.state==PIKISTATE_Flying&&red.fsm.calls==2);
 assert(red.mVelocity.x==1&&red.mVelocity.y==2&&red.mVelocity.z==3);
 rescue.mAnimationFinished=true;assert(rescue.exec()==ACTOUT_Success);
 rescue.init(nullptr);assert(rescue.exec()==ACTOUT_Fail);
 Creature object;rescue.init(&object);assert(rescue.exec()==ACTOUT_Fail);
 red.alive=false;rescue.init(&red);assert(rescue.exec()==ACTOUT_Fail);
 red.alive=true;red.state=PIKISTATE_Normal;rescue.init(&red);
 for(int i=0;i<20;++i)assert(rescue.exec()==ACTOUT_Continue);
 assert(rescue.exec()==ACTOUT_Success);
 std::puts("PASS actual Blue rescue missing-route, reuse and valid throw regressions");
}
