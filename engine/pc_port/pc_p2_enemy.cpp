#include "pc_p2_enemy.h"
#include "pc_p2_animation.h"
#include "pc_p2_snow_policy.h"
#include "pc_p2_snow_attack_policy.h"
#include "pc_p2_snow_turn_policy.h"
#include "TekiConditions.h"
#include "Material.h"
#include <chrono>
#include <iterator>
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
std::map<std::string,p2animation::Clip> timing;
P2SnowHealthPolicy healthPolicy;
P2SnowAttackPolicy attackPolicy;
P2SnowTurnPolicy turnPolicy;
}
float pc_p2_snow_max_health(const BTeki* actor,float fallback) { return healthPolicy.life(actor,fallback); }
void pc_p2_snow_reset() { clips.clear();actors.clear();timing.clear();healthPolicy.reset();attackPolicy.reset();turnPolicy.reset(); }
void pc_p2_snow_forget(BTeki* actor) { healthPolicy.forget(actor);attackPolicy.forget(actor);turnPolicy.forget(actor);actors.erase(static_cast<PelletView*>(actor)); }
bool pc_p2_snow_turn(BTeki* actor,float targetAngle,float arrivalStep,bool& arrived) {
    if(!actor->isAlive())return false;
    P2SnowTurnPolicy::Result result;
    if(!turnPolicy.evaluate(actor,actor->getDirection(),targetAngle,arrivalStep,result))return false;
    arrived=result.valid && result.arrived;
    if(result.valid)actor->setDirection(result.direction);
    return true;
}
bool pc_p2_snow_attackable(BTeki* actor,Creature& target,bool& result) {
    if(!attackPolicy.contains(actor))return false;
    TekiRecognitionCondition recognition(static_cast<Teki*>(actor));
    const Vector3f delta=target.getPosition()-actor->getPosition();
    return attackPolicy.evaluate(actor,delta.x*delta.x+delta.y*delta.y+delta.z*delta.z,
                                 actor->calcTargetAngle(target.getPosition()),recognition.satisfy(&target),result);
}
const char* pc_p2_enemy_name(PelletView* view) { return actors.count(view)?"Snow Bulborb":nullptr; }
void pc_p2_snow_setup() {
    pc_p2_snow_reset();
    if(!pc_pikipelago_room_preview())return;
    std::ifstream in("p2-snow.txt");if(!in)return;
    const auto started=std::chrono::steady_clock::now();
    std::vector<p2animation::Clip> manifest;
    if(!p2animation::parse(in,manifest) || !pc_p2_preview_goal())std::abort();
    std::ifstream policy("p2-snow-policy.txt");
    if(policy && !healthPolicy.read(policy))std::abort();
    std::ifstream attack("p2-snow-attack.txt");
    if(attack && !attackPolicy.read(attack))std::abort();
    std::ifstream turn("p2-snow-turn.txt");
    if(turn && !turnPolicy.read(turn))std::abort();
    // Validate the entire bank before allocating Shapes or uploading textures.
    size_t total=0,poses=0;
    std::vector<unsigned char> reference;
    for(const auto& clip:manifest) {
        size_t clipBytes=0;
        for(int i=0;i<clip.count;++i) {
            char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/snow_%s_%02d.mod",clip.name.c_str(),i);
            std::ifstream file(path,std::ios::binary|std::ios::ate);
            if(!file)std::abort();
            auto bytes=file.tellg();
            if(bytes<=0 || size_t(bytes)>p2animation::ClipBytes-clipBytes || size_t(bytes)>p2animation::TotalBytes-total)std::abort();
            clipBytes+=size_t(bytes);total+=size_t(bytes);
            file.seekg(0);
            std::vector<unsigned char> data(size_t(bytes),0),resources;
            if(!file.read(reinterpret_cast<char*>(data.data()),bytes) || !p2animation::resources(data,resources))std::abort();
            if(!reference.empty() && reference!=resources)std::abort();
            reference=resources;
        }
    }
    Shape* shared=nullptr;
    int attachments=0;
    timing.clear();
    for(const auto& clip:manifest) {
        timing[clip.name]=clip;
        for(int i=0;i<clip.count;++i) {
            char path[128];std::snprintf(path,sizeof(path),"courses/pikmin2room/snow_%s_%02d.mod",clip.name.c_str(),i);
            Shape* shape=gameflow.loadShape(path,true);if(!shape)std::abort();
            if(!shared) {
                shared=shape;
                for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture) {
                    shape->mTexAttrList[t].mTexture->attach();++attachments;
                }
            } else {
                // Resources are byte-identical. Keep pose geometry private, but
                // use one immutable material/texture set for every render path.
                // loadShape still allocates CPU resource copies on the scene heap.
                if(shape->mMaterialCount!=shared->mMaterialCount || shape->mTexAttrCount!=shared->mTexAttrCount ||
                   shape->mTevInfoCount!=shared->mTevInfoCount)std::abort();
                for(int j=0;j<shape->mTotalMatpolyCount;++j) {
                    auto* poly=shape->mMatpolyList[j];
                    if(!poly || !poly->mMaterial)continue;
                    int material=-1;
                    for(int m=0;m<shape->mMaterialCount;++m)if(poly->mMaterial==&shape->mMaterialList[m])material=m;
                    if(material<0)std::abort();
                    poly->mMaterial=&shared->mMaterialList[material];
                }
                shape->mMaterialList=shared->mMaterialList;
                shape->mTexAttrList=shared->mTexAttrList;
                shape->mTevInfoList=shared->mTevInfoList;
            }
            clips[clip.name].push_back(shape);++poses;
        }
    }
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    std::printf("P2_SNOW_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f load_budget_seconds=5 budget_exceeded=%d\n",
                poses,total,attachments,seconds,int(seconds>5));
    std::string word;
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
            attackPolicy.bind(static_cast<BTeki*>(teki));
            turnPolicy.bind(static_cast<BTeki*>(teki));
            if(turnPolicy.enabled())std::printf("P2_SNOW_TURN generator=%u gain=0.4 cap_degrees_per_update=10 arrival=P1 source_rotation_end_180=not_applied\n",teki->mGenerator->_70);
            if(attackPolicy.enabled())std::printf("P2_SNOW_ATTACK generator=%u range=30 half_angle=20 scope=entry_only source=YellowKochappy_fp20_fp21\n",teki->mGenerator->_70);
            if(healthPolicy.enabled()) {
                const float oldHealth=teki->mHealth;
                healthPolicy.bind(static_cast<BTeki*>(teki));
                teki->mHealth=teki->getParameterF(TPF_Life);
                std::printf("P2_SNOW_POLICY generator=%u health=%.1f max_health=%.1f previous=%.1f source=YellowKochappy_fp00\n",
                            teki->mGenerator->_70,teki->mHealth,teki->getParameterF(TPF_Life),oldHealth);
            }
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
    size_t index=timing.at(name).index(phase,corpse);
    bank[index]->updateAnim(gfx,matrix,nullptr,teki);
    bank[index]->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
