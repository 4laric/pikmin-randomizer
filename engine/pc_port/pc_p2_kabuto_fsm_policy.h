#pragma once
#include "pc_p2_animation.h"
#include <map>
namespace p2kabutofsm {
// Kabuto 75 (Armored Cannon Beetle Larva) free FSM. Disc parms from
// cannon_projectile_assets DISC_PARMS Kabuto general: fp00 850 health,
// fp06 60 speed, fp12 350 sight, fp20 180 attack range, fp24 10 damage.
// Extractor profile is source of truth.
struct Params{float health,sight,attackRange,attackDamage,moveSpeed,flickRange;};
inline const Params& params(){static const Params p={850.0f,350.0f,180.0f,10.0f,60.0f,120.0f};return p;}
// Free-state ordinals mirror Kabuto.h: Dead 0, Wait 1, Turn 2, Move 3,
// Flick 4, Attack 5.
inline const char* stateName(int s){
 switch(s){case 0:return "dead";case 1:return "wait";case 2:return "turn";
 case 3:return "move";case 4:return "flick";case 5:return "attack";default:return "null";}}
inline const char* motionClip(int m){
switch(m){case 0:return "dead";case 6:return "move";case 8:return "attack";default:return nullptr;}}
inline bool parse(std::istream& in,std::map<unsigned,std::string>& actors,std::vector<p2animation::Clip>& bank){
std::string word;int count;if(!(in>>word>>count)||word!="P2_KABUTO_1"||count<1||count>32)return false;
std::map<unsigned,std::string> parsed;
for(int i=0;i<count;++i){unsigned long long id;if(!(in>>id>>word)||id>0xffffffffULL||word!="Kabuto"||!parsed.emplace(unsigned(id),word).second)return false;}
if(!(in>>word)||word!="Kabuto")return false;
std::vector<p2animation::Clip> clips;
for(const char* name:{"dead","move","flick","attack","wait"}){
p2animation::Clip c;if(!(in>>c.name>>c.count>>c.duration)||c.name!=name||c.count<2||c.count>64||c.duration<1||c.duration>10000)return false;
for(int j=0;j<c.count;++j){int f;if(!(in>>f)||f<0||f>=c.duration||(j&&f<=c.frames.back()))return false;c.frames.push_back(f);}
if(c.frames.front()!=0||c.frames.back()!=c.duration-1)return false;clips.push_back(c);}
if(in>>word)return false;actors=parsed;bank=clips;return true;
}
}
