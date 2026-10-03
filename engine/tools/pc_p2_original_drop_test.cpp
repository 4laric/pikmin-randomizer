#include "pc_p2_original_drop.h"
#include <iostream>
#include <stdexcept>
using namespace p2original;
static unsigned checks=0;static void check(bool b){++checks;if(!b)throw std::runtime_error("drop control "+std::to_string(checks));}
int main(){
 EnemyRecord r;r.uid=0x52000001;r.pelletSize=5;r.pelletColor=3;r.pelletMinimum=1;r.pelletMaximum=3;r.pelletProbability=0;
 std::string e;std::vector<float> draws;unsigned index=0,births=0,applied=0;int physical=0;
 std::vector<std::string> events;std::vector<Position> velocities;
 DropIO io;
 io.draw=[&](float& v,std::string&){check(index<draws.size());events.push_back("draw");v=draws[index++];return true;};
 io.treasure=[&](int code,std::string&){check(code==841);events.push_back("treasure");return true;};
 io.number=[&](unsigned size,unsigned color,void*& out,std::string&){check(size==5);check(color<=3);events.push_back("birth"+std::to_string(color));++births;out=&physical;return true;};
 io.velocity=[&](void* p,const Position& v,std::string&){check(p==&physical);events.push_back("velocity");++applied;velocities.push_back(v);return true;};
 draws={0.1f};check(throwOriginalItems(r,io,e));check(index==1&&births==0&&applied==0);
 r.treasureCode=841;index=0;events.clear();check(throwOriginalItems(r,io,e));check(events.size()==2&&events[0]=="treasure"&&events[1]=="draw");
 r.treasureCode=0;r.pelletProbability=1;index=0;events.clear();draws={0,0.25f,0.5f,0.25f,0.75f,0.1f,0.5f,0.5f};
 check(throwOriginalItems(r,io,e));check(index==8&&births==2&&applied==2);check(events[3]=="birth1"&&events[6]=="velocity");check(velocities[0].x==-50&&velocities[0].y==200&&velocities[0].z==50);
 // Physical failed birth retains color/count draws but skips BOTH velocity
 // draws. The following successful attempt consumes its own exact sequence.
 index=0;births=0;applied=0;events.clear();velocities.clear();draws={0,0.25f,0.5f,0.1f,0.25f,0.75f};
 io.number=[&](unsigned,unsigned color,void*& out,std::string&){check(color<=3);events.push_back("birth");out=births++?&physical:nullptr;return true;};
 check(throwOriginalItems(r,io,e));check(index==6&&births==2&&applied==1);check(velocities[0].x==-50&&velocities[0].z==50);
 // Descending source count range uses nearest signed rounding, not unsigned
 // underflow or P1 inclusive integer-uniform distribution.
 r.pelletMinimum=3;r.pelletMaximum=1;r.pelletColor=0;index=0;births=0;applied=0;draws={0,0.25f,0.5f,0.5f};
 io.number=[&](unsigned,unsigned color,void*& out,std::string&){check(color==0);++births;out=nullptr;return true;};
 check(throwOriginalItems(r,io,e));check(index==2&&births==2&&applied==0);
 // Probability comparison is strict; equality produces no count/birth draws.
 r.pelletProbability=0.5f;index=0;births=0;draws={0.5f};check(throwOriginalItems(r,io,e));check(index==1&&births==0);
 r.pelletSize=7;index=0;check(!throwOriginalItems(r,io,e));check(index==0);r.pelletSize=5;
 draws={1.5f};check(!throwOriginalItems(r,io,e));check(index==1);
 r.pelletProbability=1;r.pelletColor=3;r.pelletMinimum=1;r.pelletMaximum=1;index=0;births=0;draws={0,0,1};
 io.number=[&](unsigned,unsigned color,void*& out,std::string&){check(color==3);++births;out=nullptr;return true;};
 check(throwOriginalItems(r,io,e));check(index==3&&births==1); // No silent endpoint-color clamp.
 std::cout<<"PASS original common drops "<<checks<<" controls\n";
}
