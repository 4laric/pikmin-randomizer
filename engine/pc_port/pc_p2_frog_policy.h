#pragma once
#include "pc_p2_animation.h"
#include <map>
namespace p2frog {
inline const char* motionClip(int m){
// PaniAnimator enum and TaiOtimoti actions; Flick is jump wind-up; unmatched motions use static fallback.
switch(m){case 0:return "dead";case 1:return "damage";case 2:return "wait1";
case 3:return "wait2";case 4:return "waitact1";case 5:return "waitact2";
case 6:return "move1";case 8:return "attack";case 9:return "type1";case 10:return "type2";
case 14:return "type5";default:return nullptr;}}
inline bool parse(std::istream& in,std::map<unsigned,int>& actors,std::vector<p2animation::Clip> (&banks)[2]){
std::string word;int count;if(!(in>>word>>count)||word!="P2_FROG_1"||count<1||count>32)return false;
std::map<unsigned,int> parsedActors;
for(int i=0;i<count;++i){unsigned long long id;if(!(in>>id>>word)||id>0xffffffffULL||(word!="Frog"&&word!="MaroFrog")||!parsedActors.emplace(unsigned(id),word=="MaroFrog").second)return false;}
std::vector<p2animation::Clip> parsed[2];
for(int kind=0;kind<2;++kind){if(!(in>>word)||word!=(kind?"MaroFrog":"Frog"))return false;
for(const char* name:{"dead","wait1","waitact2","move1","waitact1","type1","wait2","type2","attack","damage","type5"}){
p2animation::Clip c;if(!(in>>c.name>>c.count>>c.duration)||c.name!=name||c.count<2||c.count>12||c.duration<1||c.duration>10000)return false;
for(int j=0;j<c.count;++j){int f;if(!(in>>f)||f<0||f>=c.duration||(j&&f<=c.frames.back()))return false;c.frames.push_back(f);}
if(c.frames.front()!=0||c.frames.back()!=c.duration-1)return false;parsed[kind].push_back(c);}}
if(in>>word)return false;actors=parsedActors;banks[0]=parsed[0];banks[1]=parsed[1];return true;
}}
