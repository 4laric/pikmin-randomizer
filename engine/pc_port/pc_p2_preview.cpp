#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "Pellet.h"
#include "PlayerState.h"
#include "MapMgr.h"
#include "Shape.h"
#include "Graphics.h"
#include "gameflow.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Texture.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>

// One disposable room only. This is deliberately not a campaign treasure registry.
static Pellet* previewTreasure = nullptr;
static Shape* previewShape = nullptr;
static bool delivered = false;
static int initialRepairs = 0;
bool pc_p2_preview_ready() { return pc_pikipelago_room_preview() && previewShape && previewTreasure; }
Pellet* pc_p2_preview_treasure() { return previewTreasure; }

void pc_p2_preview_setup() {
    if (!pc_pikipelago_room_preview()) return;
    previewTreasure = nullptr; previewShape = nullptr; delivered = false;
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
    gsys->setHeap(previousHeap);
    const float points[][2]={{-85,0},{-175,-100},{185,-180},{-220,-180}};
    for (const auto& point : points)
        std::printf("[Pikipelago] P2_ROOM_GROUND x=%.1f z=%.1f y=%.3f\n",point[0],point[1],mapMgr->getMinY(point[0],point[1],true));
    std::printf("[Pikipelago] P2_ROOM_READY treasure=bolt carry=5 repairs=%d\n",initialRepairs);
    std::fflush(stdout);
}

bool pc_p2_preview_draw(Pellet* pellet, Graphics& gfx, Matrix4f& matrix) {
    if (!pc_pikipelago_room_preview() || pellet != previewTreasure || !previewShape || pellet->mConfig->mModelId.mId != 'pr05') return false;
    previewShape->updateAnim(gfx,matrix,nullptr,pellet);
    previewShape->drawshape(gfx,*gfx.mCamera,nullptr);
    return true;
}

bool pc_p2_preview_deliver(Pellet* pellet) {
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
