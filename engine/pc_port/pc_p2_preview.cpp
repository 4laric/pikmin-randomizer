#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "Pellet.h"
#include "PlayerState.h"
#include "MapMgr.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"
#include <SDL2/SDL.h>
#include "gameflow.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Texture.h"
#include "system.h"
#include "pc_p2_economy.h"
#include "pc_p2_purple.h"
#include "pc_p2_cave.h"
#include "pc_p2_enemy.h"
#include "GoalItem.h"
#include "ItemMgr.h"
#include "Generator.h"
#include "teki.h"
#include <map>
#include <string>
#include <cstdio>
#include <cstdlib>

// One disposable room only. This is deliberately not a campaign treasure registry.
static Pellet* previewTreasure = nullptr;
static Shape* previewShape = nullptr;
static bool delivered = false;
static int initialRepairs = 0;
static GoalItem* podAnchor=nullptr;
static Shape* podShape=nullptr;
static P2Economy economy;
static std::string treasureId;
static int treasureValue=0,corpseValue=0;
static std::map<PelletView*,std::string> corpses;
static void podTitle(const std::string& recent) {
    if(SDL_Window* window=SDL_GL_GetCurrentWindow()) {
        std::string title="Pikipelago - Research Pod: "+std::to_string(economy.total())+" Pokos";
        if(!recent.empty())title+=" | "+recent;
        SDL_SetWindowTitle(window,title.c_str());
    }
}
Suckable* pc_p2_preview_goal(){return pc_pikipelago_room_preview()?podAnchor:nullptr;}
bool pc_p2_preview_is_pod(GoalItem* goal){return pc_pikipelago_room_preview() && podAnchor && goal==podAnchor;}
int pc_p2_preview_pokos(){return podAnchor?economy.total():-1;}
bool pc_p2_preview_ready() { return pc_pikipelago_room_preview() && previewShape && previewTreasure; }
Pellet* pc_p2_preview_treasure() { return previewTreasure; }

void pc_p2_preview_setup() {
    if (!pc_pikipelago_room_preview()) return;
    previewTreasure = nullptr; previewShape = nullptr; delivered = false;
    podAnchor=nullptr;podShape=nullptr;corpses.clear();
    initialRepairs = playerState->getCurrParts();
    Iterator it(pelletMgr);
    CI_LOOP(it) {
        Pellet* pellet = static_cast<Pellet*>(*it);
        if (pellet && pellet->mConfig->mModelId.mId == 'pr05') {
            if (previewTreasure) { std::fprintf(stderr,"P2 preview: duplicate treasure\n"); std::abort(); }
            previewTreasure = pellet;
        }
    }
    if (!previewTreasure) { std::fprintf(stderr,"P2 preview: treasure generator missing\n"); std::abort(); }
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    std::printf("[Pikipelago] P2_PREVIEW_HEAP previous=%d map_vertices=%p movie_range=%p..%p\n", previousHeap,
        static_cast<void*>(mapMgr->mMapModel->mVertexList),
        reinterpret_cast<void*>(gsys->mHeaps[SYSHEAP_Movie].mInitialStackTop),
        reinterpret_cast<void*>(gsys->mHeaps[SYSHEAP_Movie].mInitialStackLimit));
    previewShape = gameflow.loadShape("courses/pikmin2room/treasure.mod", true);
    if (!previewShape) { std::fprintf(stderr,"P2 preview: converted treasure missing\n"); std::abort(); }
    // Stage finalSetup can run during rendering, where attachObjs is forbidden.
    // Upload only this late-loaded static model's textures through the PC texture API.
    for (int i=0;i<previewShape->mTexAttrCount;++i)
        if (previewShape->mTexAttrList[i].mTexture) previewShape->mTexAttrList[i].mTexture->attach();
    if(FILE* config=std::fopen("p2-pod.txt","r")) {
        char version[32],id[64],corpseId[64];int weight,capacity;
        bool valid=std::fscanf(config,"%31s %63s %d %d %d %63s %d",version,id,&treasureValue,&weight,&capacity,corpseId,&corpseValue)==7;
        std::fclose(config);
        if(!valid || std::string(version)!="P2_POD_1" || weight<1 || weight>1000 || capacity<1 || capacity>128 || treasureValue<0 || treasureValue>1000000 || corpseValue<0 || corpseValue>1000000 || std::string(corpseId)!="Kochappy") {
            std::fprintf(stderr,"Invalid P2 pod config\n");std::abort();
        }
        treasureId=id;economy.load("p2-economy.txt");
        podAnchor=itemMgr->getContainer(Red);
        if(!podAnchor){std::fprintf(stderr,"P2 pod anchor missing\n");std::abort();}
        previewTreasure->mConfig->mCarryMinPikis.mValue=weight;
        previewTreasure->mConfig->mCarryMaxPikis.mValue=capacity;
        podShape=gameflow.loadShape("courses/pikmin2room/pod.mod",true);
        if(!podShape){std::fprintf(stderr,"P2 pod shape missing\n");std::abort();}
        for(int i=0;i<podShape->mTexAttrCount;++i)if(podShape->mTexAttrList[i].mTexture)podShape->mTexAttrList[i].mTexture->attach();
        Iterator enemies(tekiMgr);CI_LOOP(enemies) {
            Teki* enemy=static_cast<Teki*>(*enemies);
            if(enemy && enemy->mTekiType==TEKI_Chappy && enemy->mGenerator)
                corpses[static_cast<PelletView*>(enemy)]="corpse:"+std::to_string(enemy->mGenerator->_70);
        }
        std::printf("[Pikipelago] P2_POD_READY treasure=%s value=%d weight=%d capacity=%d pokos=%d\n",id,treasureValue,weight,capacity,economy.total());
        podTitle("");
    }
    pc_p2_snow_setup();
    pc_p2_purple_setup();
    pc_p2_cave_setup();
    gsys->setHeap(previousHeap);
    const float points[][2]={{-85,0},{-175,-100},{185,-180},{-220,-180}};
    for (const auto& point : points)
        std::printf("[Pikipelago] P2_ROOM_GROUND x=%.1f z=%.1f y=%.3f\n",point[0],point[1],mapMgr->getMinY(point[0],point[1],true));
    std::printf("[Pikipelago] P2_ROOM_READY treasure=%s carry=%d repairs=%d\n",podAnchor?treasureId.c_str():"bolt",previewTreasure->mConfig->mCarryMinPikis(),initialRepairs);
    std::fflush(stdout);
}

