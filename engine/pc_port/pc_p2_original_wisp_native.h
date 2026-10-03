#pragma once
#include "pc_p2_original_wisp.h"
#include "pc_p2_original_resource_contents.h"
#include "pc_p2_original_wisp_snapshot.h"
#include <functional>
class BTeki;class Graphics;struct Matrix4f;struct CollEvent;
namespace p2original { namespace wisp {
class Services {
public:
 virtual ~Services()=default;
 virtual bool eggResources(std::string&)=0;
 virtual bool reserveEggs(unsigned,std::string&)=0;
 virtual bool attachEgg(Creature* parent,void* actualWaterMatrix,const Position&,float,Creature*&,std::string&)=0;
 virtual bool detachEgg(Creature*,std::string&)=0;
 virtual bool destroyCapturedEgg(Creature*,std::string&)=0;
 // Birth-context owner supplies epoch/activation before registry bind. The
 // returned identity is authoritative source incarnation plus cargo ordinal.
 virtual bool capturedEpochIdentity(const CatalogRow&,Generator*,unsigned,p2originalresource::SourceIdentity&,std::string&)=0;
 // Read-only graph resolver. Carried cargo must ALREADY use this real parent's
 // water matrix. Released cargo, if still live, must be independent; null is
 // valid only when the graph owns a terminal source outcome. Never attach here.
 virtual bool checkpointEgg(const p2originalresource::SourceIdentity&,bool born,bool released,Creature* parent,void* water,Creature*& out,std::string& e){(void)born;(void)released;(void)parent;(void)water;out=nullptr;e="Honeywisp typed Egg checkpoint graph resolver unavailable";return false;}
 // Deferred source presentation is explicit; mechanics never use substitutes.
 virtual bool presentationReady()const{return false;}
 virtual bool effect(Creature*,const char*,float,const Matrix4f&,std::string&){return true;}
};
class Native {
public:
 explicit Native(Services&);~Native();
 Native(const Native&)=delete;Native& operator=(const Native&)=delete;
 Provider& provider();bool owns(const Creature*)const;
 bool tick(BTeki*,float,std::string&);
 bool draw(BTeki*,Graphics&,const Matrix4f&,std::string&);
 bool flyingCollision(BTeki*,Creature*,std::string&);
 bool capturedIdentity(Creature* parent,std::string&,std::string&)const;
 bool capturedSourceIdentity(Creature* parent,p2originalresource::SourceIdentity&,std::string&)const;
 bool snapshot(BTeki*,Snapshot&,std::string&)const;
 bool preflightRestore(BTeki*,const Snapshot&,std::string&)const;
 // Caller preflights the complete graph first and serializes its apply phase.
 // Resolves no new bodies; never invokes birth/release/contents/death/RNG.
 bool applyRestore(BTeki*,const Snapshot&,std::string&);
 void forget(BTeki*);
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
// Caller integration must suppress ordinary host AI/damage/collision for owned
// carriers. This collision entry accepts only actual PIKISTATE_Flying contacts.
bool pc_p2_original_wisp_update(BTeki*);
bool pc_p2_original_wisp_refresh(BTeki*,Graphics&);
bool pc_p2_original_wisp_collision(BTeki*,Creature* collider);
bool pc_p2_original_wisp_owns(const BTeki*);
void pc_p2_original_wisp_forget(BTeki*);
