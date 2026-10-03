#include "pc_p2_original_wisp.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
#include <vector>

// Deliberately fake opaque identities: these tests exercise provider policy,
// never native actors, authored resource conversion, or ordinary gameplay.
using namespace p2original;
using namespace p2original::wisp;
static bool near(float a,float b){return std::fabs(a-b)<0.0001f;}
struct Fake final:Engine {
 Resources r; int rootStorage[10]{},eggStorage[10]{},generatorStorage=0;
 Position p,vel; bool canAppear=true,isVisible=true,eggIndependent=false;
 unsigned allocations=0,reservedWisps=0,reservedEggs=0,releases=0,kills=0,cleanups=0;
 float actorFacing=0;bool nullBirth=false;
 bool atari=false,hidden=false,cullable=true,alive=true,stopped=false;
 unsigned anim=99;std::vector<std::string> effects;
 std::function<bool(Host&,std::string&)> onKill;
 Fake(){r.parameters={60,2.5f,20,100,1,80,90,200,9999};r.model=r.collider=r.waterJoint=r.glowJoint=r.egg=true;r.motions.fill(true);}
 bool resources(Resources& out,std::string&)override{out=r;return true;}
 bool reserve(unsigned w,unsigned e,std::string&)override{reservedWisps=w;reservedEggs=e;return true;}
 bool allocate(Host& h,const Position& pos,float,std::string&)override{assert(allocations<10);p=pos;h.creature=nullBirth?nullptr:reinterpret_cast<Creature*>(&rootStorage[allocations]);++allocations;return true;}
 bool attachEgg(Host&,Creature*& out,std::string&)override{out=reinterpret_cast<Creature*>(&eggStorage[allocations-1]);return true;}
 bool setPosition(Host&,const Position& pos,std::string&)override{p=pos;return true;}
 bool facing(Host&,float f,std::string&)override{actorFacing=f;return true;}
 bool flags(Host&,bool a,bool h,bool c,bool l,std::string&)override{atari=a;hidden=h;cullable=c;alive=l;return true;}
 bool motion(Host&,unsigned a,bool s,std::string&)override{anim=a;stopped=s;return true;}
 bool effect(Host&,const char* op,std::string&)override{effects.emplace_back(op);return true;}
 bool appear(const Host&,bool& out,std::string&)override{out=canAppear;return true;}
 bool visible(const Host&,bool& out,std::string&)override{out=isVisible;return true;}
 bool position(const Host&,Position& out,std::string&)override{out=p;return true;}
 bool floor(const Position&,float& out,std::string&)override{out=0;return true;}
 bool velocity(Host&,const Position& v,std::string&)override{vel=v;return true;}
 bool releaseEgg(Host& h,Creature* egg,std::string&)override{assert(egg==h.egg);++releases;eggIndependent=true;return true;}
 bool kill(Host& h,std::string& e)override{++kills;return onKill?onKill(h,e):true;}
 bool cleanup(Host& h,std::string&)override{++cleanups;assert(!h.released||!h.egg);return true;}
 Generator* generator(){return reinterpret_cast<Generator*>(&generatorStorage);}
};
static CatalogRow row(){CatalogRow r;r.sourceKey="tutorial/initgen.txt#34";r.enemy.uid=1382397626;r.enemy.source=16;r.enemy.count=1;r.enemy.generatorVersion="0000";r.enemy.generatorTail={"200.000000","30.000000"};return r;}
struct Fixture {
 Fake engine;Provider provider;CatalogRow original;Creature* actor=nullptr;std::string e;
 Fixture():provider(engine),original(row()){assert(provider.preflight({original},e));assert(provider.reserve({original},e));assert(provider.birth(original,engine.generator(),0,{10,20,30},0,actor,e));assert(actor);assert(provider.bind(original,actor,77,e));}
 Host& host(){assert(provider.lookup(actor));return *provider.lookup(actor);}
 void tick(float dt,Event event=Event::None){assert(provider.tick(actor,dt,event,e));}
 void move(){tick(1);assert(host().state==State::Stay);tick(.01f);assert(host().state==State::Appear&&engine.anim==3);tick(0,Event::End);assert(host().state==State::Move&&engine.anim==0);}
};
int main(){
 std::string e;Initial out;
 auto original=row();assert(decode(original,out,e)&&near(out.fly,200)&&near(out.slide,30));
 for(auto tail:std::vector<std::vector<std::string>>{{},{"200"},{"200","30","1"},{"nan","30"},{"200junk","30"}}){auto bad=original;bad.enemy.generatorTail=tail;assert(!decode(bad,out,e));}
 {auto bad=original;bad.enemy.generatorVersion="????";assert(!decode(bad,out,e));bad=original;bad.enemy.source=37;assert(!decode(bad,out,e));}
 {Fake f;f.r.waterJoint=false;Provider p(f);assert(!p.preflight({original},e));assert(f.allocations==0);}
 {Fake f;f.r.motions[3]=false;Provider p(f);assert(!p.preflight({original},e));}
 // Every supplied catalog field remains immutable across resource reservation,
 // root allocation and token binding; reject before the native callback.
 const std::vector<std::function<void(CatalogRow&)>> mutations={
  [](CatalogRow& r){r.course="changed";},[](CatalogRow& r){r.member="other.txt";},
  [](CatalogRow& r){++r.index;},[](CatalogRow& r){r.enemy.source=37;},
  [](CatalogRow& r){r.enemy.generatorTail[0]="201";},[](CatalogRow& r){r.enemy.directionDegrees=90;},
  [](CatalogRow& r){r.enemy.position.x=5;},[](CatalogRow& r){r.enemy.offset.z=1;},
  [](CatalogRow& r){r.enemy.pelletProbability=.1f;},[](CatalogRow& r){r.enemy.treasureCode=1;},
  [](CatalogRow& r){r.enemy.count=2;},[](CatalogRow& r){r.enemy.deathCount=1;}
 };
 for(const auto& mutate:mutations){
  Fake f;Provider p(f);assert(p.preflight({original},e));auto changed=original;mutate(changed);
  assert(!p.reserve({changed},e)&&f.reservedWisps==0);assert(p.reserve({original},e));
  Creature* actor=nullptr;assert(!p.birth(changed,f.generator(),0,{0,0,0},0,actor,e)&&!actor&&f.allocations==0);
  assert(p.birth(original,f.generator(),0,{0,0,0},0,actor,e)&&actor);assert(!p.bind(changed,actor,77,e));
  assert(p.bind(original,actor,77,e));assert(p.release(actor,77,e));
 }
 {Fake f;Provider p(f);assert(p.preflight({original},e)&&p.reserve({original},e));Creature* actor=nullptr;
  assert(!p.birth(original,f.generator(),0,{0,std::numeric_limits<float>::infinity(),0},0,actor,e)&&!actor&&f.allocations==0);
 }
 {Fake f;Provider p(f);auto two=original;two.enemy.count=2;assert(p.preflight({two},e)&&p.reserve({two},e));Creature* first=nullptr;Creature* second=nullptr;
  assert(p.birth(two,f.generator(),0,{0,0,0},0,first,e));assert(p.bind(two,first,77,e));
  assert(!p.birth(two,f.generator(),0,{0,0,0},0,second,e)&&!second&&f.allocations==1);
  assert(p.birth(two,f.generator(),1,{0,0,0},0,second,e)&&second!=first);assert(!p.bind(two,second,77,e));assert(p.bind(two,second,78,e));
  assert(!p.preflight({two},e));assert(p.release(first,77,e)&&p.release(second,78,e));
 }
 // A null root consumes the original ordinal too; retry must not consume a
 // second actor's capacity under the same durable identity.
 {Fake f;Provider p(f);auto two=original;two.enemy.count=2;assert(p.preflight({two},e)&&p.reserve({two},e));Creature* actor=nullptr;f.nullBirth=true;
  assert(p.birth(two,f.generator(),0,{0,0,0},0,actor,e)&&!actor);f.nullBirth=false;
  assert(!p.birth(two,f.generator(),0,{0,0,0},0,actor,e)&&!actor&&f.allocations==1);
  assert(p.birth(two,f.generator(),1,{0,0,0},0,actor,e)&&actor);assert(p.bind(two,actor,77,e)&&p.release(actor,77,e));
 }
 // A complete teardown permits fresh preparation and new associations on the
 // same provider; retired ticks and releases must never touch a fresh actor.
 {Fixture f;auto old=f.actor;assert(f.provider.release(old,77,f.e));assert(!f.provider.release(old,77,f.e));
  auto other=original;other.enemy.source=37;other.enemy.uid=999;other.sourceKey="other";
  assert(f.provider.preflight({original,other},f.e)&&f.provider.reserve({original,other},f.e));
  assert(f.provider.birth(original,f.engine.generator(),0,{5,10,15},1,f.actor,f.e)&&f.actor!=old);
  assert(f.provider.bind(original,f.actor,78,f.e));assert(!f.provider.tick(old,1,Event::None,f.e));
  assert(f.host().state==State::Stay&&f.host().spawnIndex==0&&!f.host().released&&near(f.host().timer,0));
  assert(near(f.engine.actorFacing,1));assert(f.provider.release(f.actor,78,f.e));
 }
 {Fixture f;assert(f.engine.reservedWisps==1&&f.engine.reservedEggs==1);assert(near(f.host().spawn[0].y,80));assert(near(f.host().spawn[1].x,-20)&&near(f.host().spawn[1].z,230));assert(f.engine.hidden&&!f.engine.atari&&f.engine.stopped&&f.engine.anim==3);assert(!f.provider.tick(f.actor,-1,Event::None,f.e));assert(!f.provider.tick(f.actor,std::numeric_limits<float>::quiet_NaN(),Event::None,f.e));
  assert(f.provider.flyingCollision(f.actor,true,f.e));assert(f.host().state==State::Stay);f.move();assert(f.engine.atari&&!f.engine.hidden);assert(f.provider.flyingCollision(f.actor,false,f.e));assert(f.host().state==State::Move);
  f.engine.p={10,80,230};f.tick(0);assert(f.host().state==State::Move);f.engine.p.z=230.1f;f.tick(0);assert(f.host().state==State::Disappear&&f.engine.anim==4);f.tick(0);assert(near(f.host().scale,.95f));f.tick(0,Event::End);assert(f.host().state==State::Stay&&f.host().spawnIndex==1);assert(near(f.host().facing,3.14159265f)&&near(f.engine.actorFacing,f.host().facing));assert(near(f.engine.p.x,-20)&&near(f.engine.p.y,80)&&near(f.engine.p.z,230));assert(f.engine.hidden&&near(f.host().scale,0));}
 {Fixture f;f.tick(1.1f);assert(f.host().state==State::Appear);f.tick(0);assert(near(f.host().scale,.05f));f.tick(0);assert(near(f.host().scale,.1f));f.tick(0,Event::End);assert(near(f.host().scale,1));f.tick(.2f);assert(near(f.host().pitch,.5f));assert(near(f.engine.vel.x,0)&&near(f.engine.vel.z,80));assert(near(f.engine.vel.y,2.5f*(60+20*std::sin(.5f)-80)));}
 {Fixture f;f.move();assert(f.provider.flyingCollision(f.actor,true,f.e));assert(f.host().state==State::Drop&&!f.engine.cullable&&f.engine.anim==1);f.tick(100);assert(f.host().state==State::Drop&&f.engine.releases==0);f.tick(0,Event::ReleaseEgg);assert(f.engine.releases==1&&f.engine.eggIndependent&&!f.host().egg);f.tick(0,Event::ReleaseEgg);assert(f.engine.releases==1);f.tick(0,Event::End);assert(f.host().state==State::Dead&&!f.engine.alive&&near(f.engine.vel.y,100)&&f.engine.anim==2);f.tick(1);assert(f.engine.kills==0);f.tick(.01f);assert(f.engine.kills==1);assert(f.provider.release(f.actor,77,f.e));assert(!f.provider.lookup(f.actor)&&f.engine.eggIndependent);assert(!f.provider.release(f.actor,77,f.e)&&f.engine.cleanups==1);}
 {Fixture f;f.move();assert(f.provider.flyingCollision(f.actor,true,f.e));f.tick(0,Event::ReleaseEgg);f.tick(0,Event::End);f.engine.isVisible=false;f.tick(0);assert(f.engine.kills==1);assert(!f.provider.release(f.actor,99,f.e));assert(f.provider.lookup(f.actor));assert(f.provider.release(f.actor,77,f.e));}
 // Native kill may synchronously invoke forget/release. Ensure tick returns
 // without using the erased Host and the released Egg survives that retirement.
 {Fixture f;f.move();assert(f.provider.flyingCollision(f.actor,true,f.e));f.tick(0,Event::ReleaseEgg);f.tick(0,Event::End);
  f.engine.onKill=[&](Host& h,std::string& error){auto* creature=h.creature;unsigned token=h.token;return f.provider.release(creature,token,error);};
  f.engine.isVisible=false;f.tick(0);assert(!f.provider.lookup(f.actor)&&f.engine.kills==1&&f.engine.cleanups==1&&f.engine.eggIndependent);
 }
 std::puts("P2_ORIGINAL_WISP_POLICY_PASS: literal tails, resources, events, flying collision, endpoints, scales, independent Egg contract; no gameplay claim");
}
