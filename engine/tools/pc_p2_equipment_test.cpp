#include "pc_p2_equipment_policy.h"
#include <cassert>
#include <set>
#include <string>
int main() {
    using namespace p2equipment;
    std::set<std::string> receipts;
    auto read=[&] {return project([&](const char* id){return receipts.count(id);});};
    auto k=read();assert(k.bits==0&&k.courses()==1&&k.damage(12)==12&&k.speed(160)==160&&k.whistle(100)==100);
    receipts.insert("key");receipts.insert("unknown");
    assert(read().bits==0&&!read().has(TheKey));
    receipts.insert("map02");assert(read().courses()==5&&!read().has(SphericalAtlas));
    receipts.insert("map01");assert(read().courses()==7); // never unlock Wild
    const auto before=read().bits;receipts.insert("map01");assert(read().bits==before);
    // Reconstructing in a fresh process/state needs only accepted saved receipts.
    const auto saved=receipts;receipts.clear();assert(read().bits==0);receipts=saved;assert(read().bits==before);
    for(int i=0;i<TheKey;++i) {receipts.insert(Sources[i].id);assert(read().has(i));assert(item(Sources[i].id)==i);}
    k=read();assert(k.bits==0xfff&&k.damage(12)==6&&k.whistle(100)==200&&k.speed(160)==240);
    assert(!k.has(-1)&&!k.has(13)&&item(nullptr)==-1&&item("map01extra")==-1);
    assert(Sources[SphericalAtlas].dictionary==184&&Sources[GeographicProjection].dictionary==185);
}
