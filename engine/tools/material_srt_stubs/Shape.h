#pragma once
#include "Graphics.h"
#include <cassert>
class Shape {
public:
 Material* mMaterialList=nullptr;int mMaterialCount=0,draws=0;float expected=1,expectedSecond=0;bool throwOnDraw=false;
 TexAttr* mTexAttrList=nullptr;int mTexAttrCount=0;bool specularFixture=false,specularExpected=true;
 void drawshape(Graphics& g,Camera&,void*){
  assert(g.clears%2==1);++draws;
  if(specularFixture){
   auto& m=mMaterialList[0];assert(m.mTextureInfo.mTextureDataCount==2&&m.mTextureInfo.mTexGenDataCount==2);
   assert(m.mTevInfo->mTevStageCount==unsigned(specularExpected?2:1)&&m.mDisplayListPtr==nullptr&&m.mLightingInfo.mCtrlFlag==0x93);
   assert(m.mTevInfo->mTevStages[0].mTevColorCombiner.mScale==1);
   assert(m.mTextureInfo.mTextureData[1]._UNUSED10==0xE6&&m.mTextureInfo.mTextureData[1].mScaleX==-.5f);
   assert(m.mTevInfo->mTevStages[1].mTevColorCombiner.mInArgD==0&&m.mTevInfo->mTevStages[1].mChannelID==5);
  }else assert(mMaterialList[0].mTextureInfo.mTextureData[0].mAnimatedTexMtx.mMtx[0][0]==expected);
  if(expectedSecond)assert(mMaterialList[1].mTextureInfo.mTextureData[0].mAnimatedTexMtx.mMtx[0][0]==expectedSecond);
  if(throwOnDraw)throw 1;
 }
};
