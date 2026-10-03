// Actual source GenPiki controller/physical factory seam; not full wild AI admission.
#include "system.h"
#include "App.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "GameStat.h"
#include "AIConstant.h"
#include "ItemMgr.h"
#include "pc_p2_original_piki_init.h"
#include "pc_p2_original_piki_physical.h"
#include "pc_p2_original_source_uid.h"
#include "pc_p2_species.h"
#include <vector>
#include "pc_bbft.h"
#include "pc_randomizer.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_coop.h"
#include "netplay/pc_sim_rng.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <SDL2/SDL.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <limits>
namespace {
unsigned checks=0;
void require(bool condition,const char* name) {
    ++checks;
    if(!condition){std::printf("FAIL ORIGINAL_GENPIKI %s\n",name);std::fflush(nullptr);std::_Exit(1);}
}
int field() {
    int count=0;Iterator it(pikiMgr);
    for(it.first();!it.isDone();it.next())++count;
    return count;
}
struct SourceRecord {const char* key;unsigned count;int species,wild;std::array<float,3> position;};
// Exact six Piki records from actual-original-day5.json, SHA256
// b8a4fb5a39f8371a879eec4ece9025bee75977a4b4394111d5825e6ec79c0bbf.
// The catalog here is a scoped fixture authority, not full seed admission.
const SourceRecord sourceRows[]={
 {"tutorial/defaultgen.txt#5",5,1,1,{{-585.95697f,0.0f,2782.98999f}}},
 {"tutorial/initgen.txt#0",20,1,0,{{-127.273682f,0.999996f,2733.692383f}}},
 {"tutorial/initgen.txt#1",20,0,0,{{-509.160645f,0.999996f,3112.911133f}}},
 {"tutorial/initgen.txt#2",20,2,0,{{-600.782227f,0.999996f,2702.050293f}}},
 {"tutorial/initgen.txt#3",20,3,0,{{-144.240707f,0.0f,3121.715088f}}},
 {"tutorial/initgen.txt#4",20,4,0,{{-144.240707f,0.0f,3121.715088f}}},
};
const std::string sourceFingerprint="b8a4fb5a39f8371a879eec4ece9025bee75977a4b4394111d5825e6ec79c0bbf";
struct PhysicalProvider: p2original::PikiSpawnProvider {
 const SourceRecord* source=nullptr;
 std::vector<Piki*> bodies;
 explicit PhysicalProvider(const SourceRecord& r):source(&r){bodies.reserve(r.count);}
 bool prepare(const p2original::PikiSpawnRecord& r,std::string& error)override {
  if(r.uid!=p2original::originalSourceCatalogUid(source->key)||r.count!=source->count
      ||r.species!=source->species||r.wildParameter!=source->wild){error="fixture source row changed";return false;}
  // All member identities are admitted before this row consumes any RNG or
  // physical slot. Capacity skips do not create a consumed member identity.
  for(unsigned attempt=0;attempt<source->count;++attempt){
   OriginalPikiBody admitted;
   admitted.origin={source->key,p2original::originalSourceCatalogUid(source->key),attempt,1,sourceFingerprint};
   const bool wild=source->wild==1;
   admitted.state={static_cast<std::uint8_t>(source->species),wild,wild};
   if(!pc_p2_original_piki_body_birth_admit(admitted)){error="source member admission failed";return false;}
  }
  return true;
 }
 float randomUnit()override{return gsys->getRand(1.0f);}
 p2original::PikiBirthResult birth(unsigned attempt,const std::array<float,3>& position,bool wild,std::string& e)override {
  OriginalPikiBody original;
  original.origin={source->key,p2original::originalSourceCatalogUid(source->key),attempt,1,sourceFingerprint};
  original.state={static_cast<std::uint8_t>(source->species),wild,wild};
  Piki* body=nullptr;
  const auto result=pc_p2_original_piki_physical_birth(original,position,body,e);
  if(result==p2original::PikiBirthResult::Born){
   require(body&&body->mGenerator==nullptr,"source Piki owns no invented native Generator");
   OriginalPikiBody observed;
   require(pc_p2_original_piki_body_query(body,observed),"actual born canonical body");
   require(observed.origin.attempt==attempt&&observed.origin.sourceKey==source->key
       &&observed.state.species==source->species&&observed.state.wild==wild&&observed.state.wasWild==wild,
       "actual source attempt species/wild provenance");
   require(body->mSRT.t.x==position[0]&&body->mSRT.t.y==position[1]&&body->mSRT.t.z==position[2],
       "authored physical position without floor correction");
   require(pc_p2_species(body)==source->species&&body->mHappa==Leaf&&body->mMode==PikiMode::FreeMode,
       "actual source species Leaf Free");
   bodies.push_back(body);
  }
  return result;
 }
};
void run() {
 auto* manager=pikiMgr;auto* captains=naviMgr;std::string error;
 require(field()==20&&GameStat::mapPikis==20,"actual field and population baseline20");
 const int ordinaryLimit=AICONST.mMaxPikisOnField();
 std::printf("ORIGINAL_GENPIKI_CAPACITY map=%d ordinary_limit=%d queued=%d source_limit=100\n",
     GameStat::mapPikis,ordinaryLimit,itemMgr?itemMgr->getContainerExitCount():0);
 require(ordinaryLimit==20,"actual starting Flarlic ordinary limit20");
 require(pikiMgr->birth()==nullptr,"ordinary birth retains cap20 before source allocation");
 std::vector<OriginalPikiSource> rows;
 for(const auto& row:sourceRows)rows.push_back({row.key,p2original::originalSourceCatalogUid(row.key),row.count,static_cast<std::uint8_t>(row.species)});
 require(pc_p2_original_piki_origin_install(sourceFingerprint,rows,error),"complete six source Piki rows");
 PcSimRngCheckpoint before,after;
 Iterator existing(pikiMgr);existing.first();auto* unchanged=static_cast<Piki*>(*existing);
 OriginalPikiBody admitted;
 admitted.origin={sourceRows[0].key,p2original::originalSourceCatalogUid(sourceRows[0].key),0,1,sourceFingerprint};
 admitted.state={1,true,true};
 const auto refusal=[&](const OriginalPikiBody& input,const std::array<float,3>& position){
  PcSimRngCheckpoint a,b;require(pc_sim_rng_capture(a,error),"actual refusal RNG before");
  Piki* output=unchanged;
  require(pc_p2_original_piki_physical_birth(input,position,output,error)==p2original::PikiBirthResult::Failed,
      "actual physical admission refused");
  require(output==unchanged&&field()==20&&GameStat::mapPikis==20,
      "refusal leaves output and actual population unchanged");
  require(pc_sim_rng_capture(b,error),"actual refusal RNG after");
  require(a.simState==b.simState&&a.cosmeticState==b.cosmeticState&&a.simDraws==b.simDraws&&a.cosmeticDraws==b.cosmeticDraws,
      "refusal before allocation consumes no native RNG");
 };
 auto nonfinite=sourceRows[0].position;nonfinite[0]=std::numeric_limits<float>::infinity();
 refusal(admitted,nonfinite);
 auto foreign=admitted;foreign.origin.catalogFingerprint=std::string(64,'f');refusal(foreign,sourceRows[0].position);
 {PcOriginalPikiInitScope nested(unchanged);require(nested.valid(),"held real native init scope");refusal(admitted,sourceRows[0].position);}
 require(pc_sim_rng_capture(before,error),"actual RNG before original source attempts");
 unsigned attempts=0,blocked=0,born=0;
 std::vector<Piki*> owned;
 for(const auto& row:sourceRows){
  p2original::PikiSpawnRecord record;record.uid=p2original::originalSourceCatalogUid(row.key);
  record.count=row.count;record.species=row.species;record.wildParameter=row.wild;record.position=row.position;
  PhysicalProvider provider(row);p2original::PikiSpawnResult result;
  // Explicit fresh source progress; debug retail-default false. This is not an
  // AP color mask and not a loaded/captured full P2 PlayData authority.
  require(p2original::spawnOriginalPiki(record,{},provider,result,error),"actual source attempt-to-physical provider");
  std::printf("ORIGINAL_GENPIKI_ROW key=%s attempts=%u policy=%u capacity=%u born=%u\n",
      row.key,result.attempts,result.policySkipped,result.capacitySkipped,result.born);
  std::fflush(nullptr);
  attempts+=result.attempts;blocked+=result.policySkipped;born+=result.born;
  owned.insert(owned.end(),provider.bodies.begin(),provider.bodies.end());
 }
 require(pc_sim_rng_capture(after,error),"actual RNG after original source attempts");
 require(attempts==105&&blocked==100&&born==5&&owned.size()==5,"retail source filters five wild Red births");
 require(after.simDraws-before.simDraws==210,"exact original two draws per attempt with no host birth draws");
 require(field()==25&&GameStat::mapPikis==25,"actual wild bodies count in native field capacity");
 require(AICONST.mMaxPikisOnField()==ordinaryLimit,"source birth never mutates ordinary global limit");
 require(pikiMgr->birth()==nullptr,"ordinary birth retains cap20 after five original source births");
 Piki* duplicateOutput=unchanged;PcSimRngCheckpoint duplicateBefore,duplicateAfter;
 require(pc_sim_rng_capture(duplicateBefore,error),"actual live member refusal RNG before");
 require(pc_p2_original_piki_physical_birth(admitted,sourceRows[0].position,duplicateOutput,error)==p2original::PikiBirthResult::Failed,
     "already live source member refused before physical birth");
 require(duplicateOutput==unchanged&&field()==25&&GameStat::mapPikis==25,"duplicate leaves output and actual field unchanged");
 require(pc_sim_rng_capture(duplicateAfter,error),"actual live member refusal RNG after");
 require(duplicateBefore.simState==duplicateAfter.simState&&duplicateBefore.cosmeticState==duplicateAfter.cosmeticState
     &&duplicateBefore.simDraws==duplicateAfter.simDraws&&duplicateBefore.cosmeticDraws==duplicateAfter.cosmeticDraws,
     "duplicate source member consumes no native RNG");
 for(auto* body:owned){
  require(pc_p2_original_piki_body_wild(body),"actual wild source body");
  body->setEraseKill();body->kill(false);
  OriginalPikiBody out;
  require(!pc_p2_original_piki_body_query(body,out),"actual native kill retires original identity before pool reuse");
 }
 require(field()==20&&GameStat::mapPikis==20,"actual owned physical disposal restores population20");
 require(pikiMgr==manager&&naviMgr==captains,"native managers preserved");
 std::printf("PASS ORIGINAL_GENPIKI checks=%u records=6 attempts=105 policy_skipped=100 physical_births=5 wild_red=5 sim_draws=210 admission_refusals=4 catalog_fixture=1 full_course=0 discovery=0 saved_restore=0\n",checks);
 std::fflush(nullptr);std::_Exit(0);
}
class TestApp:public PlugPikiApp {
    std::chrono::steady_clock::time_point began=std::chrono::steady_clock::now();
public:int idle()override {
    require(std::chrono::steady_clock::now()-began<std::chrono::seconds(55),"bounded actual startup");
    int result=PlugPikiApp::idle();
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_randomizer_ready()||!pikiMgr||!naviMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    auto* captain=naviMgr->getActiveNavi();
    if(!captain||!captain->getCurrState()||captain->getCurrState()->getID()!=NAVISTATE_Walk)return result;
    require(!GameStat::orimaDead&&captain->mHealth>1,"live captain");
    if(field()!=20)return result;
    std::printf("ORIGINAL_GENPIKI_BASELINE pikmin=20 window=960x540\n");std::fflush(nullptr);
    run();return result;
}
};
}
int main(int argc,char** argv) {
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();
    pc_sim_rng_note_main_thread();std::string error;
    require(pc_sim_rng_begin_offline(0x148,0x248,error),"actual offline RNG profile");
    pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_randomizer_enabled(),"real generated assets required");
    if(!pc_window_init("Original GenPiki physical source fixture",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    int width=0,height=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&width,&height);
    require(width==960&&height==540,"actual centered960 startup");
    pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}
