#include "pc_p2_actor_slots.h"
#include <cassert>
int main(){
 int old=1,other=2;
 int* slots[4]={&old,&other,&old,nullptr};
 const int count=3;
 p2ActorForgetSlots(slots,count,&old);
 assert(slots[0]==nullptr && slots[1]==&other && slots[2]==nullptr && count==3);
 old=3; // same address reused by the manager: no old reference can reach it.
 for(int i=0;i<count;++i)assert(slots[i]!=&old);
 p2ActorForgetSlots(slots,count,&old);assert(slots[1]==&other);
 p2ActorForgetSlots(slots,0,&other);assert(slots[1]==&other);
 p2ActorForgetSlots(slots,5,&other);assert(slots[1]==&other);
 p2ActorForgetSlots(slots,count,&other);assert(slots[1]==nullptr);
}
