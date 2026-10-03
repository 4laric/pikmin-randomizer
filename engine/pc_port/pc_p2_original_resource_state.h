#pragma once
#include "pc_p2_original_resource_contents.h"
#include <array>
#include <set>
namespace p2originalresource {
struct SprayCompletion {
 ChildIdentity child;HoneyKind kind=HoneyKind::Spicy;unsigned captain=0;
 bool operator<(const SprayCompletion&)const;
};
struct ResourceSnapshot {
 unsigned version=1;
 std::array<int,2> sprayCounts{{0,0}}; // source story PlayData: spicy=0,bitter=1
 std::array<int,2> berryCounts{{0,0}};
 std::array<int,2> sprayUses{{0,0}};
 std::array<bool,2> sprayMade{{false,false}}; // authoritative demo flags
 std::vector<SprayCompletion> completed;
};
// Campaign-owned state, never a treasure/Pokos reward journal or sidefile.
// Installation is explicit from the campaign checkpoint/fresh-campaign owner.
class ResourceState {
public:
 bool restore(const ResourceSnapshot&,const EggContents&,std::string&);
 bool snapshot(ResourceSnapshot&,std::string&)const;
 bool ready()const{return mReady;}
 bool sprayMade(HoneyKind)const;
 int sprayCount(HoneyKind)const;
 // Actual NaviAbsorb END after successful physical absorption calls this.
 // Stable captain roster index permits both captains to share one shrink.
 bool completeSpray(const ChildIdentity&,HoneyKind,unsigned captain,const EggContents&,std::string&);
 // Used by actual campaign spray use/crafting owners; callers perform the
 // physical source mechanic. No resource is credited on unrelated callbacks.
 bool useSpray(HoneyKind,std::string&);
 // Source PlayData::addDopeFruit increments one berry, and resets the
 // remainder to zero on threshold. Bulk count equals repeated source calls.
 // Threshold MUST come from actual source AI mDopeCount, never a default.
 bool addBerry(HoneyKind,int count,int sourceThreshold,std::string&);
 bool markSprayMade(HoneyKind,std::string&);
private:
 bool mReady=false;ResourceSnapshot mState;std::set<SprayCompletion> mCompleted;
};
}
