// Real native GenItem/gate factory and animation fixture, actual 3-row source.
// Source gate bodies are born and retired inside stopped engine steps.
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
#include "pc_p2_original_gate_native.h"
#include "BuildingItem.h"
#include "Interactions.h"
#include "PikiAI.h"
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
void require(bool b,const char* s){++checks;if(!b){std::printf("FAIL ORIGINAL_GATE %s\n",s);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool b,const std::string& e){if(!b)std::fprintf(stderr,"ORIGINAL_GATE_ERROR %s\n",e.c_str());require(b,"native source adapter operation");}

const char* manifestPath=nullptr;bool forceDown=false;
struct WorkProbe:ActBreakWall {
 explicit WorkProbe(Piki* p):ActBreakWall(p){}
 void prepare(BuildingItem* b){init(b);mWall=b;mState=STATE_BreakWall;mWorkTimer=0;mIsAttackReady=true;mStartAttackTime=gameflow.mWorldClock.mCurrentGameMinute;mHitPikminPosition=mPiki->mSRT.t;}
};
void run(){
 std::string e;std::vector<GateRecord> rows;checked(readGates(manifestPath,rows,e),e);require(rows.size()==3,"literal original three gate rows");
 checked(pc_p2_original_gate_install(rows,e),e);
 std::vector<std::unique_ptr<Generator>> owned;std::vector<std::unique_ptr<GenObjectOriginalGate>> objects;std::vector<Generator*> inventory;
 for(const auto& r:rows){auto g=std::make_unique<Generator>();auto o=std::unique_ptr<GenObjectOriginalGate>(dynamic_cast<GenObjectOriginalGate*>(GenObjectFactory::getProduct(0x70326774u)));require(o&&o->getLatestVersion()==0x47543031u,"real p2gt/GT01 factory");o->uid=r.uid;g->mGenObject=o.get();g->mGenType=nullptr;g->mCarryOverFlags=r.reserved;g->mRespawnInterval=r.resurrectionDays;g->mDayLimit=r.dayLimit;inventory.push_back(g.get());objects.push_back(std::move(o));owned.push_back(std::move(g));}
 auto incomplete=inventory;incomplete.pop_back();require(!pc_p2_original_gate_preflight(incomplete,e),"incomplete inventory refuses");auto duplicate=inventory;duplicate[1]=duplicate[0];require(!pc_p2_original_gate_preflight(duplicate,e),"duplicate inventory refuses");checked(pc_p2_original_gate_preflight(inventory,e),e);
 for(auto* g:inventory)g->init();
 auto links=pc_p2_original_gate_links();require(links.size()==3,"three actual source gate links");for(unsigned i=0;i<3;++i)require(links[i].identity==rows[i].sourceSha+":"+rows[i].sourceKey&&links[i].alive,"ordered source link identity/alive");
 auto snapshot=[&](BuildingItem* b){GateState state;std::string id;require(pc_p2_original_gate_snapshot(b,state,id),"actual body source snapshot");return state;};
 auto animate=[&](BuildingItem* b,GatePhase target){for(int frames=0;frames<1800;++frames){b->doAI();b->doAnimation();if(snapshot(b).phase==target)return;}require(false,"actual native animation reached source phase before bound");};
 for(unsigned i=0;i<3;++i){auto* g=inventory[i];const auto& r=rows[i];auto* b=dynamic_cast<BuildingItem*>(g->mLatestSpawnCreature);require(b&&g->mAliveCount==1&&b->mGenerator==g,"actual native Generator body binding");require(b->mSRT.t.x==r.position[0]+r.offset[0]&&b->mSRT.t.y==r.position[1]+r.offset[1]&&b->mSRT.t.z==r.position[2]+r.offset[2],"exact original gate transform");require(std::abs(b->mFaceDirection-r.rotation[1]*0.017453292519943295f)<0.00001f,"source yaw");require(b->mMaxHealth==r.segmentLife*3&&b->mNumStages==3&&b->mWayPoint,"actual 3stage body/health/route");
  Iterator workers(pikiMgr);workers.first();auto* worker=static_cast<Piki*>(*workers);require(worker!=nullptr,"real native Pikmin worker");auto work=std::make_unique<WorkProbe>(worker);work->prepare(b);float sourceDamage=pc_p2_original_gate_work_damage(worker);require(sourceDamage>=1,"source health-unit attack excludes P1 work fractions");work->breakWall();b->doAI();require(snapshot(b).health==r.segmentLife-sourceDamage,"actual ActBreakWall uses raw source damage without /600");animate(b,GatePhase::Wait);
  std::vector<std::uint8_t> fresh;checked(gateExport(r,gateInitial(r),fresh,e),e);RamStream initial(fresh.data(),int(fresh.size()));b->doLoad(initial);
  InteractAttack hit(naviMgr->getNavi(),nullptr,r.segmentLife*.25f,false);require(b->stimulate(hit),"real InteractAttack accepts gate work");animate(b,GatePhase::Wait);require(snapshot(b).health==r.segmentLife*.75f&&snapshot(b).segmentsDown==0,"actual source partial segment damage");
  std::array<unsigned char,128> bytes{};RamStream output(bytes.data(),int(bytes.size()));b->doSave(output);require(output.getPosition()==128,"actual native doSave typed payload");
  auto old=b;int poolSize=itemMgr->getSize();int nodeSize=itemMgr->mMeltingPotMgr->getSize();b->kill(false);require(itemMgr->getSize()==poolSize&&itemMgr->mMeltingPotMgr->getSize()==nodeSize-1,"retirement preserves unrelated item pool and unlinks one node");require(!pc_p2_original_gate_owned(old),"actual native retirement clears source identity");g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;
  if(negative&&i==0){bytes.back()^=1;RamStream input(bytes.data(),int(bytes.size()));g->loadCreature(input);require(false,"corrupt physical gate cache must refuse");}
  RamStream input(bytes.data(),int(bytes.size()));g->loadCreature(input);b=dynamic_cast<BuildingItem*>(g->mLatestSpawnCreature);require(b&&g->mAliveCount==1&&snapshot(b).health==r.segmentLife*.75f,"actual generator cache reconstructs partial HP body");if(i==0){auto actual=pc_p2_original_gate_links();require(actual.size()==3&&actual.back().identity==r.sourceSha+":"+r.sourceKey&&actual.front().identity==rows[1].sourceSha+":"+rows[1].sourceKey,"gate links follow actual recreated body birth order");}
  for(unsigned stage=0;stage<3;++stage){InteractAttack damage(naviMgr->getNavi(),nullptr,r.segmentLife+1,false);require(b->stimulate(damage),"physical next segment attack");b->doAI();require(snapshot(b).phase==GatePhase::Down&&snapshot(b).segmentsDown==stage,"native fall waits animation completion");
   if(i==0&&stage==0){b->doAnimation();auto pending=snapshot(b);RamStream saved(bytes.data(),int(bytes.size()));b->doSave(saved);b->kill(false);g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;RamStream replay(bytes.data(),int(bytes.size()));g->loadCreature(replay);b=dynamic_cast<BuildingItem*>(g->mLatestSpawnCreature);auto resumed=snapshot(b);require(resumed.phase==GatePhase::Down&&resumed.health==pending.health&&resumed.segmentsDown==pending.segmentsDown&&resumed.animationFrame==pending.animationFrame,"actual native mid-fall save/load preserves source phase and frame");}
   animate(b,stage==2?GatePhase::Open:GatePhase::Wait);require(snapshot(b).segmentsDown==stage+1,"actual animation advances one segment");}
  bool alive=true;require(pc_p2_original_gate_alive(r.sourceSha+":"+r.sourceKey,alive)&&!alive,"actual open gate drives living association");require(b->isCompleted()&&!b->isAlive()&&b->mWayPoint->mIsOpen,"physical finished gate opens route");RamStream done(bytes.data(),int(bytes.size()));b->doSave(done);b->kill(false);g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;RamStream loaded(bytes.data(),int(bytes.size()));g->loadCreature(loaded);b=dynamic_cast<BuildingItem*>(g->mLatestSpawnCreature);require(b&&b->isCompleted()&&snapshot(b).phase==GatePhase::Open,"actual destroyed body cache restore");b->kill(false);g->mLatestSpawnCreature=nullptr;g->mAliveCount=0;
 }
 std::array<unsigned char,256> fullRecord{};RamStream serialized(fullRecord.data(),int(fullRecord.size()));Generator::ramMode=true;owned[0]->write(serialized);Generator nativeDecoded;RamStream parsed(fullRecord.data(),serialized.getPosition());nativeDecoded.read(parsed);Generator::ramMode=false;auto* decodedObject=dynamic_cast<GenObjectOriginalGate*>(nativeDecoded.mGenObject);require(decodedObject&&decodedObject->uid==rows[0].uid&&nativeDecoded.mCarryOverFlags==3&&nativeDecoded.mRespawnInterval==0,"actual complete native Generator cache transport without legacy GenType");
 std::array<unsigned char,104> record{};RamStream out(record.data(),int(record.size()));objects[0]->ramSaveParameters(out);GenObjectOriginalGate decoded;RamStream in(record.data(),int(record.size()));decoded.ramLoadParameters(in);require(decoded.uid==rows[0].uid&&in.getPosition()==104,"actual source-bound generator cache");
 pc_p2_original_gate_unload();for(auto& g:owned)g->mGenObject=nullptr;
 std::printf("PASS ORIGINAL_GATE_NATIVE checks=%u literal_rows=3 physical_births=10 actual_animation=1 physical_cache=1 retail_model=0 full_course_gameplay=0\n",checks);std::fflush(nullptr);std::_Exit(0);
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
 std::printf("ORIGINAL_GATE_BASELINE pikmin=20 window=960x540\n");std::fflush(nullptr);run();return result;
 }
};
}
int main(int argc,char** argv){
 for(int i=1;i<argc;++i){if(!std::strncmp(argv[i],"--bad-cache=",12))negative=argv[i]+12;else if(!std::strncmp(argv[i],"--gate-manifest=",16))manifestPath=argv[i]+16;else if(!std::strcmp(argv[i],"--force-captain-down"))forceDown=true;}
 require(manifestPath!=nullptr,"literal source gate manifest supplied");
 SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();
 pc_sim_rng_note_main_thread();std::string e;checked(pc_sim_rng_begin_offline(0x148,0x248,e),e);pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_randomizer_enabled(),"real generated assets required");
 if(!pc_window_init("Original source gate factory fixture",960,540))return 3;
 pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();int width=0,height=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&width,&height);require(width==960&&height==540,"centered 960x540 startup");
 pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}