bool pc_p2_preview_draw(Pellet* pellet, Graphics& gfx, Matrix4f& matrix) {
    if (!pc_pikipelago_room_preview() || pellet != previewTreasure || !previewShape || pellet->mConfig->mModelId.mId != 'pr05') return false;
    previewShape->updateAnim(gfx,matrix,nullptr,pellet);
    previewShape->drawshape(gfx,*gfx.mCamera,nullptr);
    return true;
}

bool pc_p2_preview_deliver(Pellet* pellet) {
    if(pc_pikipelago_room_preview() && podAnchor) {
        // P1's long-idle captain can be carried like a pellet. Returning him to
        // the Pod must finish the normal wake-up path, never create money/seeds.
        if(naviMgr && pellet->mConfig->mModelId.mId=='navi' && pellet->mPelletView==static_cast<PelletView*>(naviMgr->getNavi())) {
            std::puts("[Pikipelago] P2_POD_CAPTAIN_RETURN pokos_unchanged=1 seeds=0");return true;
        }
        std::string receipt;int value=0;
        if(pellet==previewTreasure){receipt="treasure:"+treasureId;value=treasureValue;}
        else {
            auto found=corpses.find(pellet->mPelletView);
            if(found==corpses.end()) {std::fprintf(stderr,"Unregistered P2 pod cargo id=%08x view=%p pellet=%p treasure=%p; refusing seed side effects\n",pellet->mConfig->mModelId.mId,(void*)pellet->mPelletView,(void*)pellet,(void*)previewTreasure);std::abort();}
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+found->second.substr(7);value=corpseValue;
        }
        bool added=economy.credit(receipt,value);
        podTitle((pellet==previewTreasure?treasureId:(pc_p2_enemy_name(pellet->mPelletView)?pc_p2_enemy_name(pellet->mPelletView):"Dwarf Bulborb"))+" +"+std::to_string(added?value:0));
        pc_p2_purple_status();
        std::printf("[Pikipelago] P2_POD_RECEIPT id=%s value=%d new=%d pokos=%d seeds=0\n",receipt.c_str(),value,int(added),economy.total());
        if(pellet==previewTreasure) {
            delivered=true;
            if(FILE* file=std::fopen("treasure-receipt.txt","w")){std::fprintf(file,"treasure=%s count=1 pokos=%d\n",treasureId.c_str(),economy.total());std::fclose(file);}
        }
        if(playerState->getCurrParts()!=initialRepairs){std::fprintf(stderr,"P2 pod changed repairs\n");std::abort();}
        std::fflush(stdout);return true;
    }
    if (!pc_pikipelago_room_preview() || pellet != previewTreasure || pellet->mConfig->mModelId.mId != 'pr05') return false;
    if (!delivered) {
        delivered = true;
        const int repairs = playerState->getCurrParts();
        if (repairs != initialRepairs) { std::fprintf(stderr,"P2 preview: unexpected repair progression\n"); std::abort(); }
        if (FILE* file=std::fopen("treasure-receipt.txt","w")) {
            std::fprintf(file,"room=room_4x4a_4_conc treasure=bolt count=1 repairs=%d\n",repairs);
            std::fclose(file);
        }
        std::printf("[Pikipelago] P2_TREASURE_DELIVERED id=bolt count=1 repairs=%d seeds=0\n",repairs);
        std::fflush(stdout);
    }
    return true;
}

bool pc_p2_preview_draw_pod(GoalItem* goal,Graphics& gfx,Matrix4f& matrix) {
    if(!pc_p2_preview_is_pod(goal) || !podShape)return false;
    // Static visual uses the existing destination's suction height; animation is deferred.
    Matrix4f world,view;Vector3f position=goal->mSRT.t;position.y+=74;
    world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),position);
    gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
    podShape->updateAnim(gfx,view,nullptr,goal);podShape->drawshape(gfx,*gfx.mCamera,nullptr);
    return true;
}
