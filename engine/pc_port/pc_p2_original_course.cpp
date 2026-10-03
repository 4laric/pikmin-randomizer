#include "pc_p2_original_course.h"
#include "pc_p2_original_captain_motion.h"
#include "pc_p2_original_dispatch.h"
#include "pc_p2_original_gen_object.h"
#include "pc_p2_original_group_engine.h"
#include "pc_p2_original_pelplant_native.h"
#include "pc_p2_original_chappy_native.h"
#include "pc_p2_original_frog_native.h"
#include "pc_p2_original_uji_native.h"
#include "pc_p2_original_red_native.h"
#include "pc_p2_original_tank_native.h"
#include "pc_p2_original_armor_native.h"
#include "pc_p2_original_foliage_native.h"
#include "pc_p2_original_catfish_native.h"
#include "pc_p2_original_bulblax_snagret_native.h"
#include "pc_p2_original_hanachirashi_native.h"
#include "pc_p2_original_cannon_native.h"
#include "pc_p2_original_corpse_native.h"
#include "pc_p2_original_sprout_native.h"
#include "pc_p2_chappy.h"
#include "pc_p2_original_onyon_native.h"
#include "pc_p2_original_gate_native.h"
#include "pc_p2_original_bridge_native.h"
#include "pc_p2_original_barrel_native.h"
#include "pc_p2_original_cave_native.h"
#include "pc_p2_original_manifest.h"
#include "pc_p2_original_progress.h"
#include "pc_p2_original_calendar_state.h"
#include "pc_randomizer.h"
#include "pc_p2_original_piki_native.h"
#include "pc_p2_campaign_treasure_held.h"
#include "Creature.h"
#include "Stream.h"
#include "teki.h"
#include "Pellet.h"
#include <fstream>
#include <memory>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <filesystem>
#include <cmath>
namespace {
using namespace p2original;
struct Course {
 std::unique_ptr<captain::SourceBank> captains;
 std::unique_ptr<pelplant::Native> plants;
 std::unique_ptr<chappy::Native> chappies;
 std::unique_ptr<frog::Native> frogs;
 std::unique_ptr<uji::Native> ujis;
 std::unique_ptr<red::Native> reds;
 std::unique_ptr<tank::Native> tanks;
 std::unique_ptr<armor::Native> armors;
 std::unique_ptr<foliage::Native> foliage;
 std::unique_ptr<catfish::Native> catfishes;
 std::unique_ptr<bulblax_snagret::Native> bulblaxes;
 std::unique_ptr<hanachirashi::Native> witherings;
 std::unique_ptr<cannon::Native> cannons;
 Dispatch dispatch;
 std::map<unsigned,GeneratorState> literal;
 std::set<const Generator*> shadows;
 bool started=false;
 bool onyons=false;
 bool pikis=false;
 bool gates=false;
 bool bridges=false;
 bool barrels=false;
 bool caves=false;
 bool selectedSession=false;
 bool loaded=false;
 std::string course;
 std::vector<CalendarLoad> plannedLoads;
 std::set<unsigned> freshEnemies;
 std::map<unsigned,int> enemyExpiry;
 std::map<unsigned,int> itemExpiry;
 std::map<unsigned,unsigned> selectedEnemies;
 std::map<unsigned,std::pair<unsigned,int>> itemMetadata;
};
std::unique_ptr<Course> current;
CalendarLedger calendarLedger;
bool fail(std::string& e,const char* text){e=text;return false;}
}
bool pc_p2_original_course_prepare(const std::string& fingerprint,const std::vector<CatalogRow>& rows,
 const std::vector<GeneratorState>& literal,std::function<bool(unsigned)> metColor,std::string& e){
 if(current||!metColor||rows.size()!=literal.size())return fail(e,"original course prepare requires unowned complete source inventory");
 auto next=std::make_unique<Course>();next->plants=std::make_unique<pelplant::Native>(std::move(metColor));
 next->chappies=std::make_unique<chappy::Native>();next->frogs=std::make_unique<frog::Native>();next->ujis=std::make_unique<uji::Native>();
 next->reds=std::make_unique<red::Native>();next->tanks=std::make_unique<tank::Native>();next->armors=std::make_unique<armor::Native>();
 next->foliage=std::make_unique<foliage::Native>();
 next->catfishes=std::make_unique<catfish::Native>();next->bulblaxes=std::make_unique<bulblax_snagret::Native>();
 next->witherings=std::make_unique<hanachirashi::Native>();next->cannons=std::make_unique<cannon::Native>(pc_p2_original_corpse_resources);
 if(!next->dispatch.add(0,next->plants->provider(),[](const CatalogRow& r,std::string& e){pelplant::Initial value;return pelplant::decode(r,value,e);},e))return false;
 for(unsigned source:{2u,43u})if(!next->dispatch.add(source,next->chappies->provider(),chappy::admits,e))return false;
 for(unsigned source:{17u,18u})if(!next->dispatch.add(source,next->frogs->provider(),frog::capability,e))return false;
 for(unsigned source:{12u,13u,14u})if(!next->dispatch.add(source,next->ujis->provider(),uji::decode,e))return false;
 if(!next->dispatch.add(1,next->reds->provider(),red::capability,e))return false;
 for(unsigned source:{24u,25u})if(!next->dispatch.add(source,next->tanks->provider(),tank::decode,e))return false;
 if(!next->dispatch.add(15,next->armors->provider(),armor::admits,e))return false;
 for(unsigned source:{91u,88u})if(!next->dispatch.add(source,next->foliage->provider(),foliage::decode,e))return false;
 if(!next->dispatch.add(26,next->catfishes->provider(),catfish::decode,e))return false;
 for(unsigned source:{33u,34u})if(!next->dispatch.add(source,next->bulblaxes->provider(),bulblax_snagret::decode,e))return false;
 if(!next->dispatch.add(55,next->witherings->provider(),hanachirashi::decode,e))return false;
 for(unsigned source:{95u,96u})if(!next->dispatch.add(source,next->cannons->provider(),cannon::decode,e))return false;
 // Validate structural/source metadata atomically BEFORE publishing catalog.
 Catalog checked;
 if(!checked.install(fingerprint,rows,[&](const CatalogRow& r,std::string& e){if(pc_randomizer_original_session()){e.clear();return true;}return next->dispatch.capability(r,e);},e))return false;
 for(const auto& s:literal){auto* r=checked.find(s.uid);std::string bytes;
  if(!r||s.count!=r->enemy.count||s.epoch||s.activation||s.dayNum||s.deathCount
   ||!encodeOriginalState(fingerprint,s,bytes,e)||!next->literal.emplace(s.uid,s).second)
   return fail(e,"original literal inventory is incomplete, duplicated or contains runtime state");
 }
 if(!originalActors().install(fingerprint,rows,[&](const CatalogRow& r,std::string& e){if(pc_randomizer_original_session()){e.clear();return true;}return next->dispatch.capability(r,e);},e))return false;
 next->plants->onIdentity([](Creature* actor,std::string& identity,std::string& e){
  unsigned source=0,token=0;InstanceIdentity id;
  if(!originalActors().query(actor,source,token,&id)||source!=0)return fail(e,"original plant lost full course identity");
  identity=id.catalog+":"+std::to_string(id.generator)+":"+std::to_string(id.ordinal)+":"+std::to_string(id.epoch)+":"+std::to_string(id.activation);
  e.clear();return true;
 });
 next->plants->onDeath([](Creature* actor,std::string& e){
  if(!current||!current->started||!actor||!actor->mGenerator)return fail(e,"original plant death outside active course");
  bool handled=false;
  if(!pc_p2_original_generator_death(actor->mGenerator,actor,handled,e)||!handled)return false;
  // kill(false) calls Generator::informDeath itself. The source END above is
  // the one gameplay death; detach before disposal to prevent a second count.
  actor->mGenerator=nullptr;
  const unsigned token=pc_p2_original_actor_token(actor);
  if(!current->dispatch.release(actor,token,e))return false;
  pc_p2_original_native_retired(actor);return true;
 });
 current=std::move(next);e.clear();return true;
}
bool pc_p2_original_course_start(GeneratorList* list,std::string& e){
 if(!current||current->started||!list||!list->mGenListHead)return fail(e,"original course start requires prepared native generator list");
 std::vector<GroupBinding> bindings;std::map<unsigned,std::vector<Generator*>> inventory;
 std::vector<Generator*> onyonInventory;
 std::vector<Generator*> pikiInventory;
 std::vector<Generator*> gateInventory,bridgeInventory,barrelInventory,caveInventory;
 // Validate the entire list before collect mutates compatibility observations.
 for(auto* node=list->mGenListHead->mChild;node;node=node->mNext){
  auto* g=static_cast<Generator*>(node);auto* object=dynamic_cast<GenObjectOriginalEnemy*>(g->mGenObject);
  if(dynamic_cast<GenObjectOriginalOnyon*>(g->mGenObject))onyonInventory.push_back(g);
  if(dynamic_cast<GenObjectOriginalPiki*>(g->mGenObject))pikiInventory.push_back(g);
  if(dynamic_cast<GenObjectOriginalGate*>(g->mGenObject))gateInventory.push_back(g);
  if(dynamic_cast<GenObjectOriginalBridge*>(g->mGenObject))bridgeInventory.push_back(g);
  if(dynamic_cast<GenObjectOriginalBarrel*>(g->mGenObject))barrelInventory.push_back(g);
  if(dynamic_cast<GenObjectOriginalCave*>(g->mGenObject))caveInventory.push_back(g);
  if(!object)continue;
  auto found=current->literal.find(object->mState.uid);
  if(found==current->literal.end())return fail(e,"original native list has unknown source object");
  inventory[found->first].push_back(g);
 }
 if(current->selectedSession){
  for(unsigned uid:current->freshEnemies)if(!inventory.count(uid))return fail(e,"original native list omitted selected calendar enemy");
  for(const auto& entry:inventory){
   const auto* row=originalActors().find(entry.first);if(!row||!current->dispatch.capability(*row,e))return false;
   if(!current->freshEnemies.count(entry.first)){
    for(auto* g:entry.second)if(!g->readFromRam())return fail(e,"original disc enemy was not selected by literal calendar");
   }
  }
 }else if(inventory.size()!=current->literal.size())return fail(e,"original native list omitted source objects");
 std::set<const Generator*> shadows;
 for(const auto& entry:inventory){Generator* cached=nullptr;Generator* disc=nullptr;GroupBinding selected;
  for(auto* g:entry.second){GroupBinding b;
   if(!pc_p2_original_gen_object_collect(g,current->literal.at(entry.first),b,e))return false;
   if(g->readFromRam()){
    if(cached)return fail(e,"original native cache duplicates source UID");cached=g;selected=b;
   }else{
    if(disc)return fail(e,"original native disc duplicates source UID");disc=g;
    if(!cached)selected=b;
   }
  }
  if(cached&&disc)shadows.insert(disc); // exact literal validation already passed
  if(current->selectedSession&&disc){
   const auto deadline=current->enemyExpiry.find(entry.first);
   if(deadline==current->enemyExpiry.end())return fail(e,"original selected enemy lacks calendar expiry authority");
   if(deadline->second>=0&&(selected.state.dayLimit<0||deadline->second<selected.state.dayLimit))selected.state.dayLimit=deadline->second;
  }
  bindings.push_back(selected);current->selectedEnemies.emplace(entry.first,originalActors().find(entry.first)->enemy.source);
 }
 // Family reservations observe the same shared pools. Check the aggregate
 // inventory first so individually valid families cannot oversubscribe them.
 unsigned roots=0,pellets=0;
 for(const auto& entry:current->selectedEnemies){
  const auto& r=originalActors().find(entry.first)->enemy;roots+=r.count;
  if(r.source==16)roots+=r.count; // one captured original Egg per Honeywisp
  if(!foliage::supported(r.source)){
   const unsigned cargo=(r.source==0||!corpseDisabled(r.source))?1:0;
   pellets+=r.count*(cargo+(r.pelletProbability>0?std::max(r.pelletMinimum,r.pelletMaximum):0)+(r.treasureCode?1:0));
  }
 }
 if(!tekiMgr||!pelletMgr||tekiMgr->getMax()-tekiMgr->getSize()<int(roots)
  ||pelletMgr->getMax()-pelletMgr->getSize()<int(pellets))return fail(e,"original whole-course native actor/corpse/drop capacity insufficient");
 if(current->onyons){if(!pc_p2_original_onyon_preflight(onyonInventory,e))return false;}
 else if(!onyonInventory.empty())return fail(e,"original source Onyons lack admitted typed manifest");
 if(current->pikis){if(!pc_p2_original_piki_preflight(pikiInventory,e))return false;}
 else if(!pikiInventory.empty())return fail(e,"original source Pikmin lack admitted full atlas/calendar census");
 if(current->gates){if(!pc_p2_original_gate_preflight(gateInventory,e))return false;}
 else if(!gateInventory.empty())return fail(e,"original source gates lack admitted typed manifest");
 if(current->bridges){if(!pc_p2_original_bridge_preflight(bridgeInventory,e))return false;}
 else if(!bridgeInventory.empty())return fail(e,"original source bridges lack admitted typed manifest");
 if(current->barrels){if(!pc_p2_original_barrel_preflight(barrelInventory,e))return false;}
 else if(!barrelInventory.empty())return fail(e,"original source Barrels lack admitted typed manifest");
 if(current->caves){if(!pc_p2_original_cave_preflight(caveInventory,e))return false;}
 else if(!caveInventory.empty())return fail(e,"original source Caves lack admitted typed manifest");
 // Shared Chappy bank is published once with the full source union; later
 // family preflights must not add a missing Fire/Hairy variant to live data.
 std::set<unsigned> chappySources;
 for(const auto& entry:current->selectedEnemies){
  const auto source=entry.second;
  if(source==2||source==33||source==43)chappySources.insert(source);
  if(!pc_p2_original_corpse_resources(source,e))return false;
 }
 if(!chappySources.empty()&&!pc_p2_chappy_prepare_original(chappySources,e))return false;
 if(!pc_p2_original_course_install(bindings,current->dispatch,e,current->selectedSession))return false;
 current->shadows=std::move(shadows);current->started=true;e.clear();return true;
}
bool pc_p2_original_course_finish(std::string& e){
 // Preserve unresolved source HEAD/pending graphs before any provider is
 // disposed. BODY retirement intentionally stays after the Party observer in
 // GameCoreSection::exitStage; this read-only guard must not retire BODYs.
 if(!pc_p2_original_sprout_preflight_course_finish(e))return false;
 if(!current){e.clear();return true;}
 // Refuse before disposing generators, actors or their App-heap resources.
 // A collected receipt cannot replace a pending physical cargo graph.
 if(!pc_p2_campaign_treasure_held_unload(e))return false;
 if(!pc_p2_original_corpse_unload(e))return false;
 if(current->started&&!pc_p2_original_course_unload(e))return false;
 if(current->bridges)pc_p2_original_bridge_before_teardown();
 if(current->barrels)pc_p2_original_barrel_before_teardown();
 if(current->pikis)pc_p2_original_piki_unload();
 current.reset();e.clear();return true;
}
bool pc_p2_original_course_prepared(){return bool(current);}
bool pc_p2_original_course_item_expired(const Generator* g,bool& expired){
 if(!current||!current->selectedSession||!pc_randomizer_original_session()||!g)return false;
 const auto metadata=current->itemMetadata.find(g->_70);if(metadata==current->itemMetadata.end())return false;
 const auto selected=current->itemExpiry.find(g->_70);
 if(selected==current->itemExpiry.end()){std::fprintf(stderr,"P2_ORIGINAL_ITEM_EXPIRY_AUTHORITY_MISSING uid=%u\n",g->_70);std::abort();}
 int deadline=metadata->second.second;
 if(selected->second>=0&&(deadline<0||selected->second<deadline))deadline=selected->second;
 expired=deadline>=0&&std::int64_t(deadline)<std::int64_t(originalProgress().context().day);return true;
}

