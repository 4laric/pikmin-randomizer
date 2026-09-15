#pragma once
#include <functional>
#include <vector>
struct Vector3f {
    float x=0,y=0,z=0;
    Vector3f()=default;
    Vector3f(float a,float b,float c):x(a),y(b),z(c){}
    void set(float a,float b,float c){x=a;y=b;z=c;}
    Vector3f operator-(const Vector3f& v)const{return {x-v.x,y-v.y,z-v.z};}
};
struct CollPart { Vector3f mCentre; float mRadius=15; };
struct Creature { struct {Vector3f s{1,1,1},t;} mSRT; virtual ~Creature()=default; };
struct Piki;
struct FSM {void transit(Piki*,int){}};
struct Piki:Creature {
    bool alive=true,stickable=true;
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
struct NaviMgr {Creature* getNavi(){return nullptr;}};
inline PikiMgr* pikiMgr=nullptr;
inline NaviMgr* naviMgr=nullptr;
namespace PikiMode {constexpr int FreeMode=0;}
constexpr int PIKISTATE_Normal=0;
