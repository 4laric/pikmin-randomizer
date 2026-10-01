// Reuse only private fixture initialization/capture helpers, not its app.
#define main groink_unused_fixture_main
#include "p2_groink_target_runtime.cpp"
#undef main
#include "Texture.h"
#include "sysNew.h"
#include "Piki.h"
#include "../pc_port/pc_p2_demon_attachment.h"

class DemonVisualApp final : public PlugPikiApp {
    Shape* models[2]{};
    Vector3f mouths[2][2];
    P2DemonMatrix mouthMatrices[2][2];
    int frames=0, ticks=0;
    bool ready=false;
public:
    int idle() override {
        int result=PlugPikiApp::idle(); require(++frames<1800,"Demon timeout");
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip(); return result;
        }
        if(!pc_p2_preview_ready()||!naviMgr||!naviMgr->getNavi()) return result;
        if(!ready) {
            std::ifstream in("demon-mouths.txt");
            for(int pose=0;pose<2;++pose) for(int slot=0;slot<2;++slot) {
                auto& m=mouthMatrices[pose][slot];
                for(auto& row:m.m) for(float& x:row) in>>x;
                require(bool(in)&&p2_demon_attachment_pose(m).valid,"mouth input");
                mouths[pose][slot].set(m.m[0][3],m.m[1][3],m.m[2][3]);
            }
            const int heap=gsys->setHeap(SYSHEAP_App);
            models[0]=gameflow.loadShape("courses/pikmin2room/demon0.mod",true);
            models[1]=gameflow.loadShape("courses/pikmin2room/demon17.mod",true);
            for(auto model:models) {
                require(model!=nullptr,"Demon model");
                for(int i=0;i<model->mTexAttrCount;++i)
                    if(model->mTexAttrList[i].mTexture) model->mTexAttrList[i].mTexture->attach();
            }
            gsys->setHeap(heap); ready=true;
        }
        naviMgr->getNavi()->resetPosition(Vector3f(0,0,100));
        ++ticks; return result;
    }
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx); if(!ready) return;
        const int pose=ticks<60?0:1;
        gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1);
        gfx.useMaterial(nullptr); gfx.setDepth(true);
        Matrix4f world,view;
        world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),Vector3f(0,100,0));
        gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
        models[pose]->updateAnim(gfx,view,nullptr,nullptr);
        models[pose]->drawshape(gfx,*gfx.mCamera,nullptr);
        gfx.useMaterial(nullptr);
        for(int slot=0;slot<2;++slot) {
            const auto p=mouths[pose][slot];
            gfx.setColour(slot?Colour(0,80,255,255):Colour(255,0,0,255),true);
            gfx.drawSphere(Vector3f(p.x,p.y+100,p.z),3,gfx.mCamera->mLookAtMtx);
            auto mouth=mouthMatrices[pose][slot]; mouth.m[1][3]+=100;
            auto attached=p2_demon_attachment_pose(mouth);
            require(attached.valid,"captain pose");
            Matrix4f captainWorld,captainView; captainWorld.makeIdentity();
            for(int r=0;r<3;++r) for(int c=0;c<4;++c) captainWorld.mMtx[r][c]=attached.matrix.m[r][c];
            gfx.mCamera->mLookAtMtx.multiplyTo(captainWorld,captainView);
            auto* navi=naviMgr->getNavi();
            require(navi&&navi->mNaviShapeObject,"captain shape");
            navi->mNaviAnimMgr.updateContext();
            gfx.useMaterial(nullptr);
            navi->mNaviShapeObject->mShape->updateAnim(gfx,captainView,nullptr,navi);
            navi->mNaviShapeObject->mShape->drawshape(gfx,*gfx.mCamera,nullptr);
        }
        if(ticks==30||ticks==90) {
            capture(pose?"demon17.ppm":"demon0.ppm");
            std::printf("DEMON_VISUAL_CAPTURE frame=%d markers=2 no_attachment=1\n",pose?17:0);
            std::puts("DEMON_CAPTAIN_SHAPES count=2 display_only=1 ordinary_animation=1");
        }
        if(ticks>=90) { std::puts("PASS DEMON_VISUAL"); std::fflush(stdout); std::_Exit(0); }
    }
};
int main(int argc,char** argv) {
    SDL_setenv("SDL_AUDIODRIVER","dummy",1); SDL_SetMainReady(); pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND","1"); pc_bbft_init(argc,argv);
    require(pc_pikipelago_room_preview(),"room flag");
    require(pc_window_init("Demon mouth visual fixture",960,720),"window init");
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr=new NodeMgr();
    gsys->run(new DemonVisualApp()); return 0;
}

