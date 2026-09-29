#include "pc_p2_frog.h"
#include "pc_p2_frog_policy.h"
#include "pc_p2_frog_flight.h"
#include "pc_p2_campaign_actor.h"
#include "pc_randomizer.h"
#include "Material.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Interactions.h"
#include "MapMgr.h"
#include <fstream>
#include <set>
#include <cstdlib>
#include <cstdio>
#include "gl/pc_gfx.h"
#include <cmath>
namespace {
std::map<PelletView*,int> actors;
const char* ids[]={"Frog","MaroFrog"};
std::map<std::string,std::vector<Shape*>> animated[2];
std::map<std::string,p2animation::Clip> timing[2];
std::set<PelletView*> pressing,bitteredFrogs,drawn,drawnCorpse;

enum FState {
    FRG_DEAD = 0, FRG_WAIT = 1, FRG_TURN = 2, FRG_JUMP = 3, FRG_JUMPWAIT = 4,
    FRG_FALL = 5, FRG_ATTACK = 6, FRG_FAIL = 7, FRG_TURNTOHOME = 8, FRG_GOHOME = 9,
};
const float PI_F = 3.14159265f;
constexpr float HOME_RADIUS = 15.0f;       // source mHomeRadius default
constexpr float TERRITORY = 200.0f;        // source mTerritoryRadius default
constexpr float MOVE_SPEED = 80.0f;        // source mMoveSpeed default
constexpr float TURN_RATE = 2.5f;          // port adaptation
constexpr float ATTACK_ANGLE = 0.261799f;  // 15 deg source mMaxAttackAngle default
constexpr float FACE_OK_ANGLE = 0.174533f; // 10 deg settle
constexpr int FLEE_STUCK_MIN = 3;          // source mShakeOffSticking1 first tier (flick-timer graduation omitted)
constexpr float JUMP_LAUNCH_S = 8.0f / 30.0f; // type1 key event 2 (frame 8)
constexpr float FLICK_KNOCKBACK = 0.0f;
constexpr float FLICK_DAMAGE = 0.0f;

struct FrogFsm {
    int kind = 0;
    FState state = FRG_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f targetPos;
    bool targetValid = false;
    float groundY = 0.0f;
    p2frog::Flight flight;
    bool launched = false;
    bool escaped = false;
    bool pressDone = false;
    bool jumpEntryChecked = false;
    unsigned rng = 1;
    unsigned token = 0;
    bool deadLogged = false;float deathPrior=0.0f;bool deathPriorSet=false;
    std::string clip = "wait1";
    float phase = 0.0f;
    float logTimer = 0.0f;
    float lastHealth = 0.0f;
};
std::map<PelletView*, FrogFsm> fsms;
bool ready = false;

unsigned nextRand(FrogFsm& s) { s.rng = s.rng * 1664525u + 1013904223u; return s.rng >> 8; }
float rand01(FrogFsm& s) { return float(nextRand(s) & 0xffff) / 65535.0f; }
float wrapPi(float a) { while (a > PI_F) a -= 2.0f * PI_F; while (a < -PI_F) a += 2.0f * PI_F; return a; }
float distXZ(const Vector3f& a, const Vector3f& b) { const float dx = a.x - b.x, dz = a.z - b.z; return std::sqrt(dx * dx + dz * dz); }
float clipSeconds(int kind, const std::string& name) {
    auto it = timing[kind].find(name);
    return it == timing[kind].end() ? 1.0f : it->second.duration / 30.0f;
}
// Family-local instrumentation only: records the P1-proxy Attack motion of a
// registered frog; it does not assert the source landing press.
bool logPress(BTeki* actor,int kind){
    auto* view=static_cast<PelletView*>(actor);
    bool active=actor->mTekiAnimator&&actor->mTekiAnimator->getCurrentMotionIndex()==TekiMotion::Attack;
    if(active){if(pressing.insert(view).second){std::printf("P2_FROG_PRESS species=%s attack=1 behavior=P1_proxy\n",ids[kind]);return true;}return false;}
    pressing.erase(view);return false;
}
bool isBittered(PelletView* view){return bitteredFrogs.count(view)!=0;}
void loadAnimation(std::vector<p2animation::Clip> (&banks)[2]){
    size_t total=0;
    for(int kind=0;kind<2;++kind){std::vector<unsigned char> reference;
        for(const auto& clip:banks[kind]){size_t clipBytes=0;
            for(int i=0;i<clip.count;++i){char path[192];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/frog_%s_%s_%02d.mod",ids[kind],clip.name.c_str(),i);
                std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)std::abort();auto size=file.tellg();
                if(size<=0||size>512*1024)std::abort();clipBytes+=size_t(size);total+=size_t(size);
                if(clipBytes>512*1024||total>10*1024*1024)std::abort();file.seekg(0);
                std::vector<unsigned char> bytes(size_t(size),0),resources;
                if(!file.read(reinterpret_cast<char*>(bytes.data()),size)||!p2animation::resources(bytes,resources))std::abort();
                if(!reference.empty()&&reference!=resources)std::abort();reference=resources;
            }
        }
    }
    for(int kind=0;kind<2;++kind){Shape* shared=nullptr;
        for(const auto& clip:banks[kind]){timing[kind][clip.name]=clip;
            for(int i=0;i<clip.count;++i){char path[160];std::snprintf(path,sizeof(path),"courses/pikmin2room/frog_%s_%s_%02d.mod",ids[kind],clip.name.c_str(),i);
                Shape* shape=gameflow.loadShape(path,true);if(!shape)std::abort();
                if(!shared){shared=shape;for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture)shape->mTexAttrList[t].mTexture->attach();}
                else{
                    if(shape->mMaterialCount!=shared->mMaterialCount||shape->mTexAttrCount!=shared->mTexAttrCount||shape->mTevInfoCount!=shared->mTevInfoCount)std::abort();
                    for(int j=0;j<shape->mTotalMatpolyCount;++j){auto* poly=shape->mMatpolyList[j];if(!poly||!poly->mMaterial)continue;int material=-1;
                        for(int m=0;m<shape->mMaterialCount;++m)if(poly->mMaterial==&shape->mMaterialList[m])material=m;
                        if(material<0)std::abort();poly->mMaterial=&shared->mMaterialList[material];}
                    shape->mMaterialList=shared->mMaterialList;shape->mTexAttrList=shared->mTexAttrList;shape->mTevInfoList=shared->mTevInfoList;
                }
                animated[kind][clip.name].push_back(shape);
            }
        }
    }
    std::printf("P2_FROG_BANK_READY mod_bytes=%zu gameplay=P1_unchanged\n",total);
}

