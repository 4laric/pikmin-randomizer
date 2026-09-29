#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_bbft.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_p2_dwarf_orange_policy.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_shape.h"
#include "pc_p2_kochappy_stun.h"
#include "pc_p2_kochappy_fsm.h"
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
 p2dwarforange::Health health;
// own44-fix (#871): one DRAW line per (actor, corpse) so each marker carries
// its own generator token (mirrors P2_MAMUTA_DRAW per-actor logging).
std::set<std::pair<PelletView*,int>> logged;
// Token captured at bind: dieSoon() detaches mGenerator before the corpse
// draw, so the live lookup would read 0 for corpse=1.
std::map<PelletView*,unsigned> tokens;
bool interpolation=false;
std::map<std::string,std::vector<p2pose::Baked>> baked;
struct Mutable {Shape* shape=nullptr;p2pose::Pose scratch;std::string clip;float frame=0;bool corpse=false;};
std::map<PelletView*,Mutable> instances;
// Source BlueKochappy purple-pikmin stun: fp38 = 5 s (KochappyBase flick/press).
constexpr float PurpleFitDuration = 5.0f;
}
void pc_p2_dwarf_orange_reset(){instances.clear();baked.clear();interpolation=false;clips.clear();timing.clear();actors.clear();health.reset();logged.clear();tokens.clear();}
void pc_p2_dwarf_orange_forget(BTeki* actor){
    instances.erase(static_cast<PelletView*>(actor));
    const bool wasRegistered=actors.erase(static_cast<PelletView*>(actor))!=0;
    // The generator is already detached by dieSoon(), so identity is not
    // available here; the registration transition is the cleanup signal.
    if(wasRegistered){std::printf("P2_DWARF_ORANGE_FORGET registered=1\n");std::fflush(stdout);}
    logged.erase({static_cast<PelletView*>(actor),0});logged.erase({static_cast<PelletView*>(actor),1});tokens.erase(static_cast<PelletView*>(actor));
    health.forget(actor);pc_p2_kochappy_stun_forget(actor);
}
float pc_p2_dwarf_orange_max_health(const BTeki* actor,float fallback){return health.life(actor,fallback);}
const char* pc_p2_dwarf_orange_name(PelletView* actor){return actors.count(actor)?"Dwarf Orange Bulborb":nullptr;}
bool pc_p2_dwarf_orange_registered(const BTeki* actor){return actors.count(const_cast<BTeki*>(actor))!=0;}
unsigned long pc_p2_dwarf_orange_count(){return (unsigned long)actors.size();}
void pc_p2_dwarf_orange_setup(){
    pc_p2_dwarf_orange_reset();
    std::ifstream option("p2-dwarf-orange-interpolation.txt");
    if(option){std::string magic,extra;if(!(option>>magic)||magic!="P2_DWARF_ORANGE_INTERPOLATION_1"||(option>>extra))std::abort();interpolation=true;}
    std::ifstream profile("p2-dwarf-orange-profile.txt"),bank("p2-dwarf-orange-bank.txt"),bindings("p2-dwarf-orange-actors.txt");
    if(!profile && !bank && !bindings){if(interpolation)std::abort();return;}
    std::vector<p2animation::Clip> manifest;std::set<std::uint32_t> wanted;
    if(!profile || !bank || !bindings || !tekiMgr || !health.read(profile) || !p2dwarforange::bank(bank,manifest) || !p2dwarforange::bindings(bindings,wanted)){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","staged_config_invalid"))return;}
    if (pc_randomizer_p2_bridge()) {
        wanted = pc_p2_campaign_ids(44);
        if (wanted.empty()) return;
    }
    // Reject identity overlap and unresolved/duplicate generator IDs before loading.
    std::vector<Teki*> selected;std::set<std::uint32_t> seen;
    Iterator it(tekiMgr);CI_LOOP(it){
        Teki* actor=static_cast<Teki*>(*it);
        if(!actor || !actor->mGenerator || !wanted.count(pc_p2_campaign_token(actor)))continue;
        if(!seen.insert(pc_p2_campaign_token(actor)).second || actor->mTekiType!=TEKI_Chappy || pc_p2_enemy_name(actor) || pc_p2_sheargrub_name(actor) || pc_p2_kochappy_name(actor)){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","actor_identity_mismatch"))return;}
        selected.push_back(actor);
    }
    if(seen!=wanted){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","actor_roster_incomplete"))return;}
    size_t total=0,poses=0;std::vector<unsigned char> reference,topology;
    for(const auto& clip:manifest){
        if(interpolation&&clip.frames.empty())std::abort();
        size_t clipBytes=0;
        for(int i=0;i<clip.count;++i){
            char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/dwarf_orange_%s_%02d.mod",clip.name.c_str(),i);
            std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","clip_file_missing"))return;}auto bytes=file.tellg();
            if(bytes<=0 || size_t(bytes)>p2animation::ClipBytes-clipBytes || size_t(bytes)>p2animation::TotalBytes-total){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","clip_file_invalid"))return;}
            clipBytes+=size_t(bytes);total+=size_t(bytes);file.seekg(0);
            std::vector<unsigned char> data(size_t(bytes),0),resources;
            if(!file.read(reinterpret_cast<char*>(data.data()),bytes) || !p2animation::resources(data,resources)){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","clip_file_unparsable"))return;}
            if(!reference.empty() && reference!=resources){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","clip_resource_mismatch"))return;}reference=resources;
            if(interpolation){p2pose::Baked pose;if(!p2pose::decodeBaked(data,pose)||(!topology.empty()&&topology!=pose.topology))std::abort();topology=pose.topology;baked[clip.name].push_back(std::move(pose));}
        }
    }
    const auto started=std::chrono::steady_clock::now();Shape* shared=nullptr;int attachments=0;
    for(const auto& clip:manifest){
        timing[clip.name]=clip;
        for(int i=0;i<clip.count;++i){
            char path[128];std::snprintf(path,sizeof(path),"courses/pikmin2room/dwarf_orange_%s_%02d.mod",clip.name.c_str(),i);
            Shape* shape=gameflow.loadShape(path,true);if(!shape){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","shape_load_failed"))return;}
            if(!shared){shared=shape;for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture){shape->mTexAttrList[t].mTexture->attach();++attachments;}}
            else{
                if(shape->mMaterialCount!=shared->mMaterialCount || shape->mTexAttrCount!=shared->mTexAttrCount || shape->mTevInfoCount!=shared->mTevInfoCount){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","shape_layout_mismatch"))return;}
                for(int j=0;j<shape->mTotalMatpolyCount;++j){auto* poly=shape->mMatpolyList[j];if(!poly || !poly->mMaterial)continue;int material=-1;
                    for(int m=0;m<shape->mMaterialCount;++m)if(poly->mMaterial==&shape->mMaterialList[m])material=m;
                    if(material<0){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","shape_material_mismatch"))return;}poly->mMaterial=&shared->mMaterialList[material];}
                shape->mMaterialList=shared->mMaterialList;shape->mTexAttrList=shared->mTexAttrList;shape->mTevInfoList=shared->mTevInfoList;
            }
            clips[clip.name].push_back(shape);++poses;
        }
    }
    for(Teki* actor:selected){
        if(interpolation){
            const int heap=gsys->setHeap(SYSHEAP_App);const auto& first=manifest.front();const auto& base=baked.at(first.name).front().pose;
            std::string path="courses/pikmin2room/dwarf_orange_"+first.name+"_00.mod";
            Mutable state;state.shape=p2pose::privateShape(path.c_str(),*shared,base);if(!state.shape)std::abort();
            state.scratch.positions.resize(base.positions.size());state.scratch.normals.resize(base.normals.size());
            for(const auto& entry:instances)if(entry.second.shape->mVertexList==state.shape->mVertexList||entry.second.shape->mNormalList==state.shape->mNormalList)std::abort();
            instances.emplace(static_cast<PelletView*>(actor),std::move(state));gsys->setHeap(heap);
            std::printf("P2_DWARF_ORANGE_INTERPOLATION_READY generator=%u private_geometry=1\n",pc_p2_campaign_token(actor));
        }
        if(!health.bind(static_cast<BTeki*>(actor))){if(pc_p2_setup_skip(pc_randomizer_p2_bridge(),"BlueKochappy","health_bind_failed"))return;}actors.insert(actor);tokens[actor]=pc_p2_campaign_token(actor);actor->mHealth=actor->getParameterF(TPF_Life);
        const auto& pos=actor->getPosition();
        pc_p2_kochappy_stun_register(actor,PurpleFitDuration);
        // deliv4 (#871): lane-06 ordinary-delivery source bind so
        // GoalItem::suckMe grants onion:p2:44 instead of suppressing the P1
        // host CHECK (bc6/bc7 hauled the corpse with carriers>0 but no receipt:
        // P2_P1_CHECK_SUPPRESSED host_type=3). Mirrors Otakara/Kurage/ElecBug.
        // Single-use: consumed on delivery, cleared on forget/recycle.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 44, pc_p2_campaign_token(actor));
        std::printf("P2_DWARF_ORANGE_DELIVERY_BIND generator=%u source_id=44\n", pc_p2_campaign_token(actor));
        // own44b (#871): this READY records the visual/health/stun binding; in
        // bridge mode (and not room preview, or with p2-dwarf-orange-fsm.txt)
        // pc_p2_kochappy_fsm owns the actor and the P1 host AI is suppressed
        // (BTeki::doAI early-return at src/plugPikiNakata/tekibteki.cpp:636,
        // driven per-frame by BTeki::update at tekibteki.cpp:521 - same pattern
        // as pc_p2_armor_suppress_ai at tekibteki.cpp:660). The predicate below
        // exactly matches pc_p2_kochappy_fsm_setup's bridge gate
        // (pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview()), so
        // behavior=native below only prints when the FSM will actually own.
        const bool fsmOwns = (pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview()) || std::ifstream("p2-dwarf-orange-fsm.txt").good();
        std::printf("P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=%u x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=%s purple_stun=bluekochappy_5s\n",pc_p2_campaign_token(actor),pos.x,pos.y,pos.z,actor->mHealth,actor->getParameterF(TPF_Life),fsmOwns?"native-FSM-owned":"P1");
    }
    std::printf("P2_DWARF_ORANGE_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f\n",poses,total,attachments,std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count());
}
bool pc_p2_dwarf_orange_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    if(!actors.count(static_cast<PelletView*>(actor)))return false;
    if(logged.insert({static_cast<PelletView*>(actor),corpse?1:0}).second){
        const auto token=tokens.find(static_cast<PelletView*>(actor));
        std::printf("P2_DWARF_ORANGE_DRAW generator=%u corpse=%d %s\n",token!=tokens.end()?token->second:pc_p2_campaign_token(actor),int(corpse),
                    pc_p2_kochappy_fsm_suppress_ai(actor)?"OWN_FSM_driven":"P1_gameplay_unchanged");
        std::fflush(stdout);
    }
    int motion=actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name=corpse || motion==TekiMotion::Dead?"dead":motion==TekiMotion::Attack?"attack":motion==TekiMotion::Flick?"flick":
        (actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1?"move1":"wait1");
    int frames=actor->mTekiAnimator->getFrameCount();float phase=frames>1?actor->mTekiAnimator->getCounter()/(frames-1):0;
    if(interpolation)name=corpse||motion==TekiMotion::Dead||motion==TekiMotion::Type1?"dead":motion==TekiMotion::Attack?"attack":motion==TekiMotion::Flick?"flick":motion==TekiMotion::Move1||motion==TekiMotion::Move2?"move1":"wait1";
    Shape* shape=clips.at(name).at(timing.at(name).index(phase,corpse));
    if(interpolation){auto& state=instances.at(actor);const auto& clip=timing.at(name);const float frame=corpse?float(clip.duration-1):std::max(0.f,std::min(1.f,phase))*float(clip.duration-1);
        p2pose::Interval span;if(!std::isfinite(phase)||!p2pose::bracket(clip.frames,frame,span))std::abort();
        shape=state.shape;const auto& poses=baked.at(name);
        if(!p2pose::apply(*shape,poses[span.left].pose,poses[span.right].pose,span.weight,state.scratch))std::abort();
        state.clip=name;state.frame=frame;state.corpse=corpse;
    }
    shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
bool pc_p2_dwarf_orange_geometry(BTeki* actor,p2pose::Pose& out,std::string& clip,float& frame,bool& corpse){
    auto it=instances.find(actor);if(it==instances.end()||it->second.clip.empty())return false;const auto& s=it->second;
    out.positions.resize(s.shape->mVertexCount);out.normals.resize(s.shape->mNormalCount);
    for(int i=0;i<s.shape->mVertexCount;++i){const auto& v=s.shape->mVertexList[i];out.positions[i]={v.x,v.y,v.z};}
    for(int i=0;i<s.shape->mNormalCount;++i){const auto& v=s.shape->mNormalList[i];out.normals[i]={v.x,v.y,v.z};}
    clip=s.clip;frame=s.frame;corpse=s.corpse;return true;
}
