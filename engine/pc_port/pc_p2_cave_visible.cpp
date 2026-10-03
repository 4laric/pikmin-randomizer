#include "pc_p2_cave_visible.h"
#include "pc_p2_cave_visible_policy.h"
#include "pc_p2_cave_campaign_boundary.h"
#include "pc_p2_teki_lifetime.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Controller.h"
#include "Kontroller.h"
#include "Font.h"
#include "Texture.h"
#include "ItemMgr.h"
#include "UfoItem.h"
#include "MapCode.h"
#include "Graphics.h"
#include "Dolphin/gx.h"
#include "Camera.h"
#include "MapMgr.h"
#include "MoviePlayer.h"
#include "gameflow.h"
#include "system.h"
#include <algorithm>
#include <cstdio>

// The qualified source line may ship before the optional cave provider. A
// composed provider enables this only after linking the real transition owner.
#if defined(PIKMIN_P2_CAVE_CAMPAIGN_PROVIDER)
P2CaveBoundarySnapshot pc_p2_cave_campaign_boundary();
bool pc_p2_cave_campaign_request_boundary(const P2CaveBoundarySnapshot&);
__attribute__((weak)) bool pc_netplay_session_active();
namespace {
P2CaveVisibleInput input;
unsigned long drawnScene=0;
unsigned long promptedScene=0;
bool online(){return pc_netplay_session_active && pc_netplay_session_active();}
bool snapshot(P2CaveBoundarySnapshot& source,P2CaveVisibleBoundary& actor){
    if(!mapMgr || online())return false;
    source=pc_p2_cave_campaign_boundary();
    // A temporarily unsafe Walk/UI state keeps the same scene identity. This
    // preserves the latch across the real SAVE choice and cancellation.
    if(!source.sceneGeneration || source.sceneGeneration!=pc_p2_scene_generation()
        || source.cave!="forest_1" || source.token.empty())return false;
    actor.present=true;actor.ready=source.ready;actor.scene=source.sceneGeneration;
    actor.seed=source.seed;actor.floor=source.floor;actor.cave=source.cave;actor.token=source.token;
    actor.returning=source.action==P2CaveBoundaryAction::Return;
    actor.x=source.x;actor.z=source.z;actor.radius=source.radius;
    actor.y=mapMgr->getMinY(actor.x,actor.z,true);
    return actor.valid();
}
bool safe(Navi* n){
    return n && naviMgr && n==naviMgr->getActiveNavi() && n->mKontroller
        && n->getCurrState() && n->getCurrState()->getID()==NAVISTATE_Walk
        // Navi::update enters the captain-down path at health <= 1, even
        // though serialized party health may represent smaller positive values.
        && std::isfinite(n->mHealth) && n->mHealth>1
        && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive && !gameflow.mIsDayEndActive
        && gameflow.mMoviePlayer && !gameflow.mMoviePlayer->mIsActive && !online();
}
Vector3f ring(const P2CaveVisibleBoundary& a,float angle,float r,float y){
    return Vector3f(a.x+std::cos(angle)*r,a.y+y,a.z+std::sin(angle)*r);
}
void tri(Graphics& gfx,const Vector3f& a,const Vector3f& b,const Vector3f& c,const Colour& color){
    const Vector3f vertices[]={a,b,c};const Vector2f uv[]={Vector2f(0,0),Vector2f(0,0),Vector2f(0,0)};
    gfx.setColour(color,true);gfx.drawOneTri(vertices,nullptr,uv,3);
}
void mesh(Graphics& gfx,const P2CaveVisibleBoundary& a){
    // Authored geometry, deliberately independent of legal imported meshes.
    // A recessed dark mouth with a solid irregular stone rim; the returning
    // actor adds a tall tapered water jet and a broad visible splash crown.
    constexpr int segments=24;constexpr float tau=6.28318530718f;
    for(int i=0;i<segments;++i){
        const float t=i*tau/segments,u=(i+1)*tau/segments;
        const float r=48.f+(i%3)*3.f,s=48.f+((i+1)%3)*3.f;
        const float h=17.f+(i%4)*.6f,k=17.f+((i+1)%4)*.6f;
        auto inner=ring(a,t,36,15),next=ring(a,u,36,15);
        auto outer=ring(a,t,r,h),outNext=ring(a,u,s,k);
        const Colour stone(i%2?Colour(160,164,170,255):Colour(188,192,194,255));
        tri(gfx,inner,next,outNext,stone);tri(gfx,inner,outNext,outer,stone);
        tri(gfx,outer,outNext,ring(a,u,s+7,1),Colour(91,97,105,255));
        tri(gfx,outer,ring(a,u,s+7,1),ring(a,t,r+7,1),Colour(91,97,105,255));
    }
    for(int i=0;i<segments;++i){
        const float t=i*tau/segments,u=(i+1)*tau/segments;
        tri(gfx,Vector3f(a.x,a.y+14,a.z),ring(a,u,36,15),ring(a,t,36,15),Colour(17,21,27,255));
    }
    if(a.returning){
        for(int i=0;i<segments;++i){
            const float t=i*tau/segments,u=(i+1)*tau/segments;
            auto low=ring(a,t,16,5),lowNext=ring(a,u,16,5);
            auto high=ring(a,t,8,104),highNext=ring(a,u,8,104);
            tri(gfx,low,lowNext,highNext,Colour(75,195,239,255));
            tri(gfx,low,highNext,high,Colour(128,225,255,255));
            tri(gfx,high,highNext,ring(a,u,23,115+(i%3)*5),Colour(200,247,255,255));
        }
    }
}
void prompt(Graphics& gfx,const P2CaveVisibleBoundary& a,const char* label){
    auto* font=gsys->mConsFont;
    if(!font->mTexture||!font->mChars)return;
    Vector3f eye(a.x,a.y+(a.returning?142:62),a.z);
    eye.multMatrix(gfx.mCamera->mLookAtMtx);
    if(eye.z>=0)return;
    gfx.useMatrix(Matrix4f::ident,0);gfx.setDepth(false);
    const float width=font->stringWidth(label),left=-width*.5f;
    const Vector3f backing[]={Vector3f(eye.x+left-5,eye.y-4,eye.z),
        Vector3f(eye.x-left+5,eye.y-4,eye.z),Vector3f(eye.x-left+5,eye.y+font->mCharHeight+4,eye.z),
        Vector3f(eye.x+left-5,eye.y+font->mCharHeight+4,eye.z)};
    const Vector2f empty[]={Vector2f(0,0),Vector2f(0,0),Vector2f(0,0),Vector2f(0,0)};
    gfx.useTexture(nullptr,0);gfx.setColour(Colour(15,20,27,220),true);gfx.drawOneTri(backing,nullptr,empty,4);
    gfx.useTexture(font->mTexture,0);gfx.setColour(Colour(255,255,230,255),true);
    float x=left;
    for(const unsigned char* c=reinterpret_cast<const unsigned char*>(label);*c;++c){
        if(*c<32||*c>=128)continue;
        const auto& glyph=font->mChars[*c-32];const auto& r=glyph.mTextureCoords;
        const float lo=eye.x+x-glyph.mLeftOffset,hi=lo+glyph.mWidth;
        const Vector3f v[]={Vector3f(lo,eye.y+glyph.mHeight,eye.z),Vector3f(hi,eye.y+glyph.mHeight,eye.z),
            Vector3f(hi,eye.y,eye.z),Vector3f(lo,eye.y,eye.z)};
        const float u=font->mTexture->mWidthFactor,t=font->mTexture->mHeightFactor;
        const Vector2f uv[]={Vector2f(r.mMinX*u,r.mMinY*t),Vector2f(r.mMaxX*u,r.mMinY*t),
            Vector2f(r.mMaxX*u,r.mMaxY*t),Vector2f(r.mMinX*u,r.mMaxY*t)};
        // drawOneTri submits the complete PC GX fan; legacy drawRectangle does
        // not submit each glyph before the next primitive replaces its stream.
        gfx.drawOneTri(v,nullptr,uv,4);x+=glyph.mCharSpacing;
    }
}
void probe(const P2CaveVisibleBoundary& a){
    if(a.returning)return;
    auto* ufo=itemMgr?itemMgr->getUfo():nullptr;
    for(int dx:{-260,-130,0,130,260})for(int dz:{-260,-130,0,130,260}){
        const float x=a.x+dx,z=a.z+dz;float height=0,low=1000000,high=-1000000;bool dry=true;
        for(int ox:{-40,0,40})for(int oz:{-40,0,40}){
            float y=0;auto* triangle=mapMgr->getStaticGroundBelow(x+ox,z+oz,1000000,y);
            if(!triangle){dry=false;continue;}
            const auto attribute=MapCode::getAttribute(triangle);
            if(attribute==ATTR_Water||attribute==ATTR_Hole)dry=false;
            if(!ox&&!oz)height=y;low=std::min(low,y);high=std::max(high,y);
        }
        std::printf("P2_CAVE_VISIBLE_SITE x=%.6f y=%.6f z=%.6f dry9=%d height_span=%.6f ufo_clearance=%.6f readonly=1\n",
            x,height,z,int(dry),high-low,ufo?std::hypot(x-ufo->mSRT.t.x,z-ufo->mSRT.t.z):-1.f);
    }
}
}
bool pc_p2_cave_visible_interact(Navi* n){
    // Inactive/co-op captains must not reset the active captain's latch.
    if(!naviMgr || n!=naviMgr->getActiveNavi() || !n || !n->mKontroller)return false;
    P2CaveBoundarySnapshot source;P2CaveVisibleBoundary actor;
    if(!snapshot(source,actor))return false;
    const bool click=input.sample(actor,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,
        n->mKontroller->keyDown(KBBTN_A),n->mKontroller->keyClick(KBBTN_A),safe(n));
    if(!click || !pc_p2_cave_campaign_request_boundary(source))return false;
    input.accepted();
    std::printf("P2_CAVE_VISIBLE_ACTIVATED action=%s scene=%lu ordinary_A=1 authored=1\n",
        actor.returning?"return":"enter",source.sceneGeneration);
    return true;
}
bool pc_p2_cave_visible_active(){
    P2CaveBoundarySnapshot source;P2CaveVisibleBoundary actor;
    return snapshot(source,actor);
}
void pc_p2_cave_visible_reset(){input.reset();drawnScene=0;promptedScene=0;}
void pc_p2_cave_visible_draw(Graphics& gfx){
    P2CaveBoundarySnapshot source;P2CaveVisibleBoundary actor;
    if(!gfx.mCamera || !snapshot(source,actor))return;
    if(drawnScene!=source.sceneGeneration){drawnScene=source.sceneGeneration;
        std::printf("P2_CAVE_VISIBLE_DRAW kind=%s scene=%lu x=%.3f y=%.3f z=%.3f authored=1\n",
            actor.returning?"geyser":"hole",drawnScene,actor.x,actor.y,actor.z);probe(actor);}
    const Colour color=gfx.mPrimaryColour,aux=gfx.mAuxiliaryColour;
    const int blend=gfx.setCBlending(BLEND_Alpha),cull=gfx.mCullMode;
    const bool depth=gfx.setDepth(true);
    Texture* texture=gfx.mActiveTexture[0];const bool light=gfx.setLighting(false,nullptr);
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
    gfx.useMaterial(nullptr);gfx.useTexture(nullptr,0);gfx.useMatrix(gfx.mCamera->mLookAtMtx,0);
    // DGX's default material resets GX culling to BACK. Set two-sided fans
    // after that initialization, or the upward rim/mouth faces disappear.
    gfx.setCullFront(2);
#if PIKI_USE_DGX
    // These submitted fans carry their own colors. Avoid inheriting the last
    // map material's register color for the stone rim and recessed mouth.
    GXSetChanCtrl(GX_COLOR0A0,GX_FALSE,GX_SRC_REG,GX_SRC_VTX,0,GX_DF_NONE,GX_AF_NONE);
#endif
    mesh(gfx,actor);
    auto* n=naviMgr?naviMgr->getActiveNavi():nullptr;
    if(safe(n) && actor.ready && input.prompt() && actor.near(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z)
        && gsys && gsys->mConsFont){
        const char* label=actor.returning?"A: Return to surface":"A: Enter cave";
        prompt(gfx,actor,label);
        if(promptedScene!=source.sceneGeneration){promptedScene=source.sceneGeneration;
            std::printf("P2_CAVE_VISIBLE_PROMPT kind=%s scene=%lu font_atlas_fans=1\n",actor.returning?"geyser":"hole",promptedScene);}
    }
    gfx.useMatrix(gfx.mCamera->mLookAtMtx,0);
    gfx.setColour(color,true);gfx.mAuxiliaryColour=aux;gfx.setCBlending(blend);
    gfx.useTexture(texture,0);gfx.setLighting(light,nullptr);gfx.setDepth(depth);gfx.setCullFront(cull);
}
#else
bool pc_p2_cave_visible_interact(Navi*){return false;}
bool pc_p2_cave_visible_active(){return false;}
void pc_p2_cave_visible_draw(Graphics&){}
void pc_p2_cave_visible_reset(){}
#endif
