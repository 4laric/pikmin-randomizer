// Actual source-bound physical factory, collision/work hook and cache controls.
// Work assignment/state injection is labeled; this is not full-course gameplay.
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
#include "GameStat.h"
#include "Generator.h"
#include "Stream.h"
#include "WorkObject.h"
#include "DynColl.h"
#include "MapMgr.h"
#include "pc_p2_original_bridge_native.h"
#include "Interactions.h"
#include "PikiAI.h"
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
#include <memory>
namespace {
using namespace p2original;
unsigned checks=0;const char* manifestPath=nullptr;bool forceDown=false;
void require(bool good,const char* why){++checks;if(!good){std::printf("FAIL ORIGINAL_BRIDGE %s\n",why);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool good,const std::string& e){if(!good)std::fprintf(stderr,"ORIGINAL_BRIDGE_ERROR %s\n",e.c_str());require(good,"native source adapter operation");}
struct WorkProbe:ActBridge {explicit WorkProbe(Piki* p):ActBridge(p){}void work(Bridge* b,int stage){mBridge=b;mStageID=stage;doWork(1);}};
void run(){
 // idle runs outside a heap; fixture allocation/preflight uses the stage App heap.
 gsys->setHeap(SYSHEAP_App);
 pc_p2_original_bridge_register();std::string e;std::vector<BridgeRecord> rows;checked(readBridges(manifestPath,rows,e),e);require(rows.size()==2,"literal day5 bridge rows long and sloped");checked(pc_p2_original_bridge_install(rows,e),e);
 std::vector<std::unique_ptr<Generator>> owned;std::vector<std::unique_ptr<GenObjectOriginalBridge>> objects;std::vector<Generator*> inventory;
 for(const auto& r:rows){auto g=std::make_unique<Generator>();auto* product=GenObjectFactory::getProduct(0x70326272u);auto o=std::unique_ptr<GenObjectOriginalBridge>(dynamic_cast<GenObjectOriginalBridge*>(product));require(o&&o->getLatestVersion()==0x42523031u,"real typed factory");o->uid=r.uid;g->mGenObject=o.get();g->mGenType=nullptr;g->mCarryOverFlags=r.reserved;g->mRespawnInterval=r.resurrectionDays;g->mDayLimit=r.dayLimit;inventory.push_back(g.get());objects.push_back(std::move(o));owned.push_back(std::move(g));}
 auto incomplete=inventory;incomplete.pop_back();require(!pc_p2_original_bridge_preflight(incomplete,e),"whole inventory preflight rejects omissions");checked(pc_p2_original_bridge_preflight(inventory,e),e);
 int nodeBaseline=workObjectMgr->getSize();
 for(auto* g:inventory){bool handled=false;checked(pc_p2_original_bridge_generator_init(g,handled,e),e);require(handled,"typed init handled");}
 auto links=pc_p2_original_bridge_links();require(links.size()==rows.size(),"all actual source links");for(unsigned i=0;i<rows.size();++i)require(links[i].identity==rows[i].sourceSha+":"+rows[i].sourceKey&&links[i].stage==0,"actual birth order initial stage");
 auto snapshot=[&](Bridge* b){BridgeState s;std::string id;require(pc_p2_original_bridge_snapshot(b,s,id),"physical snapshot");return s;};
 Iterator workers(pikiMgr);workers.first();auto* worker=static_cast<Piki*>(*workers);require(worker!=nullptr,"real initialized Pikmin worker");
 for(unsigned i=0;i<rows.size();++i){const auto& r=rows[i];auto* g=inventory[i];auto* b=dynamic_cast<Bridge*>(g->mLatestSpawnCreature);require(b&&b->mStageCount==bridgeStageCount(r.type)&&b->mGenerator==g,"actual bridge/source binding and topology");require(b->mBuildShape->mCollGroupCount==b->mStageCount*2+1,"retail collision groups including final");require(!b->mStartWaypoint->mIsOpen&&!b->mEndWaypoint->mIsOpen,"unfinished routes closed");
  WorkProbe work(worker);work.work(b,0);require(snapshot(b).health[0]==r.stageLife-pc_p2_original_bridge_work_damage(worker),"actual ActBridge work uses raw source damage once");
  InteractBuild injected(worker,0,r.stageLife);require(b->stimulate(injected),"explicit injected pending stage for cache control");require(snapshot(b).extensionTicks==40&&snapshot(b).stage==0,"retail forty tick extension pending");for(int tick=0;tick<17;++tick)b->update();auto pending=snapshot(b);require(pending.extensionTicks==23,"actual bridge update countdown");
  std::array<unsigned char,168> bytes{};RamStream output(bytes.data(),int(bytes.size()));b->doSave(output);require(output.getPosition()==168,"actual typed doSave");int size=workObjectMgr->getSize();auto* old=b;b->kill(false);require(workObjectMgr->getSize()==size-1&&!pc_p2_original_bridge_owned(old),"physical node/collision/identity retired");g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;
  RamStream input(bytes.data(),int(bytes.size()));bool handled=false;checked(pc_p2_original_bridge_generator_load(g,input,handled,e),e);b=dynamic_cast<Bridge*>(g->mLatestSpawnCreature);require(handled&&b&&snapshot(b).extensionTicks==23,"actual fresh physical cache restore pending extension");for(int tick=0;tick<22;++tick)b->update();require(snapshot(b).stage==0,"extension did not finish early");b->update();require(snapshot(b).stage==1&&b->isStageFinished(0),"actual stage collision switches once");
  auto actual=pc_p2_original_bridge_links();require(actual.back().identity==r.sourceSha+":"+r.sourceKey&&actual.back().stage==1,"recreated bridge moves to physical birth order end");
  for(int stage=1;stage<b->mStageCount;++stage){InteractBuild hit(worker,stage,r.stageLife);require(b->stimulate(hit),"explicit injected completion control");for(int tick=0;tick<40;++tick)b->update();}
  require(b->isFinished()&&!b->isAlive()&&b->mStartWaypoint->mIsOpen&&b->mEndWaypoint->mIsOpen,"physical completed routes open");require(!(b->mStartWaypoint->mFlags&WayPointFlags::InWater)&&!(b->mEndWaypoint->mFlags&WayPointFlags::InWater),"completed routes permit nonBlue crossing");require(b->getFirstUnfinishedStage()==-1&&b->isStageFinished(b->mStageCount-1),"worker completion independent of disabled segment collision");require(b->mBuildShape->mJointVisibility[2],"retail final collision active");RamStream saved(bytes.data(),int(bytes.size()));b->doSave(saved);b->kill(false);g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;RamStream replay(bytes.data(),int(bytes.size()));checked(pc_p2_original_bridge_generator_load(g,replay,handled,e),e);b=dynamic_cast<Bridge*>(g->mLatestSpawnCreature);require(b&&b->isFinished()&&b->mBuildShape->mJointVisibility[2],"completed geometry persists across actual recreation");
 }
 // All completed bodies remain physical despite isAlive()==false. Course
 // creature bytes have already been saved above; teardown runs before reset.
 std::vector<int> completedDays;for(auto* g:inventory)completedDays.push_back(g->mLatestSpawnDay);
 require(workObjectMgr->getSize()==nodeBaseline+int(rows.size()),"completed physical nodes retained until explicit teardown");
 pc_p2_original_bridge_before_teardown();require(workObjectMgr->getSize()==nodeBaseline&&pc_p2_original_bridge_links().empty(),"completed teardown unlinks all owned nodes and preserves unrelated nodes");
 for(size_t i=0;i<inventory.size();++i)require(!inventory[i]->mLatestSpawnCreature&&inventory[i]->mLatestSpawnDay==completedDays[i],"completed teardown clears latest pointer without calendar death replay");
 auto* living=inventory.front();int livingDay=living->mLatestSpawnDay;bool handled=false;checked(pc_p2_original_bridge_generator_init(living,handled,e),e);
 require(handled&&living->mLatestSpawnCreature&&living->mLatestSpawnCreature->isAlive()&&workObjectMgr->getSize()==nodeBaseline+1,"teardown control creates one actual living bridge");
 std::array<unsigned char,168> livingBytes{};RamStream livingSave(livingBytes.data(),int(livingBytes.size()));living->mLatestSpawnCreature->doSave(livingSave);require(livingSave.getPosition()==168,"living course bytes saved before teardown");
 pc_p2_original_bridge_before_teardown();require(workObjectMgr->getSize()==nodeBaseline&&!living->mLatestSpawnCreature&&living->mLatestSpawnDay==livingDay,"living teardown detaches node and preserves calendar");
 pc_p2_original_bridge_before_teardown();auto allocationBefore=piki_pc_allocation_stats();pc_p2_original_bridge_unload();auto allocationAfter=piki_pc_allocation_stats();
 require(allocationAfter.unknownFrees==allocationBefore.unknownFrees&&allocationAfter.liveBlocks<allocationBefore.liveBlocks,"owned concrete bridge allocations released through matching PC allocator");for(auto& g:owned)g->mGenObject=nullptr;
 std::printf("PASS ORIGINAL_BRIDGE_NATIVE checks=%u physical_factory=1 retail_geometry=1 actual_work_hook=1 physical_cache=1 injected_completion=1 natural_gameplay=0\n",checks);std::fflush(nullptr);std::_Exit(0);
}
class TestApp:public PlugPikiApp {
 std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();bool captainSeen=false;
public:int idle()override{
 require(std::chrono::steady_clock::now()-start<std::chrono::seconds(55),"bounded fixture startup");int result=PlugPikiApp::idle();auto* guarded=naviMgr?naviMgr->getNavi():nullptr;require(!captainSeen||guarded,"captain did not disappear");
 if(guarded&&guarded->getCurrState()){captainSeen=true;if(forceDown)p2_fixture_require_captain(false,false,0,0);p2_fixture_require_captain(GameStat::orimaDead,guarded->getCurrState()->getID()==NAVISTATE_Dead,guarded->mHealth,0);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 const bool surface=pc_pikipelago_surface_course()!=nullptr;
 if((!surface&&!pc_randomizer_ready())||!guarded||!pikiMgr||!itemMgr||!workObjectMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 int count=0;Iterator it(pikiMgr);for(it.first();!it.isDone();it.next())++count;if(count!=20)return result;std::puts("ORIGINAL_BRIDGE_BASELINE pikmin=20 window=960x540");run();return result;
 }
};
}
int main(int argc,char** argv){
 for(int i=1;i<argc;++i){if(!std::strncmp(argv[i],"--bridge-manifest=",18))manifestPath=argv[i]+18;else if(!std::strcmp(argv[i],"--force-captain-down"))forceDown=true;}
 require(manifestPath,"literal source bridge manifest supplied");SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_sim_rng_note_main_thread();std::string e;checked(pc_sim_rng_begin_offline(0x148,0x248,e),e);pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_randomizer_enabled()||pc_pikipelago_surface_course()!=nullptr,"selected generated fixture or authored surface assets");if(!pc_window_init("Original source bridge factory fixture",960,540))return 3;pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();int w=0,h=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&w,&h);require(w==960&&h==540,"centered 960x540");pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}