void stop(BTeki* a){a->inputDrive(Vector3f(0.0f,0.0f,0.0f));a->mVelocity.x=0.0f;a->mVelocity.y=0.0f;a->mVelocity.z=0.0f;}
void walkTo(BTeki* a,FrogFsm& s,const Vector3f& target,float speed,float dt){
    const Vector3f pos=a->getPosition();
    const float desired=std::atan2(target.x-pos.x,target.z-pos.z);
    const float maxTurn=TURN_RATE*dt;
    float diff=wrapPi(desired-s.heading);
    if(diff>maxTurn)diff=maxTurn;if(diff<-maxTurn)diff=-maxTurn;
    s.heading=wrapPi(s.heading+diff);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading)*speed,0.0f,std::cos(s.heading)*speed);
    a->inputDrive(drive);a->mVelocity.set(drive);
}
void turnTo(BTeki* a,FrogFsm& s,const Vector3f& target,float dt){
    const Vector3f pos=a->getPosition();
    const float desired=std::atan2(target.x-pos.x,target.z-pos.z);
    const float maxTurn=TURN_RATE*dt;
    float diff=wrapPi(desired-s.heading);
    if(diff>maxTurn)diff=maxTurn;if(diff<-maxTurn)diff=-maxTurn;
    s.heading=wrapPi(s.heading+diff);
    a->setDirection(s.heading);
}
Creature* nearestTarget(const Vector3f& pos,float sight){
    Creature* best=nullptr;float bestSq=sight*sight;
    for(Navi* n:pc_p2_navis()){if(n->isAlive()){const Vector3f p=n->getPosition();
        const float dx=p.x-pos.x,dz=p.z-pos.z,d=dx*dx+dz*dz;if(d<bestSq){bestSq=d;best=n;}}}
    if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
        const Vector3f q=p->getPosition();const float dx=q.x-pos.x,dz=q.z-pos.z,d=dx*dx+dz*dz;if(d<bestSq){bestSq=d;best=p;}}}
    return best;
}
int stuckPikminCount(Creature* creature){
    int n=0;
    for(Creature* s=creature->mStickListHead;s;s=s->mNextSticker){
        if(!s||!s->isPiki()||!s->isAlive())continue;
        ++n;
    }
    return n;
}
float probeFloorY(const Vector3f& pos,float fallback){
    if(!mapMgr)return fallback;
    // includePlatColl=true matches the engine grounded convention used by the
    // other P2 ground modules (pc_p2_bulbmin.cpp, pc_p2_dangomushi.cpp) and the
    // P1 fixture. The raw false query ignores platform/collision surfaces and
    // returns a lower Y, so the frog model sat below the floor (user: too low).
    const float y=mapMgr->getMinY(pos.x,pos.z,true);
    return std::isfinite(y)?y:fallback;
}
bool attackable(const FrogFsm& s,const Vector3f& pos,const Creature* target,float range){
    if(!target)return false;const Vector3f tp=target->getPosition();
    if(distXZ(pos,tp)>=range)return false;
    const float ang=std::fabs(wrapPi(std::atan2(tp.x-pos.x,tp.z-pos.z)-s.heading));
    return ang<ATTACK_ANGLE;
}
bool shouldFlick(BTeki* actor){return stuckPikminCount(actor)>=FLEE_STUCK_MIN;}
// MaroFrog attackNaviPosition: an in-range living captain overrides the jump
// landing point (the source captain retarget).
void retargetNavi(BTeki* actor,FrogFsm& s){
    // Source attackNaviPosition iterates every captain with no break
    // (MaroFrog.cpp:21-34): the last alive in-range captain in index order wins.
    if(s.kind!=1||!naviMgr)return;
    for(Navi* n:pc_p2_navis()){
        if(!n->isAlive())continue;
        const Vector3f np=n->getPosition();
        if(distXZ(actor->getPosition(),np)<p2frog::params(s.kind).attackRange){s.targetPos=np;s.targetValid=true;}
    }
}
// Source StateJump KEYEVENT_2: flickNearbyNavi + flickNearbyPikmin (non-damaging
// adjacent shake; the P2 water branch is absent on the dry P1 host).
void doJumpFlick(BTeki* actor,FrogFsm& s){
    const Vector3f pos=actor->getPosition();
    const float range=p2frog::params(s.kind).shakeRange;
    int hit=0;
    if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){Piki* q=static_cast<Piki*>(*it);if(!q||!q->isAlive())continue;
        if(distXZ(q->getPosition(),pos)<range){if(q->stimulate(InteractFlick(actor,FLICK_KNOCKBACK,FLICK_DAMAGE,FLICK_BACKWARDS_ANGLE)))++hit;}}}
    for(Navi* n:pc_p2_navis()){if(n->isAlive()&&distXZ(n->getPosition(),pos)<range)
        if(n->stimulate(InteractFlick(actor,FLICK_KNOCKBACK,FLICK_DAMAGE,FLICK_BACKWARDS_ANGLE)))++hit;}
    std::printf("P2_FROG_JUMP_FLICK species=%s hit=%d\n",ids[s.kind],hit);std::fflush(stdout);
}
// Source collisionCallback while falling: InteractPress(attackDamage) on grounded
// (floor-triangle) non-bittered Navi/Pikmin inside the source head radius, applied
// once at the Fall->Attack landing. The separate pressOnGround stuck-shakeoff is
// not reproduced on the P1 host (see the jump flick instead).
int doLandPress(BTeki* actor,FrogFsm& s){
    if(isBittered(static_cast<PelletView*>(actor)))return 0;
    const Vector3f pos=actor->getPosition();
    const float radius=p2frog::headRadius(s.kind);
    const p2frog::Params& p=p2frog::params(s.kind);
    int pressedPikmin=0,pressedNavi=0;
    if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){Piki* q=static_cast<Piki*>(*it);if(!q||!q->isAlive()||q->isFlying())continue;
        const Vector3f qp=q->getPosition();const float dx=qp.x-pos.x,dz=qp.z-pos.z;
        if(dx*dx+dz*dz<=radius*radius){if(q->stimulate(InteractPress(actor,p.attackDamage)))++pressedPikmin;}}}
    if(naviMgr){Iterator it(naviMgr);CI_LOOP(it){Navi* n=static_cast<Navi*>(*it);if(!n||!n->isAlive()||n->isFlying())continue;
        const Vector3f np=n->getPosition();const float dx=np.x-pos.x,dz=np.z-pos.z;
        if(dx*dx+dz*dz<=radius*radius){if(n->stimulate(InteractPress(actor,p.attackDamage)))++pressedNavi;}}}
    std::printf("P2_FROG_LAND species=%s radius=%.1f bittered=0 pikmin=%d navi=%d behavior=source\n",ids[s.kind],radius,pressedPikmin,pressedNavi);
    std::fflush(stdout);
    return pressedPikmin+pressedNavi;
}
void setPhase(int kind,FrogFsm& s){
    const float dur=clipSeconds(kind,s.clip);
    float ph=s.stateTime/dur;
    if(ph>1.0f)ph=1.0f;
    s.phase=ph;
}
void transition(BTeki* actor,FrogFsm& s,FState st,const char* clip,unsigned gen){
    s.state=st;s.stateTime=0.0f;s.launched=false;s.pressDone=false;s.jumpEntryChecked=false;if(clip)s.clip=clip;
    std::printf("P2_FROG_STATE species=%s generator=%u state=%s\n",ids[s.kind],gen,p2frog::stateName(st));
    std::fflush(stdout);
}
// Source death is deferred to the per-state exec points, never taken mid-air:
// Wait (isDead), Turn/TurnToHome/GoHome (mNextState=Dead, finishMotion), and
// Attack/Fail (KEYEVENT_END). Jump/JumpWait/Fall never transit to Dead directly.
void die(BTeki* actor,FrogFsm& s,unsigned gen,float priorHealth){
    if(!s.deadLogged){s.deadLogged=true;const unsigned sourceId=s.kind?18u:17u;std::printf("P2_FROG_DEAD species=%s generator=%u source_id=%u health=0 prior_health=%.1f\n",ids[s.kind],gen,sourceId,priorHealth);std::fflush(stdout);}
    transition(actor,s,FRG_DEAD,"dead",gen);
}
void launchHop(BTeki* actor,FrogFsm& s){
    const Vector3f pos=actor->getPosition();
    const p2frog::Params& p=p2frog::params(s.kind);
    s.groundY=probeFloorY(pos,s.groundY);
    const float dx=s.targetPos.x-pos.x,dz=s.targetPos.z-pos.z;
    const float len=std::sqrt(dx*dx+dz*dz);
    s.flight=p2frog::launchFlight(pos.x,s.groundY,pos.z,s.targetPos.x,s.targetPos.z,p.airTime,p.jumpSpeed);
    if(len>0.0001f)s.heading=std::atan2(dx,dz);
    actor->setDirection(s.heading);
}
void advanceHop(BTeki* actor,FrogFsm& s,float dt){
    const p2frog::Params& p=p2frog::params(s.kind);
    // Own the complete airborne position: host physics ran before this update.
    p2frog::advanceFlying(s.flight,s.targetPos.x,s.targetPos.z,p.airTime,dt);
    actor->getPosition().set(s.flight.x,s.flight.y,s.flight.z);
}
}
void pc_p2_frog_reset(){actors.clear();fsms.clear();pressing.clear();bitteredFrogs.clear();drawn.clear();drawnCorpse.clear();for(auto& b:animated)b.clear();for(auto& b:timing)b.clear();ready=false;}
void pc_p2_frog_forget(BTeki* actor){auto* v=static_cast<PelletView*>(actor);pc_randomizer_p2_forget_source(v);actors.erase(v);fsms.erase(v);pressing.erase(v);bitteredFrogs.erase(v);drawn.erase(v);drawnCorpse.erase(v);}
void pc_p2_frog_set_bittered(BTeki* actor,bool bittered){auto* view=static_cast<PelletView*>(actor);if(!actors.count(view))return;if(bittered)bitteredFrogs.insert(view);else bitteredFrogs.erase(view);}
const char* pc_p2_frog_name(PelletView* view){auto i=actors.find(view);return i==actors.end()?nullptr:ids[i->second];}
float pc_p2_frog_param_f(const BTeki* actor,int idx,float fallback){
    auto i=actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));if(i==actors.end())return fallback;
    const p2frog::Params& p=p2frog::params(i->second);
    switch(idx){
    case TPF_Life:return p.health;
    case TPF_VisibleRange:return p.sight;
    case TPF_AttackableRange:return p.attackRange;
    case TPF_AttackPower:return p.attackDamage;
    default:return fallback;
    }
}
bool pc_p2_frog_suppress_ai(const BTeki* actor){return ready&&actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))!=0;}
void pc_p2_frog_setup(){
    pc_p2_frog_reset();
    std::printf("P2_FROG_SETUP\n");std::fflush(stdout);
    const bool bridge = pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview();
    const bool preview = pc_pikipelago_room_preview();
    if(!bridge && !preview)return;
    std::ifstream input("p2-frog.txt");if(!input)return;
    std::map<unsigned,int> wanted;std::vector<p2animation::Clip> banks[2];
    if(!p2frog::parse(input,wanted,banks))std::abort();
    if(bridge){
        // Campaign identity comes from the seed (sources 17 Frog + 18 MaroFrog).
        // Filed generators are placeholders there.
        wanted.clear();
        for(unsigned id : pc_p2_campaign_ids(17)) wanted[id]=0;
        for(unsigned id : pc_p2_campaign_ids(18)) wanted[id]=1;
    }
    if(wanted.empty())return;
    std::set<unsigned> seen;
    Iterator it(tekiMgr);CI_LOOP(it){Teki* teki=static_cast<Teki*>(*it);if(!teki||!teki->mGenerator)continue;
        const unsigned token = bridge ? pc_p2_campaign_token(teki) : teki->mGenerator->_70;
        auto found=wanted.find(token);if(found==wanted.end())continue;
        int kind=found->second;if(!seen.insert(found->first).second)std::abort();if(teki->mTekiType!=(kind?TEKI_Frow:TEKI_Frog))std::abort();
        actors[static_cast<PelletView*>(teki)]=kind;
        teki->mHealth=p2frog::params(kind).health;
        FrogFsm& f=fsms[static_cast<PelletView*>(teki)];
        f.kind=kind;f.home=teki->getPosition();f.heading=teki->getDirection();
        f.groundY=probeFloorY(teki->getPosition(),teki->getPosition().y);f.targetPos=f.home;f.targetValid=true;
        f.rng=(token*2654435761u)|1u;
        f.token=token;
        f.state=FRG_WAIT;f.clip="wait1";f.phase=0.0f;
        f.lastHealth=teki->mHealth;
        const unsigned sourceId = kind ? 18u : 17u;
        if(bridge){
            pc_randomizer_p2_bind_source(static_cast<PelletView*>(teki), sourceId, token);
            std::printf("P2_FROG_DELIVERY_BIND generator=%u source_id=%u\n",token,sourceId);
        }
        std::printf("P2_FROG_BIND generator=%u source_id=%u visual_only=0\n",token,sourceId);
        std::printf("P2_FROG_READY species=%s generator=%u health=%.1f max_health=%.1f behavior=source_fsm rewards=P1_unchanged\n",ids[kind],token,teki->mHealth,teki->getParameterF(TPF_Life));
        std::printf("P2_ENEMY_READY species=%s native_family=Frog generator=%u x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native source_FSM=implemented\n",ids[kind],token,teki->getPosition().x,teki->getPosition().y,teki->getPosition().z,teki->mHealth,p2frog::params(kind).health);
        std::printf("P2_FROG_STATE species=%s generator=%u state=wait\n",ids[kind],token);
        std::fflush(stdout);
    }
    if(seen.size()!=wanted.size()){
        std::printf("P2_FROG_ERROR missing_actor wanted=%zu found=%zu\n",wanted.size(),seen.size());
        std::abort();
    }
    loadAnimation(banks);ready=true;
}
void pc_p2_frog_update(BTeki* actor){
    if(!ready)return;
    auto it=actors.find(static_cast<PelletView*>(actor));if(it==actors.end())return;
    auto ft=fsms.find(static_cast<PelletView*>(actor));if(ft==fsms.end())return;
    FrogFsm& s=ft->second;
    const float dt=gsys->getFrameTime();if(dt<=0.0f||dt>0.5f)return;
    const Vector3f pos=actor->getPosition();
    const unsigned live=actor->mGenerator?pc_p2_campaign_token(actor):0u;
    if(live) s.token=live;
    const unsigned gen=s.token ? s.token : live;
    const unsigned sourceId = s.kind ? 18u : 17u;
    const p2frog::Params& p=p2frog::params(s.kind);

    // The P1 TAI reaction path (`TaiDamagingAction`) normally applies stored
    // damage through makeDamaged(); it is suppressed for registered frogs, so
    // the source FSM applies pending damage itself. Mirrors TAIsimultaneousDamage.
    if(actor->mStoredDamage>0.0f)actor->makeDamaged();

    // Natural-combat observability: incremental still-positive decrease is real
    // attack damage. Death marker records prior_health for fixture distinction.
    const float previousHealth = s.lastHealth;
    if(actor->mHealth<=0.0f&&!s.deathPriorSet&&previousHealth>0.0f){s.deathPrior=previousHealth;s.deathPriorSet=true;}
    const float priorForDeath=s.deathPriorSet?s.deathPrior:previousHealth;
    if(actor->mHealth < s.lastHealth && actor->mHealth > 0.0f){
        std::printf("P2_FROG_DAMAGE generator=%u source_id=%u health=%.1f\n",gen,sourceId,actor->mHealth);
        std::fflush(stdout);
    }
    s.lastHealth = actor->mHealth;

    s.stateTime+=dt;
    switch(s.state){
    case FRG_WAIT:{
        stop(actor);
        actor->getPosition().y=s.groundY;
        if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
        if(shouldFlick(actor)){
            s.targetPos=pos;s.targetValid=true;retargetNavi(actor,s);
            transition(actor,s,FRG_JUMP,"type1",gen);
            break;
        }
        if(s.stateTime>=clipSeconds(s.kind,s.clip)){
            s.stateTime=0.0f;
            Creature* t=nearestTarget(pos,p.sight);
            if(t){
                s.targetPos=t->getPosition();s.targetValid=true;retargetNavi(actor,s);
                if(attackable(s,pos,t,p.attackRange))transition(actor,s,FRG_JUMP,"type1",gen);
                else if(std::fabs(wrapPi(std::atan2(s.targetPos.x-pos.x,s.targetPos.z-pos.z)-s.heading))>FACE_OK_ANGLE)
                    transition(actor,s,FRG_TURN,"waitact1",gen);
            }
        }
        break;
    }
    case FRG_TURN:{
        stop(actor);
        actor->getPosition().y=s.groundY;
        if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
        if(shouldFlick(actor)){s.targetPos=pos;s.targetValid=true;transition(actor,s,FRG_JUMP,"type1",gen);break;}
        Creature* t=nearestTarget(pos,p.sight);
        if(t){
            turnTo(actor,s,t->getPosition(),dt);
            if(attackable(s,pos,t,p.attackRange)){
                s.targetPos=t->getPosition();s.targetValid=true;retargetNavi(actor,s);
                transition(actor,s,FRG_JUMP,"type1",gen);
            } else if(std::fabs(wrapPi(std::atan2(t->getPosition().x-pos.x,t->getPosition().z-pos.z)-s.heading))<=FACE_OK_ANGLE){
                transition(actor,s,FRG_WAIT,"wait1",gen);
            } else if(s.stateTime>=clipSeconds(s.kind,"waitact1")){
                transition(actor,s,FRG_WAIT,"wait1",gen);
            }
        } else {
            transition(actor,s,FRG_WAIT,"wait1",gen);
        }
        break;
    }
    case FRG_JUMP:{
        stop(actor);
        if(!s.launched)actor->getPosition().y=s.groundY;
        if(!s.jumpEntryChecked){
            s.jumpEntryChecked=true;
            if(stuckPikminCount(actor)>0&&rand01(s)<p.jumpFail){transition(actor,s,FRG_FAIL,"damage",gen);break;}
        }
        if(!s.launched&&s.stateTime>=JUMP_LAUNCH_S){
            s.launched=true;launchHop(actor,s);doJumpFlick(actor,s);
        }
        if(s.launched)advanceHop(actor,s,dt);
        if(s.stateTime>=clipSeconds(s.kind,"type1"))transition(actor,s,FRG_JUMPWAIT,"wait2",gen);
        break;
    }
    case FRG_JUMPWAIT:{
        stop(actor);
        advanceHop(actor,s,dt);
        // Retail wait2 loops frames 18..19 until mAirTime expires, then plays
        // the remaining tail before Fall applies its separate downward speed.
        if(p2frog::readyToFall(s.flight.elapsed,s.stateTime,p.airTime,clipSeconds(s.kind,"wait2"))){
            p2frog::startFall(s.flight,p.fallSpeed);
            transition(actor,s,FRG_FALL,"type2",gen);
        }
        break;
    }
    case FRG_FALL:{
        stop(actor);
        // Source StateFall::exec lands on floor-triangle contact (FrogState.cpp:341),
        // not on a timer: transit once the probed floor reaches the falling frog.
        // Sample the destination, not the takeoff ground height.
        const Vector3f landing(s.flight.x,s.flight.y,s.flight.z);
        const float floorY=probeFloorY(landing,s.groundY);
        const bool landed=p2frog::advanceFalling(s.flight,floorY,dt);
        actor->getPosition().set(s.flight.x,s.flight.y,s.flight.z);
        if(landed){
            s.groundY=floorY;
            actor->getPosition().y=s.groundY;transition(actor,s,FRG_ATTACK,"attack",gen);
        }
        break;
    }
    case FRG_ATTACK:{
        stop(actor);
        actor->getPosition().y=s.groundY;
        if(!s.pressDone){s.pressDone=true;doLandPress(actor,s);}
        if(s.stateTime>=clipSeconds(s.kind,"attack")){
            if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
            if(distXZ(pos,s.home)>TERRITORY)transition(actor,s,FRG_TURNTOHOME,"waitact1",gen);
            else transition(actor,s,FRG_WAIT,"wait1",gen);
        }
        break;
    }
    case FRG_FAIL:{
        stop(actor);
        actor->getPosition().y=s.groundY;
        if(s.stateTime>=clipSeconds(s.kind,"damage")){
            if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
            if(shouldFlick(actor))transition(actor,s,FRG_JUMP,"type1",gen);
            else if(distXZ(pos,s.home)>TERRITORY)transition(actor,s,FRG_TURNTOHOME,"waitact1",gen);
            else transition(actor,s,FRG_WAIT,"wait1",gen);
        }
        break;
    }
    case FRG_TURNTOHOME:{
        stop(actor);
        actor->getPosition().y=s.groundY;
        if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
        if(shouldFlick(actor)){s.targetPos=pos;s.targetValid=true;transition(actor,s,FRG_JUMP,"type1",gen);break;}
        turnTo(actor,s,s.home,dt);
        if(std::fabs(wrapPi(std::atan2(s.home.x-pos.x,s.home.z-pos.z)-s.heading))<=FACE_OK_ANGLE||s.stateTime>=clipSeconds(s.kind,"waitact1"))
            transition(actor,s,FRG_GOHOME,"move1",gen);
        break;
    }
    case FRG_GOHOME:{
        actor->getPosition().y=s.groundY;
        if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
        if(distXZ(pos,s.home)<HOME_RADIUS){transition(actor,s,FRG_WAIT,"wait1",gen);break;}
        if(shouldFlick(actor)){s.targetPos=pos;s.targetValid=true;transition(actor,s,FRG_JUMP,"type1",gen);break;}
        walkTo(actor,s,s.home,MOVE_SPEED,dt);
        break;
    }
    case FRG_DEAD:{
        stop(actor);
        actor->getPosition().y=s.groundY;
        // dieSoon() only runs inside the P1 doAI block, which is suppressed for
        // registered frogs; pcEscapeNow() finalizes the corpse outside doAI,
        // fired exactly once when the dead animation completes.
        if(!s.escaped&&s.stateTime>=clipSeconds(s.kind,"dead")){s.escaped=true;actor->pcEscapeNow();}
        break;
    }
    default:break;
    }
    setPhase(s.kind,s);
    s.logTimer+=dt;
    if(s.logTimer>=1.0f){s.logTimer=0.0f;const Vector3f now=actor->getPosition();
        std::printf("P2_FROG_FSM_POS species=%s generator=%u state=%s x=%.2f y=%.2f z=%.2f health=%.1f\n",
            ids[s.kind],gen,p2frog::stateName(s.state),now.x,now.y,now.z,actor->mHealth);std::fflush(stdout);}
}
bool pc_p2_frog_probe(const BTeki* actor,const char** state,const char** clip,float* phase){
    auto* view=static_cast<PelletView*>(const_cast<BTeki*>(actor));
    if(!actors.count(view))return false;
    auto ft=fsms.find(view);if(ft==fsms.end())return false;
    if(state)*state=p2frog::stateName(ft->second.state);
    if(clip)*clip=ft->second.clip.c_str();
    if(phase)*phase=ft->second.phase;
    return true;
}
bool pc_p2_frog_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    auto it=actors.find(static_cast<PelletView*>(actor));if(it==actors.end())return false;
    int kind=it->second;if(!corpse)logPress(actor,kind);
    {
        auto* view=static_cast<PelletView*>(actor);
        auto ftok=fsms.find(view);
        const unsigned liveTok=actor->mGenerator?pc_p2_campaign_token(actor):0u;
        const unsigned token=liveTok ? liveTok : (ftok!=fsms.end()?ftok->second.token:0u);
        const unsigned sourceId=kind?18u:17u;
        if(drawn.insert(view).second){
            std::printf("P2_FROG_DRAW generator=%u source_id=%u species=%s corpse=%d\n",token,sourceId,ids[kind],int(corpse));
            std::fflush(stdout);
        }
        if(corpse && drawnCorpse.insert(view).second){
            std::printf("P2_FROG_CORPSE_DRAW generator=%u source_id=%u species=%s\n",token,sourceId,ids[kind]);
            std::fflush(stdout);
        }
    }
    auto ft=fsms.find(static_cast<PelletView*>(actor));
    const char* name=corpse?"dead":(ft!=fsms.end()?ft->second.clip.c_str():p2frog::motionClip(actor->mTekiAnimator->getCurrentMotionIndex()));
    Shape* shape=animated[kind].at("wait1").front();
    if(name){
        float phase=corpse?1.0f:(ft!=fsms.end()?ft->second.phase:0.0f);
        shape=animated[kind].at(name).at(timing[kind].at(name).index(phase,corpse));
    }
    shape->updateAnim(gfx,matrix,nullptr,actor);
    // lane09 specular-instrumentation hook: bracket the family's own draw so the
    // renderer can attribute its GX_AF_SPEC COLOR1 uploads to this family draw.
    pc_gfx_specular_family_scope(1);
    shape->drawshape(gfx,*gfx.mCamera,nullptr);
    pc_gfx_specular_family_scope(0);
    return true;
}
