#include "pc_p2_shijimi_effect_native.h"
#include "Graphics.h"
#include "Camera.h"
#include "Dolphin/gx.h"
#include "gl/pc_gfx.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
namespace p2original { namespace shijimi {
namespace {std::set<NativeDownEffects*>& effects(){static std::set<NativeDownEffects*> all;return all;}
unsigned char color(unsigned char a,unsigned char b){return unsigned(a)*(unsigned(b)+1)>>8;}}
struct NativeDownEffects::Impl {
 DownEffects fx;DownEffects::Clipping clipping;GXTexObj texture{};bool attached=false;
 explicit Impl(DownEffects::Clipping c):clipping(std::move(c)){}
};
NativeDownEffects::NativeDownEffects(DownEffects::Clipping c):m(std::make_unique<Impl>(std::move(c))){effects().insert(this);}
NativeDownEffects::~NativeDownEffects(){effects().erase(this);if(m->attached)pc_gfx_release_texture(&m->texture);}
bool NativeDownEffects::load(const std::string& path,std::string& e){
 if(!m->clipping){e="source77 Down requires actual scene clipping";return false;}
 if(!m->fx.load(path,e))return false;
 if(m->attached)pc_gfx_release_texture(&m->texture);
 // Genuine TEX1: 64x64 I8 BTI at32, tiled image bytes at64.
 GXInitTexObj(&m->texture,const_cast<unsigned char*>(m->fx.texture().data()+64),64,64,GX_TF_I8,GX_CLAMP,GX_CLAMP,GX_FALSE);
 GXInitTexObjLOD(&m->texture,GX_LINEAR,GX_LINEAR,0,0,0,GX_FALSE,GX_FALSE,GX_ANISO_1);m->attached=true;return true;
}
bool NativeDownEffects::create(std::uint64_t id,Position p,Color c,std::uint32_t seed,std::string& e){return m->fx.create(id,p,c,seed,e);}
bool NativeDownEffects::follow(std::uint64_t id,Position p,std::string& e){return m->fx.follow(id,p,e);}
bool NativeDownEffects::fade(std::uint64_t id,std::string& e){return m->fx.fade(id,e);}
bool NativeDownEffects::tick(float seconds,std::string& e){if(!m->fx.ready()){e.clear();return true;}return m->fx.tick(seconds,m->clipping,e);}
std::size_t NativeDownEffects::particles()const{return m->fx.particles();}
void NativeDownEffects::draw(Graphics& g,EffectColors primary,EffectColors environment){
 if(!m->attached||!g.mCamera||!particles())return;
 bool light=g.setLighting(false,nullptr);int blend=g.setCBlending(BLEND_Alpha);int cull=g.mCullMode;g.setCullFront(2);bool depth=g.setDepth(false);
 g.useMatrix(g.mCamera->mLookAtMtx,0);g.useTexture(nullptr,0);GXLoadTexObj(&m->texture,GX_TEXMAP0);
 GXSetNumTevStages(1);GXSetNumTexGens(1);GXSetTexCoordGen2(GX_TEXCOORD0,GX_TG_MTX2X4,GX_TG_TEX0,GX_IDENTITY,GX_FALSE,GX_PTIDENTITY);
 GXSetTevOrder(GX_TEVSTAGE0,GX_TEXCOORD0,GX_TEXMAP0,GX_COLOR_NULL);GXSetNumIndStages(0);GXSetTevDirect(GX_TEVSTAGE0);GXSetTevDirect(GX_TEVSTAGE1);
 GXSetTevColorIn(GX_TEVSTAGE0,GX_CC_C1,GX_CC_C0,GX_CC_TEXC,GX_CC_ZERO);GXSetTevAlphaIn(GX_TEVSTAGE0,GX_CA_ZERO,GX_CA_TEXA,GX_CA_A0,GX_CA_ZERO);
 GXSetTevColorOp(GX_TEVSTAGE0,GX_TEV_ADD,GX_TB_ZERO,GX_CS_SCALE_1,GX_TRUE,GX_TEVPREV);GXSetTevAlphaOp(GX_TEVSTAGE0,GX_TEV_ADD,GX_TB_ZERO,GX_CS_SCALE_1,GX_TRUE,GX_TEVPREV);
 // Literal BSP1 0x0459/e6/ref10/z25: additive SRCALPHA+ONE,
 // alpha>10, depth LEQUAL with no depth writes, early depth compare.
 GXSetBlendMode(GX_BM_BLEND,GX_BL_SRCALPHA,GX_BL_ONE,GX_LO_SET);GXSetZMode(GX_TRUE,GX_LEQUAL,GX_FALSE);GXSetZCompLoc(GX_TRUE);
 GXSetAlphaCompare(GX_GREATER,10,GX_AOP_AND,GX_ALWAYS,0);GXSetCullMode(GX_CULL_NONE);
 GXClearVtxDesc();GXSetVtxDesc(GX_VA_POS,GX_DIRECT);GXSetVtxDesc(GX_VA_TEX0,GX_DIRECT);
 GXSetVtxAttrFmt(GX_VTXFMT0,GX_VA_POS,GX_POS_XYZ,GX_F32,0);GXSetVtxAttrFmt(GX_VTXFMT0,GX_VA_TEX0,GX_TEX_ST,GX_F32,0);
 const auto& camera=g.mCamera->mLookAtMtx;
 for(const auto& pair:m->fx.emitters()){const auto& b=pair.second;if(b.clipped)continue;const auto& r=m->fx.resource(b.resource);constexpr unsigned bsp=200;
  for(const auto& p:b.particles){
   unsigned char alpha=color(color(r[bsp+0x29],primary.a),static_cast<unsigned char>(255*p.alpha));
   GXSetTevColor(GX_TEVREG0,GXColor{color(r[bsp+0x26],primary.r),color(r[bsp+0x27],primary.g),color(r[bsp+0x28],primary.b),alpha});
   GXSetTevColor(GX_TEVREG1,GXColor{color(r[bsp+0x2a],environment.r),color(r[bsp+0x2b],environment.g),color(r[bsp+0x2c],environment.b),color(r[bsp+0x2d],environment.a)});
   float theta=float(p.angle>>5)*6.2831853071795864769f/2048,c=std::cos(theta),s=std::sin(theta);
   float half=25*.28f*p.scale;GXBegin(GX_QUADS,GX_VTXFMT0,4);
   for(int i=0;i<4;++i){float x=(i==0||i==3)?-half:half,y=i<2?half:-half;float a=c*x-s*y,h=s*x+c*y;
    GXPosition3f32(p.position.x+camera.mMtx[0][0]*a+camera.mMtx[1][0]*h,p.position.y+camera.mMtx[0][1]*a+camera.mMtx[1][1]*h,p.position.z+camera.mMtx[0][2]*a+camera.mMtx[1][2]*h);
    GXTexCoord2f32((i==0||i==3)?0:1,i<2?0:1);
   }GXEnd();
  }
 }
 g.useTexture(nullptr,0);g.setCullFront(cull);g.setCBlending(blend);g.setDepth(depth);g.setLighting(light,nullptr);
}
} }
void pc_p2_shijimi_effect_tick_all(float seconds){for(auto* fx:p2original::shijimi::effects()){std::string e;if(!fx->tick(seconds,e)){std::fprintf(stderr,"P2_ORIGINAL_SHIJIMI_FX refusal: %s\n",e.c_str());std::abort();}}}
