// Kabuto 75 own identity on TEKI_Beatle: free larva FSM (Dead/Wait/Turn/Move/
// Flick/Attack) with mouth-joint stone fire (Stone 74, non-homing for 75).
// Bridge binds via campaign_ids + bind_source (onion:p2:75); P2 FSM decides
// every tick, host AI suppressed.
// #884: the attack births a travelling Stone on KEYEVENT_2 (attack frame 50,
// seen by exec after 51 animation frames) at the source mouth joint into a
// shooter-independent fleet (pc_p2_kabuto_stone_fleet.h) ticked at 30 Hz from
// gameCoreSection, instead of an instant cone strike. The attack tick itself
// is p2kabutostone::attackStep, which the regression test drives directly.
// #884 round 4: Attack is entered only through the source isAttackableTarget
// lane and the source Wait/Turn/Move selection (pc_p2_kabuto_aim.h), not the
// old 180 / 0.5 rad cone.
#include "pc_p2_kabuto_fsm.h"
#include "pc_p2_original_cannon_bank.h"
#include "pc_p2_original_cannon_combat.h"
#include "pc_p2_attachments.h"
#include "pc_p2_body_coll.h"
#include "pc_p2_original_cannon_native.h"
#include "pc_p2_original_actor.h"
#include "pc_p2_original_drop_engine.h"
#include "pc_p2_sfx.h"
#include "pc_p2_kabuto_fsm_policy.h"
#include "pc_p2_kabuto_stone_fleet.h"
#include "pc_p2_kabuto_aim.h"
#include "pc_p2_rock_host.h"
#include "pc_p2_projectile_engine_receiver.h"
#include "pc_p2_campaign_actor.h"
#include "pc_randomizer.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "EffectMgr.h"
#include "MapMgr.h"
#include "zen/particle.h"
#include "gameflow.h"
#include "pc_p2_pose_family.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Pellet.h"
#include "Boss.h"
#include "Interactions.h"
#include "MapMgr.h"
#include "MoviePlayer.h"
#include "AIConstant.h"
#include "ObjType.h"
#include "system.h"
#include "gl/pc_gfx.h"
#include <cstdint>
#include <map>
#include <set>
#include <vector>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
std::map<PelletView*,bool> actors;
std::map<std::string,std::vector<Shape*>> animated;
std::map<std::string,p2animation::Clip> timing;
std::set<PelletView*> drawn,drawnCorpse;
enum KState { KB_DEAD=0,KB_WAIT=1,KB_TURN=2,KB_MOVE=3,KB_FLICK=4,KB_ATTACK=5,KB_FIXSTAY=6,KB_FIXAPPEAR=7,KB_FIXHIDE=8,KB_FIXWAIT=9,KB_FIXTURN=10,KB_FIXATTACK=11,KB_FIXFLICK=12 };
const float PI_F=3.14159265f;
constexpr int FLICK_STUCK_MIN=3;
struct KabutoFsm {
    unsigned source=75;bool original=false;KState next=KB_WAIT;
    p2attach::Instance sockets;p2attach::Token socketToken=0;std::uint64_t socketTick=0;
    KState state=KB_WAIT;float stateTime=0.0f;float heading=0.0f;
    Vector3f home;Vector3f targetPos;bool targetValid=false;
    unsigned rng=1;unsigned token=0;bool deadLogged=false;bool fireDone=false;bool flickDone=false;bool escaped=false;float deathPrior=0.0f;bool deathPriorSet=false;
    std::string clip="wait";float phase=0.0f;float logTimer=0.0f;float lastHealth=0.0f;float poolFullCooldown=0.0f;
    // #884 round 4 source Wait/Turn/Move selection (pc_p2_kabuto_aim.h):
    // StateWait mStateTimer + latched mNextState, StateMove mStateTimer,
    // mAlertTimer (Kabuto.cpp:296-305, starts 0 at onInit :43) and the
    // setRandTarget wander point (Kabuto.cpp:198-206).
    float waitTimer=0.0f;bool waitNextTurn=false;float moveTimer=0.0f;float alert=0.0f;
    p2kabutoaim::Vec3 wander;
};
std::map<PelletView*,KabutoFsm> fsms;
bool ready=false;
// #884 Stone fleet. Stones outlive their shooter: they are owned here, not by
// the actor, and are cleared only by reset (teardown / re-entry).
p2kabutostone::Fleet fleet;
struct StoneMap{p2rockhost::TraceProxy proxy;unsigned long long calls=0,walls=0;} stoneMap;
double stoneDebt=0.0;
unsigned slotGen[p2kabutostone::kFleetCapacity]={};
int slotPosTicks[p2kabutostone::kFleetCapacity]={};
// Visual-only roll state (#884): horizontal distance rolled per slot and the
// tick counter for the ground dust; neither feeds the simulation.
float slotRoll[p2kabutostone::kFleetCapacity]={};
int slotDustTicks[p2kabutostone::kFleetCapacity]={};
bool stoneDrawLogged=false;
constexpr int kDustTickInterval=3;       // 10 Hz puffs
constexpr float kDustGroundSlack=6.0f;   // base within 6 of the floor = rolling
constexpr float kDustParticles=3.0f;
constexpr short kDustLifetime=20;
// The P1 Iwagon mesh (tekis/iwagon/iwagon.mod) is a unit-scale boulder centred
// on its origin, radius 25.44 (vertex extremes -28.5..25.4).
constexpr float kIwagonMeshRadius=25.44f;
std::map<std::uint64_t,BTeki*> shooters;
std::uint64_t tokenOf(Creature* c){return static_cast<std::uint64_t>(reinterpret_cast<std::uintptr_t>(c));}
float wrapPi(float a){while(a>PI_F)a-=2.0f*PI_F;while(a<-PI_F)a+=2.0f*PI_F;return a;}
float distXZ(const Vector3f& a,const Vector3f& b){const float dx=a.x-b.x,dz=a.z-b.z;return std::sqrt(dx*dx+dz*dz);}
float clipSeconds(const std::string& name){auto it=timing.find(name);return it==timing.end()?1.0f:it->second.duration/30.0f;}
p2posefamily::Bank poseBank("KABUTO"); // #895 interpolated draw
p2posefamily::Actors poseVis;
struct OriginalResources {
 p2posefamily::Bank bank{"ORIGINAL_CANNON"};
 std::map<std::string,std::vector<Shape*>> shapes;
 std::map<std::string,p2animation::Clip> clocks;
};
OriginalResources originalResources[2];
OriginalResources originalStoneResource;
bool slotOriginal[p2kabutostone::kFleetCapacity]={};
std::shared_ptr<const p2attach::Bank> originalSockets;
const auto& clocks(const KabutoFsm& s){return s.original?originalResources[s.source-95].clocks:timing;}
float seconds(const KabutoFsm& s,const std::string& clip){auto i=clocks(s).find(clip);return i==clocks(s).end()?1.0f:i->second.duration/30.0f;}
const char* stateName(int s){static const char* names[]={"dead","wait","turn","move","flick","attack","fixstay","fixappear","fixhide","fixwait","fixturn","fixattack","fixflick"};return s>=0&&s<13?names[s]:"null";}
void loadAnimation(const std::vector<p2animation::Clip>& bank){
    // #895: compact loader (few Shapes + decoded vectors per clip); the Shapes
    // stay the nearest-pose fallback. Fail-closed as before.
    size_t total=0;p2poseload::Shared shared;
    for(const auto& clip:bank){timing[clip.name]=clip;
        std::string error;
        if(!p2posefamily::loadFamilyClip(poseBank,clip.name,"kabuto_Kabuto_"+clip.name,clip.count,clip.duration,clip.frames,shared,total,animated[clip.name],error)){
            std::printf("P2_KABUTO_BANK_INVALID clip=%s reason=%s\n",clip.name.c_str(),error.c_str());std::fflush(stdout);std::abort();}
    }
    std::printf("P2_KABUTO_BANK_READY mod_bytes=%zu resident=1 gameplay=P1_unchanged\n",total);
}
void stop(BTeki* a){a->inputDrive(Vector3f(0.0f,0.0f,0.0f));a->mVelocity.x=0.0f;a->mVelocity.y=0.0f;a->mVelocity.z=0.0f;}
// Facing (EnemyBase::updateFaceDir) and StateMove setTargetSpeed along it.
void face(BTeki* a,KabutoFsm& s,float heading){s.heading=wrapPi(heading);a->setDirection(s.heading);}
void driveForward(BTeki* a,KabutoFsm& s,float speed){
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading)*speed,0.0f,std::cos(s.heading)*speed);
    a->inputDrive(drive);a->mVelocity.set(drive);
}
p2kabutoaim::Vec3 aimVec(const Vector3f& v){p2kabutoaim::Vec3 r;r.x=v.x;r.y=v.y;r.z=v.z;return r;}
// Host candidate snapshot for getSearchedTarget / isAttackableTarget: every
// live Navi (co-op: all of naviMgr) and every live Pikmin, at getPosition()
// (source uses creature positions, Kabuto.cpp:248, enemyAction.cpp:47-49).
// P1 Piki::isAlive only excludes Dying / Dead (piki.cpp:2546-2553), so the
// P1 state is mapped to its P2 object (pc_p2_kabuto_aim.h PikminPhase):
// planted / in-ground Pikmin are P2 sprouts (never targets); squashed,
// electrocuted and swallowed Pikmin are in P2 states whose dead() is true,
// so P2 Piki::isAlive rejects them (never searched, never in the lane).
// Any mouth-held Pikmin counts as swallowed: P2 InteractSwallow::actPiki
// transits every startStickMouth victim to PIKISTATE_Swallowed
// (interactPiki.cpp:672,689), while P2-bridged mouths here may stick a P1
// Piki to the mouth without the P1 Swallowed state.
p2kabutoaim::PikminPhase pikminPhase(Piki* p){
    if(p->isStickToMouth())return p2kabutoaim::PikminPhase::Dead;
    switch(p->getState()){
    case PIKISTATE_Grow:case PIKISTATE_Bury:case PIKISTATE_NukareWait:return p2kabutoaim::PikminPhase::Sprout;
    case PIKISTATE_Pressed:case PIKISTATE_DenkiDying:case PIKISTATE_Swallowed:return p2kabutoaim::PikminPhase::Dead;
    default:return p2kabutoaim::PikminPhase::Active;}
}
struct AimSnapshot{std::vector<p2kabutoaim::Candidate> cands;std::vector<Creature*> creatures;};
void buildAim(AimSnapshot& a){
    a.cands.clear();a.creatures.clear();
    auto push=[&](Creature* c,const p2kabutoaim::Candidate& k){if(!k.alive&&!k.searchable)return;a.cands.push_back(k);a.creatures.push_back(c);};
    if(naviMgr){Iterator it(naviMgr);CI_LOOP(it){Navi* n=static_cast<Navi*>(*it);if(!n||!n->isAlive())continue;
        push(n,p2kabutoaim::naviCandidate(aimVec(n->getPosition()),true));}}
    if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){Piki* q=static_cast<Piki*>(*it);if(!q||!q->isAlive())continue;
        push(q,p2kabutoaim::pikminCandidate(aimVec(q->getPosition()),true,pikminPhase(q)));}}
}
float rngUnit(KabutoFsm& s){s.rng=s.rng*1664525u+1013904223u;return float((s.rng>>8)&0xffffffu)/16777216.0f;}
int stuckPikminCount(Creature* c){int n=0;for(Creature* s=c->mStickListHead;s;s=s->mNextSticker){if(!s||!s->isPiki()||!s->isAlive())continue;++n;}return n;}
bool shouldFlick(BTeki* a){auto f=fsms.find(static_cast<PelletView*>(a));
 // Retail all four blow thresholds are3: rounded flick timer must exceed3.
 // Every accepted EnemyBase::damageCallBack adds1; original Attack uses
 // interactDefault's damage count instead of the P1 armour-portion gate.
 return f!=fsms.end()&&f->second.original?a->mDamageCount>=4.0f:stuckPikminCount(a)>=FLICK_STUCK_MIN;}
