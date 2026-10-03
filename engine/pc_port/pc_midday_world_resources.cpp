#if defined(PIKI_PC_PORT)
#include "pc_midday_world_resources.h"
#include "Shape.h"
#include "Material.h"
#include "CreatureCollPart.h"
#include "Collision.h"
#include "Joint.h"
namespace pc_midday {
bool world_texture_data_fields(PVWTextureData& s,ActorArchive& ar){
 if(!ar.field("mSourceAttrIndex",s.mSourceAttrIndex))return false;
 if(!ar.ref("mTextureAttribute",RefKind::TexAttr,s.mTextureAttribute))return false;
 if(!ar.ref("mTexture",RefKind::Texture,s.mTexture))return false;
 if(!ar.field("mAnimationFactor",s.mAnimationFactor))return false;
 if(!ar.field("mIsMatrixDirty",s.mIsMatrixDirty))return false;
 if(!ar.field("mScaleX",s.mScaleX))return false;
 if(!ar.field("mScaleY",s.mScaleY))return false;
 if(!ar.field("mRotationZ",s.mRotationZ))return false;
 if(!ar.field("mTranslationX",s.mTranslationX))return false;
 if(!ar.field("mTranslationY",s.mTranslationY))return false;
 if(!ar.field("mPivotX",s.mPivotX))return false;
 if(!ar.field("mPivotY",s.mPivotY))return false;
 if(!ar.field("mTotalFrameCount",s.mTotalFrameCount))return false;
 if(!ar.field("mAnimSpeed",s.mAnimSpeed))return false;
 if(!ar.field("mCurrentFrame",s.mCurrentFrame))return false;
 bool matrixReady=ar.mode()==Mode::Capture&&s.mIsMatrixDirty;
 if(!ar.scalar("matrixReady",ScalarKind::Bool,&matrixReady))return false;
 if(matrixReady){
 if(!ar.field("mAnimatedTexMtx.matrix.0.0",s.mAnimatedTexMtx.mMtx[0][0]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.0.1",s.mAnimatedTexMtx.mMtx[0][1]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.0.2",s.mAnimatedTexMtx.mMtx[0][2]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.0.3",s.mAnimatedTexMtx.mMtx[0][3]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.1.0",s.mAnimatedTexMtx.mMtx[1][0]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.1.1",s.mAnimatedTexMtx.mMtx[1][1]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.1.2",s.mAnimatedTexMtx.mMtx[1][2]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.1.3",s.mAnimatedTexMtx.mMtx[1][3]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.2.0",s.mAnimatedTexMtx.mMtx[2][0]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.2.1",s.mAnimatedTexMtx.mMtx[2][1]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.2.2",s.mAnimatedTexMtx.mMtx[2][2]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.2.3",s.mAnimatedTexMtx.mMtx[2][3]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.3.0",s.mAnimatedTexMtx.mMtx[3][0]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.3.1",s.mAnimatedTexMtx.mMtx[3][1]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.3.2",s.mAnimatedTexMtx.mMtx[3][2]))return false;
 if(!ar.field("mAnimatedTexMtx.matrix.3.3",s.mAnimatedTexMtx.mMtx[3][3]))return false;
 }
 return true; }
bool world_tev_fields(PVWTevInfo& s,ActorArchive& ar){
 if(!ar.field("mTevColRegs.0.mAnimatedColor.r",s.mTevColRegs[0].mAnimatedColor.r))return false;
 if(!ar.field("mTevColRegs.0.mAnimatedColor.g",s.mTevColRegs[0].mAnimatedColor.g))return false;
 if(!ar.field("mTevColRegs.0.mAnimatedColor.b",s.mTevColRegs[0].mAnimatedColor.b))return false;
 if(!ar.field("mTevColRegs.0.mAnimatedColor.a",s.mTevColRegs[0].mAnimatedColor.a))return false;
 if(!ar.field("mTevColRegs.0.mCurrentAnimFrame",s.mTevColRegs[0].mCurrentAnimFrame))return false;
 if(!ar.field("mTevColRegs.0.mAnimSpeed",s.mTevColRegs[0].mAnimSpeed))return false;
 if(!ar.field("mTevColRegs.0.mAnimFrameCount",s.mTevColRegs[0].mAnimFrameCount))return false;
 if(!ar.field("mTevColRegs.1.mAnimatedColor.r",s.mTevColRegs[1].mAnimatedColor.r))return false;
 if(!ar.field("mTevColRegs.1.mAnimatedColor.g",s.mTevColRegs[1].mAnimatedColor.g))return false;
 if(!ar.field("mTevColRegs.1.mAnimatedColor.b",s.mTevColRegs[1].mAnimatedColor.b))return false;
 if(!ar.field("mTevColRegs.1.mAnimatedColor.a",s.mTevColRegs[1].mAnimatedColor.a))return false;
 if(!ar.field("mTevColRegs.1.mCurrentAnimFrame",s.mTevColRegs[1].mCurrentAnimFrame))return false;
 if(!ar.field("mTevColRegs.1.mAnimSpeed",s.mTevColRegs[1].mAnimSpeed))return false;
 if(!ar.field("mTevColRegs.1.mAnimFrameCount",s.mTevColRegs[1].mAnimFrameCount))return false;
 if(!ar.field("mTevColRegs.2.mAnimatedColor.r",s.mTevColRegs[2].mAnimatedColor.r))return false;
 if(!ar.field("mTevColRegs.2.mAnimatedColor.g",s.mTevColRegs[2].mAnimatedColor.g))return false;
 if(!ar.field("mTevColRegs.2.mAnimatedColor.b",s.mTevColRegs[2].mAnimatedColor.b))return false;
 if(!ar.field("mTevColRegs.2.mAnimatedColor.a",s.mTevColRegs[2].mAnimatedColor.a))return false;
 if(!ar.field("mTevColRegs.2.mCurrentAnimFrame",s.mTevColRegs[2].mCurrentAnimFrame))return false;
 if(!ar.field("mTevColRegs.2.mAnimSpeed",s.mTevColRegs[2].mAnimSpeed))return false;
 if(!ar.field("mTevColRegs.2.mAnimFrameCount",s.mTevColRegs[2].mAnimFrameCount))return false;
 if(!ar.field("mKonstColors.0.r",s.mKonstColors[0].r))return false;
 if(!ar.field("mKonstColors.0.g",s.mKonstColors[0].g))return false;
 if(!ar.field("mKonstColors.0.b",s.mKonstColors[0].b))return false;
 if(!ar.field("mKonstColors.0.a",s.mKonstColors[0].a))return false;
 if(!ar.field("mKonstColors.1.r",s.mKonstColors[1].r))return false;
 if(!ar.field("mKonstColors.1.g",s.mKonstColors[1].g))return false;
 if(!ar.field("mKonstColors.1.b",s.mKonstColors[1].b))return false;
 if(!ar.field("mKonstColors.1.a",s.mKonstColors[1].a))return false;
 if(!ar.field("mKonstColors.2.r",s.mKonstColors[2].r))return false;
 if(!ar.field("mKonstColors.2.g",s.mKonstColors[2].g))return false;
 if(!ar.field("mKonstColors.2.b",s.mKonstColors[2].b))return false;
 if(!ar.field("mKonstColors.2.a",s.mKonstColors[2].a))return false;
 if(!ar.field("mKonstColors.3.r",s.mKonstColors[3].r))return false;
 if(!ar.field("mKonstColors.3.g",s.mKonstColors[3].g))return false;
 if(!ar.field("mKonstColors.3.b",s.mKonstColors[3].b))return false;
 if(!ar.field("mKonstColors.3.a",s.mKonstColors[3].a))return false;
 return true; }
bool world_material_fields(Material& s,ActorArchive& ar){
 if(!ar.field("mIndex",s.mIndex))return false;
 if(!ar.field("mFlags",s.mFlags))return false;
 if(!ar.field("mTextureIndex",s.mTextureIndex))return false;
 if(!ar.ref("mAttribute",RefKind::TexAttr,s.mAttribute))return false;
 if(!ar.ref("mTexture",RefKind::Texture,s.mTexture))return false;
 if(!ar.ref("mEnvMapTexture",RefKind::Texture,s.mEnvMapTexture))return false;
 if(!ar.field("mColourInfo.mColour.r",s.mColourInfo.mColour.r))return false;
 if(!ar.field("mColourInfo.mColour.g",s.mColourInfo.mColour.g))return false;
 if(!ar.field("mColourInfo.mColour.b",s.mColourInfo.mColour.b))return false;
 if(!ar.field("mColourInfo.mColour.a",s.mColourInfo.mColour.a))return false;
 if(!ar.field("mColourInfo.mCurrentFrame",s.mColourInfo.mCurrentFrame))return false;
 if(!ar.field("mLightingInfo.mCtrlFlag",s.mLightingInfo.mCtrlFlag))return false;
 if(!ar.field("mLightingInfo.mNumChans",s.mLightingInfo.mNumChans))return false;
 u32 flags=ar.mode()==Mode::Capture?s.mFlags:0;
 if(!ar.scalar("pvwFlags",ScalarKind::U32,&flags))return false;
 if(flags&1){
  int count=ar.mode()==Mode::Capture?int(s.mTextureInfo.mTextureDataCount):0;
  if(!ar.scalar("textureCount",ScalarKind::S32,&count)||count<0||count>256||count!=int(s.mTextureInfo.mTextureDataCount)||(count&&!s.mTextureInfo.mTextureData))return ar.fail("material texture allocation mismatch");
  if(!ar.field("colourSpeed",s.mColourInfo.mSpeed)||!ar.field("textureScale",s.mTextureInfo.mScale)||!ar.ref("tev",RefKind::PVWTevInfo,s.mTevInfo))return false;
  for(int i=0;i<count;++i){auto* entry=&s.mTextureInfo.mTextureData[i];if(!ar.ref(("texture."+std::to_string(i)).c_str(),RefKind::PVWTextureData,entry)||entry!=&s.mTextureInfo.mTextureData[i])return ar.fail("material texture alias mismatch");}
 }
 return true; }
bool world_materials_fields(ShapeDynMaterials& s,ActorArchive& ar){
 int count=ar.mode()==Mode::Capture?s.mMatCount:0;
 if(!ar.scalar("count",ScalarKind::S32,&count)||count<0||count>256||count!=s.mMatCount||(count&&!s.mMaterials))return ar.fail("material allocation mismatch");
 if(!ar.ref("next",RefKind::ShapeDynMaterials,s.mNext)||!ar.ref("model",RefKind::Shape,s.mModel))return false;
 for(int i=0;i<count;++i){auto* entry=&s.mMaterials[i];if(!ar.ref(("material."+std::to_string(i)).c_str(),RefKind::Material,entry)||entry!=&s.mMaterials[i])return ar.fail("material array alias mismatch");}
 return true;
}

static bool matrix(Matrix4f& m,ActorArchive& ar){for(int i=0;i<4;++i)for(int j=0;j<4;++j)if(!ar.field((std::to_string(i)+"."+std::to_string(j)).c_str(),m.mMtx[i][j]))return false;return true;}
static bool plane(Plane& p,ActorArchive& ar){return ar.field("normal",p.mNormal)&&ar.field("offset",p.mOffset);}
bool world_dyn_shape_fields(DynCollShape& s,ActorArchive& ar){
 if(!ar.field("contacts",s.mContactTickCount)||!ar.field("lastContact",s.mLastContactTick)||!ar.ref("creature",RefKind::Creature,s.mCreature)||!ar.ref("model",RefKind::Shape,s.mCollisionModel))return false;
 bool model=ar.mode()==Mode::Capture&&s.mCollisionModel;if(!ar.scalar("hasModel",ScalarKind::Bool,&model)||model!=(s.mCollisionModel!=nullptr))return ar.fail("dynamic collision model allocation mismatch");
 if(!ar.field("scale",s.mLocalSRT.s)||!ar.field("rotation",s.mLocalSRT.r)||!ar.field("translation",s.mLocalSRT.t))return false;
 {PrefixArchive a(ar,"transform");if(!matrix(s.mTransformMtx,a))return false;}
 if(!model)return true;
 int vertices=ar.mode()==Mode::Capture?s.mCollisionModel->mVertexCount:0,triangles=ar.mode()==Mode::Capture?s.mCollisionModel->mTriCount:0,joints=ar.mode()==Mode::Capture?s.mCollisionModel->mJointCount:0,groups=ar.mode()==Mode::Capture?s.mCollisionModel->mBaseRoomCount:0;
 if(!ar.scalar("vertices",ScalarKind::S32,&vertices)||!ar.scalar("triangles",ScalarKind::S32,&triangles)||!ar.scalar("joints",ScalarKind::S32,&joints)||!ar.scalar("groups",ScalarKind::S32,&groups)||vertices<0||vertices>65536||triangles<0||triangles>32767||joints<0||joints>4096||groups<0||groups>4096||vertices!=s.mCollisionModel->mVertexCount||triangles!=s.mCollisionModel->mTriCount||joints!=s.mCollisionModel->mJointCount||groups!=s.mCollisionModel->mBaseRoomCount||(vertices&&!s.mVertexList)||(triangles&&!s.mCollTriList)||(joints&&!s.mJointVisibility)||(groups&&(!s.mCollGroupList||s.mCollGroupCount!=groups)))return ar.fail("dynamic collision storage mismatch");
 if(!ar.field("boundsMin",s.mBoundingBox.mMin)||!ar.field("boundsMax",s.mBoundingBox.mMax))return false;
 {PrefixArchive a(ar,"inverse");if(!matrix(s.mInverseMatrix,a))return false;}{PrefixArchive a(ar,"view");if(!matrix(s.mViewMtx,a))return false;}
 for(int i=0;i<vertices;++i)if(!ar.field(("vertex."+std::to_string(i)).c_str(),s.mVertexList[i]))return false;
 for(int i=0;i<joints;++i)if(!ar.field(("visible."+std::to_string(i)).c_str(),s.mJointVisibility[i]))return false;
 for(int i=0;i<triangles;++i){auto& t=s.mCollTriList[i];PrefixArchive a(ar,("triangle."+std::to_string(i)).c_str());if(!a.field("map",t.mMapCode)||!a.field("room",t.mCollRoomIndex))return false;{PrefixArchive p(a,"plane");if(!plane(t.mTriangle,p))return false;}for(int j=0;j<3;++j){if(!a.field(("vertex."+std::to_string(j)).c_str(),t.mVertexIndices[j])||!a.field(("adjacent."+std::to_string(j)).c_str(),t.mAdjacentTriIndices[j]))return false;PrefixArchive p(a,("edge."+std::to_string(j)).c_str());if(!plane(t.mEdgePlanes[j],p))return false;}}
 for(int i=0;i<groups;++i){auto* g=s.mCollGroupList[i];if(!g)return ar.fail("missing dynamic collision group");PrefixArchive a(ar,("group."+std::to_string(i)).c_str());if(!a.ref("identity",RefKind::CollGroup,g)||g!=s.mCollGroupList[i])return ar.fail("collision group allocation alias");int count=ar.mode()==Mode::Capture?g->mTriCount:0;if(!a.scalar("count",ScalarKind::S32,&count)||count<0||count>triangles||count!=g->mTriCount||(count&&!g->mTriangleList))return ar.fail("group triangle allocation");s16 far=ar.mode()==Mode::Capture?g->mFarCulledTriCount:0;if(!a.scalar("farCount",ScalarKind::S16,&far)||far<0||far>count||far!=g->mFarCulledTriCount||!a.field("joint",g->mJointIndex)||!a.ref("model",RefKind::Shape,g->mModel)||!a.ref("platform",RefKind::DynCollObject,g->mPlatCollision)||!a.ref("next",RefKind::CollGroup,g->mNextCollGroup))return false;
 bool distances=ar.mode()==Mode::Capture&&g->mFarCulledTriDistances;if(!a.scalar("distances",ScalarKind::Bool,&distances)||distances!=(g->mFarCulledTriDistances!=nullptr))return ar.fail("group distance allocation");
 // Group vertices are an alias into this collider, or null before first refresh.
 bool bound=ar.mode()==Mode::Capture&&g->mVertexList;if(!a.scalar("verticesBound",ScalarKind::Bool,&bound))return false;if(ar.mode()==Mode::Capture&&bound&&g->mVertexList!=s.mVertexList)return ar.fail("foreign group vertex storage");if(ar.mode()==Mode::Apply)g->mVertexList=bound?s.mVertexList:nullptr;
 for(int j=0;j<count;++j){int index=-1;if(ar.mode()==Mode::Capture){for(int k=0;k<triangles;++k)if(g->mTriangleList[j]==&s.mCollTriList[k]){index=k;break;}}if(!a.scalar(("triangle."+std::to_string(j)).c_str(),ScalarKind::S32,&index)||index<0||index>=triangles)return ar.fail("foreign group triangle");if(ar.mode()==Mode::Apply)g->mTriangleList[j]=&s.mCollTriList[index];}if(far&&!distances)return ar.fail("missing far culling distances");for(int j=0;j<far;++j)if(!a.field(("distance."+std::to_string(j)).c_str(),g->mFarCulledTriDistances[j]))return false;if(ar.mode()==Mode::Apply)g->mFarCulledTriCount=far;}
 return true;
}
bool world_platform_fields(CreaturePlatMgr& s,ActorArchive& ar){int count=ar.mode()==Mode::Capture?s.mPartCount:0;if(!ar.scalar("count",ScalarKind::S32,&count)||count<0||count>16||count!=s.mPartCount)return ar.fail("platform allocation mismatch");if(!count)return true;if(!ar.ref("model",RefKind::Shape,s.mParentCreatureModel))return false;for(int i=0;i<count;++i){auto* part=s.mPlatParts[i];if(!part)return ar.fail("missing platform part");PrefixArchive a(ar,("part."+std::to_string(i)).c_str());if(!a.ref("identity",RefKind::DynCollObject,part)||part!=s.mPlatParts[i]||!a.field("joint",part->mJointIndex)||!a.ref("parent",RefKind::Creature,part->mParentCreature))return false;if(!world_dyn_shape_fields(*part,a))return false;}return true;}
bool world_joint_fields(Joint& s,ActorArchive& ar){
 if(!ar.field("visible",s.mIsVisible)||!ar.field("scale",s.mScale)||!ar.field("rotation",s.mRotation)||!ar.field("translation",s.mTranslation)||!ar.field("boundsMin",s.mBounds.mMin)||!ar.field("boundsMax",s.mBounds.mMax)||!ar.ref("shape",RefKind::Shape,s.mParentShape))return false;
 {PrefixArchive a(ar,"animation");if(!matrix(s.mAnimMatrix,a))return false;}{PrefixArchive a(ar,"inverse");if(!matrix(s.mInverseAnimMatrix,a))return false;}return true;
}
}
#endif