void pc_p2_original_course_retired(Creature* actor){if(current)current->dispatch.retired(actor);}
bool pc_p2_original_course_shadow(const Generator* g){return current&&current->shadows.count(g);}
bool pc_p2_original_course_load(const char* directory,const char* course,std::function<bool(unsigned)> metColor,std::string& e){
 if(!directory||!*directory||!course||!*course)return fail(e,"original private manifest requires selected surface course");
 const std::string selected=course;
 for(char c:selected)if(!((c>='a'&&c<='z')||c=='_'))return fail(e,"original manifest course path invalid");
 const std::string path=std::string(directory)+"/"+selected+".p2c";
 std::string bytes;
 if(pc_randomizer_original_session()){
  if(!pc_randomizer_original_input("p2-original/"+selected+".p2c",bytes,e))return false;
 }else{
  std::ifstream input(path,std::ios::binary|std::ios::ate);
  if(!input)return fail(e,"selected original course manifest missing");
  const auto size=input.tellg();if(size<=0||size>4*1024*1024)return fail(e,"original private manifest size invalid");
  bytes.assign(size_t(size),'\0');input.seekg(0);
  if(!input.read(bytes.data(),size))return fail(e,"original private manifest read failed");
 }
 SourceManifest manifest;
 if(!readSourceManifest(bytes,selected,manifest,e))return false;
 const bool selectedSession=pc_randomizer_original_session();
 if(selectedSession){
  const char* selectedRoot=pc_randomizer_original_catalog_root();std::error_code status;
  if(!selectedRoot||manifest.fingerprint!=pc_randomizer_original_campaign()
   ||std::filesystem::canonical(directory,status)!=std::filesystem::path(selectedRoot)||status)
   return fail(e,"original manifest differs from verified selected session");
 }
 if(!originalProgress().initialize(manifest.fingerprint,e))return false;
 std::vector<CalendarLoad> plannedLoads;CalendarState sourceFlags;
 if(selectedSession){
  if(!calendarLedger.initialize(manifest.fingerprint,originalProgress().context().day,e)
   ||!calendarLedger.state(selected,sourceFlags,e)
   ||!pc_randomizer_original_calendar_plan(selected,sourceFlags,plannedLoads,e))return false;
 }
 if(!pc_p2_original_incarnation_initialize(manifest.fingerprint,e))return false;
 // P2PK1 is all-calendar authority; P2PA1 names the exact selected native
 // calendar inventory and binds its zero-based source day independently.
 const auto loadBytes=[&](const std::string& path,std::string& out){
  if(selectedSession){const auto name=std::filesystem::path(path).filename().generic_string();return pc_randomizer_original_input("p2-original/"+name,out,e);}
  std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in)return fail(e,"original typed source file missing");
  auto n=in.tellg();if(n<=0||n>4*1024*1024)return fail(e,"original typed source size invalid");
  std::string b(size_t(n),'\0');in.seekg(0);if(!in.read(b.data(),n))return fail(e,"original typed source read failed");out.swap(b);return true;
 };
 p2original::PikiManifest pikiAtlas;std::vector<unsigned> pikiActive;std::map<unsigned,int> pikiExpiry;
 std::error_code pikiStatus;const std::string pikiPath=std::string(directory)+"/campaign.p2pk";
 const bool hasPikis=selectedSession?pc_randomizer_original_has_input("p2-original/campaign.p2pk")
  :std::filesystem::exists(pikiPath,pikiStatus);
 if(pikiStatus)return fail(e,"original Pikmin atlas status failed");
 if(selectedSession&&!hasPikis)return fail(e,"selected original Pikmin atlas missing from immutable Bundle");
 if(hasPikis){std::string b;
  if(!loadBytes(pikiPath,b)||!p2original::readPikiManifest(b,pikiAtlas,e))return false;
  if(pikiAtlas.campaign!=manifest.fingerprint)return fail(e,"original Pikmin atlas selected campaign mismatch");
  if(selectedSession){
   for(const auto& load:plannedLoads)for(const auto& source:load.member->sources)if(source.kind=="piki"){
    auto row=std::find_if(pikiAtlas.rows.begin(),pikiAtlas.rows.end(),[&](const auto& r){return r.spawn.uid==source.uid;});
    if(row==pikiAtlas.rows.end()||row->sourceKey!=selected+"/"+load.member->name+"#"+std::to_string(source.index)||row->sourceSha!=load.member->sha
     ||!pikiExpiry.emplace(source.uid,load.expiry).second)return fail(e,"original active calendar Piki authority mismatch");
    pikiActive.push_back(source.uid);
   }
  }else if(!loadBytes(std::string(directory)+"/"+selected+".p2pa",b)
   ||!p2original::readPikiActive(b,pikiAtlas,selected,originalProgress().context().day,pikiActive,e))return false;
 }
 const std::string onyonPath=std::string(directory)+"/"+selected+".p2on";
 std::error_code statusError;
 const bool hasOnyons=selectedSession?pc_randomizer_original_has_input("p2-original/"+selected+".p2on")
  :std::filesystem::exists(onyonPath,statusError);
 if(statusError)return fail(e,"original typed Onyon manifest status failed");
 std::vector<OnyonRecord> onyons;
 if(hasOnyons){
  if(selectedSession){std::string b;if(!loadBytes(onyonPath,b)||!parseOnyons(b,onyons,e))return false;}
  else if(!readOnyons(onyonPath,onyons,e))return false;
  for(const auto& row:onyons){
   if(row.sourceKey.compare(0,selected.size()+1,selected+"/"))return fail(e,"original Onyon manifest belongs to another course");
   for(const auto& enemy:manifest.rows)if(enemy.enemy.uid==row.uid)return fail(e,"original typed source UID collision");
  }
 }
 std::vector<GateRecord> gates;std::vector<BridgeRecord> bridges;
 std::vector<BarrelRecord> barrels;std::vector<CaveRecord> caves;
 const auto typedFile=[&](const char* suffix,std::string& path,bool& exists){
  path=std::string(directory)+"/"+selected+suffix;std::error_code status;
  // Selection membership survives a later missing/changed physical file.
  // A selected-present sidecar must reach loadBytes and refuse failed reads.
  exists=selectedSession?pc_randomizer_original_has_input("p2-original/"+selected+suffix)
   :std::filesystem::exists(path,status);
  if(status)return fail(e,"original typed item manifest status failed");return true;
 };
 std::string gatePath,bridgePath,barrelPath,cavePath;bool hasGates=false,hasBridges=false,hasBarrels=false,hasCaves=false;
 if(!typedFile(".p2gt",gatePath,hasGates)||!typedFile(".p2br",bridgePath,hasBridges)||!typedFile(".p2ba",barrelPath,hasBarrels)||!typedFile(".p2cv",cavePath,hasCaves))return false;
 if(hasGates){if(selectedSession){std::string b;if(!loadBytes(gatePath,b)||!parseGates(b,gates,e))return false;}else if(!readGates(gatePath,gates,e))return false;}
 if(hasBridges){if(selectedSession){std::string b;if(!loadBytes(bridgePath,b)||!parseBridges(b,bridges,e))return false;}else if(!readBridges(bridgePath,bridges,e))return false;}
 if(hasBarrels){if(selectedSession){std::string b;if(!loadBytes(barrelPath,b)||!parseBarrels(b,barrels,e))return false;}else if(!readBarrels(barrelPath,barrels,e))return false;}
 if(hasCaves){if(selectedSession){std::string b;if(!loadBytes(cavePath,b)||!parseCaves(b,caves,e))return false;}else if(!readCaves(cavePath,caves,e))return false;}
 // The shared UID namespace covers every kind, including inactive Pikmin.
 std::set<unsigned> sourceUids;
 for(const auto& row:manifest.rows)sourceUids.insert(row.enemy.uid);
 for(const auto& row:pikiAtlas.rows)if(!sourceUids.insert(row.spawn.uid).second)return fail(e,"original Pikmin/source UID collision");
 const auto checkItem=[&](const auto& row){
  if(row.sourceKey.compare(0,selected.size()+1,selected+"/")||!sourceUids.insert(row.uid).second)
   return fail(e,"original typed item course or UID collision");return true;
 };
 for(const auto& row:onyons)if(!checkItem(row))return false;
 for(const auto& row:gates)if(!checkItem(row))return false;
 for(const auto& row:bridges)if(!checkItem(row))return false;
 for(const auto& row:barrels)if(!checkItem(row))return false;
 for(const auto& row:caves)if(!checkItem(row))return false;
 // Item manifests retain all-calendar source authority. Install only rows
 // whose exact UID/key/raw-member hash belongs to this selected calendar load.
 if(selectedSession){
  const auto selectItems=[&](auto& rows){
   rows.erase(std::remove_if(rows.begin(),rows.end(),[&](const auto& row){
    for(const auto& load:plannedLoads)for(const auto& source:load.member->sources)
     if(source.uid==row.uid)return false;
    return true;
   }),rows.end());
   for(const auto& row:rows){bool matched=false;
    for(const auto& load:plannedLoads)for(const auto& source:load.member->sources)if(source.uid==row.uid){
     if(source.kind!="item"||row.sourceKey!=selected+"/"+load.member->name+"#"+std::to_string(source.index)||row.sourceSha!=load.member->sha)
      return fail(e,"original active item calendar authority mismatch");
     matched=true;
    }
    if(!matched)return fail(e,"original active item calendar entry missing");
   }
   return true;
  };
  if(!selectItems(onyons)||!selectItems(gates)||!selectItems(bridges)||!selectItems(barrels)||!selectItems(caves))return false;
 }
 if(!pc_p2_original_course_prepare(manifest.fingerprint,manifest.rows,manifest.literal,std::move(metColor),e))return false;
 const auto rollback=[&](){
  // No source body has been born during installation.
  if(current->gates)pc_p2_original_gate_unload();
  if(current->bridges)pc_p2_original_bridge_unload();
  if(current->barrels)pc_p2_original_barrel_unload();
  if(current->caves)pc_p2_original_cave_unload();
  if(current->pikis)pc_p2_original_piki_unload();
  if(current->onyons)pc_p2_original_onyon_unload();current.reset();
 };
 if(hasGates&&!gates.empty()){
  if(!pc_p2_original_gate_install(gates,e)){rollback();return false;}current->gates=true;
 }
 if(hasBridges&&!bridges.empty()){
  if(!pc_p2_original_bridge_install(bridges,e)){rollback();return false;}current->bridges=true;
 }
 if(hasBarrels&&!barrels.empty()){
  if(!pc_p2_original_barrel_install(barrels,e)){rollback();return false;}current->barrels=true;
 }
 if(hasCaves&&!caves.empty()){
  if(!pc_p2_original_cave_install(caves,e)){rollback();return false;}current->caves=true;
 }
 if(hasPikis){
  if(!pc_p2_original_piki_install(pikiAtlas,pikiActive,e,pikiExpiry)){rollback();return false;}
  current->pikis=true;
 }
 if(hasOnyons&&!onyons.empty()){
  auto progress=[](){const auto& s=originalProgress().snapshot();return PcOriginalOnyonProgress{std::uint8_t(s.container&7),std::uint8_t(s.boot&7)};};
  auto boot=[](int species){std::string e;if(!originalProgress().boot(unsigned(species),e)){std::fprintf(stderr,"P2_ORIGINAL_ONYON_BOOT_FAIL %s\n",e.c_str());std::abort();}};
  if(!pc_p2_original_onyon_install(onyons,progress,boot,e)){rollback();return false;}
  current->onyons=true;
 }
 current->selectedSession=selectedSession;current->course=selected;current->plannedLoads=std::move(plannedLoads);
 if(selectedSession)for(const auto& load:current->plannedLoads)for(const auto& source:load.member->sources)if(source.kind=="teki"){
  const auto* row=originalActors().find(source.uid);
  if(!row||row->sourceKey!=selected+"/"+load.member->name+"#"+std::to_string(source.index)
   ||!current->enemyExpiry.emplace(source.uid,load.expiry).second){rollback();return fail(e,"original selected enemy calendar authority mismatch");}
  current->freshEnemies.insert(source.uid);
 }
 if(selectedSession)for(const auto& load:current->plannedLoads)for(const auto& source:load.member->sources)if(source.kind=="item")
  if(!current->itemExpiry.emplace(source.uid,load.expiry).second){rollback();return fail(e,"original selected item calendar duplicated");}
 for(const auto& row:onyons)current->itemMetadata.emplace(row.uid,std::make_pair(unsigned(row.resurrectionDays),row.dayLimit));
 for(const auto& row:gates)current->itemMetadata.emplace(row.uid,std::make_pair(unsigned(row.resurrectionDays),row.dayLimit));
 for(const auto& row:bridges)current->itemMetadata.emplace(row.uid,std::make_pair(unsigned(row.resurrectionDays),row.dayLimit));
 for(const auto& row:barrels)current->itemMetadata.emplace(row.uid,std::make_pair(unsigned(row.resurrectionDays),row.dayLimit));
 for(const auto& row:caves)current->itemMetadata.emplace(row.uid,std::make_pair(unsigned(row.resurrectionDays),row.dayLimit));
 e.clear();return true;
}
bool pc_p2_original_course_use_models(std::string& e){
 if(!current){e.clear();return true;}
 if(!tekiMgr)return fail(e,"original course model admission lacks native manager");
 // Explicit early chassis reservation precedes startStage. Physical preflight
 // later verifies actual bank/corpse/drop resources and manager capacity.
 std::set<unsigned> sources;
 if(current->selectedSession){
  if(!generatorList||!generatorList->mGenListHead)return fail(e,"original model admission lacks selected native inventory");
  for(auto* node=generatorList->mGenListHead->mChild;node;node=node->mNext){auto* g=static_cast<Generator*>(node);if(auto* object=dynamic_cast<GenObjectOriginalEnemy*>(g->mGenObject)){
   const auto* row=originalActors().find(object->mState.uid);if(!row||!current->dispatch.capability(*row,e))return false;sources.insert(row->enemy.source);
  }}
 }else for(const auto& entry:originalActors().rows())sources.insert(entry.second.enemy.source);
 for(unsigned source:sources){int type=-1;
  if(source==0)type=TEKI_Palm;
  else if(foliage::supported(source))type=TEKI_Palm;
  else if(source==1||source==15)type=TEKI_Chappy;
  else if(source==2||source==43)type=TEKI_Swallow;
  else if(source==17)type=TEKI_Frog;
  else if(source==18)type=TEKI_Frow;
  else if(uji::species(source))type=uji::nativeType(source);
  else if(tank::species(source))type=tank::nativeType(source);
  else if(catfish::species(source))type=catfish::nativeType(source);
  else if(bulblax_snagret::species(source))type=bulblax_snagret::nativeType(source);
  else if(hanachirashi::species(source))type=hanachirashi::nativeType(source);
  else if(cannon::species(source))type=cannon::nativeType(source);
  if(type<0)return fail(e,"original source has no early resource owner");
  tekiMgr->mUsingType[type]=true;
 }
 e.clear();return true;
}
bool pc_p2_original_course_boot(const char* directory,const char* course,std::string& e){
 return pc_p2_original_course_load(directory,course,pc_p2_original_progress_met,e);
}
void pc_p2_original_course_day_advanced(){
 const char* catalog=pc_randomizer_original_session()?pc_randomizer_original_catalog_root():std::getenv("PIKMIN_P2_ORIGINAL_CATALOG");
 if(!catalog||!*catalog||!originalProgress().ready()||!originalProgress().context().story)return;
 std::string e;
 if(!originalProgress().nextDay(e)||(pc_randomizer_original_session()&&!calendarLedger.advance(originalProgress().context().day,e))){
  std::fprintf(stderr,"P2_ORIGINAL_DAY_ADVANCE_FAIL %s\n",e.c_str());std::abort();
 }
}

