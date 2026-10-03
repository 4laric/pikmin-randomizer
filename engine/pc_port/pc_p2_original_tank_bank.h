#pragma once
#include "pc_p2_animation.h"
#include "pc_p2_tank_breath.h"
#include <array>
#include <istream>
#include <string>
namespace p2original { namespace tank {
// Resource-only grammar; there are no AP actor/placement IDs in this file.
// P2_ORIGINAL_TANK_BANK_1, then Tank 24 / Wtank 25, each followed by seven
// ordered `<name> <pose-count> <duration> <sample-frames...>` clip rows.
using Banks=std::array<std::vector<p2animation::Clip>,2>;
inline bool parseBank(std::istream& in,Banks& out,std::string& error){
 auto fail=[&](const char* text){error=text;return false;};
 std::string word;if(!(in>>word)||word!="P2_ORIGINAL_TANK_BANK_1")return fail("original Tank resource-only bank header missing");
 Banks next;
 for(unsigned kind=0;kind<2;++kind){unsigned source=0;
  if(!(in>>word>>source)||word!=(kind?"Wtank":"Tank")||source!=24+kind)return fail("original Tank bank literal species/source mismatch");
  // Retail Tank animation archive is shared by both species. Durations
  // verified from each actual BCA, not from actor/seed metadata.
  const int sourceDuration[]={90,55,95,95,35,50,40};unsigned index=0;
  for(const char* name:{"dead","move1","flick","attack","waitact1","waitact2","type5"}){
   p2animation::Clip clip;
   if(!(in>>clip.name>>clip.count>>clip.duration)||clip.name!=name||clip.count<2||clip.count>64||clip.duration<2||clip.duration>10000)return fail("original Tank authored clip invalid");
   if(clip.duration!=sourceDuration[index++])return fail("original Tank clip duration differs from source BCA");
   for(int i=0;i<clip.count;++i){int frame=0;if(!(in>>frame)||frame<0||frame>=clip.duration||(i&&frame<=clip.frames.back()))return fail("original Tank sampled frames invalid");clip.frames.push_back(frame);}
   if(clip.frames.front()!=0||clip.frames.back()!=clip.duration-1)return fail("original Tank sampled endpoints invalid");
   if(clip.name=="attack"){
    if(clip.duration!=p2tankbreath::ATTACK_CLIP_FRAMES)return fail("original Tank attack duration differs from source");
    bool key=false;for(int frame:clip.frames)key|=frame==p2tankbreath::KEYEVENT2_FRAME;
    if(!key)return fail("original Tank source breath keyframe is not sampled");
   }
   next[kind].push_back(std::move(clip));
  }
 }
 if(in>>word)return fail("trailing original Tank resource-only bank data");
 out=std::move(next);error.clear();return true;
}
} }
