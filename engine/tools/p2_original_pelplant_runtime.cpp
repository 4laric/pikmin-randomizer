// #148 real source0 provider fixture. Engine initialized births/direct damage
// are diagnostic controls; only SDL input drives actual Piki pickup/Onion carry.
// No health/cargo/population/reward/transport-action writes masquerade as play.
#include <SDL2/SDL.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <memory>
#include <array>
#include "system.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Pellet.h"
#include "teki.h"
#include "Generator.h"
#include "MapMgr.h"
#include "GameStat.h"
#include "PlayerState.h"
#include "KeyConfig.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_original_pelplant_native.h"
#include "pc_p2_original_actor.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
namespace {
using namespace p2original;
using namespace p2original::pelplant;
SDL_Joystick* pad=nullptr;
bool refusal=false;
void require(bool yes,const char* text){if(!yes){std::printf("FAIL P2_ORIGINAL_PELPLANT %s\n",text);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool yes,const std::string& error){if(!yes)std::fprintf(stderr,"P2_ORIGINAL_PELPLANT_ERROR %s\n",error.c_str());require(yes,"actual native provider call");}
float distance(const Vector3f& a,const Vector3f& b){float x=a.x-b.x,z=a.z-b.z;return std::sqrt(x*x+z*z);}
void input(unsigned keys=0,int x=0,int y=0,int cx=0,int cy=0){
 pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,(keys&KBBTN_B)!=0);
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTX,Sint16(cx*32767/74));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTY,Sint16(-cy*32767/74));SDL_JoystickUpdate();
}
void point(Navi* n,const Vector3f& goal,bool walk,unsigned keys=0){
 const Vector3f& from=walk?n->mSRT.t:n->mCursorWorldPos;
 float dx=goal.x-from.x,dz=goal.z-from.z,d=std::sqrt(dx*dx+dz*dz);int x=0,y=0;
 if(d>(walk?15.f:6.f)){const Vector3f& a=n->controlCamera()->mViewXAxis;float power=walk?65:22;
  x=int(std::lround(power*(dx*a.x+dz*a.z)/d));y=int(std::lround(power*(dx*a.z-dz*a.x)/d));}
 input(keys,x,y);
}
int heads(){int n=0;Iterator it(itemMgr->getPikiHeadMgr());CI_LOOP(it){if(static_cast<PikiHeadItem*>(*it)->isAlive())++n;}return n;}
// EXACT_ROWS is populated from the seven original day5 catalog literals below.
std::vector<CatalogRow> rows(){std::vector<EnemyRecord> rows;std::vector<CatalogRow> catalogRows;
// SOURCE0_ROWS_BEGIN
{EnemyRecord a;a.source=0;a.birthType=0;a.count=1;a.spawnType=1;a.treasureCode=0;a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=8;a.uid=1380981806u;a.directionDegrees=50.0f;a.appearRadius=100.0f;a.enemySize=0.0f;a.pelletProbability=0.0f;a.position={-400.922485f,0.0f,2646.80151f};a.offset={0.0f,0.0f,0.0f};a.generatorVersion="0001";a.generatorTail={"3","1","2"};rows.push_back(a);CatalogRow cr;cr.course="tutorial";cr.member="nonloop/3-9.txt";cr.index=0;cr.sourceKey="tutorial/nonloop/3-9.txt#0";cr.enemy=a;catalogRows.push_back(cr);}
{EnemyRecord a;a.source=0;a.birthType=0;a.count=1;a.spawnType=1;a.treasureCode=0;a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=8;a.uid=1377574526u;a.directionDegrees=130.0f;a.appearRadius=80.0f;a.enemySize=0.0f;a.pelletProbability=0.0f;a.position={-584.422363f,0.0f,3160.86987f};a.offset={0.0f,0.0f,0.0f};a.generatorVersion="0001";a.generatorTail={"3","1","2"};rows.push_back(a);CatalogRow cr;cr.course="tutorial";cr.member="nonloop/3-9.txt";cr.index=1;cr.sourceKey="tutorial/nonloop/3-9.txt#1";cr.enemy=a;catalogRows.push_back(cr);}
{EnemyRecord a;a.source=0;a.birthType=0;a.count=2;a.spawnType=2;a.treasureCode=0;a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=8;a.uid=1379639453u;a.directionDegrees=273.0f;a.appearRadius=50.0f;a.enemySize=0.0f;a.pelletProbability=0.0f;a.position={-21.917719f,1e-06f,2870.73413f};a.offset={0.0f,0.0f,0.0f};a.generatorVersion="0001";a.generatorTail={"3","1","1"};rows.push_back(a);CatalogRow cr;cr.course="tutorial";cr.member="nonloop/3-9.txt";cr.index=2;cr.sourceKey="tutorial/nonloop/3-9.txt#2";cr.enemy=a;catalogRows.push_back(cr);}
{EnemyRecord a;a.source=0;a.birthType=0;a.count=1;a.spawnType=1;a.treasureCode=0;a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=8;a.uid=1380772436u;a.directionDegrees=120.0f;a.appearRadius=100.0f;a.enemySize=0.0f;a.pelletProbability=0.0f;a.position={-1342.3938f,4.195519f,2825.7605f};a.offset={0.0f,0.0f,0.0f};a.generatorVersion="0001";a.generatorTail={"3","5","2"};rows.push_back(a);CatalogRow cr;cr.course="tutorial";cr.member="nonloop/3-9.txt";cr.index=3;cr.sourceKey="tutorial/nonloop/3-9.txt#3";cr.enemy=a;catalogRows.push_back(cr);}
{EnemyRecord a;a.source=0;a.birthType=0;a.count=1;a.spawnType=1;a.treasureCode=0;a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=8;a.uid=1378713252u;a.directionDegrees=75.0f;a.appearRadius=60.0f;a.enemySize=0.0f;a.pelletProbability=0.0f;a.position={-1340.81335f,0.0f,2606.40112f};a.offset={0.0f,0.0f,0.0f};a.generatorVersion="0001";a.generatorTail={"3","5","2"};rows.push_back(a);CatalogRow cr;cr.course="tutorial";cr.member="nonloop/3-9.txt";cr.index=4;cr.sourceKey="tutorial/nonloop/3-9.txt#4";cr.enemy=a;catalogRows.push_back(cr);}
{EnemyRecord a;a.source=0;a.birthType=0;a.count=1;a.spawnType=1;a.treasureCode=0;a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=8;a.uid=1376670982u;a.directionDegrees=240.0f;a.appearRadius=80.0f;a.enemySize=0.0f;a.pelletProbability=0.0f;a.position={52.872227f,9.173491f,3055.30957f};a.offset={0.0f,0.0f,0.0f};a.generatorVersion="0001";a.generatorTail={"3","5","2"};rows.push_back(a);CatalogRow cr;cr.course="tutorial";cr.member="nonloop/3-9.txt";cr.index=5;cr.sourceKey="tutorial/nonloop/3-9.txt#5";cr.enemy=a;catalogRows.push_back(cr);}
{EnemyRecord a;a.source=0;a.birthType=0;a.count=1;a.spawnType=1;a.treasureCode=0;a.pelletColor=3;a.pelletSize=1;a.pelletMinimum=1;a.pelletMaximum=8;a.uid=1392447527u;a.directionDegrees=0.0f;a.appearRadius=100.0f;a.enemySize=0.0f;a.pelletProbability=0.0f;a.position={-259.878662f,50.0f,2476.47852f};a.offset={0.0f,0.0f,0.0f};a.generatorVersion="0001";a.generatorTail={"3","10","1"};rows.push_back(a);CatalogRow cr;cr.course="tutorial";cr.member="nonloop/3-9.txt";cr.index=6;cr.sourceKey="tutorial/nonloop/3-9.txt#6";cr.enemy=a;catalogRows.push_back(cr);}
// SOURCE0_ROWS_END
 require(catalogRows.size()==7,"seven source0 rows");return catalogRows;
}
struct Instance {Creature* actor=nullptr;Pellet* pellet=nullptr;std::uint64_t handle=0;unsigned token=0,row=0,ordinal=0,amount=0;bool dead=false,delivered=false;unsigned receipts=0,duplicates=0;Vector3f release;int expectedSeeds=0;};
class PelplantApp final:public PlugPikiApp {
 std::unique_ptr<Native> native;ActorRegistry& catalog=originalActors();
 std::vector<CatalogRow> source;std::array<std::unique_ptr<Generator>,7> generators;
 std::array<std::uint64_t,7> generatorHandles{};std::vector<Instance> instances;
 int frame=0,ready=0,phase=0,age=0,caseIndex=0,phaseStart=0,settled=0,baseline=0,growthControl=0;
 bool captainSeen=false,carried=false,nearGoal=false;float travel=0;
 GoalItem* onion=nullptr;
 const unsigned cases[3]={0,4,7};
 Instance& current(){return instances[cases[caseIndex]];}
 int rewards(){return heads()+onion->getTotalStorePikis();}
 Pellet* livePellet(Pellet* identity){Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p==identity&&p->isAlive())return p;}return nullptr;}
 bool death(Creature* actor,std::string& error){
  auto found=std::find_if(instances.begin(),instances.end(),[actor](const Instance& i){return i.actor==actor;});
  if(found==instances.end()){error="death outside original fixture registry";return false;}
  Host* h=native->provider().lookup(actor);
  if(!h||!h->released||h->captured||!found->pellet||native->captured(found->pellet)){error="death did not release same native captured pellet";return false;}
  Pellet* p=livePellet(found->pellet);if(!p||!p->mConfig){error="released configured pellet missing";return false;}
  std::printf("P2_ORIGINAL_PELPLANT_POSITION stage=death_end amount=%u actor=%.3f,%.3f,%.3f pellet=%.3f,%.3f,%.3f flags=%08x dynamics=%d state=%d\n",found->amount,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z,p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,unsigned(p->mCreatureFlags),int(p->isRealDynamics()),p->getState());
  found->release=p->mSRT.t;found->expectedSeeds=p->mConfig->mPelletColor()==Red?p->mConfig->mMatchingOnyonSeeds():p->mConfig->mNonMatchingOnyonSeeds();
  found->dead=true;
  std::printf("P2_ORIGINAL_PELPLANT_RELEASE source=0 uid=%u ordinal=%u token=%u amount=%u same_pointer=1 captured=0 direct_damage_control=1\n",source[found->row].enemy.uid,found->ordinal,found->token,found->amount);
  if(!native->provider().release(actor,found->token,error))return false;
  if(!catalog.retire(actor,found->handle)){error="original fixture instance retirement failed";return false;}return true;
 }
 void setup(){
  // PlugPikiApp::idle clears the active heap before returning. This fixture
  // admits engine resources and births after that return, so use the same
  // App heap as ordinary course initialization and restore the caller's heap.
  struct HeapScope {
   int previous;
   HeapScope():previous(gsys->setHeap(SYSHEAP_App)){}
   ~HeapScope(){gsys->setHeap(previous);}
  } heapScope;
  source=rows();const int rootsBefore=tekiMgr->getSize(),pelletsBefore=pelletMgr->getSize();
  native=std::make_unique<Native>([](unsigned color){return color<3&&playerState&&playerState->hasContainer(int(color));});
  auto& provider=native->provider();std::string error;
  const bool physical=provider.preflight(source,error);
  if(refusal){require(!physical&&provider.size()==0&&tekiMgr->getSize()==rootsBefore&&pelletMgr->getSize()==pelletsBefore,"physical refusal before actor birth");std::puts("PASS P2_ORIGINAL_PELPLANT_RESOURCE_REFUSAL actor_births=0 owned_cleanup=1 gameplay=0");std::fflush(nullptr);std::_Exit(0);}
  checked(physical,error);
  checked(native->geometryOwnershipControl(error),error);
  for(int control=0;control<7;++control){auto invalid=source;
   if(control==0)invalid[0].enemy.generatorVersion="0002";
   if(control==1)invalid[0].enemy.generatorTail.pop_back();
   if(control==2)invalid[0].enemy.generatorTail.push_back("0");
   if(control==3)invalid[0].enemy.generatorTail[0]="4";
   if(control==4)invalid[0].enemy.generatorTail[1]="2";
   if(control==5)invalid[0].enemy.generatorTail[2]="3";
   if(control==6)invalid[0].enemy.generatorTail[1]="1.0";
   require(!provider.preflight(invalid,error)&&provider.size()==0&&tekiMgr->getSize()==rootsBefore&&pelletMgr->getSize()==pelletsBefore,"strict tail refusal without actor allocation");
  }
  checked(provider.preflight(source,error),error);checked(provider.reserve(source,error),error);
  // Genuine manager exhaustion AFTER reservation: full birth allocates the
  // real plant then capture must fail and clean up only its own allocation.
  std::vector<Pellet*> fill;const int available=pelletMgr->getMax()-pelletMgr->getSize();
  for(int i=0;i<available;++i){Pellet* p=pelletMgr->newNumberPellet(Red,0);require(p,"owned negative pool fill");p->init(onion->mSRT.t);p->startAI(0);fill.push_back(p);}
  require(!pelletMgr->newNumberPellet(Red,0),"pool genuinely exhausted");
  generators[0]=std::make_unique<Generator>();Creature* failed=nullptr;
  Position p{-460,mapMgr->getMinY(-460,2155,true),2155};
  require(!provider.birth(source[0],generators[0].get(),0,p,source[0].enemy.directionDegrees*3.14159265359f/180.f,failed,error),"real capture allocation refusal");
  require(!failed&&provider.size()==0&&tekiMgr->getSize()==rootsBefore,"post-allocation owned plant cleanup");
  for(Pellet* owned:fill)owned->kill(false);
  require(pelletMgr->getSize()==pelletsBefore,"only owned negative cargo cleaned");
  std::puts("P2_ORIGINAL_PELPLANT_NEGATIVE_CONTROLS tail_refusals=7 before_birth=1 real_pool_exhaustion=1 after_allocation_cleanup=1");
  checked(catalog.install("1365d511318bebf4eb29adbff90891309460cbbd1bc6e5e99dfcb1dbe8588e5e",source,[](const CatalogRow& r,std::string& e){Initial out;return decode(r,out,e);},error),error);
  native->onDeath([this](Creature* a,std::string& e){return death(a,e);});
  native->onOnion([this](Pellet* p,unsigned token,bool duplicate){auto f=std::find_if(instances.begin(),instances.end(),[token](const Instance& i){return i.token==token;});require(f!=instances.end()&&f->pellet==p&&f->dead,"ordinary Onion exact cargo identity");if(duplicate)++f->duplicates;else{++f->receipts;f->delivered=true;}std::printf("P2_ORIGINAL_PELPLANT_ONION token=%u amount=%u duplicate=%d ordinary_hook=1\n",token,f->amount,int(duplicate));});
  for(unsigned row=0;row<source.size();++row){if(!generators[row])generators[row]=std::make_unique<Generator>();checked(catalog.generator(generators[row].get(),source[row].enemy.uid,generatorHandles[row],error),error);
   for(unsigned ordinal=0;ordinal<source[row].enemy.count;++ordinal){
    // Disclosed family-fixture locations only; source common metadata stays
    // literal and the original-course relocation audit is a separate gate.
    float x=-1500.f-80.f*float(instances.size()),z=2800;
    if(row==0)x=-460,z=2155;if(row==3)x=-600,z=2155;if(row==6)x=-500,z=2155;
    if(row==6){
     // The earlier -700 site straddled the Forest camp's raised bank. Confirm
     // the full initial ten-pellet footprint on actual engine ground queries.
     float low=1e9f,high=-1e9f;
     for(int dx=-60;dx<=60;dx+=60)for(int dz=-60;dz<=60;dz+=60){const float y=mapMgr->getMinY(x+dx,z+dz,true);require(std::isfinite(y),"finite diagnostic10 floor footprint");low=std::min(low,y);high=std::max(high,y);}
     require(high-low<.25f,"diagnostic10 initial footprint lies on flat camp ground");
     std::printf("P2_ORIGINAL_PELPLANT_FIXTURE_GROUND amount=10 x=%.2f z=%.2f samples=9 radius=60 min_y=%.3f max_y=%.3f initial_placement_only=1 original_source_position=0\n",x,z,low,high);
    }
    Position at{x,mapMgr->getMinY(x,z,true),z};Creature* actor=nullptr;
    checked(provider.birth(source[row],generators[row].get(),ordinal,at,source[row].enemy.directionDegrees*3.14159265359f/180.f,actor,error),error);require(actor&&native->owns(actor),"real canonical native source0 actor");
    Instance i;i.actor=actor;i.row=row;i.ordinal=ordinal;Initial initial;checked(decode(source[row],initial,error),error);i.amount=initial.amount;
    checked(catalog.actorActivation(actor,source[row].enemy.uid,ordinal,1,1,i.token,i.handle,error),error);
    unsigned actualSource=999,actualToken=0;InstanceIdentity identity;
    require(catalog.query(actor,actualSource,actualToken,&identity)&&actualSource==0&&actualToken==i.token&&identity.generator==source[row].enemy.uid&&identity.ordinal==ordinal&&identity.epoch==1&&identity.activation==1,"actual original registry source0 identity");
    checked(provider.bind(source[row],actor,i.token,error),error);instances.push_back(i);
    auto* h=provider.lookup(actor);require(h&&h->row.enemy.source==0&&h->row.enemy.pelletSize==1,"literal source0 and unmodified common drop metadata");
    require(distance(actor->mSRT.t,Vector3f(at.x,at.y,at.z))<.1f&&std::fabs(actor->mSRT.t.y-at.y)<.1f,"actual actor birth retains requested fixture position");
    std::printf("P2_ORIGINAL_PELPLANT_POSITION stage=birth row=%u ordinal=%u requested=%.3f,%.3f,%.3f actor=%.3f,%.3f,%.3f captured=%d pellet=%.3f,%.3f,%.3f\n",row,ordinal,at.x,at.y,at.z,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z,int(h->captured!=nullptr),h->captured?h->captured->mSRT.t.x:0,h->captured?h->captured->mSRT.t.y:0,h->captured?h->captured->mSRT.t.z:0);
   }
  }
  require(instances.size()==8&&provider.size()==8,"seven rows eight actual native births");
  // Small/Middle full-only damage control, followed by source farm-triggered
  // Middleâ†’Full growth with authentic runtime animation events.
  auto& middle=instances[7];auto* h=provider.lookup(middle.actor);require(h&&h->state==State::Middle&&!h->captured,"actual10 initialMiddle");
  const float health=h->health;checked(provider.damage(middle.actor,100,"s__0",error),error);require(h->damage==0&&h->health==health,"Middle rejects damaging head-hit");checked(provider.farm(middle.actor,-1,error),error);
  std::puts("P2_ORIGINAL_PELPLANT_READY rows=7 births=8 source0_distinguished=1 resources_before_birth=1 baseline=20 direct_initialization=1 original_positions=0");
 }
