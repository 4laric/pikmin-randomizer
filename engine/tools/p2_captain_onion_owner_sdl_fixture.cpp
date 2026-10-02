// #1166 offline P1 SDL switched-captain Onion ownership, ordinary save/load.
// Derived from #1130; no production state writes on the positive path.
#include <SDL2/SDL.h>
#include <GL/gl.h>
// MinGW's GL headers restore WIN32 after -UWIN32. Engine headers reserve
// that spelling for the incompatible legacy renderer; keep host _WIN32.
#if defined(_WIN32) && defined(WIN32)
#undef WIN32
#endif
#include "App.h"
#include "CPlate.h"
#include "Collision.h"
#include "GameCoreSection.h"
#include "GameStat.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "Section.h"
#include "BaseInf.h"
#include "PlayerState.h"
#include "pc_randomizer.h"
#include <filesystem>
#include <fstream>
#include "Graphics.h"
#include "MapMgr.h"
#include <cmath>
#include "Interactions.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "Pcam/Camera.h"
#include "Pcam/CameraManager.h"
#include "KeyConfig.h"
#include "pc_coop.h"
#include "pc_diary_observer.h"
#include "p2_purple_save_input.h"
// Captain-only extension. The shared Purple policy and its live fixture stay unchanged.
static PurpleSaveInput captain_save_input(bool dayAdvanced, const PcPauseSnapshot& pause,
                                         PcDiaryAction diary, const PcSaveUiSnapshot& save)
{
    const PurpleSaveInput original = purple_save_input(dayAdvanced, pause, diary, save);
    if (original != PurpleSaveInput::Neutral) return original;
    if (dayAdvanced && save.available && save.outerMemoryRouted && save.defaultFile.available
        && save.defaultFile.successful && save.defaultFile.typingComplete
        && save.defaultFile.confirmationReady) return PurpleSaveInput::Confirm;
    return PurpleSaveInput::Neutral;
}
#include "pc_whistle_observer.h"
#include "pc_onion_start_observer.h"
#include "Node.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiAI.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gfx.h"
#include "pc_gpu_preference.h"
#include "pc_p2_captain.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include "teki.h"
// Legacy inline UI helpers omit unused switch cases. Keep fixture warnings
// strict while allowing this unchanged production header's existing warnings.
#if defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wswitch"
#endif
#include "zen/DrawContainer.h"
#if defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

namespace {
SDL_Joystick* virtualPad=nullptr;
bool sForceCaptainDown = false;
bool sForceInactiveDown = false;

void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL P2_CAPTAIN_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}

// Fixture-only equivalent of root scripts/p2_fixture_captain_guard.h. CI is
// standalone native, so this observer carries the same fail-closed semantics.
void requireCaptain(Navi* n, int tick) {
    const float hp=n?n->mHealth:0;
    const bool dead=!n || !naviMgr || !n->getCurrState() || naviMgr->isNaviDead(n) || n->getCurrState()->getID()==NAVISTATE_Dead;
    if(!GameStat::orimaDead && !dead && std::isfinite(hp) && hp>1.0f)return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",tick,hp,int(GameStat::orimaDead),int(dead));
    std::fflush(nullptr);std::_Exit(86);
}

// Reusable P6 PPM capture after a real draw (mirrors the other room fixtures).
// Returns true (and writes the file) only when the captured frame is non-black,
// so a caller can retry across the setup fade-in.
bool capture(const char* path)
{
    pc_gfx_flush_batch();
    auto bind = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    require(bind != nullptr, "framebuffer entry point unavailable");
    GLint previous = 0; glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous); bind(GL_FRAMEBUFFER, 0);
    int width = 0, height = 0; SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &width, &height);
    std::vector<unsigned char> pixels(size_t(width) * size_t(height) * 3);
    glReadBuffer(GL_BACK); glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    bind(GL_FRAMEBUFFER, previous);
    bool visible = false; for (unsigned char value : pixels) visible |= value > 8;
    if (!visible) return false;
    FILE* file = std::fopen(path, "wb"); require(file != nullptr, "capture file");
    std::fprintf(file, "P6\n%d %d\n255\n", width, height);
    for (int y = height - 1; y >= 0; --y) std::fwrite(pixels.data() + size_t(y) * width * 3, 1, size_t(width) * 3, file);
    std::fclose(file);
    return true;
}




