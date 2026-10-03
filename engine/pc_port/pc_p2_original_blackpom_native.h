#pragma once
#include "pc_p2_original_actor.h"
#include "pc_p2_original_blackpom_policy.h"
#include <memory>
class Pom;
class Graphics;
class Creature;
class Piki;
class CollPart;
struct Vector3f;
namespace p2original { namespace blackpom {
// The Purple owner implements this adapter with the qualified ordinary bud
// mechanic. No conversion FSM or invented original GenPiki identity lives here.
class Mechanic {
public:
 virtual ~Mechanic()=default;
 virtual bool preflight(std::string&)=0;
 virtual bool bind(Pom*,const InstanceIdentity&,unsigned token,std::string&)=0;
 virtual bool start(Pom*,std::string&)=0;
 // Drop mechanic references only; Native/floor manager owns physical kill.
 virtual bool release(Pom*,std::string&)=0;
 // Actual mechanic motion/frame, independent of camera and render sampling.
 virtual bool pose(const Pom*,unsigned& motion,float& frame)const=0;
};
// Concrete adapter to the Purple owner's exported source6 core hooks. Requires
// that owner's source pin in the linked game; no alternate mechanic is created.
std::unique_ptr<Mechanic> coreMechanic();
class Native {
public:
 explicit Native(Mechanic&);
 ~Native();
 Native(const Native&)=delete;Native& operator=(const Native&)=delete;
 // Caller preloads BOSS_Pom manager capacity before constructBoss. This checks
 // actual resources/capacity without constructing or binding any game actor.
 bool prepare(unsigned,std::string&);
 bool birth(Generator*,const Vector3f&,float,const BirthContext&,Pom*&,bool& suppressed,std::string&);
 // Floor owner has already installed exact registry UID/ordinal/epoch/activation.
 bool bind(Pom*,unsigned,std::string&);
 bool release(Pom*,std::string&);
 // Actual native death callback only, after the registry owner retired its
 // handle and before BossMgr returns this root to its free pool. Does not kill.
 bool nativeRetired(Pom*,std::string&);
 // Abort unused reservations after the floor owner releases every partial root.
 bool cancel(std::string&);
 bool draw(Pom*,Graphics&);
 // Seven original collider parts, evaluated from every integer source BCA
 // frame. Part 1 is the authored slot/st__ receptor, radius30. Never P1 CollInfo.
 bool collider(const Pom*,unsigned part,Vector3f& center,float& radius)const;
 // Simulation update only: seats actual collider tree, independently of draw.
 bool follow(Pom*,std::string&);
 bool press(Pom*,Piki*,CollPart*,bool descending);
 void onDeath(std::function<bool(Pom*,std::string&)>);
 // Called after exact core binding and before start. The authoritative body/
 // SAVE consumer installs its actual donor snapshot and successful head hook.
 void onBind(std::function<bool(Pom*,const InstanceIdentity&,unsigned,std::string&)>);
 bool beforeKill(Pom*,std::string&);
 static Native* owner(const Creature*);
 bool owns(const Creature*)const;
 bool active(const Pom*)const;
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
struct PcOriginalBlackPomPress {bool handled=false,accepted=false;};
// Only actual managed source6; an owned rejected contact still blocks P1 stick.
PcOriginalBlackPomPress pc_p2_original_blackpom_flying_press(Creature*,Piki*,CollPart*,bool descending);
bool pc_p2_original_blackpom_update(Pom*);
bool pc_p2_original_blackpom_refresh(Pom*,Graphics&);
bool pc_p2_original_blackpom_collision(Pom*,Creature*);
bool pc_p2_original_blackpom_before_kill(Pom*);
