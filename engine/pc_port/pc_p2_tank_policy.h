#pragma once
#include "pc_p2_animation.h"
#include <map>
namespace p2tank {
// Audited source parameters: health, sight, attack range/radius, damage,
// move speed, flick range. Tank kind 0 (Fiery, InteractFire), Wtank kind 1
// (Watery, InteractBubble). Health 1000 per inst-frogs handoff; sight/attack
// from Tank general block (fp00/fp14/fp22/fp24); extractor profile is source
// of truth (experimental/pikmin2_tank_assets.py).
struct Params{float health,sight,attackRange,attackRadius,attackDamage,moveSpeed,flickRange,shakeRange;};
inline const Params& params(int kind){
  static const Params table[2]={{1000.0f,200.0f,120.0f,25.0f,10.0f,80.0f,120.0f,120.0f},
                                {1000.0f,200.0f,120.0f,25.0f,0.0f,80.0f,120.0f,120.0f}};
  return table[kind?1:0];}
// Source TANK_* state ordinals mirror Tank.h StateID: Dead 0, Wait 1, Move 2,
// MoveTurn 3, ChaseTurn 4, Attack 5, Flick 6.
inline const char* stateName(int state){
 switch(state){case 0:return "dead";case 1:return "wait";case 2:return "move";
 case 3:return "moveturn";case 4:return "chaseturn";case 5:return "attack";
 case 6:return "flick";default:return "null";}}
inline const char* motionClip(int m){
switch(m){case 0:return "dead";case 6:return "move1";case 8:return "attack";
 case 9:return "type5";default:return nullptr;}}
inline bool parse(std::istream& in,std::map<unsigned,int>& actors,std::vector<p2animation::Clip> (&banks)[2]){
std::string word;int count;if(!(in>>word>>count)||word!="P2_TANK_1"||count<1||count>32)return false;
std::map<unsigned,int> parsedActors;
for(int i=0;i<count;++i){unsigned long long id;if(!(in>>id>>word)||id>0xffffffffULL||(word!="Tank"&&word!="Wtank")||!parsedActors.emplace(unsigned(id),word=="Wtank").second)return false;}
std::vector<p2animation::Clip> parsed[2];
for(int kind=0;kind<2;++kind){if(!(in>>word)||word!=(kind?"Wtank":"Tank"))return false;
for(const char* name:{"dead","move1","flick","attack","waitact1","waitact2","type5"}){
p2animation::Clip c;if(!(in>>c.name>>c.count>>c.duration)||c.name!=name||c.count<2||c.count>64||c.duration<1||c.duration>10000)return false;
for(int j=0;j<c.count;++j){int f;if(!(in>>f)||f<0||f>=c.duration||(j&&f<=c.frames.back()))return false;c.frames.push_back(f);}
if(c.frames.front()!=0||c.frames.back()!=c.duration-1)return false;parsed[kind].push_back(c);}}
if(in>>word)return false;actors=parsedActors;banks[0]=parsed[0];banks[1]=parsed[1];return true;
}}