GameCoreSection* findCore(CoreNode* node,int depth=0){
    if(!node||depth>20)return nullptr;
    if(auto* c=dynamic_cast<GameCoreSection*>(node))return c;
    for(auto* c=node->Child();c;c=c->Next())if(auto* found=findCore(c,depth+1))return found;
    return nullptr;
}
bool resumePhase=false,forceNullState=false,forceMissingManager=false;
int storedCount(){int n=0;for(int c=0;c<3;++c)for(int m=0;m<3;++m)n+=pikiInfMgr.mPikiCounts[c][m];return n;}
int cards(){int n=0;const auto d=std::filesystem::path("../../campaign");if(std::filesystem::exists(d))for(auto& f:std::filesystem::directory_iterator(d))if(f.path().extension()==".sav")++n;return n;}
class CaptainSaveApp final:public PlugPikiApp {
    int frames=0,tick=-1,startDay=-1,initialCards=0;
    const std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
    bool dayAdvanced=false,resumeMenuLogged=false,withdrawQueued=false;
    int withdrawnFromTotal=-1;
    enum OwnerStage { Boot, InitialApproach, InitialWithdraw, InitialSettle, Deposit, SwitchOne, Withdraw, Settle, Owned };
    OwnerStage ownerStage=Boot;
    int ownerFrames=0, switchFrames=0, startupFrames=0, initialApproachFrames=0;
    bool initialApproachNeutral=false;
    std::vector<Piki*> startupBodies, ownedBodies, startupFreeBodies, startupWorkers, recalledWorkers, manualBornBodies;
    unsigned workerEventsRead=0, workerEpisodesRead=0, workerTerminalsRead=0;
    std::vector<unsigned> completedWorkerEpisodes;
    bool acquisitionNeeded=false, setupBSubmitted=false, setupBObserved=false, setupGatherObserved=false, setupRecruitmentObserved=false;
    bool menuSeen=false, menuConfirm=false;
    int menuFrames=0, diaryActions=0;
    bool releaseDiaryInput=false, pauseEvidenceCaptured=false;
    int pauseCaptureAttempts=0;
    bool diaryRevealObserved=false, diaryAdvanceObserved=false;
    PcDiaryAction lastDiaryAction=PcDiaryAction::Unavailable;
    void elapsed(const char* phase){std::printf("P2_SAVE_TIME phase=%s elapsed_ms=%lld\n",phase,(long long)std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-started).count());}
    bool saving=false,shot=false,sawWhistle=false,initialized[2]={false,false},retired=false;
    int teardownGapFrames=0;
    int controlStage=0;
    bool pendingNegative=false;
    void guardLiveState(){
        if(retired){require(!naviMgr && !pc_p2_captain::adapter(),"unexpected captain rebirth during bounded map gap");require(++teardownGapFrames<180,"bounded expected map transition gap");return;}
        if(!naviMgr && (initialized[0]||initialized[1])){
            // Only the actual quitter path may retire initialized captains:
            // exitStage unbinds the adapter and nulls NaviMgr, then queues map
            // selection and softReset after the native day advances.
            const bool actualExit=saving && !pc_p2_captain::adapter() && gsys->resetPending()
                && gameflow.mNextOnePlayerSectionID==ONEPLAYER_MapSelect
                && gameflow.mWorldClock.mCurrentDay==startDay+1;
            if(!actualExit)requireCaptain(nullptr,tick);
            retired=true;teardownGapFrames=0;
            std::puts("P2_SAVE_TEARDOWN actual_quitter_map_soft_reset=1 bounded_gap=180");return;
        }
        if(naviMgr)for(int i=0;i<2;++i){auto* n=naviMgr->getNavi(i);
            if(n&&n->getCurrState())initialized[i]=true;
            if(initialized[i])requireCaptain(n,tick);
        }
    }
    void pad(unsigned keys=0,int x=0,int y=0){
        const int id=SDL_JoystickInstanceID(virtualPad);int selected=-1;
        if(pc_window_input_get_assignment(0,&selected)!=PC_INPUT_DEV_GAMEPAD||selected!=id){pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,id);pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);}
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_B,(keys&KBBTN_B)!=0);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_START,(keys&KBBTN_START)!=0);
        SDL_JoystickSetVirtualButton(virtualPad,SDL_CONTROLLER_BUTTON_DPAD_UP,(keys&KBBTN_DPAD_UP)!=0);
        SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*32767/74));
        SDL_JoystickSetVirtualAxis(virtualPad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*32767/74));SDL_JoystickUpdate();
    }
    void selected(int slot){auto* n=naviMgr->getNavi(slot);require(naviMgr->getActiveNavi()==n,"selected captain");require(cameraMgr->mController==n->mKontroller && cameraMgr->mCamera->mTargetCreature==n,"camera binding");std::printf("P2_SAVE_SELECTED phase=%s slot=%d camera=1\n",resumePhase?"resume":"save",slot);}
    int liveCount(){int n=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++n;}return n;}
    // validSlot observes the used-slot boundary without accessing protected layout.
    // More occupied slots than live Pikmin fails the observation immediately.
    int plateCount(Navi* n){require(n&&n->mPlateMgr,"captain plate exists");int limit=liveCount();for(int i=0;i<=limit;++i)if(!n->mPlateMgr->validSlot(i))return i;require(false,"plate exceeds live population");return -1;}
    std::vector<Piki*> liveBodies(){
        std::vector<Piki*> bodies;Iterator it(pikiMgr);CI_LOOP(it){
            auto* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
            require(std::find(bodies.begin(),bodies.end(),p)==bodies.end(),"unique live body enumeration");bodies.push_back(p);
        }return bodies;
    }
    void sameBodies(const std::vector<Piki*>& expected){
        const auto current=liveBodies();require(current.size()==expected.size(),"same actual live body count");
        for(auto* p:current)require(std::find(expected.begin(),expected.end(),p)!=expected.end(),"same actual live body identities");
    }
    PcTransportObservation transportTarget(Piki* p){
        auto* top=p->mActiveAction;
        require(top && top->mChildActions && top->mCurrActionIdx==PikiAction::Transport && top->mCurrActionIdx>=0 && top->mCurrActionIdx<top->mChildCount,"valid transport table index");
        const Action* action=top->mChildActions[top->mCurrActionIdx].mAction;
        require(action && action->mPiki==p,"transport action belongs to this body");
        const auto* transport=dynamic_cast<const ActTransport*>(action);
        require(transport!=nullptr,"actual transport action type");
        const auto target=transport->pcTransportObservation();
        require(target.valid() && target.actor==reinterpret_cast<uintptr_t>(p),"actual live member pellet target");return target;
    }
    size_t workerBody(uintptr_t actor){
        auto it=std::find_if(startupBodies.begin(),startupBodies.end(),[&](Piki* p){return reinterpret_cast<uintptr_t>(p)==actor;});
        require(it!=startupBodies.end(),"worker episode belongs to original body");return size_t(it-startupBodies.begin());
    }
    const PcWorkerEpisode& workerEpisode(unsigned id,uintptr_t actor,uintptr_t target){
        require(id>0 && id<=workerEpisodesRead,"worker episode has observed begin");
        const auto& e=pc_worker_episodes[id-1];
        require(e.id==id && e.actor==actor && e.target.target==target,"exact worker task/body/target continuity");
        require(std::find(completedWorkerEpisodes.begin(),completedWorkerEpisodes.end(),id)==completedWorkerEpisodes.end(),"one resolution per task episode");
        return e;
    }
    void consumeWorkerEvents(){
        require(!pc_worker_observer_overflow,"worker event ring not overflowed");
        while(workerEpisodesRead<pc_worker_episode_count){
            const auto& e=pc_worker_episodes[workerEpisodesRead++];
            require(e.id==workerEpisodesRead && e.action && e.target.valid() && e.target.visible && !e.target.atGoal,"safe observed native task begin");
            std::printf("P2_ONION_WORKER_EPISODE episode=%u body_token=%zu target_token=%llu\n",e.id,workerBody(e.actor),(unsigned long long)e.target.target);
        }
        while(workerEventsRead<pc_worker_observer_count){
            const auto event=pc_worker_observer_events[workerEventsRead++];
            require(event.eligible() && event.nativeResult(),"actual call-time worker eligibility/result");
            workerEpisode(event.episode,event.actor,event.target.target);
            completedWorkerEpisodes.push_back(event.episode);
            const size_t token=workerBody(event.actor);recalledWorkers.push_back(startupBodies[token]);
            std::printf("P2_ONION_WORKER_RECALL episode=%u body_token=%zu target_token=%llu held_seconds=%.6f distance=%.6f radius=%.6f instant=%d after_mode=%d after_state=%d accepted=1\n",event.episode,token,(unsigned long long)event.target.target,event.heldSeconds,event.distance,event.radius,int(event.instant),event.afterMode,event.afterState);
        }
        while(workerTerminalsRead<pc_worker_terminal_count){
            const auto& event=pc_worker_terminals[workerTerminalsRead++];
            require(event.eligible(),"only exact live-visible nongGoal slot-failure natural Formation allowed");
            const auto& e=workerEpisode(event.episode,event.actor,event.after.target);
            require(e.action==event.action,"actual terminal action matches episode");
            completedWorkerEpisodes.push_back(event.episode);
            std::printf("P2_ONION_WORKER_NATURAL episode=%u body_token=%zu target_token=%llu reason=%d result=%d before_visible=1 after_visible=1 before_goal=0 after_goal=0 captain=%d mode=%d joined=1 accepted=1\n",event.episode,workerBody(event.actor),(unsigned long long)event.after.target,event.reason,event.result,event.captain,event.mode);
        }
    }
    // Explicit fresh-save setup, never evidence of automatic startup ownership.
    // Only SDL input recruits; no direct callPikis, actor, cursor or stock writes.
    bool acquireStartup(Navi* a,Navi* b){
        require(!resumePhase && naviMgr->getActiveNavi()==a,"fresh captain0 acquisition only");
        require(liveCount()==20 && storedCount()==0,"startup actual live20 stock0");
        if(startupBodies.empty()){
            startupBodies=liveBodies();require(startupBodies.size()==20,"startup twenty unique bodies");
            acquisitionNeeded=!(formation(a)==20 && formation(b)==0 && plateCount(a)==20 && plateCount(b)==0);
            // Read all actual starting bodies before applying the narrower work refusal policy.
            for(size_t i=0;i<startupBodies.size();++i){auto* body=startupBodies[i];const Vector3f pos=body->getPosition();
                std::printf("P2_ONION_STARTUP_INITIAL body_token=%zu address=%p mode=%d state=%d action=%d owner=%d position=%.3f,%.3f,%.3f\n",i,static_cast<void*>(body),int(body->mMode),body->getState(),body->mActiveAction?body->mActiveAction->mCurrActionIdx:-1,body->mNavi?body->mNavi->mNaviID:-1,pos.x,pos.y,pos.z);
            }
            pc_worker_observer_begin();
            elapsed("startup_acquisition_begin");
            std::puts("P2_ONION_STARTUP_ACQUIRE disclosed_setup=1 automatic_ownership_claim=0 input_player=1 captain=0");
        }
        sameBodies(startupBodies);consumeWorkerEvents();require(++startupFrames<=180,"bounded180-frame ordinary startup acquisition");
        // Observe engine-consumed input and a subsequent real Free -> Formation change.
        // Submitted SDL state alone never qualifies as an observed recruitment.
        if(setupBSubmitted && a->mKontroller && a->mKontroller->keyClick(KBBTN_B))setupBObserved=true;
        if(setupBObserved && a->getCurrState()->getID()==NAVISTATE_Gather)setupGatherObserved=true;
        for(auto* p:startupBodies){
            if(setupBObserved && setupGatherObserved && p->mMode==PikiMode::FormationMode && p->mNavi==a
                && std::find(startupFreeBodies.begin(),startupFreeBodies.end(),p)!=startupFreeBodies.end())setupRecruitmentObserved=true;
            if(p->mMode==PikiMode::FormationMode && p->mNavi==a && std::find(recalledWorkers.begin(),recalledWorkers.end(),p)!=recalledWorkers.end())setupRecruitmentObserved=true;
            if(p->mMode==PikiMode::FreeMode && std::find(startupFreeBodies.begin(),startupFreeBodies.end(),p)==startupFreeBodies.end())startupFreeBodies.push_back(p);
        }
        const bool complete=formation(a)==20 && formation(b)==0 && plateCount(a)==20 && plateCount(b)==0;
        if(complete){
            pad(); // Release whistle before actual deposit; observe ordinary state recovery.
            if(a->getCurrState()->getID()!=NAVISTATE_Walk && a->getCurrState()->getID()!=NAVISTATE_Idle)return false;
            require(!acquisitionNeeded || (setupBObserved && setupGatherObserved && setupRecruitmentObserved),"needed acquisition requires observed B/Gather and actual recruitment");
            require(acquisitionNeeded || (!setupBSubmitted && !setupBObserved && !setupGatherObserved && !setupRecruitmentObserved),"already assembled makes no SDL recruitment claim");
            std::printf("P2_ONION_STARTUP_ACQUIRED frames=%d unique=20 live=20 stored=0 owner0=20 owner1=0 plate0=20 plate1=0 acquisition_needed=%d observed_B=%d observed_Gather=%d observed_recruitment=%d via_ordinary_SDL=%d\n",startupFrames,int(acquisitionNeeded),int(setupBObserved),int(setupGatherObserved),int(setupRecruitmentObserved),int(acquisitionNeeded && setupBObserved && setupGatherObserved && setupRecruitmentObserved));
            require(completedWorkerEpisodes.size()==pc_worker_episode_count,"every observed Transport task episode has exact native resolution");
            std::printf("P2_ONION_WORKER_SETUP needed=%u observed=%zu recalls=%u natural=%u original_unique=20\n",pc_worker_episode_count,completedWorkerEpisodes.size(),workerEventsRead,workerTerminalsRead);
            pc_worker_observer_end();
            return true;
        }
        Piki* target=nullptr;float nearest=1.0e30f;
        for(size_t i=0;i<startupBodies.size();++i){auto* p=startupBodies[i];
            const Vector3f delta=p->getPosition()-a->getPosition();const float d2=delta.x*delta.x+delta.z*delta.z;
            const Vector3f cursor=p->getPosition()-a->mCursorWorldPos;
            if(startupFrames==1 || startupFrames%30==0)std::printf("P2_ONION_STARTUP_BODY frame=%d body_token=%zu address=%p generator_id=%u mode=%d state=%d action=%d owner=%d callable=%d rope=%d navi_distance=%.3f cursor_distance=%.3f\n",
                startupFrames,i,static_cast<void*>(p),unsigned(p->getGeneratorID()),int(p->mMode),p->getState(),p->mActiveAction?p->mActiveAction->mCurrActionIdx:-1,p->mNavi?p->mNavi->mNaviID:-1,int(p->mIsCallable),int(p->mRope!=nullptr),std::sqrt(d2),std::sqrt(cursor.x*cursor.x+cursor.z*cursor.z));
            // Wait for genuine exit/LookAt transitions; do not substitute a new body.
            require(p->mMode==PikiMode::FreeMode || p->mMode==PikiMode::FormationMode || p->mMode==PikiMode::ExitMode || p->mMode==PikiMode::TransportMode,"startup mode outside reviewed native recall contract");
            if(p->mMode==PikiMode::TransportMode && p->getState()!=PIKISTATE_LookAt){
                require(!pc_vs_active() && p->isAlive() && p->mIsCallable && !p->isBuried() && !p->isKinoko() && !p->isFired() && !p->isDamaged() && !p->mRope && p->getState()==PIKISTATE_Normal,"safe ordinary transport recall body");
                const auto targetFacts=transportTarget(p);
                if(std::find(startupWorkers.begin(),startupWorkers.end(),p)==startupWorkers.end()){
                    startupWorkers.push_back(p);
                    const Vector3f pos=p->getPosition();const Vector3f captainPos=a->getPosition();
                    std::printf("P2_ONION_WORKER_SETUP_BEGIN body_token=%zu body_pos=%.3f,%.3f,%.3f captain_pos=%.3f,%.3f,%.3f target_token=%llu target_generator=%u target_pos=%.3f,%.3f,%.3f transport_state=%d disclosed_worker_recall=1\n",i,pos.x,pos.y,pos.z,captainPos.x,captainPos.y,captainPos.z,(unsigned long long)targetFacts.target,targetFacts.generator,targetFacts.x,targetFacts.y,targetFacts.z,targetFacts.state);
                }
            }
            // LookAt has already received the native whistle. It remains FreeMode
            // until its reaction animation finishes; callPikis excludes it too.
            // Approach an uncalled body instead, or release input and await cleanup.
            if((p->mMode==PikiMode::FreeMode || p->mMode==PikiMode::TransportMode) && p->getState()!=PIKISTATE_LookAt && p->mIsCallable && !p->mRope && d2<nearest){nearest=d2;target=p;}
        }
        if(!target){pad();return false;}
        // The same camera-relative left-stick transform used by onionMenu.
        // Aim by walking toward the observed body, never writing cursor/world position.
        const Vector3f delta=target->getPosition()-a->getPosition();const float d=std::sqrt(nearest);
        require(a->controlCamera()!=nullptr,"startup camera basis exists");
        const Vector3f axis=a->controlCamera()->mViewXAxis;
        const int x=d>30?int(55*(delta.x*axis.x+delta.z*axis.z)/d):0;
        const int y=d>30?int(55*(delta.x*axis.z-delta.z*axis.x)/d):0;
        // Walk enters Gather on keyClick; release two frames per cycle so an
        // Idle wake cannot consume the only B edge. Hold grows the real radius.
        if(startupFrames%30<28)setupBSubmitted=true;
        pad(startupFrames%30<28?KBBTN_B:0,x,y);
        return false;
    }
    int formation(Navi* n){int count=0;Iterator it(pikiMgr);CI_LOOP(it){auto* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mMode==PikiMode::FormationMode&&p->mNavi==n)++count;}return count;}
    void owned(const char* stage){
        auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);
        require(liveCount()==20&&storedCount()==0,"owned field20 stock0");
        require(ownedBodies.size()==20,"withdrawal twenty unique bodies recorded");sameBodies(ownedBodies);
        require(formation(a)==0&&formation(b)==20,"all20 actual formation owner captain1");
        require(a->mPlateMgr&&b->mPlateMgr&&plateCount(a)==0&&plateCount(b)==20,"CPlate agrees with observed ownership");
        if(stage)std::printf("P2_ONION_OWNER stage=%s owner0=0 owner1=20 plate0=0 plate1=20 live=20 stored=0 input_player=1 switched_captain=1\n",stage);
    }
    // Read-only startup observation, capped at twenty records per process.
    // Missing objects are reported, never created or repaired by telemetry.
    void bootTelemetry(){
        if(tick>=0 || (frames!=1 && frames%60!=0) || frames>1140)return;
        auto* a=naviMgr?naviMgr->getNavi(0):nullptr;
        auto* b=naviMgr?naviMgr->getNavi(1):nullptr;
        const int live=pikiMgr?liveCount():-1;
        auto plate=[live](Navi* n){
            if(!n || !n->mPlateMgr || live<0)return -1;
            for(int i=0;i<=live;++i)if(!n->mPlateMgr->validSlot(i))return i;
            return live+1; // Observed overflow sentinel; no ownership assertion here.
        };
        std::printf("P2_ONION_BOOT frame=%d ready=%d paused=%d overlay=%d movie=%d initialized0=%d initialized1=%d state0=%d state1=%d live=%d stored=%d formation0=%d formation1=%d plate0=%d plate1=%d owner_stage=%d\n",
            frames,int(pc_randomizer_ready()),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),
            int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive),int(initialized[0]),int(initialized[1]),
            a&&a->getCurrState()?a->getCurrState()->getID():-1,b&&b->getCurrState()?b->getCurrState()->getID():-1,
            live,storedCount(),pikiMgr&&a?formation(a):-1,pikiMgr&&b?formation(b):-1,plate(a),plate(b),int(ownerStage));
        std::fflush(stdout);
    }
    bool initialOnionEligible(Navi* n){
        auto* onion=itemMgr?itemMgr->getContainer(pc_randomizer_start_color()):nullptr;
        require(onion && onion->mCollInfo && !pc_p2_preview_is_pod(onion),"actual initial Onion collision");
        const auto* coll=onion->mCollInfo->getSphere('cont');require(coll,"initial cont sphere");
        const float radius=n->getSize()+coll->mRadius;const Vector3f diff=coll->mCentre-n->getCentre();
        require(std::isfinite(radius)&&radius>0&&std::isfinite(diff.length()),"finite initial eligibility geometry");
        bool busy=false;
        for(int i=0;i<naviMgr->getNaviCount();++i){auto* other=naviMgr->getNavi(i);if(other&&other!=n&&other->getCurrState()&&other->getCurrState()->getID()==NAVISTATE_Container&&other->mGoalItem==onion)busy=true;}
        return n->getCurrState()->getID()==NAVISTATE_Walk && !n->mStickListHead && !playerState->inDayEnd() && !gameflow.mPauseAll
            && !(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) && !busy && !n->roughCulling(onion,radius*1.5f) && diff.length()<=radius;
    }
    bool initialIterableNeutral=false;
    int initialIterableCount(Navi* n){
        require(n && n->mPlateMgr,"initial iterable plate exists");
        std::vector<Piki*> seen;
        int index=n->mPlateMgr->getFirst();
        for(int steps=0;steps<=20;++steps){
            require(index>=0 && index<=20,"bounded native plate iterator index");
            if(n->mPlateMgr->isDone(index))return int(seen.size());
            require(steps<20 && n->mPlateMgr->validSlot(index),"native iterable fits actual used slots and original20");
            auto* p=static_cast<Piki*>(n->mPlateMgr->getCreature(index));
            require(p && std::find(manualBornBodies.begin(),manualBornBodies.end(),p)!=manualBornBodies.end(),"iterable pointer belongs to original living withdrawal bodies");
            require(std::find(seen.begin(),seen.end(),p)==seen.end(),"native iterable has no duplicate body");
            require(p->isAlive() && p->mHealth>0.0f && p->mColor==pc_randomizer_start_color()
                && p->getState()==PIKISTATE_Normal && p->mMode==PikiMode::FormationMode && p->mNavi==n,"native iterable healthy original color and owner");
            seen.push_back(p);
            const int next=n->mPlateMgr->getNext(index);require(next>index,"native iterator advances");index=next;
        }
        require(false,"bounded native iterator termination");return -1;
    }
    bool onionInputHeld=false;
    unsigned onionInputObservations=0;
    void onionMenu(Navi* n,int target){
        require(naviMgr->getActiveNavi()==n,"Onion input owner is selected captain");
        require(!pc_vs_active(),"offline ordinary Onion fixture");
        auto* onion=itemMgr?itemMgr->getContainer(pc_randomizer_start_color()):nullptr;require(onion,"real starting Onion");
        require(!pc_p2_preview_is_pod(onion),"actual Onion not Research Pod");
        if(n->getCurrState()->getID()==NAVISTATE_Container){
            require(containerWindow && n->mGoalItem==onion,"ordinary offline selected Onion UI");
            const int state=containerWindow->getStatus(), squad=containerWindow->getMyPikiDisp();
            if(!menuSeen){
                if(ownerStage==Deposit){
                    const int iterable=initialIterableCount(n);
                    std::printf("P2_ONION_DEPOSIT_INITIAL displayed=%d iterable=%d used=%d formation=%d live=%d stored=%d\n",squad,iterable,plateCount(n),formation(n),liveCount(),storedCount());
                    require(squad==20 && iterable==20 && plateCount(n)==20 && formation(n)==20 && liveCount()==20 && storedCount()==0,"initial deposit menu exposes all original20 before any selection");
                }
                menuSeen=true;onionInputHeld=false;elapsed(target?"withdraw_menu_open":"deposit_menu_open");
            }
            if(onionInputObservations++<240)std::printf("P2_ONION_MENU_INPUT captain=%d target=%d displayed=%d stock=%d live=%d state=%d held=%08x pressed=%08x axis_y=%.3f release_next=%d\n",n->mNaviID,target,squad,storedCount(),liveCount(),state,unsigned(n->mKontroller->mCurrentInput),unsigned(n->mKontroller->mInputPressed),double(n->mKontroller->mMainStickY),int(onionInputHeld));
            require(squad>=0&&squad<=20,"ordinary menu selection bounded20");
            if(state!=zen::DrawContainer::STATE_Operation){pad();onionInputHeld=false;menuConfirm=false;return;}
            if(onionInputHeld){pad();onionInputHeld=false;return;} // One engine tick of release between every stick/A edge.
            if(squad==target){pad(menuConfirm?KBBTN_A:0);onionInputHeld=menuConfirm;menuConfirm=true;}
            else{menuConfirm=false;pad(0,0,squad<target?-65:65);onionInputHeld=true;}
        }else if(!menuSeen){
            require(onion->mCollInfo && n->controlCamera(),"actual Onion collision and camera available");
            const auto* coll=onion->mCollInfo->getSphere('cont');require(coll,"actual Onion cont sphere");
            const Vector3f centre=n->getCentre(), goal=coll->mCentre, diff=goal-centre;
            const float radius=n->getSize()+coll->mRadius, distance=diff.length();
            require(std::isfinite(radius)&&radius>0&&std::isfinite(distance),"finite actual interaction geometry");
            const bool culled=n->roughCulling(onion,radius*1.5f);
            bool busy=false;
            for(int i=0;i<naviMgr->getNaviCount();++i){auto* other=naviMgr->getNavi(i);if(other&&other!=n&&other->getCurrState()&&other->getCurrState()->getID()==NAVISTATE_Container&&other->mGoalItem==onion)busy=true;}
            const bool blocked=n->mStickListHead || playerState->inDayEnd() || gameflow.mPauseAll || (gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) || busy;
            const bool inRange=!culled && distance<=radius;
            if(onionInputObservations++<240)std::printf("P2_ONION_APPROACH captain=%d state=%d centre=%.3f,%.3f,%.3f target=%.3f,%.3f,%.3f distance=%.3f radius=%.3f culled=%d busy=%d blocked=%d in_range=%d held=%08x pressed=%08x\n",n->mNaviID,n->getCurrState()->getID(),centre.x,centre.y,centre.z,goal.x,goal.y,goal.z,distance,radius,int(culled),int(busy),int(blocked),int(inRange),unsigned(n->mKontroller->mCurrentInput),unsigned(n->mKontroller->mInputPressed));
            if(blocked){pad();onionInputHeld=false;return;}
            if(inRange){pad(onionInputHeld?0:KBBTN_A);onionInputHeld=!onionInputHeld;return;}
            onionInputHeld=false;
            const float dx=goal.x-centre.x,dz=goal.z-centre.z,d=std::sqrt(dx*dx+dz*dz);
            if(d<=0.001f){pad();return;} // No invented vertical movement; bounded diagnostics identify an unreachable height.
            const Vector3f axis=n->controlCamera()->mViewXAxis;
            pad(0,int(65*(dx*axis.x+dz*axis.z)/d),int(65*(dx*axis.z-dz*axis.x)/d));
        }else{pad();onionInputHeld=false;}
    }

