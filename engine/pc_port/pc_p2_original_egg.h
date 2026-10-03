#pragma once
#include "pc_p2_original_group.h"
#include <memory>
#include <set>
namespace p2original { namespace egg {
enum class Event { None, End, Other };
struct Parameters {float health=0;};
struct Resources {
 Parameters parameters;bool parametersLoaded=false,model=false,collider=false,motion=false;
 bool contents=false,breakEffects=false,capture=false;
};
struct Flags {
 bool leaveCarcass=false,damageAnimation=false,deathEffect=false,bitterImmune=true;
 bool constrained=false,invulnerable=false,cullable=true,living=true,lifeGauge=false;
};
struct Host {
 Creature* creature=nullptr;Generator* generator=nullptr;Creature* parent=nullptr;
 CatalogRow row;unsigned ordinal=0,token=0;std::string dependentIdentity;
 Parameters parameters;Flags flags;float health=0,flickTimer=0;
 bool dependent=false,captured=false,falling=false,dropGroup=false;
 bool contentsGenerated=false,effectsEmitted=false,killRequested=false;
};
bool decode(const CatalogRow&,std::string&);
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool resources(Resources&,std::string&)=0;
 virtual bool commonResources(const CatalogRow&,std::string&)=0;
 virtual bool reserve(unsigned fieldEggs,std::string&)=0;
 virtual bool reserveCaptured(unsigned dependencyEggs,std::string&)=0;
 // Success/null is a source manager null birth. Allocate installs actual hooks.
 virtual bool allocate(Host&,const Position&,float facing,std::string&)=0;
 // Base init; determine actual source DropGroup. Ground (non-DropGroup) init
 // projects floor from position.y+20, stops authored damage1 clip and evaluates
 // the real model/collider immediately. Never infer AP personality flags.
 virtual bool initialize(Host&,std::string&)=0;
 virtual bool flags(Host&,const Flags&,std::string&)=0;
 virtual bool motion(Host&,bool restart,bool stopped,std::string&)=0;
 // Derive from authoritative parent's source incarnation + cargo ordinal;
 // disjoint from standalone source37 identity. No pointer-based persisted ID.
 virtual bool capturedIdentity(Creature* parent,std::string&,std::string&)=0;
 virtual bool startCapture(Host&,Creature* parent,void* actualMatrix,std::string&)=0;
 virtual bool endCapture(Host&,std::string&)=0;
 // Real Egg doUpdate target velocity (zero on floor; current otherwise),
 // captured simulation/matrix/collider synchronization and normal physics.
 virtual bool update(Host&,float,std::string&)=0;
 // Source genItem RNG/forced/drop/demo checks and actual manager births.
 // Delegated to the owned resource module; null source births stay null.
 virtual bool contents(Host&,std::string&)=0;
 virtual bool breakEffects(Host&,std::string&)=0;
 // Actual kill informs original generator and may synchronously retire Host.
 virtual bool kill(Host&,std::string&)=0;
 // Captured cargo cleanup never destroys independently released contents.
 virtual bool cleanup(Host&,std::string&)=0;
};
class Provider final:public GroupProvider {
public:
 explicit Provider(Engine& e):mEngine(e){}
 bool preflight(const std::vector<CatalogRow>&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,std::string&) override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&) override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&) override;
 bool release(Creature*,unsigned,std::string&) override;
 void retiredNative(Creature*);
 bool reserveCaptured(unsigned,std::string&);
 bool attach(Creature* parent,void* captureMatrix,const Position&,float,Creature*&,std::string&);
 // Release capture ownership, retain provider/manager ownership. Parent teardown
 // must not kill this Egg after detach; it has its own update/kill lifetime.
 bool detach(Creature*,std::string&);
 Host* lookup(Creature*);
 bool tick(Creature*,float,Event,std::string&);
 bool damage(Creature*,float,float flickSpeed,std::string&);
 bool press(Creature*,std::string&);
 bool bounce(Creature*,std::string&);
 bool collision(Creature*,Creature* other,bool isTeki,std::string&);
 std::size_t size()const{return mHosts.size();}
private:
 Engine& mEngine;Resources mResources;
 std::map<unsigned,CatalogRow> mAdmitted;std::map<unsigned,unsigned> mRemaining;
 std::map<Creature*,std::unique_ptr<Host>> mHosts;
 std::set<std::pair<unsigned,unsigned>> mUsed;std::set<std::string> mDependentUsed;
 unsigned mCapturedRemaining=0;bool mPrepared=false,mReserved=false;
 bool init(Host&,std::string&);
 bool breakOnContact(Host&,std::string&);
};
} }
