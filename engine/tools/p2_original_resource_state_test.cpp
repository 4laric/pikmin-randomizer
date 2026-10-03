#include "pc_p2_original_resource_state.h"
#include <cassert>
#include <climits>
#include <cstdio>
using namespace p2originalresource;
int main(){
 SourceIdentity source{std::string(64,'c'),1379326868,0,0,1};ChildIdentity child{source,0};
 ContentsRecord record;record.source=source;record.type=P2EggDropType::Spicy;record.complete=true;
 ChildOutcome drop;drop.identity=child;drop.kind=ChildKind::Spicy;drop.attempted=drop.born=true;record.children.push_back(drop);
 EggContents contents;std::string e;assert(contents.restore({record},e));ResourceState state;ResourceSnapshot snapshot;
 assert(!state.snapshot(snapshot,e)&&!state.completeSpray(child,HoneyKind::Spicy,0,contents,e));assert(state.restore(snapshot,contents,e));
 assert(!state.sprayMade(HoneyKind::Spicy));assert(state.markSprayMade(HoneyKind::Spicy,e)&&state.sprayMade(HoneyKind::Spicy));
 assert(state.completeSpray(child,HoneyKind::Spicy,0,contents,e)&&state.sprayCount(HoneyKind::Spicy)==1);
 assert(state.completeSpray(child,HoneyKind::Spicy,0,contents,e)&&state.sprayCount(HoneyKind::Spicy)==1);
 assert(contents.consume(child,e)); // physical kill can precede recipient END
 assert(state.completeSpray(child,HoneyKind::Spicy,1,contents,e)&&state.sprayCount(HoneyKind::Spicy)==2);
 assert(!state.completeSpray(child,HoneyKind::Bitter,0,contents,e));assert(!state.completeSpray(child,HoneyKind::Spicy,2,contents,e));
 auto absent=child;absent.source.activation=2;assert(!state.completeSpray(absent,HoneyKind::Spicy,0,contents,e));
 assert(state.useSpray(HoneyKind::Spicy,e)&&state.useSpray(HoneyKind::Spicy,e)&&!state.useSpray(HoneyKind::Spicy,e));
 assert(state.snapshot(snapshot,e)&&snapshot.sprayUses[0]==2);ResourceState restored;assert(restored.restore(snapshot,contents,e));assert(restored.completeSpray(child,HoneyKind::Spicy,1,contents,e)&&restored.sprayCount(HoneyKind::Spicy)==0);
 auto bad=snapshot;bad.completed.push_back(bad.completed[0]);assert(!restored.restore(bad,contents,e)&&restored.sprayMade(HoneyKind::Spicy));bad=snapshot;bad.version=2;assert(!restored.restore(bad,contents,e));
 bad=snapshot;bad.sprayCounts[0]=-1;assert(!restored.restore(bad,contents,e));bad=snapshot;bad.completed.clear();bad.sprayCounts[0]=INT_MAX;assert(restored.restore(bad,contents,e)&&!restored.completeSpray(child,HoneyKind::Spicy,0,contents,e));
 record.children[0].born=false;EggContents failed;assert(failed.restore({record},e));assert(!state.completeSpray(child,HoneyKind::Spicy,0,failed,e));
 ResourceState berries;ResourceSnapshot fresh;assert(berries.restore(fresh,contents,e));assert(!berries.addBerry(HoneyKind::Bitter,1,0,e));
 assert(berries.addBerry(HoneyKind::Bitter,9,10,e)&&berries.sprayCount(HoneyKind::Bitter)==0);assert(berries.snapshot(fresh,e)&&fresh.berryCounts[1]==9);
 assert(berries.addBerry(HoneyKind::Bitter,22,10,e)&&berries.sprayCount(HoneyKind::Bitter)==3);assert(berries.snapshot(fresh,e)&&fresh.berryCounts[1]==1&&!berries.sprayMade(HoneyKind::Bitter));
 fresh.berryCounts[1]=9;assert(berries.restore(fresh,contents,e));assert(berries.addBerry(HoneyKind::Bitter,1,2,e)&&berries.snapshot(fresh,e)&&fresh.berryCounts[1]==0&&fresh.sprayCounts[1]==4);
 fresh.sprayCounts[1]=INT_MAX;assert(berries.restore(fresh,contents,e));assert(!berries.addBerry(HoneyKind::Bitter,2,2,e));ResourceSnapshot unchanged;assert(berries.snapshot(unchanged,e)&&unchanged.berryCounts==fresh.berryCounts);
 std::puts("P2_ORIGINAL_RESOURCE_STATE_POLICY_PASS: real-born child validation, two-captain completion and atomic restore; no gameplay claim");
}
