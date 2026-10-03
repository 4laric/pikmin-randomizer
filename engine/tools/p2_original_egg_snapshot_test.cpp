#include "pc_p2_original_egg_snapshot.h"
#include <cassert>
#include <limits>
#include <iostream>
using namespace p2original;
int main(){
 std::string e;egg::SnapshotContext c;c.identity={std::string(64,'a'),0x52000010u,1,2,3};c.resourceFingerprint=std::string(64,'b');c.maxHealth=50;
 egg::Snapshot s;s.identity=c.identity;s.resourceFingerprint=c.resourceFingerprint;s.health=50;s.flags.constrained=true;
 assert(egg::validateSnapshot(s,c,e));
 auto bad=s;bad.identity.activation++;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.identity.epoch++;assert(!egg::validateSnapshot(bad,c,e));
 bad=s;bad.identity.ordinal++;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.resourceFingerprint[0]='c';assert(!egg::validateSnapshot(bad,c,e));
 bad=s;bad.state=1;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.health=51;assert(!egg::validateSnapshot(bad,c,e));
 bad=s;bad.sourceFrame=31;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.position.y=std::numeric_limits<float>::quiet_NaN();assert(!egg::validateSnapshot(bad,c,e));
 bad=s;bad.scale.x=0;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.flags.leaveCarcass=true;assert(!egg::validateSnapshot(bad,c,e));
 bad=s;bad.effectsEmitted=true;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.health=0;bad.killRequested=true;assert(!egg::validateSnapshot(bad,c,e));
 // Zero health pending StateWait contents/kill is legitimate and causes no
 // callback through validation. Progress ordering remains literal.
 s.health=0;assert(egg::validateSnapshot(s,c,e));s.contentsGenerated=s.effectsEmitted=s.killRequested=true;assert(egg::validateSnapshot(s,c,e));
 // Original dropgroup keeps mIsFalling false and uses normal unconstrained body.
 s=egg::Snapshot{};s.identity=c.identity;s.resourceFingerprint=c.resourceFingerprint;s.health=50;s.dropGroup=true;c.dropGroup=true;
 assert(egg::validateSnapshot(s,c,e));bad=s;bad.flags.constrained=true;assert(!egg::validateSnapshot(bad,c,e));
 // Captured graph requires the same complete parent incarnation plus already
 // bound actual matrix location. No pointer or fabricated parent is accepted.
 c.dropGroup=false;c.dependent=true;c.actualCaptureBound=true;c.actualParent=c.identity;c.capturePosition={10,20,30};
 s=egg::Snapshot{};s.identity=c.identity;s.resourceFingerprint=c.resourceFingerprint;s.dependent=s.captured=s.hasParent=true;s.parentIdentity=c.identity;s.position=c.capturePosition;
 s.flags.constrained=s.flags.invulnerable=true;s.flags.cullable=s.flags.living=false;s.health=50;
 assert(egg::validateSnapshot(s,c,e));s.health=0;assert(egg::validateSnapshot(s,c,e)); // invulnerable pending destruction can be physically restored
 bad=s;bad.parentIdentity.activation++;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.position.y++;assert(!egg::validateSnapshot(bad,c,e));
 bad=s;bad.velocity.y=1;assert(!egg::validateSnapshot(bad,c,e));auto absent=c;absent.actualCaptureBound=false;assert(!egg::validateSnapshot(s,absent,e));
 bad=s;bad.falling=true;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.flags.invulnerable=false;assert(!egg::validateSnapshot(bad,c,e));
 // Released Egg is independent of vanished parent, retains capture's source
 // invulnerability and typed incarnation, and waits for actual floor contact.
 s.captured=s.hasParent=false;s.parentIdentity={};s.falling=true;s.flags.constrained=false;s.flags.cullable=s.flags.living=true;s.velocity.y=-5;
 c.actualCaptureBound=false;c.actualParent={};assert(egg::validateSnapshot(s,c,e));
 bad=s;bad.hasParent=true;assert(!egg::validateSnapshot(bad,c,e));bad=s;bad.flags.invulnerable=false;assert(!egg::validateSnapshot(bad,c,e));
 bad=s;bad.falling=false;assert(!egg::validateSnapshot(bad,c,e));
 std::cout<<"PASS original Egg physical snapshot identity/resource/capture policy checks (no gameplay claim)\n";
}
