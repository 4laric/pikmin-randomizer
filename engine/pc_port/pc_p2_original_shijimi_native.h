#pragma once
#include "pc_p2_original_shijimi_group.h"
#include "pc_p2_original_shijimi_bank.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_original_resource_contents.h"
#include "pc_p2_shijimi_attachment.h"
#include <memory>
class BTeki;class Graphics;struct Matrix4f;
namespace p2originalresource { namespace honey { class Manager; } }
namespace p2original { namespace shijimi {
// The actual course/floor owner supplies source authority, continuous effects
// and its dynamic event ledger. These are not staged generator substitutes.
class Scene {
public:
 virtual ~Scene()=default;
 virtual bool parent(const InstanceIdentity&,unsigned,std::string&)=0;
 virtual bool emission(const Group&,std::string&)=0;
 virtual bool prepare(std::string&)=0; // genuine source77 FX + prepared real Honey
 virtual bool cave()const=0; // actual selected scene; source77 limits 10/25
 virtual bool culling(Creature*,bool sourceCullable,bool& culled,std::string&)=0;
 virtual void discardRand()=0; // same source RNG's raw rand() draw
 virtual bool born(Creature*,const Identity&,std::string&)=0;
 virtual bool retired(Creature*,const Identity&,std::string&)=0;
 virtual bool appear(Creature*,Color,std::string&)=0;
 virtual bool fade(Creature*,std::string&)=0;
 virtual bool latch(Creature*,Color,std::string&)=0; // Down restart + genuine Hit24
 virtual void forget(Creature*)=0;
};
// Transient capture from an actual owned source77 body. Piki native lifetimes
// authorize this read only; the durable reference codec excludes them.
struct GenPikiStickerCapture {
 Identity owner;
 std::vector<LiveGenPikiAttachment> stickers;
};
// Owns actual manager-allocated native bodies and their private geometry. The
// plant roots remain owned by foliage; parent cleanup never erases this journal.
class Native {
public:
 Native(Scene&,ActorRegistry&,p2originalresource::honey::Manager&,p2originalresource::Engine&);
 ~Native();
 bool prepare(std::string&);
 bool touched(Creature* actualPlant,unsigned source,const Position&,float sourceHeight,std::string&);
 bool tick(BTeki*,float seconds,std::string&);
 bool draw(BTeki*,Graphics&,const Matrix4f&);
 bool owns(const Creature*)const;
 // Relationship capture only; no cold allocation, stick FSM or SAVE admission.
 // Unsupported Bud/Onyon provenance refuses until their full branches exist.
 bool captureGenPikiAttachments(Creature*,const AttachmentAuthority&,GenPikiStickerCapture&,std::string&)const;
 bool collision(BTeki*,Creature*,std::string&);
 bool wall(BTeki*,const Position& normal,std::string&);
 bool consume(const p2originalresource::ChildIdentity&,std::string&);
 bool cleanup(std::string&);
 void forget(Creature*);
 PlantGroups& journal();
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
bool pc_p2_original_shijimi_owned(const Creature*);
bool pc_p2_original_shijimi_update(BTeki*);
bool pc_p2_original_shijimi_draw(BTeki*,Graphics&,const Matrix4f&);
bool pc_p2_original_shijimi_refresh(BTeki*,Graphics&);
bool pc_p2_original_shijimi_collision(BTeki*,Creature*);
bool pc_p2_original_shijimi_wall(BTeki*,float x,float y,float z);
void pc_p2_original_shijimi_forget(BTeki*);
