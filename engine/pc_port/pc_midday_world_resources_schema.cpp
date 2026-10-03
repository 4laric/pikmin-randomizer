#include "pc_midday_world_resources.h"
namespace pc_midday {
bool world_texture_data_schema(const ActorFields& f,const std::string& prefix,std::vector<FieldSchema>& out,std::string& error){ const auto p=prefix.empty()?"":prefix+".";
 out.push_back(FieldSchema::value((p+"mSourceAttrIndex").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::ref((p+"mTextureAttribute").c_str(),RefKind::TexAttr,true,"TexAttr",ReferenceOwnership::Content));
 out.push_back(FieldSchema::ref((p+"mTexture").c_str(),RefKind::Texture,true,"Texture",ReferenceOwnership::Content));
 out.push_back(FieldSchema::value((p+"mAnimationFactor").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mIsMatrixDirty").c_str(),ScalarKind::Bool));
 out.push_back(FieldSchema::value((p+"mScaleX").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mScaleY").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mRotationZ").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTranslationX").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTranslationY").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mPivotX").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mPivotY").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTotalFrameCount").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::value((p+"mAnimSpeed").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mCurrentFrame").c_str(),ScalarKind::F32));
 auto dirty=f.find(p+"mIsMatrixDirty"),ready=f.find(p+"matrixReady");if(dirty==f.end()||ready==f.end()||dirty->second.bits!=ready->second.bits||ready->second.bits>1){error="texture matrix readiness mismatch";return false;}
 out.push_back(FieldSchema::value((p+"matrixReady").c_str(),ScalarKind::Bool));if(ready->second.bits){
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.0.0").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.0.1").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.0.2").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.0.3").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.1.0").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.1.1").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.1.2").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.1.3").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.2.0").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.2.1").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.2.2").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.2.3").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.3.0").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.3.1").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.3.2").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mAnimatedTexMtx.matrix.3.3").c_str(),ScalarKind::F32));
 }
 return true; }
bool world_tev_schema(const ActorFields& f,const std::string& prefix,std::vector<FieldSchema>& out,std::string& error){ const auto p=prefix.empty()?"":prefix+".";
 out.push_back(FieldSchema::value((p+"mTevColRegs.0.mAnimatedColor.r").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.0.mAnimatedColor.g").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.0.mAnimatedColor.b").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.0.mAnimatedColor.a").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.0.mCurrentAnimFrame").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.0.mAnimSpeed").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.0.mAnimFrameCount").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.1.mAnimatedColor.r").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.1.mAnimatedColor.g").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.1.mAnimatedColor.b").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.1.mAnimatedColor.a").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.1.mCurrentAnimFrame").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.1.mAnimSpeed").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.1.mAnimFrameCount").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.2.mAnimatedColor.r").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.2.mAnimatedColor.g").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.2.mAnimatedColor.b").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.2.mAnimatedColor.a").c_str(),ScalarKind::S16));
 out.push_back(FieldSchema::value((p+"mTevColRegs.2.mCurrentAnimFrame").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.2.mAnimSpeed").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mTevColRegs.2.mAnimFrameCount").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::value((p+"mKonstColors.0.r").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.0.g").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.0.b").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.0.a").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.1.r").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.1.g").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.1.b").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.1.a").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.2.r").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.2.g").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.2.b").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.2.a").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.3.r").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.3.g").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.3.b").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mKonstColors.3.a").c_str(),ScalarKind::U8));
 return true; }
