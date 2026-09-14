#include "pc_p2_enemy.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_p2_animation.h"
#include "pc_p2_snow_policy.h"
#include "pc_p2_snow_attack_policy.h"
#include "pc_p2_snow_turn_policy.h"
#include "pc_p2_snow_chase_policy.h"
#include "TekiConditions.h"
#include "Material.h"
#include <chrono>
#include <iterator>
#include "pc_bbft.h"
#include "pc_p2_preview.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "System.h"
#include "Joint.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_skin.h"
#include "pc_p2_crossfade.h"
#include "Texture.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include "pc_randomizer.h"
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
bool interpolation=false;
bool crossfade=false;
bool campaignMode=false;
bool generatedMode=false;
std::shared_ptr<const p2skin::Mesh> skin;
std::shared_ptr<const p2attach::Bank> skeleton;
std::map<std::string,std::vector<p2pose::Baked>> baked;
struct Mutable { Shape* shape=nullptr;std::string clip;float frame=0;bool corpse=false;unsigned generator=0;
    std::unique_ptr<p2attach::Instance> skeleton;uint64_t token=0,tick=0;p2pose::Pose deformed;p2attach::Crossfade transition; };
std::map<PelletView*,Mutable> instances;
P2SnowHealthPolicy healthPolicy;
P2SnowAttackPolicy attackPolicy;
P2SnowTurnPolicy turnPolicy;
P2SnowChasePolicy chasePolicy;
}
float pc_p2_snow_max_health(const BTeki* actor,float fallback) { return healthPolicy.life(actor,fallback); }
void pc_p2_snow_reset() { interpolation=false;crossfade=false;campaignMode=false;generatedMode=false;skin.reset();skeleton.reset();baked.clear();instances.clear(); clips.clear();actors.clear();timing.clear();healthPolicy.reset();attackPolicy.reset();turnPolicy.reset();chasePolicy.reset(); }
void pc_p2_snow_update(BTeki* actor,float seconds){
    if(!crossfade)return;
    auto it=instances.find(static_cast<PelletView*>(actor));
    if(it!=instances.end())it->second.transition.advance(seconds,gameflow.mPauseAll||gameflow.mIsUIOverlayActive);
}
void pc_p2_snow_forget(BTeki* actor) { instances.erase(static_cast<PelletView*>(actor)); healthPolicy.forget(actor);attackPolicy.forget(actor);turnPolicy.forget(actor);chasePolicy.forget(actor);actors.erase(static_cast<PelletView*>(actor)); }
bool pc_p2_snow_chase(BTeki* actor,const Vector3f& target) {
    if(!actor->isAlive() || !chasePolicy.contains(actor))return false;
    const Vector3f& position=actor->getPosition();
    if(!std::isfinite(target.x) || !std::isfinite(target.y) || !std::isfinite(target.z) ||
       !std::isfinite(position.x) || !std::isfinite(position.y) || !std::isfinite(position.z))return true;
    P2SnowChasePolicy::Result result;
    chasePolicy.evaluate(actor,actor->getDirection(),actor->calcTargetDirection(target),actor->mTargetVelocity.y,result);
    if(result.valid) {
        actor->setDirection(result.direction);
        actor->mTargetVelocity.set(result.x,result.y,result.z);
    }
    return true;
}
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
const char* pc_p2_enemy_name(PelletView* view) { if(const char* name=pc_p2_kochappy_name(view))return name;return actors.count(view)?"Snow Bulborb":nullptr; }
namespace {
void bindSnow(Teki* teki,unsigned identity) {
    if(actors.count(static_cast<PelletView*>(teki)))return;
    if(teki->mTekiType!=TEKI_Chappy || pc_p2_kochappy_name(teki))std::abort();
    Shape* shared=clips.begin()->second.front();
    const int previousHeap=gsys->setHeap(SYSHEAP_App);
            actors.insert(static_cast<PelletView*>(teki));
            if(interpolation){
                const char* path="courses/pikmin2room/snow_wait1_00.mod";
                Shape* model=gsys->getShape(path,path,nullptr,true);const auto& base=baked.at("wait1").front().pose;
                if(!model || model->mJointCount!=1 || model->mVertexCount!=int(base.positions.size()) || model->mNormalCount!=int(base.normals.size()))std::abort();
                // Point the private geometry's material bindings at the immutable bank resources.
                for(int j=0;j<model->mTotalMatpolyCount;++j){auto* poly=model->mMatpolyList[j];if(!poly || !poly->mMaterial)continue;
                    int material=-1;for(int m=0;m<model->mMaterialCount;++m)if(poly->mMaterial==&model->mMaterialList[m])material=m;
                    if(material<0 || material>=shared->mMaterialCount)std::abort();poly->mMaterial=&shared->mMaterialList[material];}
                model->mMaterialList=shared->mMaterialList;model->mTexAttrList=shared->mTexAttrList;model->mTevInfoList=shared->mTevInfoList;
                for(const auto& other:instances)if(other.second.shape->mVertexList==model->mVertexList || other.second.shape->mNormalList==model->mNormalList)std::abort();
                instances.emplace(static_cast<PelletView*>(teki),Mutable{model,"",0,false,identity});
                if(skin){auto& state=instances.at(static_cast<PelletView*>(teki));
                    state.skeleton=std::make_unique<p2attach::Instance>();state.token=state.skeleton->bind(skeleton);
                    if(!state.token || skin->positions.size()!=base.positions.size() || skin->normals.size()!=base.normals.size())std::abort();
                    state.deformed.positions.resize(skin->positions.size());state.deformed.normals.resize(skin->normals.size());
                    std::printf("P2_SNOW_SKELETAL_READY joints=%zu positions=%zu normals=%zu\n",skin->joints,skin->positions.size(),skin->normals.size());}
                std::printf("P2_SNOW_INTERPOLATION_READY generator=%u positions=%d normals=%d private_geometry=1 gameplay_clock=P1\n",identity,model->mVertexCount,model->mNormalCount);
            }
            attackPolicy.bind(static_cast<BTeki*>(teki));
            turnPolicy.bind(static_cast<BTeki*>(teki));
            chasePolicy.bind(static_cast<BTeki*>(teki));
            if(chasePolicy.enabled())std::printf("P2_SNOW_CHASE generator=%u speed=50 gain=0.4 cap_degrees_per_update=10 preserve_y=1 scope=trace_target_velocity\n",identity);
            if(turnPolicy.enabled())std::printf("P2_SNOW_TURN generator=%u gain=0.4 cap_degrees_per_update=10 arrival=P1 source_rotation_end_180=not_applied\n",identity);
            if(attackPolicy.enabled())std::printf("P2_SNOW_ATTACK generator=%u range=30 half_angle=20 scope=entry_only source=YellowKochappy_fp20_fp21\n",identity);
            if(healthPolicy.enabled()) {
                const float oldHealth=teki->mHealth;
                healthPolicy.bind(static_cast<BTeki*>(teki));
                teki->mHealth=teki->getParameterF(TPF_Life);
                std::printf("P2_SNOW_POLICY generator=%u health=%.1f max_health=%.1f previous=%.1f source=YellowKochappy_fp00\n",
                            identity,teki->mHealth,teki->getParameterF(TPF_Life),oldHealth);
            }
            std::printf("P2_ENEMY_READY species=YellowKochappy native_family=Chappy generator=%u behavior=P1\n",identity);
    gsys->setHeap(previousHeap);
}
}
void pc_p2_snow_campaign_bind(Teki* teki) {
    if(campaignMode && teki && teki->mTekiType==TEKI_Chappy)bindSnow(teki,0);
}
void pc_p2_generated_bind(Teki* teki,const void* generator) {
    if(!teki || !generator)return;
    const unsigned source=pc_randomizer_p2_bound_source(generator);
    if(!source)return;
    if(source==45) {
        if(!generatedMode || teki->mTekiType!=TEKI_Chappy)std::abort();
        bindSnow(teki,pc_randomizer_generator_id(generator));
        return;
    }
    if(source==44) {
        if(!pc_p2_dwarf_orange_generated() || teki->mTekiType!=TEKI_Chappy)std::abort();
        pc_p2_dwarf_orange_bind(teki,pc_randomizer_generator_id(generator));
        return;
    }
    // A bound identity the generated bridge cannot host must fail closed rather
    // than silently spawn a P1 actor under a P2 identity.
    pc_randomizer_bad_p2_host();
}
void pc_p2_snow_campaign_setup() {
    if(pc_pikipelago_room_preview())return;
    const bool generated=pc_randomizer_p2_bridge() && pc_randomizer_p2_bound(45);
    if(!generated && !std::ifstream("assets/p2-snow-all-dwarfs.txt"))return;
    const int previousHeap=gsys->setHeap(SYSHEAP_App);
    pc_p2_snow_setup();
    gsys->setHeap(previousHeap);
}

