#pragma once
#include <cmath>
#include <cstdint>
#include <vector>
#include "pc_blue_rescue.h"
#define immut const
#define STACK_PAD_VAR(n)
using f32 = float;
using u16 = std::uint16_t;
struct Vector3f {
 float x=0,y=0,z=0;
 Vector3f()=default; Vector3f(float a,float b,float c):x(a),y(b),z(c){}
 float length()const{return std::sqrt(x*x+y*y+z*z);}
 float normalise(){float d=length();if(d>0){x/=d;y/=d;z/=d;}return d;}
 void set(float a,float b,float c){x=a;y=b;z=c;}
 void multiply(float s){x*=s;y*=s;z*=s;}
 Vector3f operator-(const Vector3f& b)const{return {x-b.x,y-b.y,z-b.z};}
 Vector3f operator+(const Vector3f& b)const{return {x+b.x,y+b.y,z+b.z};}
 Vector3f operator*(float s)const{return {x*s,y*s,z*s};}
};
inline float absF(float f){return std::fabs(f);}
inline float angDist(float a,float b){return a-b;}
inline float roundAng(float a){return a;}
struct PaniAnimKeyEvent {int mEventType;};
enum {KEY_Action0, KEY_Finished};
enum {PIKISTATE_Drown, PIKISTATE_WaterHanged, PIKISTATE_Flying, PIKISTATE_Normal};
enum {PIKIANIM_Walk,PIKIANIM_ThrowWait,PIKIANIM_Throw};
namespace PikiEmotion {enum {Searching,Sad,Victorious};}
enum {ACTOUT_Continue,ACTOUT_Fail,ACTOUT_Success};
struct Creature {virtual ~Creature()=default;virtual bool isPiki(){return false;}};
struct Piki;
struct TopAction;
struct FSM {int calls=0;void transit(Piki*,int);};
struct PaniMotionInfo {explicit PaniMotionInfo(int,void* = nullptr){}};
struct Piki:Creature {
 bool alive=true;int state=PIKISTATE_Drown,mEmotion=0,species=0;TopAction* mActiveAction=nullptr;FSM fsm;FSM* mFSM=&fsm;
 struct {Vector3f t;} mSRT;Vector3f mVelocity,mTargetVelocity;float mFaceDirection=0;
 bool isPiki()override{return true;}bool isAlive(){return alive;}int getState(){return state;}
 void startMotion(PaniMotionInfo,PaniMotionInfo){}void enableMotionBlend(){}
 void setSpeed(float,Vector3f){}
};
inline void FSM::transit(Piki* p,int s){++calls;if(p->state==PIKISTATE_WaterHanged || s==PIKISTATE_WaterHanged)pc_blue_rescue_clear(p);p->state=s;}
struct Action {Piki* mPiki;Action(Piki* p,bool):mPiki(p){}void setName(const char*){}};
struct WayPoint {Vector3f mPosition;float mRadius=10;};
struct RouteMgr {WayPoint* waypoint=nullptr;int queries=0;bool dry=false;
 WayPoint* findNearestWayPoint(unsigned,const Vector3f&,bool exclude){++queries;dry=exclude;return waypoint;}};
extern RouteMgr* routeMgr;
struct System {float getFrameTime(){return .033f;}};
extern System* gsys;
inline Vector3f getThrowVelocity(Vector3f,float,Vector3f,Vector3f){return {1,2,3};}
struct ActRescue:Action {
 enum StateID {STATE_Approach,STATE_Rescue,STATE_Go,STATE_Throw};
 ActRescue(Piki*);void init(Creature*);int exec();void animationKeyUpdated(const PaniAnimKeyEvent&);
 void initApproach();int exeApproach();void initRescue();int exeRescue();bool initGo();int exeGo();
 void initThrow();int exeThrow();void cleanup();
 bool holdsVictim(const Piki* p)const{return mDrowningPiki==p && (mState==STATE_Go || mState==STATE_Throw);}
 u16 mState=0;Piki* mDrowningPiki=nullptr;u16 mTargetSurviveTimer=0;
 Vector3f mRescueTargetPosition;bool mGotAnimationAction=false,mAnimationFinished=false,mThrowReady=false;
};

namespace PikiAction {enum {NOACTION=-1,Rescue=26};}
struct TopAction {int mCurrActionIdx=PikiAction::Rescue;Action* action=nullptr;Action* getCurrAction(){return action;}};
struct PikiMgr {std::vector<Piki*> actors;};
extern PikiMgr* pikiMgr;
struct Iterator {PikiMgr* manager;unsigned index=0;Iterator(PikiMgr* m):manager(m){};void first(){index=0;}bool isDone(){return index>=manager->actors.size();}void next(){++index;}Piki* operator*(){return manager->actors[index];}};
#define CI_LOOP(it) for(it.first();!it.isDone();it.next())
