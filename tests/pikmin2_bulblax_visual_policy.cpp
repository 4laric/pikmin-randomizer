#include "pc_p2_bulblax_visual_policy.h"
#include <sstream>
#include <cassert>
int main(){
 const std::string good="P2_BULBLAX_VISUAL_1\n3\n30 wait1 30 3 0 15 29\n31 move 12 2 0 11\n53 move1 80 2 0 79\n3\n230001 30 wait1 -120 30 1800 0\n230002 31 move -100 30 1820 0\n230003 53 move1 150 30 1500 0\n";
 auto parse=[](const std::string& s){std::istringstream in(s);return p2bulblax::read(in);};auto p=parse(good);assert(p.clips.size()==3&&p.displays.size()==3);assert(p.clips[0].index(15)==1&&p.clips[0].index(29)==2&&p.clips[0].index(30)==0&&p.clips[0].index(-1)==0);assert(p.displays[2].clip==2);
 auto reject=[&](std::string s){try{parse(s);assert(false);}catch(const std::runtime_error&){}};
 reject(good+"junk");
 for(const auto& pair:std::vector<std::pair<std::string,std::string>>{{"230003","230001"},{"230003","4294967296"},{"230003","-1"},{"53 move1","54 move1"},{"30 wait1","30 ../../x"},{"30 wait1","30 move"},{"0 15 29","0 29 15"},{"0 15 29","0 15 30"},{"150 30 1500","nan 30 1500"},{"150 30 1500","100001 30 1500"}}){std::string s=good;auto at=s.find(pair.first);assert(at!=std::string::npos);s.replace(at,pair.first.size(),pair.second);reject(s);}
 // Partial sampled clips remain honest: no invented missing endpoint.
 auto partial=parse("P2_BULBLAX_VISUAL_1 1 30 dead 140 2 28 111 1 1 30 dead 0 0 0 0");assert(partial.clips[0].index(0)==0);
}
