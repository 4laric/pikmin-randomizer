#pragma once
#include "pc_p2_original_pod.h"
#include "pc_p2_retail_cave_plan.h"
#include <cstdlib>
#include <utility>

namespace p2originalpod {
struct Resources {
 SourceInput input; // The actual selected-session buffer getter, never an ambient reader.
 std::string model=convertedModelRole,archive=archiveRole,sourceModel=originalModelRole;
 std::string collision=originalCollisionRole,texts=originalTextsRole;
};
inline bool sameFloor(const p2retail::Snapshot& a,const p2retail::Snapshot& b){
 return a.cave==b.cave&&a.source==b.source&&a.sourceSha256==b.sourceSha256
  &&a.catalogSha256==b.catalogSha256&&a.floor==b.floor&&a.maxFloor==b.maxFloor
  &&a.scene==b.scene&&a.story==b.story&&a.inCave==b.inCave;
}
// Derive placement only from the exact selected plan bytes. This is not mode,
// card, geometry, birth or receipt authority; native preflight still requires
// the owning selected-scene ContextProvider and independent birth authority.
inline bool floorConfig(const p2retail::FloorPlan& input,const p2retail::Snapshot& floor,
                        p2retail::FloorIdentityAuthority* births,const Resources& resources,
                        Config& out,std::string& error){
 p2retail::FloorPlan plan;
 if(!p2retail::parseFloorPlan(input.authenticatedBytes,floor.scene.layoutSha256,plan,error))return false;
 const auto* cave=p2retail::descriptor(plan.cave);
 if(!births||!cave||floor.cave!=plan.cave||floor.floor!=plan.floor||floor.source!=cave->source
  ||floor.sourceSha256!=plan.sourceSha256||floor.catalogSha256!=plan.catalogSha256
  ||floor.maxFloor!=cave->maxFloor||!floor.story||!floor.inCave
  ||floor.scene.seed.empty()||floor.scene.visit.empty()||!floor.scene.serial
  ||!resources.input||resources.model.empty()||resources.archive.empty()||resources.sourceModel.empty()
  ||resources.collision.empty()||resources.texts.empty()){
  error="pod_floor_plan_context";return false;
 }
 Config next;next.floor=floor;next.births=births;next.input=resources.input;
 next.unit=plan.pod.unit;next.slot=plan.pod.slot;next.x=plan.pod.x;next.y=plan.pod.y;next.z=plan.pod.z;
 next.yaw=plan.pod.yawDegrees*0.01745329251994329577f;
 next.model=resources.model;next.sourceArchive=resources.archive;
 next.sourceModel=resources.sourceModel;next.sourceCollision=resources.collision;next.sourceTexts=resources.texts;
 out=std::move(next);error.clear();return true;
}

// Borrowed by the concrete NativeFloor::SceneOps owner. It must preserve this
// object and its selected prepared-context provider until release succeeds.
// No destructor teardown: gameplay ownership cannot silently disappear.
class FloorLifecycle {
public:
 FloorLifecycle()=default;
 ~FloorLifecycle(){if(mPrepared)std::abort();} // Preserve failed release ownership; never silently abandon it.
 FloorLifecycle(const FloorLifecycle&)=delete;FloorLifecycle&operator=(const FloorLifecycle&)=delete;
 bool prepare(const p2retail::FloorPlan& plan,const p2retail::Snapshot& floor,
              p2retail::FloorIdentityAuthority& births,ContextProvider provider,
              const Resources& resources,std::string& error){
  if(mPrepared){error="pod_floor_already_owned";return false;}
  Config next;
  if(!floorConfig(plan,floor,&births,resources,next,error))return false;
  if(!pc_p2_original_pod_preflight(next,provider,error))return false;
  mConfig=std::move(next);mProvider=std::move(provider);mPrepared=true;return true;
 }
 bool birth(std::string& error){
  if(!mPrepared||mBorn){error="pod_floor_birth_order";return false;}
  if(!pc_p2_original_pod_birth(mConfig,mProvider,error))return false;
  mBorn=true;return true;
 }
 bool commit(const p2retail::Snapshot& floor,std::string& error){
  if(!mBorn||mCommitted||!sameFloor(mConfig.floor,floor)){error="pod_floor_commit_context";return false;}
  if(!pc_p2_original_pod_commit_floor(floor.scene,error))return false;
  mCommitted=true;return true;
 }
 bool release(std::string& error){return release({},error);}
 bool release(RetainUncollected retain,std::string& error){
  if(!mPrepared){error.clear();return true;}
  bool released=!mCommitted?pc_p2_original_pod_abort_prepared(mConfig.floor.scene,error)
   :(retain?pc_p2_original_pod_release_uncollected(mConfig.floor.scene,std::move(retain),error)
           :pc_p2_original_pod_release(error));
  if(!released)return false; // Retain exact state and provider for bounded retry.
  mConfig={};mProvider={};mPrepared=mBorn=mCommitted=false;return true;
 }
 bool prepared()const{return mPrepared;}
private:
 Config mConfig;ContextProvider mProvider;bool mPrepared=false,mBorn=false,mCommitted=false;
};
}
