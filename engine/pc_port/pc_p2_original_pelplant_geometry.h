#pragma once
#include "pc_p2_pose_shape.h"
#include <memory>
#include <algorithm>

extern "C" void pc_gfx_forget_dynamic_vertex_range(const void*,size_t);

namespace p2original { namespace pelplant {
// Only the audited static, flattened bank is admitted. The bank owns topology,
// materials and textures; this object owns every field the pose writer and
// static updateAnim mutate. Never reload a Shape or delete borrowed resources.
class Geometry {
public:
 static bool admits(const Shape& bank){
  return bank.mJointCount==1&&bank.mJointList&&bank.mJointList[0].mParentIndex==-1
   &&bank.mEnvelopeCount==0&&bank.mAnimMtxCount==1&&bank.mCurrentAnimation
   &&bank.mCurrentAnimation->mData&&bank.mCurrentAnimation->mData->mTotalFrameCount==0
   &&bank.mCurrentAnimation->mData->mJointCount==1
   &&bank.mVertexCount>0&&bank.mNormalCount>0&&bank.mVertexList&&bank.mNormalList
   &&bank.mJointList[0].mScale.x==1&&bank.mJointList[0].mScale.y==1&&bank.mJointList[0].mScale.z==1
   &&bank.mJointList[0].mRotation.x==0&&bank.mJointList[0].mRotation.y==0&&bank.mJointList[0].mRotation.z==0
   &&bank.mJointList[0].mTranslation.x==0&&bank.mJointList[0].mTranslation.y==0&&bank.mJointList[0].mTranslation.z==0;
 }
 explicit Geometry(const Shape& bank):shape(bank),root(bank.mJointList[0]),
  vertices(new Vector3f[bank.mVertexCount]),normals(new Vector3f[bank.mNormalCount]){
  std::copy(bank.mVertexList,bank.mVertexList+bank.mVertexCount,vertices.get());
  std::copy(bank.mNormalList,bank.mNormalList+bank.mNormalCount,normals.get());
  shape.mVertexList=vertices.get();shape.mNormalList=normals.get();
  shape.mJointList=&root;root.mParentShape=&shape;
  // Borrow the immutable native Null Anim, with an owned clock/context.
  // Its zero-frame path populates gfx matrices as ordinary static Shapes do.
  context.mData=bank.mCurrentAnimation->mData;
  shape.mCurrentAnimation=&context;overrideContext=&context;
  shape.mAnimOverrides=&overrideContext;shape.mBackupAnimOverrides=nullptr;
  shape.mFrameCacher=nullptr;shape.mAnimMatrices=nullptr;
  shape.mParent=shape.mNext=shape.mChild=nullptr;
  // Prevent deferred alpha-cache records retaining a released geometry shell.
  shape.mShapeFlags|=ShapeFlags::AlwaysRedraw;
 }
 ~Geometry(){
  pc_gfx_forget_dynamic_vertex_range(vertices.get(),size_t(shape.mVertexCount)*sizeof(Vector3f));
  pc_gfx_forget_dynamic_vertex_range(normals.get(),size_t(shape.mNormalCount)*sizeof(Vector3f));
 }
 Geometry(const Geometry&)=delete;
 Geometry& operator=(const Geometry&)=delete;
 Shape shape;
private:
 Joint root;
 AnimContext context;
 AnimContext* overrideContext=nullptr;
 std::unique_ptr<Vector3f[]> vertices,normals;
};
} }