bool world_material_schema(const ActorFields& f,const std::string& prefix,std::vector<FieldSchema>& out,std::string& error){ const auto p=prefix.empty()?"":prefix+".";
 out.push_back(FieldSchema::value((p+"mIndex").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::value((p+"mFlags").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::value((p+"mTextureIndex").c_str(),ScalarKind::S32));
 out.push_back(FieldSchema::ref((p+"mAttribute").c_str(),RefKind::TexAttr,true,"TexAttr",ReferenceOwnership::Content));
 out.push_back(FieldSchema::ref((p+"mTexture").c_str(),RefKind::Texture,true,"Texture",ReferenceOwnership::Content));
 out.push_back(FieldSchema::ref((p+"mEnvMapTexture").c_str(),RefKind::Texture,true,"Texture",ReferenceOwnership::Content));
 out.push_back(FieldSchema::value((p+"mColourInfo.mColour.r").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mColourInfo.mColour.g").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mColourInfo.mColour.b").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mColourInfo.mColour.a").c_str(),ScalarKind::U8));
 out.push_back(FieldSchema::value((p+"mColourInfo.mCurrentFrame").c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::value((p+"mLightingInfo.mCtrlFlag").c_str(),ScalarKind::U32));
 out.push_back(FieldSchema::value((p+"mLightingInfo.mNumChans").c_str(),ScalarKind::U32));
 u32 flags=0,original=0;if(!actor_u32(f,(p+"pvwFlags").c_str(),flags,error)||!actor_u32(f,(p+"mFlags").c_str(),original,error)||flags!=original){error="material flags mismatch";return false;}
 out.push_back(FieldSchema::value((p+"pvwFlags").c_str(),ScalarKind::U32));
 if(flags&1){int count=0;if(!actor_i32(f,(p+"textureCount").c_str(),count,error)||count<0||count>256){error="material texture bounds";return false;}
 out.push_back(FieldSchema::value((p+"textureCount").c_str(),ScalarKind::S32));out.push_back(FieldSchema::value((p+"colourSpeed").c_str(),ScalarKind::F32));
 for(auto axis:{"x","y","z"})out.push_back(FieldSchema::value((p+"textureScale."+axis).c_str(),ScalarKind::F32));
 out.push_back(FieldSchema::ref((p+"tev").c_str(),RefKind::PVWTevInfo,false,"PVWTevInfo",ReferenceOwnership::AnyLive));
 for(int i=0;i<count;++i)out.push_back(FieldSchema::ref((p+"texture."+std::to_string(i)).c_str(),RefKind::PVWTextureData,false,"PVWTextureData",ReferenceOwnership::Content));
 }
 return true; }
bool world_materials_schema(const ActorFields& f,const std::string& prefix,std::vector<FieldSchema>& out,std::string& error){const auto p=prefix.empty()?"":prefix+".";
 int count=0;if(!actor_i32(f,(p+"count").c_str(),count,error)||count<0||count>256){error="material allocation bounds";return false;}
 out.push_back(FieldSchema::value((p+"count").c_str(),ScalarKind::S32));
 out.push_back(FieldSchema::ref((p+"next").c_str(),RefKind::ShapeDynMaterials,true,"ShapeDynMaterials",ReferenceOwnership::AnyLive));
 out.push_back(FieldSchema::ref((p+"model").c_str(),RefKind::Shape,count==0,"BaseShape",ReferenceOwnership::Content));
 for(int i=0;i<count;++i)out.push_back(FieldSchema::ref((p+"material."+std::to_string(i)).c_str(),RefKind::Material,false,"Material",ReferenceOwnership::AnyLive));return true;
}

namespace {
struct ResourceSchema {
 const ActorFields& f;std::string p;std::vector<FieldSchema>& out;std::string& e;
 ResourceSchema(const ActorFields& a,const std::string& prefix,std::vector<FieldSchema>& b,std::string& error):f(a),p(prefix.empty()?"":prefix+"."),out(b),e(error){}
 void val(const std::string& k,ScalarKind t){out.push_back(FieldSchema::value((p+k).c_str(),t));}
 void vec(const std::string& k){for(auto x:{"x","y","z"})val(k+"."+x,ScalarKind::F32);}
 void mat(const std::string& k){for(int i=0;i<4;++i)for(int j=0;j<4;++j)val(k+"."+std::to_string(i)+"."+std::to_string(j),ScalarKind::F32);}
 void plane(const std::string& k){vec(k+".normal");val(k+".offset",ScalarKind::F32);}
 void ref(const std::string& k,RefKind r,const char*t,ReferenceOwnership o,bool nullable){out.push_back(FieldSchema::ref((p+k).c_str(),r,nullable,t,o));}
 bool number(const std::string& k,ScalarKind t,int lo,int hi,int& n){auto i=f.find(p+k);if(i==f.end()||i->second.category!=FieldCategory::Scalar||i->second.scalar!=t){e="missing resource discriminator "+p+k;return false;}n=t==ScalarKind::S16?int(s16(i->second.bits)):int(s32(i->second.bits));if(n<lo||n>hi){e="resource bounds "+p+k;return false;}val(k,t);return true;}
};
}
bool world_dyn_shape_schema(const ActorFields& f,const std::string& prefix,std::vector<FieldSchema>& out,std::string& e){ResourceSchema s(f,prefix,out,e);int has=0;if(!s.number("hasModel",ScalarKind::Bool,0,1,has))return false;
 s.val("contacts",ScalarKind::U32);s.val("lastContact",ScalarKind::U32);s.ref("creature",RefKind::Creature,"Creature",ReferenceOwnership::AnyLive,true);s.ref("model",RefKind::Shape,"Shape",ReferenceOwnership::Content,!has);for(auto k:{"scale","rotation","translation"})s.vec(k);s.mat("transform");if(!has)return true;
 int vertices=0,triangles=0,joints=0,groups=0;if(!s.number("vertices",ScalarKind::S32,0,65536,vertices)||!s.number("triangles",ScalarKind::S32,0,32767,triangles)||!s.number("joints",ScalarKind::S32,0,4096,joints)||!s.number("groups",ScalarKind::S32,0,4096,groups))return false;
 s.vec("boundsMin");s.vec("boundsMax");s.mat("inverse");s.mat("view");for(int i=0;i<vertices;++i)s.vec("vertex."+std::to_string(i));for(int i=0;i<joints;++i)s.val("visible."+std::to_string(i),ScalarKind::Bool);
 for(int i=0;i<triangles;++i){auto p="triangle."+std::to_string(i)+".";s.val(p+"map",ScalarKind::U32);int n=0;if(!s.number(p+"room",ScalarKind::S16,-1,groups-1,n))return false;s.plane(p+"plane");for(int j=0;j<3;++j){auto k=std::to_string(j);if(!s.number(p+"vertex."+k,ScalarKind::U32,0,vertices-1,n)||!s.number(p+"adjacent."+k,ScalarKind::S16,-1,triangles-1,n))return false;s.plane(p+"edge."+k);}}
 for(int i=0;i<groups;++i){auto p="group."+std::to_string(i)+".";int count=0,far=0,dist=0,bound=0,joint=0;if(!s.number(p+"count",ScalarKind::S32,0,triangles,count)||!s.number(p+"farCount",ScalarKind::S16,0,count,far)||!s.number(p+"distances",ScalarKind::Bool,0,1,dist)||(!dist&&far)||!s.number(p+"verticesBound",ScalarKind::Bool,0,1,bound)||!s.number(p+"joint",ScalarKind::S32,0,joints-1,joint)){if(e.empty())e="invalid group culling storage";return false;}
 s.ref(p+"identity",RefKind::CollGroup,"CollGroup",ReferenceOwnership::ActorSubobject,false);s.ref(p+"model",RefKind::Shape,"Shape",ReferenceOwnership::Content,true);s.ref(p+"platform",RefKind::DynCollObject,"DynCollShape",ReferenceOwnership::ActorSubobject,true);s.ref(p+"next",RefKind::CollGroup,"CollGroup",ReferenceOwnership::AnyLive,true);std::set<int> seen;for(int j=0;j<count;++j){int n=0;if(!s.number(p+"triangle."+std::to_string(j),ScalarKind::S32,0,triangles-1,n)||!seen.insert(n).second){e="invalid/duplicate group triangle";return false;}}for(int j=0;j<far;++j)s.val(p+"distance."+std::to_string(j),ScalarKind::U8);}
 return true;
}
bool world_platform_schema(const ActorFields& f,const std::string& prefix,std::vector<FieldSchema>& out,std::string& e){ResourceSchema s(f,prefix,out,e);int count=0;if(!s.number("count",ScalarKind::S32,0,16,count))return false;if(!count)return true;s.ref("model",RefKind::Shape,"Shape",ReferenceOwnership::Content,false);for(int i=0;i<count;++i){auto p="part."+std::to_string(i)+".";int joint=0;if(!s.number(p+"joint",ScalarKind::S32,0,4095,joint))return false;s.ref(p+"identity",RefKind::DynCollObject,"CreatureCollPart",ReferenceOwnership::ActorSubobject,false);s.ref(p+"parent",RefKind::Creature,"Creature",ReferenceOwnership::Self,false);if(!world_dyn_shape_schema(f,s.p+p.substr(0,p.size()-1),out,e))return false;}return true;}
bool world_joint_schema(const ActorFields& f,const std::string& prefix,std::vector<FieldSchema>& out,std::string& e){ResourceSchema s(f,prefix,out,e);s.val("visible",ScalarKind::S32);for(auto k:{"scale","rotation","translation","boundsMin","boundsMax"})s.vec(k);s.mat("animation");s.mat("inverse");s.ref("shape",RefKind::Shape,"BaseShape",ReferenceOwnership::Content,false);return true;}
}
