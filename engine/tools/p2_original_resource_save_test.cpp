#include "pc_p2_original_resource_save.h"
#include <cassert>
#include <cstdio>
using namespace p2originalresource;
int main(){
 const std::string campaign(64,'a');SourceIdentity id{std::string(64,'b'),1379326868,1,9,3};
 ContentsRecord record;record.source=id;record.type=P2EggDropType::Bitter;record.complete=true;ChildOutcome child;child.identity={id,0};child.kind=ChildKind::Bitter;child.born=child.attempted=true;record.children={child};
 EggContents graph;std::string e;assert(graph.restore({record},e));ResourceSnapshot state;state.sprayCounts={4,11};state.berryCounts={0,9};state.sprayUses={2,3};state.sprayMade={true,true};state.completed={{child.identity,HoneyKind::Bitter,1}};
 std::string bytes;assert(encodeResources(state,campaign,graph,bytes,e));ResourceSnapshot out;assert(decodeResources(bytes,campaign,graph,out,e)&&out.sprayCounts==state.sprayCounts&&out.berryCounts==state.berryCounts&&out.sprayUses==state.sprayUses&&out.completed.size()==1);
 const auto original=out;
 for(auto bad:{std::string("P2ORS2")+bytes.substr(6),bytes+" trailing",bytes.substr(0,bytes.size()-1),std::string(1048577,'x'),bytes+"\n"}){assert(!decodeResources(bad,campaign,graph,out,e));assert(out.sprayCounts==original.sprayCounts&&out.completed.size()==1);}
 assert(!decodeResources(bytes,std::string(64,'c'),graph,out,e));EggContents absent;assert(!decodeResources(bytes,campaign,absent,out,e));
 auto invalid=state;invalid.completed.push_back(invalid.completed.front());std::string unchanged="unchanged";assert(!encodeResources(invalid,campaign,graph,unchanged,e)&&unchanged=="unchanged");
 invalid=state;invalid.sprayUses[0]=-1;assert(!encodeResources(invalid,campaign,graph,unchanged,e));
 auto signedUid=bytes;auto at=signedUid.find("1379326868");signedUid.replace(at,10,"-1");assert(!decodeResources(signedUid,campaign,graph,out,e));
 invalid=state;invalid.completed[0].child.ancestry={{EmitterKind::PlantSpectralid,0,0}};assert(!encodeResources(invalid,campaign,graph,unchanged,e)&&unchanged=="unchanged");
 std::puts("P2_ORIGINAL_RESOURCE_SAVE_POLICY_PASS: bounded atomic campaign-SHA card/prospective-child validation; no physical resume claim");
}