// Lane evidence on every natural Attack entry (Kabuto.cpp:226-262 gate).
void logLane(unsigned gen,const char* from,const KabutoFsm& s,const Vector3f& pos,const AimSnapshot& a){
    const p2kabutoaim::Vec3 p=aimVec(pos);
    const int i=p2kabutoaim::attackableIndex(p,s.heading,a.cands.data(),int(a.cands.size()));
    if(i<0){std::printf("P2_KABUTO_LANE generator=%u from=%s lane=0 face_deg=%.1f\n",gen,from,s.heading*180.0f/PI_F);std::fflush(stdout);return;}
    const p2kabutoaim::LaneCoords l=p2kabutoaim::laneCoords(p,s.heading,a.cands[size_t(i)].pos);
    std::printf("P2_KABUTO_LANE generator=%u from=%s lane=1 face_deg=%.1f target=%s forward=%.1f lateral=%.1f dy=%.1f\n",
        gen,from,s.heading*180.0f/PI_F,a.cands[size_t(i)].navi?"navi":"piki",l.forward,l.lateral,l.dy);std::fflush(stdout);
}
// P1 Armored Cannon Beetle shot burst (TAIbeatle.cpp:605-623): when the beetle
// spawns its rolling boulder it emits EFF_Beatle_RockClouds / RockSpray /
// RockBlast 60 units ahead of the mouth, along the mouth's forward axis. The
// source P2 createRockEmitEffect is a JPA2 particle this port cannot play, so
// the P1 beetle's own effects stand in (owner request, #884). One-shots only:
// no generator handle is retained.
void p1BeetleShotBurst(const P2CannonStoneVec3& birth,float heading){
    if(!effectMgr)return;
    const Vector3f dir(std::sin(heading),0.0f,std::cos(heading));
    const Vector3f at(birth.x+dir.x*60.0f,birth.y,birth.z+dir.z*60.0f);
    const EffectMgr::effTypeTable ids[3]={EffectMgr::EFF_Beatle_RockClouds,EffectMgr::EFF_Beatle_RockSpray,EffectMgr::EFF_Beatle_RockBlast};
    for(EffectMgr::effTypeTable id:ids){
        zen::particleGenerator* g=effectMgr->create(id,at,nullptr,nullptr);
        if(g)g->setEmitDir(dir);
    }
}
// Logs the outcome of p2kabutostone::attackStep (source StateAttack KEYEVENT_2
// -> createStoneAttack, Kabuto.cpp:268-290): Stone 74 born at the "mouth"
// joint XZ (retail pose at attack frame 51) and 25 over the Kabuto's own Y,
// facing the Kabuto, non-homing for 75. The Stone then travels (fleet tick
// below). The rock emit effect (createRockEmitEffect) is not reproduced.
void logStoneFire(KabutoFsm& s,unsigned gen,const p2kabutostone::AttackStep& step){
    if(step.action==p2kabutostone::AttackAction::PoolFull){
        // Rock manager birth failure is silently tolerated (Kabuto.cpp:283).
        if(s.poolFullCooldown<=0.0f){s.poolFullCooldown=1.0f;
            std::printf("P2_KABUTO_STONE_POOL_FULL generator=%u active=%d cap=%d\n",gen,fleet.active(),p2kabutostone::Fleet::capacity());std::fflush(stdout);}
        return;
    }
    if(step.action!=p2kabutostone::AttackAction::Fired)return;
    pc_p2_sfx(s.source,gen,p2sfx::Event::Shot,Vector3f(step.birth.x,step.birth.y,step.birth.z));
    const int slot=step.slot;
    slotOriginal[slot]=s.original;slotGen[slot]=gen;slotPosTicks[slot]=0;slotRoll[slot]=0.0f;slotDustTicks[slot]=0;
    p1BeetleShotBurst(step.birth,s.heading);
    const auto& resource=clocks(s);const auto at=resource.find(s.source==96?"K_attack":"attack");
    std::printf("P2_KABUTO_STONE_BIRTH generator=%u source_id=%u stone=%u stone_type=74 slot=%d homing=%d frame=%d t=%.4f clip_frames=%d birth=(%.2f,%.2f,%.2f) face_deg=%.1f mouth_source=joint pose_frame=%d mouth_local=(%.3f,%.3f) active=%d\n",
        gen,s.source,step.id,slot,int(fleet.stone(slot).homing()),s.source==96?55:50,s.stateTime,at==resource.end()?0:at->second.duration,
        step.birth.x,step.birth.y,step.birth.z,s.heading*180.0f/PI_F,s.source==96?56:51,p2kabutostone::kMouthLocalX,p2kabutostone::kMouthLocalZ,fleet.active());
    std::fflush(stdout);
}
int doFlick(BTeki* actor,bool stuckOnly=false,bool backwards=false){
    const auto f=fsms.find(static_cast<PelletView*>(actor));const bool original=f!=fsms.end()&&f->second.original;const float range=original?45.0f:120.0f;
    const Vector3f pos=actor->getPosition();
    int hit=0;
    std::vector<Piki*> pikis;
    if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){Piki* q=static_cast<Piki*>(*it);if(!q||!q->isAlive())continue;
        if((!stuckOnly&&distXZ(q->getPosition(),pos)<range)||(original&&q->mStickTarget==actor))pikis.push_back(q);}}
    for(Piki* q:pikis){if(!q||!q->isAlive())continue;
        const float angle=original?p2original::cannon::pikminFlickAngle(actor->getDirection(),backwards,FLICK_BACKWARDS_ANGLE):FLICK_BACKWARDS_ANGLE;
        if(q->stimulate(InteractFlick(actor,original?400.0f:300.0f,original?1.0f:0.0f,angle)))++hit;}
    for(Navi* n:pc_p2_navis()){if(!stuckOnly&&n->isAlive()&&distXZ(n->getPosition(),pos)<range)
        if(n->stimulate(InteractFlick(actor,original?400.0f:300.0f,original?1.0f:0.0f,FLICK_BACKWARDS_ANGLE)))++hit;}
    if(original)actor->mDamageCount=0.0f;return hit;
}
void setPhase(KabutoFsm& s){const float d=seconds(s,s.clip);float ph=s.stateTime/d;if(ph>1.0f)ph=1.0f;s.phase=ph;}
void transition(BTeki* a,KabutoFsm& s,KState st,const char* clip,unsigned gen){
    s.state=st;s.stateTime=0.0f;s.fireDone=false;s.flickDone=false;if(clip)s.clip=clip;
    if(s.source==96){
     if(st==KB_FIXSTAY){a->clearTekiOption(TEKIOPT_Atari|TEKIOPT_ShapeVisible|TEKIOPT_LifeGaugeVisible);a->setTekiOption(TEKIOPT_Invincible);}
     else {a->setTekiOption(TEKIOPT_Atari|TEKIOPT_ShapeVisible|TEKIOPT_LifeGaugeVisible);if(st==KB_FIXHIDE)a->setTekiOption(TEKIOPT_Invincible);else a->clearTekiOption(TEKIOPT_Invincible);}
     if(st==KB_FIXAPPEAR){a->mStoredDamage=0.0f;a->mHealth=std::min(a->mHealth+1.0f,a->mMaxHealth);doFlick(a,false,true);}
     s.next=st;
    }
    // Per-state init (KabutoState.cpp): StateWait::init resets its timer and
    // latch and draws a new wander target (:76-82); StateMove::init resets its
    // timer (:192); StateAttack::init clears the alert timer (:334).
    if(st==KB_WAIT){s.waitTimer=0.0f;s.waitNextTurn=false;
        const float u0=rngUnit(s),u1=rngUnit(s);
        s.wander=p2kabutoaim::wanderTarget(aimVec(a->getPosition()),aimVec(s.home),u0,u1);}
    if(st==KB_MOVE)s.moveTimer=0.0f;
    if(st==KB_ATTACK)s.alert=0.0f;
    std::printf("P2_KABUTO_STATE generator=%u state=%s\n",gen,stateName(st));std::fflush(stdout);
    // P1 Cannon Beetle bank approximation (output-only, #946).
    if(st==KB_DEAD)pc_p2_sfx(s.source,gen,p2sfx::Event::Dead,a);
    if(st==KB_FLICK)pc_p2_sfx(s.source,gen,p2sfx::Event::Flick,a);
}
void die(BTeki* a,KabutoFsm& s,unsigned gen,float prior){
    if(!s.deadLogged){s.deadLogged=true;std::printf("P2_KABUTO_DEAD generator=%u source_id=%u health=0 prior_health=%.1f\n",gen,s.source,prior);std::fflush(stdout);}
    if(s.original&&!pc_p2_original_spawn_items(a)){std::fputs("original cannon death lost registry ownership\n",stderr);std::abort();}
    transition(a,s,KB_DEAD,s.source==96?"K_dead":"dead",gen);
}
}
void pc_p2_kabuto_fsm_reset(){
 for(const auto& f:fsms)if(f.second.original){std::fputs("P2_ORIGINAL_CANNON reset requires physical actor retirement\n",stderr);std::abort();}
 originalSockets.reset();poseBank.reset();poseVis.clear();originalStoneResource.bank.reset();originalStoneResource.shapes.clear();originalStoneResource.clocks.clear();for(auto& r:originalResources){r.bank.reset();r.shapes.clear();r.clocks.clear();}
    if(fleet.active()>0){std::printf("P2_KABUTO_STONE_RESET active=%d\n",fleet.active());std::fflush(stdout);}
    fleet.reset();stoneDebt=0.0;stoneMap.proxy.clear();stoneDrawLogged=false;shooters.clear();
    for(int i=0;i<p2kabutostone::kFleetCapacity;++i){slotOriginal[i]=false;slotGen[i]=0;slotPosTicks[i]=0;slotRoll[i]=0.0f;slotDustTicks[i]=0;}
    actors.clear();fsms.clear();drawn.clear();drawnCorpse.clear();animated.clear();timing.clear();ready=false;}
