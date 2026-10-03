// Exact registry used by the native receiver, not a born engine actor or
// gameplay fixture. No source authentication/receipt callback is simulated.
#include "pc_p2_original_pod_registry.h"
#include <cassert>
#include <cstdio>

int main(){
 using namespace p2originalpod;
 Ownership registry;
 unsigned addressStorage=0;
 auto* poolAddress=reinterpret_cast<Pellet*>(&addressStorage);
 p2retail::SceneIdentity scene{"source-seed","visit",std::string(64,'a'),7};
 p2retail::BirthIdentity birth{2,1,91,"emergence_cave:floor2:loose_treasure:0:0",37};
 registry.live.emplace(poolAddress,CargoBinding{birth,scene,{},CargoPhase::Bound});
 assert(registry.owns(poolAddress));
 registry.forget(poolAddress);
 assert(!registry.owns(poolAddress)&&registry.live.empty()&&registry.lost.size()==1);
 assert(registry.lost[0].birth==birth&&registry.lost[0].scene==scene);
 // Native pool reuse at the identical address cannot inherit ownership.
 assert(!registry.owns(reinterpret_cast<Pellet*>(&addressStorage)));
 registry.forget(poolAddress);
 assert(registry.lost.size()==1);
 // A legitimately completed entry is revoked without creating a lost source.
 registry.live.emplace(poolAddress,CargoBinding{birth,scene,{},CargoPhase::Completed});
 registry.forget(poolAddress);
 assert(registry.live.empty()&&registry.lost.size()==1);
 std::puts("PASS exact Pod registry: lost typed identity retained; recycled address unowned; repeated kill inert; completed kill no tombstone");
}
