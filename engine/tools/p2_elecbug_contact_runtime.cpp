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
#include "Boss.h"
#include "Pom.h"
#include "pc_p2_white.h"
#include "pc_p2_species.h"
#include "Generator.h"
#include "teki.h"
#include "Collision.h"
#include "GameStat.h"
#include "KeyConfig.h"
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
int desiredSpecies(){return !std::strcmp(mode,"white-electric")?P2SpeciesWhite:P2SpeciesRed;}
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
    if(d>(walk?15.f:6.f)){
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
class ContactApp:public PlugPikiApp {
    int frame=0,age=0,ready=0,throwTicks=0;
    bool captainSeen=false,started=false,offContactSeen=false,reverseSeen=false;
    bool slotSeen[2]={false,false};
    int acquisition=0,acquisitionTicks=0,whiteGather=0,ivoryThrowTicks=0;
    bool sawWhiteSprout=false,ivoryCaptured=false;
    Piki* acquiredWhite=nullptr;
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
        if(!initialized||!pikiMgr||!tekiMgr||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
        if(!started&&(n->getCurrState()->getID()!=NAVISTATE_Walk||++ready<45))return result;
        Teki* enemy=find(Target);Teki* partner=find(Partner);
        require(enemy&&partner&&pc_p2_elecbug_registered(enemy)&&pc_p2_elecbug_registered(partner),"two bound ElecBugs");
        int live=0,red=0;
        Iterator squad(pikiMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(p&&p->isAlive()){++live;if(pc_p2_species(p)==P2SpeciesRed)++red;}}
        if(!started){
            require(live==20&&red==20,"fresh20 nativeRed1 baseline");
            require(enemy->mCollInfo&&enemy->mCollInfo->hasInfo(),"initialized enemy geometry");
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
            if(aHeld&&p->mNavi==n&&pstate==PIKISTATE_Hanged&&phase!=1&&pc_p2_species(p)==desiredSpecies()&&(desiredSpecies()!=P2SpeciesWhite||p==acquiredWhite)){phase=1;witness(p,"held");}
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
        }
        if(offContactSeen&&reverseSeen){
            for(const auto& entry:flight)if(entry.second==5&&(desiredSpecies()!=P2SpeciesWhite||entry.first==acquiredWhite)){
                // Exit supplies a candidate only. The launcher must correlate
                // production contact-dispatch evidence to this exact Pikmin.
                std::printf("P2_ELECBUG_CONTACT_CANDIDATE frame=%d generator=%u piki=%p observed_reverse=1 mode=%s species=%d\n",frame,Target,static_cast<void*>(entry.first),mode,observedSpecies[entry.first]);
            }
            std::fflush(nullptr);std::_Exit(0);
        }
        // Only virtual-pad input. Gather, approach, aim during A hold, release.
        if(age<90){input(KBBTN_B);return result;}
        if(distance(n->mSRT.t,enemy->mSRT.t)>140.f){
            if(aHeld){for(const auto& entry:flight)witness(entry.first,"invalidated");flight.clear();aHeld=false;}
            point(n,enemy->mSRT.t,true);return result;
        }
        Piki* held=nullptr;
        Iterator holding(pikiMgr);CI_LOOP(holding){Piki* p=static_cast<Piki*>(*holding);if(p&&p->isAlive()&&p->mNavi==n&&p->getCurrState()&&p->getState()==PIKISTATE_Hanged)held=p;}
        if(electric()){
            // Hold and select with the ordinary pad while awaiting real discharge.
            const bool discharging=!std::strcmp(state,"discharge")||!std::strcmp(state,"childdischarge");
            if(held&&desiredSpecies()==P2SpeciesWhite&&pc_p2_species(held)==P2SpeciesWhite)require(held==acquiredWhite,"held White must be acquired witness");
            if(held&&pc_p2_species(held)!=desiredSpecies()){
                aHeld=true;point(n,enemy->mSRT.t,false,KBBTN_A|(age%6==0?KBBTN_DPAD_RIGHT:0));return result;
            }
            bool pending=false;for(const auto& entry:flight)if(entry.second>=2)pending=true;
            if(!aHeld&&pending){input();return result;}
            if(!held&&!aHeld){aHeld=true;point(n,enemy->mSRT.t,false,KBBTN_A);return result;}
            if(aHeld&&!discharging){point(n,enemy->mSRT.t,false,KBBTN_A);return result;}
            if(aHeld){
                input();for(auto& entry:flight)if(entry.second==1){entry.second=2;releasedAt[entry.first]=frame;witness(entry.first,"released");}
                aHeld=false;return result;
            }
            if(pending){input();return result;}
        }
        const int cycle=throwTicks++%45;
        if(cycle<22){aHeld=true;point(n,enemy->mSRT.t,false,KBBTN_A);}
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
    require(!std::strcmp(mode,"landing")||!std::strcmp(mode,"red-electric")||!std::strcmp(mode,"white-electric"),"known mode");
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
