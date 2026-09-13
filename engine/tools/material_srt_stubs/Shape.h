#pragma once
#include "Graphics.h"
#include <cassert>
class Shape {
public:
 Material* mMaterialList=nullptr;int mMaterialCount=0,draws=0;float expected=1,expectedSecond=0;bool throwOnDraw=false;
 void drawshape(Graphics& g,Camera&,void*){
  assert(g.clears%2==1);++draws;
  assert(mMaterialList[0].mTextureInfo.mTextureData[0].mAnimatedTexMtx.mMtx[0][0]==expected);
  if(expectedSecond)assert(mMaterialList[1].mTextureInfo.mTextureData[0].mAnimatedTexMtx.mMtx[0][0]==expectedSecond);
  if(throwOnDraw)throw 1;
 }
};
