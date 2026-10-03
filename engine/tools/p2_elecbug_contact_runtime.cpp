// #1164: ordinary SDL throws; no creature position, health or FSM writes.
// Build-only fixture target. Run under a separate <=60-second wall supervisor.
#include <SDL2/SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <map>
#include <set>
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
#include "UfoItem.h"
#include "Boss.h"
#include "Pom.h"
#include "pc_p2_white.h"
#include "pc_p2_species.h"
#include "pc_p2_original_throw.h"
#include "pc_p2_original_piki_physical.h"
#include "pc_p2_original_piki_recruit.h"
#include "pc_p2_original_progress.h"
#include "pc_p2_original_source_uid.h"
#include "Generator.h"
#include "teki.h"
#include "Collision.h"
#include "GameStat.h"
#include "KeyConfig.h"
#include "Kontroller.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_elecbug.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "p2_fixture_captain_guard.h"

namespace {
SDL_Joystick* pad=nullptr;
constexpr unsigned Target=346002, Partner=346010;
const char* mode="landing";
bool electric(){return std::strcmp(mode,"landing")!=0;}
int desiredSpecies(){return !std::strcmp(mode,"white-electric")?P2SpeciesWhite:
    !std::strcmp(mode,"yellow-electric")?P2SpeciesYellow:P2SpeciesRed;}
// Production SDL->PAD conversion divides by256; preserve intended PAD strength.
constexpr int contact_sdl_axis(int padAxis) { return padAxis * 256; }
void require(bool ok,const char* why){
    if(!ok){std::printf("FAIL P2_ELECBUG_CONTACT %s\n",why);std::fflush(nullptr);std::_Exit(1);}
}
void input(unsigned keys=0,int x=0,int y=0){
    pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));
    pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
    SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,(keys&KBBTN_B)!=0);
    SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_DPAD_RIGHT,(keys&KBBTN_DPAD_RIGHT)!=0);
    SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(contact_sdl_axis(x)));
    SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-contact_sdl_axis(y)));
    SDL_JoystickUpdate();
}
float distance(const Vector3f& a,const Vector3f& b){return std::hypot(a.x-b.x,a.z-b.z);}
void point(Navi* n,const Vector3f& goal,bool walk,unsigned keys=0){
    const Vector3f from=walk?n->mSRT.t:n->mCursorWorldPos;
    const float dx=goal.x-from.x,dz=goal.z-from.z,d=std::hypot(dx,dz);
    int x=0,y=0;
    if(d>(walk?15.f:(!std::strcmp(mode,"red-electric")?3.f:6.f))){
        const Vector3f axis=n->controlCamera()->mViewXAxis;
        const float power=walk?65.f:22.f;
        x=int(std::lround(power*(dx*axis.x+dz*axis.z)/d));
        y=int(std::lround(power*(dx*axis.z-dz*axis.x)/d));
    }
    input(keys,x,y);
}
Teki* find(unsigned token){
    Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);
        if(t&&t->mGenerator&&t->mGenerator->_70==token)return t;}
    return nullptr;
}
Vector3f pressAim(Navi* n,Teki* enemy,Teki* partner){
    Vector3f goal=enemy->mSRT.t;
    if(!std::strcmp(mode,"red-electric")){
        // Aim at the actual fitted rear body, clear of the arc endpoint.
        // Measured landing centre was nine units short with a ten-unit aim
        // lead: the throw starts behind the captain and its model trails the
        // root. Ordinary cursor input accounts for that observed gap.
        CollPart* rear=enemy->mCollInfo&&enemy->mCollInfo->hasInfo()
            ?enemy->mCollInfo->getSphere('bod2'):nullptr;
        require(rear&&std::isfinite(rear->mCentre.x)&&std::isfinite(rear->mCentre.z),
                "actual rear collision part for Red aim");
        goal=rear->mCentre;
        Vector3f direction=goal-n->mSRT.t;direction.y=0;
        require(direction.length()>1.f,"distinct Red aim target");
        direction.normalise();goal=goal+direction*19.f;
    }
    return goal;
}
class ContactApp:public PlugPikiApp {
    int frame=0,age=0,ready=0,throwTicks=0,neutralThrowTicks=0,uiResumeTicks=0;
    int redApproach=0;
    Vector3f redApproachSide;
    bool captainSeen=false,started=false,offContactSeen=false,reverseSeen=false;
    bool slotSeen[2]={false,false};
    int acquisition=0,acquisitionTicks=0,whiteGather=0,ivoryThrowTicks=0;
    bool sawWhiteSprout=false,ivoryCaptured=false;
    Piki* acquiredWhite=nullptr;
    Piki* stagedRgb=nullptr;
    bool yellowRecovered() const {
        if(!stagedRgb||!stagedRgb->isAlive()||!stagedRgb->isCreatureFlag(CF_IsOnGround))return false;
        const int state=stagedRgb->getState();
        return state!=PIKISTATE_Flying&&state!=PIKISTATE_Hanged&&state!=PIKISTATE_Dying
            &&state!=PIKISTATE_Dead&&state!=PIKISTATE_Drown&&state!=PIKISTATE_DenkiDying;
    }
    void stageRgb(Navi* captain){
        Iterator actors(pikiMgr);actors.first();auto* replace=static_cast<Piki*>(*actors);
        require(replace&&replace->isAlive(),"owned baseline replacement exists");
        replace->setEraseKill();replace->kill(false);
        const int species=desiredSpecies();
        // Red is an explicitly synthetic control identity, never a relabelled
        // original Yellow record. Both fixtures exclude acquisition claims.
        const std::string key=species==P2SpeciesYellow?"tutorial/initgen.txt#2":"fixture-red-control/initgen.txt#0";
        const std::string fingerprint=species==P2SpeciesYellow
            ?"b8a4fb5a39f8371a879eec4ece9025bee75977a4b4394111d5825e6ec79c0bbf"
            :"8926e466ec3c5d6fb8b9db2f93a7164cf5ff87d4719b5454a61eb9688ae368b3";
        const unsigned uid=p2original::originalSourceCatalogUid(key);
        std::string error;
        require(pc_p2_original_piki_origin_install(fingerprint,{{key,uid,20,species}},error),"RGB fixture catalog");
        const std::string campaign="6a012015368158125b7b88bdd14000ed2a10613f02474b0f08830d9a3b5ec029";
        require(p2original::originalProgress().initialize(campaign,error),"RGB fixture progress");
        auto context=p2original::originalProgress().context();context.story=false;
        require(p2original::originalProgress().restoreContext(context,error),"disclosed non-story RGB fixture context");
        require(pc_p2_original_piki_recruit_bind(campaign,fingerprint,error),"RGB paired recruitment");
        OriginalPikiBody body{{key,uid,0,1,fingerprint},{species,false,false}};
        const auto& pos=captain->mSRT.t;
        require(pc_p2_original_piki_physical_birth(body,{{pos.x+12,pos.y,pos.z}},stagedRgb,error)==p2original::PikiBirthResult::Born,"disclosed RGB replacement");
        require(pc_p2_original_rgb_throw_species(stagedRgb)==species,"canonical staged RGB");
        std::printf("P2_ELECBUG_%s_STAGED piki=%p species=%d relocated_debug_member=1 non_story_fixture=1 acquisition=0 campaign=0 synthetic_control=%d catalog_key=%s fingerprint=%s\n",species==P2SpeciesYellow?"YELLOW":"RED",static_cast<void*>(stagedRgb),species,int(species==P2SpeciesRed),key.c_str(),fingerprint.c_str());
    }
    std::map<Piki*,int> observedSpecies;
    void guardCaptains(){
        const char* mask=std::getenv("P2_ELECBUG_GUARD_MASK");
        const bool missingMask=mask&&!std::strcmp(mask,"missing-manager")&&captainSeen;
        if((!naviMgr||missingMask)&&captainSeen){
            std::printf("P2_ELECBUG_GUARD_OBSERVATION mask=%s injected=%d missing_manager=1 frame=%d\n",missingMask?mask:"none",int(missingMask),frame);
            p2_fixture_require_captain(true,true,0,frame);
        }
        if(!naviMgr)return;
        Navi* active=naviMgr->getActiveNavi();
        for(int i=0;i<2;++i){
            Navi* c=i<naviMgr->getNaviCount()?naviMgr->getNavi(i):nullptr;
            const bool init=c&&c->getCurrState();
            const bool nullMask=mask&&!std::strcmp(mask,"null-state")&&slotSeen[i];
            if(slotSeen[i]&&(!init||nullMask)){
                std::printf("P2_ELECBUG_GUARD_OBSERVATION mask=%s injected=%d slot=%d missing_state=1 frame=%d\n",nullMask?mask:"none",int(nullMask),i,frame);
                p2_fixture_require_captain(true,true,0,frame);
            }
            if(!init)continue;
            if(!slotSeen[i])std::printf("P2_ELECBUG_CAPTAIN_INITIALIZED slot=%d active=%d hp=%.3f frame=%d\n",i,int(c==active),c->mHealth,frame);
            slotSeen[i]=true;captainSeen=true;
            const bool force=(mask&&((!std::strcmp(mask,"active")&&c==active)||(!std::strcmp(mask,"inactive")&&c!=active)))||
                             (std::getenv("P2_ELECBUG_FORCE_CAPTAIN_DOWN")&&c==active);
            if(force)std::printf("P2_ELECBUG_GUARD_OBSERVATION mask=%s injected=1 slot=%d active=%d frame=%d\n",mask?mask:"active",i,int(c==active),frame);
            p2_fixture_require_captain(GameStat::orimaDead||force,naviMgr->isNaviDead(c)||c->getCurrState()->getID()==NAVISTATE_Dead,c->mHealth,frame);
        }
    }
    bool acquireWhite(Navi* n){
        if(desiredSpecies()!=P2SpeciesWhite)return true;
        ++acquisitionTicks;
        if(acquisition==3){if(++whiteGather<90){input(KBBTN_B);return false;}return true;}
        require(bossMgr&&itemMgr,"White acquisition managers");
        Pom* flower=nullptr;
        Iterator bosses(bossMgr);CI_LOOP(bosses){Boss* b=static_cast<Boss*>(*bosses);
            if(b&&b->isAlive()&&b->mObjType==OBJTYPE_Pom&&b->mGenerator&&b->mGenerator->_70==25)flower=static_cast<Pom*>(b);}
        int population=0,whiteOutputs=0;Piki* white=nullptr;
        Iterator actors(pikiMgr);CI_LOOP(actors){Piki* p=static_cast<Piki*>(*actors);if(p&&p->isAlive()){++population;if(flower&&p->getStickObject()==flower)ivoryCaptured=true;if(pc_p2_species(p)==P2SpeciesWhite){white=p;++whiteOutputs;}}}
        PikiHeadItem* head=nullptr;PikiHeadItem* observedSprout=nullptr;
        Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);if(h&&h->isAlive()){
            ++population;
            if(pc_p2_species(h)==P2SpeciesWhite){
                ++whiteOutputs;
                observedSprout=h;
                if(h->canPullout()&&!head)head=h;
            }
        }}
        if(acquisitionTicks%60==0){std::printf("P2_ELECBUG_ACQUISITION_PROGRESS frame=%d phase=%d population=%d sprout_seen=%d pluckable=%d white=%d ivory=%d\n",frame,acquisition,population,int(sawWhiteSprout),int(head!=nullptr),int(white!=nullptr),int(flower!=nullptr));std::fflush(nullptr);}
        require(population==20,"White acquisition population conservation");
        require(whiteOutputs<=1,"White acquisition must yield one unambiguous actor or sprout");
        if(observedSprout&&!sawWhiteSprout){std::printf("P2_ELECBUG_IVORY_SPROUT frame=%d generator=25 sprout=%p species=4 population=20\n",frame,static_cast<void*>(observedSprout));sawWhiteSprout=true;}
        if(white){
            require(sawWhiteSprout&&acquisition==2,"White requires observed sprout and ordinary pluck phase");
            std::printf("P2_ELECBUG_WHITE_ACQUIRED frame=%d piki=%p species=4 population=20 ordinary_pluck=1\n",frame,static_cast<void*>(white));
            acquiredWhite=white;acquisition=3;input(KBBTN_B);return false;
        }
        if(head)acquisition=2;
        if(acquisition==2){
            if(!head){input();return false;}
            if(distance(n->mSRT.t,head->mSRT.t)>18.f)point(n,head->mSRT.t,true);
            else input(acquisitionTicks%45<30?KBBTN_A:0);
            return false;
        }
        require(flower&&pc_p2_ivory(flower),"bound Ivory25 required");
        if(acquisitionTicks<90){input(KBBTN_B);return false;}
        if(distance(n->mSRT.t,flower->mSRT.t)>100.f){point(n,flower->mSRT.t,true);return false;}
        acquisition=1;
        if(sawWhiteSprout||ivoryCaptured){input();return false;}
        // One ordinary attempt: do not send another Pikmin while the first
        // throw is still flying or awaiting the flower's capture/conversion.
        ++ivoryThrowTicks;
        require(ivoryThrowTicks<=240,"single Ivory throw missed or capture not observed");
        if(ivoryThrowTicks<=22)point(n,flower->mSRT.t,false,KBBTN_A);else input();
        return false;
    }
    int contactSamples=0,offContactSamples=0;
    // Fixture observation only: held, released, rising, descending, off-contact.
    std::map<Piki*,int> flight;
    std::map<Piki*,int> releasedAt;
    bool aHeld=false;
    void witness(Piki* p,const char* phase){
        std::printf("P2_ELECBUG_THROW frame=%d piki=%p phase=%s\n",frame,static_cast<void*>(p),phase);
    }
