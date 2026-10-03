#pragma once
#include "pc_p2_original_catalog.h"
#include <array>
#include <map>
#include <string>
#include <vector>

namespace p2original { namespace shijimi {
enum class Color : unsigned { Yellow=0, Red=1, Purple=2 };
// A dynamic actor is a descendant, never an invented source generator record.
struct Identity {
 InstanceIdentity plant;
 unsigned emission=0, child=0;
 bool operator==(const Identity& b)const{return plant==b.plant&&emission==b.emission&&child==b.child;}
};
struct Child {
 Identity identity;
 Position position,home;
 float facing=0;
 Color color=Color::Yellow,appearance=Color::Yellow;
 bool attempted=false,born=false,initialized=false,retired=false;
 bool dropAttempted=false,dropComplete=false,dropBorn=false,dropConsumed=false;
};
struct Group {
 InstanceIdentity plant;
 unsigned plantSource=0;
 Position origin;
 bool consumed=false,complete=false,managerPresent=false;
 // Source mGroupCount is the last successful loop index, NOT survivor count.
 unsigned sourceGroupCount=0;
 std::array<Child,5> children;
};
class Engine {
public:
 virtual ~Engine()=default;
 // Consult the independent original registry/catalog, not a saved self-claim.
 virtual bool parent(const InstanceIdentity&,unsigned source,std::string&)=0;
 // Independent SourceCatalog/floor authority must check the parent's literal
 // sentinel fields and actual birth origin (including its own source fp27).
 // This must also work for a retired/absent parent in a selected saved graph.
 virtual bool emission(const Group&,std::string&)=0;
 virtual bool managerAvailable()const=0;
 virtual float randFloat()=0;
 virtual void discardRand()=0; // literal rand() in createGroup, even unused
 // Raw manager allocation executes EnemyBase::birth/setParameters (scale RNG).
 // A null object is an ordinary allocation failure and consumes no init RNG.
 virtual bool birth(Child&,void*& object,std::string&)=0;
 // Real onInit/StateWait consumes pitch and motion-frame RNG from this Engine.
 // Sets group leader/home/flyType BEFORE init, source Plants AFTER leader init.
 virtual bool init(Child&,void* object,void* leader,std::string&)=0;
 virtual bool leaderInit(Child&,void* object,std::string&)=0;
 virtual bool leaderColor(Child&,void* object,std::string&)=0;
 // Called before the follower is forced yellow and before its onInit.
 virtual bool appear(Child&,void* object,std::string&)=0;
 // Infrastructure failure is distinct from a source null birth. Retire all
 // native allocations belonging to this emission, including half-init bodies.
 virtual bool abort(const Group&,std::string&)=0;
 virtual bool sprayMade(Color)const=0;
 virtual bool honey(const Child&,const Position& position,const Position& velocity,
                    bool& born,std::string&)=0;
};
class PlantGroups {
public:
 // Invoke only from a real inactive Plants touched() with literal color0/size1.
 // Consumes the sentinel BEFORE manager lookup; source permits partial births.
 bool touch(const InstanceIdentity&,unsigned source,const Position& plant,float lifeMeterHeight,
            Engine&,Group&,std::string&);
 // Real Dead END or bitter landing only. Plant provenance short-circuits the
 // nectar-rate roll. Honey init(nullptr) and its RNG belong to real factory.
 bool drop(const Identity&,const Position&,float facing,bool inPiklopedia,
           Engine&,std::string&);
 bool retire(const Identity&,std::string&);
 bool consume(const Identity&,std::string&);
 std::vector<Group> snapshot()const;
 // Logical emission journal only; restoring physical FSM bodies requires the
 // separate no-init native checkpoint provider. This never births or rolls RNG.
 bool restore(const std::vector<Group>&,Engine&,std::string&);
 bool encode(Engine&,std::string& bytes,std::string&);
 bool decode(const std::string& bytes,Engine&,std::string&);
private:
 std::map<InstanceIdentity,Group> mGroups;
 Child* find(const Identity&);
};
} }
