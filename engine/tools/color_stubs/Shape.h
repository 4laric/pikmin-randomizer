#pragma once
#include "Material.h"
#include "Graphics.h"
#include <cassert>
struct Shape {Material* mMaterialList=nullptr;int mMaterialCount=0,draws=0,expected=0,expectedK=-1;bool throws=false;
 void drawshape(Graphics&,Camera&,void*){assert(mMaterialList[0].mTevInfo->mTevColRegs[0].mAnimatedColor.r==expected);if(expectedK>=0)assert(mMaterialList[0].mTevInfo->mKonstColors[1].r==expectedK);++draws;if(throws)throw 1;}
};
