#pragma once
#include "pc_p2_material_srt.h"
#include "Material.h"
#include <cstring>
class Shape;

namespace p2material {
bool draw(Shape&, Graphics&, unsigned materialIndex, const Sample&);

// Draw-thread scope for ONE explicitly selected, single-texgen material.
// Construct immediately before drawshape; destruction restores shared state.
class ScopedSrt {
 Material* material_=nullptr;
 bool env_=false;
 PVWTextureData saved_;
 PVWTexGenData savedGen_;
public:
 ScopedSrt(Material& material,const Sample& sample){
  if(!(material.mFlags & MATFLAG_PVW))return;
  auto& info=material.mTextureInfo;
  if(info.mTextureDataCount!=1||info.mTexGenDataCount!=1||!info.mTextureData||!info.mTexGenData)return;
  auto& data=info.mTextureData[0];auto& gen=info.mTexGenData[0];
  if(gen.mTexGenType!=1||gen.mTexCoordID!=0||data.mTotalFrameCount!=0)return;
  const bool env=data._UNUSED10==0xE6;
  if(env?(gen.mTexGenSrc!=1||data.mAnimationFactor==255||sample.rotation!=0||data.mRotationZ!=0):gen.mTexGenSrc!=4)return;
  double m[2][3];if(!matrix(sample,m))return;
  // Only save fields we will write. Static MOD caches may be uninitialized.
  savedGen_=gen;saved_.mAnimationFactor=data.mAnimationFactor;
  if(!env) {
   // The cache can be indeterminate for a static MOD. Preserve bytes, not floats.
   std::memcpy(&saved_.mAnimatedTexMtx,&data.mAnimatedTexMtx,sizeof(data.mAnimatedTexMtx));
   for(int i=0;i<4;++i)for(int j=0;j<4;++j)data.mAnimatedTexMtx.mMtx[i][j]=i==j?1.0f:0.0f;
   for(int i=0;i<2;++i){data.mAnimatedTexMtx.mMtx[i][0]=float(m[i][0]);data.mAnimatedTexMtx.mMtx[i][1]=float(m[i][1]);data.mAnimatedTexMtx.mMtx[i][3]=float(m[i][2]);}
   // Host raw UV source is (s,t,0,1), so translation belongs in column 3.
  }else{
   saved_.mScaleX=data.mScaleX;saved_.mScaleY=data.mScaleY;
   saved_.mTranslationX=data.mTranslationX;saved_.mTranslationY=data.mTranslationY;
   saved_.mPivotX=data.mPivotX;saved_.mPivotY=data.mPivotY;
   // Existing marked envmap path composes these source values with normals.
   data.mScaleX=float(sample.sx);data.mScaleY=float(sample.sy);
   data.mTranslationX=float(sample.tx);data.mTranslationY=float(sample.ty);
   data.mPivotX=float(sample.cx);data.mPivotY=float(sample.cy);
  }
  data.mAnimationFactor=0;gen.mMatrixType=0;
  material_=&material;env_=env;
 }
 ~ScopedSrt(){
  if(!material_)return;
  auto& data=material_->mTextureInfo.mTextureData[0];
  if(env_){
   data.mScaleX=saved_.mScaleX;data.mScaleY=saved_.mScaleY;
   data.mTranslationX=saved_.mTranslationX;data.mTranslationY=saved_.mTranslationY;
   data.mPivotX=saved_.mPivotX;data.mPivotY=saved_.mPivotY;
  }else{
   std::memcpy(&data.mAnimatedTexMtx,&saved_.mAnimatedTexMtx,sizeof(data.mAnimatedTexMtx));
  }
  data.mAnimationFactor=saved_.mAnimationFactor;material_->mTextureInfo.mTexGenData[0]=savedGen_;
 }
 ScopedSrt(const ScopedSrt&)=delete;ScopedSrt& operator=(const ScopedSrt&)=delete;
 bool applied()const{return material_!=nullptr;}
};
}
