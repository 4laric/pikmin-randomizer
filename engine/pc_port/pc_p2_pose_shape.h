#pragma once
#include "pc_p2_pose_blend.h"
#include "Shape.h"
#include "Joint.h"
#include "Material.h"
#include "System.h"

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
}
