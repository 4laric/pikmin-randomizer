#include "pc_p2_original_gas_links.h"
#include <cassert>
#include <cstdio>
#include <limits>
#include <map>

using namespace p2original;
using namespace p2original::gas;
// Fake source producer census/state only. No native gameplay claim.
struct Census {
 bool story=true,failBridges=false,failGates=false;
 unsigned bridgeReads=0,gateReads=0;
 std::vector<SourceStructureLink> bridges,gates;
 std::map<std::string,int> stages;
 std::map<std::string,bool> alive;
 StructureReaders readers(){return {
  [this]{return story;},
  [this](std::vector<SourceStructureLink>& out,std::string& e){++bridgeReads;if(failBridges){e="bridge unavailable";return false;}out=bridges;return true;},
  [this](std::vector<SourceStructureLink>& out,std::string& e){++gateReads;if(failGates){e="gate unavailable";return false;}out=gates;return true;},
  [this](const std::string& key,int& out,std::string& e){auto it=stages.find(key);if(it==stages.end()){e="source bridge incarnation retired";return false;}out=it->second;return true;},
  [this](const std::string& key,bool& out,std::string& e){auto it=alive.find(key);if(it==alive.end()){e="source gate incarnation retired";return false;}out=it->second;return true;}
 };}
};
static const std::string sha(64,'a');
static std::string id(const char* key){return sha+":"+key;}
int main(){
 std::string e;
 // Both producers and live-state readers must exist, even when the verified
 // census contains zero structures. Missing producer never means empty list.
 for(int missing=0;missing<5;++missing){Census c;auto r=c.readers();switch(missing){case 0:r.surfaceStory={};break;case 1:r.bridges={};break;case 2:r.gates={};break;case 3:r.bridgeStage={};break;case 4:r.gateAlive={};break;}Links links(r);assert(!links.linksReady(e)&&!e.empty());}
 {Census c;Links links(c.readers());assert(links.linksReady(e));void* b=nullptr;void* g=nullptr;assert(links.livingLinks({0,0,0},b,g,e)&&!b&&!g);c.failBridges=true;assert(!links.linksReady(e));c.failBridges=false;c.failGates=true;assert(!links.linksReady(e));}
 {Census c;c.bridges={{id("bridge-first"),{70,24,70}},{id("bridge-closer"),{0,0,0}}};c.gates={{id("gate-closest"),{0,0,0}}};c.stages[id("bridge-first")]=0;Links links(c.readers());assert(links.linksReady(e));
  unsigned before=c.gateReads;void* b=nullptr;void* g=nullptr;assert(links.livingLinks({0,0,0},b,g,e)&&b&&!g&&c.gateReads==before);
  std::string identity;bool bridge=false;assert(links.identity(b,identity,bridge)&&identity==id("bridge-first")&&bridge);
  int stage=-1;assert(links.bridgeStage(b,stage,e)&&stage==0);c.stages[identity]=2;assert(links.bridgeStage(b,stage,e)&&stage==2);
  void* restored=nullptr;assert(links.resolveLink(identity,true,restored,e)&&restored==b);assert(!links.resolveLink(identity,false,restored,e)&&!restored);
  bool alive=false;assert(!links.gateAlive(b,alive,e));c.stages.erase(identity);assert(!links.bridgeStage(b,stage,e));assert(!links.resolveLink(identity,true,restored,e)&&!restored);
  void* same=nullptr;assert(links.livingLinks({0,0,0},same,g,e)&&same==b);
 }
 // Bounds are an axis-aligned box with strict retail inequalities, including
 // exact negative edges; it is neither a radial nearest search nor inclusive.
 for(auto pos:std::vector<Position>{{75,0,0},{-75,0,0},{0,25,0},{0,-25,0},{0,0,75},{0,0,-75}}){Census c;c.bridges={{id("outside"),pos}};c.gates={{id("gate-first"),{74.999f,24.999f,-74.999f}},{id("gate-closer"),{0,0,0}}};c.alive[id("gate-first")]=true;Links links(c.readers());assert(links.linksReady(e));void* b=nullptr;void* g=nullptr;assert(links.livingLinks({0,0,0},b,g,e)&&!b&&g);
  std::string identity;bool bridge=true;assert(links.identity(g,identity,bridge)&&!bridge&&identity==id("gate-first"));bool live=false;assert(links.gateAlive(g,live,e)&&live);c.alive[identity]=false;assert(links.gateAlive(g,live,e)&&!live);int stage=0;assert(!links.bridgeStage(g,stage,e));c.alive.erase(identity);assert(!links.gateAlive(g,live,e));}
 {Census c;c.bridges={{id("bridge"),{0,0,0}}};c.gates={{id("gate"),{0,0,0}}};c.story=false;Links links(c.readers());assert(links.linksReady(e));unsigned beforeB=c.bridgeReads,beforeG=c.gateReads;void* b=reinterpret_cast<void*>(1);void* g=reinterpret_cast<void*>(1);assert(links.livingLinks({0,0,0},b,g,e)&&!b&&!g&&c.bridgeReads==beforeB&&c.gateReads==beforeG);}
 for(auto invalid:std::vector<std::vector<SourceStructureLink>>{{{"",{0,0,0}}},{{id("dup"),{0,0,0}},{id("dup"),{1,0,0}}},{{id("nan"),{0,std::numeric_limits<float>::quiet_NaN(),0}}}}){Census c;c.bridges=invalid;Links links(c.readers());assert(!links.linksReady(e));void* b=nullptr;void* g=nullptr;assert(!links.livingLinks({0,0,0},b,g,e));c.bridges.clear();c.gates=invalid;assert(!links.linksReady(e));assert(!links.livingLinks({0,0,0},b,g,e));}
 {Census c;Links links(c.readers());int foreign=0;void* unknown=&foreign;int stage=0;bool live=false,bridge=false;std::string identity;assert(!links.identity(unknown,identity,bridge));assert(!links.bridgeStage(unknown,stage,e));assert(!links.gateAlive(unknown,live,e));}
 std::puts("P2_ORIGINAL_GAS_LINKS_POLICY_PASS: ordered retail links, strict bounds, live producer state and identity handles; no gameplay claim");
}
