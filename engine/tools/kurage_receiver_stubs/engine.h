#pragma once
#include <cmath>
#include <functional>
#include <vector>

// Observable engine doubles for the Kurage receiver + captain squad-capture
// seam (lane 12, #130; codex/p2-lane12-review c29ec8398 port). The production
// pc_p2_kurage_receiver.cpp / pc_p2_captain.cpp compile against these in the
// single-TU ctest (the test neutralizes the real engine headers by defining
// their include guards first), so this stub must provide every engine fact
// those TUs touch: captain handle/health, Piki::mNavi ownership, the squad
// action abandoned at capture, and the manager globals.
using f32 = float;
#ifndef C_NAVI_PARM
#define C_NAVI_PARM(navi, field) (100.0f)
#endif
struct Vector3f {
    float x=0,y=0,z=0;
    Vector3f()=default;
    Vector3f(float a,float b,float c):x(a),y(b),z(c){}
    void set(float a,float b,float c){x=a;y=b;z=c;}
    Vector3f operator-(const Vector3f& v)const{return {x-v.x,y-v.y,z-v.z};}
    Vector3f operator*(float s)const{return {x*s,y*s,z*s};}
    float length()const{return std::sqrt(x*x+y*y+z*z);}
    void normalise(){const float l=length();if(l>0.0f){x/=l;y/=l;z/=l;}}
};
struct CollPart { Vector3f mCentre; float mRadius=15; };
struct Creature { struct {Vector3f s{1,1,1},t;} mSRT; virtual ~Creature()=default; };
constexpr int NAVISTATE_NULL=-1, NAVISTATE_Walk=0, NAVISTATE_Idle=1;
constexpr unsigned KBBTN_DPAD_UP=1;
struct NaviState { int getID()const{return NAVISTATE_Walk;} };
struct Kontroller {
    unsigned mCurrentInput=0,mPrevInput=0,mInputPressed=0,mInputReleased=0;
    unsigned mInputDoublePressed=0,mDoublePressMask=0,mInputDelay=0;
    float mMainStickX=0,mMainStickY=0,mSubStickX=0,mSubStickY=0;
    float mAnalogA=0,mAnalogB=0,mTriggerL=0,mTriggerR=0;
    bool keyDown(unsigned key)const{return (mCurrentInput & key)!=0;}
};
struct Navi:Creature {
    Kontroller controller; Kontroller* mKontroller=&controller;
    NaviState state;
    bool mIsCursorVisible=false;
    NaviState* getCurrState(){return &state;}
    bool isGrabbed()const{return false;}
    bool isHolding()const{return false;}
    float mHealth=100.0f;
    int mNaviIndex=0;
    bool alive=true;
    Vector3f mVelocity,mTargetVelocity;
    float mFaceDirection=0.0f;
    bool isAlive()const{return alive;}
    int getNaviIndex()const{return mNaviIndex;}
    Vector3f getPosition()const{return mSRT.t;}
};
struct Piki;
struct TopAction { int mCurrActionIdx=0; int cleanups=0; void abandon(void*){++cleanups;} };
struct FSM {void transit(Piki*,int){}};
struct Piki:Creature {
    Navi* mNavi=nullptr; Vector3f mAttachPosition;
    TopAction action; TopAction* mActiveAction=&action;
    int mMode=0;
    bool alive=true,stickable=true;
    int mState=0; // PIKISTATE_*
    int getState()const{return mState;}
    Creature* owner=nullptr; CollPart* part=nullptr;
    Vector3f mVelocity,mTargetVelocity; FSM fsm; FSM* mFSM=&fsm;
    int kills=0,changes=0;
    std::function<void()> detached;
    bool isAlive()const{return alive;}
    bool isStickTo()const{return owner!=nullptr;}
    bool mayIstick()const{return stickable;}
    Creature* getStickObject()const{return owner;}
    CollPart* getStickPart()const{return part;}
    void startStickObject(Creature* o,CollPart* p,int,float){owner=o;part=p;}
    void endStickObject(){owner=nullptr;part=nullptr;if(detached)detached();}
    void setEraseKill(){}
    void kill(bool){alive=false;++kills;}
    void changeMode(int,Creature*){++changes;}
};
struct ObjectMgr {
    std::vector<Piki*> entries;
    int getFirst(){return 0;} bool isDone(int i){return i>=int(entries.size());}
    int getNext(int i){return i+1;} Creature* getCreature(int i){return entries[i];}
};
struct PikiMgr:ObjectMgr{};
struct NaviMgr {
    Navi navi;
    bool dead=false;
    Navi* getNavi(int slot=0){return slot==0?&navi:nullptr;}
    Navi* getActiveNavi(){return &navi;}
    Navi* getOtherNavi(Navi*){return nullptr;}
    bool hasSecondNavi()const{return false;}
    void setActiveNavi(Navi*){}
    void informOrimaDead(Navi*){dead=true;}
    bool isNaviDead(Navi*){return dead;}
};
inline PikiMgr* pikiMgr=nullptr;
inline NaviMgr* naviMgr=nullptr;
namespace PikiMode {constexpr int FreeMode=0; constexpr int AttackMode=1; constexpr int FormationMode=2;}
namespace PikiAction {constexpr int NOACTION=0; constexpr int Crowd=1;}
constexpr int PIKISTATE_Normal=0;

// This receiver harness models the default single-captain engine. The opt-in
// switch behavior is covered separately by the captain policy/runtime tests.
struct PcamCameraManager {
    Kontroller* mController=nullptr;
    void startCamera(Navi*){}
};
inline PcamCameraManager* cameraMgr=nullptr;
inline struct GameFlowDouble { unsigned mDemoFlags=0; } gameflow;
namespace CinePlayerFlags { constexpr unsigned NaviNoAI=1; }
inline bool pc_coop_active(){return false;}
inline bool pc_vs_active(){return false;}
namespace pc_p2_captain { inline bool second_captain_requested(){return false;} }
constexpr int PIKISTATE_Flying=14; // real PikiState.h ids (the suction policy compares them)
constexpr int PIKISTATE_Push=20;
constexpr int PIKISTATE_PushPiki=21;
constexpr int PIKISTATE_Emotion=31;
