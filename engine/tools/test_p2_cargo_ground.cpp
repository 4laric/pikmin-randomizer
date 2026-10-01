#include "pc_p2_cargo_ground.h"
#include <cassert>
#include <limits>
int main(){
 for(int mask=0;mask<64;mask++)assert(pc_p2_cargo_bounded_ground(mask&1,mask&2,mask&4,mask&8,mask&16,mask&32)==(mask==31));
 assert(pc_p2_cargo_ground_candidate(20.5f,41.5f,0,1,0));
 assert(!pc_p2_cargo_ground_candidate(119.781f,41.5f,0,1,0));
 assert(pc_p2_cargo_ground_candidate(20.5f,20.5f,0,1,0));
 assert(!pc_p2_cargo_ground_candidate(20.5f,20.4f,0,1,0));
 assert(pc_p2_cargo_ground_candidate(12.75f,20,.6f,.8f,0));
 assert(!pc_p2_cargo_ground_candidate(0,40,1,0,0));
 assert(!pc_p2_cargo_ground_candidate(0,40,0,-1,0));
 assert(!pc_p2_cargo_ground_candidate(0,40,0,2,0));
 assert(!pc_p2_cargo_ground_candidate(std::numeric_limits<float>::infinity(),40,0,1,0));
 assert(!pc_p2_cargo_ground_candidate(0,std::numeric_limits<float>::quiet_NaN(),0,1,0));
 assert(pc_p2_cargo_uphill_velocity(10,0,-20,-.6f,.8f,0)==7.5f);
 assert(pc_p2_cargo_uphill_velocity(10,0,-20,0,1,0)==-20);
 assert(pc_p2_cargo_uphill_velocity(10,0,20,-.6f,.8f,0)==20);
}
