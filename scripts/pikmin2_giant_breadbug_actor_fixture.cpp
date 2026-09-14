#include "room-prefix.inc"
#include "pc_p2_purple.h"
#include "Generator.h"
#include "Teki.h"
#include "Section.h"
#include "Controller.h"
#include "PikiState.h"
#include <fstream>
// Giant Breadbug actor arena (#220 batch 4): spawn identity, P2 params,
// Purple-only press, PelletCarry contest, hide-digest heal, defeat throw-up,
// owner-linked nest birth/death. P1 FSM drives locomotion/cargo.
class GiantActorFixture:public PlugPikiApp {
 int frames=0,tick=0,phase=0,phaseTick=0,pressCount=0;
 Teki* giant=nullptr;Teki* nestTeki=nullptr;Pellet* cargoA=nullptr;Pellet* cargoB=nullptr;
 Vector3f nestPos;std::vector<Piki*> squad;Piki* purple=nullptr;Piki* carriers[2]={nullptr,nullptr};
 unsigned giantId=0,nestId=0;Vector3f giantXyz,nestXyz;
public:
 int idle() override {
  int result=PlugPikiApp::idle();require(++frames<12000,"Giant actor arena timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(frames%300==0){std::printf("P2_GIANT_ARENA_WAIT ready=%d naviMgr=%d tekiMgr=%d pause=%d overlay=%d navi=%d\n",int(pc_p2_preview_cargo_free_ready()),int(naviMgr!=nullptr),int(tekiMgr!=nullptr),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(naviMgr&&naviMgr->getNavi()!=nullptr));std::fflush(stdout);}
  if(playerState&&frames<3000)for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // seed tutorial flags before any ship-text/tutorial window can trigger
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result; // wait out the tutorial overlay: object updates stay frozen while it is up
  Navi* n=naviMgr->getNavi();if(!n)return result;++tick;++phaseTick;
  if(tick==1){
   std::ifstream in("giant-arena.txt");require(bool(in>>giantId>>nestId),"arena ids");
   require(bool(in>>giantXyz.x>>giantXyz.y>>giantXyz.z),"giant xyz");
   require(bool(in>>nestXyz.x>>nestXyz.y>>nestXyz.z),"nest xyz");
   std::puts("P2_GIANT_STEP config");std::fflush(stdout);
   Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator){if(t->mGenerator->_70==giantId)giant=t;if(t->mGenerator->_70==nestId)nestTeki=t;}}
   require(giant&&nestTeki&&giant!=nestTeki,"giant/nest identity");
   require(giant->mTekiType==TEKI_Collec&&nestTeki->mTekiType==TEKI_Hollec,"giant/nest native types");
   std::puts("P2_GIANT_STEP identity");std::fflush(stdout);
   Vector3f birth=giant->mPersonality->mPosition,nbirth=nestTeki->mPersonality->mPosition;
   require(std::fabs(birth.x-giantXyz.x)<.02&&std::fabs(birth.y-giantXyz.y)<.02&&std::fabs(birth.z-giantXyz.z)<.02,"giant birth XYZ");
   require(std::fabs(nbirth.x-nestXyz.x)<.02&&std::fabs(nbirth.y-nestXyz.y)<.02&&std::fabs(nbirth.z-nestXyz.z)<.02,"nest birth XYZ");
   require(giant->mHealth==2000.0f&&giant->mMaxHealth==2000.0f,"P2 giant health params");
   giant->setCreatureFlag(CF_AIAlwaysActive);nestTeki->setCreatureFlag(CF_AIAlwaysActive); // defeat grid AI-culling while the overlay steals the camera
   nestPos=nestTeki->mSRT.t;
   n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   require(pc_p2_purples_enabled(),"purple bank required for press gates");
   std::puts("P2_GIANT_STEP params");std::fflush(stdout);
   for(int i=0;i<20;++i){ // small starting squad: 20 red leaf Pikmin beside the captain
    Piki* p=static_cast<Piki*>(pikiMgr->birth());require(p,"squad birth");
    p->init(n);p->initColor(Red);p->setFlower(Leaf);
    Vector3f spot=giantXyz+Vector3f(float((i%5)-2)*10,0,120.0f+float(i/5)*8);
    spot.y=mapMgr->getMinY(spot.x,spot.z,true)+2.0f;p->resetPosition(spot);
    p->mFSM->transit(p,PIKISTATE_Normal);squad.push_back(p);
   }
   std::puts("P2_GIANT_STEP squad");std::fflush(stdout);
   Vector3f view=giantXyz+Vector3f(0,0,150);view.y=mapMgr->getMinY(view.x,view.z,true);n->resetPosition(view);
   std::printf("P2_GIANT_ARENA_SQUAD count=20 color=red health=%.1f\n",giant->mHealth);
   phase=1;phaseTick=0;return result;
  }
  require(giant->isAlive()||phase>=5,"giant died outside defeat phase");
  switch(phase){
  case 1:{ // Purple-only press: non-purple resisted, purple applies exactly 100.
   require(phaseTick<60,"press phase stall");
   if(phaseTick==5){
    require(!squad.empty()&&!pc_p2_is_purple(squad[0]),"non-purple presser");
    giant->eventPerformed(TekiEvent(TekiEventType::Pressed,giant,squad[0]));
    require(giant->mHealth==2000.0f,"non-purple press dealt damage");
    purple=squad[1];pc_p2_make_purple(purple);
    giant->eventPerformed(TekiEvent(TekiEventType::Pressed,giant,purple));
    require(giant->mHealth==1900.0f,"purple press damage != 100");
     pressCount=1;
     std::printf("P2_GIANT_ARENA_PRESS non_purple=resisted purple_damage=100 health=%.1f\n",giant->mHealth);
     { // Interruption release: a valid Purple press releases held cargo in place.
      Pellet* held=pelletMgr->newNumberPellet(PELCOLOR_Red,0);require(held,"interrupt pellet");
      held->init(giant->mSRT.t);held->startAI(0);require(held->startStickTeki(giant,1.0f),"interrupt stick");
      giant->setCreaturePointer(2,held);require(giant->getCreaturePointer(2)==held,"interrupt setup");
      giant->eventPerformed(TekiEvent(TekiEventType::Pressed,giant,purple));
      require(giant->getCreaturePointer(2)==nullptr,"interruption did not release held cargo");
      require(giant->mHealth==1800.0f,"interrupt press damage");
      std::printf("P2_GIANT_ARENA_INTERRUPT released=1 health=%.1f\n",giant->mHealth);
      held->kill(false);
     }
     phase=2;phaseTick=0;
   }
   return result;}
  case 2:{ // PelletCarry contest: carriers >= (min+max)/2 steal the cargo back.
   if(phaseTick==1){
    cargoA=pelletMgr->newNumberPellet(PELCOLOR_Red,0);require(cargoA,"contest pellet allocation");
    cargoA->init(giant->mSRT.t);cargoA->startAI(0);
    require(cargoA->mConfig->mCarryMinPikis()==1&&cargoA->mConfig->mCarryMaxPikis()==2,"contest pellet weight");
   }
   require(phaseTick<2400,"giant never grabbed contest pellet");
   bool held=giant->getCreaturePointer(2)==cargoA;
   if(!held&&phaseTick%60==0){ // keep the bait right in front of the wandering giant, camera nearby
    Vector3f forward;giant->outputDirectionVector(forward);
    Vector3f spot=giant->mSRT.t+forward*20.0f;spot.y=mapMgr->getMinY(spot.x,spot.z,true)+5.0f;
    cargoA->mSRT.t=spot;
    Vector3f cam=giant->mSRT.t+Vector3f(0,0,60);cam.y=mapMgr->getMinY(cam.x,cam.z,true);n->resetPosition(cam);
   }
   if(held){carriers[0]=squad[2];carriers[1]=squad[3];
    for(int i=0;i<2;++i)if(carriers[i]->isAlive())carriers[i]->startStickObject(cargoA,nullptr,i,1.0f);}
   static bool wasHeld=false;wasHeld|=held;
   if(wasHeld&&giant->getCreaturePointer(2)==nullptr){
    std::printf("P2_GIANT_ARENA_CONTEST released=1 tick=%d strength=1.5 carriers=2\n",phaseTick);
    phase=3;phaseTick=0;}
   return result;}
  case 3:{ // Hide-digest: carry home, hide underground, resurface healed.
   if(!cargoB&&giant->mStateID==3){ // wait for the post-contest cycle to finish before offering the digest pellet
    cargoB=pelletMgr->newNumberPellet(PELCOLOR_Red,0);require(cargoB,"digest pellet allocation");
    Vector3f forward;giant->outputDirectionVector(forward);
    Vector3f spot=giant->mSRT.t+forward*20.0f;spot.y=mapMgr->getMinY(spot.x,spot.z,true)+5.0f;
    cargoB->init(spot);cargoB->startAI(0);
   }
   if(!cargoB)return result;
   require(phaseTick<6000,"giant never carried digest pellet home");
   static bool hidden=false;
   bool heldB=giant->getCreaturePointer(2)==cargoB;
   if(!heldB&&giant->mStateID!=5&&giant->mStateID!=6&&giant->mStateID!=8&&giant->mStateID!=9&&phaseTick%60==0&&!hidden){ // re-bait until grabbed, camera nearby
    Vector3f forward;giant->outputDirectionVector(forward);
    Vector3f spot=giant->mSRT.t+forward*20.0f;spot.y=mapMgr->getMinY(spot.x,spot.z,true)+5.0f;
    cargoB->mSRT.t=spot;
    Vector3f cam=giant->mSRT.t+Vector3f(0,0,60);cam.y=mapMgr->getMinY(cam.x,cam.z,true);n->resetPosition(cam);
   }
   if(phaseTick==1){
    std::printf("P2_GIANT_ARENA_AI aidisabled=%d always=%d cullable=%d frozen=%u held_by=%d\n",int(giant->isCreatureFlag(CF_IsAiDisabled)),int(giant->isCreatureFlag(CF_AIAlwaysActive)),int(giant->aiCullable()),unsigned(giant->mIsFrozen),int(!giant->mHoldingCreature.isNull()));
   }
   if(giant->mStateID==9)hidden=true;
   static int lastState=-1;
   if(giant->mStateID!=lastState){int anims=giant->mTekiShape?giant->mTekiShape->mAnimMgr->countAnims():-2;
    std::printf("P2_GIANT_ARENA_STATE tick=%d state=%d motion=%d\n",phaseTick,giant->mStateID,giant->mTekiAnimator->getCurrentMotionIndex());lastState=giant->mStateID;}
   if(hidden&&giant->mStateID==3){ // fully resurfaced to wander
    require(giant->mHealth==2000.0f,"hide-digest did not restore health");
    std::printf("P2_GIANT_ARENA_DIGEST healed=1 health=%.1f tick=%d\n",giant->mHealth,phaseTick);
    phase=4;phaseTick=0;}
   return result;}
  case 4:{ // Defeat: purple presses to zero; digested treasure thrown back.
   if(phaseTick%10==1&&giant->mHealth>0){
    giant->eventPerformed(TekiEvent(TekiEventType::Pressed,giant,purple));++pressCount;}
   require(phaseTick<1200,"defeat phase stall");
   if(giant->mHealth<=0){std::printf("P2_GIANT_ARENA_DEFEAT_PRESS total_purple=%d\n",pressCount);phase=5;phaseTick=0;}
   return result;}
  case 5:{
   require(phaseTick<1200,"native death did not proceed after zero health");
   if(!giant->isAlive()){
    Pellet* found=nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);
     if(p&&p->isAlive()&&p!=cargoA&&p!=cargoB){float dx=p->mSRT.t.x-nestPos.x,dz=p->mSRT.t.z-nestPos.z;if(std::sqrt(dx*dx+dz*dz)<150)found=p;}}
    require(found,"digested treasure not thrown back at nest");
    std::printf("P2_GIANT_ARENA_THROWUP pellets=1 xyz=%.3f,%.3f,%.3f\n",found->mSRT.t.x,found->mSRT.t.y,found->mSRT.t.z);
    nestTeki->kill(false);phase=6;phaseTick=0;}
   return result;}
  case 6:{
   if(phaseTick>=30){capture("giant-actor-final.ppm");
    std::puts("PASS P2_GIANT_BREADBUG_ARENA spawn_identity press contest digest_heal defeat_throwup nest_linked");std::fflush(nullptr);std::_Exit(0);}
   return result;}
  }
  return result;
 }
};
int main(int argc,char** argv){SDL_setenv("SDL_AUDIODRIVER","dummy",1);std::setvbuf(stdout,nullptr,_IONBF,0);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"preview flag");if(!pc_window_init("Giant Breadbug actor arena",960,720))return 3;pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new GiantActorFixture());return 0;}
