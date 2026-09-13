#pragma once
struct Matrix4f { float mMtx[4][4]{}; };
struct PVWTextureData {
 unsigned _UNUSED10=0,mAnimationFactor=255,mTotalFrameCount=0;
 float mScaleX=1,mScaleY=1,mRotationZ=0,mTranslationX=0,mTranslationY=0,mPivotX=0,mPivotY=0;
 Matrix4f mAnimatedTexMtx;
};
struct PVWTexGenData { unsigned mTexCoordID=0,mTexGenType=1,mTexGenSrc=4,mMatrixType=10; };
struct PVWTextureInfo { int mTextureDataCount=1,mTexGenDataCount=1;PVWTextureData* mTextureData=nullptr;PVWTexGenData* mTexGenData=nullptr; };
enum { MATFLAG_PVW=1 };
struct Material { unsigned mFlags=MATFLAG_PVW;PVWTextureInfo mTextureInfo; };
class Graphics;