void pc_p2_snow_setup() {
    pc_p2_snow_reset();
    std::ifstream campaign("assets/p2-snow-all-dwarfs.txt");
    if(campaign){std::string magic,extra;if(!(campaign>>magic)||magic!="P2_SNOW_ALL_DWARFS_1"||(campaign>>extra)||pc_pikipelago_room_preview())std::abort();campaignMode=true;}
    // Generated sessions stage the Snow bank into the run's private asset overlay
    // and opt in only when the ENEMY_P2 layout actually binds Snow (source 45).
    const bool generated=pc_randomizer_p2_bridge() && pc_randomizer_p2_bound(45);
    if(generated && campaignMode)std::abort(); // refuse a blanket override in an exact-identity session
    if(!pc_pikipelago_room_preview() && !campaignMode && !generated)return;
    const char* prefix=(campaignMode || generated)?"assets/":"";
    char pathBuffer[256];
    auto assetPath=[&](const char* name){std::snprintf(pathBuffer,sizeof(pathBuffer),"%s%s",prefix,name);return pathBuffer;};
    std::ifstream in(assetPath("p2-snow.txt"));
    if(!in){if(campaignMode || generated)std::abort();return;}
    generatedMode=generated;
    const auto started=std::chrono::steady_clock::now();
    std::ifstream blendOption(assetPath("p2-snow-interpolation.txt"));
    if(blendOption){std::string magic,extra;if(!(blendOption>>magic)||magic!="P2_SNOW_INTERPOLATION_1"||(blendOption>>extra))std::abort();interpolation=true;}
    std::ifstream skinOption(assetPath("p2-snow-skeletal.txt"));
    if(skinOption){std::string magic,extra;if(!(skinOption>>magic)||magic!="P2_SNOW_SKELETAL_1"||(skinOption>>extra)||!interpolation)std::abort();
        std::ifstream mesh(assetPath("p2-snow-skin.txt"));
        std::ifstream joints(assetPath("p2-snow-joints.txt"));
        skin=p2skin::read(mesh);skeleton=p2attach::read(joints);
        if(!skin||!skeleton||skin->joints!=skeleton->joints.size())std::abort();}
    std::ifstream fadeOption(assetPath("p2-snow-crossfade.txt"));
    if(fadeOption){std::string magic,extra;if(!(fadeOption>>magic)||magic!="P2_SNOW_CROSSFADE_1"||(fadeOption>>extra)||!skin)std::abort();crossfade=true;}
    std::vector<unsigned char> topology;
    std::vector<p2animation::Clip> manifest;
    if(!p2animation::parse(in,manifest) || (!campaignMode && !generated && !pc_p2_preview_goal()))std::abort();
    if(!campaignMode) {
    std::ifstream policy(assetPath("p2-snow-policy.txt"));
    if(policy && !healthPolicy.read(policy))std::abort();
    std::ifstream attack(assetPath("p2-snow-attack.txt"));
    if(attack && !attackPolicy.read(attack))std::abort();
    std::ifstream turn(assetPath("p2-snow-turn.txt"));
    if(turn && !turnPolicy.read(turn))std::abort();
    std::ifstream chase(assetPath("p2-snow-chase.txt"));
    if(chase && !chasePolicy.read(chase))std::abort();
    }
    // Validate the entire bank before allocating Shapes or uploading textures.
    size_t total=0,poses=0;
    std::vector<unsigned char> reference;
    for(const auto& clip:manifest) {
        if(interpolation && clip.frames.empty())std::abort();
        size_t clipBytes=0;
        for(int i=0;i<clip.count;++i) {
            if(skin && (clip.name!="wait1" || i!=0))continue;
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
            if(interpolation){p2pose::Baked pose;
                if(!p2pose::decodeBaked(data,pose) || (!topology.empty() && topology!=pose.topology))std::abort();
                topology=pose.topology;baked[clip.name].push_back(std::move(pose));}
        }
    }
    if(skin && baked.find("wait1")==baked.end())std::abort();
    Shape* shared=nullptr;
    int attachments=0;
    timing.clear();
    for(const auto& clip:manifest) {
        timing[clip.name]=clip;
        if(skeleton){int ci=skeleton->clip(clip.name);if(ci<0||skeleton->clips[ci].duration!=clip.duration)std::abort();}
        for(int i=0;i<clip.count;++i) {
            if(skin && (clip.name!="wait1" || i!=0))continue;
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
    if(campaignMode){int count=0;Iterator all(tekiMgr);CI_LOOP(all){auto* actor=static_cast<Teki*>(*all);if(actor->mTekiType==TEKI_Chappy){bindSnow(actor,0);++count;}}
        std::printf("P2_SNOW_CAMPAIGN_READY dwarfs=%d interpolation=%d native_rewards=1\n",count,int(interpolation));return;}
    if(generatedMode){int count=0;Iterator all(tekiMgr);CI_LOOP(all){auto* actor=static_cast<Teki*>(*all);
        if(actor->mTekiType==TEKI_Chappy && actor->mGenerator && pc_randomizer_p2_bound_source(actor->mGenerator)==45){bindSnow(actor,pc_randomizer_generator_id(actor->mGenerator));++count;}}
        std::printf("P2_SNOW_GENERATED_READY dwarfs=%d interpolation=%d bridge=1\n",count,int(interpolation));return;}
    std::string word;
    std::ifstream placements("p2-snow-actors.txt");int count;
    if(!(placements>>word>>count) || word!="P2_SNOW_ACTORS_1" || count<1 || count>100)std::abort();
    std::set<unsigned long> wanted;
    for(int i=0;i<count;++i){unsigned long id;if(!(placements>>id) || id>0xffffffffUL || !wanted.insert(id).second)std::abort();}
    if(placements>>word)std::abort();
    Iterator it(tekiMgr);CI_LOOP(it) {
        Teki* teki=static_cast<Teki*>(*it);
        if(teki && teki->mGenerator && wanted.erase(teki->mGenerator->_70)) {
            if(teki->mTekiType!=TEKI_Chappy || pc_p2_kochappy_name(teki))std::abort();
            bindSnow(teki,teki->mGenerator->_70);
        }
    }
    if(!wanted.empty())std::abort();
}
namespace {
void snowClock(BTeki* teki,bool corpse,const char*& name,float& phase,float& sourceFrame) {
    int motion=teki->mTekiAnimator->getCurrentMotionIndex();
    // Chappy Type1 is the lethal squash path (TaiDyingAction), not idle.
    // Requested/residual velocity can remain nonzero during wait/turn states;
    // visual locomotion must follow the animator, just like attack and death.
    name=corpse || motion==TekiMotion::Dead || motion==TekiMotion::Type1?"dead":
        motion==TekiMotion::Attack?"attack":motion==TekiMotion::Flick?"flick":
        motion==TekiMotion::Move1 || motion==TekiMotion::Move2?"move1":"wait1";
    // Source poses follow normalized P1 motion progress; P1 events stay authoritative.
    int frames=teki->mTekiAnimator->getFrameCount();
    phase=frames>1?teki->mTekiAnimator->getCounter()/(frames-1):0;

    const auto& clip=timing.at(name);
    sourceFrame=corpse?float(clip.frames.empty()?clip.duration-1:clip.frames.back()):std::max(0.f,std::min(1.f,phase))*float(clip.duration-1);
}
}
bool pc_p2_snow_clock(BTeki* teki,const char*& name,float& frame,bool corpse){
    if(!actors.count(static_cast<PelletView*>(teki)))return false;
    float phase;snowClock(teki,corpse,name,phase,frame);return std::isfinite(frame);
}

bool pc_p2_snow_draw(BTeki* teki,Graphics& gfx,const Matrix4f& matrix,bool corpse) {
    if(!actors.count(static_cast<PelletView*>(teki)))return false;
    static bool logged[2]={false,false};
    if(!logged[corpse?1:0]){std::printf("P2_SNOW_DRAW corpse=%d\n",int(corpse));logged[corpse?1:0]=true;}
    const char* name;float phase,sourceFrame;snowClock(teki,corpse,name,phase,sourceFrame);
    auto& bank=clips.at(skin?"wait1":name);
    size_t index=timing.at(name).index(phase,corpse);
    Shape* shape=bank[skin?0:index];
    if(interpolation){
        auto& instance=instances.at(static_cast<PelletView*>(teki));shape=instance.shape;
        const auto& clip=timing.at(name);const float frame=sourceFrame;
        p2pose::Interval span;if(!p2pose::bracket(clip.frames,frame,span))std::abort();
        const auto& a=baked.at(skin?"wait1":name)[skin?0:span.left].pose;const auto& b=baked.at(skin?"wait1":name)[skin?0:span.right].pose;
        if(skin){
            const bool snap=corpse||std::string(name)=="dead"||std::string(name)=="flick"||instance.clip=="dead"||instance.clip=="flick";
            const bool sampled=crossfade?instance.transition.sample(*instance.skeleton,instance.token,skeleton->clip(name),frame,p2attach::Affine{},++instance.tick,.15f,snap):
                instance.skeleton->sample(instance.token,skeleton->clip(name),frame,p2attach::Affine{},++instance.tick);
            if(!sampled ||
            !p2skin::deform(*skin,*instance.skeleton,instance.token,instance.deformed))std::abort();
            for(size_t i=0;i<instance.deformed.positions.size();++i){const auto& v=instance.deformed.positions[i];shape->mVertexList[i].set(v.x,v.y,v.z);}
            for(size_t i=0;i<instance.deformed.normals.size();++i){const auto& v=instance.deformed.normals[i];shape->mNormalList[i].set(v.x,v.y,v.z);}
        }else{
        for(size_t i=0;i<a.positions.size();++i){auto v=p2pose::mix(a.positions[i],b.positions[i],span.weight);shape->mVertexList[i].set(v.x,v.y,v.z);}
        for(size_t i=0;i<a.normals.size();++i){p2pose::Vec v;if(!p2pose::unit(p2pose::mix(a.normals[i],b.normals[i],span.weight),v))v=span.weight<=.5f?a.normals[i]:b.normals[i];shape->mNormalList[i].set(v.x,v.y,v.z);}
        }
        BoundBox bounds(shape->mVertexList[0],shape->mVertexList[0]);for(int i=1;i<shape->mVertexCount;++i)bounds.expandBound(shape->mVertexList[i]);
        shape->mCourseExtents=bounds;shape->mJointList[0].mBounds=bounds;
        if(instance.clip!=name || instance.corpse!=corpse)std::printf("P2_SNOW_BLEND generator=%u clip=%s corpse=%d source_frame=%.5f\n",instance.generator,name,int(corpse),frame);
        instance.clip=name;instance.frame=frame;instance.corpse=corpse;
    }
    shape->updateAnim(gfx,matrix,nullptr,teki);
    shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}

bool pc_p2_snow_geometry(BTeki* actor,p2pose::Pose& out,std::string& clip,float& frame,bool& corpse){
    auto it=instances.find(static_cast<PelletView*>(actor));if(it==instances.end() || it->second.clip.empty())return false;
    const auto& state=it->second;const auto& shape=*state.shape;p2pose::Pose next;
    for(int i=0;i<shape.mVertexCount;++i){const auto& v=shape.mVertexList[i];next.positions.push_back({v.x,v.y,v.z});}
    for(int i=0;i<shape.mNormalCount;++i){const auto& v=shape.mNormalList[i];next.normals.push_back({v.x,v.y,v.z});}
    out=std::move(next);clip=state.clip;frame=state.frame;corpse=state.corpse;return true;
}
