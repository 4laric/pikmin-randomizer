// Native direct-control diagnostic. Fixture placement and collision stimuli
// are disclosed controls, not ordinary player or full-course acceptance.
#include <SDL2/SDL.h>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
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
#include "PikiMgr.h"
#include "ItemMgr.h"
#include "PikiHeadItem.h"
#include "GoalItem.h"
#include "Pellet.h"
#include "GameStat.h"
#include "Generator.h"
#include "MapMgr.h"
#include "teki.h"
#include "Collision.h"
#include "Interactions.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_original_foliage_native.h"
#include "pc_p2_retail_cave_context.h"
#include "p2_original_foliage_guard.h"
#include "pc_p2_original_group_engine.h"
#include "pc_randomizer.h"
#include "pc_coop.h"
#include "netplay/pc_sim_rng.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
namespace {
using namespace p2original;
using namespace p2original::foliage;
bool human=false,refusal=false,naturalWalk=false,caveBatch=false;
std::string batch="tutorial",sourcePair="91,88";
std::array<unsigned,2> sourceIDs{{91,88}};
unsigned firstSource(){return sourceIDs[0];}
const char* batchSources(){return sourcePair.c_str();}
SDL_Joystick* pad=nullptr;
void require(bool ok,const char* message){if(!ok){std::printf("FAIL ORIGINAL_FOLIAGE %s\n",message);std::fflush(nullptr);std::_Exit(1);}}
void checked(bool ok,const std::string& e){if(!ok)std::fprintf(stderr,"ORIGINAL_FOLIAGE_ERROR %s\n",e.c_str());require(ok,"native foliage operation");}
void input(int x=0,int y=0){
 require(pad,"natural walking virtual controller");
 pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*32767/74));SDL_JoystickUpdate();
}
void point(Navi* n,const Vector3f& goal){
 float dx=goal.x-n->mSRT.t.x,dz=goal.z-n->mSRT.t.z,d=std::sqrt(dx*dx+dz*dz);int x=0,y=0;
 if(d>5){const Vector3f& a=n->controlCamera()->mViewXAxis;const float power=55;x=int(std::lround(power*(dx*a.x+dz*a.z)/d));y=int(std::lround(power*(dx*a.z-dz*a.x)/d));}
 input(x,y);
}
int heads(){int count=0;Iterator it(itemMgr->getPikiHeadMgr());CI_LOOP(it)if(static_cast<PikiHeadItem*>(*it)->isAlive())++count;return count;}
struct HeapScope{int previous;HeapScope():previous(gsys->setHeap(SYSHEAP_App)){}~HeapScope(){gsys->setHeap(previous);}};
class FoliageApp final:public PlugPikiApp {
 std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
 std::unique_ptr<Native> native;
 std::vector<CatalogRow> rows;
 std::array<std::unique_ptr<Generator>,3> generators;
 std::array<std::string,3> cache;
 std::array<Creature*,2> actors{};
 std::array<InstanceIdentity,2> firstIdentity;
 std::array<Vector3f,2> collisionCentre;
 std::array<std::array<Vector3f,5>,2> partCentres;
 std::array<Vector3f,2> brownLargeChildCentre;
 std::array<float,2> health{};
 int ready=0,phase=0,age=0,pelletBaseline=0,rewardBaseline=0,tekiBaseline=0;
 bool captainSeen=false;
 unsigned walked=0;std::array<bool,2> naturalTouch{};Vector3f walkRetreat;
 const std::string fingerprint=std::string(64,'f');
 ActorRegistry caveRegistry;
 struct CaveLeaf{Creature* actor=nullptr;unsigned row=0,ordinal=0,token=0;std::uint64_t handle=0;Vector3f centre,child;float health=0;};
 std::vector<CaveLeaf> caveLeaves;
 std::array<std::uint64_t,3> caveGenerators{};
 unsigned caveActivation=1;
 unsigned previousCaveToken=0;
 void caveInstall(Navi* n){
  HeapScope heap;std::string e;checked(native->provider().cavePrepare(rows,e),e);checked(native->provider().caveReserve(rows,e),e);
  for(unsigned r=0;r<rows.size();++r){auto* g=generators[r].get();checked(caveRegistry.generator(g,rows[r].enemy.uid,caveGenerators[r],e),e);
   for(unsigned ordinal=0;ordinal<rows[r].enemy.count;++ordinal){Position at{n->mSRT.t.x+90,0,n->mSRT.t.z+float(caveLeaves.size()*7)};at.y=mapMgr->getMinY(at.x,at.z,true);require(std::isfinite(at.y),"bounded cave control native floor");
    CaveLeaf leaf;leaf.row=r;leaf.ordinal=ordinal;checked(native->provider().caveBirth(rows[r],g,ordinal,at,0,leaf.actor,e),e);
    checked(caveRegistry.actorActivation(leaf.actor,rows[r].enemy.uid,ordinal,caveActivation,caveActivation,leaf.token,leaf.handle,e),e);checked(native->provider().bind(rows[r],leaf.actor,leaf.token,e),e);
    require(leaf.token>previousCaveToken,"cave reentry never reuses retired family token");previousCaveToken=leaf.token;
    auto* h=native->provider().lookup(leaf.actor);require(h&&h->generator==nullptr&&leaf.actor->mGenerator==nullptr&&h->token==leaf.token,"cave association never attaches P1 generator");
    unsigned source=0,token=0;InstanceIdentity id;require(caveRegistry.query(leaf.actor,source,token,&id)&&source==rows[r].enemy.source&&id.generator==rows[r].enemy.uid&&id.ordinal==ordinal&&id.epoch==caveActivation&&id.activation==caveActivation,"caller cave registry exact source identity");
    auto* root=leaf.actor->mCollInfo->getSphere(0x66303030u);auto* child=leaf.actor->mCollInfo->getSphere(0x66303031u);require(root&&child&&root->mRadius==(source==92?50:30)&&child->mRadius==(source==92?35:20),"cave literal source root and child spheres");
    leaf.centre=root->mCentre;leaf.child=child->mCentre;leaf.health=leaf.actor->mHealth;caveLeaves.push_back(leaf);
    std::printf("ORIGINAL_CAVE_FOLIAGE_BIRTH cave=tutorial_1 floor=2 source=%u row=%u uid=%u ordinal=%u epoch=%u activation=%u token=%u native_generator=0 initialized_placement=1\n",source,rows[r].caveRow,id.generator,ordinal,caveActivation,caveActivation,token);
   }
  }
  require(caveLeaves.size()==12&&native->provider().size()==12&&tekiMgr->getSize()==tekiBaseline+12,"all authored cave leaf minimum counts6,4,2 physically born");require(!caveRegistry.retireGenerator(generators[0].get(),caveGenerators[0]),"live cave leaves retain caller generator association");checkEconomy();std::fflush(nullptr);
 }
 void caveRelease(){std::string e;for(const auto& leaf:caveLeaves){checked(native->provider().release(leaf.actor,leaf.token,e),e);unsigned source=0,token=0;
   require(caveRegistry.query(leaf.actor,source,token),"caller association retained until explicit retirement");require(caveRegistry.retire(leaf.actor,leaf.handle)&&!caveRegistry.query(leaf.actor,source,token),"caller explicitly retires released cave leaf before address reuse");}
  for(unsigned r=0;r<rows.size();++r){require(generators[r]->mAliveCount==17&&generators[r]->mLatestSpawnDay==123,"cave release changes no P1 generator counts or day");require(caveRegistry.retireGenerator(generators[r].get(),caveGenerators[r]),"caller retires cave association generator after all leaves");}
  caveLeaves.clear();require(native->provider().size()==0,"cave owned roots released");checkEconomy();
 }
 void caveSetup(Navi* n){
  HeapScope heap;std::string e;const auto* d=p2retail::descriptor("tutorial_1");const auto* f=d?p2retail::definition(*d,2):nullptr;require(f,"genuine cave tutorial_1 floor2 descriptor");
  for(unsigned i=0;i<f->rows.size();++i){const auto& literal=f->rows[i];if(literal.sourceId!=91&&literal.sourceId!=92&&literal.sourceId!=47)continue;CatalogRow r;
   r.course=d->cave;r.member=d->source;r.caveFloor=2;r.caveRow=i;r.index=2*256+i;r.sourceKey=r.course+"/"+r.member+"#"+std::to_string(r.index);r.sourceForm=SourceForm::CaveTekiInfo;r.caveSourceSha256=d->sourceSha256;
   r.enemy.source=unsigned(literal.sourceId);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.count=literal.minimum();r.enemy.generatorVersion="CAVE";rows.push_back(r);
  }
  require(rows.size()==3&&rows[0].enemy.count==6&&rows[1].enemy.count==4&&rows[2].enemy.count==2,"literal cave three-source minimums");native=std::make_unique<Native>();tekiBaseline=tekiMgr->getSize();pelletBaseline=pelletMgr->getSize();rewardBaseline=rewards();
  bool physical=native->provider().cavePrepare(rows,e);if(refusal){require(!physical&&native->provider().size()==0&&tekiMgr->getSize()==tekiBaseline,"cave missing bank refuses before any native allocation");std::puts("PASS ORIGINAL_CAVE_FOLIAGE_RESOURCE_REFUSAL sources=91,92,47 births=0 direct_control=1 cave_layout=0");std::fflush(nullptr);std::_Exit(0);}
  checked(physical,e);checked(native->geometryOwnershipControl(e),e);checked(caveRegistry.install(fingerprint,rows,caveDecode,e),e);
  for(auto& g:generators){g=std::make_unique<Generator>();g->mGenType=nullptr;g->mGenObject=nullptr;g->mAliveCount=17;g->mLatestSpawnDay=123;}
  caveInstall(n);std::puts("ORIGINAL_CAVE_FOLIAGE_READY sources=91,92,47 counts=6,4,2 descriptor=tutorial_1 floor=2 native_fixture_course=tutorial initialized_placement=1 cave_layout=0 other_families=skipped direct_control=1 gameplay=0");std::fflush(nullptr);
 }
 void caveControl(Navi* n){
  if(phase==4||phase==5){if(age>=30){require(tekiMgr->getSize()==tekiBaseline,"normal engine recycles released cave pool references");if(phase==4){++caveActivation;caveInstall(n);phase=3;age=0;}else{checkEconomy();std::puts("PASS ORIGINAL_CAVE_FOLIAGE sources=91,92,47 counts=6,4,2 typed_tekiinfo=1 normal_animation=1 no_p1_generator_effects=1 caller_retirement=1 reentry=1 no_rewards=1 initialized_placement=1 cave_layout=0 direct_control=1 gameplay=0");std::fflush(nullptr);std::_Exit(0);}}return;}
  for(const auto& leaf:caveLeaves){auto* h=native->provider().lookup(leaf.actor);require(h&&h->generator==nullptr&&leaf.actor->mGenerator==nullptr&&leaf.actor->isAlive()&&leaf.actor->mHealth==leaf.health,"cave host ownership and invulnerability retained");
   auto* actor=static_cast<BTeki*>(leaf.actor);require(actor->mVelocity.length()==0&&actor->mVolatileVelocity.length()==0&&actor->mTargetVelocity.length()==0,"cave roots retain zero physical velocities");
   auto* root=leaf.actor->mCollInfo->getSphere(0x66303030u);auto* child=leaf.actor->mCollInfo->getSphere(0x66303031u);require(root&&child&&(root->mCentre-leaf.centre).length()<.01f&&(child->mCentre-leaf.child).length()<.01f,"cave animation retains actual static colliders");}
  for(const auto& g:generators)require(g->mAliveCount==17&&g->mLatestSpawnDay==123,"cave touch and clock change no P1 generator bookkeeping");checkEconomy();
  if(phase==1&&age>=15){for(const auto& leaf:caveLeaves){auto* actor=static_cast<BTeki*>(leaf.actor);const Vector3f position=n->mSRT.t,velocity=n->mVelocity;n->mSRT.t=actor->mSRT.t;n->mVelocity.set(2,0,0);CollEvent event(n,nullptr,actor->mCollInfo->getBoundingSphere());actor->collisionCallback(event);n->mSRT.t=position;n->mVelocity=velocity;
    auto* h=native->provider().lookup(actor);require(h->active&&h->touched,"actual engine cave leaf collision dispatch starts motion");InteractAttack attack(n,actor->mCollInfo->getBoundingSphere(),1000,false);actor->stimulate(attack);InteractPress press(n,1000);actor->stimulate(press);require(actor->mHealth==leaf.health,"actual cave leaf attack and press invulnerable");}phase=2;age=0;}
  else if(phase==2){bool done=true;for(const auto& leaf:caveLeaves){auto* h=native->provider().lookup(leaf.actor);if(age==1)require(h->frame>0,"actual engine cave leaf motion clock advances");done&=!h->active&&!h->touched;if(!h->active)require(h->frame==(h->row.enemy.source==47?49:59),"cave literal normal END frame");}if(done){caveRelease();phase=4;age=0;}else require(age<900,"actual cave leaf motions finish normally");}
  else if(phase==3&&age>=30){caveRelease();phase=5;age=0;}
 }
 CatalogRow literal(unsigned source,unsigned index,unsigned uid,const Position& at,float facing,const char* course="tutorial"){
  CatalogRow r;r.course=course;r.member="plantsgen.txt";r.index=index;r.sourceKey=r.course+"/plantsgen.txt#"+std::to_string(index);
  r.enemy.source=source;r.enemy.uid=uid;r.enemy.count=1;r.enemy.position=at;r.enemy.directionDegrees=facing;return r;
 }
 int rewards(){int total=heads();for(int color=0;color<3;++color){auto* onion=itemMgr->getContainer(color);if(onion)total+=onion->getTotalStorePikis();}return total;}
 void checkEconomy(){require(pelletMgr->getSize()==pelletBaseline&&rewards()==rewardBaseline,"decorative foliage produced no cargo or rewards");}
 void install(bool reentry){
  HeapScope heap;std::string e;std::vector<GroupBinding> bindings;
  for(unsigned i=0;i<3;++i){if(!generators[i])generators[i]=std::make_unique<Generator>();auto* g=generators[i].get();
   g->mGenType=nullptr;g->mGenObject=nullptr;g->mRespawnInterval=0;g->mDayLimit=-1;g->mCarryOverFlags=0;
   GroupBinding b;b.generator=g;b.state.uid=rows[i].enemy.uid;b.state.count=rows[i].enemy.count;b.state.resurrectionDays=g->mRespawnInterval;
   if(reentry)checked(decodeOriginalState(fingerprint,b.state.uid,b.state.count,cache[i],b.state,e),e);
   bindings.push_back(b);
  }
  checked(pc_p2_original_course_install(bindings,native->provider(),e),e);
  // Disc reentry deliberately exercises original respawn/activation. RAM rows
  // with literal reserved=0 require the separate saved-creature loader.
  const bool oldRam=Generator::ramMode;Generator::ramMode=false;
  for(auto& g:generators)g->init();Generator::ramMode=oldRam;
  require(native->provider().size()==2&&tekiMgr->getSize()==tekiBaseline+2,"two native births; count-zero row has no actor");
  actors.fill(nullptr);Iterator it(tekiMgr);CI_LOOP(it){Creature* actor=*it;unsigned source=0,token=0;InstanceIdentity identity;
   if(!originalActors().query(actor,source,token,&identity))continue;
   // The original UID determines the fixture slot independently of species.
   unsigned i=identity.generator==rows[0].enemy.uid?0:identity.generator==rows[1].enemy.uid?1:2;require(i<2&&source==sourceIDs[i]&&!actors[i],"distinct original foliage identity");actors[i]=actor;
   require(native->owns(actor)&&identity.generator==rows[i].enemy.uid&&identity.ordinal==0&&token,"native source UID and ordinal association");
   auto* h=native->provider().lookup(actor);require(h&&h->generator==generators[i].get()&&h->token==token,"native generator and family binding");
   if(reentry)require(identity.activation==firstIdentity[i].activation+1&&identity.epoch==firstIdentity[i].epoch+1,"disc cache reentry advances epoch and activation");else firstIdentity[i]=identity;
   require(actor->mCollInfo&&actor->mCollInfo->getBoundingSphere(),"actual source static collider");
   collisionCentre[i]=actor->mCollInfo->getBoundingSphere()->mCentre;health[i]=actor->mHealth;
   const unsigned parts=source==46?5:2;
   require(actor->mCollInfo->getBoundingSphere()->getChildCount()==int(parts-1),"literal source collider child topology");
   for(unsigned j=0;j<parts;++j){auto* part=actor->mCollInfo->getSphere(0x66303030u+j);require(part,"literal source collider part identity");partCentres[i][j]=part->mCentre;
    if(source==46)require(part->mRadius==(j==0?50.f:j==1?25.f:20.f),"Dandelion literal root and leaf sphere radii");}
   if(source==92){auto* root=actor->mCollInfo->getSphere(0x66303030u);auto* child=actor->mCollInfo->getSphere(0x66303031u);
    require(root&&child&&root->getChildCount()==1&&root->mRadius==50&&child->mRadius==35,"brown large literal static root50 child35");brownLargeChildCentre[i]=child->mCentre;}
   std::printf("ORIGINAL_FOLIAGE_BIRTH source=%u uid=%u ordinal=%u epoch=%llu activation=%llu reentry=%d\n",source,identity.generator,identity.ordinal,(unsigned long long)identity.epoch,(unsigned long long)identity.activation,int(reentry));
  }
  require(actors[0]&&actors[1],"both literal variants physically admitted");checkEconomy();
 }
 void setup(Navi* n){
  HeapScope heap;std::string e;require(originalActors().rows().empty(),"fixture does not replace another original course");
  // Literal source/type/tail and UID from day5 rows #0/#4. These nearby
  // positions are fixture relocations, not proof of original course geometry.
  // The west site sits above a steep tutorial terrain edge. Put both control
  // plants on the east approach used by the successfully surveyed walk.
  walkRetreat=n->mSRT.t;Position a{n->mSRT.t.x+90,0,n->mSRT.t.z},b{n->mSRT.t.x+90,0,n->mSRT.t.z+70};
  a.y=mapMgr->getMinY(a.x,a.z,true);b.y=mapMgr->getMinY(b.x,b.z,true);require(std::isfinite(a.y)&&std::isfinite(b.y),"actual native arena floor");
  if(batch=="brown-large"){
   // Literal Last #0 uses source object0004's constructor birthType0 default.
   // Startup now decodes this version explicitly. Only positions are moved;
   // these controls establish neither Last-course nor cave placement.
   rows={literal(92,0,1390080862u,a,0,"last"),literal(91,0,1390538979u,b,0,"tutorial")};
  }else if(batch=="forest"){
   // Actual forest/plantsgen.txt literals #23 (Clover47) and #0 (Ooinu_s49),
   // decoded in forest47-49-source-records.json. Only positions are relocated
   // to the same surveyed tutorial arena; this is not forest-course admission.
   rows={literal(47,23,1376717705u,a,0,"forest"),literal(49,0,1389527839u,b,180,"forest")};
  }else if(batch=="dandelion"){
   rows={literal(46,13,1375741226u,a,0,"forest"),literal(80,5,1390227387u,b,90,"forest")};
  }else if(batch=="shoots"){
   rows={literal(51,0,1382955810u,a,240,"yakushima"),literal(52,5,1390174228u,b,270,"yakushima")};
  }else if(batch=="horsetails"){
   rows={literal(90,14,1384248119u,a,270,"forest"),literal(88,4,1381420794u,b,95)};
  }else rows={literal(91,0,1390538979u,a,0),literal(88,4,1381420794u,b,95)};
  auto zero=literal(firstSource(),0,originalGeneratorUid("fixture/foliage-zero#0"),a,0);zero.course="fixture";zero.member="foliage-zero";zero.sourceKey="fixture/foliage-zero#0";zero.enemy.count=0;rows.push_back(zero);
  native=std::make_unique<Native>();tekiBaseline=tekiMgr->getSize();pelletBaseline=pelletMgr->getSize();rewardBaseline=rewards();
  bool physical=native->provider().preflight(rows,e);
  if(refusal){require(!physical&&native->provider().size()==0&&tekiMgr->getSize()==tekiBaseline&&pelletMgr->getSize()==pelletBaseline,"physical resource refusal before allocation");if(batch=="tutorial")std::puts("PASS ORIGINAL_FOLIAGE_RESOURCE_REFUSAL births=0 direct_control=1 gameplay=0");else std::printf("PASS ORIGINAL_FOLIAGE_RESOURCE_REFUSAL sources=%s births=0 direct_control=1 gameplay=0\n",batchSources());std::fflush(nullptr);std::_Exit(0);}
  checked(physical,e);checked(native->geometryOwnershipControl(e),e);
  checked(originalActors().install(fingerprint,rows,[](const CatalogRow& r,std::string& err){return decode(r,err);},e),e);install(false);
  std::printf("ORIGINAL_FOLIAGE_READY sources=%s zero_count=1 baseline=20 window=960x540 initialized_placement=1 original_positions=0 naturalinput=%d callbackcontrol=%d gameplay=0\n",batchSources(),int(naturalWalk),int(!naturalWalk&&!human));std::fflush(nullptr);
 }
 void stimulus(Navi* n){
  for(unsigned i=0;i<2;++i){auto* actor=static_cast<BTeki*>(actors[i]);auto* h=native->provider().lookup(actor);require(h,"retained live native host");
   // Calls the real engine collision dispatch using a genuine captain and its
   // velocity. This is a disclosed callback control, not a walking test.
   const Vector3f priorPosition=n->mSRT.t,priorVelocity=n->mVelocity;const bool alreadyActive=h->active;const float priorFrame=h->frame;
   n->mSRT.t=actor->mSRT.t;n->mVelocity.set(2,0,0);CollEvent collision(n,nullptr,actor->mCollInfo->getBoundingSphere());actor->collisionCallback(collision);
   n->mSRT.t=priorPosition;n->mVelocity=priorVelocity;
   require(h->active&&h->touched&&(alreadyActive?h->frame==priorFrame:h->frame==0),"real captain collision starts or retains typed touched motion");
   InteractAttack attack(n,actor->mCollInfo->getBoundingSphere(),1000,false);actor->stimulate(attack);InteractPress press(n,1000);actor->stimulate(press);
   require(actor->mHealth==health[i]&&actor->isAlive()&&h->active,"actual attack and press cannot damage decorative foliage");
  }
  checkEconomy();
 }
 void checkStatic(){for(unsigned i=0;i<2;++i){auto* actor=actors[i];const auto* h=native->provider().lookup(actor);require(h&&actor->mHealth==health[i]&&actor->isAlive(),"native foliage remains invulnerable");
   const auto& centre=actor->mCollInfo->getBoundingSphere()->mCentre;const auto& before=collisionCentre[i];require(std::fabs(centre.x-before.x)<.01f&&std::fabs(centre.y-before.y)<.01f&&std::fabs(centre.z-before.z)<.01f,"animated pose does not move static source collider");
   for(unsigned j=0;j<(h->row.enemy.source==46?5u:2u);++j){const auto* part=actor->mCollInfo->getSphere(0x66303030u+j);require(part,"retained source collider part");const auto& old=partCentres[i][j];require(std::fabs(part->mCentre.x-old.x)<.01f&&std::fabs(part->mCentre.y-old.y)<.01f&&std::fabs(part->mCentre.z-old.z)<.01f,"all source leaf collider centres remain static during touch");}
   if(h->row.enemy.source==92){const auto* child=actor->mCollInfo->getSphere(0x66303031u);require(child&&child->mRadius==35,"brown large child retained");const auto& old=brownLargeChildCentre[i];require(std::fabs(child->mCentre.x-old.x)<.01f&&std::fabs(child->mCentre.y-old.y)<.01f&&std::fabs(child->mCentre.z-old.z)<.01f,"brown large child remains static through touch");}
   if(!(actor->mVelocity.x==0&&actor->mVelocity.y==0&&actor->mVelocity.z==0))std::printf("ORIGINAL_FOLIAGE_VELOCITY_FAILURE source=%u velocity=%.9g,%.9g,%.9g volatile=%.9g,%.9g,%.9g position=%.9g,%.9g,%.9g\n",h->row.enemy.source,actor->mVelocity.x,actor->mVelocity.y,actor->mVelocity.z,actor->mVolatileVelocity.x,actor->mVolatileVelocity.y,actor->mVolatileVelocity.z,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);require(actor->mVelocity.x==0&&actor->mVelocity.y==0&&actor->mVelocity.z==0,"native scenery remains constrained");}
  checkEconomy();
 }
 void reenter(){std::string e;for(unsigned i=0;i<3;++i){checked(pc_p2_original_groups().cache(generators[i].get(),fingerprint,cache[i],e),e);GeneratorState s;unsigned live=0;require(pc_p2_original_groups().state(generators[i].get(),s,live)&&s.deathCount==0&&live==rows[i].enemy.count,"cache preserves literal count and no decorative deaths");}
  checked(pc_p2_original_course_unload(e),e);require(native->provider().size()==0,"native unload releases owned foliage");for(auto* actor:actors)require(!actor->isAlive(),"unloaded native roots are dead");checkEconomy();phase=4;age=0;
 }
 void walking(Navi* n){
  if(phase==1){require(walked<2,"natural walking source index");auto* h=native->provider().lookup(actors[walked]);require(h,"naturally touched source remains owned");
   if(h->active&&h->touched){naturalTouch[walked]=true;input();phase=2;age=0;
    std::printf("ORIGINAL_FOLIAGE_NATURAL_TOUCH source=%u captain=%.3f,%.3f,%.3f plant=%.3f,%.3f,%.3f frame=%.3f naturalinput=1 callbackcontrol=0\n",h->row.enemy.source,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,actors[walked]->mSRT.t.x,actors[walked]->mSRT.t.y,actors[walked]->mSRT.t.z,h->frame);std::fflush(nullptr);
   }else {point(n,collisionCentre[walked]);if(age%120==0){std::printf("ORIGINAL_FOLIAGE_WALK_PROGRESS source=%u captain=%.3f,%.3f,%.3f goal=%.3f,%.3f,%.3f velocity=%.3f,%.3f,%.3f\n",h->row.enemy.source,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,collisionCentre[walked].x,collisionCentre[walked].y,collisionCentre[walked].z,n->mVelocity.x,n->mVelocity.y,n->mVelocity.z);std::fflush(nullptr);}require(age<600,"SDL walking must reach real foliage touch");}
  }else if(phase==2){point(n,walkRetreat);auto* h=native->provider().lookup(actors[walked]);require(h,"natural animation host retained");
   if(!h->active&&!h->touched){std::printf("ORIGINAL_FOLIAGE_NATURAL_END source=%u frame=%.3f naturalinput=1 callbackcontrol=0 retreat_input=1\n",h->row.enemy.source,h->frame);std::fflush(nullptr);++walked;age=0;if(walked==2){require(naturalTouch[0]&&naturalTouch[1],"actual captain naturally touched both original species");reenter();}else phase=1;}
   else require(age<900,"natural touched motion completes through normal engine clock");
  }
 }
public:
 int idle()override{
  const auto budget=std::chrono::seconds(human?600:90);
  if(std::chrono::steady_clock::now()-started>=budget){if(native){if(caveBatch)caveRelease();else{std::string e;if(!pc_p2_original_course_unload(e))std::fprintf(stderr,"ORIGINAL_FOLIAGE_GUARD_CLEANUP %s\n",e.c_str());}}std::puts("ORIGINAL_FOLIAGE_GUARD_EXIT exit=86 bounded=1");std::fflush(nullptr);std::_Exit(86);}
  int result=PlugPikiApp::idle();auto* n=naviMgr?naviMgr->getNavi():nullptr;const bool initialized=n&&n->getCurrState();if(initialized)captainSeen=true;
  require(!captainSeen||initialized,"initialized captain retained");
  if(initialized){
   // Canonical fixture-only guard: all actual death signals precede every
   // movie/pause/readiness return and observation counter. A negative probe
   // changes the guard input only, never captain health or production state.
   const bool forced=std::getenv("P2_ORIGINAL_FOLIAGE_FORCE_CAPTAIN_DOWN")!=nullptr;
   p2_fixture_require_captain(GameStat::orimaDead||forced,
     naviMgr->isNaviDead(n)||n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,age);
  }
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!initialized||!pikiMgr||!tekiMgr||!pelletMgr||!itemMgr||!mapMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  if(!phase){if(n->getCurrState()->getID()!=NAVISTATE_Walk||++ready<45)return result;int live=0,red=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p->isAlive()){++live;red+=p->mColor==Red;}}require(live==20&&red==20,"actual20 Red Pikmin baseline");if(caveBatch)caveSetup(n);else setup(n);phase=1;return result;}
  if(human)return result;++age;
  if(caveBatch){caveControl(n);return result;}
  if(phase==4){if(naturalWalk)input();if(age>=30){require(tekiMgr->getSize()==tekiBaseline,"normal engine recycles unloaded pool references");install(true);phase=3;age=0;}return result;}
  if(phase==5){if(naturalWalk)input();if(age>=30){require(native->provider().size()==0&&tekiMgr->getSize()==tekiBaseline,"final normal engine pool cleanup");checkEconomy();std::printf(naturalWalk?"PASS ORIGINAL_FOLIAGE_WALK sources=%s naturalinput=1 callbackcontrol=0 natural_touch=2 normal_animation=1 collider_static=1 no_rewards=1 initialized_placement=1 cache_disc_reentry=1 full_course=0\n":"PASS ORIGINAL_FOLIAGE sources=%s resources=1 collider_static=1 invulnerable=1 typed_touch=1 normal_animation=1 cache_disc_reentry=1 no_rewards=1 direct_control=1 gameplay=0\n",batchSources());std::fflush(nullptr);std::_Exit(0);}return result;}
  checkStatic();if(phase==3&&age>=30){if(naturalWalk)input();std::string e;checked(pc_p2_original_course_unload(e),e);require(native->provider().size()==0,"final owned release");phase=5;age=0;return result;}
  if(naturalWalk){walking(n);return result;}
  if(phase==1&&age>=15){stimulus(n);phase=2;age=0;}
  else if(phase==2){bool finished=true;for(auto* actor:actors){auto* h=native->provider().lookup(actor);require(h,"active callback retains same family host");if(age==1)require(h->frame>0,"normal engine update advances motion");finished&=!h->active&&!h->touched;}
   if(finished){reenter();}else require(age<900,"normal native animation eventually completes");}
  return result;
 }
};
}
int main(int argc,char** argv){
 human=std::getenv("P2_ORIGINAL_FOLIAGE_HUMAN")!=nullptr;refusal=std::getenv("P2_ORIGINAL_FOLIAGE_REFUSE_RESOURCES")!=nullptr;naturalWalk=!human&&std::getenv("P2_ORIGINAL_FOLIAGE_WALK")!=nullptr;
 if(const char* selected=std::getenv("P2_ORIGINAL_FOLIAGE_BATCH"))batch=selected;else if(std::getenv("P2_ORIGINAL_FOLIAGE_FOREST"))batch="forest";
 if(batch=="tutorial")sourceIDs={91,88},sourcePair="91,88";
 else if(batch=="forest")sourceIDs={47,49},sourcePair="47,49";
 else if(batch=="brown-large")sourceIDs={92,91},sourcePair="92,91";
 else if(batch=="dandelion")sourceIDs={46,80},sourcePair="46,80";
 else if(batch=="shoots")sourceIDs={51,52},sourcePair="51,52";
 else if(batch=="horsetails")sourceIDs={90,88},sourcePair="90,88";
 else if(batch=="cave")caveBatch=true;
 else require(false,"known explicit foliage batch");
 require(!caveBatch||(!naturalWalk&&!human),"cave birth/lifetime control requires diagnostic or refusal mode");
 SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();
 pc_sim_rng_note_main_thread();std::string e;checked(pc_sim_rng_begin_offline(0x9188,0x8891,e),e);pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(!pc_randomizer_enabled()&&pc_pikipelago_surface_course()&&!std::strcmp(pc_pikipelago_surface_course(),"tutorial")&&!pc_pikipelago_room_preview(),"real tutorial course assets required");
 require(pc_window_init("Original foliage direct-control diagnostic",960,540),"native window");pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 SDL_Window* window=SDL_GL_GetCurrentWindow();int width=0,height=0,x=0,y=0;SDL_GetWindowSize(window,&width,&height);SDL_GetWindowPosition(window,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
 require(width==960&&height==540&&std::abs(x-(bounds.x+(bounds.w-width)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-height)/2))<=2,"centered960x540 baseline");
 if(naturalWalk){int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"natural virtual pad attachment");char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
  std::string mapping=std::string(guid)+",Foliage walking fixture,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
  require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"natural controller mapping");pad=SDL_JoystickOpen(device);require(pad,"natural controller open");pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);input();
 }
 pc_coop_set_pending(false);gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new FoliageApp());return 0;
}
