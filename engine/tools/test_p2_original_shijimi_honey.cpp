#include "pc_p2_original_shijimi_honey.h"
#include <cassert>
#include <cstdio>
using namespace p2original;
using namespace p2original::shijimi;
using namespace p2originalresource;
int main(){
 std::string e;
 Child c;c.identity.plant={std::string(64,'a'),1234,3,4,5};c.born=c.initialized=c.dropAttempted=true;
 ChildOutcome out;c.facing=1.25f;
 for(unsigned n=0;n<5;++n){c.identity.child=n;
  for(auto kind:{Color::Yellow,Color::Red,Color::Purple}){c.color=kind;
   assert(honeyOutcome(c,{1,2,3},{4,200,4},out,e));
   assert(out.identity.source.fingerprint==c.identity.plant.catalog&&out.identity.source.uid==1234&&out.identity.source.ordinal==3&&out.identity.source.epoch==4&&out.identity.source.activation==5);
   assert(out.identity.ancestry.size()==1&&out.identity.ancestry[0].member==n&&out.identity.slot==0);
   assert(out.facing==0&&out.attempted&&!out.born&&!out.consumed);
   assert(out.kind==(kind==Color::Yellow?ChildKind::Nectar:kind==Color::Red?ChildKind::Spicy:ChildKind::Bitter));
   Identity back;assert(honeyOwner(out.identity,back,e)&&back==c.identity);
  }
 }
 ChildIdentity direct{out.identity.source,0};Identity owner;
 assert(!honeyOwner(direct,owner,e));
 auto other=out.identity;other.ancestry[0].kind=EmitterKind::EggMitite;assert(!honeyOwner(other,owner,e));
 other=out.identity;other.ancestry[0].member=5;assert(!honeyOwner(other,owner,e));
 other=out.identity;other.slot=1;assert(!honeyOwner(other,owner,e));
 other=out.identity;other.ancestry[0].emissionOrdinal=1;assert(!honeyOwner(other,owner,e));
 other=out.identity;other.source.fingerprint="actual-catalog";assert(!honeyOwner(other,owner,e));
 c.identity.plant.catalog="actual-catalog";assert(!honeyOutcome(c,{1,2,3},{4,200,4},out,e));
 c.identity.plant.catalog=std::string(64,'a');
 c.dropComplete=true;assert(!honeyOutcome(c,{1,2,3},{4,200,4},out,e));
 std::puts("P2_ORIGINAL_SHIJIMI_HONEY_TEST PASS canonical-ancestry exact-root typed-owner no-Egg-alias");
}
