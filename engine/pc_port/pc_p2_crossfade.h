#pragma once
#include "pc_p2_attachments.h"

namespace p2attach {
// Visual-only crossfade. advance() belongs to simulation, sample() to rendering.
// Interrupted transitions capture the last displayed local pose, not a raw clip.
class Crossfade {
    Instance::Pose from_;
    Token owner_=0;
    int clip_=-1;
    float elapsed_=0,duration_=0;
    bool blending_=false;
public:
    void reset(){owner_=0;clip_=-1;elapsed_=duration_=0;blending_=false;from_.owner=0;}
    bool advance(float seconds,bool paused=false){
        if(!std::isfinite(seconds)||seconds<0)return false;
        if(!paused&&blending_)elapsed_=std::min(duration_,elapsed_+seconds);
        return true;
    }
    float weight()const{return blending_&&duration_>0?std::min(1.f,elapsed_/duration_):1.f;}
    bool sample(Instance& instance,Token token,int clip,float frame,const Affine& owner,uint64_t tick,
                float seconds,bool snap=false,const JointCorrection* corrections=nullptr,size_t correctionCount=0){
        if(!std::isfinite(seconds)||seconds<0||seconds>10||!token)return false;
        if(owner_!=token){reset();owner_=token;}
        if(snap){blending_=false;elapsed_=duration_=0;}
        else if(clip_!=clip){
            blending_=seconds>0&&instance.capture(token,from_);elapsed_=0;duration_=seconds;
        }
        const float w=weight();
        if(!instance.sample(token,clip,frame,owner,tick,false,false,corrections,correctionCount,blending_?&from_:nullptr,w)){reset();return false;}
        clip_=clip;if(w==1)blending_=false;return true;
    }
};
}
