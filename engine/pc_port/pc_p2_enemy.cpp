#include "pc_p2_enemy.h"
#include "pc_bbft.h"
#include "pc_p2_preview.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
std::map<std::string,std::vector<Shape*>> clips;
std::set<PelletView*> actors;
}
const char* pc_p2_enemy_name(PelletView* view) { return actors.count(view)?"Snow Bulborb":nullptr; }
void pc_p2_snow_setup() {
    clips.clear();actors.clear();
    if(!pc_pikipelago_room_preview())return;
    std::ifstream in("p2-snow.txt");if(!in)return;
    std::string word;in>>word;
    if(word!="P2_SNOW_1" || !pc_p2_preview_goal())std::abort();
    for(const char* name:{"wait1","move1","attack","dead","flick"}) {
        int count,duration;
        if(!(in>>word>>count>>duration) || word!=name || count<1 || count>12 || duration<1 || duration>10000)std::abort();
        for(int i=0;i<count;++i) {
            char path[128];std::snprintf(path,sizeof(path),"courses/pikmin2room/snow_%s_%02d.mod",name,i);
            Shape* shape=gameflow.loadShape(path,true);if(!shape)std::abort();
            for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture)shape->mTexAttrList[t].mTexture->attach();
            clips[name].push_back(shape);
        }
    }
    if(in>>word)std::abort();
    std::ifstream placements("p2-snow-actors.txt");int count;
    if(!(placements>>word>>count) || word!="P2_SNOW_ACTORS_1" || count<1 || count>100)std::abort();
    std::set<unsigned long> wanted;
    for(int i=0;i<count;++i){unsigned long id;if(!(placements>>id) || id>0xffffffffUL || !wanted.insert(id).second)std::abort();}
    if(placements>>word)std::abort();
    Iterator it(tekiMgr);CI_LOOP(it) {
        Teki* teki=static_cast<Teki*>(*it);
        if(teki && teki->mGenerator && wanted.erase(teki->mGenerator->_70)) {
            if(teki->mTekiType!=TEKI_Chappy)std::abort();
            actors.insert(static_cast<PelletView*>(teki));
            std::printf("P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=%u behavior=P1\n",teki->mGenerator->_70);
        }
    }
    if(!wanted.empty())std::abort();
}
bool pc_p2_snow_draw(BTeki* teki,Graphics& gfx,const Matrix4f& matrix,bool corpse) {
    if(!actors.count(static_cast<PelletView*>(teki)))return false;
    static bool logged[2]={false,false};
    if(!logged[corpse?1:0]){std::printf("P2_SNOW_DRAW corpse=%d\n",int(corpse));logged[corpse?1:0]=true;}
    int motion=teki->mTekiAnimator->getCurrentMotionIndex();
    const char* name=corpse || motion==TekiMotion::Dead?"dead":motion==TekiMotion::Attack?"attack":motion==TekiMotion::Flick?"flick":
        (teki->mVelocity.x*teki->mVelocity.x+teki->mVelocity.z*teki->mVelocity.z>1?"move1":"wait1");
    auto& bank=clips[name];
    // Source poses follow normalized P1 motion progress; P1 events stay authoritative.
    int frames=teki->mTekiAnimator->getFrameCount();
    float phase=frames>1?teki->mTekiAnimator->getCounter()/(frames-1):0;
    if(!std::isfinite(phase))phase=0;
    if(phase<0)phase=0;if(phase>1)phase=1;
    size_t index=corpse?bank.size()-1:size_t(phase*(bank.size()-1));
    bank[index]->updateAnim(gfx,matrix,nullptr,teki);
    bank[index]->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
