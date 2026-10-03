#include "pc_p2_hanachirashi_source_policy.h"
#include <cassert>
#include <fstream>
#include <sstream>
#include <iostream>
using namespace p2hana;
int main(int argc,char** argv){
 assert(flyingNext(1800,0,0,0)==-1);assert(flyingNext(1800,1,0,1)==-1);
 assert(flyingNext(1800,1,0,1.001f)==FlyFlick);assert(flyingNext(1800,4,0,0)==Fall);
 assert(flyingNext(1800,1,1,0)==Fall);assert(flyingNext(0,1,1,0)==Dead);
 assert(airborne(Fall,.75f));assert(!airborne(Fall,.751f));assert(!airborne(TakeOff,.999f));assert(airborne(TakeOff,1));
 V emitter{},axis=unit({0,-.85f,1}),out;
 V centre=mul(axis,100);assert(wind(emitter,0,centre,300,false,out));assert(std::fabs(out.x)<.001f&&std::fabs(out.z)<.001f&&std::fabs(out.y-50)<.001f);
 assert(!wind(emitter,0,mul(axis,300),300,false,out));assert(!wind(emitter,0,mul(axis,-1),300,false,out));
 V edge=add(centre,{40,0,0});assert(!wind(emitter,0,edge,300,false,out));
 V inside=add(centre,{10,0,0});assert(wind(emitter,0,inside,300,false,out));assert(out.y>10&&out.y<50);
 V pik=out;assert(wind(emitter,0,inside,300,true,out));assert(out.y==0&&std::fabs(out.x)<std::fabs(pik.x));
 float frame=49;bool fired=false;auto key=advanceClock("attack",frame,false,fired,1.f/30,105);assert(key.key2&&!key.end&&fired);
 key=advanceClock("attack",frame,false,fired,1.f/30,105);assert(!key.key2);
 frame=38;fired=false;key=advanceClock("move1",frame,false,fired,2.f/30,40);assert(frame==1&&!key.end);
 frame=18;key=advanceClock("type2",frame,false,fired,2.f/30,25);assert(frame==6&&!key.end);
 frame=18;key=advanceClock("type2",frame,true,fired,7.f/30,25);assert(key.end&&frame==24);
 if(argc>1){std::ifstream in(argv[1]);std::string data((std::istreambuf_iterator<char>(in)),{}),error;JointBank bank;std::istringstream input(data);assert(readJoints(input,bank,error));assert(bank.size()==11);
  unsigned count=0;for(const auto& c:bank)count+=unsigned(c.second.size());assert(count==697);
  auto pose=sample(bank,"attack",50.5f);assert(std::isfinite(pose.emitter.y));
  for(std::string mutation:{std::string("P2_HANACHIRASHI_JOINTS_1 54 11 9\n"),data.substr(0,data.size()/2),data+"extra\n"}){std::istringstream bad(mutation);JointBank unchanged=bank;assert(!readJoints(bad,unchanged,error));assert(unchanged.size()==11);}
  auto corrupted=data;auto where=corrupted.find("frame 0");assert(where!=std::string::npos);corrupted.replace(where,7,"frame 1");std::istringstream bad(corrupted);assert(!readJoints(bad,bank,error));
 }
 std::cout<<"source55 clock, flight, 3D wind and complete joint-bank checks PASS\n";
}
