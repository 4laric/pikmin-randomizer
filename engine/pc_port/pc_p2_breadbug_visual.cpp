#include "pc_p2_breadbug_visual.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <SDL.h>
#include <fstream>
#include <vector>
#include <set>
#include <string>
#include <cmath>
#include <cstdlib>
#include <cstdio>
namespace {
struct Clip { int duration=0;std::vector<int> frames;std::vector<Shape*> shapes; };
struct Display { unsigned id;int kind;float x,y,z,yaw; };
Clip clips[2];Shape* nest=nullptr;std::vector<Display> displays;unsigned started=0;bool logged=false;
void fail(){std::fputs("P2_BREADBUG_VISUAL invalid profile/model\n",stderr);std::abort();}
Shape* load(const std::string& name){
    std::string path="assets/dataDir/courses/pikmin2room/"+name;
    std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in)fail();auto size=in.tellg();
    if(size<=0||size>16*1024*1024)fail();in.seekg(0);std::vector<unsigned char> data(size_t(size),0),resources;
    if(!in.read(reinterpret_cast<char*>(data.data()),size)||!p2animation::resources(data,resources))fail();
    Shape* shape=gameflow.loadShape(("courses/pikmin2room/"+name).c_str(),true);if(!shape)fail();
    for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();
    return shape;
}
}
void pc_p2_breadbug_visual_reset(){for(auto& clip:clips)clip=Clip{};nest=nullptr;displays.clear();started=0;logged=false;}
void pc_p2_breadbug_visual_setup(){
    pc_p2_breadbug_visual_reset();if(!pc_pikipelago_room_preview())return;
    std::ifstream in("p2-breadbug-visual.txt");if(!in)return;std::string word;if(!(in>>word)||word!="P2_BREADBUG_VISUAL_1")fail();
    for(int kind=0;kind<2;++kind){int count;auto& clip=clips[kind];
        if(!(in>>word>>clip.duration>>count)||word!=(kind?"move":"wait")||clip.duration<2||clip.duration>10000||count<2||count>12)fail();
        for(int i=0;i<count;++i){int frame;if(!(in>>frame)||frame<0||frame>=clip.duration||(i&&frame<=clip.frames.back()))fail();clip.frames.push_back(frame);}
        if(clip.frames.front()!=0||clip.frames.back()!=clip.duration-1)fail();
    }
    int count;if(!(in>>count)||count<1||count>8)fail();std::set<unsigned> ids;
    for(int i=0;i<count;++i){unsigned long long id;Display d;
        if(!(in>>id>>word>>d.x>>d.y>>d.z>>d.yaw)||id>0xffffffffULL||!ids.insert(unsigned(id)).second)fail();
        d.id=unsigned(id);d.kind=word=="wait"?0:word=="move"?1:word=="nest"?2:-1;
        if(d.kind<0||!std::isfinite(d.x)||!std::isfinite(d.y)||!std::isfinite(d.z)||!std::isfinite(d.yaw)||std::fabs(d.x)>100000||std::fabs(d.y)>100000||std::fabs(d.z)>100000||std::fabs(d.yaw)>360)fail();
        displays.push_back(d);
    }
    if(in>>word)fail();
    for(int kind=0;kind<2;++kind)for(size_t i=0;i<clips[kind].frames.size();++i){char name[80];std::snprintf(name,sizeof(name),"breadbug_%s_%02u.mod",kind?"move":"wait",unsigned(i));clips[kind].shapes.push_back(load(name));}
    nest=load("breadbug_nest.mod");started=SDL_GetTicks();
    for(const auto& d:displays)std::printf("P2_BREADBUG_VISUAL_READY display=%u kind=%d xyz=%.3f,%.3f,%.3f yaw=%.3f behavior=visual_only\n",d.id,d.kind,d.x,d.y,d.z,d.yaw);
}
void pc_p2_breadbug_visual_draw(Graphics& gfx){
    if(displays.empty()||!gfx.mCamera)return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
    gfx.useMaterial(nullptr);gfx.setDepth(true);
    const float elapsed=float(SDL_GetTicks()-started)*.03f; // Visual display clock at source30fps; not gameplay simulation.
    for(const auto& d:displays){Shape* shape=nest;
        if(d.kind<2){auto& clip=clips[d.kind];const float frame=std::fmod(elapsed,float(clip.duration));size_t best=0;
            for(size_t i=1;i<clip.frames.size();++i)if(std::fabs(float(clip.frames[i])-frame)<std::fabs(float(clip.frames[best])-frame))best=i;
            shape=clip.shapes[best];
        }
        Matrix4f world,view;world.makeSRT(Vector3f(1,1,1),Vector3f(0,d.yaw*0.0174532925199433f,0),Vector3f(d.x,d.y,d.z));
        gfx.mCamera->mLookAtMtx.multiplyTo(world,view);shape->updateAnim(gfx,view,nullptr,nullptr);shape->drawshape(gfx,*gfx.mCamera,nullptr);
    }
    if(!logged){std::puts("P2_BREADBUG_VISUAL_DRAW no_actor_no_collision");logged=true;}
}
