// Standalone policy probe; include the isolated or integrated family header.
#include "pc_p2_frog_policy.h"
#include <cassert>
#include <fstream>
#include <sstream>
#include <limits>
bool parse(const std::string& text){std::istringstream in(text);std::map<unsigned,int> a;std::vector<p2animation::Clip> b[2];return p2frog::parse(in,a,b);}
int main(int argc,char** argv){
 assert(argc==2);std::ifstream file(argv[1]);std::string text((std::istreambuf_iterator<char>(file)),{});assert(parse(text));
 assert(!parse(text+" trailing"));assert(!parse(text.substr(0,text.size()/2)));
 auto changed=text;auto at=changed.find("201002 MaroFrog");assert(at!=std::string::npos);changed.replace(at,14,"201001 MaroFrog");assert(!parse(changed));
 changed=text;at=changed.find("dead 12 135");assert(at!=std::string::npos);changed.replace(at,11,"dead 13 135");assert(!parse(changed));
 std::istringstream in(text);std::map<unsigned,int> actors;std::vector<p2animation::Clip> banks[2];assert(p2frog::parse(in,actors,banks));assert(actors.size()==2&&actors.at(201001)==0&&actors.at(201002)==1);
 for(auto& bank:banks){assert(bank.size()==11);for(auto& c:bank){assert(c.index(0)==0);assert(c.index(1)==size_t(c.count-1));assert(c.index(0,true)==size_t(c.count-1));assert(c.index(std::numeric_limits<float>::quiet_NaN())==0);assert(c.index(.5f)==c.index(.5f));}}
 assert(std::string(p2frog::motionClip(9))=="type1");assert(std::string(p2frog::motionClip(10))=="type2");assert(std::string(p2frog::motionClip(8))=="attack");assert(!p2frog::motionClip(7));assert(!p2frog::motionClip(999));
}
