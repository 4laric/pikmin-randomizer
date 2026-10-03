#include "pc_p2_original_blackpom_policy.h"
#include <cassert>
#include <limits>
int main(){
 using namespace p2original::blackpom;
 BirthContext c{true,true,true,"tutorial_1",1,19,0};
 assert(!suppressed(c));c.cachedPurple=1;assert(suppressed(c));
 c.floorIndex=5;assert(suppressed(c)); // Emergence applies on every floor.
 c.cave="forest_1";assert(!suppressed(c));c.floorIndex=1;assert(suppressed(c));
 c.floorIndex=2;assert(!suppressed(c));c.floorIndex=0;
 c.story=false;assert(!suppressed(c));c.story=true;
 c.inCave=false;assert(!suppressed(c));c.inCave=true;
 c.section=false;assert(!suppressed(c));c.section=true;
 c.allPurple=std::numeric_limits<std::uint32_t>::max();c.cachedPurple=1;
 assert(suppressed(c)); // population addition cannot wrap into permission.
}
