#pragma once
#include <istream>
#include <sstream>
#include <string>
#include <map>
#include <set>
#include <vector>
#include <cmath>
namespace p2original { namespace bulblax_snagret {
// GPVE01 SnakeCrow authored enemyanimmgr events and BCA durations. The
// existing general-purpose loader is permissive; original admission is not.
inline bool validateSnagretBank(std::istream& in,std::string& error){
 const std::map<std::string,std::pair<unsigned,std::string>> expected={
 {"dead",{165,"67:2,75:2,110:5,131:3,143:4,149:4"}},
 {"appear1",{55,"14:2"}},{"appear2",{165,"20:2,58:3,115:4,141:5"}},
 {"dive",{36,"12:2,28:3"}},{"hit_near",{81,"33:2,36:3,48:4"}},
 {"hit",{80,"32:2,34:3,48:4"}},{"hit_far",{80,"32:2,36:3,48:4"}},
 {"hit_r",{75,"28:2,32:3,48:4"}},{"hit_l",{75,"28:2,32:3,48:4"}},
 {"wait1",{50,"0:0,49:1"}},{"waitact1",{70,"42:2"}},
 {"waitact2",{20,"0:0,19:1"}},{"type5",{40,"10:0,29:1"}}};
 auto fail=[&](const char* why){error=why;return false;};
 std::string line;if(!std::getline(in,line))return fail("missing original Snagret bank");
 if(!line.empty()&&line.back()=='\r')line.pop_back();
 if(line!="P2_SNAGRET_BANK_1")return fail("original Snagret bank header mismatch");
 std::set<std::string> found;bool identity=false;unsigned lines=0;
 while(std::getline(in,line)){
  if(++lines>256||line.size()>32768)return fail("oversized original Snagret bank");
  std::istringstream row(line);std::string kind,species;if(!(row>>kind>>species))return fail("malformed original Snagret bank row");
  if(kind=="species"){
   unsigned source;std::string extra;if(!(row>>source)||(row>>extra))return fail("malformed Snagret species identity");
   if(species=="SnakeCrow"){if(source!=34||identity)return fail("original Snagret source identity mismatch");identity=true;}
   continue;
  }
  if(kind!="clip")return fail("unexpected original Snagret bank row");
  if(species!="SnakeCrow")continue;
  std::string name,events,posesKey,statusKey,status,framesKey,frames,extra;unsigned duration,poses;
  if(!(row>>name>>duration>>events>>posesKey>>poses>>statusKey>>status>>framesKey>>frames)||(row>>extra))return fail("malformed original SnakeCrow clip row");
  auto expectedClip=expected.find(name);
  if(!identity||expectedClip==expected.end()||!found.insert(name).second||duration!=expectedClip->second.first||events!=expectedClip->second.second
   ||posesKey!="poses"||statusKey!="status"||status!="converted"||framesKey!="frames"||poses<2||poses>256)return fail("original SnakeCrow clip/event/status mismatch");
  std::istringstream list(frames);std::string value;unsigned count=0;double previous=-1;
  while(std::getline(list,value,',')){std::istringstream number(value);double frame;std::string trailing;
   if(!(number>>frame)||(number>>trailing)||!std::isfinite(frame)||frame<=previous||frame<0||frame>duration-1||(count==0&&frame!=0))return fail("invalid original SnakeCrow sampled frame");
   previous=frame;++count;
  }
  if(count!=poses||previous!=duration-1)return fail("incomplete original SnakeCrow sampled timeline");
 }
 if(!in.eof()||!identity||found.size()!=expected.size())return fail("incomplete original SnakeCrow authored bank");
 error.clear();return true;
}
} }
