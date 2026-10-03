#pragma once
#include <istream>
#include <sstream>
#include <string>
#include <map>
#include <set>
#include <vector>
#include <cmath>
namespace p2original { namespace catfish {
// GPVE01 Catfish authored enemyanimmgr events and BCA durations. The
// existing general-purpose loader is permissive; original admission is not.
inline bool validateCatfishBank(std::istream& in,std::string& error){
 const std::map<std::string,std::pair<unsigned,std::string>> expected={
 {"attack",{85,"17:2,75:3"}},{"dead",{95,"-"}},{"flick",{70,"25:2,47:3"}},
 {"move1",{25,"0:0,24:1"}},{"type5",{40,"10:0,29:1"}},
 {"wait1",{30,"-"}},{"waitact2",{16,"-"}}};
 auto fail=[&](const char* why){error=why;return false;};
 std::string line;if(!std::getline(in,line))return fail("missing original Catfish bank");
 if(!line.empty()&&line.back()=='\r')line.pop_back();
 if(line!="P2_AQUATIC_BANK_1")return fail("original Catfish bank header mismatch");
 std::set<std::string> found;bool identity=false;unsigned lines=0;
 while(std::getline(in,line)){
  if(++lines>256||line.size()>32768)return fail("oversized original Catfish bank");
  std::istringstream row(line);std::string kind,species;if(!(row>>kind>>species))return fail("malformed original Catfish bank row");
  if(kind=="species"){
   unsigned source;std::string extra;if(!(row>>source)||(row>>extra))return fail("malformed Catfish species identity");
   if(species=="Catfish"){if(source!=26||identity)return fail("original Catfish source identity mismatch");identity=true;}
   continue;
  }
  if(kind!="clip")return fail("unexpected original Catfish bank row");
  if(species!="Catfish")continue;
  std::string name,events,posesKey,status,framesKey,frames,extra;unsigned duration,poses;
  if(!(row>>name>>duration>>events>>posesKey>>poses>>status>>framesKey>>frames)||(row>>extra))return fail("malformed original Catfish clip row");
  auto expectedClip=expected.find(name);
  if(!identity||expectedClip==expected.end()||!found.insert(name).second||duration!=expectedClip->second.first||events!=expectedClip->second.second
   ||posesKey!="poses"||status!="converted"||framesKey!="frames"||poses<2||poses>64)return fail("original Catfish clip/event/status mismatch");
  std::istringstream list(frames);std::string value;unsigned count=0;double previous=-1;
  while(std::getline(list,value,',')){std::istringstream number(value);double frame;std::string trailing;
   if(!(number>>frame)||(number>>trailing)||!std::isfinite(frame)||frame<=previous||frame<0||frame>duration-1||(count==0&&frame!=0))return fail("invalid original Catfish sampled frame");
   previous=frame;++count;
  }
  if(count!=poses||previous!=duration-1)return fail("incomplete original Catfish sampled timeline");
 }
 if(!in.eof()||!identity||found.size()!=expected.size())return fail("incomplete original Catfish authored bank");
 error.clear();return true;
}
} }
