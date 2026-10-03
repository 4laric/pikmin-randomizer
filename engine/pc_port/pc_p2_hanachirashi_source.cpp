#include "pc_p2_hanachirashi_source.h"
#include "pc_p2_hanachirashi_source_policy.h"
#include "pc_p2_hanachirashi_receiver.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_original_hanachirashi_native.h"
#include "pc_p2_flyer.h"
#include "teki.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "pc_p2_navi_select.h"
#include "Collision.h"
#include "CreatureCollPart.h"
#include "Interactions.h"
#include "MapMgr.h"
#include "sysNew.h"
#include "settings/pc_settings.h"
#include <fstream>
#include <sstream>
#include <set>
#include <cstdio>
extern Matrix4f invCamMat;
namespace p2hana {namespace {
struct Node {const char* id;const char* code;float radius;};
// Literal Hanachirashi enemycoll.txt (NOT Mar): root head joint2, eight
// stickable children. Duplicate `none` IDs are preserved through child order.
const Node nodes[9]={{"none","____",42.5f},{"han1","st__",5},{"han2","st__",4},{"none","st__",20},{"body","st__",26},{"arL1","st__",5},{"arL2","st__",5},{"arR1","st__",5},{"arR2","st__",5}};
unsigned four(const char* s){return unsigned(s[0])<<24|unsigned(s[1])<<16|unsigned(s[2])<<8|unsigned(s[3]);}
V vec(const Vector3f& v){return {v.x,v.y,v.z};}
Vector3f native(V v){return Vector3f(v.x,v.y,v.z);}
float distance(V a,V b){V d=sub(a,b);return std::sqrt(d.x*d.x+d.z*d.z);}
struct Coll {
 CollInfo* vehicle=nullptr;CollInfo* own=nullptr;std::array<CollPart*,9> parts{};
 bool bind(BTeki* a){
  if(!a->mCollInfo)return false;
  if(own){vehicle=a->mCollInfo;a->mCollInfo=own;a->mPlatMgr.release();return true;}
  ObjCollInfo* objects[9];
  for(int i=0;i<9;++i){objects[i]=new ObjCollInfo;objects[i]->mId.setID(four(nodes[i].id));objects[i]->mCode.setID(four(nodes[i].code));objects[i]->mRadius=nodes[i].radius;objects[i]->mJointIndex=-1;}
  for(int i=1;i<9;++i)objects[0]->add(objects[i]);
  own=new CollInfo(16);own->initInfoTree(objects[0]);parts[0]=own->getBoundingSphere();if(!parts[0])return false;
  for(int i=1;i<9;++i)parts[i]=parts[0]->getChildAt(i-1);
  for(auto* p:parts){if(!p)return false;p->mIsUpdateActive=false;}
  vehicle=a->mCollInfo;a->mCollInfo=own;a->mPlatMgr.release();return true;
 }
 void follow(BTeki* a,const Sample& s){
  Matrix4f actor,cam,base;actor.makeSRT(Vector3f(1,1,1),Vector3f(0,a->getDirection(),0),Vector3f(0,0,0));cam.makeIdentity();
  for(int r=0;r<3;++r)for(int c=0;c<3;++c)cam.mMtx[r][c]=invCamMat.mMtx[c][r];cam.multiplyTo(actor,base);
  for(int i=0;i<9;++i){V centre=add(vec(a->getPosition()),yaw(s.parts[i].centre,a->getDirection()));parts[i]->mCentre=native(centre);parts[i]->mRadius=nodes[i].radius;
   Matrix4f joint,world;joint.makeIdentity();for(int r=0;r<3;++r)for(int c=0;c<3;++c)joint.mMtx[r][c]=s.parts[i].rotation[r*3+c];base.multiplyTo(joint,world);parts[i]->mJointMatrix=world;
  }
 }
 void detach(BTeki* a){if(vehicle&&a->mCollInfo==own)a->mCollInfo=vehicle;vehicle=nullptr;}
};
struct Actor {
 State state=Wait;std::string motion="move1";float frame=0,time=0,fallTimer=0,pitch=0,scale=0;bool deadFlying=false,finished=false,windActive=false,windHit=false,event2=false;
 V home,targetPosition;Creature* target=nullptr;unsigned uid=0,ordinal=0,token=0;Coll coll;
};
std::map<BTeki*,Actor> actors;std::map<BTeki*,Coll> idleColliders;JointBank bank;std::string bankBytes;
unsigned stuck(BTeki* actor,unsigned& purple){unsigned n=0;purple=0;if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->getStickObject()==actor&&!p->isStickToMouth()){++n;if(p->mP2Purple)++purple;}}}return n;}
void stop(BTeki* a){a->inputDrive(Vector3f(0,0,0));a->mVelocity.x=a->mVelocity.z=0;}
void height(BTeki* a,Actor& s,float dt){float floor=mapMgr?mapMgr->getMinY(a->getPosition().x,a->getPosition().z,true):a->getPosition().y;float ideal=70;if(a->getPosition().y-floor>65){s.pitch+=2.5f*dt;if(s.pitch>2*Pi)s.pitch-=2*Pi;ideal+=5*std::sin(s.pitch);}a->mVelocity.y=floor+ideal-a->getPosition().y;}
void turn(BTeki* a,Actor& s,V target){float h=p2flyer::turnStep(a->getDirection(),target.x-a->getPosition().x,target.z-a->getPosition().z,.05f,10.f);a->setDirection(h);}
void walk(BTeki* a,Actor& s,V target){turn(a,s,target);float h=a->getDirection();V velocity={100*std::sin(h),a->mVelocity.y,100*std::cos(h)};a->inputDrive(native(velocity));a->mVelocity=native(velocity);}
void motion(Actor& s,const char* name){s.motion=name;s.frame=0;s.finished=false;s.event2=false;}
void enter(BTeki* a,Actor& s,State state){
 bool flying=a->isCreatureFlag(CF_IsFlying);s.state=state;s.time=0;s.windActive=false;s.windHit=false;s.scale=0;
 switch(state){
 case Dead:s.deadFlying=flying;stop(a);a->mVelocity.y=0;motion(s,flying?"dead":"dead2");break;
 case Wait:s.target=nullptr;stop(a);motion(s,"move1");break;
 case Move:{s.target=nullptr;float angle=std::atan2(a->getPosition().x-s.home.x,a->getPosition().z-s.home.z)+gsys->getRand(Pi)+Pi/2;float radius=gsys->getRand(150.f)+100;s.targetPosition=add(s.home,{radius*std::sin(angle),0,radius*std::cos(angle)});break;}
 case Chase:break;
 case ChaseInside:{V target=s.target?vec(s.target->getPosition()):s.home;V d=sub(s.home,target);d.y=0;s.targetPosition=s.target?add(target,mul(unit(d),275)):s.home;break;}
 case Attack:s.target=nullptr;stop(a);motion(s,"attack");break;
 case Fall:s.target=nullptr;stop(a);motion(s,"type2");break;
 case Land:s.target=nullptr;stop(a);motion(s,"move2");break;
 case Ground:s.target=nullptr;stop(a);motion(s,"wait2");break;
 case TakeOff:s.target=nullptr;stop(a);motion(s,"type1");break;
 case FlyFlick:s.target=nullptr;stop(a);motion(s,"damage");break;
 case GroundFlick:s.target=nullptr;stop(a);motion(s,"flick");break;
 case Laugh:s.target=nullptr;stop(a);motion(s,"laugh");break;
 }
 std::printf("P2_HANACHIRASHI_SOURCE_STATE uid=%u token=%u state=%d clip=%s\n",s.uid,s.token,int(state),s.motion.c_str());
}
Creature* searched(BTeki* a,unsigned count){
 if(!pikiMgr)return nullptr;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||p->isStickToMouth()||p->getStickObject()==a||!p->mGroundTriangle)continue;V d=sub(vec(p->getPosition()),vec(a->getPosition()));float angle=std::fabs(wrap(std::atan2(d.x,d.z)-a->getDirection()));if(distance(vec(p->getPosition()),vec(a->getPosition()))<275&&angle<=(count?Pi:90.f*Pi/180.f*Pi))return p;}return nullptr;
}
Creature* attackable(BTeki* a){
 if(!pikiMgr)return nullptr;V centre=add(vec(a->getPosition()),{200*std::sin(a->getDirection()),0,200*std::cos(a->getDirection())});Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&!p->isStickToMouth()&&p->getStickObject()!=a&&distance(vec(p->getPosition()),centre)<20)return p;}return nullptr;
}
bool lost(BTeki* a,const Actor& s,unsigned count){if(!s.target||!s.target->isAlive()||s.target->isStickToMouth()||s.target->getStickObject()==a)return true;V d=sub(vec(s.target->getPosition()),vec(a->getPosition()));return (d.x*d.x+d.z*d.z>10000&&d.x*d.x+d.z*d.z>275*275&&std::fabs(d.y)<12800)||std::fabs(wrap(std::atan2(d.x,d.z)-a->getDirection()))>(count?Pi:Pi/2);}
void flick(BTeki* a,bool nearby){
 if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;bool attached=p->getStickObject()==a&&!p->isStickToMouth();if(!attached&&(!nearby||distance(vec(p->getPosition()),vec(a->getPosition()))>=40))continue;
  if(attached)p->endStickObject();pc_p2_hanachirashi_flick_piki(a,p);}}
 if(nearby)for(Navi* n:pc_p2_navis())if(n&&n->isAlive()&&distance(vec(n->getPosition()),vec(a->getPosition()))<40)pc_p2_hanachirashi_flick_navi(a,n);
}
bool windTick(BTeki* a,Actor& s,float dt,const Sample& pose){
 s.scale=std::min(1.f,s.scale+3*dt);V emitter=add(vec(a->getPosition()),yaw(pose.emitter,a->getDirection()));V impulse;bool success=false;
 for(Navi* n:pc_p2_navis())if(n&&n->isAlive()&&wind(emitter,a->getDirection(),vec(n->getPosition()),s.scale*300,true,impulse))pc_p2_hanachirashi_wind_navi(a,n,native(impulse));
 if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&wind(emitter,a->getDirection(),vec(p->getPosition()),s.scale*300,false,impulse))success=pc_p2_hanachirashi_wind_piki(a,p,native(impulse));}}
 return success; // Retail stores the last in-cone Pikmin receiver result.
}
} // private
bool resources(std::string& error){
 if(!gsys){error="source55 system unavailable";return false;}
 std::ifstream input("p2-hanachirashi-joints.txt");std::string bytes((std::istreambuf_iterator<char>(input)),{});std::istringstream stream(bytes);JointBank staged;if(!readJoints(stream,staged,error))return false;
 if(!actors.empty()){if(bytes==bankBytes){error.clear();return true;}error="source55 resources cannot change with live actors";return false;}
 bankBytes=std::move(bytes);bank=std::move(staged);error.clear();return true;
}
bool birth(BTeki* a,unsigned uid,unsigned ordinal,std::string& error){
 if(!a||a->mTekiType!=TEKI_Mar||!uid||bank.size()!=11||actors.count(a)){error="source55 actor/joint resources unavailable";return false;}
 Actor state;auto cached=idleColliders.find(a);if(cached!=idleColliders.end()){state.coll=cached->second;idleColliders.erase(cached);}
 state.home=vec(a->getPosition());state.uid=uid;state.ordinal=ordinal;
 const int old=gsys->setHeap(SYSHEAP_App);bool bound=state.coll.bind(a);gsys->setHeap(old);
 if(!bound){state.coll.detach(a);error="source55 real joint collision allocation failed";return false;}
 state.coll.follow(a,sample(bank,"move1",0));a->setCreatureFlag(CF_IsFlying);a->enableGravity();a->mHealth=a->mMaxHealth=1800;
 actors.emplace(a,std::move(state));error.clear();return true;
}
bool registry(BTeki* a,unsigned token,std::string& error){auto found=actors.find(a);unsigned source=0,id=0;p2original::InstanceIdentity identity;
 if(found==actors.end()||!token||found->second.token||!p2original::originalActors().query(a,source,id,&identity)||source!=55||id!=token||identity.generator!=found->second.uid||identity.ordinal!=found->second.ordinal){error="source55 original registry mismatch";return false;}
 found->second.token=token;error.clear();return true;
}
bool active(){return !actors.empty();}
bool has(const BTeki* a){return actors.count(const_cast<BTeki*>(a));}
void forget(BTeki* a){auto found=actors.find(a);if(found==actors.end())return;found->second.coll.detach(a);idleColliders[a]=found->second.coll;actors.erase(found);}
bool clip(const BTeki* a,const char*& name,float& phase){auto found=actors.find(const_cast<BTeki*>(a));if(found==actors.end())return false;name=found->second.motion.c_str();phase=found->second.frame/float(bank.at(name).size()-1);return true;}
bool update(BTeki* a){
 auto found=actors.find(a);if(found==actors.end())return false;Actor& s=found->second;float dt=gsys->getFrameTime();if(dt<=0)return true;dt=std::min(dt,.5f);
 if(a->mStoredDamage>0)a->makeDamaged();unsigned purple=0,count=stuck(a,purple);V pos=vec(a->getPosition());
 // The source FSM executes before updateFallTimer. The previous frame's
 // fall timer is used, then the current attachment count updates it below.
 if(a->mHealth<=0&&s.state!=Dead&&s.state!=Laugh)enter(a,s,Dead);
 Sample pose=sample(bank,s.motion,s.frame);Clock event=advanceClock(s.motion,s.frame,s.finished,s.event2,dt,unsigned(bank.at(s.motion).size()));
 switch(s.state){
 case Wait:{stop(a);height(a,s,dt);Creature* target=searched(a,count);if(!target)target=attackable(a);if(target){s.target=target;enter(a,s,Chase);}else if(s.time>3)enter(a,s,Move);break;}
 case Move:{height(a,s,dt);if(Creature* target=searched(a,count)){s.target=target;enter(a,s,Chase);}else if(distance(pos,s.targetPosition)<100||s.time>7.5f){stop(a);s.finished=true;}else walk(a,s,s.targetPosition);if(event.end)enter(a,s,Wait);break;}
 case Chase:{height(a,s,dt);if(!s.finished){if(s.target){V target=vec(s.target->getPosition()),sep=sub(pos,target);sep.y=0;V point=add(target,mul(unit(sep),200));turn(a,s,target);if(distance(pos,point)>15){float angle=std::atan2(point.x-pos.x,point.z-pos.z);a->mVelocity.x=100*std::sin(angle);a->mVelocity.z=100*std::cos(angle);a->inputDrive(a->mVelocity);}else stop(a);if(distance(pos,s.home)>250)enter(a,s,ChaseInside);else if(lost(a,s,count)){if(Creature* t=searched(a,count))s.target=t;else enter(a,s,Wait);}}if(Creature* target=attackable(a)){s.target=target;stop(a);s.finished=true;}}
  if(event.end)enter(a,s,s.target?Attack:Wait);break;}
 case ChaseInside:{height(a,s,dt);if(distance(pos,s.targetPosition)<100)enter(a,s,Chase);else{if(s.target)turn(a,s,vec(s.target->getPosition()));float angle=std::atan2(s.targetPosition.x-pos.x,s.targetPosition.z-pos.z);a->mVelocity.x=100*std::sin(angle);a->mVelocity.z=100*std::cos(angle);a->inputDrive(a->mVelocity);}if(event.end)enter(a,s,Wait);break;}
 case Attack:{stop(a);height(a,s,dt);if(s.windActive&&windTick(a,s,dt,pose))s.windHit=true;if(event.key2)s.windActive=true;if(event.end)enter(a,s,s.windHit?Laugh:Wait);break;}
 case Fall:{stop(a);if(a->isCreatureFlag(CF_IsFlying))height(a,s,dt);else {float floor=mapMgr?mapMgr->getMinY(pos.x,pos.z,true):pos.y;if(pos.y-floor<50||a->mVelocity.y>0)s.finished=true;}if(event.end)enter(a,s,Land);break;}
 case Land:stop(a);if(event.end)enter(a,s,Ground);break;
 case Ground:stop(a);if(!count||s.time>1)s.finished=true;if(event.end)enter(a,s,count?GroundFlick:TakeOff);break;
 case TakeOff:stop(a);if(a->isCreatureFlag(CF_IsFlying))height(a,s,dt);if(event.end)enter(a,s,Wait);break;
 case FlyFlick:stop(a);height(a,s,dt);if(event.key2)flick(a,false);if(event.end)enter(a,s,Wait);break;
 case GroundFlick:stop(a);if(event.key2)flick(a,true);if(event.end)enter(a,s,TakeOff);break;
 case Laugh:stop(a);height(a,s,dt);if(event.end){int next=flyingNext(a->mHealth,count,purple,s.fallTimer);if(next>=0)enter(a,s,State(next));else enter(a,s,attackable(a)?Attack:Wait);}break;
 case Dead:stop(a);if(event.end){pc_p2_original_spawn_items(a);a->die();a->kill(false);return true;}break;
 }
 if(s.state==Wait||s.state==Move||s.state==Chase||s.state==ChaseInside){int next=flyingNext(a->mHealth,count,purple,s.fallTimer);if(next>=0)enter(a,s,State(next));}
 if(s.state==Dead?s.deadFlying:(s.state==TakeOff?s.event2:airborne(s.state,s.time)))a->setCreatureFlag(CF_IsFlying);else a->resetCreatureFlag(CF_IsFlying);a->enableGravity();
 s.time+=dt;s.fallTimer=count?s.fallTimer+dt:0;s.coll.follow(a,sample(bank,s.motion,s.frame));return true;
}
} // p2hana
