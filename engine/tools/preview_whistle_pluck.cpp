// Isolated real-engine test: injected sprouts/input; production whistle and animations.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "system.h"
#include "App.h"
#include "Node.h"
#include "Section.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Kontroller.h"
#include "KeyConfig.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "MapMgr.h"
#include "GameStat.h"
#include "AIConstant.h"
#include "pc_whistle_pluck.h"
#include "pc_p2_purple.h"
#include "pc_p2_white.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <set>
#include <vector>
#include <algorithm>

static bool held = false;
class Input : public Kontroller {
public:
    Input() : Kontroller(1) {}
    void update() override {
        updateCont(held ? KeyConfig::_instance->mSetCursorKey.mBind : 0);
        mMainStickX=mMainStickY=mSubStickX=mSubStickY=0;
    }
};
static void require(bool ok, const char* why) {
    if (!ok) { std::printf("FAIL whistle pluck: %s\n",why);std::fflush(stdout);std::_Exit(1); }
}
static void capture(const char* path="whistle-pluck.ppm") {
    auto bind=reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    GLint previous=0;glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous);bind(GL_FRAMEBUFFER,0);
    int w=0,h=0;SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(),&w,&h);
    std::vector<unsigned char> pixels(size_t(w)*h*3);glPixelStorei(GL_PACK_ALIGNMENT,1);glReadBuffer(GL_BACK);
    glReadPixels(0,0,w,h,GL_RGB,GL_UNSIGNED_BYTE,pixels.data());bind(GL_FRAMEBUFFER,previous);
    require(glGetError()==GL_NO_ERROR,"capture GL error");
    FILE* f=std::fopen(path,"wb");require(f!=nullptr,"capture file");std::fprintf(f,"P6\n%d %d\n255\n",w,h);
    for(int y=h-1;y>=0;--y)std::fwrite(pixels.data()+size_t(y)*w*3,1,size_t(w)*3,f);std::fclose(f);
}

