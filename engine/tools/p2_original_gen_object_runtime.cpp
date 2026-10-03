// Real native factory/stream integration only. One SYNTHETIC zero-birth row
// isolates serialization; this never claims original course/actor admission.
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
#include "pc_p2_original_gen_object.h"
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
struct ZeroBirthProvider:GroupProvider{
 unsigned preflights=0,reserves=0;
 bool preflight(const std::vector<CatalogRow>& rows,std::string&)override{++preflights;return rows.size()==1&&rows[0].enemy.count==0;}
 bool reserve(const std::vector<CatalogRow>& rows,std::string&)override{++reserves;return rows.size()==1&&rows[0].enemy.count==0;}
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&)override{return false;}
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&)override{return false;}
 bool release(Creature*,unsigned,std::string&)override{return false;}
};
void run(){
 auto* captains=naviMgr;auto* pikis=pikiMgr;auto* items=itemMgr;std::string e;PcSimRngCheckpoint before,after;checked(pc_sim_rng_capture(before,e),e);
 require(originalActors().rows().empty(),"never replace an installed original course");
 CatalogRow row;row.course="fixture";row.member="zero-birth.txt";row.sourceKey="fixture/zero-birth.txt#0";row.enemy.uid=originalGeneratorUid(row.sourceKey);row.enemy.source=2;row.enemy.count=0;row.enemy.pelletColor=1;
 checked(originalActors().install(std::string(64,'a'),{row},[](const CatalogRow&,std::string&){return true;},e),e);
 require(GenObjectFactory::factory!=nullptr,"actual native factory installed");
 std::unique_ptr<GenObjectOriginalEnemy> object(dynamic_cast<GenObjectOriginalEnemy*>(GenObjectFactory::getProduct(0x70326f67u)));
 require(object&&object->getLatestVersion()==0x4f473032u,"actual factory produces exact typed OG02 object");
 GeneratorState saved;saved.uid=row.enemy.uid;saved.count=0;saved.reserved=5;saved.resurrectionDays=0;saved.dayLimit=-1;saved.epoch=2;saved.activation=3;
 std::string bytes;checked(encodeOriginalState(originalActors().fingerprint(),saved,bytes,e),e);require(bytes.size()==132,"exact OGC2 width");
 bool prior=Generator::ramMode;Generator::ramMode=true;
 RamStream stateInput(bytes.data(),int(bytes.size()));object->read(stateInput);require(stateInput.getPosition()==132,"real GenBase RAM reader consumes exact record");require(object->mState.uid==saved.uid&&object->mState.epoch==2&&object->mState.activation==3,"real native object preserves identity fields");
 Generator source;source.mGenObject=object.get();source.mGenType=nullptr;GroupBinding binding;GeneratorState literal=saved;literal.epoch=literal.activation=0;
 checked(pc_p2_original_gen_object_collect(&source,literal,binding,e),e);ZeroBirthProvider provider;checked(pc_p2_original_course_install({binding},provider,e),e);source.init();require(provider.preflights==1&&provider.reserves==1,"whole synthetic row admitted before zero births");
 GeneratorState expected;unsigned alive=99;require(pc_p2_original_groups().state(&source,expected,alive)&&alive==0&&expected.epoch==3&&expected.activation==4,"actual RAM activation/source respawn changes observed");
 std::array<unsigned char,4096> buffer{};RamStream output(buffer.data(),int(buffer.size()));source.write(output);const int length=output.getPosition();require(length==166,"actual complete Generator RAM layout has no AP SLT1 trailer");
 std::string written(reinterpret_cast<char*>(buffer.data()),size_t(length));auto start=written.find("OGC2");require(start!=std::string::npos&&start+132<=written.size(),"typed cache payload present in actual native stream");
 if(negative){
  int readLength=length;
  if(!std::strcmp(negative,"truncated"))readLength=int(start)+131;
  else if(!std::strcmp(negative,"checksum"))buffer[start+100]^=1;
  else if(!std::strcmp(negative,"catalog"))buffer[start+4]='b';
  else if(!std::strcmp(negative,"version"))buffer[start+3]='3';
  else require(false,"known negative mode");
  Generator bad;RamStream input(buffer.data(),readLength);bad.read(input);require(false,"production adapter must abort corrupted native stream");
 }
 Generator restored;RamStream input(buffer.data(),length);restored.read(input);require(input.getPosition()==length,"actual complete Generator RAM reader consumes exact record");
 std::unique_ptr<GenObjectOriginalEnemy> restoredObject(dynamic_cast<GenObjectOriginalEnemy*>(restored.mGenObject));require(restoredObject!=nullptr&&restored.mGenType==nullptr,"real factory reconstructed typed object without P1 personality/type");
 GroupBinding restoredBinding;checked(pc_p2_original_gen_object_collect(&restored,literal,restoredBinding,e),e);
 require(restoredBinding.state.uid==expected.uid&&restoredBinding.state.epoch==expected.epoch&&restoredBinding.state.activation==expected.activation&&restoredBinding.state.reserved==expected.reserved&&restoredBinding.state.dayNum==expected.dayNum,"source state survives whole native cache transport");
 require(restored._70==row.enemy.uid&&restored.mRespawnInterval==0&&restored.mDayLimit==-1,"physical restored Generator compatibility identity repaired from authority");
 checked(pc_p2_original_course_unload(e),e);source.mGenObject=nullptr;restored.mGenObject=nullptr;Generator::ramMode=prior;
 checked(pc_sim_rng_capture(after,e),e);require(before.profile==after.profile&&before.simState==after.simState&&before.cosmeticState==after.cosmeticState&&before.simDraws==after.simDraws&&before.cosmeticDraws==after.cosmeticDraws,"native factory/cache integration consumes no RNG");
 require(naviMgr==captains&&pikiMgr==pikis&&itemMgr==items,"live game managers unchanged");
 std::printf("PASS ORIGINAL_GEN_OBJECT checks=%u real_factory=1 real_generator_stream=1 null_p1_type=1 synthetic_rows=1 actual_original_births=0 full_course=0\n",checks);std::fflush(nullptr);std::_Exit(0);
}
class TestApp:public PlugPikiApp{
 std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
public:int idle()override{
 require(std::chrono::steady_clock::now()-start<std::chrono::seconds(55),"bounded initialized fixture startup");
 int result=PlugPikiApp::idle();if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_randomizer_ready()||!naviMgr||!pikiMgr||!itemMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 auto*n=naviMgr->getActiveNavi();if(!n||!n->getCurrState()||n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
 require(!GameStat::orimaDead&&n->mHealth>1,"captain alive");int count=0;Iterator it(pikiMgr);for(it.first();!it.isDone();it.next())++count;if(count!=20)return result;
 std::printf("ORIGINAL_GEN_OBJECT_BASELINE pikmin=20 window=960x540\n");std::fflush(nullptr);run();return result;
 }
};
}
int main(int argc,char** argv){
 for(int i=1;i<argc;++i)if(!std::strncmp(argv[i],"--bad-cache=",12))negative=argv[i]+12;
 SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();
 pc_sim_rng_note_main_thread();std::string e;checked(pc_sim_rng_begin_offline(0x148,0x248,e),e);pc_gpu_preference_apply();pc_bbft_init(argc,argv);require(pc_randomizer_enabled(),"real generated assets required");
 if(!pc_window_init("Original native generator cache fixture",960,540))return 3;
 pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();int width=0,height=0;SDL_GetWindowSize(SDL_GL_GetCurrentWindow(),&width,&height);require(width==960&&height==540,"centered 960x540 startup");
 pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new TestApp());return 0;
}
