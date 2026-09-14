#include "pc_p2_receipt_host.h"
#include "pc_p2_kogane.h"
#include "pc_p2_kogane_policy.h"
#include "pc_p2_enemy.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_sheargrub.h"
#include "teki.h"
#include "Interactions.h"
#include "ItemMgr.h"
#include "MizuItem.h"
#include "ObjType.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include <map>
#include <cmath>
#include <fstream>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <sstream>
namespace {
std::map<std::string,std::vector<Shape*>> clips;
std::map<std::string,p2animation::Clip> timing;
std::map<PelletView*,int> actors;int karada=-1;

// Batch-4 behavior state (#219). One entry per registered beetle host.
// Source: Koganemushi.cpp/Wealthy.cpp/Fart.cpp, KoganeState.cpp.
struct Beetle {
    int flips=0;             // press count so far (source mFlipCount)
    float dropTimer=-1.0f;   // seconds until the pending flip drop fires (source damage.bca frame 7 of 50)
    bool moving=false;       // wander phase flag
    float phaseTimer=0.5f;   // seconds left in the current wander phase
    float heading=0.0f;      // current wander heading (radians)
    float gasTimer=0.0f;     // remaining gas cloud seconds (Fart only, source 2.5 s)
    Vector3f gasPosition;    // cloud anchor (source mFartPosition)
    std::map<Piki*,float> gasExposure; // sustained-exposure seconds per piki (P1-host InteractGas approximation)
    unsigned rng=1;          // deterministic per-actor LCG
    unsigned generator=0;    // spawn generator id, keys the in-process flip dedupe
    int treasure=0;          // configured first-flip stand-in pellet value (0 = none)
};
std::map<PelletView*,Beetle> beetles;

// In-process scene re-entry dedupe (#219): a reset+setup cycle within one
// process must not let a finite-flip beetle farm its drops again, so reset
// snapshots each actor's flip count keyed by generator id and setup restores it.
// Empty on a fresh process, so the first setup is a no-op.
std::map<unsigned,int> restoredFlips;

// On-disk flip receipts (#168/#219): the in-process snapshot above dies with the
// process, so a second process on the same run directory would re-spawn spent
// beetles. This family-local sidecar (never the P2 save) keeps per-generator flip
// counts durable. It is written atomically (temp + rename) on every flip/escape
// and loaded in setup() after the in-process snapshot; a missing file starts empty; malformed state is rejected so it cannot replay
// previously granted drops.
const char* kReceiptsPath="p2-kogane-receipts.txt";
const char* kReceiptsHeader="P2_KOGANE_RECEIPTS_1";

int loadReceipts(){
    std::ifstream in(kReceiptsPath);
    if(!in)return 0;
    std::string line;
    if(!std::getline(in,line)||line!=kReceiptsHeader)throw std::runtime_error("Invalid P2 Kogane receipt state");
    std::map<unsigned,int> rows;
    while(std::getline(in,line)){
        if(line.empty())continue;
        std::istringstream row(line);unsigned generator=0;int flips=0;std::string extra;
        if(!(row>>generator>>flips)||row>>extra||flips<1||flips>3)throw std::runtime_error("Invalid P2 Kogane receipt state");
        if(!rows.emplace(generator,flips).second)throw std::runtime_error("Invalid P2 Kogane receipt state");
    }
    if(!in.eof())throw std::runtime_error("Invalid P2 Kogane receipt state");
    for(const auto& row:rows){
        auto found=restoredFlips.find(row.first);
        if(found==restoredFlips.end()||row.second>found->second)restoredFlips[row.first]=row.second;
    }
    return int(rows.size());
}
void saveReceipts(){
    std::map<unsigned,int> rows=restoredFlips;
    for(const auto& entry:beetles)if(entry.second.generator&&entry.second.flips>0)rows[entry.second.generator]=entry.second.flips;
    if(rows.empty())return;
    std::string data=std::string(kReceiptsHeader)+"\n";
    for(const auto& row:rows)data+=std::to_string(row.first)+" "+std::to_string(row.second)+"\n";
    if (!pc_p2_receipt_host_atomic_write(kReceiptsPath,data.c_str())) {
        std::fputs("P2_KOGANE receipt persistence failed\n",stderr); std::abort();
    }
}

bool logged[2]={false,false};

// Audited source health (Koganemushi/Wealthy/Fart parameter fp00).
float sourceLife(int id){return id==9?1000.0f:id==10?1200.0f:1500.0f;}

// Source drop tables, P1-host resolution: HONEY_Y maps to native nectar
// (OBJTYPE_Water); HONEY_R/HONEY_B spray branches use their documented
// no-demo-flag fallback (HONEY_Y x3) because P1 has no spray items.
// P1 fallback for the cave treasure: the host has no P2 treasure item, so a
// configured `treasure <generator> <pellet_value>` sidecar row substitutes one
// stand-in number pellet on that actor's first flip (see doDrop), not the real
// createTreasureItem treasure (Kogane.cpp:386-414).
void dropFor(int id,int hit,int& pelletValue,int& pellets,int& nectar){
    pelletValue=0;pellets=0;nectar=0;
    if(id==9){if(hit==0){pelletValue=1;pellets=1;}else if(hit==1){nectar=2;}else{nectar=3;}}
    else if(id==10){if(hit==0){pelletValue=5;pellets=3;}else{nectar=3;}}
    else{nectar=3;}
}

unsigned nextRand(Beetle& b){b.rng=b.rng*1664525u+1013904223u;return b.rng>>8;}
float randRange(Beetle& b,float lo,float hi){return lo+(hi-lo)*float(nextRand(b)&0xffff)/65535.0f;}

void doDrop(BTeki* actor,int id,Beetle& b){
    int pelletValue,pellets,nectar;
    if(b.flips==1&&b.treasure>0){
        // First flip only: a configured cave treasure substitutes one stand-in
        // number pellet for the audited row. The host has no P2 treasure item, so
        // this is a labelled P1 stand-in, never the source treasure object.
        pelletValue=b.treasure;pellets=1;nectar=0;
        std::printf("P2_KOGANE_TREASURE generator=%u value=%d\n",
            actor->mGenerator?actor->mGenerator->_70:0u,pelletValue);
        std::fflush(stdout);
    }else dropFor(id,b.flips-1,pelletValue,pellets,nectar);
    Vector3f base=actor->getPosition();
    for(int i=0;i<pellets;++i){
        if(!pelletMgr)break;
        int color=int(nextRand(b)%3); // PELCOLOR_Blue/Red/Yellow; P2 pellets are untyped, P1 requires a color
        Pellet* p=pelletMgr->newNumberPellet(color,pelletValue==5?NUMPEL_FivePellet:NUMPEL_OnePellet);
        if(!p)break;
        Vector3f pos(base.x+randRange(b,-20.0f,20.0f),base.y+10.0f,base.z+randRange(b,-20.0f,20.0f));
        p->init(pos);
        p->mVelocity.set(randRange(b,-60.0f,60.0f),100.0f,randRange(b,-60.0f,60.0f));
        p->startAI(0);
    }
    for(int i=0;i<nectar;++i){
        if(!itemMgr)break;
        Creature* drop=itemMgr->birth(OBJTYPE_Water);
        if(!drop)break;
        Vector3f pos(base.x+randRange(b,-20.0f,20.0f),base.y+10.0f,base.z+randRange(b,-20.0f,20.0f));
        drop->init(pos);
        drop->startAI(0);
    }
    std::printf("P2_KOGANE_DROP generator=%u source_id=%d flip=%d pellet%d=%d nectar=%d\n",
        actor->mGenerator?actor->mGenerator->_70:0u,id,b.flips,pelletValue,pellets,nectar);
    std::fflush(stdout);
}
}
void pc_p2_kogane_reset(){
    for(const auto& entry:beetles)if(entry.second.generator&&entry.second.flips>0)restoredFlips[entry.second.generator]=entry.second.flips;
    clips.clear();timing.clear();actors.clear();beetles.clear();karada=-1;logged[0]=logged[1]=false;
}
void pc_p2_kogane_forget(BTeki* actor){actors.erase(static_cast<PelletView*>(actor));beetles.erase(static_cast<PelletView*>(actor));}
int pc_p2_kogane_source_id(PelletView* a){auto i=actors.find(a);return i==actors.end()?-1:i->second;}
const char* pc_p2_kogane_name(PelletView* a){int id=pc_p2_kogane_source_id(a);return id==9?"Iridescent Flint Beetle":id==10?"Iridescent Glint Beetle":id==11?"Doodlebug":nullptr;}
void pc_p2_kogane_setup(){
    pc_p2_kogane_reset();
    const int receipts=loadReceipts();
    std::printf("P2_KOGANE_RECEIPTS loaded=%d\n",receipts);
    std::fflush(stdout);
    std::ifstream sidecar("p2-kogane-native.txt");if(!sidecar)return;
    p2kogane::Config config;if(!tekiMgr||!p2kogane::read(sidecar,config))std::abort();
    auto manifest=config.clips;std::set<std::uint32_t> wanted;for(auto row:config.ids)wanted.insert(row.first);karada=config.karada;
    // Reject identity overlap and unresolved/duplicate generator IDs before loading.
    std::vector<Teki*> selected;std::set<std::uint32_t> seen;
    Iterator it(tekiMgr);CI_LOOP(it){
        Teki* actor=static_cast<Teki*>(*it);
        if(!actor || !actor->mGenerator || !wanted.count(actor->mGenerator->_70))continue;
        if(!seen.insert(actor->mGenerator->_70).second || actor->mTekiType!=TEKI_Chappy || pc_p2_enemy_name(actor) || pc_p2_sheargrub_name(actor) || pc_p2_kochappy_name(actor))std::abort();
        selected.push_back(actor);
    }
    if(seen!=wanted)std::abort();
    size_t total=0,poses=0;std::vector<unsigned char> reference;
    for(const auto& clip:manifest){
        size_t clipBytes=0;
        for(int i=0;i<clip.count;++i){
            char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/kogane_%s_%02d.mod",clip.name.c_str(),i);
            std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)std::abort();auto bytes=file.tellg();
            if(bytes<=0 || size_t(bytes)>p2animation::ClipBytes-clipBytes || size_t(bytes)>p2animation::TotalBytes-total)std::abort();
            clipBytes+=size_t(bytes);total+=size_t(bytes);file.seekg(0);
            std::vector<unsigned char> data(size_t(bytes),0),resources;
            if(!file.read(reinterpret_cast<char*>(data.data()),bytes) || !p2animation::resources(data,resources))std::abort();
            if(!reference.empty() && reference!=resources)std::abort();reference=resources;
        }
    }
    const auto started=std::chrono::steady_clock::now();Shape* shared=nullptr;int attachments=0;
    for(const auto& clip:manifest){
        timing[clip.name]=clip;
        for(int i=0;i<clip.count;++i){
            char path[128];std::snprintf(path,sizeof(path),"courses/pikmin2room/kogane_%s_%02d.mod",clip.name.c_str(),i);
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
    for(Teki* actor:selected){
        int id=config.ids.at(actor->mGenerator->_70);
        actors[actor]=id;
        Beetle& b=beetles[actor];
        b.rng=(actor->mGenerator->_70*2654435761u)|1u;
        b.generator=actor->mGenerator->_70;
        auto treasure=config.treasures.find(b.generator);
        if(treasure!=config.treasures.end())b.treasure=treasure->second;
        b.heading=actor->getDirection();
        b.phaseTimer=randRange(b,1.0f,2.0f); // source starts waiting, then wanders
        auto restored=restoredFlips.find(b.generator);
        if(restored!=restoredFlips.end()&&restored->second>0){
            b.flips=restored->second;
            std::printf("P2_KOGANE_FLIPS_RESTORED generator=%u flips=%d\n",b.generator,b.flips);
            std::fflush(stdout);
            if(b.flips>=3){
                // Already at the source flip cap: this beetle spent every drop and
                // burrowed away before the reset, so reconstruct the escaped state
                // instead of re-spawning one that can never drop again.
                std::printf("P2_KOGANE_RESTORED_ESCAPE generator=%u flips=%d\n",b.generator,b.flips);
                std::fflush(stdout);
                actor->pcEscapeNow(); // corpse suppressed via the CorpseType hook
                continue;
            }
        }
        actor->mHealth=actor->getParameterF(TPF_Life);
        std::printf("P2_KOGANE_BIND generator=%u source_id=%d karada_k0=%d visual_only=0\n",actor->mGenerator->_70,id,p2kogane::karada(id));
        const auto& pos=actor->getPosition();
        std::printf("P2_ENEMY_READY species=Kogane_family native_family=Chappy generator=%u x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native source_FSM=implemented drops=native gas=native_P1_approx escape=native treasure=%s cave=disabled\n",actor->mGenerator->_70,pos.x,pos.y,pos.z,actor->mHealth,actor->getParameterF(TPF_Life),b.treasure>0?"standin":"disabled");
    }
    std::printf("P2_KOGANE_BANK poses=%zu mod_bytes=%zu texture_attach_calls=%d load_seconds=%.3f\n",poses,total,attachments,std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count());
}
// Batch-4 hooks: every hook is a no-op for unregistered actors.
// Beetles never leave a corpse: on death/escape they burrow away (KoganeState
// Disappear); suppress the host corpse pellet for registered actors only.
int pc_p2_kogane_corpse_type(const BTeki* actor,int fallback){
    return pc_p2_kogane_source_id(const_cast<BTeki*>(actor))<0?fallback:TEKICORPSE_NoCorpse;
}
// Audited source health plus harmlessness: beetles never pursue or bite, so
// the host's target-recognition and attack params are zeroed for registered
// actors only.
float pc_p2_kogane_param_f(const BTeki* actor,int idx,float fallback){
    int id=pc_p2_kogane_source_id(const_cast<BTeki*>(actor));
    if(id<0)return fallback;
    switch(idx){
    case TPF_Life:return sourceLife(id);
    case TPF_VisibleRange:case TPF_VisibleAngle:
    case TPF_AttackableRange:case TPF_AttackableAngle:
    case TPF_AttackRange:case TPF_AttackHitRange:case TPF_AttackPower:
    case TPF_DangerTerritoryRange:case TPF_SafetyTerritoryRange:
        return 0.0f;
    default:return fallback;
    }
}
// Pikmin attacks do no damage (source: only flip-on-press affects beetles);
// swallow the attack interaction for registered actors.
bool pc_p2_kogane_attacked(Teki* teki){
    return pc_p2_kogane_source_id(static_cast<PelletView*>(teki))>=0;
}
// Press (Pikmin landing on top): count a flip, play the host damage motion and
// schedule the source frame-7 drop. The third flip's drop triggers escape.
bool pc_p2_kogane_pressed(Teki* teki,Creature*){
    int id=pc_p2_kogane_source_id(static_cast<PelletView*>(teki));
    if(id<0)return false;
    Beetle& b=beetles[static_cast<PelletView*>(teki)];
    if(teki->mDeadState!=0||b.dropTimer>=0.0f)return true; // mid-flip: swallow extra presses
    ++b.flips;
    teki->startMotion(TekiMotion::Damage);
    b.dropTimer=7.0f/50.0f*(50.0f/30.0f); // source damage.bca createItem event at frame 7 of 50 @30fps
    b.moving=false;
    teki->stopMove();
    std::printf("P2_KOGANE_FLIP generator=%u source_id=%d flip=%d\n",teki->mGenerator?teki->mGenerator->_70:0u,id,b.flips);
    std::fflush(stdout);
    saveReceipts();
    return true;
}
// Per-frame driver: wander, pending drops, Fart gas, forced escape.
void pc_p2_kogane_update(BTeki* actor){
    int id=pc_p2_kogane_source_id(static_cast<PelletView*>(actor));
    if(id<0)return;
    Beetle& b=beetles[static_cast<PelletView*>(actor)];
    if(actor->mDeadState!=0)return;
    const float dt=gsys->getFrameTime();
    if(dt<=0.0f||dt>0.5f)return; // skip paused/hitched frames
    // Pending flip drop (beetle is held still while flipping).
    if(b.dropTimer>=0.0f){
        b.dropTimer-=dt;
        if(b.dropTimer<0.0f){
            doDrop(actor,id,b);
            if(b.flips>=3){
                std::printf("P2_KOGANE_ESCAPE generator=%u source_id=%d flips=%d\n",actor->mGenerator?actor->mGenerator->_70:0u,id,b.flips);
                std::fflush(stdout);
                saveReceipts();
                actor->pcEscapeNow(); // corpse suppressed via the CorpseType hook; health stays >0 so no defeat event
                return;
            }
        }
    }
    // Fart gas cloud: 2.5 s anchor started at each move-phase start; Pikmin in
    // radius 20 accumulate exposure and die via InteractKill after 0.8 s
    // sustained (P1-host approximation of P2 InteractGas with fp24=0 Navi
    // damage; Navi is never stimulated).
    if(b.gasTimer>0.0f){
        b.gasTimer-=dt;
        if(pikiMgr){
            std::set<Piki*> inside;
            Iterator it(pikiMgr);CI_LOOP(it){
                Piki* piki=static_cast<Piki*>(*it);
                if(!piki||!piki->isAlive())continue;
                Vector3f d=piki->getPosition();d.sub(b.gasPosition);
                if(d.length()>20.0f)continue;
                inside.insert(piki);
                float& exposure=b.gasExposure[piki];
                exposure+=dt;
                if(exposure>=0.8f){
                    piki->stimulate(InteractKill(actor,0));
                    std::printf("P2_KOGANE_GAS_KILL generator=%u exposure=%.3f\n",actor->mGenerator?actor->mGenerator->_70:0u,exposure);
                    std::fflush(stdout);
                    b.gasExposure.erase(piki);
                }
            }
            for(auto it2=b.gasExposure.begin();it2!=b.gasExposure.end();){
                if(!inside.count(it2->first))it2=b.gasExposure.erase(it2);else ++it2;
            }
        }
        if(b.gasTimer<=0.0f){
            b.gasExposure.clear();
            std::printf("P2_KOGANE_GAS end generator=%u\n",actor->mGenerator?actor->mGenerator->_70:0u);
            std::fflush(stdout);
        }
    }
    // Wander driver (source StateWait/StateMove cycle: pause 1-2 s, then move
    // 0.3-0.7 s at the source move speed with a random turn of up to 90 deg).
    b.phaseTimer-=dt;
    if(b.phaseTimer<=0.0f){
        b.moving=!b.moving;
        if(b.moving){
            b.phaseTimer=randRange(b,0.3f,0.7f);
            b.heading+=randRange(b,-1.5708f,1.5708f);
            if(id==11&&b.gasTimer<=0.0f){
                b.gasTimer=2.5f;b.gasPosition=actor->getPosition();b.gasExposure.clear();
                std::printf("P2_KOGANE_GAS start generator=%u duration=2.500 radius=20.0\n",actor->mGenerator?actor->mGenerator->_70:0u);
                std::fflush(stdout);
            }
        }else{
            b.phaseTimer=randRange(b,1.0f,2.0f);
        }
    }
    if(b.moving&&b.dropTimer<0.0f){
        const float speed=120.0f; // source fp01 move speed class, P1 units
        actor->setDirection(b.heading);
        Vector3f drive(sinf(b.heading)*speed,0.0f,cosf(b.heading)*speed);
        actor->inputDrive(drive);
        actor->mVelocity.set(drive);
    }else if(b.dropTimer<0.0f){
        actor->inputDrive(Vector3f(0.0f,0.0f,0.0f));
        actor->mVelocity.x=0.0f;actor->mVelocity.z=0.0f;
    }
}
// Fixture introspection: expose the active gas cloud anchor so the arena can
// place a probe Pikmin inside it deterministically.
int pc_p2_kogane_gas_state(BTeki* actor,float* x,float* z,float* remaining){
    if(pc_p2_kogane_source_id(static_cast<PelletView*>(actor))<0)return 0;
    Beetle& b=beetles[static_cast<PelletView*>(actor)];
    if(b.gasTimer<=0.0f)return 0;
    if(x)*x=b.gasPosition.x;if(z)*z=b.gasPosition.z;if(remaining)*remaining=b.gasTimer;
    return 1;
}
bool pc_p2_kogane_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    if(!actors.count(static_cast<PelletView*>(actor)))return false;
    if(!logged[corpse?1:0]){std::printf("P2_KOGANE_DRAW corpse=%d\n",int(corpse));logged[corpse?1:0]=true;}
    if(corpse)return false;
    int motion=actor->mTekiAnimator->getCurrentMotionIndex();
    const char* name=motion==TekiMotion::Damage?"damage":actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1?"move":"wait";
    int frames=actor->mTekiAnimator->getFrameCount();float phase=frames>1?actor->mTekiAnimator->getCounter()/(frames-1):0;
    Shape* shape=clips.at(name).at(timing.at(name).index(phase,corpse));
    if(karada>=shape->mMaterialCount)std::abort();auto* tev=shape->mMaterialList[karada].mTevInfo;if(!tev)std::abort();
    Colour saved=tev->mKonstColors[0];int colour=p2kogane::karada(actors.at(actor));tev->mKonstColors[0].set(colour,colour,colour,255);
    shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);tev->mKonstColors[0]=saved;return true;
}
