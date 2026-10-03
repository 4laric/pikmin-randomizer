#include "pc_p2_kochappy.h"
#include "pc_p2_original_red_native.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_kochappy_policy.h"
#include "pc_p2_kochappy_stun.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_shape.h"
#include "pc_p2_enemy.h"
#include "pc_p2_sheargrub.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include <map>
#include <fstream>
#include <chrono>
#include <cstdio>
#include <cstdlib>
namespace {
std::map<std::string,std::vector<Shape*>> clips;
std::map<std::string,p2animation::Clip> timing;
std::set<PelletView*> actors;
p2kochappy::Health health;
bool logged[2]={false,false};
bool interpolation=false;bool originalBank=false;std::set<PelletView*> originalActors;
std::map<std::string,std::vector<p2pose::Baked>> baked;
struct Mutable {Shape* shape=nullptr;p2pose::Pose scratch;std::string clip;float frame=0;bool corpse=false;};
std::map<PelletView*,Mutable> instances;
}
void pc_p2_kochappy_reset(){originalBank=false;originalActors.clear();instances.clear();baked.clear();interpolation=false;clips.clear();timing.clear();actors.clear();health.reset();pc_p2_kochappy_stun_reset();logged[0]=logged[1]=false;}
void pc_p2_kochappy_forget(BTeki* actor){pc_p2_original_red_forget(actor);originalActors.erase(static_cast<PelletView*>(actor));instances.erase(static_cast<PelletView*>(actor));actors.erase(static_cast<PelletView*>(actor));health.forget(actor);pc_p2_kochappy_stun_forget(actor);}
float pc_p2_kochappy_max_health(const BTeki* actor,float fallback){return health.life(actor,fallback);}
const char* pc_p2_kochappy_name(PelletView* actor){return actors.count(actor)?"Dwarf Red Bulborb":nullptr;}
bool pc_p2_kochappy_registered(const BTeki* actor){return actors.count(const_cast<BTeki*>(actor))!=0;}
BTeki* pc_p2_kochappy_first_registered(){return actors.empty()?nullptr:static_cast<BTeki*>(*actors.begin());}
static bool setupKochappy(bool original,std::string& error){
    pc_p2_kochappy_reset();
    std::ifstream option("p2-kochappy-interpolation.txt");
    if(option){std::string magic,extra;if(!(option>>magic)||magic!="P2_KOCHAPPY_INTERPOLATION_1"||(option>>extra))std::abort();interpolation=true;}
    std::ifstream profile("p2-kochappy-profile.txt"),bank("p2-kochappy-bank.txt"),bindings("p2-kochappy-actors.txt");
    if(original){bank.close();bank.open("p2-original-red-bank.txt");interpolation=true;}
    if(!original&&!profile && !bank && !bindings){if(interpolation)std::abort();return true;}
    std::vector<p2animation::Clip> manifest;std::set<std::uint32_t> wanted;
        if(original){std::istringstream declared("P2_KOCHAPPY_PROFILE_1 species Kochappy health 200");
        if(!bank||!tekiMgr||!health.read(declared)||!p2kochappy::originalBank(bank,manifest)){error="original Red exact authored bank/manager unavailable";return false;}}
    else if(!profile || !bank || !bindings || !tekiMgr || !health.read(profile) || !p2kochappy::bank(bank,manifest) || !p2kochappy::bindings(bindings,wanted))std::abort();
    // Reject identity overlap and unresolved/duplicate generator IDs before loading.
    std::vector<Teki*> selected;std::set<std::uint32_t> seen;
    Iterator it(tekiMgr);CI_LOOP(it){
        Teki* actor=static_cast<Teki*>(*it);
        if(!actor || !actor->mGenerator || !wanted.count(actor->mGenerator->_70))continue;
        if(!seen.insert(actor->mGenerator->_70).second || actor->mTekiType!=TEKI_Chappy || pc_p2_enemy_name(actor) || pc_p2_sheargrub_name(actor))std::abort();
        selected.push_back(actor);
    }
    if(seen!=wanted)std::abort();
    size_t total=0,poses=0;std::vector<unsigned char> reference,topology;
    for(const auto& clip:manifest){
        if(interpolation&&clip.frames.empty())std::abort();
        size_t clipBytes=0;
        for(int i=0;i<clip.count;++i){
            char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/kochappy_%s_%02d.mod",clip.name.c_str(),i);
            std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)std::abort();auto bytes=file.tellg();
            if(bytes<=0 || size_t(bytes)>p2animation::ClipBytes-clipBytes || size_t(bytes)>p2animation::TotalBytes-total)std::abort();
            clipBytes+=size_t(bytes);total+=size_t(bytes);file.seekg(0);
            std::vector<unsigned char> data(size_t(bytes),0),resources;
            if(!file.read(reinterpret_cast<char*>(data.data()),bytes) || !p2animation::resources(data,resources))std::abort();
            if(!reference.empty() && reference!=resources)std::abort();reference=resources;
            if(interpolation){p2pose::Baked pose;if(!p2pose::decodeBaked(data,pose)||(!topology.empty()&&topology!=pose.topology))std::abort();topology=pose.topology;baked[clip.name].push_back(std::move(pose));}
        }
    }
    const auto started=std::chrono::steady_clock::now();Shape* shared=nullptr;int attachments=0;
    for(const auto& clip:manifest){
        timing[clip.name]=clip;
        for(int i=0;i<clip.count;++i){
            char path[128];std::snprintf(path,sizeof(path),"courses/pikmin2room/kochappy_%s_%02d.mod",clip.name.c_str(),i);
            Shape* shape=gameflow.loadShape(path,true);if(!shape)std::abort();
            if(!shared){shared=shape;for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture){shape->mTexAttrList[t].mTexture->attach();++attachments;}}
            else{
                if(shape->mMaterialCount!=shared->mMaterialCount || shape->mTexAttrCount!=shared->mTexAttrCount || shape->mTevInfoCount!=shared->mTevInfoCount)std::abort();
                for(int j=0;j<shape->mTotalMatpolyCount;++j){auto* poly=shape->mMatpolyList[j];if(!poly || !poly->mMaterial)continue;int material=-1;
                    for(int m=0;m<shape->mMaterialCount;++m)if(poly->mMaterial==&shape->mMaterialList[m])material=m;
                    if(material<0)std::abort();poly->mMaterial=&shared->mMaterialList[material];}
                shape->mMaterialList=shared->mMaterialList;shape->mTexAttrList=shared->mTexAttrList;shape->mTevInfoList=shared->mTevInfoList;
            }
            clips[clip.name].push_back(shape);++poses;
        }
    }
    if(original){originalBank=true;error.clear();return true;}
    for(Teki* actor:selected){
        if(interpolation){
            const int heap=gsys->setHeap(SYSHEAP_App);const auto& first=manifest.front();const auto& base=baked.at(first.name).front().pose;
            std::string path="courses/pikmin2room/kochappy_"+first.name+"_00.mod";
            Mutable state;state.shape=p2pose::privateShape(path.c_str(),*shared,base);if(!state.shape)std::abort();
            state.scratch.positions.resize(base.positions.size());state.scratch.normals.resize(base.normals.size());
            for(const auto& entry:instances)if(entry.second.shape->mVertexList==state.shape->mVertexList||entry.second.shape->mNormalList==state.shape->mNormalList)std::abort();
            instances.emplace(actor,std::move(state));gsys->setHeap(heap);
            std::printf("P2_KOCHAPPY_INTERPOLATION_READY generator=%u private_geometry=1\n",actor->mGenerator->_70);
        }
        if(!health.bind(static_cast<BTeki*>(actor)))std::abort();actors.insert(actor);actor->mHealth=actor->getParameterF(TPF_Life);
        const auto& pos=actor->getPosition();
        pc_p2_kochappy_stun_register(actor,10.0f);
        std::printf("P2_ENEMY_READY species=Kochappy source_id=1 native_family=Chappy generator=%u x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=P1 purple_stun=red_earthquake_v1\n",actor->mGenerator->_70,pos.x,pos.y,pos.z,actor->mHealth,actor->getParameterF(TPF_Life));
    }
    std::printf("P2_KOCHAPPY_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f\n",poses,total,attachments,std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count());
    return true;
}
void pc_p2_kochappy_setup(){
 for(const auto& row:p2original::originalActors().rows())if(row.second.enemy.source==1)return;
 std::string error;setupKochappy(false,error);}
