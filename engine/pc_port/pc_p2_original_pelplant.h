#pragma once
#include "pc_p2_original_catalog.h"
#include "pc_p2_original_group.h"
#include <array>
#include <map>
#include <memory>

class Creature;
class Generator;
class Pellet;

namespace p2original { namespace pelplant {
// Literal generator bytes, not P1 personality or pellet enum values.
struct Initial { unsigned color=0, amount=1, stage=0; };
bool decode(const CatalogRow&, Initial&, std::string&);
enum class State { Small, Middle, Full, GrowSmallMiddle, GrowMiddleFull,
                   Damage, Dead, WitherFull, WitherMiddle, WitherSmall };
enum class Event { None, End, LoopEnd, EndBlend, Other };
struct Parameters { float smallToMiddle=120, middleToFull=120, colorPeriod=1.5f, maxHealth=1; };
struct Resources {
 Parameters parameters;
 // All ten authored clips, capture/root/neck joints, scaled head collider,
 // and the requested number/color config must resolve in the native loader.
 std::array<bool,10> clips{};
 bool model=false, root=false, head=false, neck=false, collider=false;
 std::array<std::array<bool,3>,4> numberConfigs{};
};
struct Host {
 Creature* creature=nullptr;
 Generator* generator=nullptr;
 unsigned ordinal=0, token=0;
 CatalogRow row;
 Initial initial;
 std::string durableIdentity;
 Parameters parameters;
 State state=State::Small, previous=State::Full;
 Pellet* captured=nullptr;
 float health=1, damage=0, growthTime=0, colorTime=0;
 float lodRadius=45;
 int farmPower=0, actualColor=1;
 bool growing=true, dead=false, released=false;
 bool cullable=false;
};
// Native bridge: allocation is a real manager-owned creature with the family
// update/damage/render hooks installed, never a bare P1 Palm with its AI active.
// Capture disables collision/carry and follows the authored head matrix;
// release reverses that SAME pellet's capture. No synthetic delivery callback.
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool resources(Resources&,std::string&)=0;
 virtual bool commonResources(const CatalogRow&,std::string&)=0;
 virtual bool identity(Host&,std::string& durable,std::string& error)=0;
 virtual bool reserve(unsigned actors,const std::array<unsigned,4>& pellets,std::string&)=0;
 virtual bool allocate(Host&,const Position&,float radians,std::string&)=0;
 virtual bool captureNumber(Host&,unsigned amount,int color,Pellet*&,std::string&)=0;
 virtual bool pelletColor(Pellet*,int,std::string&)=0;
 virtual bool metColor(unsigned)const=0;
 virtual bool motion(Host&,unsigned animation,bool blend,std::string&)=0;
 virtual bool flags(Host&,bool vulnerable,bool living,bool cullable,float lod,std::string&)=0;
 virtual bool flick(Host&,std::string&)=0;
 virtual bool deathProcedure(Host&,std::string&)=0;
 virtual bool endCapture(Host&,Pellet*,std::string&)=0;
 virtual bool killPlant(Host&,std::string&)=0;
 // Destroys only still-captured owned cargo, listeners, collider and creature.
 // Already released ordinary cargo is not owned by the plant anymore.
 virtual bool cleanup(Host&,std::string&)=0;
};
class Provider : public GroupProvider {
public:
 explicit Provider(Engine& engine):mEngine(engine){}
 Provider(const Provider&)=delete;
 Provider& operator=(const Provider&)=delete;
 bool preflight(const std::vector<CatalogRow>&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,std::string&) override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&) override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&) override;
 bool release(Creature*,unsigned,std::string&) override;
 Host* lookup(Creature*);
 bool tick(Creature*,float,Event,std::string&);
 bool damage(Creature*,float,const char special[4],std::string&);
 bool farm(Creature*,int,std::string&);
 bool stick(Creature*,const char special[4],std::string&);
 // Called by ordinary Onion delivery before the pellet is forgotten. This
 // only observes exact native cargo identity; it does not award population.
 bool onion(Pellet*,unsigned& token,bool& duplicate,std::string* durableIdentity=nullptr);
 void forgetPellet(Pellet*);
 std::size_t size()const{return mHosts.size();}
private:
 struct Cargo {unsigned token; bool delivered=false;std::string identity;};
 Engine& mEngine;
 Resources mResources;
 std::map<Creature*,std::unique_ptr<Host>> mHosts;
 std::map<Pellet*,Cargo> mCargo;
 std::map<unsigned,CatalogRow> mAdmitted;
 std::map<unsigned,unsigned> mRemaining;
 bool mPrepared=false,mReserved=false;
 bool enter(Host&,State,std::string&);
 bool attach(Host&,std::string&);
 bool color(Host&,float,std::string&);
};
} }
