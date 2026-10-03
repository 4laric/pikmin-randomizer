#include "pc_p2_original_wisp_snapshot.h"
#include <cassert>
#include <limits>
#include <iostream>
using namespace p2original;using namespace p2original::wisp;
int main(){
 Initial initial;Snapshot s;s.identity={"fp",42,0,7,2};s.cargo={"fp",42,0,7,2};s.spawn[1]={-30,0,200};s.eggBorn=true;std::string e;
 auto valid=[&](const Snapshot& x,int duration=30,const std::vector<Key>& keys=std::vector<Key>{}){return validateSnapshot(x,initial,duration,keys,e);};
 assert(valid(s));
 auto slot=s;slot.cargoSlot=1;assert(!valid(slot));
 auto bad=s;bad.cargo.activation++;assert(!valid(bad));bad=s;bad.spawn[1].x+=1;assert(!valid(bad));bad=s;bad.clock.next=1;assert(!valid(bad));bad=s;bad.released=true;assert(!valid(bad));bad=s;bad.position.x=std::numeric_limits<float>::infinity();assert(!valid(bad));bad=s;bad.targetVelocity.z=std::numeric_limits<float>::quiet_NaN();assert(!valid(bad));
 s.state=State::Move;s.motion=0;s.scale=1;s.atari=true;s.hidden=false;s.clock.stopped=false;s.clock.frame=6;s.clock.next=1;
 assert(valid(s,100,{{0,0},{99,1}}));bad=s;bad.clock.next=0;assert(!valid(bad,100,{{0,0},{99,1}}));bad=s;bad.clock.completed=true;assert(!valid(bad,100,{{0,0},{99,1}}));
 s.state=State::Drop;s.motion=1;s.cullable=false;s.clock.frame=5;s.clock.next=0;assert(valid(s,35,{{5,2}}));s.clock.frame=6;s.clock.next=1;s.released=true;assert(valid(s,35,{{5,2}}));bad=s;bad.clock.next=0;assert(!valid(bad,35,{{5,2}}));
 // Last-event-wins at a large source step can enter Dead still carrying cargo.
 s.state=State::Dead;s.motion=2;s.dead=true;s.alive=false;s.released=false;s.clock.frame=0;s.clock.next=0;assert(valid(s,10,{{0,0},{9,1}}));s.released=true;assert(valid(s,10,{{0,0},{9,1}}));
 s=Snapshot{};s.identity={"fp",42,0,7,2};s.cargo={"fp",42,0,7,2};s.spawn[1]={-30,0,200};s.spawnIndex=1;s.facing=3.14159265358979323846f;assert(valid(s));s.facing=0;assert(!valid(s));
 std::cout<<"Wisp snapshot validation PASS\n";
}
