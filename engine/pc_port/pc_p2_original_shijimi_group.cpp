#include "pc_p2_original_shijimi_group.h"
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace p2original { namespace shijimi {
namespace {
bool reject(std::string& e,const char* s){e=s;return false;}
bool finite(const Position& p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
bool color(Color c){return unsigned(c)<=2;}
bool parentIdentity(const InstanceIdentity& id){
 if(id.catalog.size()!=64||!id.generator||!id.epoch||!id.activation)return false;
 for(char c:id.catalog)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;
 return true;
}
constexpr float tau=6.2831853071795864769f;
struct Rollback {
 Engine& engine;Group& group;std::string& error;bool finished=false;
 ~Rollback(){if(!finished){std::string cleanup;if(!engine.abort(group,cleanup))error+="; emission cleanup failed: "+cleanup;}}
};
}
bool PlantGroups::touch(const InstanceIdentity& id,unsigned source,const Position& plant,float height,
 Engine& engine,Group& out,std::string& e){
 if((source!=50&&source!=87)||!finite(plant)||!std::isfinite(height)||height<0
   ||!parentIdentity(id)||!engine.parent(id,source,e))return reject(e,"invalid authoritative Sentinel parent");
 auto previous=mGroups.find(id);
 if(previous!=mGroups.end()){
  Position origin=plant;origin.y+=height;
  if(previous->second.plantSource!=source||previous->second.origin.x!=origin.x||previous->second.origin.y!=origin.y||previous->second.origin.z!=origin.z)return reject(e,"Sentinel duplicate changed authored parent origin");
  if(!previous->second.complete)return reject(e,"Sentinel emission pending; no retry permitted");
  out=previous->second;e.clear();return true;
 }
 Group initial;initial.plant=id;initial.plantSource=source;initial.origin=plant;initial.origin.y+=height;
 initial.consumed=true;
 for(unsigned n=0;n<5;++n){initial.children[n].identity={id,0,n};initial.children[n].position=initial.origin;initial.children[n].home=initial.origin;}
 if(!finite(initial.origin)||!engine.emission(initial,e))return reject(e,"Sentinel origin lacks independent source authority");
 auto& group=mGroups.emplace(id,initial).first->second;
 group.managerPresent=engine.managerAvailable();
 if(!group.managerPresent){group.complete=true;out=group;e.clear();return true;}
 Rollback rollback{engine,group,e};
 auto& leader=group.children[0];leader.attempted=true;void* leaderObject=nullptr;
 if(!engine.birth(leader,leaderObject,e))return false;
 leader.born=leaderObject!=nullptr;
 if(!leader.born){group.complete=true;out=group;rollback.finished=true;e.clear();return true;}
 if(!engine.init(leader,leaderObject,leaderObject,e))return false;
 leader.initialized=true;
 if(!engine.leaderInit(leader,leaderObject,e))return false;
 engine.discardRand();
 leader.color=engine.randFloat()<0.5f?Color::Purple:Color::Red;
 if(!engine.leaderColor(leader,leaderObject,e))return false;
 for(unsigned n=1;n<5;++n){
  auto& child=group.children[n];child.facing=tau*float(n)/5.0f;
  child.position.y+=50.0f*engine.randFloat()-25.0f;child.attempted=true;
  void* object=nullptr;if(!engine.birth(child,object,e))return false;child.born=object!=nullptr;
  if(!child.born)continue;
  const float selection=engine.randFloat();
  child.appearance=selection<0.1f?Color::Red:selection<0.2f?Color::Purple:Color::Yellow;
  child.color=child.appearance;
  if(!engine.appear(child,object,e))return false;
  child.color=Color::Yellow;
  // Retail onInit overwrites follower home to its individual birth position.
  child.home=child.position;
  if(!engine.init(child,object,leaderObject,e))return false;
  child.initialized=true;
  group.sourceGroupCount=n;
 }
 group.complete=true;out=group;rollback.finished=true;e.clear();return true;
}
Child* PlantGroups::find(const Identity& id){auto i=mGroups.find(id.plant);if(i==mGroups.end()||id.emission||id.child>=5)return nullptr;return &i->second.children[id.child];}
bool PlantGroups::drop(const Identity& id,const Position& position,float facing,bool zukan,Engine& engine,std::string& e){
 auto* child=find(id);if(!child||!child->born||!child->initialized||!finite(position)||!std::isfinite(facing))return reject(e,"invalid Spectralid drop owner");
 if(child->dropAttempted){if(!child->dropComplete)return reject(e,"Spectralid drop pending; no retry permitted");e.clear();return true;}
 if(child->retired)return reject(e,"drop from retired Spectralid");
 if(zukan){e.clear();return true;}
 child->dropAttempted=true;
 if(child->color!=Color::Yellow&&!engine.sprayMade(child->color)){child->dropComplete=true;e.clear();return true;}
 Position pos=position;pos.y+=2;
 // Source uses sin(face) for BOTH horizontal components.
 const float lateral=std::sin(facing)*50.0f;Position velocity{lateral,200.0f,lateral};
 if(!engine.honey(*child,pos,velocity,child->dropBorn,e))return false;
 child->dropComplete=true;e.clear();return true;
}
bool PlantGroups::retire(const Identity& id,std::string& e){auto* child=find(id);if(!child||!child->born)return reject(e,"invalid Spectralid retirement");child->retired=true;e.clear();return true;}
bool PlantGroups::consume(const Identity& id,std::string& e){auto* child=find(id);if(!child||!child->dropBorn)return reject(e,"invalid Spectralid Honey consumption");child->dropConsumed=true;e.clear();return true;}
std::vector<Group> PlantGroups::snapshot()const{std::vector<Group> out;for(const auto& i:mGroups)out.push_back(i.second);return out;}
bool PlantGroups::restore(const std::vector<Group>& rows,Engine& engine,std::string& e){
 if(!mGroups.empty())return reject(e,"restore requires empty Spectralid emission journal");
 std::map<InstanceIdentity,Group> prospective;
 for(const auto& g:rows){
  if(!g.consumed||!g.complete||!finite(g.origin)||g.sourceGroupCount>4||(g.plantSource!=50&&g.plantSource!=87)
    ||!parentIdentity(g.plant)||!engine.parent(g.plant,g.plantSource,e)||!engine.emission(g,e)
    ||!prospective.emplace(g.plant,g).second)return reject(e,"invalid saved Sentinel emission parent");
  unsigned last=0;
  for(unsigned n=0;n<5;++n){const auto& c=g.children[n];
   if(!(c.identity==Identity{g.plant,0,n})||!finite(c.position)||!finite(c.home)||!std::isfinite(c.facing)
     ||!color(c.color)||!color(c.appearance)||(c.born&&!c.attempted)||c.initialized!=c.born
     ||(c.retired&&!c.born)||(c.dropAttempted&&!c.born)||c.dropComplete!=c.dropAttempted||(c.dropBorn&&!c.dropComplete)||(c.dropConsumed&&!c.dropBorn))return reject(e,"invalid saved Spectralid child");
   if(n&&c.born){last=n;if(c.color!=Color::Yellow)return reject(e,"plant follower is not source Yellow");}
   if(n==0&&c.born&&c.color==Color::Yellow)return reject(e,"plant leader lacks source Red/Purple kind");
   if(c.position.x!=g.origin.x||c.position.z!=g.origin.z)return reject(e,"saved Spectralid birth moved horizontally");
   if(n==0&&(c.position.y!=g.origin.y||c.home.x!=g.origin.x||c.home.y!=g.origin.y||c.home.z!=g.origin.z||c.facing!=0||c.appearance!=Color::Yellow))return reject(e,"saved Spectralid leader origin changed");
   if(n&&c.attempted&&(c.position.y<g.origin.y-25||c.position.y>g.origin.y+25||c.facing!=tau*float(n)/5.0f))return reject(e,"saved Spectralid follower scatter changed");
   if(n&&c.born&&(c.home.x!=c.position.x||c.home.y!=c.position.y||c.home.z!=c.position.z))return reject(e,"saved Spectralid follower onInit home changed");
   if((!g.managerPresent||(n&&!g.children[0].born))&&c.attempted)return reject(e,"impossible saved Spectralid attempt");
   if(g.managerPresent&&(n==0||g.children[0].born)&&!c.attempted)return reject(e,"missing saved Spectralid attempt");
  }
  if(last!=g.sourceGroupCount)return reject(e,"saved Spectralid group frontier mismatch");
 }
 mGroups=std::move(prospective);e.clear();return true;
}
bool PlantGroups::encode(Engine& engine,std::string& bytes,std::string& e){
 const auto rows=snapshot();PlantGroups verified;
 if(rows.size()>4096||!verified.restore(rows,engine,e))return reject(e,"Spectralid journal is not publishable");
 std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(std::numeric_limits<float>::max_digits10);
 out<<"P2_ORIGINAL_SENTINEL_JOURNAL_1 "<<rows.size()<<'\n';
 for(const auto& g:rows){
  out<<std::quoted(g.plant.catalog)<<' '<<g.plant.generator<<' '<<g.plant.ordinal<<' '<<g.plant.epoch<<' '<<g.plant.activation<<' '
     <<g.plantSource<<' '<<g.origin.x<<' '<<g.origin.y<<' '<<g.origin.z<<' '<<g.managerPresent<<' '<<g.sourceGroupCount<<'\n';
  for(const auto& c:g.children){
   unsigned flags=unsigned(c.attempted)|(unsigned(c.born)<<1)|(unsigned(c.initialized)<<2)|(unsigned(c.retired)<<3)
     |(unsigned(c.dropAttempted)<<4)|(unsigned(c.dropComplete)<<5)|(unsigned(c.dropBorn)<<6)|(unsigned(c.dropConsumed)<<7);
   out<<c.identity.emission<<' '<<c.identity.child<<' '<<c.position.x<<' '<<c.position.y<<' '<<c.position.z<<' '
      <<c.home.x<<' '<<c.home.y<<' '<<c.home.z<<' '<<c.facing<<' '<<unsigned(c.color)<<' '<<unsigned(c.appearance)<<' '<<flags<<'\n';
  }
 }
 if(!out||out.str().size()>4*1024*1024)return reject(e,"Spectralid journal size limit exceeded");
 bytes=out.str();e.clear();return true;
}
bool PlantGroups::decode(const std::string& bytes,Engine& engine,std::string& e){
 if(!mGroups.empty()||bytes.size()>4*1024*1024)return reject(e,"Spectralid decode requires empty bounded journal");
 std::istringstream in(bytes);in.imbue(std::locale::classic());std::string version;unsigned count;
 if(!(in>>version>>count)||version!="P2_ORIGINAL_SENTINEL_JOURNAL_1"||count>4096)return reject(e,"invalid Spectralid journal header");
 std::vector<Group> rows;
 for(unsigned n=0;n<count;++n){Group g;unsigned manager;
  if(!(in>>std::quoted(g.plant.catalog)>>g.plant.generator>>g.plant.ordinal>>g.plant.epoch>>g.plant.activation>>g.plantSource
    >>g.origin.x>>g.origin.y>>g.origin.z>>manager>>g.sourceGroupCount)||manager>1||g.plant.catalog.size()>256)return reject(e,"invalid Spectralid journal parent row");
  g.consumed=g.complete=true;g.managerPresent=manager!=0;
  for(auto& c:g.children){unsigned kind,appearance,flags;c.identity.plant=g.plant;
   if(!(in>>c.identity.emission>>c.identity.child>>c.position.x>>c.position.y>>c.position.z>>c.home.x>>c.home.y>>c.home.z
      >>c.facing>>kind>>appearance>>flags)||kind>2||appearance>2||flags>255)return reject(e,"invalid Spectralid journal child row");
   c.color=Color(kind);c.appearance=Color(appearance);c.attempted=flags&1;c.born=flags&2;c.initialized=flags&4;c.retired=flags&8;
   c.dropAttempted=flags&16;c.dropComplete=flags&32;c.dropBorn=flags&64;c.dropConsumed=flags&128;
  }
  rows.push_back(g);
 }
 if(in>>version)return reject(e,"trailing Spectralid journal bytes");
 return restore(rows,engine,e);
}
} }
