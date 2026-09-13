// Private extension of the unchanged natural cargo fixture.
#define main cargo_fixture_unused_main
#include "cargo-base.inc"
#undef main
#include "pc_p2_breadbug_cargo_phase.h"
class BreadbugCargoAnimationFixture:public BreadbugCargoFixture {
 int observed=0,pauseTicks=0;bool pauseDone=false;float pausedCounter=0;
public:
 int idle() override {
  if(pauseTicks==60){gameflow.mPauseAll=false;pauseDone=true;pauseTicks=0;std::puts("P2_BREADBUG_ANIMATION_PAUSE_PASS frames=60 injected_engine_pause");}
  int result=BreadbugCargoFixture::idle();
  if(!tekiMgr)return result;Teki* actor=nullptr;Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator&&t->mGenerator->_70==186081)actor=t;}
  if(!actor||!actor->mTekiAnimator)return result;auto* anim=actor->mTekiAnimator;
  if(pauseTicks){require(anim->getCounter()==pausedCounter,"paused native animation advanced");++pauseTicks;return result;}
  int state=actor->mStateID;if(state!=5&&state!=6&&state!=8)return result;
  int motion=anim->getCurrentMotionIndex();bool matches=state==8?motion==TekiMotion::Type3:motion==TekiMotion::Move2;
  float start=0,end=0;if(matches&&state!=8){start=anim->getKeyValueByKeyType(0);end=anim->getKeyValueByKeyType(1);}
  auto selected=p2breadbugcargo::select(state,actor->getCreaturePointer(2)!=nullptr,matches,anim->getCounter(),anim->getFrameCount(),start,end);
  std::printf("P2_BREADBUG_ANIMATION_FRAME state=%d counter=%.6f kind=%d source=%.6f\n",state,anim->getCounter(),int(selected.kind),selected.frame);std::fflush(stdout);
  if(selected.kind==p2breadbugcargo::Hide&&++observed==1)capture("breadbug-hide-first.ppm");
  if(state==6&&selected.kind==p2breadbugcargo::Back&&!pauseDone){pausedCounter=anim->getCounter();gameflow.mPauseAll=true;pauseTicks=1;capture("breadbug-back-pause.ppm");std::puts("P2_BREADBUG_ANIMATION_PAUSE_BEGIN");}
  return result;
 }
};
int main(int argc,char** argv){SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);require(pc_pikipelago_room_preview(),"preview flag");if(!pc_window_init("Breadbug cargo animation comparison",960,720))return 3;pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new BreadbugCargoAnimationFixture());return 0;}
