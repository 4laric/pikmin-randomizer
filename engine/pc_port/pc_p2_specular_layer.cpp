#include "pc_p2_specular_layer.h"
#include "Shape.h"
#include "Material.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include <cstring>

namespace p2material {
bool drawSpecular(Shape& shape,Graphics& gfx,unsigned index,unsigned texture,const Sample& sample,bool enabled){
 if(!gfx.mCamera||!shape.mMaterialList||shape.mMaterialCount<=0||index>=unsigned(shape.mMaterialCount)||
    !shape.mTexAttrList||shape.mTexAttrCount<=0||texture>=unsigned(shape.mTexAttrCount)||sample.rotation!=0)return false;
 auto& mat=shape.mMaterialList[index];auto& info=mat.mTextureInfo;
 if(!(mat.mFlags&MATFLAG_PVW)||!mat.mTevInfo||mat.mTevInfo->mTevStageCount!=1||!mat.mTevInfo->mTevStages||
    info.mTextureDataCount!=1||info.mTexGenDataCount!=1||!info.mTextureData||!info.mTexGenData||
    info.mTexGenData[0].mTexGenSrc!=4||info.mTexGenData[0].mTexGenType!=1||info.mTexGenData[0].mTexCoordID!=0||
    info.mTextureData[0].mTotalFrameCount!=0||!info.mTextureData[0].mTexture||!shape.mTexAttrList[texture].mTexture)return false;
 const auto& base=mat.mTevInfo->mTevStages[0];const auto& rgb=base.mTevColorCombiner;
 if(base.mTexCoordID!=0||base.mTexMapID!=0||base.mChannelID!=4||rgb.mInArgA!=15||rgb.mInArgB!=8||rgb.mInArgC!=10||
    rgb.mInArgD!=15||rgb.mTevOp!=0||rgb.mBias!=0||rgb.mScale>1||rgb.mDoClamp!=1||rgb.mOutReg!=0)return false;
 double checked[2][3];if(!matrix(sample,checked))return false;
 struct Restore {
  Material& mat;Graphics& gfx;PVWTextureInfo info;PVWTevInfo* tev;u8* list;u32 lighting;
  Restore(Material& m,Graphics& g):mat(m),gfx(g),info(m.mTextureInfo),tev(m.mTevInfo),list(m.mDisplayListPtr),lighting(m.mLightingInfo.mCtrlFlag){}
  ~Restore(){mat.mTextureInfo=info;mat.mTevInfo=tev;mat.mDisplayListPtr=list;mat.mLightingInfo.mCtrlFlag=lighting;gfx.useMaterial(nullptr);}
 } restore(mat,gfx);
 PVWTextureData data[2];
 // Preserve the potentially indeterminate static texture-matrix cache as bytes.
 std::memcpy(static_cast<void*>(&data[0]),&info.mTextureData[0],sizeof(PVWTextureData));
 data[0].mAnimationFactor=255;data[0]._UNUSED10=0;
 data[1].mTexture=shape.mTexAttrList[texture].mTexture;data[1]._UNUSED10=0xE6;
 data[1].mAnimationFactor=0;data[1].mTotalFrameCount=0;data[1].mRotationZ=0;
 data[1].mScaleX=float(sample.sx);data[1].mScaleY=float(sample.sy);
 data[1].mTranslationX=float(sample.tx);data[1].mTranslationY=float(sample.ty);
 data[1].mPivotX=float(sample.cx);data[1].mPivotY=float(sample.cy);
 PVWTexGenData gens[2]={{0,1,4,10},{1,1,1,0}};
 PVWTevStage stages[2];stages[0]=mat.mTevInfo->mTevStages[0];stages[1]=stages[0];
 // Source Queen stage 0 doubles its diffuse product; stage 1 adds TEXC*RASC.
 stages[0].mTevColorCombiner.mScale=1;
 stages[1].mTexCoordID=1;stages[1].mTexMapID=1;stages[1].mChannelID=5;
 auto& color=stages[1].mTevColorCombiner;
 color.mInArgA=15;color.mInArgB=10;color.mInArgC=8;color.mInArgD=0;
 color.mTevOp=0;color.mBias=0;color.mScale=0;color.mDoClamp=1;color.mOutReg=0;
 auto& alpha=stages[1].mTevAlphaCombiner;
 alpha.mInArgA=7;alpha.mInArgB=7;alpha.mInArgC=7;alpha.mInArgD=0;
 alpha.mTevOp=0;alpha.mBias=0;alpha.mScale=0;alpha.mDoClamp=1;alpha.mOutReg=0;
 PVWTevInfo tev;
 std::memcpy(static_cast<void*>(&tev),mat.mTevInfo,sizeof(PVWTevInfo));tev.mTevStageCount=enabled?2:1;tev.mTevStages=stages;
 info.mTextureDataCount=2;info.mTexGenDataCount=2;info.mTevStageCount=1;info.mTextureData=data;info.mTexGenData=gens;
 mat.mTevInfo=&tev;mat.mDisplayListPtr=nullptr;mat.mLightingInfo.mCtrlFlag=0x93;
 gfx.useMaterial(nullptr);shape.drawshape(gfx,*gfx.mCamera,nullptr);
 return true;
}
}
