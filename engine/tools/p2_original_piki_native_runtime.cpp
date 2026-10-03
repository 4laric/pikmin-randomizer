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
#include "Generator.h"
#include "pc_p2_original_piki_init.h"
#include "pc_p2_original_piki_native.h"
#include "pc_p2_original_progress.h"
#include "pc_p2_original_group_engine.h"
#include "Stream.h"
#include <fstream>
#include <memory>
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
std::string readFile(const std::string& path){std::ifstream in(path,std::ios::binary|std::ios::ate);require(bool(in),"private source file exists");auto n=in.tellg();require(n>0&&n<4*1024*1024,"private source file bound");std::string b(size_t(n),'\0');in.seekg(0);require(bool(in.read(b.data(),n)),"private source read");return b;}
void run(){
 const char* directory=std::getenv("PIKMIN_P2_PIKI_FIXTURE_FILES");require(directory&&*directory,"explicit private immutable atlas/native streams");std::string root=directory,e;
 p2original::PikiManifest atlas;require(p2original::readPikiManifest(readFile(root+"/campaign.p2pk"),atlas,e),"actual all-calendar P2PK1");require(atlas.rows.size()==28,"all28 immutable source rows retained");
 require(p2original::originalProgress().initialize(atlas.campaign,e),"fixture explicit campaign progression");auto context=p2original::originalProgress().context();context.day=5;require(p2original::originalProgress().restoreContext(context,e),"explicit zero-based diagnostic source day5");
 require(pc_p2_original_incarnation_initialize(atlas.campaign,e),"full atlas incarnation authority");std::vector<unsigned> active;
 require(p2original::readPikiActive(readFile(root+"/tutorial.p2pa"),atlas,"tutorial",5,active,e)&&active.size()==6,"actual six selected Piki sources");
 require(field()==20&&GameStat::mapPikis==20,"native baseline20");auto* ordinary=pikiMgr->birth();require(!ordinary,"ordinary Flarliccap20 retained");
 pc_p2_original_piki_register();
 auto* factory=GenObjectFactory::factory;
 require(factory&&factory->mMaxSpawners>=15&&factory->mSpawnerCount<=factory->mMaxSpawners,"initialized factory capacity includes all legacy and typed kinds");
 for(u32 kind:{0x70696b69u,0x61637472u,0x6974656du,0x6d706172u,0x6e617669u,0x70656c74u,0x706c6e74u,0x776f726bu,0x74656b69u,0x626f7373u,0x6d6f626au,0x64656267u,0x70326f67u,0x70326f6eu,0x70327069u}){
  unsigned matches=0;for(int i=0;i<factory->mSpawnerCount;++i)if(factory->mSpawnerInfo[i].mID==kind)++matches;
  require(matches==1,"every legacy and typed generator kind registered exactly once");
 }
 for(unsigned visit=0;visit<2;++visit){
  require(pc_p2_original_piki_install(atlas,active,e),"install immutable atlas and paired recruitment before native read");
  std::vector<std::unique_ptr<Generator>> owned;std::vector<Generator*> inventory;
  for(const char* member:{"default.gen","init.gen"}){
   auto bytes=readFile(root+"/piki-streams/tutorial/"+member);RamStream input(bytes.data(),int(bytes.size()));
   input.readInt();for(unsigned i=0;i<4;++i)input.readFloat();unsigned count=unsigned(input.readInt());require(count<=6,"actual native stream count");
   for(unsigned i=0;i<count;++i){auto g=std::make_unique<Generator>();g->read(input);require(dynamic_cast<GenObjectOriginalPiki*>(g->mGenObject),"actual native factory produced p2pi OP01");require(!g->mGenArea&&!g->mGenType,"no invented P1 area/type");inventory.push_back(g.get());owned.push_back(std::move(g));}
   require(input.getPosition()==int(bytes.size()),"real Generator reader consumed native source stream exactly");
  }
  require(inventory.size()==6,"complete selected native inventory");auto incomplete=inventory;incomplete.pop_back();PcSimRngCheckpoint before,after;
  require(pc_sim_rng_capture(before,e),"preflight RNG snapshot");require(!pc_p2_original_piki_preflight(incomplete,e),"missing selected row refuses before births");require(pc_sim_rng_capture(after,e),"refusal RNG snapshot");require(before.simDraws==after.simDraws&&field()==20,"failed admission no RNG or births");
  require(pc_p2_original_piki_preflight(inventory,e),"whole typed inventory physical preflight");require(pc_sim_rng_capture(before,e),"before source controller");
  for(auto* g:inventory)g->init();require(pc_sim_rng_capture(after,e),"after source controller");
  require(after.simDraws-before.simDraws==210,"exact105 literal attempts210SIMdraws");require(field()==25&&GameStat::mapPikis==25,"actual20to25 physical source birth");
  std::vector<Piki*> born;Iterator it(pikiMgr);for(it.first();!it.isDone();it.next()){auto* p=static_cast<Piki*>(*it);OriginalPikiBody body;if(!pc_p2_original_piki_body_query(p,body))continue;
   require(body.origin.catalogFingerprint==atlas.catalog&&body.origin.sourceKey=="tutorial/defaultgen.txt#5"&&body.origin.activation==visit+1,"actual canonical full-atlas identity and fresh activation");require(body.state.species==1&&body.state.wild&&body.state.wasWild&&!p->mGenerator,"source wildRed body no nativeGenerator");born.push_back(p);
  }
  require(born.size()==5,"five actual wildRed source bodies");bool handled=false;require(!pc_p2_original_piki_generator_init(inventory[0],handled,e)&&handled,"consumed generator cannot replay");
  for(auto* p:born){p->setEraseKill();p->kill(false);}require(field()==20&&GameStat::mapPikis==20,"owned source retirement restores20");
  pc_p2_original_piki_unload();for(auto& g:owned){delete g->mGenObject;g->mGenObject=nullptr;}
 }
 std::printf("PASS ORIGINAL_GENPIKI_NATIVE checks=%u full_atlas_rows=28 active_rows=6 native_stream=1 visits=2 physical_births=10 sim_draws=420 full_course=0 recruitment_gameplay=0 saved_restore=0\n",checks);std::fflush(nullptr);std::_Exit(0);
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
