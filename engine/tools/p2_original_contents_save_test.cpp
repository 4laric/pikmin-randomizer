#include "pc_p2_original_contents_save.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <limits>
using namespace p2originalresource;
ContentsRecord single(unsigned uid=0x52000001u){ContentsRecord r;r.source={std::string(64,'a'),uid,0,7,4};r.type=P2EggDropType::SingleNectar;r.complete=true;ChildOutcome c;c.identity={r.source,0};c.kind=ChildKind::Nectar;c.position={1,2,3};c.velocity={0,250,0};c.attempted=c.born=true;r.children={c};return r;}
std::string replace(std::string bytes,const std::string& from,const std::string& to){auto at=bytes.find(from);assert(at!=std::string::npos);bytes.replace(at,from.size(),to);return bytes;}
int main(){
 const std::string campaign(64,'b');std::string e,bytes;
 std::vector<ContentsRecord> rows;for(unsigned type=0;type<7;++type){auto r=single(0x52000001u+type);r.type=static_cast<P2EggDropType>(type);auto& child=r.children[0];
  if(type==0)child.kind=ChildKind::PelletOne;
  if(type==1)child.kind=ChildKind::PelletFive;
  if(type==3){auto second=child;second.identity.slot=1;second.born=false;r.children.push_back(second);}
  if(type==4){child.kind=ChildKind::MititeGroup;child.mititeCount=10;child.born=false;auto fallback=single().children[0];fallback.identity={r.source,1};r.children.push_back(fallback);}
  if(type==5)child.kind=ChildKind::Spicy;
  if(type==6)child.kind=ChildKind::Bitter;
  rows.push_back(r);
 }
 rows[0].children[0].consumed=true;
 rows[1].source.epoch=rows[1].source.activation=std::numeric_limits<std::uint64_t>::max();rows[1].children[0].identity.source=rows[1].source;
 rows[2].children[0].position.x=std::numeric_limits<float>::denorm_min();rows[2].children[0].position.y=-0.0f;rows[2].children[0].facing=std::numeric_limits<float>::max();
 assert(encodeContents(rows,campaign,bytes,e));std::vector<ContentsRecord> decoded;assert(decodeContents(bytes,campaign,decoded,e));std::string roundtrip;assert(encodeContents(decoded,campaign,roundtrip,e)&&bytes==roundtrip);
 assert(decoded[0].children[0].consumed&&decoded[1].source.epoch==std::numeric_limits<std::uint64_t>::max());
 assert(std::memcmp(&rows[2].children[0].position.x,&decoded[2].children[0].position.x,sizeof(float))==0);
 assert(std::memcmp(&rows[2].children[0].position.y,&decoded[2].children[0].position.y,sizeof(float))==0);
 // Every byte truncation before complete end marker rejects atomically.
 const auto sentinel=single(9);auto refuses=[&](const std::string& bad,const std::string& hash=std::string(64,'b')){std::vector<ContentsRecord> out{sentinel};assert(!decodeContents(bad,hash,out,e));assert(out.size()==1&&out[0].source==sentinel.source);};
 for(std::size_t n=0;n<bytes.size()-1;++n)refuses(bytes.substr(0,n));
 refuses(bytes,std::string(64,'c'));refuses(bytes,std::string(63,'b'));refuses(bytes,std::string(64,'B'));
 refuses(bytes+std::string(200,'X'));refuses(bytes+"garbage");refuses(std::string(1024*1024+1,' '));
 refuses(replace(bytes,"P2_EGG_CONTENTS 1","P2_EGG_CONTENTS 2"));refuses(replace(bytes,"records 7","records 4097"));refuses(replace(bytes,"records 7","records -7"));refuses(replace(bytes,"records 7","records +7"));
 const auto uid=std::to_string(rows[0].source.uid);refuses(replace(bytes," "+uid+" 0 7 4"," -1 0 7 4"));refuses(replace(bytes," "+uid+" 0 7 4"," 4294967296 0 7 4"));
 refuses(replace(bytes," "+uid+" 0 7 4"," "+uid+" 0 18446744073709551616 4"));
 refuses(replace(bytes,"child 0 0 1 2 3 0 250 0 0 0 0 1 1 1","child 0 0 nan 2 3 0 250 0 0 0 0 1 1 1"));
 refuses(replace(bytes,"child 0 0 1 2 3 0 250 0 0 0 0 1 1 1","child 0 0 1e100 2 3 0 250 0 0 0 0 1 1 1"));
 refuses(replace(bytes,"child 0 0 1 2 3 0 250 0 0 0 0 1 1 1","child 0 0 1 2 3 0 250 0 0 0 0 true 1 1"));
 refuses(replace(bytes,"child 0 0 1 2 3 0 250 0 0 0 0 1 1 1","child 0 0 1 2 3 0 250 0 0 0 0 1 0 1"));
 std::string untouched="sentinel";auto invalid=rows;invalid[0].complete=false;assert(!encodeContents(invalid,campaign,untouched,e)&&untouched=="sentinel");
 invalid=rows;invalid[0].children[0].identity.source.uid++;assert(!encodeContents(invalid,campaign,untouched,e)&&untouched=="sentinel");
 invalid=rows;invalid[0].children[0].identity.ancestry={{EmitterKind::PlantSpectralid,0,0}};assert(!encodeContents(invalid,campaign,untouched,e)&&untouched=="sentinel");
 invalid=rows;invalid.push_back(invalid[0]);assert(!encodeContents(invalid,campaign,untouched,e)&&untouched=="sentinel");
 invalid=rows;invalid[0].children[0].velocity.y=std::numeric_limits<float>::infinity();assert(!encodeContents(invalid,campaign,untouched,e)&&untouched=="sentinel");
 std::vector<ContentsRecord> boundary;for(unsigned i=0;i<4096;++i)boundary.push_back(single(0x52000001u+i));
 assert(encodeContents(boundary,campaign,bytes,e)&&decodeContents(bytes,campaign,decoded,e)&&decoded.size()==4096);boundary.push_back(single(0x53000001u));
 assert(!encodeContents(boundary,campaign,untouched,e)&&untouched=="sentinel");boundary.pop_back();
 for(unsigned i=0;i<boundary.size();++i){auto& r=boundary[i];r.source.uid=std::numeric_limits<std::uint32_t>::max()-i;r.source.ordinal=std::numeric_limits<std::uint32_t>::max();r.source.epoch=r.source.activation=std::numeric_limits<std::uint64_t>::max();auto& c=r.children[0];c.identity.source=r.source;c.position=c.velocity={-std::numeric_limits<float>::max(),-std::numeric_limits<float>::max(),-std::numeric_limits<float>::max()};c.facing=-std::numeric_limits<float>::max();}
 assert(!encodeContents(boundary,campaign,untouched,e)&&untouched=="sentinel"); // byte bound independently of record bound
 assert(encodeContents({},campaign,bytes,e)&&decodeContents(bytes,campaign,decoded,e)&&decoded.empty());
 std::cout<<"PASS bounded EggContents codec roundtrip/campaign/typed-outcome/atomic-malformed checks; no runtime writes\n";
}
