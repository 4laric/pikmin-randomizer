#pragma once
#include "pc_p2_pose_blend.h"
#include <algorithm>
#include <array>
#include <cmath>
namespace p2original { namespace pelplant {
// Pelplant::BlendAccelerationFunc, not the generic quadratic function passed
// during startBlend. Obj::doAnimationUpdateAnimator supplies this each tick.
// Retain the source's 2048-entry sine index truncation. The host computes the
// indexed sine value instead of embedding the original platform's table.
inline float witherWeight(float seconds) {
 if(!std::isfinite(seconds))return -1;
 float t=std::clamp(seconds,0.f,1.f);
 const float angle=6.28318530717958647692f*(-3.f*t);
 const int index=int(angle*-325.9493f)&0x7ff;
 const float sine=-std::sin(float(index)*(6.28318530717958647692f/2048.f));
 return std::clamp(.5f*(1.f-t)*sine+t,0.f,1.f);
}
inline bool samplePose(const std::vector<p2pose::Pose>& poses,const std::vector<int>& frames,
                       float frame,p2pose::Pose& out) {
 p2pose::Interval span;
 return poses.size()==frames.size()&&p2pose::bracket(frames,frame,span)
  &&p2pose::blendInto(poses[span.left],poses[span.right],span.weight,out);
}
// The same weight must drive collision/capture joints and visible geometry.
inline bool blendJoint(const std::array<float,12>& start,const std::array<float,12>& end,
                       float weight,std::array<float,12>& out) {
 if(!std::isfinite(weight)||weight<0||weight>1)return false;
 for(std::size_t i=0;i<12;++i){if(!std::isfinite(start[i])||!std::isfinite(end[i]))return false;}
 for(std::size_t i=0;i<12;++i)out[i]=weight==0?start[i]:weight==1?end[i]:start[i]*(1-weight)+end[i]*weight;
 return true;
}
} }
