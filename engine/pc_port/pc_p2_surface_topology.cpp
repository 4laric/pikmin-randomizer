#include "pc_p2_surface_topology.h"
#include "pc_bbft.h"
#include "Shape.h"
#include "Collision.h"
#include <cstdio>
#include <cstdlib>
#include <cstdint>
namespace {
BaseShape* active=nullptr;
p2surface::Topology topology;
unsigned ambiguous=0;
p2surface::Plane convert(const Plane& p){return {p.mNormal.x,p.mNormal.y,p.mNormal.z,p.mOffset};}
int index(const CollTriInfo* tri){return int((reinterpret_cast<std::uintptr_t>(tri)-reinterpret_cast<std::uintptr_t>(active->mTriList))/sizeof(CollTriInfo));}
}
void pc_p2_surface_topology_reset(){active=nullptr;topology.clear();ambiguous=0;}
void pc_p2_surface_topology_init(BaseShape* model){
    pc_p2_surface_topology_reset();
    if(!pc_pikipelago_surface_course())return;
    if(!model||!model->mTriList||model->mTriCount<=0||model->mTriCount>32767)std::abort();
    std::vector<p2surface::Face> faces;
    for(int i=0;i<model->mTriCount;++i){const CollTriInfo& t=model->mTriList[i];
        faces.push_back({{t.mVertexIndices[0],t.mVertexIndices[1],t.mVertexIndices[2]},convert(t.mTriangle),
                        {convert(t.mEdgePlanes[0]),convert(t.mEdgePlanes[1]),convert(t.mEdgePlanes[2])},t.mMapCode});}
    if(!topology.build(faces))std::abort();
    active=model;
    std::printf("P2_SURFACE_TOPOLOGY_READY faces=%d multi_edges=%d all_incidents_retained=1 ambiguous_policy=no_unique_continuation\n",topology.size(),topology.multiEdges());
}
bool pc_p2_surface_topology_owns(BaseShape* model,const CollTriInfo* tri){
    if(!pc_pikipelago_surface_course()||!model||active!=model||!tri||model->mTriCount!=topology.size())return false;
    std::uintptr_t start=reinterpret_cast<std::uintptr_t>(model->mTriList),point=reinterpret_cast<std::uintptr_t>(tri);
    return point>=start&&point<start+sizeof(CollTriInfo)*topology.size()&&(point-start)%sizeof(CollTriInfo)==0;
}
const std::vector<p2surface::Incident>* pc_p2_surface_incidents(BaseShape* model,const CollTriInfo* tri,int edge){
    return pc_p2_surface_topology_owns(model,tri)?topology.incidents(index(tri),edge):nullptr;
}
p2surface::Crossing pc_p2_surface_continuation(BaseShape* model,const CollTriInfo* tri,int edge,const Vector3f& position){
    if(!pc_p2_surface_topology_owns(model,tri))return {p2surface::Kind::Invalid,-1};
    auto result=topology.continuation(index(tri),edge,position.x,position.z);
    if(result.kind==p2surface::Kind::Ambiguous){if(ambiguous++<16)std::printf("P2_SURFACE_TOPOLOGY_AMBIGUOUS face=%d edge=%d x=%.3f z=%.3f outcome=no_unique_continuation\n",index(tri),edge,position.x,position.z);}
    return result;
}
unsigned pc_p2_surface_ambiguous_queries(){return ambiguous;}
