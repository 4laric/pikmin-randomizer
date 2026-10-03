#pragma once
#include "pc_p2_original_wisp.h"
#include "pc_p2_original_wisp_clock.h"
#include "pc_p2_original_resource_contents.h"
namespace p2original { namespace wisp {
struct Snapshot {
 InstanceIdentity identity;
 State state=State::Stay;unsigned spawnIndex=0,motion=3;
 Position spawn[2],position,velocity,targetVelocity;
 float facing=0,pitch=0,timer=0,scale=0;
 bool atari=false,hidden=true,cullable=true,alive=true,dead=false;
 Clock clock{0,0,true,false};
 // Parent incarnation plus cargo slot0 is durable; an existing independent
 // released Egg may already have broken/consumed. Never persist its pointer.
 p2originalresource::SourceIdentity cargo;
 unsigned cargoSlot=0; // typed captured Egg dependency; Qurione owns exactly slot0
 bool eggBorn=false,released=false;
};
inline bool validateSnapshot(const Snapshot& s,const Initial& initial,int duration,const std::vector<Key>& keys,std::string& e){
 auto fail=[&](const char* text){e=text;return false;};
 for(float v:{s.spawn[0].x,s.spawn[0].y,s.spawn[0].z,s.spawn[1].x,s.spawn[1].y,s.spawn[1].z,s.position.x,s.position.y,s.position.z,s.velocity.x,s.velocity.y,s.velocity.z,s.targetVelocity.x,s.targetVelocity.y,s.targetVelocity.z,s.facing,s.pitch,s.timer,s.scale,s.clock.frame})if(!std::isfinite(v))return fail("Honeywisp checkpoint contains nonfinite physical state");
 unsigned expected=0;switch(s.state){case State::Stay:case State::Appear:expected=3;break;case State::Disappear:expected=4;break;case State::Move:expected=0;break;case State::Drop:expected=1;break;case State::Dead:expected=2;break;default:return fail("Honeywisp checkpoint source FSM invalid");}
 if(s.motion!=expected||s.spawnIndex>1||duration<1||s.clock.frame<0||s.clock.frame>=duration||s.clock.next>keys.size()||s.timer<0||s.scale<0||s.scale>1||s.pitch<0)return fail("Honeywisp checkpoint authored state/clock bounds invalid");
 if(s.clock.completed||s.clock.stopped!=(s.state==State::Stay))return fail("Honeywisp checkpoint clock is not a stable source FSM boundary");
 unsigned frontier=0;while(frontier<keys.size()&&keys[frontier].frame<int(s.clock.frame))++frontier;
 if(s.clock.next!=frontier)return fail("Honeywisp checkpoint authored key frontier invalid");
 bool dead=s.state==State::Dead,stay=s.state==State::Stay;
 bool atari=s.state==State::Move||s.state==State::Drop||dead;
 bool cullable=s.state!=State::Drop&&!dead;
 if(s.dead!=dead||s.alive==dead||s.hidden!=stay||s.atari!=atari||s.cullable!=cullable)return fail("Honeywisp checkpoint source event flags invalid");
 if((s.state!=State::Move&&!dead&&(s.targetVelocity.x!=0||s.targetVelocity.y!=0||s.targetVelocity.z!=0))||(s.state==State::Move&&s.targetVelocity.y!=0))return fail("Honeywisp checkpoint source target velocity invalid");
 // A single large source step can cross release and END together; the source
 // listener retains only END and the Dead state then still carries its Egg.
 if((s.released&&s.state!=State::Drop&&!dead)||(stay&&(s.scale!=0||s.clock.frame!=0||s.clock.next!=0))||(s.state==State::Move&&s.scale!=1))return fail("Honeywisp checkpoint lifecycle/release state invalid");
 if(s.cargoSlot!=0||s.identity.catalog.empty()||!s.identity.generator||!s.identity.activation||s.cargo.fingerprint!=s.identity.catalog||s.cargo.uid!=s.identity.generator||s.cargo.ordinal!=s.identity.ordinal||s.cargo.epoch!=s.identity.epoch||s.cargo.activation!=s.identity.activation)return fail("Honeywisp checkpoint cargo differs from full parent incarnation");
 // Face reverses precisely once per endpoint switch. Saved endpoints must
 // encode the literal tail flight/slide geometry, not an arbitrary new route.
 const float pi=3.14159265358979323846f;
 float birthFace=s.facing-(s.spawnIndex?pi:0);
 float dx=initial.fly*std::sin(birthFace)+initial.slide*std::sin(birthFace-pi/2);
 float dz=initial.fly*std::cos(birthFace)+initial.slide*std::cos(birthFace-pi/2);
 if(std::fabs((s.spawn[1].x-s.spawn[0].x)-dx)>.01f||std::fabs((s.spawn[1].z-s.spawn[0].z)-dz)>.01f||s.spawn[1].y!=s.spawn[0].y)return fail("Honeywisp checkpoint literal source endpoint geometry invalid");
 e.clear();return true;
}
} }
