#include "pc_p2_original_wisp_save.h"
#include <cassert>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
using namespace p2original;using namespace p2original::wisp;
struct Comma:std::numpunct<char>{char do_decimal_point()const override{return ',';}};
int main(){
 std::locale::global(std::locale(std::locale::classic(),new Comma));
 const std::string campaign(64,'c'),catalog(64,'a');Initial initial;Snapshot s;s.identity={catalog,42,3,std::numeric_limits<std::uint64_t>::max(),std::numeric_limits<std::uint64_t>::max()};s.cargo={catalog,42,3,s.identity.epoch,s.identity.activation};s.spawn[1]={-30,0,200};s.eggBorn=true;s.state=State::Move;s.motion=0;s.scale=1;s.atari=true;s.hidden=false;s.clock={6.125f,1,false,false};s.position={1.23456789f,-12.75f,500.125f};s.velocity={std::numeric_limits<float>::min(),-0.0f,35.0000038f};s.targetVelocity={1.23456789f,0,35.0000038f};s.pitch=.987654321f;s.timer=1.23456789f;
 const std::vector<Key> keys={{0,0},{99,1}};std::string bytes,e;
 assert(encodeSnapshot(s,campaign,initial,100,keys,bytes,e));assert(bytes.size()<8192&&bytes.find(',')==std::string::npos);
 Snapshot decoded;assert(decodeSnapshot(bytes,campaign,initial,100,keys,decoded,e));std::string roundtrip;assert(encodeSnapshot(decoded,campaign,initial,100,keys,roundtrip,e));assert(bytes==roundtrip);assert(decoded.identity.catalog==catalog&&decoded.cargo.fingerprint==catalog&&catalog!=campaign);assert(decoded.velocity.x==s.velocity.x&&std::signbit(decoded.velocity.y));
 std::vector<std::string> fields;std::istringstream in(bytes);std::string word;while(in>>word)fields.push_back(word);assert(fields.size()==46&&fields[1]==campaign&&fields[2]==catalog);
 // Existing mutation indices name snapshot fields; the explicit campaign
 // envelope inserted after magic is tested independently below.
 auto change=[&](unsigned index,const std::string& value){auto next=fields;next[index?index+1:0]=value;std::ostringstream out;for(unsigned i=0;i<next.size();++i){if(i)out<<' ';out<<next[i];}return out.str();};
 auto reject=[&](const std::string& bad,const std::string& expected=std::string(64,'c')){Snapshot result=s;assert(!decodeSnapshot(bad,expected,initial,100,keys,result,e));std::string unchanged;assert(encodeSnapshot(result,campaign,initial,100,keys,unchanged,e));assert(unchanged==bytes);};
 reject("");reject(std::string(8193,'x'));reject(bytes+" trailing");reject(bytes+"\n");reject(bytes+char(127));reject(bytes,std::string(64,'b'));reject(bytes,"short");
 reject(bytes,catalog);auto wrongEnvelope=bytes;wrongEnvelope.replace(6,64,catalog);reject(wrongEnvelope);
 for(unsigned index:{2u,3u,4u,5u,6u,7u,8u,34u,38u,39u,40u,41u,42u}){reject(change(index,"-1"));reject(change(index,"+1"));reject(change(index,"18446744073709551616"));}
 for(unsigned index:{28u,29u,30u,31u,32u,35u,36u,43u,44u})for(const char* bad:{"2","-0","+1","00","true"})reject(change(index,bad));
 reject(change(0,"P2OW2"));reject(change(1,"short"));reject(change(37,std::string(64,'b')));reject(change(42,"1"));reject(change(34,"0"));reject(change(15,"nan"));reject(change(21,"inf"));reject(change(12,"-29"));reject(change(6,"999"));
 std::string output="preserve";auto bad=s;bad.cargo.activation--;assert(!encodeSnapshot(bad,campaign,initial,100,keys,output,e)&&output=="preserve");assert(!encodeSnapshot(s,"short",initial,100,keys,output,e)&&output=="preserve");
 Snapshot untouched=s;assert(!decodeSnapshot(bytes,campaign,Initial{201,30},100,keys,untouched,e));assert(!decodeSnapshot(bytes,campaign,initial,100,{{0,0},{5,1}},untouched,e));
 // Carried and independently released Egg outcomes both survive Dead state.
 s.state=State::Dead;s.motion=2;s.alive=false;s.dead=true;s.cullable=false;s.clock={0,0,false,false};s.targetVelocity={0,400,0};
 for(bool released:{false,true}){s.released=released;assert(encodeSnapshot(s,campaign,initial,10,{{0,0},{9,1}},output,e));assert(decodeSnapshot(output,campaign,initial,10,{{0,0},{9,1}},decoded,e));assert(decoded.released==released&&decoded.eggBorn&&decoded.cargoSlot==0);}
 // Literal generator tail permits signed distances; do not invent a new limit.
 s.spawn[1]={30,0,-200};assert(encodeSnapshot(s,campaign,Initial{-200,-30},10,{{0,0},{9,1}},output,e));assert(decodeSnapshot(output,campaign,Initial{-200,-30},10,{{0,0},{9,1}},decoded,e));
 std::cout<<"Wisp save codec PASS bounded strict parsing, exact roundtrip, identity/context and failure atomicity\n";
}