public:
    int idle() override {
        const int result=PlugPikiApp::idle();
        // First post-idle boundary: guard even when paused/in a movie. Do not
        // treat an allocated but uninitialized captain as initialized gameplay.
        guardCaptains();
        Navi* n=naviMgr?naviMgr->getActiveNavi():nullptr;
        const bool initialized=n&&n->getCurrState();
        if(captainSeen&&!initialized){
            std::printf("P2_ELECBUG_GUARD_OBSERVATION mask=none injected=0 active_missing=1 frame=%d\n",frame);
            p2_fixture_require_captain(true,true,0,frame);
        }
        ++frame;
        require(frame<3600,"frame bound; requires separate60s wall supervisor");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!initialized||!pikiMgr||!tekiMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive){
            if(frame%60==0){std::printf("P2_ELECBUG_WAIT frame=%d initialized=%d pause=%d overlay=%d captain_state=%d buttons=%08x\n",frame,int(initialized),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),initialized?n->getCurrState()->getID():-1,initialized?n->mKontroller->mCurrentInput:0);std::fflush(nullptr);}
            if(initialized&&gameflow.mIsUIOverlayActive&&electric()&&desiredSpecies()!=P2SpeciesWhite){
                // Ordinary B first reveals the message, then advances it.
                input(frame%8<4?KBBTN_B:0);aHeld=false;uiResumeTicks=15;
            }
            return result;
        }
        if(uiResumeTicks>0){--uiResumeTicks;input();return result;}
        if(!started&&(n->getCurrState()->getID()!=NAVISTATE_Walk||++ready<45))return result;
        Teki* enemy=find(Target);Teki* partner=find(Partner);
        require(enemy&&partner&&pc_p2_elecbug_registered(enemy)&&pc_p2_elecbug_registered(partner),"two bound ElecBugs");
        int live=0,red=0;
        Iterator squad(pikiMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(p&&p->isAlive()){++live;if(pc_p2_species(p)==P2SpeciesRed)++red;}}
        if(!started){
            std::printf("P2_ELECBUG_BASELINE live=%d red=%d captain=%.3f,%.3f,%.3f\n",live,red,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);std::fflush(nullptr);
            require(live==20&&red==20,"fresh20 nativeRed1 baseline");
            require(enemy->mCollInfo&&enemy->mCollInfo->hasInfo(),"initialized enemy geometry");
            if(desiredSpecies()==P2SpeciesYellow||!std::strcmp(mode,"red-electric"))stageRgb(n);
            started=true;
            std::printf("P2_ELECBUG_CONTACT_READY live=%d red=%d captain_hp=%.3f source_id=28 generators=%u,%u\n",live,red,n->mHealth,Target,Partner);
            if(std::getenv("P2_ELECBUG_READY_ONLY")){
                std::puts("PASS P2_ELECBUG_READY_ONLY combat=UNTESTED");std::fflush(nullptr);std::_Exit(0);
            }
        }
        const char* mask=std::getenv("P2_ELECBUG_GUARD_MASK");
        if(mask&&!std::strcmp(mask,"inactive"))require(false,"inactive guard mask unavailable: no initialized inactive captain");
        if(!acquireWhite(n))return result;
        ++age;
        if(desiredSpecies()==P2SpeciesYellow){
            require(live==20&&stagedRgb&&stagedRgb->isAlive(),"Yellow encounter preserves20 living Pikmin");
            require(pc_p2_original_rgb_throw_species(stagedRgb)==2,"Yellow source identity retained");
            require(stagedRgb->getState()!=PIKISTATE_DenkiDying,"Yellow must reject electric death");
        }
        const char* state=pc_p2_elecbug_state_name(enemy);
        require(state,"registered state exists");
        if(!std::strcmp(state,"reverse"))reverseSeen=true;
        std::set<Piki*> living;
        Iterator candidates(pikiMgr);CI_LOOP(candidates){
            Piki* p=static_cast<Piki*>(*candidates);
            if(!p)continue;
            if(!p->isAlive()){
                if(reverseSeen&&flight.count(p)&&flight[p]==5)living.insert(p);
                continue;
            }
            if(!p->getCurrState()){
                auto previous=flight.find(p);
                if(previous!=flight.end()){witness(p,"invalidated");flight.erase(previous);}
                continue;
            }
            living.insert(p);
            int& phase=flight[p];
            observedSpecies[p]=pc_p2_species(p);
            const int pstate=p->getState();
            if(aHeld&&p->mNavi==n&&pstate==PIKISTATE_Hanged&&phase!=1&&pc_p2_species(p)==desiredSpecies()&&(desiredSpecies()!=P2SpeciesWhite||p==acquiredWhite)&&(!stagedRgb||p==stagedRgb)){phase=1;witness(p,"held");}
            if(phase==2){
                if(pstate==PIKISTATE_Flying&&p->mVelocity.y>.01f){phase=3;witness(p,"rising");}
                else {
                    // Hanged becomes Normal during the ordinary throw animation,
                    // before KEY_Action0 launches the captain's exact target.
                    NaviThrowState* windup=n->getCurrState()->getID()==NAVISTATE_Throw
                        ?static_cast<NaviThrowState*>(n->getCurrState()):nullptr;
                    const bool pending=windup&&windup->mTargetPiki==p&&!windup->mHasThrownPiki&&
                        (pstate==PIKISTATE_Hanged||pstate==PIKISTATE_Normal)&&p->mNavi==n&&frame-releasedAt[p]<=60;
                    if(!pending){phase=0;witness(p,"invalidated");}
                }
            }
            if(phase==3&&pstate==PIKISTATE_Flying&&p->mVelocity.y<-.01f){phase=4;witness(p,"descending");}
            if(((phase==3||phase==4)&&pstate!=PIKISTATE_Flying)||
               (phase==5&&!reverseSeen&&pstate!=PIKISTATE_Flying)){
                phase=0;witness(p,"invalidated");
            }
            if(p->mVelocity.y>=-.01f)continue;
            const float xz=distance(p->getPosition(),enemy->getPosition());
            if(xz>30.f)continue;
            Vector3f ignored;
            const bool contact=enemy->mCollInfo&&enemy->mCollInfo->hasInfo()&&enemy->mCollInfo->checkCollision(p,ignored);
            const float dy=p->getPosition().y-enemy->getPosition().y;
            if(contact)++contactSamples;
            else if(dy>30.f&&!reverseSeen&&phase==4&&pstate==PIKISTATE_Flying){
                offContactSeen=true;++offContactSamples;phase=5;
                std::printf("P2_ELECBUG_OFF_CONTACT frame=%d generator=%u piki=%p contact=0\n",frame,Target,static_cast<void*>(p));
            }
            std::printf("P2_ELECBUG_CONTACT_SAMPLE age=%d dy=%.3f xz=%.3f vy=%.3f contact=%d state=%s piki=%p\n",
                age,dy,xz,p->mVelocity.y,int(contact),state,static_cast<void*>(p));
        }
        for(auto it=flight.begin();it!=flight.end();){
            if(!living.count(it->first)&&!(reverseSeen&&it->second==5)){witness(it->first,"invalidated");it=flight.erase(it);}
            else ++it;
        }
        if(age%30==0){
            std::printf("P2_ELECBUG_CONTACT_PROGRESS age=%d live=%d target_distance=%.2f state=%s throw_ticks=%d off_contact=%d contacts=%d\n",
                age,live,distance(n->mSRT.t,enemy->mSRT.t),state,throwTicks,offContactSamples,contactSamples);
            std::fflush(nullptr);
            if(stagedRgb){std::printf("P2_ELECBUG_SELECTION age=%d a_held=%d neutral=%d captain_state=%d buttons=%08x throw_bind=%08x yellow_state=%d yellow_mode=%d yellow_navi=%p captain=%p yellow_distance=%.3f next=%p\n",age,int(aHeld),neutralThrowTicks,n->getCurrState()->getID(),n->mKontroller->mCurrentInput,KeyConfig::_instance->mThrowKey.mBind,stagedRgb->getState(),stagedRgb->mMode,static_cast<void*>(stagedRgb->mNavi),static_cast<void*>(n),distance(stagedRgb->mSRT.t,n->mSRT.t),static_cast<void*>(n->mNextThrowPiki));std::fflush(nullptr);}
        }
        if(offContactSeen&&reverseSeen){
            for(const auto& entry:flight)if(entry.second==5&&(desiredSpecies()!=P2SpeciesWhite||entry.first==acquiredWhite)){
                if(desiredSpecies()==P2SpeciesYellow){
                    if(entry.first!=stagedRgb||!yellowRecovered())continue;
                    std::printf("P2_ELECBUG_YELLOW_SURVIVED frame=%d piki=%p species=2 alive=1 grounded=1 live=%d state=%d\n",frame,static_cast<void*>(stagedRgb),live,stagedRgb->getState());
                }
                // Exit supplies a candidate only. The launcher must correlate
                // production contact-dispatch evidence to this exact Pikmin.
                std::printf("P2_ELECBUG_CONTACT_CANDIDATE frame=%d generator=%u piki=%p observed_reverse=1 mode=%s species=%d\n",frame,Target,static_cast<void*>(entry.first),mode,observedSpecies[entry.first]);
            }
            // Yellow waits for actual ground recovery after the dispatch.
            if(desiredSpecies()!=P2SpeciesYellow ||
                (flight.count(stagedRgb)&&flight[stagedRgb]==5
                 &&yellowRecovered())){
                std::fflush(nullptr);std::_Exit(0);
            }
        }
        // Only virtual-pad input. Gather, approach, aim during A hold, release.
        if(age<(!std::strcmp(mode,"red-electric")?30:90)){input(KBBTN_B);return result;}
        if (!std::strcmp(mode,"red-electric") && redApproach < 2) {
            Vector3f away=enemy->mSRT.t-partner->mSRT.t;
            away.y=0;
            require(away.length()>1.f,"distinct Red approach endpoints");
            away.normalise();
            if (redApproach==0 && redApproachSide.length()==0) {
                redApproachSide.set(-away.z,0,away.x);
                if (redApproachSide.DP(n->mSRT.t-enemy->mSRT.t)<0) redApproachSide.multiply(-1.f);
            }
            // Walk around the live arc to the outside of its endpoint. This
            // uses ordinary pad movement; no enemy/Pikmin/receiver state writes.
            Vector3f goal=enemy->mSRT.t+away*70.f;
            if (redApproach==0) goal=goal+redApproachSide*50.f;
            if(age%30==0){std::printf("P2_ELECBUG_RED_ROUTE phase=%d captain=%.3f,%.3f,%.3f goal=%.3f,%.3f,%.3f distance=%.3f ordinary_pad=1\n",redApproach,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,goal.x,goal.y,goal.z,distance(n->mSRT.t,goal));std::fflush(nullptr);}
            if (distance(n->mSRT.t,goal)>20.f) {
                neutralThrowTicks=0;point(n,goal,true);return result;
            }
            ++redApproach;
            std::printf("P2_ELECBUG_RED_APPROACH phase=%d ordinary_pad=1\n",redApproach);
            input();return result;
        }
        UfoItem* ship=itemMgr?itemMgr->getUfo():nullptr;
        if(electric()&&desiredSpecies()!=P2SpeciesWhite&&!aHeld&&ship){
            const Vector3f goal=ship->getGoalPos();
            const Vector3f offset=goal-n->mSRT.t;
            // Walk's recovery A action uses the offset goal, not ship origin.
            if(offset.length()<=60.f||distance(n->mSRT.t,ship->mSRT.t)<=70.f){
                neutralThrowTicks=0;point(n,enemy->mSRT.t,true);return result;
            }
        }
        if(distance(n->mSRT.t,enemy->mSRT.t)>140.f){
            if(aHeld){for(const auto& entry:flight)witness(entry.first,"invalidated");flight.clear();aHeld=false;}
            neutralThrowTicks=0;
            point(n,enemy->mSRT.t,true);return result;
        }
        if(electric()&&desiredSpecies()!=P2SpeciesWhite&&neutralThrowTicks<15){
            input();if(n->getCurrState()->getID()==NAVISTATE_Walk)++neutralThrowTicks;
            return result;
        }
        Piki* held=nullptr;
        Iterator holding(pikiMgr);CI_LOOP(holding){Piki* p=static_cast<Piki*>(*holding);if(p&&p->isAlive()&&p->mNavi==n&&p->getCurrState()&&p->getState()==PIKISTATE_Hanged)held=p;}
        if(electric()){
            // Hold and select with the ordinary pad while awaiting real discharge.
            const bool discharging=!std::strcmp(state,"discharge")||!std::strcmp(state,"childdischarge");
            if(held&&desiredSpecies()==P2SpeciesWhite&&pc_p2_species(held)==P2SpeciesWhite)require(held==acquiredWhite,"held White must be acquired witness");
            if(held&&(pc_p2_species(held)!=desiredSpecies()||(stagedRgb&&held!=stagedRgb))){
                aHeld=true;point(n,pressAim(n,enemy,partner),false,KBBTN_A|(age%6==0?KBBTN_DPAD_RIGHT:0));return result;
            }
            bool pending=false;for(const auto& entry:flight)if(entry.second>=2)pending=true;
            if(!aHeld&&pending){input();return result;}
            if(!held&&!aHeld){aHeld=true;point(n,pressAim(n,enemy,partner),false,KBBTN_A);return result;}
            if(aHeld&&!discharging){point(n,pressAim(n,enemy,partner),false,KBBTN_A);return result;}
            if(aHeld){
                if(!std::strcmp(mode,"red-electric")) {
                    const Vector3f goal=pressAim(n,enemy,partner);
                    const float error=distance(n->mCursorWorldPos,goal);
                    require(std::isfinite(error),"finite Red cursor alignment");
                    if(error>3.f){point(n,goal,false,KBBTN_A);return result;}
                    std::printf("P2_ELECBUG_RED_AIM frame=%d error=%.6f cursor=%.6f,%.6f goal=%.6f,%.6f ordinary_pad=1\n",frame,error,n->mCursorWorldPos.x,n->mCursorWorldPos.z,goal.x,goal.z);
                }
                input();for(auto& entry:flight)if(entry.second==1){entry.second=2;releasedAt[entry.first]=frame;witness(entry.first,"released");}
                aHeld=false;return result;
            }
            if(pending){input();return result;}
        }
        const int cycle=throwTicks++%45;
        if(cycle<22){aHeld=true;point(n,pressAim(n,enemy,partner),false,KBBTN_A);}
        else {
            input();
            if(aHeld)for(auto& entry:flight)if(entry.second==1){entry.second=2;releasedAt[entry.first]=frame;witness(entry.first,"released");}
            aHeld=false;
        }
        return result;
    }
};
}
int main(int argc,char** argv){
    if(const char* requested=std::getenv("P2_ELECBUG_MODE"))mode=requested;
    require(!std::strcmp(mode,"landing")||!std::strcmp(mode,"red-electric")||!std::strcmp(mode,"white-electric")||!std::strcmp(mode,"yellow-electric"),"known mode");
    if(const char* mask=std::getenv("P2_ELECBUG_GUARD_MASK"))require(!std::strcmp(mask,"active")||!std::strcmp(mask,"inactive")||!std::strcmp(mask,"null-state")||!std::strcmp(mask,"missing-manager"),"known negative observation mask");
    std::printf("P2_ELECBUG_MODE mode=%s species=%d\n",mode,desiredSpecies());
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
    SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires experimental room argument");
    if(!pc_window_init("P2 Anode landing-contact acceptance",960,540))return 3;
    pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);
    pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    SDL_Window* window=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_Rect bounds{};
    SDL_GetWindowSize(window,&width,&height);SDL_GetWindowPosition(window,&x,&y);
    SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
    require(width==960&&height==540&&std::abs(x-(bounds.x+(bounds.w-width)/2))<=2&&std::abs(y-(bounds.y+(bounds.h-height)/2))<=2,"measured centered960x540");
    std::puts("P2_ELECBUG_CONTACT_WINDOW size=960x540 centered=1");
    const int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);
    require(device>=0,"virtual pad attach");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
    const std::string mapping=std::string(guid)+",Anode acceptance pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
    require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual pad mapping");
    pad=SDL_JoystickOpen(device);require(pad,"virtual pad open");
    pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);
    pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);
    pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);
    pc_window_set_gamepad_binding(PC_KEY_ACT_DPAD_RIGHT,SDL_CONTROLLER_BUTTON_DPAD_RIGHT);input();
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new ContactApp());return 0;
}
