#include "pc_p2_original_egg_save.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <limits>
#include <sstream>
#include <vector>
using namespace p2original;
namespace {
std::string replace(const std::string& bytes,unsigned index,const std::string& value){std::istringstream in(bytes);std::vector<std::string> words;std::string w;while(in>>w)words.push_back(w);assert(index<words.size());words[index]=value;std::string out;for(const auto& s:words){if(!out.empty())out+=' ';out+=s;}return out;}
bool bits(float a,float b){return std::memcmp(&a,&b,sizeof(float))==0;}
}
int main(){
 const std::string campaign(64,'c');std::string e,bytes;
 egg::SnapshotContext c;c.identity={std::string(64,'a'),0x52000025u,1,2,std::numeric_limits<std::uint64_t>::max()};c.resourceFingerprint=std::string(64,'b');c.maxHealth=50;
 egg::Snapshot s;s.identity=c.identity;s.resourceFingerprint=c.resourceFingerprint;s.flags.constrained=true;s.health=50;
 s.position={-0.0f,std::numeric_limits<float>::denorm_min(),std::numeric_limits<float>::max()};s.velocity={1.23456789f,-2.5f,0};s.targetVelocity={3,4,5};s.scale={.2f,2,3};s.facing=-1.25f;s.flickTimer=.6f;s.sourceFrame=17.5f;s.stopped=false;s.flags.lifeGauge=true;
 assert(egg::encodeSnapshot(s,campaign,c,bytes,e));egg::Snapshot decoded;assert(egg::decodeSnapshot(bytes,campaign,c,decoded,e));
 assert(bits(s.position.x,decoded.position.x)&&bits(s.position.y,decoded.position.y)&&bits(s.position.z,decoded.position.z));assert(decoded.identity==s.identity&&decoded.flags.lifeGauge&&decoded.sourceFrame==17.5f);
 std::string roundtrip;assert(egg::encodeSnapshot(decoded,campaign,c,roundtrip,e)&&roundtrip==bytes);
 auto refuses=[&](const std::string& bad,const std::string& sha=std::string()){egg::Snapshot sentinel;sentinel.resourceFingerprint="unchanged";sentinel.health=123;assert(!egg::decodeSnapshot(bad,sha.empty()?campaign:sha,c,sentinel,e));assert(sentinel.resourceFingerprint=="unchanged"&&sentinel.health==123);};
 for(std::size_t n=0;n<bytes.size();++n)refuses(bytes.substr(0,n));
 refuses(bytes,std::string(64,'d'));refuses(bytes,std::string(64,'A'));refuses(bytes,std::string(63,'c'));refuses(bytes+" trailing");refuses(bytes+std::string(129,'x'));refuses(std::string(8193,' '));
 for(auto value:{"P2OE2","P2OE0"}){refuses(replace(bytes,0,value));}refuses(replace(bytes,2,std::string(64,'A')));refuses(replace(bytes,7,std::string(64,'d')));
 for(auto value:{"-1","+1","4294967296","1x"}){refuses(replace(bytes,3,value));}refuses(replace(bytes,5,"18446744073709551616"));refuses(replace(bytes,8,"+0"));refuses(replace(bytes,8,"1"));
 for(auto value:{"nan","inf","0x1p2","1e99","1e","--1"})refuses(replace(bytes,9,value));
 for(auto value:{"2","-0","+1","00","true"})refuses(replace(bytes,25,value));
 refuses(replace(bytes,22,"51"));refuses(replace(bytes,24,"31"));refuses(replace(bytes,26,"1"));refuses(replace(bytes,40,"1"));refuses(replace(bytes,42,"1"));
 auto wrong=c;wrong.identity.epoch++;egg::Snapshot sentinel;sentinel.resourceFingerprint="unchanged";assert(!egg::decodeSnapshot(bytes,campaign,wrong,sentinel,e)&&sentinel.resourceFingerprint=="unchanged");
 auto bad=s;bad.position.y=std::numeric_limits<float>::infinity();std::string unchanged="unchanged";assert(!egg::encodeSnapshot(bad,campaign,c,unchanged,e)&&unchanged=="unchanged");assert(!egg::encodeSnapshot(s,std::string(64,'A'),c,unchanged,e)&&unchanged=="unchanged");
 // Dropgroup and zero-health destruction progress retain every source flag.
 s.dropGroup=c.dropGroup=true;s.flags.constrained=false;s.health=0;s.contentsGenerated=s.effectsEmitted=s.killRequested=true;
 assert(egg::encodeSnapshot(s,campaign,c,bytes,e)&&egg::decodeSnapshot(bytes,campaign,c,decoded,e));assert(decoded.dropGroup&&decoded.killRequested&&decoded.contentsGenerated&&decoded.effectsEmitted);
 // Captured pending kill is valid only with the already-bound authored graph.
 s=egg::Snapshot{};c.dropGroup=false;c.dependent=c.actualCaptureBound=true;c.actualParent=c.identity;c.capturePosition={10,20,30};s.identity=c.identity;s.resourceFingerprint=c.resourceFingerprint;s.dependent=s.captured=s.hasParent=true;s.parentIdentity=c.identity;s.position=c.capturePosition;s.flags.constrained=s.flags.invulnerable=true;s.flags.cullable=s.flags.living=false;
 assert(egg::encodeSnapshot(s,campaign,c,bytes,e)&&egg::decodeSnapshot(bytes,campaign,c,decoded,e));assert(decoded.captured&&decoded.parentIdentity==c.identity&&decoded.health==0);
 wrong=c;wrong.actualCaptureBound=false;assert(!egg::decodeSnapshot(bytes,campaign,wrong,sentinel,e)&&sentinel.resourceFingerprint=="unchanged");wrong=c;wrong.actualParent.activation--;assert(!egg::decodeSnapshot(bytes,campaign,wrong,sentinel,e));refuses(replace(bytes,47,"1"));
 // Independent falling cargo retains its full source incarnation, no parent.
 s.captured=s.hasParent=false;s.parentIdentity={};s.falling=true;s.flags.constrained=false;s.flags.cullable=s.flags.living=true;s.velocity.y=-5;c.actualCaptureBound=false;c.actualParent={};
 assert(egg::encodeSnapshot(s,campaign,c,bytes,e)&&egg::decodeSnapshot(bytes,campaign,c,decoded,e));assert(decoded.dependent&&decoded.falling&&!decoded.hasParent&&decoded.parentIdentity.fingerprint.empty());
 std::cout<<"PASS bounded Egg snapshot codec identity/campaign/capture/precision/atomic refusal policy checks; no gameplay claim\n";
}