static void setting(bool on) {
    FILE* f=std::fopen("pikmin_settings.conf","w");require(f,"private settings");
    std::fprintf(f,"whistlePluck = %d\nwindowWidth = 960\nwindowHeight = 540\ndisplayMode = 0\n",on?1:0);
    std::fclose(f);pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    require(pc_settings_get_whistle_pluck()==int(on),"setting reload");
}
static int sprouts() {
    int count=0;Iterator it(itemMgr->getPikiHeadMgr());CI_LOOP(it) ++count;return count;
}
class PluckApp : public PlugPikiApp {
    int frames=0, phase=0, ticks=0, total=0, before=0;
    float previous=-1;
    Input* input=nullptr;
    std::set<Piki*> original;
    std::vector<Piki*> emerged;
    PikiHeadItem* target=nullptr;
    Vector3f patch;
public:
    int idle() override {
        int result=PlugPikiApp::idle();
        require(++frames<2400,"timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {gameflow.mMoviePlayer->requestSkip();return result;}
        if(!naviMgr || !pikiMgr || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)return result;
        Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState())return result;
        if(phase==0) {
            if(frames<250 || n->getCurrState()->getID()!=NAVISTATE_Walk)return result;
            Iterator it(pikiMgr);CI_LOOP(it) {Piki* p=static_cast<Piki*>(*it);if(p->isAlive())original.insert(p);}
            require(original.size()==20,"fresh live 20-Pikmin squad");
            require(!pc_settings_get_whistle_pluck(),"default must be off");
            input=new Input();n->mKontroller=input;
            patch=n->mCursorWorldPos;patch.y=mapMgr->getMinY(patch.x,patch.z,true);
            for(int i=0;i<4;++i) {
                PikiHeadItem* s=static_cast<PikiHeadItem*>(itemMgr->birth(OBJTYPE_Pikihead));require(s,"spawn sprout");
                Vector3f pos=patch;pos.x+=i*5.0f;
                s->init(pos);s->setColor((pc_p2_purples_enabled() || pc_p2_whites_enabled()) ? Red : i%3);s->mFlowerStage=i%3;s->startAI(0);
                s->mFlowerStage=i%3;
                if(pc_p2_purples_enabled())s->mP2Purple=true;
                if(pc_p2_whites_enabled())s->mP2White=true;
                require(s->canPullout(),"fixture grounded sprout state");if(i==0)target=s;
            }
            int wx,wy,ww,wh;SDL_Window* window=SDL_GL_GetCurrentWindow();SDL_GetWindowPosition(window,&wx,&wy);SDL_GetWindowSize(window,&ww,&wh);
            SDL_Rect bounds;SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window),&bounds);
            std::printf("WINDOW x=%d y=%d w=%d h=%d display=(%d,%d,%d,%d)\n",wx,wy,ww,wh,bounds.x,bounds.y,bounds.w,bounds.h);
            require(ww==960 && wh==540,"window size");capture("whistle-pluck-before.ppm");
            total=GameStat::mapPikis;before=sprouts();require(before==4,"four fixture sprouts");
            held=true;phase=1;ticks=0;
            std::printf("FIXTURE_READY live=20 active=Walk window=%dx%d centered sprouts=4 total=%d\n",pc_window_get_width(),pc_window_get_height(),total);
        } else if(phase==1 && ++ticks>=12) {
            require(sprouts()==before,"disabled real whistle plucked");held=false;
            n->mStateMachine->transit(n,NAVISTATE_Walk);setting(true);
            n->mCursorWorldPos=target->mSRT.t;
            gameflow.mPauseAll=true;require(!pc_whistle_pluck(n,100),"paused pluck");gameflow.mPauseAll=false;
            gameflow.mIsUIOverlayActive=true;require(!pc_whistle_pluck(n,100),"UI pluck");gameflow.mIsUIOverlayActive=false;
            bool movie=gameflow.mMoviePlayer->mIsActive;gameflow.mMoviePlayer->mIsActive=true;
            require(!pc_whistle_pluck(n,100),"movie pluck");gameflow.mMoviePlayer->mIsActive=movie;
            float health=n->mHealth;n->mHealth=0;require(!pc_whistle_pluck(n,100),"dead captain pluck");n->mHealth=health;
            n->mCursorWorldPos.x-=100;require(!pc_whistle_pluck(n,100),"radius boundary");n->mCursorWorldPos=target->mSRT.t;
            n->mCursorWorldPos.y-=25;require(!pc_whistle_pluck(n,100),"vertical boundary");n->mCursorWorldPos=target->mSRT.t;
            int limit=AICONST.mMaxPikisOnField();AICONST.mMaxPikisOnField.mValue=0;
            require(!pc_whistle_pluck(n,100) && sprouts()==before,"failed allocation lost sprout");
            AICONST.mMaxPikisOnField.mValue=total;
            require(pc_whistle_pluck(n,100),"conversion at field limit");AICONST.mMaxPikisOnField.mValue=limit;
            require(sprouts()==before-1,"single conversion");target=nullptr;
            std::puts("GUARDS_PASS disabled-real-whistle pause UI movie dead range height allocation-failure full-cap-conversion");
            phase=2;ticks=0;
        } else if(phase==2 && ++ticks>=10) {
            before=sprouts();held=true;phase=3;ticks=0;
        } else if(phase==3) {
            if(sprouts()<before) {require(sprouts()==before-1,"multiple same-frame plucks");held=false;before=sprouts();phase=4;ticks=0;}
        } else if(phase==4 && ++ticks>=20) {
            require(sprouts()==before,"release kept plucking");held=true;phase=5;previous=-1;
        } else if(phase==5) {
            if(sprouts()<before) {
                require(sprouts()==before-1,"burst instead of stagger");
                const float time=n->mWhistleTimer;
                require(previous<0 || time-previous>=PC_WHISTLE_PLUCK_INTERVAL-0.001f,"cadence too fast");
                std::printf("PLUCK_EVENT held_seconds=%.3f remaining=%d\n",time,sprouts());previous=time;before=sprouts();
                if(!before){held=false;phase=6;ticks=0;capture("whistle-pluck-emerging.ppm");}
            }
        } else if(phase==6 && ++ticks>=150) {
            require(sprouts()==0,"sprout replay");require(emerged.size()==4,"four emergence animations");
            int maturity[3]={};
            for(Piki* p:emerged) {
                require(p->isAlive() && p->getState()==PIKISTATE_Normal && p->mMode==PikiMode::FormationMode && p->mNavi==n,"animation did not join squad");
                require(p->mHappa>=Leaf && p->mHappa<=Flower,"maturity invalid");++maturity[p->mHappa];
                require(p->mColor==((pc_p2_purples_enabled() || pc_p2_whites_enabled()) ? Red : p->mHappa),"color changed");
                require(!pc_p2_purples_enabled() || pc_p2_is_purple(p),"Purple identity lost");
                require(!pc_p2_whites_enabled() || pc_p2_is_white(p),"White identity lost");
            }
            require(maturity[Leaf]==2 && maturity[Bud]==1 && maturity[Flower]==1,"maturity changed");
            require(int(GameStat::mapPikis)==total,"population changed");capture("whistle-pluck-after.ppm");
            std::printf("PASS whistle pluck: native animation, stagger, release, formation, identity, maturity, population=%d\n",total);
            std::fflush(stdout);std::_Exit(0);
        }
        Iterator it(pikiMgr);CI_LOOP(it) {
            Piki* p=static_cast<Piki*>(*it);if(original.count(p))continue;
            if(p->getState()==PIKISTATE_AutoNuki && std::find(emerged.begin(),emerged.end(),p)==emerged.end()) {
                require(p->mPikiAnimMgr.getUpperAnimator().getCurrentMotionIndex()==PIKIANIM_Kaifuku,"wrong emergence motion");emerged.push_back(p);
            }
        }
        std::fflush(stdout);return result;
    }
};
int main(int argc,char** argv) {
    SDL_SetMainReady();SDL_setenv("SDL_AUDIODRIVER","dummy",1);pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"private experimental arena required");
    if(!pc_window_init("Whistle Pluck fixture",960,540))return 3;
    pc_settings_init();pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new PluckApp());return 0;
}
