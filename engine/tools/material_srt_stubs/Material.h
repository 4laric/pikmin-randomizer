#pragma once
using u8=unsigned char;using u32=unsigned;
class Texture {};
struct TexAttr {Texture* mTexture=nullptr;};
struct Matrix4f { float mMtx[4][4]{}; };
struct PVWTextureData {
 Texture* mTexture=nullptr;
 unsigned _UNUSED10=0,mAnimationFactor=255,mTotalFrameCount=0;
 float mScaleX=1,mScaleY=1,mRotationZ=0,mTranslationX=0,mTranslationY=0,mPivotX=0,mPivotY=0;
 Matrix4f mAnimatedTexMtx;
};
struct PVWTexGenData { unsigned mTexCoordID=0,mTexGenType=1,mTexGenSrc=4,mMatrixType=10; };
struct PVWTextureInfo { int mTextureDataCount=1,mTexGenDataCount=1,mTevStageCount=0;PVWTextureData* mTextureData=nullptr;PVWTexGenData* mTexGenData=nullptr; };
struct PVWCombiner {u8 mInArgA=15,mInArgB=8,mInArgC=10,mInArgD=15,mTevOp=0,mBias=0,mScale=0,mDoClamp=1,mOutReg=0;};
struct PVWTevStage {u8 mTexCoordID=0,mTexMapID=0,mChannelID=4;PVWCombiner mTevColorCombiner,mTevAlphaCombiner;};
struct PVWTevInfo {unsigned mTevStageCount=1;PVWTevStage* mTevStages=nullptr;};
struct PVWLightingInfo {unsigned mCtrlFlag=0;};
enum { MATFLAG_PVW=1 };
struct Material { unsigned mFlags=MATFLAG_PVW;PVWTextureInfo mTextureInfo;PVWTevInfo* mTevInfo=nullptr;u8* mDisplayListPtr=nullptr;PVWLightingInfo mLightingInfo; };
class Graphics;
