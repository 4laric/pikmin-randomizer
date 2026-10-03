#include "pc_p2_original_pelplant.h"
#include "pc_p2_original_pelplant_blend.h"
#include <cassert>
#include <iostream>
// Deliberately labelled bridge controls. These prove ownership/FSM contracts,
// not native model capture, combat, Onion population or gameplay acceptance.
class Creature {public: int identity=0;};
class Generator {};
class Pellet {public: int color=0;bool captured=false,alive=true;};
using namespace p2original;
using namespace p2original::pelplant;
struct ControlledEngine final:Engine {
 Resources pack;std::vector<std::unique_ptr<Creature>> roots;
 std::vector<std::unique_ptr<Pellet>> pellets;
 unsigned reservedActors=0,allocations=0,cleanups=0,releases=0,kills=0,motionIndex=99;
 std::array<unsigned,4> reservedPellets{};
 bool cleanupFails=false,captureFails=false,allocationFails=false,commonResourceFails=false;unsigned met=7;
 ControlledEngine(){pack.model=pack.root=pack.head=pack.neck=pack.collider=true;pack.clips.fill(true);
  for(auto& colors:pack.numberConfigs)colors.fill(true);pack.parameters={90,60,1.5f,50};}
 bool resources(Resources& r,std::string&)override{r=pack;return true;}
 bool commonResources(const CatalogRow&,std::string&)override{return !commonResourceFails;}
 bool identity(Host& h,std::string& durable,std::string&)override{durable="fixture-catalog:"+h.row.sourceKey+":"+std::to_string(h.ordinal)+":epoch1:activation1";return true;}
 bool reserve(unsigned a,const std::array<unsigned,4>& p,std::string&)override{reservedActors=a;reservedPellets=p;return true;}
 bool allocate(Host& h,const Position&,float,std::string&)override{auto p=std::make_unique<Creature>();p->identity=++allocations;h.creature=p.get();roots.push_back(std::move(p));return !allocationFails;}
 bool captureNumber(Host&,unsigned,int c,Pellet*& out,std::string&)override{if(captureFails)return false;auto p=std::make_unique<Pellet>();p->color=c;p->captured=true;out=p.get();pellets.push_back(std::move(p));return true;}
 bool pelletColor(Pellet* p,int c,std::string&)override{p->color=c;return true;}
 bool metColor(unsigned c)const override{return met&(1u<<c);}
 bool motion(Host&,unsigned index,bool,std::string&)override{motionIndex=index;return true;}
 bool flags(Host&,bool,bool,bool,float,std::string&)override{return true;}
 bool flick(Host&,std::string&)override{return true;}
 bool deathProcedure(Host&,std::string&)override{return true;}
 bool endCapture(Host&,Pellet* p,std::string&)override{p->captured=false;++releases;return true;}
 bool killPlant(Host&,std::string&)override{++kills;return true;}
 bool cleanup(Host& h,std::string&)override{if(cleanupFails)return false;++cleanups;if(h.captured){h.captured->alive=false;h.captured=nullptr;}return true;}
};
CatalogRow row(unsigned uid,unsigned amount,unsigned stage,unsigned count=1){CatalogRow r;r.course="tutorial";r.member="nonloop/3-9.txt";r.sourceKey="original:"+std::to_string(uid);r.enemy.uid=uid;r.enemy.count=count;r.enemy.generatorVersion="0001";r.enemy.generatorTail={"3",std::to_string(amount),std::to_string(stage)};return r;}
int main(){
 std::string error;Initial initial;auto one=row(1,1,2);
 assert(witherWeight(0)==0&&witherWeight(1)==1&&witherWeight(2)==1&&witherWeight(-1)==0);
 assert(witherWeight(.125f)==0&&witherWeight(.25f)>.62f&&witherWeight(.25f)<.63f);
 std::array<float,12> jointA{},jointB{},jointOut{};jointA[7]=90;jointB[7]=0;
 assert(blendJoint(jointA,jointB,witherWeight(.25f),jointOut)&&jointOut[7]>33&&jointOut[7]<35);
 assert(blendJoint(jointA,jointB,0,jointOut)&&jointOut==jointA);
 assert(blendJoint(jointA,jointB,1,jointOut)&&jointOut==jointB);
 p2pose::Pose poseA{{{0,90,0}},{{1,0,0}}},poseB{{{0,0,0}},{{1,0,0}}},poseOut=poseA;
 assert(samplePose({poseA,poseB},{0,29},14.5f,poseOut)&&poseOut.positions[0].y==45);
 assert(p2pose::blendInto(poseA,poseB,witherWeight(.25f),poseOut)&&poseOut.positions[0].y>33&&poseOut.positions[0].y<35);
 assert(blendJoint(jointA,jointB,witherWeight(.25f),jointOut)&&std::fabs(poseOut.positions[0].y-jointOut[7])<.0001f);
 assert(decode(one,initial,error)&&initial.color==3&&initial.amount==1&&initial.stage==2);
 auto old=one;old.enemy.generatorVersion="0000";old.enemy.generatorTail={"0","1"};assert(decode(old,initial,error)&&initial.amount==1);
 for(auto tail:std::vector<std::vector<std::string>>{{"3","1"},{"3","1","2","0"},{"4","1","2"},{"3","0","2"},{"3","2","2"},{"3","1","3"},{"-1","1","2"},{"3","1.0","2"}}){auto bad=one;bad.enemy.generatorTail=tail;assert(!decode(bad,initial,error));}
 auto badVersion=one;badVersion.enemy.generatorVersion="0002";assert(!decode(badVersion,initial,error));
 ControlledEngine engine;Provider provider(engine);
 std::vector<CatalogRow> rows{row(1,1,2),row(2,1,2),row(3,1,1,2),row(4,5,2),row(5,5,2),row(6,5,2),row(7,10,1)};
 engine.pack.clips[7]=false;assert(!provider.preflight(rows,error)&&engine.allocations==0);engine.pack.clips[7]=true;
 engine.pack.numberConfigs[2][2]=false;assert(!provider.preflight(rows,error)&&engine.allocations==0);engine.pack.numberConfigs[2][2]=true;
 engine.commonResourceFails=true;assert(!provider.preflight(rows,error)&&engine.allocations==0&&engine.reservedActors==0);engine.commonResourceFails=false;
 assert(provider.preflight(rows,error));auto changed=rows;changed[0].enemy.treasureCode=5;assert(!provider.reserve(changed,error));
 const std::array<unsigned,4> expectedPellets{{4,3,1,0}};
 assert(provider.reserve(rows,error)&&engine.reservedActors==8&&engine.reservedPellets==expectedPellets);
 Generator gen;Creature* actor=nullptr;assert(provider.birth(rows[0],&gen,0,{1,2,3},0.5f,actor,error));
 assert(provider.bind(rows[0],actor,0x53000001,error));Host* host=provider.lookup(actor);Pellet* captured=host->captured;
 assert(captured&&captured->captured&&captured->color==1);
 assert(host->cullable&&host->lodRadius==45);
 assert(provider.damage(actor,0,"s__0",error));assert(provider.tick(actor,0,Event::Other,error)&&host->state==State::Full);
 assert(provider.tick(actor,0,Event::None,error)&&host->state==State::Dead&&engine.releases==0);
 assert(provider.tick(actor,0,Event::LoopEnd,error)&&engine.releases==0);
 assert(provider.tick(actor,0,Event::End,error)&&engine.releases==1&&engine.kills==1&&!captured->captured);
 assert(provider.release(actor,0x53000001,error)&&captured->alive);
 unsigned token=0;bool duplicate=true;assert(provider.onion(captured,token,duplicate)&&token==0x53000001&&!duplicate);
 assert(provider.onion(captured,token,duplicate)&&duplicate);provider.forgetPellet(captured);assert(!provider.onion(captured,token,duplicate));
 Generator middle;assert(provider.birth(rows[6],&middle,0,{0,0,0},0,actor,error));assert(provider.bind(rows[6],actor,0x53000002,error));host=provider.lookup(actor);
 assert(!host->captured&&provider.damage(actor,100,"s__0",error)&&host->damage==0);
 assert(!host->cullable&&host->lodRadius==45);
 assert(provider.tick(actor,61,Event::None,error)&&host->state==State::Middle);
 assert(provider.tick(actor,0,Event::LoopEnd,error)&&host->state==State::GrowMiddleFull&&host->captured&&engine.motionIndex==7);
 assert(!host->cullable&&host->lodRadius==103);
 assert(provider.tick(actor,0,Event::End,error)&&host->state==State::Full);
 assert(host->cullable&&host->lodRadius==103);
 captured=host->captured;assert(provider.farm(actor,-1,error)&&provider.tick(actor,0,Event::LoopEnd,error)&&host->state==State::WitherFull);
 assert(host->cullable&&host->lodRadius==103);
 assert(provider.tick(actor,0,Event::EndBlend,error)&&host->state==State::Small&&host->captured==captured);
 assert(!host->cullable&&host->lodRadius==45);
 assert(provider.farm(actor,1,error)&&provider.tick(actor,0,Event::LoopEnd,error)&&host->state==State::GrowSmallMiddle);
 assert(provider.tick(actor,0,Event::End,error)&&provider.tick(actor,0,Event::LoopEnd,error)&&host->captured==captured);
 assert(provider.release(actor,0x53000002,error)&&!captured->alive);
 // Failed after real allocation: owner returns pending actor if cleanup fails.
 Generator failure;engine.captureFails=true;engine.cleanupFails=true;actor=nullptr;
 assert(!provider.birth(rows[1],&failure,0,{0,0,0},0,actor,error)&&actor&&provider.lookup(actor));
 assert(!provider.release(actor,0,error));engine.cleanupFails=false;assert(provider.release(actor,0,error));
 std::cout<<"Pelplant strict bytes, eight-actor reservation, authored event FSM and owned cleanup controls PASS; native gameplay not claimed\n";
}
