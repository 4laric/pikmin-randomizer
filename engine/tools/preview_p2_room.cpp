// Isolated integration fixture: real movement and transport AI, no production input changes.
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
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "Pellet.h"
#include "PelletState.h"
#include "MapMgr.h"
#include "Camera.h"
#include "LifeGauge.h"
#include "Light.h"
#include "Shape.h"
#include "Material.h"
#include "Mesh.h"
#include "PlayerState.h"
#include "Demo.h"
#include "teki.h"
#include "pc_p2_preview.h"
#include "pc_window.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
static int phase=0,ticks=0;
static bool assembled=false;
static bool secondFloor=false;
static std::vector<Vector3f> walkGoals;
static int walkPoint=0;
static Vector3f origin;
static bool corpseLifecycle=false, corpseApproach=false, combatWalking=false;
static Vector3f combatDestination;
static void require(bool value,const char* message) { if(!value) { std::printf("FAIL p2 room: %s\n",message);std::fflush(stdout);std::_Exit(1); } }
static void verifyCarryDigits() {
    GaugeInfo gauge;
    LFlareGroup* group=lgMgr->mDigitFlareGroup;
    for(int value : {0,9,10,99,100,101,1000}) {
        LFInfo* previous=group->mLFInfo;
        Colour white(255,255,255,255);
        gauge.showDigits(Vector3f(0,0,0),white,value,8,8);
        int actual=0,count=0;float sum=0;
        for(LFInfo* f=group->mLFInfo;f!=previous;f=f->mPrevInfo) {
            require(f!=nullptr,"missing carry digit");
            actual=actual*10+int(std::round(f->mUvMin.x*11));
            sum+=f->mFlarePos.x;++count;
        }
        require(actual==value && count==(value>=1000?4:value>=100?3:value>=10?2:1),"carry digit value/count");
        require(std::fabs(sum)<0.001f,"carry number not centered");
        group->mLFInfo=previous;
    }
    std::puts("P2_CARRY_DIGITS_PASS 0 9 10 99 100 101 1000: actual flare UVs and centering");
}
// Navi::update polls its controller after GameCoreSection::updateAI starts.
// Override that virtual poll in the standalone fixture, never production input.
class FixtureController : public Kontroller {
public:
    FixtureController() : Kontroller(1) {}
    void update() override {
        updateCont((phase==1 || phase==7)?KBBTN_MSTICK_RIGHT:0);
        mMainStickX=(phase==1 || phase==7)?74:0; mMainStickY=0;
        if((assembled || secondFloor) && (phase==1 || phase==7) && naviMgr) {
            Navi* n=naviMgr->getNavi();
            if(n && n->mNaviCamera) {
                float dx=walkGoals[walkPoint].x-n->mSRT.t.x,dz=walkGoals[walkPoint].z-n->mSRT.t.z;
                float distance=std::sqrt(dx*dx+dz*dz);
                if(distance<20 && walkPoint+1<int(walkGoals.size()))++walkPoint;
                if(distance>1) {
                    const Vector3f& axis=n->mNaviCamera->mViewXAxis;
                    mMainStickX=static_cast<signed char>(65*(dx*axis.x+dz*axis.z)/distance);
                    mMainStickY=static_cast<signed char>(65*(dx*axis.z-dz*axis.x)/distance);
                }
            }
        }
        mSubStickX=0; mSubStickY=0;
        if(combatWalking && naviMgr) {
            Navi* n=naviMgr->getNavi();
            if(n && n->mNaviCamera) {
                float dx=combatDestination.x-n->mSRT.t.x,dz=combatDestination.z-n->mSRT.t.z;
                float distance=std::sqrt(dx*dx+dz*dz);
                if(distance>1) {
                    const Vector3f& axis=n->mNaviCamera->mViewXAxis;
                    updateCont(KBBTN_MSTICK_RIGHT);
                    mMainStickX=static_cast<signed char>(65*(dx*axis.x+dz*axis.z)/distance);
                    mMainStickY=static_cast<signed char>(65*(dx*axis.z-dz*axis.x)/distance);
                }
            }
        }
    }
};
static unsigned hashBytes(const void* data,size_t size,unsigned hash=2166136261u) {
    const unsigned char* bytes=static_cast<const unsigned char*>(data);
    for(size_t i=0;i<size;++i)hash=(hash^bytes[i])*16777619u;
    return hash;
}
static void cameraLog(Navi* n,const char* tag) {
    Camera* c=n->mNaviCamera;if(!c)return;
    if(mapMgr->mMapModel && mapMgr->mMapModel->mJointCount>0) {
        Shape* model=mapMgr->mMapModel;
        for(int i=model->mTotalMatpolyCount-1;i>=0;--i){
            Material* m=model->mMatpolyList[i]->mMaterial;
            std::printf("P2_MATERIAL_%s index=%u flags=%x pixel=%x,%x,%x,%x\n",tag,m->mIndex,m->mFlags,m->mPeInfo.mControlFlags,m->mPeInfo.mAlphaCompareFlags,m->mPeInfo.mDepthTestFlags,m->mPeInfo.mBlendModeFlags);
        }
        unsigned vertices=hashBytes(model->mVertexList,sizeof(Vector3f)*(model->mVertexCount<350?model->mVertexCount:350));
        unsigned lists=2166136261u;
        for(int m=0;m<model->mMeshCount;++m)for(int g=0;g<model->mMeshList[m].mMtxGroupCount;++g){
            MtxGroup& group=model->mMeshList[m].mMtxGroupList[g];
            for(int d=0;d<group.mDispLength;++d)lists=hashBytes(group.mDispList[d].mData,group.mDispList[d].mDataLength,lists);
        }
        AnimContext* animation=model->mCurrentAnimation;
        std::printf("P2_MODEL_%s vertices=%d first350hash=%08x dlhash=%08x animation=%p frame=%.3f flags=%d frames=%d matrices=%p\n",tag,model->mVertexCount,vertices,lists,(void*)animation,animation?animation->mCurrentFrame:-1.f,animation&&animation->mData?animation->mData->mAnimFlags:-1,animation&&animation->mData?animation->mData->mTotalFrameCount:-1,(void*)model->mAnimMatrices);
        const Matrix4f& root=model->mAnimMatrices?model->mAnimMatrices[0]:model->mJointList[0].mAnimMatrix;
        float difference=0;
        for(int row=0;row<3;++row) {
            std::printf("P2_MATRIX_%s row=%d root=%.4f,%.4f,%.4f,%.4f view=%.4f,%.4f,%.4f,%.4f\n",tag,row,root.mMtx[row][0],root.mMtx[row][1],root.mMtx[row][2],root.mMtx[row][3],c->mLookAtMtx.mMtx[row][0],c->mLookAtMtx.mMtx[row][1],c->mLookAtMtx.mMtx[row][2],c->mLookAtMtx.mMtx[row][3]);
            for(int col=0;col<4;++col)difference+=std::fabs(root.mMtx[row][col]-c->mLookAtMtx.mMtx[row][col]);
        }
        std::printf("P2_MATRIX_%s absolute_difference=%.6f\n",tag,difference);
    }
    std::printf("P2_CAMERA_%s pos=%.3f,%.3f,%.3f ground=%.3f yaxis=%.3f,%.3f,%.3f zaxis=%.3f,%.3f,%.3f\n",tag,c->mPosition.x,c->mPosition.y,c->mPosition.z,mapMgr->getMinY(c->mPosition.x,c->mPosition.z,true),c->mViewYAxis.x,c->mViewYAxis.y,c->mViewYAxis.z,c->mViewZAxis.x,c->mViewZAxis.y,c->mViewZAxis.z);
}
static void capture(const char* path="p2-room.ppm") {
    auto bind=reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    GLint previous=0;glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous);bind(GL_FRAMEBUFFER,0);
    int w=0,h=0;SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(),&w,&h);
    std::vector<unsigned char> pixels(size_t(w)*h*3);glPixelStorei(GL_PACK_ALIGNMENT,1);glReadBuffer(GL_BACK);
    glReadPixels(0,0,w,h,GL_RGB,GL_UNSIGNED_BYTE,pixels.data());bind(GL_FRAMEBUFFER,previous);
    require(glGetError()==GL_NO_ERROR,"capture GL error");
    FILE* f=std::fopen(path,"wb");require(f!=nullptr,"capture file");std::fprintf(f,"P6\n%d %d\n255\n",w,h);
    for(int y=h-1;y>=0;--y)std::fwrite(pixels.data()+size_t(y)*w*3,1,size_t(w)*3,f);std::fclose(f);
}
#include "preview_p2_purple.inc"
#include "preview_p2_beasts_floor2.inc"
#include "preview_p2_purple_impact.inc"
#include "preview_p2_white.inc"
#include "preview_p2_cargo.inc"
#include "preview_p2_cave.inc"
#include "preview_p2_snow.inc"
class RoomApp : public PlugPikiApp {
    int frames=0,repairs=0;
    Teki* enemy=nullptr;
    Pellet* corpse=nullptr;
    Vector3f corpseOrigin;
    bool corpseReachedGoal=false; float corpseDistance=0;
    // Observe before fixture phase/UI gates: autonomous combat and hauling can
    // happen while the scripted treasure phase is still in progress.
    Teki* observedEnemy=nullptr;
    Pellet* observedCorpse=nullptr;
    bool observedDead=false, observedRemoved=false;
    int observedState=-1;
    Vector3f observedOrigin;
    float observedDistance=0;
    void observeCorpse() {
        if(!corpseLifecycle || !tekiMgr || !pelletMgr || pc_p2_purples_enabled() || pc_p2_cave_floor())return;
        if(!observedEnemy) {
            Iterator enemies(tekiMgr);CI_LOOP(enemies) {
                Teki* v=static_cast<Teki*>(*enemies);
                if(v->isAlive() && v->mTekiType==TEKI_Chappy) {
                    require(!observedEnemy,"ambiguous corpse observation enemy");observedEnemy=v;
                    std::printf("P2_LIFECYCLE_ENEMY frame=%d phase=%d enemy=%p generator=%p x=%.2f y=%.2f z=%.2f\n",frames,phase,(void*)v,(void*)v->mGenerator,v->mSRT.t.x,v->mSRT.t.y,v->mSRT.t.z);
                }
            }
        }
        if(!observedEnemy || observedRemoved)return;
        if(frames%150==0 && !observedCorpse) {
            Teki* v=observedEnemy;
            std::printf("P2_LIFECYCLE_ANIMATION frame=%d counter=%.3f grid_culled=%d frozen=%d\n",frames,v->mTekiAnimator->getCounter(),int(v->mGrid.aiCulling()),int(v->mIsFrozen));
            std::printf("P2_LIFECYCLE_PENDING frame=%d phase=%d enemy=%p alive=%d health=%.2f dead_state=%d ai_state=%d motion=%d finished=%d speed=%.2f culled=%d updatable=%d bound=%p x=%.2f y=%.2f z=%.2f\n",frames,phase,(void*)v,int(v->isAlive()),v->mHealth,v->mDeadState,int(v->mStateID),v->mTekiAnimator->getCurrentMotionIndex(),int(v->animationFinished()),v->mAnimationSpeed,int(v->isCreatureFlag(CF_UseAICulling)),int(v->mOptUpdateContext.updatable()),(void*)v->mPellet,v->mSRT.t.x,v->mSRT.t.y,v->mSRT.t.z);
        }
        if(!observedDead && !observedEnemy->isAlive()) {
            observedDead=true;
            std::printf("P2_LIFECYCLE_DEATH frame=%d phase=%d enemy=%p health=%.2f\n",frames,phase,(void*)observedEnemy,observedEnemy->mHealth);
        }
        Pellet* live=nullptr;
        Iterator pellets(pelletMgr);CI_LOOP(pellets) {
            Pellet* p=static_cast<Pellet*>(*pellets);
            if(p->isAlive() && p->mPelletView==static_cast<PelletView*>(observedEnemy)){require(!live,"duplicate corpse identity");live=p;}
        }
        if(live) {
            require(!observedCorpse || observedCorpse==live,"corpse identity changed");
            if(!observedCorpse) {
                observedCorpse=live;observedOrigin=live->mSRT.t;
                std::printf("P2_LIFECYCLE_BIRTH frame=%d phase=%d enemy=%p pellet=%p x=%.2f y=%.2f z=%.2f\n",frames,phase,(void*)observedEnemy,(void*)live,observedOrigin.x,observedOrigin.y,observedOrigin.z);
            }
            float dx=live->mSRT.t.x-observedOrigin.x,dz=live->mSRT.t.z-observedOrigin.z;
            float distance=std::sqrt(dx*dx+dz*dz);if(distance>observedDistance)observedDistance=distance;
            if(observedState!=live->getState()) {
                observedState=live->getState();
                std::printf("P2_LIFECYCLE_STATE frame=%d phase=%d pellet=%p state=%d distance=%.2f goal=%p x=%.2f y=%.2f z=%.2f\n",frames,phase,(void*)live,observedState,observedDistance,(void*)live->mTargetGoal,live->mSRT.t.x,live->mSRT.t.y,live->mSRT.t.z);
            }
        } else if(observedCorpse) {
            observedRemoved=true;
            std::printf("P2_LIFECYCLE_REMOVED frame=%d phase=%d pellet=%p last_state=%d distance=%.2f\n",frames,phase,(void*)observedCorpse,observedState,observedDistance);
        }
        std::fflush(stdout);
    }
public:
    int idle() override {
        int result=PlugPikiApp::idle();require(++frames<10000,"timeout");
        observeCorpse();
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(beastsFloor2Enabled && pc_p2_preview_cargo_free_ready()) {
            if(!naviMgr || !pikiMgr || !tekiMgr || !bossMgr || !itemMgr || !pelletMgr)return result;
            Navi* n=naviMgr->getNavi();
            if(n && n->getCurrState() && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive)beastsFloor2Fixture(n);
            return result;
        }
        if(!pc_p2_preview_ready() || !naviMgr || !pikiMgr || !tekiMgr)return result;
        Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState() || (!pc_p2_purples_enabled() && phase<=1 && n->getCurrState()->getID()!=NAVISTATE_Walk) || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)return result;
        static bool digitsVerified=false;
        if(!digitsVerified){verifyCarryDigits();digitsVerified=true;}
        if(cargoCarryFixture(n))return result;
        if(snowRenderFixture(n))return result;
        if(pc_p2_cave_floor()){caveFixture(n);std::fflush(stdout);return result;}
        if(pc_p2_whites_enabled()){whiteFixture(n);std::fflush(stdout);return result;}
        if(pc_p2_purple_impact_enabled()){purpleImpactFixture(n);std::fflush(stdout);return result;}
        if(pc_p2_purples_enabled()){purpleFixture(n);std::fflush(stdout);return result;}
        if(phase==0) {
            if(++ticks<60)return result;
            for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
            int reds=0,dwarfs=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive() && v->mColor==Red)++reds;}
            Iterator e(tekiMgr);CI_LOOP(e){Teki* v=static_cast<Teki*>(*e);if(v->isAlive() && v->mTekiType==TEKI_Chappy){++dwarfs;enemy=v;}}
            if(corpseLifecycle)require(enemy && enemy==observedEnemy,"scripted enemy differs from lifecycle identity");
            cameraLog(n,"START");capture("p2-room-start.ppm");
            std::printf("P2_FIXTURE_COUNTS reds=%d dwarfs=%d\n",reds,dwarfs);
            require(reds==20,"expected twenty field reds");require(dwarfs==(secondFloor?0:1),"unexpected dwarf fixture count");
            float points[][2]={{-85,0},{-175,-100},{185,-180},{-220,-180}};
            if(FILE* positions=std::fopen("p2-probe-positions.txt","r")) {
                for(auto& p:points)require(std::fscanf(positions,"%f %f",&p[0],&p[1])==2 && std::isfinite(p[0]) && std::isfinite(p[1]),"ground position fixture framing");
                std::fclose(positions);
            }
            float expected[4]={0,0,0,0};
            if(FILE* ground=std::fopen("p2-ground.txt","r")) {
                require(std::fscanf(ground,"%f %f %f %f",&expected[0],&expected[1],&expected[2],&expected[3])==4,"ground fixture framing");
                std::fclose(ground);
            }
            for(int i=0;i<4;++i)require(std::isfinite(expected[i]) && std::fabs(mapMgr->getMinY(points[i][0],points[i][1],true)-expected[i])<0.05f,"native ground differs from decoded fixture terrain");
            n->mKontroller=new FixtureController();
            repairs=playerState->getCurrParts();origin=n->mSRT.t;phase=1;ticks=0;
            if(pc_p2_preview_goal())require(pc_p2_preview_pokos()==0,"new Pod fixture must start with empty ledger");
            if(pc_p2_preview_goal()) {
                int index=0;Iterator mixed(pikiMgr);CI_LOOP(mixed) {
                    Piki* v=static_cast<Piki*>(*mixed);if(!v->isAlive())continue;
                    int color=index++%3;v->setColor(color);require(v->mColor==color,"mixed Pod squad colors unavailable");
                }
                std::puts("P2_POD_MIXED_SQUAD blue/red/yellow, normal carrying strength");
            }
            std::puts("P2_FIXTURE_ACTORS_GROUND_PASS");
        } else if(phase==1 && ++ticks>=((assembled||secondFloor)?1800:60)) {
            require(!assembled && !secondFloor,"controller did not finish terrain route before timeout");
        }
        bool arrived=secondFloor ? (walkPoint+1==int(walkGoals.size()) && std::fabs(n->mSRT.t.x-walkGoals.back().x)<25 && std::fabs(n->mSRT.t.z-walkGoals.back().z)<25)
                                : (assembled?(walkPoint==3 && n->mSRT.t.z>890 && std::fabs(n->mSRT.t.x)<30):ticks>=60);
        if(phase==1 && arrived) {
            float dx=n->mSRT.t.x-origin.x,dz=n->mSRT.t.z-origin.z;
            std::printf("P2_MOVE_DEBUG origin=%.2f,%.2f,%.2f now=%.2f,%.2f,%.2f stick=%d,%d main=%.2f,%.2f vel=%.2f,%.2f target=%.2f,%.2f flags=%u state=%d\n",origin.x,origin.y,origin.z,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,int(n->mKontroller->mMainStickX),int(n->mKontroller->mMainStickY),n->mMainStick.x,n->mMainStick.z,n->mVelocity.x,n->mVelocity.z,n->mTargetVelocity.x,n->mTargetVelocity.z,n->mKontroller->mCurrentInput,n->getCurrState()->getID());
            require(dx*dx+dz*dz>4,"controller movement failed");require(std::fabs(n->mSRT.t.y-mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true))<5,"captain left floor");
            std::printf("P2_FIXTURE_MOVEMENT_PASS distance=%.2f\n",std::sqrt(dx*dx+dz*dz));
            if(assembled)require(n->mSRT.t.z>890 && origin.z<350,"captain did not cross both seams");
            cameraLog(n,"MOVED");capture("p2-room-moved.ppm");
            if(FILE* renderOnly=std::fopen("p2-render-only.txt","r")){std::fclose(renderOnly);std::puts("PASS p2 render: ground, movement and two camera captures");std::fflush(stdout);std::_Exit(0);}
            Pellet* target=pc_p2_preview_treasure();int count=0;Iterator p(pikiMgr);CI_LOOP(p){
                Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
                v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Transport;
                v->mActiveAction->mChildActions[PikiAction::Transport].initialise(target);v->mMode=PikiMode::TransportMode;++count;
            }
            require(count>=5,"insufficient carriers");phase=2;ticks=0;
            std::puts("P2_FIXTURE_TRANSPORT_ASSIGNED real AI, positions unchanged");
        } else if(phase==2) {
            if(FILE* f=std::fopen("treasure-receipt.txt","r")) {
                std::fclose(f);require(playerState->getCurrParts()==repairs,"treasure changed repairs");
                if(pc_p2_preview_goal())require(pc_p2_preview_pokos()==180,"Citrus Lump must award 180 Pokos");
                if(secondFloor) {
                    cameraLog(n,"FINAL");capture();
                    std::puts("PASS p2 second floor: decoded terrain, controller slope traversal and native return delivery; no combat or cave lifecycle claim");
                    std::fflush(stdout);std::_Exit(0);
                }
                std::puts("P2_FIXTURE_DELIVERY_PASS"); phase=3; ticks=0;
                if(corpseApproach){combatDestination=enemy->mSRT.t;combatWalking=true;}
            }
            require(++ticks<5000,"native transport did not deliver");
        } else if(phase==3 && corpseApproach && (combatWalking || ticks==0)) {
            // Keep the real death animation inside the captain's active area.
            // Do not disable culling or force corpse birth to satisfy this test.
            combatDestination=enemy->mSRT.t;
            float dx=combatDestination.x-n->mSRT.t.x,dz=combatDestination.z-n->mSRT.t.z;
            combatWalking=dx*dx+dz*dz>120*120;
            if(!combatWalking) {
                std::printf("P2_CORPSE_CAPTAIN_APPROACH frame=%d distance=%.2f x=%.2f z=%.2f controller_only=1\n",frames,std::sqrt(dx*dx+dz*dz),n->mSRT.t.x,n->mSRT.t.z);
                ticks=1;
            } else require(++ticks<900,"captain combat approach stalled");
        } else if(phase==3 && ++ticks>=90) {
            Iterator p(pikiMgr);int attackers=0;CI_LOOP(p){
                Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
                v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
                v->mActiveAction->mChildActions[PikiAction::Attack].initialise(enemy);v->mMode=PikiMode::AttackMode;++attackers;
            }
            require(attackers>0,"no attackers after delivery");phase=4;ticks=0;
            std::printf("P2_FIXTURE_ATTACK_ASSIGNED count=%d\n",attackers);
        } else if(phase==4) {
            if(!enemy->isAlive()) {
                std::puts("P2_FIXTURE_COMBAT_PASS");phase=5;ticks=0;
            }
            if(++ticks%300==0)std::printf("P2_COMBAT_PROGRESS health=%.2f\n",enemy->mHealth);
            require(ticks<3000,"native combat did not kill dwarf");
        } else if(phase==5) {
            Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);if(p->isAlive() && p->mPelletView==static_cast<PelletView*>(enemy)){corpse=p;break;}}
            if(corpse) {
                corpseOrigin=corpse->mSRT.t;
                Iterator pikis(pikiMgr);int freeCount=0;CI_LOOP(pikis){Piki* p=static_cast<Piki*>(*pikis);if(p->isAlive()){p->changeMode(PikiMode::FreeMode,n);++freeCount;}}
                std::printf("P2_CORPSE_FREE_RECRUIT count=%d x=%.2f z=%.2f model=%08x\n",freeCount,corpseOrigin.x,corpseOrigin.z,corpse->mConfig->mModelId.mId);
                phase=6;ticks=0;
            }
            require(++ticks<600,"corpse pellet did not appear after enemy death");
        } else if(phase==6) {
            float dx=corpse->mSRT.t.x-corpseOrigin.x,dz=corpse->mSRT.t.z-corpseOrigin.z;
            float distance=std::sqrt(dx*dx+dz*dz);if(distance>corpseDistance)corpseDistance=distance;
            corpseReachedGoal=corpseReachedGoal || corpse->getState()==PELSTATE_Goal;
            if(++ticks%150==0) {
                int transport=0,free=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->mMode==PikiMode::TransportMode)++transport;if(v->mMode==PikiMode::FreeMode)++free;}
                std::printf("P2_CORPSE_PROGRESS state=%d alive=%d x=%.2f y=%.2f z=%.2f distance=%.2f transport=%d free=%d goal=%p\n",corpse->getState(),int(corpse->isAlive()),corpse->mSRT.t.x,corpse->mSRT.t.y,corpse->mSRT.t.z,corpseDistance,transport,free,(void*)corpse->mTargetGoal);
                capture("p2-room-corpse.ppm");
                if(ticks==150 && transport<corpse->mConfig->mCarryMinPikis()) {
                    Iterator recruits(pikiMgr);int count=0;CI_LOOP(recruits){Piki* p=static_cast<Piki*>(*recruits);if(!p->isAlive())continue;
                        p->mActiveAction->abandon(nullptr);p->mActiveAction->mCurrActionIdx=PikiAction::Transport;
                        p->mActiveAction->mChildActions[PikiAction::Transport].initialise(corpse);p->mMode=PikiMode::TransportMode;++count;
                    }
                    std::printf("P2_CORPSE_RECRUIT_FALLBACK direct transport assigned=%d; no teleport, route regression only\n",count);
                }
            }
            if(!corpse->isAlive()) {
                if(pc_p2_preview_goal())require(pc_p2_preview_pokos()==182 && playerState->getCurrParts()==repairs,"corpse must add two Pokos without repairs");
                require(corpseReachedGoal && corpseDistance>(assembled?1000:100),"corpse disappeared without traversing room and entering Onion goal");
                const float ground=mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true);
                std::printf("P2_FINAL_POSITION x=%.3f y=%.3f z=%.3f ground=%.3f velocity=%.3f,%.3f stick=%d,%d\n",n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,ground,n->mVelocity.x,n->mVelocity.z,int(n->mKontroller->mMainStickX),int(n->mKontroller->mMainStickY));
                cameraLog(n,"FINAL");capture();
                require(std::fabs(n->mSRT.t.x)<=340 && std::fabs(n->mSRT.t.z)<=(assembled?1360:340),"captain outside room bounds");
                require(std::fabs(n->mSRT.t.y-ground)<5 && std::fabs(ground)<0.05f,"captain final position not on room floor");
                if(pc_p2_preview_goal() && assembled) {
                    walkGoals.clear();for(float z:{800.f,510.f,275.f,0.f,-250.f})walkGoals.push_back(Vector3f(0,0,z));
                    walkPoint=0;phase=7;ticks=0;
                } else {
                    std::puts("PASS p2 room: actors, ground, controller movement, native carry delivery, unchanged repairs, native combat kill, far corpse transport and delivery");std::fflush(stdout);std::_Exit(0);
                }
            }
            require(ticks<1800,"far corpse carrying stalled or gave up");
        } else if(phase==7) {
            if(walkPoint+1==int(walkGoals.size()) && std::fabs(n->mSRT.t.z+250)<25) {
                capture("p2-pod-return.ppm");
                require(pc_p2_preview_pokos()==182,"Pod balance changed on walk back");
                std::puts("PASS p2 Pod: mixed-color native treasure and corpse delivery, 182 Pokos, unchanged repairs, controller return to Pod");
                std::fflush(stdout);std::_Exit(0);
            }
            require(++ticks<1800,"return walk to Pod stalled");
        }
        std::fflush(stdout);return result;
    }
};
int main(int argc,char** argv) {
    // Automated fixture only: keep the real mixer/timing, never open a speaker device.
    SDL_setenv("SDL_AUDIODRIVER","dummy",1);
    if(FILE* marker=std::fopen("p2-beasts-floor2-fixture.txt","r")) {
        char header[64],extra;
        require(std::fscanf(marker,"%63s",header)==1,"missing Beasts fixture marker");
        if(std::string(header)=="P2_BEASTS_FLOOR2_FIXTURE_2") {
            char population[32];require(std::fscanf(marker,"%31s",population)==1,"missing Beasts generation context");
            std::string digits(population);
            require(digits.size()<=10 && digits.find_first_not_of("0123456789")==std::string::npos,"invalid Beasts population");
            unsigned long long count=std::strtoull(population,nullptr,10);require(count<=2147483647ULL,"Beasts population overflow");
            beastsGlobalPurple=int(count);beastsExpectedFlowers=count<20?2:0;
        } else require(std::string(header)=="P2_BEASTS_FLOOR2_FIXTURE_1","invalid Beasts fixture version");
        require(std::fscanf(marker," %c",&extra)==EOF,"trailing Beasts fixture data");
        beastsFloor2Enabled=true;std::fclose(marker);
    }
    if(FILE* marker=std::fopen("p2-corpse-lifecycle.txt","r")) {
        corpseLifecycle=true;corpseApproach=std::fgetc(marker)=='1';std::fclose(marker);
    }
    for(float z:{275.f,510.f,800.f,920.f})walkGoals.push_back(Vector3f(0,0,z));
    if(FILE* marker=std::fopen("p2-assembled.txt","r")){assembled=true;std::fclose(marker);}
    if(FILE* route=std::fopen("p2-second-floor.txt","r")) {
        secondFloor=true;walkGoals.clear();int count=0;
        require(std::fscanf(route,"%d",&count)==1 && count>0 && count<=32,"walk fixture count");
        for(int i=0;i<count;++i){float x,z;require(std::fscanf(route,"%f %f",&x,&z)==2 && std::isfinite(x) && std::isfinite(z),"walk fixture point");walkGoals.push_back(Vector3f(x,0,z));}
        std::fclose(route);
    }
    SDL_SetMainReady();pc_gpu_preference_apply();_putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1");pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"requires --experimental-pikmin2-room");
    if(!pc_window_init("P2 room integration fixture",960,720))return 3;
    pc_settings_init();gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new RoomApp());return 0;
}