bool pc_p2_original_calendar_encode(std::string& bytes,std::string& e){return calendarLedger.encode(bytes,e);}
bool pc_p2_original_calendar_decode(const std::string& campaign,unsigned day,const std::string& bytes,std::string& e){
 if(current)return fail(e,"original calendar adoption requires unloaded scene");return calendarLedger.decode(campaign,day,bytes,e);
}
bool pc_p2_original_course_loaded(std::string& e){
 if(!current||!current->selectedSession){e.clear();return true;}
 if(!current->started||current->loaded)return fail(e,"original calendar successful-load event outside fresh admitted scene");
 if(!calendarLedger.commit(current->course,current->plannedLoads,e))return false;current->loaded=true;e.clear();return true;
}

bool pc_p2_original_course_read_plan(bool& defaultLoaded,bool& dayLoaded,bool& initLoaded,bool& plantsLoaded,std::string& e){
 if(!current||!current->selectedSession||current->started||!pc_randomizer_original_session())return fail(e,"original native plan read outside selected fresh scene");
 defaultLoaded=dayLoaded=initLoaded=plantsLoaded=false;
 std::set<unsigned> seen;
 for(const auto& load:current->plannedLoads){
  if(!load.member)return fail(e,"original native plan lost immutable member");
  std::string member=load.member->name;
  if(member=="defaultgen.txt")member="default.gen";else if(member=="initgen.txt")member="init.gen";else if(member=="plantsgen.txt")member="plants.gen";
  else{if(member.size()<4||member.substr(member.size()-4)!=".txt")return fail(e,"original native member suffix invalid");member.replace(member.size()-4,4,".gen");}
  const std::string role="p2-original/native/"+current->course+"/"+member;std::string bytes;
  if(!pc_randomizer_original_input(role,bytes,e)||bytes.size()>4*1024*1024||bytes.size()<24)return fail(e,"original selected native stream missing or outside bound");
  // The native legacy reader accepts old versions and updates Navi before
  // checking the object list. Reject malformed selected headers first.
  if(bytes.compare(0,4,"1.0v"))return fail(e,"original native member header version mismatch");
  RamStream header(bytes.data(),int(bytes.size()));header.readInt();
  for(unsigned i=0;i<4;++i)if(!std::isfinite(header.readFloat()))return fail(e,"original native starting transform is nonfinite");
  if(header.readInt()!=int(load.member->sources.size()))return fail(e,"original native member declared count mismatch");
  GeneratorMgr* manager=nullptr;
  switch(load.category){case 0:manager=generatorMgr;break;case 1:manager=plantGeneratorMgr;break;case 2:manager=onceGeneratorMgr;break;case 5:manager=dailyGeneratorMgr;break;
   case 3:case 4:manager=new GeneratorMgr;manager->setName(load.member->name.c_str());limitGeneratorMgr->add(manager);break;
   default:return fail(e,"original native plan category invalid");}
  if(!manager)return fail(e,"original native manager unavailable");
  RamStream input(bytes.data(),int(bytes.size()));manager->read(input,load.category!=0);
  if(input.getPosition()!=int(bytes.size())||manager->originalSourceCount()!=int(load.member->sources.size()))return fail(e,"original native stream changed declared source prefix");
  auto* generator=manager->originalSourceHead();
  for(const auto& source:load.member->sources){
   if(!generator||generator->_70!=source.uid||!seen.insert(source.uid).second||generator->readFromRam()||generator->mGenArea||generator->mGenType)
    return fail(e,"original native source order UID or typed controller mismatch");
   unsigned uid=0;const char* kind=nullptr;
   if(auto* object=dynamic_cast<GenObjectOriginalEnemy*>(generator->mGenObject)){
    uid=object->mState.uid;kind="teki";
    const auto literal=current->literal.find(uid);
    if(literal==current->literal.end()||generator->mCarryOverFlags!=literal->second.reserved)return fail(e,"original native enemy common header mismatch");
   }
   else if(auto* object=dynamic_cast<GenObjectOriginalPiki*>(generator->mGenObject)){uid=object->uid;kind="piki";}
   else if(auto* object=dynamic_cast<GenObjectOriginalOnyon*>(generator->mGenObject)){uid=object->uid;kind="item";}
   else if(auto* object=dynamic_cast<GenObjectOriginalGate*>(generator->mGenObject)){uid=object->uid;kind="item";}
   else if(auto* object=dynamic_cast<GenObjectOriginalBridge*>(generator->mGenObject)){uid=object->uid;kind="item";}
   else if(auto* object=dynamic_cast<GenObjectOriginalBarrel*>(generator->mGenObject)){uid=object->uid;kind="item";}
   else if(auto* object=dynamic_cast<GenObjectOriginalCave*>(generator->mGenObject)){uid=object->uid;kind="item";}
   if(!kind||uid!=source.uid||kind!=source.kind)return fail(e,"original native source kind lacks its actual typed provider");
   if(source.kind=="item"){
    auto metadata=current->itemMetadata.find(uid);if(metadata==current->itemMetadata.end())return fail(e,"original typed item immutable common metadata missing");
    generator->mRespawnInterval=int(metadata->second.first);generator->mDayLimit=metadata->second.second;
   }
   generator=generator->mNextGenerator;
  }
  if(generator)return fail(e,"original native member has extra undeclared source object");
  // Resource-use observations follow complete per-member identity validation;
  // whole-course admission still precedes every physical actor birth.
  manager->updateUseList();
  if(load.category==0)defaultLoaded=true;else if(load.category==1)plantsLoaded=true;else if(load.category==2)initLoaded=true;else if(load.category==5)dayLoaded=true;
 }
 if(!defaultLoaded)return fail(e,"original literal calendar omitted default source member");
 e.clear();return true;
}

p2original::captain::SourceBank* pc_p2_original_captain_source_bank(){return current&&current->captains&&current->captains->ready()?current->captains.get():nullptr;}
