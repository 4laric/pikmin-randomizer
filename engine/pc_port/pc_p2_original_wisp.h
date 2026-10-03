#pragma once
#include "pc_p2_original_group.h"
#include <array>
#include <memory>
#include <set>

namespace p2original { namespace wisp {
// QurioneMgr.cpp literal 0000 generator extension, not a host personality.
struct Initial { float fly=200, slide=30; };
bool decode(const CatalogRow&,Initial&,std::string&);
enum class State { Stay, Appear, Disappear, Move, Drop, Dead };
enum class Event { None, ReleaseEgg, End };
struct Parameters {
 float flightHeight=0,pitchRate=0,pitchAmplitude=0,deathRate=0,deathTime=0;
 float moveSpeed=0,viewAngle=0,sightRadius=0,health=0;
};
struct Resources {
 Parameters parameters;
 bool model=false,collider=false,waterJoint=false,glowJoint=false,egg=false;
 std::array<bool,5> motions{};
};
struct Host {
 Creature* creature=nullptr; Generator* generator=nullptr; Creature* egg=nullptr;
 CatalogRow row; Initial initial; Parameters parameters;
 unsigned ordinal=0,token=0,spawnIndex=0;
 State state=State::Stay;
 Position spawn[2]; float facing=0,pitch=0,timer=0,scale=0;
 bool released=false,dead=false;
};
// Each native operation below must act on the actual owned creature. Capture
// follows the authored water joint; release leaves the SAME Egg in its manager,
// independently updated after the Honeywisp ascends/retire. No policy-only egg.
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool resources(Resources&,std::string&)=0;
 virtual bool reserve(unsigned wisps,unsigned capturedEggs,std::string&)=0;
 virtual bool allocate(Host&,const Position&,float,std::string&)=0;
 virtual bool attachEgg(Host&,Creature*&,std::string&)=0;
 virtual bool setPosition(Host&,const Position&,std::string&)=0;
 virtual bool facing(Host&,float,std::string&)=0;
 virtual bool flags(Host&,bool atari,bool hidden,bool cullable,bool alive,std::string&)=0;
 virtual bool motion(Host&,unsigned animation,bool stopped,std::string&)=0;
 virtual bool effect(Host&,const char* operation,std::string&)=0;
 virtual bool appear(const Host&,bool&,std::string&)=0;
 virtual bool visible(const Host&,bool&,std::string&)=0;
 virtual bool position(const Host&,Position&,std::string&)=0;
 virtual bool floor(const Position&,float&,std::string&)=0;
 virtual bool velocity(Host&,const Position&,std::string&)=0;
 virtual bool releaseEgg(Host&,Creature*,std::string&)=0;
 // May synchronously retire this Host. Caller never dereferences it afterward.
 virtual bool kill(Host&,std::string&)=0;
 virtual bool cleanup(Host&,std::string&)=0;
};
class Provider final:public GroupProvider {
public:
 explicit Provider(Engine& engine):mEngine(engine){}
 bool preflight(const std::vector<CatalogRow>&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,std::string&) override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&) override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&) override;
 bool release(Creature*,unsigned,std::string&) override;
 void retiredNative(Creature*);
 bool tick(Creature*,float,Event,std::string&);
 // Only an actual flying-Pikmin collision in Move triggers Drop.
 bool flyingCollision(Creature*,bool isPikmin,std::string&);
 Host* lookup(Creature*);
private:
 Engine& mEngine; Resources mResources;
 std::map<unsigned,CatalogRow> mAdmitted;
 std::map<unsigned,unsigned> mRemaining;
 std::map<Creature*,std::unique_ptr<Host>> mHosts;
 std::set<std::pair<unsigned,unsigned>> mUsed;
 bool mPrepared=false,mReserved=false;
 bool enter(Host&,State,std::string&);
};
} }
