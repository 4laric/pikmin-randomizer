// Source-bound physical controls with explicitly injected work/death inputs.
// Direct creature doSave/typed-load controls are not full GeneratorCache proof.
#include "system.h"
#include "sysNew.h"
#include "App.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "PikiMgr.h"
#include "ItemMgr.h"
#include "BuildingItem.h"
#include "CreatureNode.h"
#include "GameStat.h"
#include "GameCoreSection.h"
#include "UpdateMgr.h"
#include "Generator.h"
#include "Stream.h"
#include "Interactions.h"
#include "PikiAI.h"
#include "pc_p2_original_barrel_native.h"
#include "pc_p2_surface_water.h"
#include "pc_p2_surface_water_drain.h"
#include "p2_fixture_captain_guard.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_randomizer.h"
#include "pc_coop.h"
#include "netplay/pc_sim_rng.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <SDL2/SDL.h>
#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <limits>

namespace {
using namespace p2original;
const char* barrelPath=nullptr;const char* waterPath=nullptr;bool forceDown=false;
unsigned checks=0;
const std::string waterSha="f87b0f012eeac4918acb5e1a64ae315fe6a2e3b3434f3e163fe72b17619548f3";
void require(bool good,const char* why){++checks;if(!good){std::printf("FAIL ORIGINAL_BARREL %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool good,const std::string& error){if(!good)std::fprintf(stderr,"ORIGINAL_BARREL_ERROR %s\n",error.c_str());require(good,"typed adapter operation");}
BarrelState state(Creature* c){BarrelState s;std::string id;require(pc_p2_original_barrel_snapshot(c,s,id),"physical or retired carrier snapshot");return s;}
bool sameWater(const p2water::DrainSnapshot& a,const p2water::DrainSnapshot& b){
 if(a.course!=b.course||a.sourceSha!=b.sourceSha||a.boxes.size()!=b.boxes.size())return false;
 for(size_t i=0;i<a.boxes.size();++i){const auto& x=a.boxes[i];const auto& y=b.boxes[i];if(x.id!=y.id||x.phase!=y.phase||x.lowered!=y.lowered||x.goal!=y.goal||x.timer!=y.timer)return false;}return true;
}
p2water::DrainSnapshot water(){p2water::DrainSnapshot s;require(pc_p2_surface_water_snapshot(s),"public source water snapshot");return s;}
struct WorkProbe:ActBreakWall {
 explicit WorkProbe(Piki* p):ActBreakWall(p){}
 void work(BuildingItem* b){mWall=b;mWorkTimer=0;mStartAttackTime=gameflow.mWorldClock.mCurrentGameMinute;mIsAttackReady=true;mFailAttackCounter=0;breakWall();}
};
// Own the constructor's private heap and stage entries; never install this
// object as the global cache. This only proves the creature-write segment.
struct CacheProbe:GeneratorCache {
 CacheProbe(){initGame();}
 ~CacheProbe(){
  for(auto* list:{&mAliveCacheList,&mDeadCacheList})while(list->mChild){auto* entry=static_cast<Cache*>(list->mChild);entry->del();delete entry;}
  delete[] mCacheHeap;mCacheHeap=nullptr;
 }
 void verifyRetired(Generator* g,const std::array<unsigned char,112>& expected){
  require(g->mCarryOverFlags==3&&!Generator::ramMode,"literal flags3 and ordinary stream mode before isolated cache control");
  auto* originalGlobal=generatorCache;int originalIndex=g->mGeneratorListIdx;
  std::array<unsigned char,112> direct{};RamStream raw(direct.data(),int(direct.size()));g->saveCreature(raw);
  require(raw.getPosition()==112&&direct==expected,"Generator saveCreature flags3 emits exactly112 without XYZ prefix");
  g->mGeneratorListIdx=7;beginSave(STAGE_Practice);saveGeneratorCreature(g);endSave();g->mGeneratorListIdx=originalIndex;
  auto* entry=findCache(mAliveCacheList,STAGE_Practice);
  require(entry&&mUsedSize==116&&mFreeSize==mTotalCacheSize-116&&entry->mCacheHeapOffset==0&&entry->mTotalCacheSize==116&&entry->mCreatureCacheSize==116&&entry->mCreatureCount==1&&entry->mGenCacheSize==0&&entry->mGenCount==0,"isolated cache retains one index4 plus retired112 segment");
  RamStream segment(mCacheHeap,mUsedSize);require(segment.readInt()==7&&std::memcmp(mCacheHeap+4,expected.data(),112)==0,"isolated cache index and retired bytes exact");
  std::array<unsigned char,36> metadata{};RamStream card(metadata.data(),int(metadata.size()));entry->saveCard(card);
  require(card.getPosition()==36,"cache entry card metadata remains nine native ints");RamStream fields(metadata.data(),int(metadata.size()));
  const int values[]={STAGE_Practice,0,116,0,116,0,0,1,0};for(int value:values)require(fields.readInt()==value,"isolated cache card metadata matches creature segment");
  require(!Generator::ramMode&&generatorCache==originalGlobal&&g->mGeneratorListIdx==originalIndex,"cache control restores stream mode/index and preserves global cache");
 }
};
void run(){
 // idle() enters without an allocation heap; all fixture objects/preflight
 // resources belong to the private App heap. This process ends with _Exit.
 gsys->setHeap(SYSHEAP_App);
 std::string e;std::ifstream input(waterPath);std::vector<p2water::Box> boxes;
 require(p2water::read(input,boxes,"tutorial")&&boxes.size()==3,"exact tutorial immutable water manifest");
 auto wrongBounds=boxes;wrongBounds[0].min[0]-=1;
 require(!pc_p2_surface_water_bind_original("tutorial",waterSha,wrongBounds),"source bound mismatch rejected before admission");
 require(!pc_p2_surface_water_bind_original("tutorial",std::string(64,'0'),boxes),"wrong raw source SHA rejected");
 require(pc_p2_surface_water_bind_original("tutorial",waterSha,boxes),"explicit fixture water authority accepted");
 auto initialWater=water();
 auto atomicReject=[&](const p2water::DrainSnapshot& bad){auto before=water();require(!pc_p2_surface_water_restore(bad),"invalid public water restore rejected");require(sameWater(before,water()),"failed whole restore leaves water unchanged");};
 auto bad=initialWater;bad.course="forest";atomicReject(bad);bad=initialWater;bad.sourceSha=std::string(64,'0');atomicReject(bad);
 bad=initialWater;p2water::startDrain(bad.boxes.front());bad.boxes.back().timer=std::numeric_limits<float>::quiet_NaN();atomicReject(bad);
 bad=initialWater;bad.boxes.back().id=-1;atomicReject(bad);
 pc_p2_original_barrel_register();std::vector<BarrelRecord> rows;checked(readBarrels(barrelPath,rows,e),e);require(!rows.empty()&&rows.size()<=16,"bounded literal tutorial barrel inventory");checked(pc_p2_original_barrel_install(rows,e),e);
 std::vector<std::unique_ptr<Generator>> generators;std::vector<std::unique_ptr<GenObjectOriginalBarrel>> objects;std::vector<Generator*> inventory;
 for(const auto& r:rows){auto g=std::make_unique<Generator>();auto* product=GenObjectFactory::getProduct(0x70326261u);auto o=std::unique_ptr<GenObjectOriginalBarrel>(dynamic_cast<GenObjectOriginalBarrel*>(product));require(o&&o->getLatestVersion()==0x42413031u,"actual p2ba BA01 factory");o->uid=r.uid;g->mGenObject=o.get();g->mGenType=nullptr;g->mCarryOverFlags=r.reserved;g->mRespawnInterval=r.resurrectionDays;g->mDayLimit=r.dayLimit;inventory.push_back(g.get());objects.push_back(std::move(o));generators.push_back(std::move(g));}
 auto missing=inventory;missing.pop_back();require(!pc_p2_original_barrel_preflight(missing,e),"full inventory preflight rejects omission");checked(pc_p2_original_barrel_preflight(inventory,e),e);
 int baseline=itemMgr->mMeltingPotMgr->getSize();require(searchUpdateMgr,"actual search manager present");int baselineSearch=searchUpdateMgr->mClientTotal;
 for(auto* g:inventory){bool handled=false;checked(pc_p2_original_barrel_generator_init(g,handled,e),e);require(handled,"typed physical init handled");}
 require(itemMgr->mMeltingPotMgr->getSize()==baseline+int(rows.size()),"all source physical nodes adopted");
 Iterator workers(pikiMgr);workers.first();require(!workers.isDone(),"real initialized worker available");auto* worker=static_cast<Piki*>(*workers);auto* captain=naviMgr->getNavi();
 std::vector<std::array<unsigned char,112>> retired(rows.size()),pendingBytes(rows.size());std::vector<int> savedDay(rows.size()),sourceBoxes(rows.size());
 for(size_t i=0;i<rows.size();++i){auto* g=inventory[i];auto* b=dynamic_cast<BuildingItem*>(g->mLatestSpawnCreature);require(b&&pc_p2_original_barrel_owned(b)&&b->mGenerator==g,"physical source barrel birth");require(state(b).health==4000&&b->getBoundingSphereRadius()==43,"literal source life and work sphere");
  auto before=state(b);InteractAttack naviHit(captain,nullptr,5000,false);require(!b->stimulate(naviHit)&&state(b).health==before.health,"captain rejected as source work actor");
  WorkProbe probe(worker);probe.work(b);require(state(b).health==4000-pc_p2_original_barrel_work_damage(worker),"actual ActBreakWall raw work hook once (assigned control)");
  InteractAttack zero(worker,nullptr,state(b).health,false);require(b->stimulate(zero)&&state(b).health==0&&state(b).phase==BarrelPhase::Normal,"injected exact zero stays normal");
  InteractAttack negative(worker,nullptr,10,false);require(b->stimulate(negative)&&state(b).phase==BarrelPhase::Dying,"injected strict-negative starts authored death");
  int sourceBox=pc_p2_surface_water_box(b->mSRT.t,43);require(sourceBox>=0,"retail radius43 barrel intersects source water");sourceBoxes[i]=sourceBox;
  itemMgr->update();auto pending=state(b);require(pending.animationFrame>0&&pending.animationFrame<70,"actual ItemMgr update advances pending source animation");
  auto& bytes=pendingBytes[i];RamStream save(bytes.data(),int(bytes.size()));b->doSave(save);require(save.getPosition()==112,"direct pending creature cache112 bytes");int oldDay=g->mLatestSpawnDay;
  // Explicit fixture transport: remove old physical node without source death.
  b->mGenerator=nullptr;b->kill(false);g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;require(g->mLatestSpawnDay==oldDay,"fixture transport does not replay calendar death");
  RamStream load(bytes.data(),int(bytes.size()));bool handled=false;checked(pc_p2_original_barrel_generator_load(g,load,handled,e),e);b=dynamic_cast<BuildingItem*>(g->mLatestSpawnCreature);require(handled&&b&&state(b).animationFrame==pending.animationFrame&&pc_p2_original_barrel_owned(b),"fresh physical pending cache resumes exact frame");
  int priorSize=itemMgr->mMeltingPotMgr->getSize();int ticks=0;while(pc_p2_original_barrel_owned(b)&&ticks++<10000)itemMgr->update();require(ticks<10000,"bounded actual manager authored-death control");require(!pc_p2_original_barrel_owned(b)&&itemMgr->mMeltingPotMgr->getSize()==priorSize-1,"post iteration physical retirement removes exactly owned node");
  require(g->mLatestSpawnCreature==b&&g->mAliveCount==0&&state(b).phase==BarrelPhase::Retired,"retired unlinked typed cache carrier retained");
  auto lowering=water();require(lowering.boxes[size_t(sourceBox)].phase==p2water::Phase::Lowering,"authored clip end requests original water lowering");
  auto deadDay=g->mLatestSpawnDay;itemMgr->update();require(g->mLatestSpawnDay==deadDay,"retirement death bookkeeping occurs once");savedDay[i]=deadDay;
  RamStream carrierSave(retired[i].data(),int(retired[i].size()));b->doSave(carrierSave);require(carrierSave.getPosition()==112,"direct retired carrier cache112 bytes");
  {CacheProbe isolated;isolated.verifyRetired(g,retired[i]);} // Explicitly frees private heap and every cache entry.
  pc_p2_surface_water_update(0.25f);auto drainPending=water();require(pc_p2_surface_water_restore(drainPending)&&sameWater(drainPending,water()),"public pending water restore retains exact timer and lowering");
  for(int tick=0;tick<100&&water().boxes[size_t(sourceBox)].phase!=p2water::Phase::Dead;++tick)pc_p2_surface_water_update(0.25f);
  require(water().boxes[size_t(sourceBox)].phase==p2water::Phase::Dead,"bounded drain reaches source dead state");
  Vector3f deep((boxes[size_t(sourceBox)].min[0]+boxes[size_t(sourceBox)].max[0])*0.5f,-10000,(boxes[size_t(sourceBox)].min[2]+boxes[size_t(sourceBox)].max[2])*0.5f);
  require(pc_p2_surface_water_box(deep,0)!=sourceBox,"dead source box excluded from deep query");require(pc_p2_surface_water_restore(initialWater),"restore initial fixture water for next isolated control");
 }
 // Cache bytes above are complete before explicit stage teardown composition.
 pc_p2_original_barrel_before_teardown();require(searchUpdateMgr->mClientTotal==baselineSearch,"owned search clients released before manager reset");require(itemMgr->mMeltingPotMgr->getSize()==baseline,"owned physical teardown preserves unrelated item nodes");
 for(size_t i=0;i<rows.size();++i){auto* g=inventory[i];require(!g->mLatestSpawnCreature,"teardown clears retired generator carrier reference");int day=g->mLatestSpawnDay;RamStream load(retired[i].data(),int(retired[i].size()));bool handled=false;checked(pc_p2_original_barrel_generator_load(g,load,handled,e),e);require(handled&&g->mLatestSpawnCreature&&state(g->mLatestSpawnCreature).phase==BarrelPhase::Retired&&g->mAliveCount==0,"cold retired cache restores carrier");require(itemMgr->mMeltingPotMgr->getSize()==baseline&&!pc_p2_original_barrel_owned(g->mLatestSpawnCreature)&&searchUpdateMgr->mClientTotal==baselineSearch,"cold retired restore creates no physical node or search client");require(g->mLatestSpawnDay==day&&day==savedDay[i],"cold retired restore preserves calendar counter");require(water().boxes[size_t(sourceBoxes[i])].phase==p2water::Phase::Lowering,"cold retired cache requests its actual source water box");}
 pc_p2_original_barrel_before_teardown();
 // Replay previously serialized pending bytes to exercise dying-node teardown.
 auto* pendingGenerator=inventory.front();int calendar=pendingGenerator->mLatestSpawnDay;RamStream replay(pendingBytes.front().data(),112);bool handled=false;checked(pc_p2_original_barrel_generator_load(pendingGenerator,replay,handled,e),e);require(handled&&pc_p2_original_barrel_owned(pendingGenerator->mLatestSpawnCreature)&&!pendingGenerator->mLatestSpawnCreature->isAlive(),"pending replay creates actual dying physical node");require(itemMgr->mMeltingPotMgr->getSize()==baseline+1,"dying replay adopts one node");pc_p2_original_barrel_before_teardown();require(itemMgr->mMeltingPotMgr->getSize()==baseline&&!pendingGenerator->mLatestSpawnCreature&&pendingGenerator->mLatestSpawnDay==calendar,"explicit dying teardown unlinks without replaying calendar death");
 auto allocationBefore=piki_pc_allocation_stats();pc_p2_original_barrel_unload();auto allocationAfter=piki_pc_allocation_stats();require(allocationAfter.unknownFrees==allocationBefore.unknownFrees&&allocationAfter.liveBlocks<allocationBefore.liveBlocks,"owned concrete allocations released with matching PC allocator");for(auto& g:generators)g->mGenObject=nullptr;
 std::printf("PASS ORIGINAL_BARREL_NATIVE checks=%u physical_factory=1 assigned_work_hook=1 injected_damage=1 manager_animation=1 direct_creature_cache=1 isolated_generator_cache_creature_write=1 full_generator_cache=0 water_restore_controls=1 natural_gameplay=0\n",checks);std::fflush(nullptr);std::_Exit(0);
}
class TestApp:public PlugPikiApp {
 std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();bool seen=false;
public:int idle()override{
 require(std::chrono::steady_clock::now()-start<std::chrono::seconds(55),"bounded guarded startup");int result=PlugPikiApp::idle();auto* captain=naviMgr?naviMgr->getNavi():nullptr;require(!seen||captain,"captain remains present");
 if(captain&&captain->getCurrState()){seen=true;if(forceDown)p2_fixture_require_captain(false,false,0,0);p2_fixture_require_captain(GameStat::orimaDead,captain->getCurrState()->getID()==NAVISTATE_Dead,captain->mHealth,0);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 const char* course=pc_pikipelago_surface_course();if(!course||std::strcmp(course,"tutorial")||!pc_p2_surface_water_active()||!captain||!pikiMgr||!itemMgr||!itemMgr->mMeltingPotMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive||GameCoreSection::inPause())return result;
 int count=0;Iterator it(pikiMgr);for(it.first();!it.isDone();it.next())++count;if(count!=20)return result;require(std::isfinite(gsys->getFrameTime())&&gsys->getFrameTime()>0&&gsys->getFrameTime()<0.1f,"bounded actual manager animation delta");std::puts("ORIGINAL_BARREL_BASELINE pikmin=20 window=960x540 fixture_water_authority=1");run();return result;
 }
};
}
int main(int argc,char** argv){
 for(int i=1;i<argc;++i){if(!std::strncmp(argv[i],"--barrel-manifest=",18))barrelPath=argv[i]+18;else if(!std::strncmp(argv[i],"--water-manifest=",17))waterPath=argv[i]+17;else if(!std::strcmp(argv[i],"--force-captain-down"))forceDown=true;}
 require(barrelPath&&waterPath&&std::strcmp(barrelPath,waterPath),"distinct literal barrel/water manifests supplied");SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_sim_rng_note_main_thread();std::string e;checked(pc_sim_rng_begin_offline(0x1262,0x2262,e),e);pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_pikipelago_surface_course()!=nullptr,"real selected tutorial assets");if(!pc_window_init("Original source barrel controls",960,540))return 3;pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();int w=0,h=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&w,&h);require(w==960&&h==540,"960x540 centered startup");pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}