void pc_p2_kabuto_fsm_forget(BTeki* a){poseVis.forget(a);auto* v=static_cast<PelletView*>(a);
    // The shooter is gone; its stones keep flying and Press is no longer
    // attributed to it (no dangling actor pointer is kept).
    const std::uint64_t tok=tokenOf(a);const int orphaned=fleet.forgetOwner(tok);shooters.erase(tok);
    if(orphaned>0){auto f=fsms.find(v);std::printf("P2_KABUTO_STONE_ORPHAN generator=%u stones=%d\n",f!=fsms.end()?f->second.token:0u,orphaned);std::fflush(stdout);}
    auto f=fsms.find(v);if(f==fsms.end()||!f->second.original)pc_randomizer_p2_forget_source(v);actors.erase(v);fsms.erase(v);drawn.erase(v);drawnCorpse.erase(v);pc_p2_original_cannon_forget(a);}
bool pc_p2_kabuto_original_resources(unsigned source,std::string& error){
 if(source!=95&&source!=96){error="invalid original cannon source";return false;}
 std::ifstream in("p2-original-cannon-bank.txt");p2original::cannon::Banks banks;
 if(!p2original::cannon::parseBank(in,banks,error))return false;
 if(!originalSockets){std::ifstream socketFile("p2-original-cannon-attach.txt");auto staged=p2attach::read(socketFile);
  if(!staged||staged->joint("mouth")<0){error="original cannon literal mouth socket unavailable";return false;}
  for(const char* name:{"attack","K_attack"}){const int index=staged->clip(name);if(index<0||staged->clips[index].duration!=95){error="original cannon authored socket clip missing";return false;}
   const int fire=std::string(name)=="attack"?51:56;const auto& frames=staged->clips[index].frames;
   if(std::find(frames.begin(),frames.end(),fire)==frames.end()){error="original cannon exact firing-pose socket missing";return false;}}
  originalSockets=std::move(staged);
 }
 auto& resident=originalResources[source-95];const auto& clips=banks[source-95];
 if(!resident.clocks.empty()){
  if(resident.clocks.size()!=clips.size()){error="resident cannon inventory changed";return false;}
  for(const auto& c:clips){auto f=resident.clocks.find(c.name);if(f==resident.clocks.end()||f->second.frames!=c.frames||f->second.duration!=c.duration||f->second.count!=c.count){error="resident cannon bank changed";return false;}}
 }else{
  OriginalResources staged;p2poseload::Shared shared;size_t total=0;
  for(const auto& c:clips){
   if(!p2posefamily::loadFamilyClip(staged.bank,c.name,std::string("cannon_")+(source==95?"Rkabuto":"Fkabuto")+"_"+c.name,c.count,c.duration,c.frames,shared,total,staged.shapes[c.name],error))return false;
   auto* physical=staged.bank.clip(c.name);if(!physical||physical->poses.size()!=size_t(c.count)){error="original cannon physical vectors missing";return false;}staged.clocks[c.name]=c;
  }
  resident=std::move(staged);
 }
 const std::string bodyKey=source==95?"original_cannon|Rkabuto":"original_cannon|Fkabuto";pc_p2_body_coll_manage(bodyKey,true);
 const auto* body=resident.bank.clip("wait");if(!body||body->poses.empty()||!pc_p2_body_coll_register_pose(bodyKey,body->poses.front())){error="original cannon visible body collision unavailable";return false;}
 if(!resident.bank.ready()||resident.bank.clipCount()!=14){error="original cannon physical bank unavailable";return false;}
 std::ifstream stoneFile("p2-original-stone-bank.txt");std::vector<p2animation::Clip> stones;if(!p2original::cannon::parseStoneBank(stoneFile,stones,error))return false;
 if(originalStoneResource.clocks.empty()){
  OriginalResources staged;p2poseload::Shared shared;size_t total=0;
  for(const auto& c:stones){if(!p2posefamily::loadFamilyClip(staged.bank,c.name,"cannon_Stone_"+c.name,c.count,c.duration,c.frames,shared,total,staged.shapes[c.name],error))return false;
   const auto* physical=staged.bank.clip(c.name);if(!physical||physical->poses.size()!=size_t(c.count)){error="original Stone physical vectors missing";return false;}staged.clocks[c.name]=c;}
  originalStoneResource=std::move(staged);
 }else for(const auto& c:stones){auto f=originalStoneResource.clocks.find(c.name);if(f==originalStoneResource.clocks.end()||f->second.frames!=c.frames||f->second.duration!=c.duration||f->second.count!=c.count){error="resident original Stone bank changed";return false;}}
 error.clear();return true;
}
bool pc_p2_kabuto_original_birth(BTeki* actor,unsigned source,unsigned uid,unsigned ordinal,std::string& error){
 if(!actor||(source!=95&&source!=96)||!uid||actor->mTekiType!=TEKI_Beatle||actors.count(static_cast<PelletView*>(actor))){error="invalid or reused original cannon actor";return false;}
 auto& resource=originalResources[source-95];if(!resource.bank.ready()){error="original cannon resources not admitted";return false;}
 auto* view=static_cast<PelletView*>(actor);auto inserted=fsms.try_emplace(view);if(!inserted.second){error="original cannon FSM address owned";return false;}
 auto& f=inserted.first->second;f.socketToken=f.sockets.bind(originalSockets);if(!f.socketToken){error="original cannon socket instance failed";return false;}f.original=true;f.source=source;f.home=actor->getPosition();f.heading=actor->getDirection();f.token=uid;f.rng=((uid^ordinal)*2654435761u)|1u;
 f.lastHealth=source==96?2000.0f:850.0f;actor->mHealth=actor->mMaxHealth=f.lastHealth;actor->mDamageCount=0.0f;actor->setTekiOption(TEKIOPT_DamageCountable);actors[view]=true;shooters[tokenOf(actor)]=actor;
 if(source==96){f.state=KB_FIXSTAY;f.clip="K_appear";actor->clearTekiOption(TEKIOPT_Atari|TEKIOPT_LifeGaugeVisible|TEKIOPT_ShapeVisible);actor->setTekiOption(TEKIOPT_Invincible);}
 else {const float u0=rngUnit(f),u1=rngUnit(f);f.wander=p2kabutoaim::wanderTarget(aimVec(f.home),aimVec(f.home),u0,u1);}
 if(!poseVis.draw(actor,resource.bank,f.clip,0,uid)){error="original cannon private geometry allocation failed";return false;}
 std::printf("P2_ORIGINAL_CANNON_BIRTH source=%u uid=%u ordinal=%u state=%s health=%.1f x=%.3f y=%.3f z=%.3f\n",source,uid,ordinal,stateName(f.state),actor->mHealth,f.home.x,f.home.y,f.home.z);
 pc_p2_body_coll_assign(actor,source==95?"original_cannon|Rkabuto":"original_cannon|Fkabuto");
 ready=true;error.clear();return true;
}
bool pc_p2_kabuto_original_registry(BTeki* actor,unsigned token,std::string& error){auto f=fsms.find(static_cast<PelletView*>(actor));if(f==fsms.end()||!f->second.original||!token||pc_p2_original_actor_token(actor)!=token){error="original cannon registry mismatch";return false;}f->second.token=token;error.clear();return true;}
float pc_p2_kabuto_fsm_param_f(const BTeki* a,int idx,float fb){
    auto i=actors.find(static_cast<PelletView*>(const_cast<BTeki*>(a)));if(i==actors.end())return fb;
    const auto& p=p2kabutofsm::params();
    auto f=fsms.find(static_cast<PelletView*>(const_cast<BTeki*>(a)));if(f!=fsms.end()&&f->second.original){if(idx==TPF_Life)return f->second.source==96?2000.0f:850.0f;if(idx==TPF_LifeRecoverRate)return .0001f;if(idx==TPF_Scale)return 1.0f;if(idx==TPF_CollisionRadius)return 45.0f;}
    switch(idx){case TPF_Life:return p.health;case TPF_VisibleRange:return p.sight;
    case TPF_AttackableRange:return p.attackRange;case TPF_AttackPower:return p.attackDamage;default:return fb;}
}
bool pc_p2_kabuto_original_actor(const BTeki* actor){auto f=fsms.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));return f!=fsms.end()&&f->second.original;}
bool pc_p2_kabuto_fsm_suppress_ai(const BTeki* a){return ready&&actors.count(static_cast<PelletView*>(const_cast<BTeki*>(a)))!=0;}
void pc_p2_kabuto_fsm_setup(){
    if(pc_p2_original_cannon_admitted())return;
    pc_p2_kabuto_fsm_reset();
    std::printf("P2_KABUTO_SETUP\n");std::fflush(stdout);
    const bool bridge=pc_randomizer_p2_bridge()&&!pc_pikipelago_room_preview();
    const bool preview=pc_pikipelago_room_preview();
    if(!bridge&&!preview)return;
    std::ifstream input("p2-kabuto.txt");if(!input)return;
    std::map<unsigned,std::string> wanted;std::vector<p2animation::Clip> bank;
    if(!p2kabutofsm::parse(input,wanted,bank))std::abort();
    for(const auto& c:bank)if(c.name=="attack"&&!p2kabutostone::clipHasKey2(c.duration)){
        std::printf("P2_KABUTO_ERROR key2_outside_attack duration=%d key2_frame=%d\n",c.duration,p2kabutostone::kAttackKey2Frame);std::fflush(stdout);std::abort();}
    if(bridge){wanted.clear();for(unsigned id:pc_p2_campaign_ids(75))wanted[id]="Kabuto";}
    if(wanted.empty())return;
    std::set<unsigned> seen;
    Iterator it(tekiMgr);CI_LOOP(it){Teki* teki=static_cast<Teki*>(*it);if(!teki||!teki->mGenerator)continue;
        const unsigned token=bridge?pc_p2_campaign_token(teki):teki->mGenerator->_70;
        if(wanted.find(token)==wanted.end())continue;
        if(teki->mTekiType!=TEKI_Beatle){ // #948: wrong vehicle: refuse with a reason, never abort a campaign
            if(!bridge)std::abort();
            std::printf("P2_KABUTO_UNBOUND generator=%u source_id=75 type=%d reason=host_type_mismatch\n",token,int(teki->mTekiType));std::fflush(stdout);continue;}
        if(!seen.insert(token).second){
            if(!bridge)std::abort();
            std::printf("P2_KABUTO_UNBOUND generator=%u source_id=75 reason=duplicate_generator\n",token);std::fflush(stdout);continue;}
        actors[static_cast<PelletView*>(teki)]=true;shooters[tokenOf(teki)]=teki;
        teki->mHealth=p2kabutofsm::params().health;
        KabutoFsm& f=fsms[static_cast<PelletView*>(teki)];
        f.home=teki->getPosition();f.heading=teki->getDirection();f.targetPos=f.home;f.targetValid=true;
        f.rng=(token*2654435761u)|1u;f.token=token;f.state=KB_WAIT;f.clip="wait";f.phase=0.0f;f.lastHealth=teki->mHealth;
        {const float u0=rngUnit(f),u1=rngUnit(f);f.wander=p2kabutoaim::wanderTarget(aimVec(f.home),aimVec(f.home),u0,u1);}
        if(bridge){pc_randomizer_p2_bind_source(static_cast<PelletView*>(teki),75,token);std::printf("P2_KABUTO_DELIVERY_BIND generator=%u source_id=75\n",token);}
        std::printf("P2_KABUTO_BIND generator=%u source_id=75 visual_only=0\n",token);
        std::printf("P2_KABUTO_READY species=Kabuto generator=%u health=%.1f max_health=%.1f behavior=source_fsm rewards=P1_unchanged\n",token,teki->mHealth,teki->getParameterF(TPF_Life));
        std::printf("P2_ENEMY_READY species=Kabuto native_family=Kabuto generator=%u x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native source_FSM=implemented\n",token,teki->getPosition().x,teki->getPosition().y,teki->getPosition().z,teki->mHealth,p2kabutofsm::params().health);
        std::printf("P2_KABUTO_STATE generator=%u state=wait\n",token);std::fflush(stdout);
    }
    if(seen.size()!=wanted.size()){std::printf("P2_KABUTO_MISSING wanted=%zu found=%zu\n",wanted.size(),seen.size());std::fflush(stdout);if(!bridge)std::abort();}
    loadAnimation(bank);ready=true;
}
void pc_p2_kabuto_fsm_update(BTeki* actor){
    if(!ready)return;
    auto it=actors.find(static_cast<PelletView*>(actor));if(it==actors.end())return;
    auto ft=fsms.find(static_cast<PelletView*>(actor));if(ft==fsms.end())return;
    KabutoFsm& s=ft->second;
    const float dt=gsys->getFrameTime();if(dt<=0.0f||dt>0.5f)return;
    const Vector3f pos=actor->getPosition();
    const unsigned live=s.original?pc_p2_original_actor_token(actor):(actor->mGenerator?pc_p2_campaign_token(actor):0u);
    if(live)s.token=live;
    const unsigned gen=s.token?s.token:live;
    if(actor->mStoredDamage>0.0f)actor->makeDamaged();
    const float previousHealth=s.lastHealth;
    if(actor->mHealth<=0.0f&&!s.deathPriorSet&&previousHealth>0.0f){s.deathPrior=previousHealth;s.deathPriorSet=true;}
    const float priorForDeath=s.deathPriorSet?s.deathPrior:previousHealth;
    if(actor->mHealth<s.lastHealth&&actor->mHealth>0.0f){
        pc_p2_sfx(s.source,gen,p2sfx::Event::Damage,actor);
        std::printf("P2_KABUTO_DAMAGE generator=%u source_id=%u health=%.1f\n",gen,s.source,actor->mHealth);std::fflush(stdout);}
    s.lastHealth=actor->mHealth;
    if(s.poolFullCooldown>0.0f)s.poolFullCooldown-=dt;
    // updateCaution (Kabuto.cpp:296-305): damage or stuck Pikmin re-arm the
    // alert (EB_Colliding has no P1 host flag); the alert timer runs to fp29.
    if(actor->mHealth<previousHealth||stuckPikminCount(actor)!=0)s.alert=0.0f;
    if(s.alert<p2kabutoaim::params().alertDuration)s.alert+=dt;
    const float prevStateTime=p2kabutostone::advanceStateTime(s.stateTime,dt);
    static AimSnapshot aim;
    const p2kabutoaim::Vec3 apos=aimVec(pos);
    // getSearchedTarget (Kabuto.cpp:212-220): nearest Navi / Pikmin within
    // sight and the alert-dependent view angle; finding one clears the alert.
    auto searched=[&]()->bool{buildAim(aim);
        const int t=p2kabutoaim::searchTarget(apos,s.heading,p2kabutoaim::viewAngleDeg(s.alert),aim.cands.data(),int(aim.cands.size()));
        if(t>=0){s.alert=0.0f;s.targetPos=aim.creatures[size_t(t)]->getPosition();s.targetValid=true;}
        return t>=0;};
    switch(s.state){
    case KB_FIXSTAY:{stop(actor);s.stateTime=0.0f;if(searched()){face(actor,s,std::atan2(s.targetPos.x-pos.x,s.targetPos.z-pos.z));transition(actor,s,KB_FIXAPPEAR,"K_appear",gen);}break;}
    case KB_FIXHIDE:{stop(actor);doFlick(actor,true,true);if(s.stateTime>=seconds(s,"K_hide"))transition(actor,s,KB_FIXSTAY,"K_appear",gen);break;}
    case KB_FIXAPPEAR:case KB_FIXWAIT:case KB_FIXTURN:case KB_FIXATTACK:case KB_FIXFLICK:{
     stop(actor);
     const KState state=s.state;
     if(state!=KB_FIXAPPEAR&&state!=KB_FIXFLICK&&actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
     const bool has=searched();buildAim(aim);
     const bool lane=p2kabutoaim::attackableIndex(apos,s.heading,aim.cands.data(),int(aim.cands.size()))>=0;
     const float angle=has?wrapPi(std::atan2(s.targetPos.x-pos.x,s.targetPos.z-pos.z)-s.heading):0.0f;
     auto select=[&](){if(actor->mHealth<=0.0f)return KB_DEAD;if(shouldFlick(actor))return KB_FIXFLICK;if(lane)return KB_FIXATTACK;if(!has)return KB_FIXHIDE;return std::fabs(angle)<=0.0f?KB_FIXWAIT:KB_FIXTURN;};
     if(state==KB_FIXTURN&&has){const float step=std::max(-7.5f*PI_F/180.0f,std::min(7.5f*PI_F/180.0f,angle*.075f));face(actor,s,s.heading+step);}
     if(state==KB_FIXWAIT||state==KB_FIXTURN){if(shouldFlick(actor))s.next=KB_FIXFLICK;else if(lane)s.next=KB_FIXATTACK;else if(!has)s.next=KB_FIXHIDE;else if(state==KB_FIXWAIT&&std::fabs(angle)>0.0f)s.next=KB_FIXTURN;else if(state==KB_FIXTURN&&std::fabs(angle)<=0.0f)s.next=KB_FIXWAIT;}
     if(state==KB_FIXATTACK&&!s.fireDone&&prevStateTime<(56.0f/30.0f-1e-4f)&&s.stateTime>=(56.0f/30.0f-1e-4f)){
      s.fireDone=true;p2attach::Affine world;const float cs=std::cos(s.heading),sn=std::sin(s.heading);
      world.m[0][0]=cs;world.m[0][2]=sn;world.m[2][0]=-sn;world.m[2][2]=cs;world.m[0][3]=pos.x;world.m[1][3]=pos.y;world.m[2][3]=pos.z;
      p2attach::Affine mouth;if(!s.sockets.sample(s.socketToken,originalSockets->clip("K_attack"),56.0f,world,++s.socketTick)||!s.sockets.socket(s.socketToken,originalSockets->joint("mouth"),mouth)){std::fputs("fixed cannon mouth sampling failed\n",stderr);std::abort();}
      p2kabutostone::AttackStep step;step.birth={mouth.m[0][3],pos.y+25.0f,mouth.m[2][3]};step.slot=fleet.fire(tokenOf(actor),step.birth,s.heading,step.id,false,71.0f/30.0f);step.action=step.slot>=0?p2kabutostone::AttackAction::Fired:p2kabutostone::AttackAction::PoolFull;logStoneFire(s,gen,step);
     }
     if(state==KB_FIXFLICK&&!s.flickDone&&s.stateTime>=(31.0f/30.0f-1e-4f)){s.flickDone=true;doFlick(actor);if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}}
     if(s.stateTime>=seconds(s,s.clip)){
      KState next=(state==KB_FIXWAIT||state==KB_FIXTURN)?s.next:select();
      if(state==KB_FIXFLICK)next=actor->mHealth<=0.0f?KB_DEAD:KB_FIXATTACK;
      if(next==KB_DEAD)die(actor,s,gen,priorForDeath);
      else transition(actor,s,next,next==KB_FIXFLICK?"K_flick":next==KB_FIXATTACK?"K_attack":next==KB_FIXWAIT?"K_wait":next==KB_FIXTURN?"K_pivot":"K_hide",gen);
     }
     break;}
    case KB_WAIT:{
        // StateWait::exec (KabutoState.cpp:89-110): a searched target or
        // > 3 s latches Turn; the transit happens when the wait clip ends.
        // Wait never attacks directly (source enters Attack only from Turn,
        // Move and Flick).
        stop(actor);
        if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
        if(shouldFlick(actor)){transition(actor,s,KB_FLICK,"flick",gen);break;}
        if(p2kabutoaim::waitWantsTurn(s.waitTimer,searched()))s.waitNextTurn=true;
        s.waitTimer+=dt;
        if(s.stateTime>=seconds(s,s.clip)){
            s.stateTime=0.0f;
            if(s.waitNextTurn)transition(actor,s,KB_TURN,s.original?"pivot":"wait",gen);
        }
        break;}
    case KB_TURN:{
        // StateTurn::exec (KabutoState.cpp:139-174) via p2kabutoaim::turnExec:
        // turn toward the searched target at the retail rate and attack only
        // once isAttackableTarget holds; there is no facing-close-enough exit,
        // so an off-axis target keeps it turning until the lane holds. With
        // no target it turns to the wander point and moves within 30 deg.
        stop(actor);
        if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
        if(shouldFlick(actor)){transition(actor,s,KB_FLICK,"flick",gen);break;}
        buildAim(aim);
        const p2kabutoaim::TurnResult r=p2kabutoaim::turnExec(apos,s.heading,dt,p2kabutoaim::viewAngleDeg(s.alert),aim.cands.data(),int(aim.cands.size()),s.wander);
        if(r.target>=0){s.alert=0.0f;s.targetPos=aim.creatures[size_t(r.target)]->getPosition();s.targetValid=true;}
        face(actor,s,r.faceDir);
        if(r.next==p2kabutoaim::Next::Attack){logLane(gen,"turn",s,pos,aim);transition(actor,s,KB_ATTACK,"attack",gen);}
        else if(r.next==p2kabutoaim::Next::Move)transition(actor,s,KB_MOVE,"move",gen);
        break;}
    case KB_MOVE:{
        // StateMove::exec (KabutoState.cpp:203-260) via p2kabutoaim::moveExec.
        pc_p2_sfx_stride(s.source,gen,actor,24.0f);
        if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
        if(shouldFlick(actor)){stop(actor);transition(actor,s,KB_FLICK,"flick",gen);break;}
        buildAim(aim);
        const p2kabutoaim::MoveResult r=p2kabutoaim::moveExec(apos,s.heading,dt,p2kabutoaim::viewAngleDeg(s.alert),s.moveTimer,aim.cands.data(),int(aim.cands.size()),s.wander);
        if(r.target>=0){s.alert=0.0f;s.targetPos=aim.creatures[size_t(r.target)]->getPosition();s.targetValid=true;}
        face(actor,s,r.faceDir);
        s.moveTimer+=dt;
        if(r.next==p2kabutoaim::Next::Attack){stop(actor);logLane(gen,"move",s,pos,aim);transition(actor,s,KB_ATTACK,"attack",gen);}
        else if(r.next==p2kabutoaim::Next::Turn){stop(actor);transition(actor,s,KB_TURN,s.original?"pivot":"wait",gen);}
        else if(r.next==p2kabutoaim::Next::Wait){stop(actor);transition(actor,s,KB_WAIT,"wait",gen);}
        else if(r.walk)driveForward(actor,s,p2kabutoaim::params().moveSpeed);
        else stop(actor);
        break;}
    case KB_ATTACK:{
        stop(actor);
        // StateAttack::exec (KabutoState.cpp:350-358) via the tested seam:
        // health gate first, so a Kabuto killed before the event never fires;
        // then KEYEVENT_2 (retail attack event frame 50, seen after 51 frames
        // at 30 fps) births the Stone at the mouth exactly once.
        const Vector3f ap=actor->getPosition();
        p2kabutostone::AttackStep step;
        if(s.original){
         if(actor->mHealth<=0.0f)step.action=p2kabutostone::AttackAction::Die;
         else if(!s.fireDone&&p2kabutostone::key2Crossed(prevStateTime,s.stateTime)){
          s.fireDone=true;p2attach::Affine world;const float cs=std::cos(s.heading),sn=std::sin(s.heading);
          world.m[0][0]=cs;world.m[0][2]=sn;world.m[2][0]=-sn;world.m[2][2]=cs;world.m[0][3]=ap.x;world.m[1][3]=ap.y;world.m[2][3]=ap.z;
          p2attach::Affine mouth;if(!s.sockets.sample(s.socketToken,originalSockets->clip("attack"),51.0f,world,++s.socketTick)||!s.sockets.socket(s.socketToken,originalSockets->joint("mouth"),mouth)){std::fputs("original cannon mouth sampling failed\n",stderr);std::abort();}
          step.birth={mouth.m[0][3],ap.y+25.0f,mouth.m[2][3]};step.slot=fleet.fire(tokenOf(actor),step.birth,s.heading,step.id,s.source==95,71.0f/30.0f);
          step.action=step.slot>=0?p2kabutostone::AttackAction::Fired:p2kabutostone::AttackAction::PoolFull;
         }
        }else step=p2kabutostone::attackStep(fleet,tokenOf(actor),actor->mHealth,s.fireDone,prevStateTime,s.stateTime,{ap.x,ap.y,ap.z},s.heading);
        if(step.action==p2kabutostone::AttackAction::Die){die(actor,s,gen,priorForDeath);break;}
        logStoneFire(s,gen,step);
        if(s.stateTime>=seconds(s,"attack")){
            // KEYEVENT_END (KabutoState.cpp:360-372): Flick, else Turn when a
            // target is searched, else Wait.
            if(shouldFlick(actor))transition(actor,s,KB_FLICK,"flick",gen);
            else if(searched())transition(actor,s,KB_TURN,s.original?"pivot":"wait",gen);
            else transition(actor,s,KB_WAIT,"wait",gen);
        }
        break;}
    case KB_FLICK:{
        stop(actor);
        const auto key=s.original?p2original::cannon::flickKey(s.flickDone,s.stateTime,actor->mHealth):p2original::cannon::FlickKey::None;
        if((!s.original&&!s.flickDone)||key!=p2original::cannon::FlickKey::None){s.flickDone=true;int hit=doFlick(actor);std::printf("P2_KABUTO_FLICK generator=%u source_id=%u hit=%d\n",gen,s.source,hit);std::fflush(stdout);
         if(key==p2original::cannon::FlickKey::FlickDead){die(actor,s,gen,priorForDeath);break;}}
        if(s.stateTime>=seconds(s,"flick")){
            // KEYEVENT_END (KabutoState.cpp:306-311): Dead, else Attack.
            if(actor->mHealth<=0.0f){die(actor,s,gen,priorForDeath);break;}
            buildAim(aim);logLane(gen,"flick",s,pos,aim);
            transition(actor,s,KB_ATTACK,"attack",gen);
        }
        break;}
    case KB_DEAD:{
        stop(actor);
        if(!s.escaped&&s.stateTime>=seconds(s,s.clip)){s.escaped=true;actor->pcEscapeNow();}
        // KB_DEAD has no mDeadState assignment; silence unused-enum warning.
        break;}
    default:break;
    }
    setPhase(s);
    s.logTimer+=dt;
    if(s.logTimer>=1.0f){s.logTimer=0.0f;const Vector3f now=actor->getPosition();
        std::printf("P2_KABUTO_FSM_POS species=Kabuto generator=%u state=%s x=%.2f y=%.2f z=%.2f health=%.1f\n",
            gen,stateName(s.state),now.x,now.y,now.z,actor->mHealth);std::fflush(stdout);}
}
bool pc_p2_kabuto_fsm_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    auto it=actors.find(static_cast<PelletView*>(actor));if(it==actors.end())return false;
    {
        auto* v=static_cast<PelletView*>(actor);
        auto ftok=fsms.find(v);
        const unsigned liveTok=(ftok!=fsms.end()&&ftok->second.original)?pc_p2_original_actor_token(actor):(actor->mGenerator?pc_p2_campaign_token(actor):0u);
        const unsigned token=liveTok?liveTok:(ftok!=fsms.end()?ftok->second.token:0u);
        if(drawn.insert(v).second&&!corpse){std::printf("P2_KABUTO_DRAW generator=%u source_id=%u corpse=%d\n",token,ftok!=fsms.end()?ftok->second.source:75u,int(corpse));std::fflush(stdout);}
        if(corpse&&drawnCorpse.insert(v).second){std::printf("P2_KABUTO_CORPSE_DRAW generator=%u source_id=%u\n",token,ftok!=fsms.end()?ftok->second.source:75u);std::fflush(stdout);}
    }
    auto ft=fsms.find(static_cast<PelletView*>(actor));
    if(ft!=fsms.end()&&ft->second.original){const auto& s=ft->second;
     if(!corpse&&s.state==KB_FIXSTAY)return true;
     const auto& r=originalResources[s.source-95];const std::string name=corpse?"carry":s.clip;
     auto c=r.clocks.find(name);if(c==r.clocks.end())return false;
     const float frame=corpse?0.0f:std::min(float(c->second.duration-1),s.stateTime*30.0f);
     Shape* shape=poseVis.draw(actor,r.bank,name,frame,s.token);if(!shape)return false;
     shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
    }
    const char* name=corpse?"dead":(ft!=fsms.end()?ft->second.clip.c_str():p2kabutofsm::motionClip(actor->mTekiAnimator->getCurrentMotionIndex()));
    Shape* shape=animated.at("wait").front();
    if(name){float phase=corpse?1.0f:(ft!=fsms.end()?ft->second.phase:0.0f);shape=animated.at(name).at(timing.at(name).index(phase,corpse));
        // #895: lerp + crossfade into a private Shape; nearest pose stays the fallback.
        const p2animation::Clip& clipTiming=timing.at(name);
        const float sourceFrame=corpse?float(clipTiming.duration-1):std::max(0.f,std::min(1.f,phase))*float(clipTiming.duration-1);
        if(Shape* smooth=poseVis.draw(actor,poseBank,name,sourceFrame,actor->mGenerator?pc_p2_campaign_token(actor):0u))shape=smooth;}
    shape->updateAnim(gfx,matrix,nullptr,actor);
    pc_gfx_specular_family_scope(1);
    shape->drawshape(gfx,*gfx.mCamera,nullptr);
    pc_gfx_specular_family_scope(0);
    return true;
}
namespace {
// Host map trace for the Stone in the P2 base-point convention (mPosition is
// the sphere bottom; P1 traceMove adds/subtracts the radius itself).
// Dynamic collision: P2 runs the Stone through platMgr->traceMove too
// (enemyBase.cpp:2137-2139; EB_PlatformCollEnabled is on by default,
// enemyBase.cpp:1080, and Rock::onInit never clears it, Rock.cpp:47-94), so
// bridges/gates/map platforms stop it. P2 platforms are item-only
// (PlatAttacher users: itemBridge.cpp, itemMgr.cpp, gamePlatMgr.cpp,
// collinfo.cpp), so P1 enemy/boss body platforms (CreatureCollPart from
// CreaturePlatMgr::init, tekibteki.cpp:401-402), including the shooter's own,
// are skipped with MoveTrace::mIgnoreEnemyCollParts. The tracing creature is
// the unregistered TraceProxy, which owns no parts.
bool stoneTrace(void* ctx,const P2CannonStoneVec3& base,const P2CannonStoneVec3& vel,float dt,float radius,P2CannonStoneTraceResult& out){
    StoneMap& m=*static_cast<StoneMap*>(ctx);
    if(!mapMgr||!mapMgr->mMapModel)return false;
    if(!std::isfinite(base.x)||!std::isfinite(base.y)||!std::isfinite(base.z)||!std::isfinite(vel.x)||!std::isfinite(vel.y)||!std::isfinite(vel.z))return false;
    m.proxy.clear();
    MoveTrace mv(Vector3f(base.x,base.y,base.z),Vector3f(vel.x,vel.y,vel.z),radius,false);
    mv.mIgnoreEnemyCollParts=true;
    // P2 wall classification for Rock::wallCallback (Rock.cpp:244-249):
    // |contact normal y| <= sin 45 deg below the 0.6 floor threshold
    // (MoveInfo.h:38-39, mapMgrTraceMove.cpp:148-157), not P1's |n.y| < 0.5.
    mv.mP2WallThreshold=true;
    mapMgr->traceMove(&m.proxy,mv,dt);
    ++m.calls;
    out.position={mv.mPosition.x,mv.mPosition.y,mv.mPosition.z};
    out.velocity={mv.mVelocity.x,mv.mVelocity.y,mv.mVelocity.z};
    out.wall=m.proxy.wall;m.walls+=out.wall?1u:0u;
    return std::isfinite(out.position.x)&&std::isfinite(out.position.y)&&std::isfinite(out.position.z)
        &&std::isfinite(out.velocity.x)&&std::isfinite(out.velocity.y)&&std::isfinite(out.velocity.z);
}
struct StoneSnapshot{std::vector<p2kabutostone::Target> targets;std::vector<Creature*> creatures;std::vector<char> kinds;};
void snapshotAdd(StoneSnapshot& snap,Creature* c,P2CannonStoneContactKind kind,char code){
    if(!c||!c->isAlive()||!c->isAtari()||c->isBuried())return;
    const Vector3f centre=c->getCentre();
    p2kabutostone::Target t;t.token=tokenOf(c);t.centre={centre.x,centre.y,centre.z};t.radius=c->getCentreSize();
    t.kind=kind;t.onFloor=c->mGroundTriangle!=nullptr;t.alive=true;
    const auto p=c->getPosition();t.position={p.x,p.y,p.z};t.homingSearchable=c->mObjType==OBJTYPE_Navi||(c->isPiki()&&pikminPhase(static_cast<Piki*>(c))==p2kabutoaim::PikminPhase::Active);
    snap.targets.push_back(t);snap.creatures.push_back(c);snap.kinds.push_back(code);
}
// Host target snapshot: every Navi (co-op), live Pikmin, live Teki including
// the shooter (its contact is suppressed only by the 1 s source grace).
// getCentre/getCentreSize and mGroundTriangle stand in for the P2 CollTree
// and mFloorTriangle (Rock.cpp:212).
void buildSnapshot(StoneSnapshot& snap){
    snap.targets.clear();snap.creatures.clear();snap.kinds.clear();
    if(naviMgr){Iterator it(naviMgr);CI_LOOP(it){snapshotAdd(snap,static_cast<Navi*>(*it),P2CannonStoneContactKind::NaviPiki,'n');}}
    if(pikiMgr){Iterator it(pikiMgr);CI_LOOP(it){snapshotAdd(snap,static_cast<Piki*>(*it),P2CannonStoneContactKind::NaviPiki,'p');}}
    if(tekiMgr){Iterator it(tekiMgr);CI_LOOP(it){snapshotAdd(snap,static_cast<Teki*>(*it),P2CannonStoneContactKind::Teki,'t');}}
}
const char* targetName(char code){return code=='n'?"navi":code=='p'?"piki":code=='t'?"teki":code=='l'?"pellet":"boss";}
// Source Rock collisionCallback zeroes the Stone's health on any creature
// contact that is not a Navi/Piki (Rock.cpp:207-233), so pellets and other
// non-Teki creatures stop it. Pellets and P1 bosses are offered as Other:
// they stop the Stone and take no strike (a P1 boss has no P2 counterpart
// receiver here; see design-kabuto.md Round 4 for items).
void snapshotOthers(StoneSnapshot& snap){
    if(pelletMgr){Iterator it(pelletMgr);CI_LOOP(it){snapshotAdd(snap,static_cast<Pellet*>(*it),P2CannonStoneContactKind::Other,'l');}}
    if(bossMgr){Iterator it(bossMgr);CI_LOOP(it){snapshotAdd(snap,static_cast<Boss*>(*it),P2CannonStoneContactKind::Other,'b');}}
}
// A bound Kabuto actor is hosted on the P1 Beatle, whose strategy accepts
// InteractAttack only through a damage portion 0 collision part
// (TAIbeatle.cpp:1100-1113; a null part is portion -1,
// interactBattle.cpp:399-444), so a Stone's partless InteractAttack would do
// nothing. Source Kabuto takes the Stone's 250 through EnemyBase (no Kabuto
// damage override, Kabuto.h). Apply it as the P1 Attack receiver does
// (tekibteki.cpp:1990-2006: stored damage + last assailant), which the
// Kabuto FSM drains through makeDamaged on its next update.
// Returns false when `target` is not a bound Kabuto actor (the caller then
// uses the ordinary engine receiver); `hit` reports the outcome otherwise.
bool kabutoHostStoneAttack(Creature* target,float damage,P2ProjectileEngineHit& hit){
    Teki* t=static_cast<Teki*>(target);
    if(actors.find(static_cast<PelletView*>(t))==actors.end())return false;
    hit=P2ProjectileEngineHit();hit.attempted=true;hit.healthBefore=t->mHealth;hit.storedDamageBefore=t->mStoredDamage;
    // InteractAttack::actCommon visibility gate (interactBattle.cpp:450-456)
    // and the Beatle strategy's invincible gate (TAIbeatle.cpp:1102-1104).
    if(t->isVisible()&&!t->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){
        t->mStoredDamage+=damage;if(pc_p2_kabuto_original_actor(t))t->mDamageCount+=1.0f;t->setCreaturePointer(1,nullptr);hit.applied=true;}
    hit.healthAfter=t->mHealth;hit.storedDamageAfter=t->mStoredDamage;hit.rejected=!hit.applied&&t->isAlive();
    return true;
}
// Visual roll + the P1 boulder's ground dust (#884). The rolled distance is the
// horizontal path length per 30 Hz source tick (display only). While the stone
// is on the floor, a detached one-shot EFF_Iwagon_Start2 puff (the P1 boulder's
// own rolling dust, runrock_kb.pcr) is emitted at its base every few ticks.
void rollStone(int i){
    const P2CannonStone& st=fleet.stone(i);
    const float vx=st.velocity().x,vz=st.velocity().z;
    slotRoll[i]+=std::sqrt(vx*vx+vz*vz)*P2CannonStone::kSourceDelta;
    if(!effectMgr||!mapMgr||!mapMgr->mMapModel||st.scale()<1.0f)return;
    if(++slotDustTicks[i]%kDustTickInterval!=0)return;
    const Vector3f base(st.position().x,st.position().y,st.position().z);
    if(base.y-mapMgr->getMinY(base.x,base.z,true)>kDustGroundSlack)return; // airborne: no dust
    zen::particleGenerator* g=effectMgr->create(EffectMgr::EFF_Iwagon_Start2,base,nullptr,nullptr);
    if(g)g->configureOneShotBurst(kDustParticles,kDustLifetime);
}
void stoneTick(StoneSnapshot& snap){
    buildSnapshot(snap);snapshotOthers(snap);
    p2kabutostone::Strike strikes[64];p2kabutostone::DeadEvent deads[p2kabutostone::kFleetCapacity];p2kabutostone::Released rel[p2kabutostone::kFleetCapacity];
    int sn=0,dn=0,rn=0;
    fleet.tick(p2kabutostone::kStoneGravity,&stoneTrace,&stoneMap,snap.targets.data(),int(snap.targets.size()),
        strikes,64,sn,deads,p2kabutostone::kFleetCapacity,dn,rel,p2kabutostone::kFleetCapacity,rn,pc_p2_navis().size()==1?tokenOf(pc_p2_navis().first()):0);
    // Receivers run only after the whole snapshot/tick, since they may change
    // actor state (snapshot-before-stimulate).
    for(int i=0;i<sn;++i){const auto& k=strikes[i];
        int idx=-1;for(size_t j=0;j<snap.targets.size();++j)if(snap.targets[j].token==k.target){idx=int(j);break;}
        if(idx<0)continue;
        Creature* target=snap.creatures[size_t(idx)];const char code=snap.kinds[size_t(idx)];
        const bool attack=k.kind==P2CannonStoneStrikeKind::Attack;
        // Press is attributed to the live shooter (Rock.cpp:213-218); a Teki
        // Attack to the Stone itself, which has no Creature here (Rock.cpp:222).
        Creature* owner=nullptr;
        if(!attack&&k.owner){auto sh=shooters.find(k.owner);if(sh!=shooters.end())owner=sh->second;}
        P2ProjectileEngineHit hit;bool kabutoHost=false;
        if(target&&target->isAlive()){
            kabutoHost=attack&&code=='t'&&kabutoHostStoneAttack(target,k.damage,hit);
            if(!kabutoHost)hit=p2_projectile_apply_engine_strike(target,owner,attack,code=='t',k.damage);}
        std::printf("P2_KABUTO_STONE_HIT generator=%u stone=%u kind=%s target=%s token=%llx damage=%.1f applied=%d health=%.1f->%.1f stored=%.1f->%.1f owner=%d kabuto_host=%d t_flight=%.3f travel=%.1f\n",
            slotGen[k.slot],k.stone,attack?"Attack":"Press",targetName(code),static_cast<unsigned long long>(k.target),k.damage,int(hit.applied),
            hit.healthBefore,hit.healthAfter,hit.storedDamageBefore,hit.storedDamageAfter,int(owner!=nullptr),int(kabutoHost),k.flight,k.travel);
    }
    for(int i=0;i<dn;++i){const auto& d=deads[i];
        std::printf("P2_KABUTO_STONE_DEAD generator=%u stone=%u reason=%s t_flight=%.3f travel=%.1f max_lateral=%.3f hits=%d closest=%.1f x=%.1f y=%.1f z=%.1f\n",
            slotGen[d.slot],d.stone,p2kabutostone::deadReasonName(d.reason),d.flight,d.travel,d.maxLateral,d.hits,
            d.closestNaviPiki<99999.0f?d.closestNaviPiki:99999.0f,d.pos.x,d.pos.y,d.pos.z);}
    for(int i=0;i<rn;++i){
        std::printf("P2_KABUTO_STONE_RELEASE generator=%u stone=%u slot=%d\n",slotGen[rel[i].slot],rel[i].stone,rel[i].slot);
        slotGen[rel[i].slot]=0;slotPosTicks[rel[i].slot]=0;slotRoll[rel[i].slot]=0.0f;slotDustTicks[rel[i].slot]=0;}
    bool pos=false;
    for(int i=0;i<p2kabutostone::kFleetCapacity;++i){
        if(!fleet.used(i)||!fleet.stone(i).isAlive())continue;
        rollStone(i);
        if(++slotPosTicks[i]%15!=0)continue;
        const P2CannonStone& st=fleet.stone(i);pos=true;
        std::printf("P2_KABUTO_STONE_POS generator=%u stone=%u x=%.1f y=%.1f z=%.1f scale=%.3f t=%.3f\n",slotGen[i],fleet.id(i),st.position().x,st.position().y,st.position().z,st.scale(),st.timer());
    }
    if(sn||dn||rn||pos)std::fflush(stdout);
}
}
void pc_p2_kabuto_fsm_update_stones(){
    if(fleet.active()==0){stoneDebt=0.0;return;}
    if(!gsys||!mapMgr||!mapMgr->mMapModel)return;
    // Same pause/movie gate as pc_p2_projectiles_update.
    const bool active=!gameflow.mPauseAll&&!gameflow.mIsUIOverlayActive&&!(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive);
    if(!active)return;
    const int ticks=p2kabutostone::stoneTicksFor(stoneDebt,gsys->getFrameTime());
    static StoneSnapshot snap;
    for(int i=0;i<ticks&&fleet.active()>0;++i)stoneTick(snap);
}
// Visual stand-in: the retail Rock/Stone model is not staged, so the P1 Rolling
// Boulder (Iwagon, Beatle's P1 spawn type) mesh is drawn at the Stone's base,
// scaled from its 24-unit radius to the Stone's 40 x scale bounding sphere.
//
// The shared Iwagon shape's joints are overridden to TekiShapeObject::
// mAnimContext (tekibteki.cpp:241), whose mData starts null (Animator.h:479-484)
// and is written only by a live Iwagon BTeki's Animator::updateContext
// (animMgr.cpp:527-530, called from tekibteki.cpp:179,2209). With no Iwagon
// drawn yet this stage, BaseShape::updateAnim would hit ERROR("no joint anim!!")
// -> System::halt (shapeBase.cpp:3358-3361, system.cpp:1225-1231). So while the
// context is empty it is pointed at the shape's own current animation data,
// mCurrentAnimation->mData, and restored after the stones draw. That is the
// animation most recently loaded into the Iwagon shape (loadDck / importDck /
// loadDca / importDca each overwrite it, shapeBase.cpp:3100,3128,3148,3174),
// i.e. normally the last clip of its bundle; only a shape with no animation
// loaded still holds the 0-frame "Null Anim" created at load
// (shapeBase.cpp:2854-2857 via importDck(nullptr), 3111-3113), which takes the
// base-pose branch (shapeBase.cpp:3376-3382). Which one the campaign Iwagon
// holds at runtime is unverified. Either way the frame is pinned to 0 (the
// explicit frame pointer skips animate(), shapeBase.cpp:3354-3356), so the
// stand-in shows that clip's frame-0 pose. Without anim data, no draw.
void pc_p2_kabuto_fsm_draw_stones(Graphics& gfx){
    if(fleet.active()==0||!gfx.mCamera)return;
    for(int i=0;i<p2kabutostone::kFleetCapacity;++i){if(!slotOriginal[i]||!fleet.used(i))continue;
     const auto& st=fleet.stone(i);const bool dead=st.phase()==P2CannonStonePhase::Dead;if(!dead&&st.phase()!=P2CannonStonePhase::Move)continue;
     const std::string clip=dead?"dead":"run";const auto& timing=originalStoneResource.clocks.at(clip);const auto& shapes=originalStoneResource.shapes.at(clip);
     const float frame=dead?std::min(float(timing.duration-1),fleet.deadSeconds(i)*30.0f):std::fmod(st.timer()*30.0f,float(timing.duration));Shape* model=shapes.at(timing.index(frame/float(timing.duration-1),false));
     Matrix4f world,view;world.makeSRT(Vector3f(st.scale(),st.scale(),st.scale()),Vector3f(0,st.faceDir(),0),Vector3f(st.position().x,st.position().y,st.position().z));gfx.mCamera->mLookAtMtx.multiplyTo(world,view);model->updateAnim(gfx,view,nullptr,nullptr);model->drawshape(gfx,*gfx.mCamera,nullptr);
    }
    TekiShapeObject* so=tekiMgr?tekiMgr->getTekiShapeObject(TEKI_Iwagon):nullptr;
    Shape* shape=so?so->mShape:nullptr;
    AnimData* const sharedAnim=so?so->mAnimContext.mData:nullptr;
    AnimData* const shapeAnim=(shape&&shape->mCurrentAnimation)?shape->mCurrentAnimation->mData:nullptr;
    AnimData* const drawAnim=sharedAnim?sharedAnim:shapeAnim;
    if(!stoneDrawLogged){stoneDrawLogged=true;
        std::printf("P2_KABUTO_STONE_DRAW model=%s anim=%s frames=%d\n",shape&&drawAnim?"iwagon_standin":"none",
            !shape?"none":sharedAnim?"shared":shapeAnim?"shape_current":"missing",drawAnim?drawAnim->mTotalFrameCount:-1);std::fflush(stdout);}
    if(!shape||!drawAnim)return;
    const float savedFrame=so->mAnimContext.mCurrentFrame;
    so->mAnimContext.mData=drawAnim;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
    gfx.useMaterial(nullptr);gfx.setDepth(true);
    for(int i=0;i<p2kabutostone::kFleetCapacity;++i){
        if(slotOriginal[i]||!fleet.used(i))continue;
        const P2CannonStone& st=fleet.stone(i);
        if(st.phase()!=P2CannonStonePhase::Move&&st.phase()!=P2CannonStonePhase::Dead)continue;
        // P1 boulder, sized to the Stone's map sphere (r25, mPosition is the
        // sphere bottom) so the drawn rock sits on the floor exactly where the
        // trace puts it, and rolled about the axis perpendicular to its
        // heading by the distance travelled (visual only).
        const float radius=p2kabutostone::kMapRadius*st.scale();
        const float k=radius/kIwagonMeshRadius;
        const float roll=(i>=0&&i<p2kabutostone::kFleetCapacity)?slotRoll[i]/p2kabutostone::kMapRadius:0.0f;
        Matrix4f yaw,body,world,view;
        yaw.makeSRT(Vector3f(1.0f,1.0f,1.0f),Vector3f(0.0f,st.faceDir(),0.0f),Vector3f(st.position().x,st.position().y+radius,st.position().z));
        body.makeSRT(Vector3f(k,k,k),Vector3f(roll,0.0f,0.0f),Vector3f(0.0f,0.0f,0.0f));
        yaw.multiplyTo(body,world);
        gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
        // Frame pinned so the shared Iwagon animation context is not advanced.
        float frame=0.0f;
        shape->updateAnim(gfx,view,&frame,nullptr);
        shape->drawshape(gfx,*gfx.mCamera,nullptr);
    }
    // Hand the shared context back exactly as the Iwagon animator left it.
    so->mAnimContext.mData=sharedAnim;
    so->mAnimContext.mCurrentFrame=savedFrame;
}