public:
 int idle() override {
  int result=PlugPikiApp::idle();Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  bool initialized=n&&n->getCurrState();if(initialized)captainSeen=true;
  require(!captainSeen||initialized,"initialized captain disappeared");
  if(initialized)require(!GameStat::orimaDead&&!naviMgr->isNaviDead(n)&&n->getCurrState()->getID()!=NAVISTATE_Dead&&std::isfinite(n->mHealth)&&n->mHealth>0,"captain remains alive before pause/movie boundary");
  require(++frame<12000,"bounded actual gameplay frame budget");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!initialized||!pikiMgr||!tekiMgr||!pelletMgr||!itemMgr||!mapMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  if(phase==0){if(n->getCurrState()->getID()!=NAVISTATE_Walk||++ready<45)return result;
   int live=0,red=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p->isAlive()){++live;red+=p->mColor==Red;}}
   require(live==20&&red==20,"actual20 fieldRed baseline");onion=itemMgr->getContainer(Red);require(onion,"real Red Onion, no pod receiver");setup();phase=1;}
  ++age;auto& i=current();std::string error;
  if(growthControl==0){auto& middle=instances[7];auto* h=native->provider().lookup(middle.actor);require(h,"source growth control actor retained");
   if(h->state==State::Small){const float hp=h->health;checked(native->provider().damage(middle.actor,100,"s__0",error),error);require(h->health==hp&&h->damage==0&&!h->captured,"Small rejects damaging head-hit after actual wither blend");checked(native->provider().farm(middle.actor,1,error),error);growthControl=1;std::puts("P2_ORIGINAL_PELPLANT_FULL_ONLY Small=1 Middle=1 actual_wither_blend=1");}}
  if(phase==1){auto* h=native->provider().lookup(i.actor);require(h&&!h->dead,"live actual provider actor");
   if(h->state!=State::Full)return result;
   i.pellet=h->captured;require(i.pellet&&native->captured(i.pellet)&&i.pellet->mConfig,"actual configured captured number pellet");
   std::printf("P2_ORIGINAL_PELPLANT_POSITION stage=full_before_damage amount=%u actor=%.3f,%.3f,%.3f pellet=%.3f,%.3f,%.3f\n",i.amount,i.actor->mSRT.t.x,i.actor->mSRT.t.y,i.actor->mSRT.t.z,i.pellet->mSRT.t.x,i.pellet->mSRT.t.y,i.pellet->mSRT.t.z);
   require(i.pellet->mConfig->mCarryMinPikis()>=int(i.amount),"configured literal number carry identity");
   baseline=rewards();carried=nearGoal=false;travel=0;settled=0;
   checked(native->provider().damage(i.actor,0,"s__0",error),error);phase=2;phaseStart=age;return result;}
  if(phase==2){input();if(!i.dead)return result;require(i.expectedSeeds>0&&!native->captured(i.pellet),"source death-END releases actual cargo");Pellet* released=livePellet(i.pellet);require(released,"first ordinary released update retains cargo");std::printf("P2_ORIGINAL_PELPLANT_POSITION stage=first_released_update amount=%u pellet=%.3f,%.3f,%.3f flags=%08x dynamics=%d state=%d\n",i.amount,released->mSRT.t.x,released->mSRT.t.y,released->mSRT.t.z,unsigned(released->mCreatureFlags),int(released->isRealDynamics()),released->getState());std::fflush(nullptr);phase=3;phaseStart=age;return result;}
  Pellet* body=livePellet(i.pellet);
  if(phase==3){
   Piki* nearest=nullptr;float closest=1e9f;Iterator roster(pikiMgr);CI_LOOP(roster){auto* p=static_cast<Piki*>(*roster);if(p->isAlive()&&p->mColor==Red&&distance(n->mSRT.t,p->mSRT.t)<closest){closest=distance(n->mSRT.t,p->mSRT.t);nearest=p;}}
   if(n->getPlatePikis()<10&&nearest&&closest>50)point(n,nearest->mSRT.t,true);else input(KeyConfig::_instance->mSetCursorKey.mBind);
   if(n->getPlatePikis()>=10&&age-phaseStart>30){phase=4;phaseStart=age;input();}return result;}
  if(body){require(!native->captured(body),"released cargo stays ordinary");
   if(body->mCarrierCount>=body->mConfig->mCarryMinPikis()){carried=true;travel=std::max(travel,distance(body->mSRT.t,i.release));}
   if(carried&&body->mTargetGoal==static_cast<Suckable*>(onion)&&distance(body->mSRT.t,onion->mSRT.t)<100)nearGoal=true;
   if(age%60==0){
    float closest=1e9f;int formation=0,flying=0;Iterator roster(pikiMgr);CI_LOOP(roster){auto* p=static_cast<Piki*>(*roster);if(p->isAlive()){closest=std::min(closest,distance(p->mSRT.t,body->mSRT.t));formation+=p->mMode==PikiMode::FormationMode;flying+=p->getState()==PIKISTATE_Flying;}}
    std::printf("P2_ORIGINAL_PELPLANT_CARRY amount=%u carriers=%u strength=%u ordinary_Onion=1 travel=%.2f rewards=%d free=%d atari=%d state=%d slot=%d body=%.2f,%.2f,%.2f navi_distance=%.2f cursor_distance=%.2f followers=%d nearest_piki=%.2f formation=%d flying=%d cstick=%.3f free_camera=%d\n",i.amount,body->mCarrierCount,body->mCarrierCounter,travel,rewards()-baseline,int(body->isFree()),int(body->isAtari()),body->getState(),body->getMinFreeSlotIndex(),body->mSRT.t.x,body->mSRT.t.y,body->mSRT.t.z,distance(n->mSRT.t,body->mSRT.t),distance(n->mCursorWorldPos,body->mSRT.t),n->getPlatePikis(),closest,formation,flying,n->mCStick.length(),pc_settings_get_free_camera());std::fflush(nullptr);
   }
   if(body->mCarrierCount>=body->mConfig->mCarryMinPikis()){input();return result;}
   // Use the ordinary tutorial driver's approach and cursor-aimed throw.
   // A flying Pikmin's real collision with an available number-pellet slot
   // enters Transport; no fixture writes to Pikmin or pellet action state.
   if(distance(n->mSRT.t,body->mSRT.t)>100){point(n,body->mSRT.t,true);phaseStart=age;return result;}
   const unsigned keys=(age-phaseStart)%60<15?KeyConfig::_instance->mThrowKey.mBind:0;
   point(n,body->mSRT.t,false,keys);return result;
  }
  input();require(carried&&nearGoal&&travel>25,"cargo disappeared without actual Piki carry and Onion approach");
  if(++settled<90)return result;
  require(i.delivered&&i.receipts==1&&i.duplicates==0,"actual ordinary Onion hook exactly once");require(rewards()-baseline==i.expectedSeeds,"actual Onion population conservation");
  std::printf("P2_ORIGINAL_PELPLANT_CASE_PASS amount=%u same_pointer=1 ordinary_SDL_Piki_carry=1 ordinary_Onion=1 receipts=1 duplicates=0 rewards=%d direct_damage_control=1 natural_attack=0\n",i.amount,rewards()-baseline);
  if(++caseIndex<3){phase=1;return result;}
  auto& provider=native->provider();for(auto& owned:instances)if(provider.lookup(owned.actor)){checked(provider.release(owned.actor,owned.token,error),error);require(catalog.retire(owned.actor,owned.handle),"owned final registry cleanup");}
  for(unsigned row=0;row<source.size();++row)require(catalog.retireGenerator(generators[row].get(),generatorHandles[row]),"owned generator retirement after family cleanup");
  require(provider.size()==0,"no retained family-owned roots");
  std::puts("PASS P2_ORIGINAL_PELPLANT_RUNTIME seven_rows=1 eight_births=1 literal_amounts=1,5,10 full_only_damage=1 actual_animation_release=1 ordinary_Piki_Onion=1 exactly_once=1 owned_cleanup=1 fixture_placements=1 natural_attack=0 save_resume=0");std::fflush(nullptr);std::_Exit(0);
 }
};
}
int main(int argc,char**argv){
 for(int i=1;i<argc;++i)if(!std::strcmp(argv[i],"--refuse-resources"))refusal=true;
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_pikipelago_surface_course()&&!std::strcmp(pc_pikipelago_surface_course(),"tutorial")&&!pc_pikipelago_room_preview(),"ordinary tutorial lifecycle, not Pod preview");
 require(pc_window_init("P2 original Pelplant actual provider fixture",960,540),"window init");pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect b{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&b);
 require(width==960&&height==540&&std::abs(x-(b.x+(b.w-width)/2))<=2&&std::abs(y-(b.y+(b.h-height)/2))<=2,"960x540 centered baseline");
 int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual SDL pad");
 char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",Pelplant fixture pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
 require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"pad mapping");pad=SDL_JoystickOpen(device);require(pad,"pad open");pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);input();
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new PelplantApp());return 0;
}
