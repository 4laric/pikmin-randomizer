#pragma once
#include "pc_p2_original_honey_policy.h"
#include <array>
#include <locale>
#include <sstream>
namespace p2originalresource { namespace honey {
inline unsigned sourceMotion(Phase phase){return phase==Phase::Fall?0:phase==Phase::Bounce?3:phase==Phase::Wait?4:phase==Phase::Touch?5:6;}
inline bool animationSnapshot(const std::string& bytes,const std::string& fingerprint,Phase phase,const std::array<ReceiverClip,7>& clips,unsigned& motion,ReceiverClock& clock,std::string& error){
 auto bad=[&](){error="Honey source animation snapshot invalid";return false;};
 if(bytes.size()>256||fingerprint.size()!=64||static_cast<int>(phase)<0||phase>=Phase::Dead)return bad();
 for(char c:fingerprint)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return bad();
 std::istringstream in(bytes);in.imbue(std::locale::classic());std::string magic,fp;unsigned parsedMotion;ReceiverClock parsed;int done;
 if(!(in>>magic>>fp>>parsedMotion>>parsed.frame>>parsed.next>>done)||magic!="P2OHA1"||fp!=fingerprint||phase==Phase::Dead||parsedMotion!=sourceMotion(phase)||parsedMotion>=clips.size()||(done!=0&&done!=1))return bad();
 in>>std::ws;if(!in.eof())return bad();
 const auto& clip=clips[parsedMotion];if(!clip.valid()||!std::isfinite(parsed.frame)||parsed.frame<0||parsed.frame>=clip.duration)return bad();
 parsed.complete=done!=0;
 // Bounce/Touch/Shrink consume END immediately and change phase. A completed
 // live snapshot in these phases would suppress its only transition forever.
 if(parsed.complete){if(phase!=Phase::Fall||clip.loopStart>=0||parsed.frame!=clip.duration-1||parsed.next!=clip.keys.size())return bad();}
 else {std::size_t frontier=0;while(frontier<clip.keys.size()&&clip.keys[frontier].frame<static_cast<int>(parsed.frame))++frontier;if(parsed.next!=frontier)return bad();if(clip.loopStart>=0&&parsed.frame>=static_cast<int>(clip.loopEnd)+1)return bad();}
 motion=parsedMotion;clock=parsed;error.clear();return true;
}
} }
