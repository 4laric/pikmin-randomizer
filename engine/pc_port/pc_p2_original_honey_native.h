#pragma once
#include "pc_p2_original_honey_snapshot.h"
#include "ObjectMgr.h"
#include <memory>
class Piki;class Navi;class Shape;class Graphics;class Creature;struct Matrix4f;
namespace p2originalresource { namespace honey {
class Actor;
HoneyKind kind(const Actor&);
const ChildIdentity& identity(const Actor&);
P2EggVec3 position(const Actor&);
float scale(const Actor&);
Phase phase(const Actor&);
bool actorWorld(const Actor&,Matrix4f&,std::string&);
Shape& shape(Actor&);
Creature& creature(Actor&);
struct Resources {
 Shape* sourceShape=nullptr;float gravity=0;bool collider=false;
 // Actual source motion IDs0,3,4,5,6 (not P1 Water animations).
 bool clips[7]{};
 // Actual P2 Piki MIZUNOMI/GROWUP1/GROWUP2 and Navi MIZUNOMI durations,
 // loop bounds and literal
 // authored source keys. Native P1 character motions are presentation only.
 ReceiverClip receiverClips[4];
};
class Services {
public:
 virtual ~Services()=default;
 virtual bool resources(Resources&,std::string&)=0;
 virtual bool receiversReady(std::string&)=0;
 // Start/advance actual converted Honey clip and key stream; pose writes only
 // this actor's private flattened source Shape. No synthetic half-clip events.
 virtual bool motion(Actor&,unsigned,std::string&)=0;
 virtual bool advance(Actor&,Shape&,float,std::vector<int>& keyEvents,std::string&)=0;
 // Actual source joint0 sphere centre at current mechanical source frame;
 // independent of render visibility. Source radius remains exactly15.
 virtual bool collisionCentre(const Actor&,P2EggVec3&,std::string&)=0;
 virtual void presentation(Actor&,const char*){} // deferred FX/sound/material
 virtual bool consumed(const ChildIdentity&,std::string&)=0;
 virtual bool captainIndex(Navi*,unsigned&,std::string&)=0;
 // At actual MIZUNOMI END, once per real captain absorption; same shrinking
 // child may serve both captains. The inventory owner dedupes child+captain.
 virtual bool sprayCompleted(const ChildIdentity&,unsigned,HoneyKind,std::string&)=0;
 virtual void camera(Navi*,bool){} // lock/unlock; optional near-low presentation
 // Exact source clip frame/loop/key frontier, supplied by the mechanical
 // animation backend. Restore must not execute birth/init RNG or past keys.
 virtual bool captureAnimation(const Actor&,std::string&,std::string&)=0;
 // Validate the complete prospective animation set before any body allocation.
 virtual bool validateAnimation(Phase,const std::string&,std::string&)=0;
 virtual bool restoreAnimation(Actor&,const std::string&,std::string&)=0;
 virtual void forget(Actor&){} // drop backend tracks before address reuse
};
class Manager final:public ObjectMgr {
public:
 explicit Manager(Services&);~Manager();
 bool preflight(std::string&);
 bool birth(HoneyKind,const ChildOutcome&,Engine& rng,Creature*& out,std::string&);
 bool contact(Creature* honey,Creature* collider,std::string&);
 bool absorb(Creature*,std::string&);
 bool start(Piki*,Creature* honey,std::string&);
 bool start(Navi*,Creature* honey,std::string&);
 // Call at real Piki/Navi forget before pool reuse; do not dereference after.
 void forget(Piki*);void forget(Navi*);
 bool cleanup(std::string&);
 bool snapshot(std::vector<Snapshot>&,std::string&)const;
 // Restore a complete private course before receivers/search/update run.
 // Active absorption/growth receivers must finish before this course snapshot.
 bool restore(const std::vector<Snapshot>&,Engine& rng,std::string&);
 Creature* getCreature(int)override;int getFirst()override;int getNext(int)override;bool isDone(int)override;
 int getSize()override;int getMax()override{return 24;}
 void update()override;void refresh(Graphics&)override;
 bool owns(const Creature*)const;
private:
 struct Impl;std::unique_ptr<Impl> m;
};
// Actor is an actual native Creature, with typed Honey semantics and an owned
// collider/shape. Its neutral P1 object ID cannot trigger WaterItem casts.
// Manager update/render/search must be connected by the original course owner.
} }
