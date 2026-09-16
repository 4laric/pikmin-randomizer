// Optional actor close-up. Positions only this synthetic render fixture's enemy;
// not a combat, route, or placement acceptance test.
#include "pc_p2_enemy.h"
static bool snowRenderFixture(Navi* n) {
    static bool requested=[](){FILE* f=std::fopen("p2-snow-render.txt","r");if(!f)return false;std::fclose(f);return true;}();
    if(!requested)return false;
    static int frame=0;static Teki* snow=nullptr;
    if(++frame==1) {
        Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(pc_p2_enemy_name(static_cast<PelletView*>(t)))snow=t;}
        require(snow!=nullptr,"missing opted-in Snow actor");
        snow->mSRT.t=n->mSRT.t+Vector3f(70,0,30);
        snow->mSRT.t.y=mapMgr->getMinY(snow->mSRT.t.x,snow->mSRT.t.z,true);
    }
    if(frame==30){capture("p2-snow-live.ppm");std::puts("PASS Snow render capture (synthetic nearby placement)");std::fflush(stdout);std::_Exit(0);}
    return true;
}
