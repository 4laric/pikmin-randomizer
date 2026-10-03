#include "pc_p2_watage_native.h"
#include "Graphics.h"
#include "Camera.h"
#include "Dolphin/gx.h"
#include "gl/pc_gfx.h"
#include <cmath>
#include <cstdio>
#include <set>
#include <cstdlib>
namespace p2watage {
namespace {std::set<NativeEffect*>& instances(){static std::set<NativeEffect*> s;return s;}}
struct NativeEffect::Impl {
 Effect effect;GXTexObj texture{};bool attached=false;std::uint32_t seed=0x1e4;DrawStats stats;
};
NativeEffect::NativeEffect():m(std::make_unique<Impl>()){instances().insert(this);}
NativeEffect::~NativeEffect(){instances().erase(this);if(m->attached)pc_gfx_release_texture(&m->texture);}
bool NativeEffect::load(std::string& e){
 if(m->effect.particles()){e="Watage native reload with live emitters";return false;}
 if(m->attached){pc_gfx_release_texture(&m->texture);m->attached=false;}
 if(!m->effect.load("watage-effect",e))return false;
 // Original TEX1 contains the 32x32 IA4 BTI at32 and tiled pixels at64.
 GXInitTexObj(&m->texture,const_cast<unsigned char*>(m->effect.texture().data()+64),32,32,GX_TF_IA4,GX_CLAMP,GX_CLAMP,GX_FALSE);
 GXInitTexObjLOD(&m->texture,GX_LINEAR,GX_LINEAR,0,0,0,GX_FALSE,GX_FALSE,GX_ANISO_1);m->attached=true;return true;
}
bool NativeEffect::touch(Vec position,std::string& e){m->seed=m->seed*0x19660du+0x3c6ef35fu;bool ok=m->effect.touch(position,m->seed,e);if(ok)std::printf("P2_WATAGE_EMIT resource=0x1e4 texture=IP2_watage2_ia emissions=%u particles=%zu origin=%.3f,%.3f,%.3f\n",emissions(),particles(),position.x,position.y,position.z);return ok;}
bool NativeEffect::tick(float seconds,std::string& e){return m->effect.tick(seconds,e);}
std::size_t NativeEffect::particles()const{return m->effect.particles();}
unsigned NativeEffect::emissions()const{return m->effect.emissions();}
DrawStats NativeEffect::draws()const{return m->stats;}
bool NativeEffect::cameraControl(Graphics& g,std::string& e){
 if(!g.mCamera||!g.mCamera->mPlanePointers[0]||!particles()){e="Watage camera control requires live rendered emitter";return false;}
 auto* camera=g.mCamera;auto* plane=&camera->mPlanePointers[0]->mPlane;
 const auto saved=*plane;const int count=camera->mActivePlaneCount;
 const auto origin=m->effect.bursts()[0].origin;const int age=m->effect.bursts()[0].particles[0].age;
 const auto n=particles();const auto emission=emissions();const auto before=draws();
 const int cull=g.mCullMode,blend=g.mBlendMode;const bool depth=g.mIsDepthEnabled,light=g.mIsLightingEnabled;
 // Deliberately exercise non-effect render state; checking a coincidental
 // default NONE/depth-write state would miss the former DGX return-value bug.
 g.setCullFront(0);g.setCBlending(BLEND_Alpha);g.setDepth(false);g.setLighting(true,nullptr);
 camera->mActivePlaneCount=1;plane->mNormal.set(1,0,0);plane->mOffset=origin.x+101;
 draw(g);const auto hidden=draws();const bool hiddenState=g.mCullMode==0&&g.mBlendMode==BLEND_Alpha&&!g.mIsDepthEnabled&&g.mIsLightingEnabled;plane->mOffset=origin.x-101;draw(g);const auto visible=draws();
 const bool visibleState=g.mCullMode==0&&g.mBlendMode==BLEND_Alpha&&!g.mIsDepthEnabled&&g.mIsLightingEnabled;
 *plane=saved;camera->mActivePlaneCount=count;
 g.setCullFront(cull);g.setCBlending(blend);g.setDepth(depth);g.setLighting(light,nullptr);
 if(hidden.quads!=before.quads||hidden.culled!=before.culled+1||visible.quads<=hidden.quads||particles()!=n||emissions()!=emission||m->effect.bursts()[0].particles[0].age!=age||!hiddenState||!visibleState||g.mCullMode!=cull||g.mBlendMode!=blend||g.mIsDepthEnabled!=depth||g.mIsLightingEnabled!=light){e="Watage draw-only camera control failed";return false;}
 std::puts("PASS P2_WATAGE_CAMERA sphere_radius=100 actual_gx_draw=1 hidden_quads=0 visible_quads=1 clock_unchanged=1 planes_restored=1 graphics_state_restored=1 direct_control=1 gameplay=0");e.clear();return true;
}

void NativeEffect::draw(Graphics& g){
 if(!g.mCamera||!particles())return;
 bool light=g.setLighting(false,nullptr);int blend=g.setCBlending(BLEND_Alpha);int cull=g.mCullMode;g.setCullFront(2);bool depth=g.setDepth(false);
 g.useMatrix(g.mCamera->mLookAtMtx,0);
 // Invalidate the native texture cache around this independently owned GX obj.
 // Otherwise a following actor can skip reloading its old cached texture.
 g.useTexture(nullptr,0);
 GXLoadTexObj(&m->texture,GX_TEXMAP0);
 GXSetNumTevStages(1);GXSetNumTexGens(1);GXSetTexCoordGen2(GX_TEXCOORD0,GX_TG_MTX2X4,GX_TG_TEX0,GX_IDENTITY,GX_FALSE,GX_PTIDENTITY);
 GXSetTevOrder(GX_TEVSTAGE0,GX_TEXCOORD0,GX_TEXMAP0,GX_COLOR_NULL);
 GXSetNumIndStages(0);GXSetTevDirect(GX_TEVSTAGE0);GXSetTevDirect(GX_TEVSTAGE1);
 // Literal source TEV mode3: mix environment/primary through texture intensity.
 GXSetTevColorIn(GX_TEVSTAGE0,GX_CC_C1,GX_CC_C0,GX_CC_TEXC,GX_CC_ZERO);
 GXSetTevAlphaIn(GX_TEVSTAGE0,GX_CA_ZERO,GX_CA_A0,GX_CA_TEXA,GX_CA_ZERO);
 GXSetTevColorOp(GX_TEVSTAGE0,GX_TEV_ADD,GX_TB_ZERO,GX_CS_SCALE_1,GX_TRUE,GX_TEVPREV);
 GXSetTevAlphaOp(GX_TEVSTAGE0,GX_TEV_ADD,GX_TB_ZERO,GX_CS_SCALE_1,GX_TRUE,GX_TEVPREV);
 GXSetBlendMode(GX_BM_BLEND,GX_BL_SRCALPHA,GX_BL_INVSRCALPHA,GX_LO_CLEAR);
 GXSetZMode(GX_TRUE,GX_LEQUAL,GX_FALSE);GXSetZCompLoc(GX_TRUE);GXSetAlphaCompare(GX_ALWAYS,0,GX_AOP_AND,GX_ALWAYS,0);GXSetCullMode(GX_CULL_NONE);
 GXClearVtxDesc();GXSetVtxDesc(GX_VA_POS,GX_DIRECT);GXSetVtxDesc(GX_VA_TEX0,GX_DIRECT);
 GXSetVtxAttrFmt(GX_VTXFMT0,GX_VA_POS,GX_POS_XYZ,GX_F32,0);GXSetVtxAttrFmt(GX_VTXFMT0,GX_VA_TEX0,GX_TEX_ST,GX_F32,0);
 for(const auto& b:m->effect.bursts()){
  // StaticClipping's authored 100 sphere is at global origin, not localY85.
  if(!g.mCamera->isPointVisible(Vector3f(b.origin.x,b.origin.y,b.origin.z),100)){++m->stats.culled;continue;}
  ++m->stats.batches;
  for(const auto& p:b.particles){
   GXSetTevColor(GX_TEVREG0,GXColor{231,226,200,static_cast<u8>(255*p.alpha)});GXSetTevColor(GX_TEVREG1,GXColor{60,48,34,255});
   float angle=p.angle*6.283185307179586f/65536,c=std::cos(angle),s=std::sin(angle);
   float x=25*.224853515625f*p.scale,y=25*.261962890625f*p.scale;
   // JPADrawRotation type8: two perpendicular source planes, Y rotation.
   // Vertices use the JPA default25 halfsize. Never camera-facing sparkle.
   for(int plane=0;plane<2;++plane){++m->stats.quads;GXBegin(GX_QUADS,GX_VTXFMT0,4);
    for(int i=0;i<4;++i){float a=(i==0||i==3)?-x:x,h=(i<2)?y:-y;
     float dx=plane?-s*a:c*a,dz=plane?c*a:s*a;
     GXPosition3f32(p.position.x+dx,p.position.y+h,p.position.z+dz);GXTexCoord2f32((i==0||i==3)?0:1,i<2?0:1);
    }GXEnd();
   }
  }
 }
 g.useTexture(nullptr,0);g.setCullFront(cull);g.setCBlending(blend);g.setDepth(depth);g.setLighting(light,nullptr);
}
}
void pc_p2_watage_tick_all(float seconds){
 for(auto* effect:p2watage::instances()){std::string e;if(!effect->tick(seconds,e)){std::fprintf(stderr,"P2_WATAGE refusal: %s\n",e.c_str());std::abort();}}
}
