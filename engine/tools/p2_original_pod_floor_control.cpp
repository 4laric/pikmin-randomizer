#include "pc_p2_original_pod_floor.h"
#include <cassert>
#include <fstream>
#include <iterator>
#include <iostream>
struct UnusedAuthority:p2retail::FloorIdentityAuthority {
 mutable unsigned calls=0;
 bool expectedBirth(const p2retail::CaveDescriptor&,unsigned,const p2retail::SceneIdentity&,
                    unsigned,unsigned,p2retail::BirthIdentity&,std::string&)const override{++calls;return false;}
};
int main(int argc,char** argv){
 assert(argc==3);std::ifstream in(argv[1],std::ios::binary);assert(in);
 std::string bytes{std::istreambuf_iterator<char>(in),{}};std::string error;
 p2retail::FloorPlan plan;assert(p2retail::parseFloorPlan(bytes,argv[2],plan,error));
 const auto* cave=p2retail::descriptor(plan.cave);assert(cave);
 p2retail::Snapshot floor{cave->cave,cave->source,cave->sourceSha256,cave->catalogSha256,
                         plan.floor,cave->maxFloor,{"selected","visit",argv[2],1},true,true};
 UnusedAuthority authority;p2originalpod::Resources resources;p2originalpod::Config out;
 assert(!p2originalpod::floorConfig(plan,floor,&authority,resources,out,error));
 // This never emits bytes or authenticates resources; the plan helper does not
 // invoke it. Actual native preflight cannot proceed with this denial callback.
 resources.input=[](const std::string&,std::string&,std::string&){return false;};
 assert(p2originalpod::floorConfig(plan,floor,&authority,resources,out,error));
 assert(out.x==plan.pod.x&&out.y==plan.pod.y&&out.z==plan.pod.z&&out.unit==plan.pod.unit&&out.slot==plan.pod.slot);
 auto changed=plan;changed.pod.x+=200;changed.cave="forged";
 assert(p2originalpod::floorConfig(changed,floor,&authority,resources,out,error));
 assert(out.x==plan.pod.x&&out.floor.cave==plan.cave); // Mutable parsed fields never choose placement.
 const auto prior=out;changed.authenticatedBytes+="forged";
 assert(!p2originalpod::floorConfig(changed,floor,&authority,resources,out,error));assert(out.x==prior.x);
 auto bad=floor;bad.floor++;assert(!p2originalpod::floorConfig(plan,bad,&authority,resources,out,error));
 bad=floor;bad.sourceSha256=std::string(64,'a');assert(!p2originalpod::floorConfig(plan,bad,&authority,resources,out,error));
 bad=floor;bad.scene.layoutSha256=std::string(64,'a');assert(!p2originalpod::floorConfig(plan,bad,&authority,resources,out,error));
 assert(!p2originalpod::floorConfig(plan,floor,nullptr,resources,out,error));
 assert(authority.calls==0); // Placement helper neither issues origins nor simulates receipts.
 std::cout<<"PASS exact selected-plan Pod anchor/context/transactional-output control; no native birth or gameplay\n";
}
