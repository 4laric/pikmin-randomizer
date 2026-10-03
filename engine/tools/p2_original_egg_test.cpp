#include "pc_p2_original_egg.h"
#include <cassert>
#include <iostream>
using namespace p2original;
struct Fake:egg::Engine {
 unsigned field=0,dependencies=0,next=10,updates=0,restarts=0,resumes=0;
 bool drop=false,nullBirth=false,cleanupFail=false,contentsFail=false;
 std::string sequence;
 egg::Provider* retirement=nullptr;
 bool retireInUpdate=false;
 bool resources(egg::Resources& r,std::string&)override{r.parameters.health=50;r.parametersLoaded=r.model=r.collider=r.motion=r.contents=r.breakEffects=r.capture=true;return true;}
 bool commonResources(const CatalogRow&,std::string&)override{return true;}
 bool reserve(unsigned n,std::string&)override{field=n;return true;}
 bool reserveCaptured(unsigned n,std::string&)override{dependencies=n;return true;}
 bool allocate(egg::Host& h,const Position&,float,std::string&)override{h.creature=nullBirth?nullptr:reinterpret_cast<Creature*>(std::uintptr_t(next++));return true;}
 bool initialize(egg::Host& h,std::string&)override{h.dropGroup=drop;return true;}
 bool flags(egg::Host&,const egg::Flags&,std::string&)override{return true;}
 bool motion(egg::Host&,bool restart,bool stopped,std::string&)override{if(restart&&stopped)++restarts;else if(!restart&&!stopped)++resumes;return true;}
 bool capturedIdentity(Creature* p,std::string& s,std::string&)override{s="source16:epoch3:ordinal"+std::to_string(std::uintptr_t(p))+":cargo0";return true;}
 bool startCapture(egg::Host&,Creature*,void*,std::string&)override{return true;}
 bool endCapture(egg::Host&,std::string&)override{return true;}
 bool update(egg::Host& h,float,std::string& e)override{++updates;return retireInUpdate&&retirement?retirement->release(h.creature,h.token,e):true;}
 bool contents(egg::Host&,std::string& e)override{if(contentsFail){e="injected contents refusal";return false;}sequence+='C';return true;}
 bool breakEffects(egg::Host&,std::string&)override{sequence+='E';return true;}
 bool kill(egg::Host& h,std::string& e)override{sequence+='K';return retirement?retirement->release(h.creature,h.token,e):true;}
 bool cleanup(egg::Host&,std::string& e)override{if(cleanupFail){e="injected cleanup failure";return false;}return true;}
};
CatalogRow row(){CatalogRow r;r.enemy.source=37;r.enemy.uid=7;r.enemy.count=3;r.sourceKey="forest/egg";return r;}
Creature* birth(egg::Provider& p,const CatalogRow& r,std::string& e,unsigned ordinal=0,unsigned token=1){Creature* c=nullptr;assert(p.birth(r,reinterpret_cast<Generator*>(1),ordinal,{},0,c,e));assert(c&&p.bind(r,c,token,e));return c;}
int main(){
 std::string e;Fake f;egg::Provider p(f);auto r=row();assert(egg::decode(r,e));auto bad=r;bad.enemy.generatorVersion="0000";assert(!egg::decode(bad,e));bad=r;bad.enemy.generatorTail={"0"};assert(!egg::decode(bad,e));
 assert(p.preflight({r},e));bad=r;bad.enemy.pelletProbability=1;assert(!p.reserve({bad},e));assert(p.reserve({r},e)&&f.field==3);assert(p.reserveCaptured(2,e)&&f.dependencies==2);
 Creature* c=birth(p,r,e);auto* h=p.lookup(c);assert(h->health==50&&h->flags.constrained&&!h->flags.invulnerable);
 assert(p.bounce(c,e)&&h->health==50);assert(p.collision(c,reinterpret_cast<Creature*>(2),false,e)&&h->health==50);assert(!p.press(c,e)&&h->health==50);
 assert(p.damage(c,10,1,e)&&h->health==40);assert(p.tick(c,0,egg::Event::None,e)&&f.resumes==1&&h->flickTimer==0);
 assert(p.tick(c,0,egg::Event::End,e)&&f.restarts==2);assert(p.damage(c,100,0,e)&&h->health==0);
 f.contentsFail=true;assert(!p.tick(c,0,egg::Event::None,e)&&f.sequence.empty());f.contentsFail=false;
 assert(p.tick(c,0,egg::Event::None,e)&&f.sequence=="CEK");assert(!p.release(c,2,e));f.cleanupFail=true;assert(!p.release(c,1,e)&&p.lookup(c));f.cleanupFail=false;assert(p.release(c,1,e));
 Creature* dependent=nullptr;auto parent=reinterpret_cast<Creature*>(20);
 assert(!p.attach(parent,nullptr,{},0,dependent,e));assert(p.attach(parent,&f,{},0,dependent,e));h=p.lookup(dependent);
 assert(h->dependent&&!h->generator&&!h->token&&!h->dependentIdentity.empty()&&h->captured&&!h->flags.living&&!h->flags.cullable&&h->flags.invulnerable);
 assert(p.damage(dependent,100,1,e)&&h->health==50&&h->flickTimer==0);Creature* duplicate=nullptr;assert(!p.attach(parent,&f,{},0,duplicate,e));
 assert(p.detach(dependent,e)&&!h->captured&&!h->parent&&h->falling&&h->flags.living&&h->flags.invulnerable&&!h->flags.constrained);
 assert(p.tick(dependent,0.1f,egg::Event::None,e)&&h->health==50);assert(p.bounce(dependent,e)&&h->health==0&&h->flags.lifeGauge);
 f.sequence.clear();assert(p.tick(dependent,0,egg::Event::None,e)&&f.sequence=="CEK");assert(p.release(dependent,0,e));
 assert(!p.birth(r,reinterpret_cast<Generator*>(99),0,{},0,c,e));
 assert(p.preflight({r},e)&&p.reserve({r},e));c=birth(p,r,e);assert(p.release(c,1,e));
 Fake dropping;dropping.drop=true;egg::Provider dp(dropping);assert(dp.preflight({r},e)&&dp.reserve({r},e));c=birth(dp,r,e);h=dp.lookup(c);assert(!h->flags.constrained);
 assert(dp.collision(c,reinterpret_cast<Creature*>(3),true,e)&&h->health==50);assert(dp.collision(c,nullptr,false,e)&&h->health==50);
 assert(dp.collision(c,reinterpret_cast<Creature*>(3),false,e)&&h->health==0);assert(dp.tick(c,0,egg::Event::None,e)&&dropping.sequence=="CEK");assert(dp.release(c,1,e));
 Fake null;null.nullBirth=true;egg::Provider np(null);assert(np.preflight({r},e)&&np.reserve({r},e));c=reinterpret_cast<Creature*>(4);assert(np.birth(r,reinterpret_cast<Generator*>(1),0,{},0,c,e)&&!c);
 assert(!np.birth(r,reinterpret_cast<Generator*>(2),0,{},0,c,e));
 // Native kill can synchronously remove the provider Host. No read after kill.
 Fake synchronous;egg::Provider sp(synchronous);synchronous.retirement=&sp;assert(sp.preflight({r},e)&&sp.reserve({r},e));c=birth(sp,r,e);
 assert(sp.damage(c,100,0,e)&&sp.tick(c,0,egg::Event::None,e)&&sp.size()==0&&synchronous.sequence=="CEK");
 Fake physics;egg::Provider pp(physics);physics.retirement=&pp;physics.retireInUpdate=true;assert(pp.preflight({r},e)&&pp.reserve({r},e));c=birth(pp,r,e);
 assert(pp.tick(c,0.1f,egg::Event::None,e)&&pp.size()==0&&physics.sequence.empty());
 std::cout<<"Original Egg source lifecycle policy checks passed (fake engine; no gameplay claim)\n";
}
