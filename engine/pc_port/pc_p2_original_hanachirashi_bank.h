#pragma once
#include <istream>
#include <map>
#include <sstream>
#include <string>
namespace p2original { namespace hanachirashi {
struct Clock {int duration=0;std::string events;};
inline const std::map<std::string,Clock>& retailClocks(){
 static const std::map<std::string,Clock> rows={{"attack",{105,"50:2"}},{"damage",{45,"15:2"}},{"dead",{120,"-"}},{"dead2",{120,"-"}},{"flick",{55,"25:2"}},{"laugh",{64,"-"}},{"move1",{40,"0:0,39:1"}},{"move2",{23,"-"}},{"type1",{60,"30:2"}},{"type2",{25,"5:0,19:1"}},{"wait2",{40,"0:0,39:1"}}};return rows;
}
// Literal GPVE01 rev0 durations from the private retail BCA archive; event
// lists from enemyanimmgr.txt. Asset bytes remain private. Whole-source clock
// validation rejects a partial bank before native managers or actors change.
inline bool validateBank(std::istream& input,std::string& error){
 auto fail=[&](const char* why){error=why;return false;};
 std::string line;if(!std::getline(input,line)||line!="P2_FLYING_BANK_1")return fail("original Hanachirashi bank header missing");
 std::map<std::string,Clock> found;bool identity=false;
 while(std::getline(input,line)){
  std::istringstream row(line);std::string kind,species;if(!(row>>kind))continue;
  if(kind=="species"){
   std::string id,extra;if(!(row>>species>>id))return fail("invalid flying species identity");
   if(species!="Hanachirashi")continue;
   if(identity)return fail("duplicate Hanachirashi identity");
   if(id=="clips"){int count=0;if(!(row>>count)||count!=11||(row>>extra))return fail("Hanachirashi literal clip inventory mismatch");}
   else if(id!="55"||(row>>extra))return fail("Hanachirashi literal source identity mismatch");
   identity=true;
  }else if(kind=="clip"){
   std::string name,events,marker,status;if(!(row>>species>>name))return fail("invalid flying clip identity");
   if(species!="Hanachirashi")continue;
   int duration=0,poses=0;if(!identity||!(row>>duration>>events>>marker>>poses>>status))return fail("truncated Hanachirashi clock");
   if(status=="status"&&!(row>>status))return fail("truncated Hanachirashi status");
   auto literal=retailClocks().find(name);
   if(literal==retailClocks().end()||duration!=literal->second.duration||events!=literal->second.events||marker!="poses"||poses<1||poses>64||status!="converted"||!found.emplace(name,Clock{duration,events}).second)return fail("Hanachirashi literal duration/event/resource mismatch");
   std::string trailer;if(row>>trailer){if(trailer!="frames"||!(row>>trailer))return fail("invalid Hanachirashi sampled-frame trailer");std::string extra;if(row>>extra)return fail("trailing Hanachirashi clock data");}
  }else if(kind=="frames"){
   std::string frames,extra;if(!(row>>frames)||(row>>extra))return fail("invalid sampled frames row");
  }else return fail("unknown flying bank row");
 }
 if(!identity||found.size()!=retailClocks().size())return fail("original Hanachirashi complete clocks missing");
 error.clear();return true;
}
} }
