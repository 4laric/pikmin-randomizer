#pragma once
#include "pc_p2_pose_blend.h"
#include "pc_p2_pose_motion.h"
#include <string>
#include "Shape.h"
#include "Joint.h"
#include "Material.h"
#include "system.h"

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
    shape.mCourseExtents=bounds;shape.mJointList[0].mBounds=bounds;return true;
}
// Write one pose into a private single-joint Shape and refresh its bounds.
inline bool write(Shape& shape,const Pose& pose){
    if(shape.mJointCount!=1||shape.mVertexCount<1||shape.mVertexCount!=int(pose.positions.size())||shape.mNormalCount!=int(pose.normals.size()))return false;
    for(size_t i=0;i<pose.positions.size();++i){const auto v=pose.positions[i];shape.mVertexList[i].set(v.x,v.y,v.z);}
    for(size_t i=0;i<pose.normals.size();++i){const auto v=pose.normals[i];shape.mNormalList[i].set(v.x,v.y,v.z);}
    BoundBox bounds(shape.mVertexList[0],shape.mVertexList[0]);for(int i=1;i<shape.mVertexCount;++i)bounds.expandBound(shape.mVertexList[i]);
    shape.mCourseExtents=bounds;shape.mJointList[0].mBounds=bounds;return true;
}
// Per-actor presentation of a decoded pose bank (#895): bracket/lerp the
// clip's poses at a source frame, crossfade from the last displayed geometry
// when the clip changes, and write the result into the actor's private Shape.
// Fade time is advanced by the owning module's simulation update.
struct Track {
    Shape* shape=nullptr;
    Pose scratch,mixed,display;
    p2motion::Fade fade;
    std::string clip;
    bool shown=false;
    void size(const Pose& base){
        scratch.positions.resize(base.positions.size());scratch.normals.resize(base.normals.size());
        mixed.positions.resize(base.positions.size());mixed.normals.resize(base.normals.size());
    }
};
struct Presented { bool ok=false,crossfadeStarted=false; Interval span; };
template<class PoseAt>
inline Presented present(Track& track,const std::string& clip,std::size_t count,PoseAt poseAt,const std::vector<int>& frames,
                         float sourceFrame,const p2motion::Tunables& tune){
    Presented out;
    if(!track.shape||!count||frames.size()!=count||!p2motion::interval(frames,sourceFrame,tune.lerp,out.span)
       ||out.span.left>=count||out.span.right>=count)return out;
    const Pose& a=poseAt(out.span.left);const Pose& b=poseAt(out.span.right);
    if(track.scratch.positions.size()!=a.positions.size()||track.scratch.normals.size()!=a.normals.size())track.size(a);
    if(!blendInto(a,b,out.span.weight,track.scratch))return out;
    if(track.clip!=clip){
        if(track.shown&&!track.clip.empty())out.crossfadeStarted=track.fade.begin(track.display,tune.crossfadeSeconds);
        else track.fade.reset();
        track.clip=clip;
    }
    const Pose* shown=&track.scratch;
    if(track.fade.active()&&track.fade.mix(track.scratch,track.mixed))shown=&track.mixed;
    if(!write(*track.shape,*shown))return out;
    track.display.positions.assign(shown->positions.begin(),shown->positions.end());
    track.display.normals.assign(shown->normals.begin(),shown->normals.end());
    track.shown=true;out.ok=true;return out;
}
}
