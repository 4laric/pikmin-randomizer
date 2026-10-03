#include "pc_p2_original_egg_snapshot.h"
#include <cmath>
namespace p2original { namespace egg { namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool hex(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
bool same(const p2originalresource::SourceIdentity& a,const p2originalresource::SourceIdentity& b){return a.fingerprint==b.fingerprint&&a.uid==b.uid&&a.ordinal==b.ordinal&&a.epoch==b.epoch&&a.activation==b.activation;}
bool valid(const p2originalresource::SourceIdentity& id){return hex(id.fingerprint)&&(id.uid&0xff000000u)==0x52000000u&&id.ordinal<10&&id.epoch&&id.activation;}
bool finite(Position p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
bool empty(const p2originalresource::SourceIdentity& id){return id.fingerprint.empty()&&!id.uid&&!id.ordinal&&!id.epoch&&!id.activation;}
}
bool validateSnapshot(const Snapshot& s,const SnapshotContext& c,std::string& e){
 if(!valid(s.identity)||!valid(c.identity)||!same(s.identity,c.identity))return fail(e,"Egg snapshot requires exact authenticated source incarnation");
 if(!hex(s.resourceFingerprint)||!hex(c.resourceFingerprint)||s.resourceFingerprint!=c.resourceFingerprint)return fail(e,"Egg snapshot source bank/pose resources changed");
 if(!std::isfinite(c.maxHealth)||c.maxHealth<=0||s.state!=0||s.dependent!=c.dependent||s.dropGroup!=c.dropGroup)return fail(e,"Egg snapshot source class/FSM/dropgroup differs from bound body");
 if(!finite(s.position)||!finite(s.velocity)||!finite(s.targetVelocity)||!finite(s.scale)||s.scale.x<=0||s.scale.y<=0||s.scale.z<=0
  ||!std::isfinite(s.facing)||!std::isfinite(s.health)||s.health<0||s.health>c.maxHealth||!std::isfinite(s.flickTimer)||s.flickTimer<0
  ||!std::isfinite(s.sourceFrame)||s.sourceFrame<0||s.sourceFrame>30)return fail(e,"Egg snapshot physical health/animation state invalid");
 if(s.flags.leaveCarcass||s.flags.damageAnimation||s.flags.deathEffect||!s.flags.bitterImmune)return fail(e,"Egg snapshot source immutable flags changed");
 if((s.contentsGenerated||s.effectsEmitted||s.killRequested)&&s.health!=0)return fail(e,"Egg snapshot destruction progress without zero health");
 if((s.effectsEmitted&&!s.contentsGenerated)||(s.killRequested&&!s.effectsEmitted))return fail(e,"Egg snapshot source destruction ordering invalid");
 if(s.captured){
  if(!s.dependent||!s.hasParent||!valid(s.parentIdentity)||!same(s.identity,s.parentIdentity)||!c.actualCaptureBound||!same(s.parentIdentity,c.actualParent)
   ||s.falling||s.dropGroup||!s.flags.constrained||!s.flags.invulnerable||s.flags.cullable||s.flags.living)
   return fail(e,"Egg snapshot capture requires exact already-bound parent/matrix graph");
  if(!finite(c.capturePosition)||s.position.x!=c.capturePosition.x||s.position.y!=c.capturePosition.y||s.position.z!=c.capturePosition.z
   ||s.velocity.x||s.velocity.y||s.velocity.z||s.targetVelocity.x||s.targetVelocity.y||s.targetVelocity.z)
   return fail(e,"Egg snapshot capture transform does not match already-restored authored matrix");
 }else {
  if(s.hasParent||!empty(s.parentIdentity)||c.actualCaptureBound)return fail(e,"Egg snapshot independent body has a capture graph link");
  if(!s.flags.living||!s.flags.cullable)return fail(e,"Egg snapshot independent living/culling flags invalid");
  if(s.dependent){if(!s.falling||s.dropGroup||s.flags.constrained||!s.flags.invulnerable)return fail(e,"Egg snapshot released source cargo flags invalid");}
  else if(s.falling||s.flags.constrained==s.dropGroup||s.flags.invulnerable)return fail(e,"Egg snapshot standalone constraint/dropgroup flags invalid");
 }
 e.clear();return true;
}
} }
