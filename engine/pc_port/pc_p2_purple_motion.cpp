#include "pc_p2_purple_motion.h"
#include "pc_p2_purple.h"
#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "Piki.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {
struct Clip { float seconds=0; std::vector<Shape*> shapes; std::vector<Matrix4f> happa; std::vector<bool> seen; };
Clip clips[2]; Shape* growth[3]={}; bool enabled=false;
Shape* load(const std::string& name) {
    Shape* result=gameflow.loadShape(("courses/pikmin2room/"+name+".mod").c_str(),true);
    if(!result)std::abort();
    for(int i=0;i<result->mTexAttrCount;++i)if(result->mTexAttrList[i].mTexture)result->mTexAttrList[i].mTexture->attach();
    return result;
}
int clipIndex(const std::string& name){return name=="rolljmp"?0:name=="fall"?1:-1;}
}

void pc_p2_purple_motion_setup() {
    enabled=false;for(Clip& clip:clips)clip=Clip();
    if(!pc_pikipelago_room_preview()||!pc_p2_purples_enabled())return;
    std::ifstream in("p2-purple-motion.txt");if(!in)return;
    std::string word;if(!(in>>word)||word!="P2_PURPLE_MOTION_1")std::abort();
    int expectedFrames[]={14,20};int clipNumber=0;
    for(const char* expected:{"rolljmp","fall"}) {
        int count;float seconds;if(!(in>>word>>count>>seconds)||word!=expected||count<1||count>32||!std::isfinite(seconds)||seconds<=0)std::abort();
        if(count!=expectedFrames[clipNumber]||std::fabs(seconds-float(expectedFrames[clipNumber])/30.0f)>0.00001f)std::abort();++clipNumber;
        Clip& clip=clips[clipIndex(word)];clip.seconds=seconds;clip.happa.resize(count);clip.seen.assign(count,false);
        for(int i=0;i<count;++i){char suffix[8];std::snprintf(suffix,sizeof(suffix),"_%02d",i);clip.shapes.push_back(load("purple_"+word+suffix));}
    }
    while(in>>word) {
        std::string name;int index;if(word!="happa"||!(in>>name>>index))std::abort();int which=clipIndex(name);
        if(which<0||index<0||index>=int(clips[which].happa.size())||clips[which].seen[index])std::abort();
        Matrix4f& matrix=clips[which].happa[index];matrix.makeIdentity();
        for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(in>>matrix.mMtx[r][c])||!std::isfinite(matrix.mMtx[r][c]))std::abort();
        clips[which].seen[index]=true;
    }
    for(const Clip& clip:clips)for(bool seen:clip.seen)if(!seen)std::abort();
    for(int i=0;i<3;++i)growth[i]=load("purple_happa_"+std::to_string(i));enabled=true;
    std::printf("P2_PURPLE_MOTION_READY rolljmp=14frames fall=20frames source_loop=repeat bca_event_metadata=absent boundary=flight_motion_time\n");
}
bool pc_p2_purple_motion_enabled(){return enabled;}
bool pc_p2_draw_purple_motion(Piki* p,Graphics& gfx,PcP2PurpleMotionClip requested,float elapsed) {
    if(!enabled||!pc_p2_is_purple(p)||!std::isfinite(elapsed)||elapsed<0)return false;
    Clip& clip=clips[requested==PcP2PurpleMotionClip::RollJump?0:1];
    int index=int(std::fmod(elapsed,clip.seconds)/clip.seconds*clip.shapes.size());if(index<0||index>=int(clip.shapes.size()))index=0;
    Matrix4f view;gfx.mCamera->mLookAtMtx.multiplyTo(p->mWorldMtx,view);clip.shapes[index]->updateAnim(gfx,view,nullptr,p);clip.shapes[index]->drawshape(gfx,*gfx.mCamera,nullptr);
    Matrix4f leaf;view.multiplyTo(clip.happa[index],leaf);Shape* top=growth[p->mHappa>=0&&p->mHappa<3?p->mHappa:0];top->updateAnim(gfx,leaf,nullptr,p);top->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