bool pc_p2_kochappy_prepare_original(std::string& error){
 if(!actors.empty()){error="original Red resources while family actors owned";return false;}
 if(originalBank){error.clear();return true;}
 return setupKochappy(true,error);
}
bool pc_p2_kochappy_bind_original(BTeki* actor,unsigned token,std::string& error){
 unsigned source=0,actual=0;auto* view=static_cast<PelletView*>(actor);
 if(!originalBank||!actor||!actor->mGenerator||actor->mTekiType!=TEKI_Chappy||actors.count(view)
 ||!p2original::originalActors().query(actor,source,actual)||source!=1||actual!=token){error="original Red visual registry/chassis ownership mismatch";return false;}
 const int previousHeap=gsys->setHeap(SYSHEAP_App);
 struct RestoreHeap {int previous;~RestoreHeap(){gsys->setHeap(previous);}} restore{previousHeap};
 const auto& base=baked.at("wait1").front().pose;Shape* shared=clips.at("wait1").front();
 Mutable state;state.shape=p2pose::privateShape("courses/pikmin2room/kochappy_wait1_00.mod",*shared,base);
 if(!state.shape){error="original Red private render geometry unresolved";return false;}
 state.scratch.positions.resize(base.positions.size());state.scratch.normals.resize(base.normals.size());
 for(const auto& entry:instances)if(entry.second.shape->mVertexList==state.shape->mVertexList||entry.second.shape->mNormalList==state.shape->mNormalList){error="original Red reused mutable geometry";return false;}
 if(!health.bind(actor)){error="original Red health binding refused";return false;}
 instances.emplace(view,std::move(state));actors.insert(view);originalActors.insert(view);actor->mHealth=actor->mMaxHealth=200;
 pc_p2_kochappy_stun_register(actor,10);error.clear();return true;
}
bool pc_p2_kochappy_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    if(!actors.count(static_cast<PelletView*>(actor)))return false;
    if(!logged[corpse?1:0]){std::printf("P2_KOCHAPPY_DRAW corpse=%d\n",int(corpse));logged[corpse?1:0]=true;}
    int motion=actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name=corpse || motion==TekiMotion::Dead?"dead":motion==TekiMotion::Attack?"attack":motion==TekiMotion::Flick?"flick":
        (actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1?"move1":"wait1");
    int frames=actor->mTekiAnimator->getFrameCount();float phase=frames>1?actor->mTekiAnimator->getCounter()/(frames-1):0;
    if(interpolation)name=corpse||motion==TekiMotion::Dead||motion==TekiMotion::Type1?"dead":motion==TekiMotion::Attack?"attack":motion==TekiMotion::Flick?"flick":motion==TekiMotion::Move1||motion==TekiMotion::Move2?"move1":"wait1";
    if(originalActors.count(static_cast<PelletView*>(actor))){
        const auto snapshot=pc_p2_kochappy_fsm_observe(actor);
        if(!corpse&&!snapshot.available)std::abort();
        float frame=0;if(!p2kochappy::originalFrame(snapshot.state,snapshot.stateTime,corpse,name,frame))std::abort();
        phase=frame/std::max(1.f,float(timing.at(name).duration-1));
    }
    Shape* shape=clips.at(name).at(timing.at(name).index(phase,corpse));
    if(interpolation){auto& state=instances.at(actor);const auto& clip=timing.at(name);const float frame=corpse?float(clip.duration-1):std::max(0.f,std::min(1.f,phase))*float(clip.duration-1);
        p2pose::Interval span;if(!std::isfinite(phase)||!p2pose::bracket(clip.frames,frame,span))std::abort();
        shape=state.shape;const auto& poses=baked.at(name);
        if(!p2pose::apply(*shape,poses[span.left].pose,poses[span.right].pose,span.weight,state.scratch))std::abort();
        state.clip=name;state.frame=frame;state.corpse=corpse;
    }
    shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
bool pc_p2_kochappy_geometry(BTeki* actor,p2pose::Pose& out,std::string& clip,float& frame,bool& corpse){
    auto it=instances.find(actor);if(it==instances.end()||it->second.clip.empty())return false;const auto& s=it->second;
    out.positions.resize(s.shape->mVertexCount);out.normals.resize(s.shape->mNormalCount);
    for(int i=0;i<s.shape->mVertexCount;++i){const auto& v=s.shape->mVertexList[i];out.positions[i]={v.x,v.y,v.z};}
    for(int i=0;i<s.shape->mNormalCount;++i){const auto& v=s.shape->mNormalList[i];out.normals[i]={v.x,v.y,v.z};}
    clip=s.clip;frame=s.frame;corpse=s.corpse;return true;
}
