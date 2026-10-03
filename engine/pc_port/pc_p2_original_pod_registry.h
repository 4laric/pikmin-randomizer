#pragma once
#include "pc_p2_original_pod.h"
#include <map>

// Source-identity ownership storage used by the native receiver. This alone
// has no receiver, birth authentication, receipt authority or ledger access.
namespace p2originalpod {
enum class CargoPhase {Bound,Sucking,Completed,Lost};
struct CargoBinding {
 p2retail::BirthIdentity birth;p2retail::SceneIdentity scene;
 CompletedCallback callback;CargoPhase phase=CargoPhase::Bound;
};
struct LostBinding {p2retail::BirthIdentity birth;p2retail::SceneIdentity scene;};
struct Ownership {
 std::map<Pellet*,CargoBinding> live;
 std::vector<LostBinding> lost;
 bool owns(const Pellet* p)const{return live.count(const_cast<Pellet*>(p))!=0;}
 void forget(Pellet* p){
  auto it=live.find(p);if(it==live.end())return;
  if(it->second.phase!=CargoPhase::Completed)lost.push_back({it->second.birth,it->second.scene});
  // A freed native pool address is never an identity tombstone.
  live.erase(it);
 }
};
}
