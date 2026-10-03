#pragma once
#include "pc_p2_animation.h"
#include <array>
#include <istream>
namespace p2original { namespace cannon {
using Banks=std::array<std::vector<p2animation::Clip>,2>;
inline bool parseBank(std::istream& in,Banks& out,std::string& error){
 auto fail=[&](const char* s){error=s;return false;};
 std::string word;if(!(in>>word)||word!="P2_ORIGINAL_CANNON_BANK_1")return fail("original cannon resource bank header missing");
 Banks staged;
 const char* names[]={"dead","move","flick","attack","pivot","wait","K_pivot","K_wait","K_attack","K_flick","K_dead","K_appear","K_hide","carry"};
 const int durations[]={90,55,82,95,35,50,35,50,95,82,90,36,18,40};
 for(unsigned kind=0;kind<2;++kind){unsigned source=0;
  if(!(in>>word>>source)||word!=(kind?"Fkabuto":"Rkabuto")||source!=95+kind)return fail("original cannon literal species/source mismatch");
  for(unsigned k=0;k<14;++k){p2animation::Clip c;
   if(!(in>>c.name>>c.count>>c.duration)||c.name!=names[k]||c.count<2||c.count>64||c.duration!=durations[k])return fail("original cannon authored clip/duration mismatch");
   for(int i=0;i<c.count;++i){int f;if(!(in>>f)||f<0||f>=c.duration||(i&&f<=c.frames.back()))return fail("original cannon sampled frames invalid");c.frames.push_back(f);}
   if(c.frames.front()!=0||c.frames.back()!=c.duration-1)return fail("original cannon sampled endpoints invalid");
   staged[kind].push_back(std::move(c));
  }
 }
 if(in>>word)return fail("trailing original cannon bank data");out=std::move(staged);error.clear();return true;
}
inline bool parseStoneBank(std::istream& in,std::vector<p2animation::Clip>& out,std::string& error){
 auto fail=[&](const char* s){error=s;return false;};std::string magic,species;unsigned id=0;
 if(!(in>>magic>>species>>id)||magic!="P2_ORIGINAL_STONE_BANK_1"||species!="Stone"||id!=74)return fail("original Stone bank identity invalid");
 std::vector<p2animation::Clip> next;unsigned k=0;const int durations[]={71,40};
 for(const char* name:{"dead","run"}){p2animation::Clip c;
  if(!(in>>c.name>>c.count>>c.duration)||c.name!=name||c.duration!=durations[k++]||c.count<2||c.count>64)return fail("original Stone authored clip invalid");
  for(int i=0;i<c.count;++i){int f;if(!(in>>f)||f<0||f>=c.duration||(i&&f<=c.frames.back()))return fail("original Stone frames invalid");c.frames.push_back(f);}
  if(c.frames.front()!=0||c.frames.back()!=c.duration-1)return fail("original Stone endpoints invalid");next.push_back(std::move(c));
 }
 if(in>>magic)return fail("trailing original Stone bank data");out=std::move(next);error.clear();return true;
}

} }
