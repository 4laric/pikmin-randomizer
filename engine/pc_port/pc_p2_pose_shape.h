#pragma once
#include "pc_p2_pose_blend.h"
#include "pc_p2_pose_motion.h"
#include <string>
#include "Shape.h"
#include "Joint.h"
#include "Material.h"
#include "system.h"
#include <cstddef>
#include <cstdio>

// pc_port/gl/pc_gfx.cpp: drop and never re-cache resident meshes built from
// vertex storage the CPU rewrites (the GameCube code DCFlushRange()s it).
extern "C" void pc_gfx_mark_dynamic_vertex_range(const void* addr, size_t bytes);

namespace p2pose {
// Call on the App heap. Geometry is private; audited bank resources are shared.
inline Shape* privateShape(const char* path,Shape& shared,const Pose& base){
    Shape* model=gsys->getShape(path,path,nullptr,true);
    if(!model||model->mJointCount!=1||model->mVertexCount!=int(base.positions.size())||model->mNormalCount!=int(base.normals.size())||
       model->mMaterialCount!=shared.mMaterialCount||model->mTexAttrCount!=shared.mTexAttrCount||model->mTevInfoCount!=shared.mTevInfoCount)return nullptr;
    for(int j=0;j<model->mTotalMatpolyCount;++j){auto* poly=model->mMatpolyList[j];if(!poly||!poly->mMaterial)continue;
        int material=-1;for(int m=0;m<model->mMaterialCount;++m)if(poly->mMaterial==&model->mMaterialList[m])material=m;
        if(material<0)return nullptr;poly->mMaterial=&shared.mMaterialList[material];}
    model->mMaterialList=shared.mMaterialList;model->mTexAttrList=shared.mTexAttrList;model->mTevInfoList=shared.mTevInfoList;return model;
}
inline bool apply(Shape& shape,const Pose& a,const Pose& b,float weight,Pose& scratch){
    if(shape.mJointCount!=1||shape.mVertexCount!=int(a.positions.size())||shape.mNormalCount!=int(a.normals.size())||!blendInto(a,b,weight,scratch))return false;
    for(size_t i=0;i<scratch.positions.size();++i){const auto v=scratch.positions[i];shape.mVertexList[i].set(v.x,v.y,v.z);}
    for(size_t i=0;i<scratch.normals.size();++i){const auto v=scratch.normals[i];shape.mNormalList[i].set(v.x,v.y,v.z);}
    BoundBox bounds(shape.mVertexList[0],shape.mVertexList[0]);for(int i=1;i<shape.mVertexCount;++i)bounds.expandBound(shape.mVertexList[i]);
    // The resident-mesh cache keys on the display list; without this the
    // first blended pose is frozen for the life of the level (#897: the
    // Crawbster's first pose is its fly drop-in 1200 units up, so the live
    // model was never on screen).
    pc_gfx_mark_dynamic_vertex_range(shape.mVertexList,size_t(shape.mVertexCount)*sizeof(shape.mVertexList[0]));
    pc_gfx_mark_dynamic_vertex_range(shape.mNormalList,size_t(shape.mNormalCount)*sizeof(shape.mNormalList[0]));
    shape.mCourseExtents=bounds;shape.mJointList[0].mBounds=bounds;return true;
}
// Write one pose into a private single-joint Shape and refresh its bounds.
inline bool write(Shape& shape,const Pose& pose){
    if(shape.mJointCount!=1||shape.mVertexCount<1||shape.mVertexCount!=int(pose.positions.size())||shape.mNormalCount!=int(pose.normals.size()))return false;
    for(size_t i=0;i<pose.positions.size();++i){const auto v=pose.positions[i];shape.mVertexList[i].set(v.x,v.y,v.z);}
    for(size_t i=0;i<pose.normals.size();++i){const auto v=pose.normals[i];shape.mNormalList[i].set(v.x,v.y,v.z);}
    BoundBox bounds(shape.mVertexList[0],shape.mVertexList[0]);for(int i=1;i<shape.mVertexCount;++i)bounds.expandBound(shape.mVertexList[i]);
    // Same resident-cache rule as apply(): the #895 Track path rewrites this
    // private Shape every frame (#897).
    pc_gfx_mark_dynamic_vertex_range(shape.mVertexList,size_t(shape.mVertexCount)*sizeof(shape.mVertexList[0]));
    pc_gfx_mark_dynamic_vertex_range(shape.mNormalList,size_t(shape.mNormalCount)*sizeof(shape.mNormalList[0]));
    shape.mCourseExtents=bounds;shape.mJointList[0].mBounds=bounds;return true;
}
// Per-actor presentation of a decoded pose bank (#895): the engine-free
// p2motion::Presenter picks the lerped pose (with crossfade on clip change and
// across a discontinuous loop seam); this writes it into the actor's private
// Shape. Fade time and staleness advance from the owning module's simulation
// update through Track::advance.
struct Track {
    Shape* shape=nullptr;
    p2motion::Presenter view;
    float refExtent=0.f;       // rest-pose bounding-box diagonal, for the draw guard (#964)
    unsigned refusals=0;
    void size(const Pose& base){
        refExtent=p2motion::extent(base);
        view.scratch.positions.resize(base.positions.size());view.scratch.normals.resize(base.normals.size());
        view.mixed.positions.resize(base.positions.size());view.mixed.normals.resize(base.normals.size());
    }
    void advance(float seconds){view.advance(seconds);}
};
struct Presented { bool ok=false,crossfadeStarted=false,wrapBlend=false; Interval span; };
template<class PoseAt>
inline Presented present(Track& track,const std::string& clip,std::size_t count,PoseAt poseAt,const std::vector<int>& frames,
                         float sourceFrame,const p2motion::Tunables& tune,bool seamOk=true){
    Presented out;
    if(!track.shape)return out;
    const p2motion::Shown shown=track.view.select(clip,count,poseAt,frames,sourceFrame,seamOk,tune);
    out.span=shown.span;
    if(!shown.pose)return out;
    // #964 guard: never write a pose with non-finite or exploded vertices into the
    // draw Shape; the caller keeps its pre-loaded pose Shape and this says why.
    const p2motion::GuardVerdict verdict=p2motion::guardPose(*shown.pose,track.refExtent);
    if(!verdict.ok){
        if(++track.refusals<=8)
            std::printf("P2_POSE_GUARD_REFUSED clip=%s reason=%s vertex=%zu value=%.1f limit=%.1f left=%zu right=%zu weight=%.3f poses=%zu\n",
                        clip.c_str(),verdict.reason,verdict.index,double(verdict.value),double(verdict.limit),shown.span.left,shown.span.right,
                        double(shown.span.weight),count);
        std::fflush(stdout);
        return out;
    }
    if(!write(*track.shape,*shown.pose))return out;
    track.view.commit(*shown.pose);
    out.crossfadeStarted=shown.crossfadeStarted;out.wrapBlend=shown.wrapBlend;out.ok=true;return out;
}
}
