// Real native GenItem/Onyon factory fixture on literal five-row authority.
// P1 landing nodes are detached only inside this stopped-engine fixture.
// No synthetic transform, gameplay, retail model, or campaign save claim.
#include "system.h"
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
#include "pc_p2_original_onyon_native.h"
#include "GoalItem.h"
#include "UfoItem.h"
#include "p2_fixture_captain_guard.h"
#include "pc_p2_original_group_engine.h"
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
unsigned checks=0;const char* negative=nullptr;
void require(bool b,const char* s){++checks;if(!b){std::printf("FAIL ORIGINAL_GEN_OBJECT %s\n",s);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool b,const std::string& e){if(!b)std::fprintf(stderr,"ORIGINAL_GEN_OBJECT_ERROR %s\n",e.c_str());require(b,"native source adapter operation");}

const char* manifestPath=nullptr;bool wildOnly=false,discoveredOnly=false,forceDown=false;
void run(){
 std::string e;std::vector<OnyonRecord> rows;checked(readOnyons(manifestPath,rows,e),e);
 require(rows.size()==5,"actual original tutorial five item rows");
 // Native fixture infrastructure only: unhook its owned baseline nodes without
 // deleting game objects. The engine does not step until verification completes.
 auto* list=&itemMgr->getMeltingPotMgr()->mRootNode;
 std::vector<CoreNode*> detached;
 for(auto* node=list->mChild;node;){auto* next=node->mNext;auto* c=static_cast<CreatureNode*>(node)->mCreature;
  if(c&&(c->mObjType==OBJTYPE_Goal||c->mObjType==OBJTYPE_Ufo)){detached.push_back(node);node->del();}node=next;
 }
 require(!itemMgr->getContainer(Red)&&!itemMgr->getUfo(),"fixture landing nodes detached without deleting infrastructure");
 PcOriginalOnyonProgress state;state.containers=wildOnly?0:7;state.boot=(wildOnly||discoveredOnly)?0:7;unsigned bootEvents=0;
 checked(pc_p2_original_onyon_install(rows,[&](){return state;},[&](int color){state.boot|=1u<<color;++bootEvents;},e),e);
 std::vector<std::unique_ptr<Generator>> owned;std::vector<std::unique_ptr<GenObjectOriginalOnyon>> objects;std::vector<Generator*> inventory;
 for(const auto& r:rows){auto gen=std::make_unique<Generator>();auto object=std::unique_ptr<GenObjectOriginalOnyon>(dynamic_cast<GenObjectOriginalOnyon*>(GenObjectFactory::getProduct(0x70326f6eu)));
  require(object&&object->getLatestVersion()==0x4f4e3031u,"real factory p2on/ON01");object->uid=r.uid;gen->mGenObject=object.get();gen->mGenType=nullptr;
  gen->mCarryOverFlags=r.reserved;gen->mRespawnInterval=r.resurrectionDays;gen->mDayLimit=r.dayLimit;inventory.push_back(gen.get());objects.push_back(std::move(object));owned.push_back(std::move(gen));
 }
 auto incomplete=inventory;incomplete.pop_back();require(!pc_p2_original_onyon_preflight(incomplete,e),"incomplete inventory refuses before physical birth");
 auto wrong=inventory;wrong[1]=wrong[0];require(!pc_p2_original_onyon_preflight(wrong,e),"duplicate source refuses before physical birth");
 require(pc_p2_original_onyon_color_access(detached.empty()?nullptr:static_cast<CreatureNode*>(detached[0])->mCreature,true),"unowned AP permission retained");
 checked(pc_p2_original_onyon_preflight(inventory,e),e);
 unsigned births=0,skips=0;
 for(unsigned i=0;i<inventory.size();++i){auto* gen=inventory[i];gen->init();const auto& r=rows[i];
  if(!p2original::onyonEligible(r,wildOnly?0:7)){require(gen->mLatestSpawnCreature==nullptr&&gen->mAliveCount==0,"source boot policy skip");++skips;continue;}
  ++births;auto* actor=gen->mLatestSpawnCreature;require(actor&&gen->mAliveCount==1&&actor->mGenerator==gen,"actual Generator::init owns physical item");
  require(actor->mSRT.t.x==r.position[0]+r.offset[0]&&actor->mSRT.t.y==r.position[1]+r.offset[1]&&actor->mSRT.t.z==r.position[2]+r.offset[2],"literal authored source float placement");
  require(std::abs(actor->mFaceDirection-r.rotation[1]*0.017453292519943295f)<0.00001f,"source degree yaw consumed");
  std::string identity;require(pc_p2_original_onyon_identity(actor,identity)&&identity==r.sourceSha+":"+r.sourceKey,"durable source identity excludes pointers and AP tokens");
  if(r.index==4)require(itemMgr->getUfo()==actor&&dynamic_cast<UfoItem*>(actor),"real native ship family/manager");
  else {auto* onion=dynamic_cast<GoalItem*>(actor);require(onion&&itemMgr->getContainer(r.index)==actor&&onion->mOnionColour==r.index,"real native RGB Onion family/manager");bool isBooted=true;require(pc_p2_original_onyon_booted(actor,isBooted)&&isBooted==(!wildOnly&&!discoveredOnly),"actual source progress rather than AP mask");
   if(wildOnly||discoveredOnly){require(!pc_p2_original_onyon_access(actor),"wild source Onion initially unopened");require(!pc_p2_original_onyon_color_access(actor,true),"AP unlock cannot bypass source-unopened Onion");onion->startBoot();require(bootEvents>0&&pc_p2_original_onyon_access(actor),"actual native boot event updates independent source progress");}
  }
 }
 require(births==(wildOnly?2:4)&&skips==(wildOnly?3:1),"full five-row inventory physically births exact policy subset");
 std::array<unsigned char,104> buffer{};RamStream output(buffer.data(),int(buffer.size()));objects[0]->ramSaveParameters(output);require(output.getPosition()==104,"real native cache hook writes exact checksummed width");
 if(negative){if(!std::strcmp(negative,"checksum"))buffer[100]^=1;else require(false,"known cache negative");}
 GenObjectOriginalOnyon restored;RamStream input(buffer.data(),int(buffer.size()));restored.ramLoadParameters(input);require(restored.uid==rows[0].uid&&input.getPosition()==104,"actual native cache callback reconstructs source-bound identity");
 if(negative)require(false,"corrupted cache must refuse");
 // Detach newly born fixture items before restoring baseline list ownership;
 // no game tick, save, shared assets or external process is modified.
 for(auto* node=list->mChild;node;){auto* next=node->mNext;auto* c=static_cast<CreatureNode*>(node)->mCreature;std::string id;if(pc_p2_original_onyon_identity(c,id))node->del();node=next;}
 pc_p2_original_onyon_unload();for(auto* node:detached)list->add(node);
 require(itemMgr->getContainer(Red)&&itemMgr->getUfo(),"fixture baseline infrastructure restored");
 for(auto& gen:owned)gen->mGenObject=nullptr;
 std::printf("PASS ORIGINAL_ONYON_NATIVE checks=%u literal_rows=5 physical_births=%u policy_skips=%u wild=%d discovered_unbooted=%d native_behavior=1 retail_model=0 full_course_gameplay=0\n",checks,births,skips,int(wildOnly),int(discoveredOnly));std::fflush(nullptr);std::_Exit(0);
}
class TestApp:public PlugPikiApp{
 std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
bool captainSeen=false;
public:int idle()override{
 require(std::chrono::steady_clock::now()-start<std::chrono::seconds(55),"bounded initialized fixture startup");
 int result=PlugPikiApp::idle();
 auto* guarded=naviMgr?naviMgr->getNavi():nullptr;
 require(!captainSeen||guarded!=nullptr,"initialized captain did not disappear");
 if(auto* n=guarded&&guarded->getCurrState()?guarded:nullptr){captainSeen=true;if(forceDown)p2_fixture_require_captain(false,false,0,0);p2_fixture_require_captain(GameStat::orimaDead,n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,0);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_randomizer_ready()||!naviMgr||!pikiMgr||!itemMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 auto*n=naviMgr->getActiveNavi();if(!n||!n->getCurrState()||n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
 require(!GameStat::orimaDead&&n->mHealth>1,"captain alive");int count=0;Iterator it(pikiMgr);for(it.first();!it.isDone();it.next())++count;if(count!=20)return result;
 std::printf("ORIGINAL_ONYON_BASELINE pikmin=20 window=960x540\n");std::fflush(nullptr);run();return result;
 }
};
}
int main(int argc,char** argv){
 for(int i=1;i<argc;++i){if(!std::strncmp(argv[i],"--bad-cache=",12))negative=argv[i]+12;else if(!std::strncmp(argv[i],"--onyon-manifest=",17))manifestPath=argv[i]+17;else if(!std::strcmp(argv[i],"--wild-only"))wildOnly=true;else if(!std::strcmp(argv[i],"--discovered-unbooted"))discoveredOnly=true;else if(!std::strcmp(argv[i],"--force-captain-down"))forceDown=true;}
 require(manifestPath!=nullptr,"literal source onyn manifest supplied");
 SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();
 pc_sim_rng_note_main_thread();std::string e;checked(pc_sim_rng_begin_offline(0x148,0x248,e),e);pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_randomizer_enabled(),"real generated assets required");
 if(!pc_window_init("Original source Onyon factory fixture",960,540))return 3;
 pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();int width=0,height=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&width,&height);require(width==960&&height==540,"centered 960x540 startup");
 pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}
