#pragma once
#include "pc_p2_retail_cave_context.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <sstream>

namespace p2retail {
struct Placement {unsigned row=0,ordinal=0,unit=0,slot=0;std::string instance;float x=0,y=0,z=0,yawDegrees=0;};
struct Anchor {unsigned unit=0,slot=0;float x=0,y=0,z=0,yawDegrees=0;};
struct FloorPlan {
 std::string cave,sourceSha256,catalogSha256,geometrySha256,routesSha256,layoutSha256,transition;
 unsigned floor=0;std::vector<Placement> actors;Anchor pod,exit;
 std::string authenticatedBytes;
};
inline bool position(float x,float y,float z,float yaw){
 return std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z)&&std::isfinite(yaw)&&
        std::fabs(x)<=100000&&std::fabs(y)<=100000&&std::fabs(z)<=100000&&yaw>=0&&yaw<360;
}
inline bool parseFloorPlan(const std::string& bytes,const std::string& expectedSha256,FloorPlan& out,std::string& error){
 unsigned char hash[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),hash);
 if(bytes.size()>1024*1024||!hex64(expectedSha256)||pc_netplay_sha::hex(hash,32)!=expectedSha256){
  error="retail floor plan digest differs";return false;
 }
 std::istringstream in(bytes);FloorPlan next;std::string tag;unsigned count=0;
 if(!(in>>tag)||tag!="P2_RETAIL_FLOOR_1"||!(in>>next.cave>>next.floor>>next.sourceSha256>>next.catalogSha256>>next.geometrySha256>>next.routesSha256>>tag>>count)||
    tag!="actors"||count>10000||!hex64(next.geometrySha256)||!hex64(next.routesSha256)){
  error="retail floor plan framing";return false;
 }
 const auto* cave=descriptor(next.cave);const auto* floor=cave?definition(*cave,next.floor):nullptr;
 if(!floor||cave->sourceSha256!=next.sourceSha256||cave->catalogSha256!=next.catalogSha256){error="retail floor plan source pin";return false;}
 std::set<std::string> expected,seen;
 for(const auto& row:floor->rows)for(unsigned i=0;i<row.minimum();++i)expected.insert(instanceKey(*cave,next.floor,row,i));
 for(unsigned i=0;i<count;++i){
  Placement p;
  if(!(in>>tag>>p.row>>p.ordinal>>p.instance>>p.unit>>p.slot>>p.x>>p.y>>p.z>>p.yawDegrees)||tag!="actor"||
     p.row>=floor->rows.size()||p.ordinal>=floor->rows[p.row].minimum()||
     p.instance!=instanceKey(*cave,next.floor,floor->rows[p.row],p.ordinal)||!seen.insert(p.instance).second||
     !position(p.x,p.y,p.z,p.yawDegrees)){error="retail floor plan actor identity/transform";return false;}
  next.actors.push_back(std::move(p));
 }
 if(expected!=seen){error="retail floor plan incomplete source roster";return false;}
 for(unsigned i=0;i<2;++i){auto& a=i?next.exit:next.pod;
  if(!(in>>tag>>a.unit>>a.slot>>a.x>>a.y>>a.z>>a.yawDegrees)||tag!=(i?"exit":"pod")||!position(a.x,a.y,a.z,a.yawDegrees)){
   error="retail floor plan source anchor";return false;
  }
 }
 if(!(in>>tag>>next.transition)||tag!="transition"||next.transition!=(next.floor==cave->maxFloor?"geyser":"hole")||in>>tag){
  error="retail floor plan transition/trailing bytes";return false;
 }
 next.layoutSha256=expectedSha256;next.authenticatedBytes=bytes;out=std::move(next);error.clear();return true;
}
}
