#include "pc_p2_original_honey_snapshot.h"
#include <cassert>
#include <set>
#include <iostream>
using namespace p2originalresource;using namespace p2originalresource::honey;
int main(){ChildIdentity egg;egg.source={std::string(64,'a'),19,7,0,1};ChildIdentity first=egg;first.ancestry={{EmitterKind::PlantSpectralid,0,0}};ChildIdentity second=first;second.ancestry[0].member=1;
 assert(validChildIdentity(egg)&&validChildIdentity(first)&&validChildIdentity(second));assert(!(first==second)&&!(first==egg));
 std::set<ChildIdentity> factoryHistory;assert(factoryHistory.insert(first).second&&factoryHistory.insert(second).second&&!factoryHistory.insert(first).second&&factoryHistory.insert(egg).second); // same parent and Honey slot remain three genuine births
 Snapshot row;row.identity=second;Snapshot copied=row;assert(copied.identity==second&&copied.identity.ancestry[0].member==1);
 auto mitite=egg;mitite.ancestry={{EmitterKind::EggMitite,0,0}};auto tenth=mitite;tenth.ancestry[0].member=9;assert(validChildIdentity(mitite)&&validChildIdentity(tenth)&&!(mitite==egg)&&!(mitite==first)&&!(mitite==tenth));assert(factoryHistory.insert(mitite).second&&factoryHistory.insert(tenth).second&&!factoryHistory.insert(mitite).second);auto invalidMitite=mitite;invalidMitite.ancestry[0].member=10;assert(!validChildIdentity(invalidMitite));
 auto bad=first;bad.ancestry[0].member=5;assert(!validChildIdentity(bad));bad=first;bad.slot=1;assert(!validChildIdentity(bad));bad=first;bad.ancestry.push_back(bad.ancestry[0]);assert(!validChildIdentity(bad));bad=first;bad.ancestry[0].emissionOrdinal=1;assert(!validChildIdentity(bad));
 std::cout<<"P2_ORIGINAL_HONEY_IDENTITY_PASS\n";
}