public:
    CaptainSaveApp(){initialCards=cards();require(resumePhase?initialCards==1:initialCards==0,"expected committed generation before phase");}
    void draw(Graphics& gfx)override{PlugPikiApp::draw(gfx);if(tick>=0&&!shot)shot=capture("captain-campaign.ppm");if(saving&&!dayAdvanced&&!pauseEvidenceCaptured){
            const PcPauseSnapshot pause=pc_pause_observe();
            if(pause.available&&pause.mainInputReady){
                require(++pauseCaptureAttempts<=60,"bounded rendered ready-pause capture attempts");
                pauseEvidenceCaptured=capture("pause-menu.ppm");
                std::printf("P2_ONION_PAUSE_CAPTURE attempt=%d ready=1 state=%d selected=%d captured=%d\n",pauseCaptureAttempts,pause.state,pause.mainSelection,int(pauseEvidenceCaptured));
                if(pauseEvidenceCaptured)elapsed("ready_pause_render_captured");
            }
        }if(resumePhase&&withdrawQueued&&frames%240==0){const std::string path="onion-menu-"+std::to_string(frames)+".ppm";require(capture(path.c_str()),"ordinary Onion menu capture");}}
    int idle()override{
        if(pendingNegative){
            // Queue mutation until the next ordinary pre-engine guard. This
            // avoids rendering a deliberately null state before that guard.
            auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);
            if(forceNullState)b->mCurrState=nullptr;
            else if(forceMissingManager)naviMgr=nullptr;
            else (sForceInactiveDown?b:a)->mHealth=0;
            pendingNegative=false;
        }
        guardLiveState(); // also protects the engine from negative null-state setup
        const int result=PlugPikiApp::idle();require(++frames<7200,"frame bound");
        guardLiveState(); // never bypass initialized actors for movie/readiness/pause
        bootTelemetry(); // Before every positive readiness early-return path.
        if(!saving && tick<0 && initialized[0] && initialized[1]
            && (sForceCaptainDown||sForceInactiveDown||forceNullState||forceMissingManager)){
            // Both actual initialized actors just passed the ordinary guards.
            // Queue only the explicit negative; mutate at the next pre-engine guard.
            std::puts("P2_ONION_NEGATIVE_QUEUED initialized0=1 initialized1=1 before_positive_boot=1");
            std::fflush(stdout);
            pendingNegative=true;gameflow.mPauseAll=TRUE;return result;
        }

        if(resumePhase&&tick<0&&!withdrawQueued){
            const bool menu=!naviMgr||gameflow.mIsUIOverlayActive;
            if(menu&&!resumeMenuLogged){resumeMenuLogged=true;std::puts("P2_SAVE_RESUME_MENU ordinary_A_input=1 area_day_injected=0");}
            pad(menu&&frames%20<4?KBBTN_A:0);
        }
        if(saving){
            // Existing value-only UI snapshots gate ordinary SDL edges. Native
            // fades, movies, results and card writes retain their own timing.
            const bool confirming=gameflow.mWorldClock.mCurrentDay==startDay+1;
            if(confirming&&!dayAdvanced){dayAdvanced=true;elapsed("day_advanced");}
            const PcPauseSnapshot pause=pc_pause_observe();
            const PcDiaryAction diary=confirming?pc_diary_observe():PcDiaryAction::Unavailable;
            const PcSaveUiSnapshot save=confirming?pc_save_ui_observe():PcSaveUiSnapshot{};
            const PurpleSaveInput intent=captain_save_input(confirming,pause,diary,save);
            require(intent!=PurpleSaveInput::Unexpected,"unexpected pause/save selection refuses ordinary confirmation");
            ++menuFrames;
            { // Every observed frame, including neutral transitions and nested waits.
                std::printf("P2_ONION_SAVE_UI frame=%d day_advanced=%d pause_available=%d pause_state=%d main_ready=%d main_selected=%d sunset_ready=%d sunset_selected=%d diary=%d result_available=%d result_state=%d save_state=%d results_ready=%d primary_ready=%d primary_yes=%d secondary_ready=%d slot_ready=%d slot=%d nested_blocked=%d failure_available=%d failure_inactive=%d file_available=%d file_state=%d memory_available=%d memory_routed=%d memory_state=%d default_available=%d default_state=%d default_success=%d default_typing=%d default_ready=%d intent=%d release=%d\n",
                    menuFrames,int(confirming),int(pause.available),pause.state,int(pause.mainInputReady),pause.mainSelection,int(pause.sunsetInputReady),pause.subSelection,int(diary),int(save.available),save.resultState,save.saveState,int(save.resultsInputReady),int(save.primaryInputReady),int(save.primaryYes),int(save.secondaryInputReady),int(save.cardSlotInputReady),save.cardSlot,int(save.nestedUiBlocked),int(save.failureAvailable),int(save.failureInactive),int(save.fileAvailable),save.fileState,int(save.memoryAvailable),int(save.outerMemoryRouted),save.defaultFile.memoryState,int(save.defaultFile.available),save.defaultFile.state,int(save.defaultFile.successful),int(save.defaultFile.typingComplete),int(save.defaultFile.confirmationReady),int(intent),int(releaseDiaryInput));
                elapsed("ordinary_save_ui_observed");
            }
            if(!confirming&&!pauseEvidenceCaptured){
                // draw() must capture the actual ready pause before any menu edge.
                // This neutral wait cannot skip a fade or leave the menu early.
                pad();releaseDiaryInput=false;return result;
            }
            if(diary!=lastDiaryAction){
                std::printf("P2_ONION_DIARY observed=%d elapsed_stage=diary_eligibility\n",int(diary));
                elapsed("diary_eligibility_changed");lastDiaryAction=diary;
            }
            if(releaseDiaryInput){pad();releaseDiaryInput=false;}
            else if(intent!=PurpleSaveInput::Neutral){
                const bool reveal=intent==PurpleSaveInput::RevealDiary;
                const bool advance=intent==PurpleSaveInput::AdvanceDiary;
                if(reveal || advance){
                    require(++diaryActions<240,"bounded ordinary diary actions");
                    diaryRevealObserved|=reveal;diaryAdvanceObserved|=advance;
                    std::printf("P2_ONION_DIARY input=%s observed=%d action=%d ordinary_SDL=1\n",reveal?"B":"A",int(diary),diaryActions);
                }
                if(intent==PurpleSaveInput::Down)pad(0,0,-65);
                else if(intent==PurpleSaveInput::Up)pad(0,0,65);
                else pad(reveal?KBBTN_B:KBBTN_A);
                releaseDiaryInput=true; // Next normal engine update must consume release before another edge.
            }else pad();
            if(!confirming){
                if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive)gameflow.mMoviePlayer->requestSkip();
                return result;
            }
            if(cards()==initialCards+1 && gameflow.mWorldClock.mCurrentDay==startDay+1){
                require(diaryRevealObserved&&diaryAdvanceObserved,"observed actual diary reveal and advance inputs");
                elapsed("native_commit_observed");
                std::printf("PASS P2_CAPTAIN_ONION_OWNER_SAVE day_before=%d day_after=%d native_card_generation_count=%d scripted_sunset=1 scripted_results_input=1 saved_bytes_injected=0\n",startDay,gameflow.mWorldClock.mCurrentDay,cards());std::fflush(nullptr);std::_Exit(0);
            }
            require(cards()<=initialCards+1,"unexpected extra checkpoint");
        }
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(saving)return result;
        if(!pc_randomizer_enabled()||!pc_randomizer_ready()||!naviMgr||!naviMgr->getActiveNavi()||(gameflow.mPauseAll && !withdrawQueued)||(gameflow.mIsUIOverlayActive && !withdrawQueued))return result;
        auto* a=naviMgr->getNavi(0);auto* b=naviMgr->getNavi(1);require(a&&b,"two campaign captains");
        if(!a->getCurrState()||!b->getCurrState())return result; // Initial startup readiness; initialized guards above fail closed.
        if(tick<0){
            require(pc_randomizer_resumed()==resumePhase,"actual production campaign load state");
            int live=liveCount();
            if(ownerStage==Boot){
                const int state0=a->getCurrState()->getID(),state1=b->getCurrState()->getID();
                const bool resting0=state0==NAVISTATE_Walk || state0==NAVISTATE_Idle;
                const bool resting1=state1==NAVISTATE_Walk || state1==NAVISTATE_Idle;
                if(!resting1 || (!resting0 && !(startupFrames>0 && state0==NAVISTATE_Gather)))return result;
                require(live==0 && storedCount()==20,"actual manual-start/resume stock20 field0");
                require(a->mPlateMgr && b->mPlateMgr,"initialized captain formation plates");
                require(formation(a)==0 && formation(b)==0 && plateCount(a)==0 && plateCount(b)==0,"initial stock has no field owners");
                startDay=gameflow.mWorldClock.mCurrentDay;
                withdrawnFromTotal=live+storedCount();require(withdrawnFromTotal==20,"actual total20 baseline");
                selected(0);withdrawQueued=true;elapsed("ownership_boot");
                if(!resumePhase){
                    const char* manual=std::getenv("PIKMIN_RANDOMIZER_MANUAL_START");
                    require(manual && std::string(manual)=="1","explicit production manual-start binding");
                    std::puts("P2_ONION_MANUAL_START live=0 stored=20 owner0=0 owner1=0 plate0=0 plate1=0 ordinary_UI_next=1");
                    pc_worker_observer_begin();pc_onion_start_begin(); // Before first ordinary input and first native birth.
                    ownerStage=InitialApproach;menuSeen=false;menuConfirm=false;
                }else ownerStage=SwitchOne;
            }
            if(ownerStage==InitialApproach){
                require(!resumePhase && ++initialApproachFrames<=180,"bounded180-frame ordinary initial Onion approach");
                require(live==0 && storedCount()==20 && formation(a)==0 && formation(b)==0 && plateCount(a)==0 && plateCount(b)==0,"approach preserves actual stock20 field0");
                require(pc_onion_start_enabled && !pc_onion_start_failed && pc_onion_start_count==0 && pc_onion_start_events==0,"no native births or action entries before withdrawal");
                require(pc_worker_observer_enabled && !pc_worker_observer_overflow && pc_worker_episode_count==0 && pc_worker_observer_count==0 && pc_worker_terminal_count==0,"no work before withdrawal");
                require(naviMgr->getActiveNavi()==a && a->mKontroller,"selected initialized captain0 approaches");
                require(a->getCurrState()->getID()!=NAVISTATE_Container,"no initial menu before explicit approach boundary");
                if(initialOnionEligible(a)){
                    const bool neutral=a->mKontroller->mCurrentInput==0 && a->mKontroller->mMainStickX==0 && a->mKontroller->mMainStickY==0;
                    pad();onionInputHeld=false;
                    if(!initialApproachNeutral || !neutral){initialApproachNeutral=true;return result;}
                    auto* onion=itemMgr->getContainer(pc_randomizer_start_color());const auto* coll=onion->mCollInfo->getSphere('cont');const Vector3f centre=a->getCentre();
                    std::printf("P2_ONION_APPROACH_BOUNDARY frames=%d limit=180 selected=0 live=0 stored=20 history_bodies=0 history_events=0 neutral=1 eligible=1 distance=%.3f radius=%.3f centre=%.3f,%.3f,%.3f\n",initialApproachFrames,(coll->mCentre-centre).length(),a->getSize()+coll->mRadius,centre.x,centre.y,centre.z);
                    elapsed("initial_approach_boundary");ownerStage=InitialWithdraw;return result;
                }
                initialApproachNeutral=false;onionMenu(a,20);return result;
            }
            if(ownerStage==InitialWithdraw || ownerStage==InitialSettle){
                require(!resumePhase,"initial captain0 withdrawal is fresh-only");
                require(++startupFrames<=180,"bounded180-frame ordinary initial Onion withdrawal");
                require(live<=20 && live+storedCount()==20,"initial UI withdrawal conserves total20");
                std::printf("P2_ONION_START_HISTORY frames=%d bodies=%u events=%u failed=%d bad_actor=%llu bad_action=%d\n",startupFrames,pc_onion_start_count,pc_onion_start_events,int(pc_onion_start_failed),(unsigned long long)pc_onion_start_bad_actor,pc_onion_start_bad_action);
                require(pc_onion_start_enabled && !pc_onion_start_failed,"continuous native initial Exit-to-Crowd history");
                require(pc_worker_observer_enabled && !pc_worker_observer_overflow && pc_worker_episode_count==0 && pc_worker_observer_count==0 && pc_worker_terminal_count==0,"no initial Transport episode or recall");
                const auto born=liveBodies();
                for(auto* p:born)require(p->getState()==PIKISTATE_Normal && (p->mMode==PikiMode::ExitMode || (p->mMode==PikiMode::FormationMode && p->mNavi==a)),"initial bodies only native Exit or captain0 Formation");
                for(auto* p:born)if(std::find(manualBornBodies.begin(),manualBornBodies.end(),p)==manualBornBodies.end())manualBornBodies.push_back(p);
                require(manualBornBodies.size()<=20 && manualBornBodies.size()==born.size(),"no original withdrawal body lost or replaced");
                if(ownerStage==InitialWithdraw){
                    if(live==20 && a->getCurrState()->getID()!=NAVISTATE_Container){pad();ownerStage=InitialSettle;elapsed("initial_withdraw20_spawned");}
                    else{onionMenu(a,20);return result;}
                }
                pad();
                if(formation(a)!=20 || formation(b)!=0 || plateCount(a)!=20 || plateCount(b)!=0)return result;
                require(manualBornBodies.size()==20,"twenty original ordinary UI withdrawal bodies");
                sameBodies(manualBornBodies);
                const int iterable=initialIterableCount(a);
                const bool neutral=a->mKontroller->mCurrentInput==0 && a->mKontroller->mMainStickX==0 && a->mKontroller->mMainStickY==0;
                std::printf("P2_ONION_ITERABLE_READY frames=%d iterable=%d used=%d formation=%d neutral=%d prior_ready=%d\n",startupFrames,iterable,plateCount(a),formation(a),int(neutral),int(initialIterableNeutral));
                if(iterable!=20 || !neutral){initialIterableNeutral=false;return result;}
                if(!initialIterableNeutral){initialIterableNeutral=true;return result;}
                require(pc_onion_start_complete(),"all20 continuous actual Exit-to-Crowd histories complete");
                for(auto* p:manualBornBodies){bool found=false;for(const auto& body:pc_onion_start_bodies)if(body.actor==reinterpret_cast<uintptr_t>(p))found=true;require(found,"every original body matches native history");}
                std::printf("P2_ONION_INITIAL_HISTORY bodies=20 exit_entries=20 formed=20 unexpected=0 events=%u continuous=1\n",pc_onion_start_events);
                pc_onion_start_end();pc_worker_observer_end();
                std::printf("P2_ONION_STARTUP_ACQUIRED frames=%d unique=20 live=20 stored=0 owner0=20 owner1=0 plate0=20 plate1=0 acquisition_needed=0 observed_B=0 observed_Gather=0 observed_recruitment=0 via_ordinary_SDL=0\n",startupFrames);
                std::puts("P2_ONION_WORKER_SETUP needed=0 observed=0 recalls=0 natural=0 original_unique=20");
                std::printf("P2_ONION_INITIAL_UI_WITHDRAW frames=%d unique=20 live=20 stored=0 owner0=20 owner1=0 plate0=20 plate1=0 input_player=1 whistle=0\n",startupFrames);
                ownerStage=Deposit;menuSeen=false;menuConfirm=false;elapsed("initial_captain0_formation20");
            }
            require(++ownerFrames<1800,"bounded ordinary ownership preparation");
            if(ownerStage==Deposit){
                if(live==0 && storedCount()==20 && a->getCurrState()->getID()!=NAVISTATE_Container){
                    require(formation(a)==0&&formation(b)==0&&plateCount(a)==0&&plateCount(b)==0,"deposit clears both owner formations and plates");
                    std::puts("P2_ONION_DEPOSIT_BOUNDARY live=0 stored=20 owner0=0 owner1=0 plate0=0 plate1=0 startup_whistle_ended=1");
                    pad();menuSeen=false;menuConfirm=false;ownerStage=SwitchOne;elapsed("deposit20_complete");
                }else{onionMenu(a,0);return result;}
            }
            if(ownerStage==SwitchOne){
                if(switchFrames==0){pad(KBBTN_DPAD_UP);++switchFrames;return result;}
                pad();++switchFrames;
                if(naviMgr->getActiveNavi()!=b){require(switchFrames<60,"SDL switch to captain1");return result;}
                selected(1);require(live==0&&storedCount()==20,"real stock before captain1 withdrawal");
                ownerStage=Withdraw;menuSeen=false;menuConfirm=false;elapsed("captain1_withdraw_begin");
            }
            if(ownerStage==Withdraw){
                if(live==20 && b->getCurrState()->getID()!=NAVISTATE_Container){pad();ownerStage=Settle;elapsed("withdraw20_spawned");}
                else{require(live<=20,"Onion field cap20");onionMenu(b,20);return result;}
            }
            if(ownerStage==Settle){
                pad();require(live+storedCount()==withdrawnFromTotal,"withdrawal conserves actual total");
                if(formation(b)!=20)return result;
                ownedBodies=liveBodies();require(ownedBodies.size()==20,"twenty unique actual withdrawn bodies");
                owned("withdraw_complete");ownerStage=Owned;elapsed("captain1_formation20");
            }
            require(live<=20,"campaign field exceeds20live");
            if(live<20)return result; // fresh production TEST_BACKGROUND withdrawal
            require(live==20,"campaign20live baseline");
            require(pc_p2_captain::adapter()&&pc_p2_captain::captive_count()==0,"fresh live binding");
            selected(1);tick=0;elapsed("scene_ready");
            std::printf("P2_SAVE_SCENE phase=%s resumed=%d day=%d live=%d stored=%d health0=%.3f health1=%.3f active_selected=1 ownership_observed_after_UI=1 ownership_restoration_not_assumed=1\n",resumePhase?"resume":"save",int(pc_randomizer_resumed()),startDay,live,storedCount(),a->mHealth,b->mHealth);
        }
        owned(nullptr);
        if(b->getCurrState()->getID()==NAVISTATE_Gather)sawWhistle=true;
        require(++tick<180,"bounded ownership switch/whistle control stages");
        // Replace the old100-tick movement demonstration with observation-gated
        // ownership switches and whistle. Walking to the Onion already exercises
        // actual selected movement; no additional mirrored-input claim is made.
        switch(controlStage){
        case 0:pad(KBBTN_DPAD_UP);controlStage=1;break;
        case 1:
            pad();if(naviMgr->getActiveNavi()!=a)break;
            selected(0);owned("switched_to0");elapsed("switch0_owner_retained");controlStage=2;break;
        case 2:pad(KBBTN_DPAD_UP);controlStage=3;break;
        case 3:
            pad();if(naviMgr->getActiveNavi()!=b)break;
            selected(1);owned("switched_back1");elapsed("switch1_owner_retained");controlStage=4;break;
        case 4:pad(KBBTN_B);controlStage=5;break;
        case 5:
            if(!sawWhistle)break;
            pad();owned("whistle1");elapsed("whistle1_observed");controlStage=6;break;
        case 6:
            pad();if(!shot)break;
            owned("before_sunset_or_resume_exit");
            if(resumePhase){require(cards()==initialCards,"resume did not commit another generation");std::printf("PASS P2_CAPTAIN_ONION_OWNER_RESUME day=%d generations=%d controls=1 camera=1 onion_movement=1 whistle=1 stored=%d saved_bytes_injected=0\n",startDay,cards(),storedCount());std::fflush(nullptr);std::_Exit(0);}
            pad(KBBTN_START);saving=true;elapsed("ordinary_pause_requested");std::puts("P2_SAVE_SUNSET ordinary_pause_UI=1 direct_forceDayEnd=0 dayendflag_writes=0");
            break;
        }
        std::fflush(stdout);return result;
    }
};
} // namespace
int main(int argc,char** argv){
    for(int i=1;i<argc;++i){resumePhase|=std::string(argv[i])=="--resume-phase";sForceCaptainDown|=std::string(argv[i])=="--force-captain-down";sForceInactiveDown|=std::string(argv[i])=="--force-inactive-down";forceNullState|=std::string(argv[i])=="--force-null-state";forceMissingManager|=std::string(argv[i])=="--force-missing-manager";}
    SDL_setenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1",1);SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_randomizer_second_captain(),"generated bootstrap captain option required");
    require(pc_randomizer_enabled()&&!pc_pikipelago_room_preview(),"ordinary randomizer campaign required");
    if(!pc_window_init("Captain native campaign save/resume",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect bounds{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&bounds);
    require(width==960&&height==540&&std::abs(x-(bounds.x+(bounds.w-width)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-height)/2))<=2,"centered fixture baseline");
    std::printf("P2_SAVE_WINDOW size=%dx%d centered=1 after_settings=1\n",width,height);
    pc_coop_set_pending(false);
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
    const int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"attach virtual");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
    const std::string mapping=std::string(guid)+",Combined captain SDL pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
    require(SDL_GameControllerAddMapping(mapping.c_str())>=0 && SDL_IsGameController(device),"mapped SDL virtual controller");
    virtualPad=SDL_JoystickOpen(device);require(virtualPad&&SDL_JoystickIsVirtual(device),"actual virtual P1");
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(virtualPad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    std::printf("P2_SAVE_SDL_ROUTING instance=%d virtual=1 player=1 input_script=0 background_test_seam=1\n",int(SDL_JoystickInstanceID(virtualPad)));
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new CaptainSaveApp());return 0;
}
