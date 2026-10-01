#include "pc_p2_demon_bridge.h"
#include "pc_p2_demon_drop_state.h"
#include "pc_p2_demon_escape_state.h"
#include "pc_p2_demon_admission.h"
#include "Navi.h"
#include "NaviState.h"
#include "Creature.h"
#include "Collision.h"
#include "PaniPikiAnimator.h"
#include "pc_p2_demon_escape.h"
#include <limits>

namespace {
struct Binding {
    Navi* captain=nullptr;
    std::uint64_t ownerToken=0;
    Creature* owner=nullptr;
    CollPart* mouth=nullptr;
    unsigned slot=0;
    float priorMotionSpeed=30;
} binding;
P2DemonEscapeWindow escapeWindow;
std::uint64_t nextDropGeneration=0;
bool current(Navi* n) { return n && binding.captain==n; }
void detach(Navi* n) {
    if(!current(n)) return;
    const float speed=binding.priorMotionSpeed;
    Creature* const owner=binding.owner;
    CollPart* const mouth=binding.mouth;
    binding={}; // Revoke callback authority before native owner-list mutation.
    // Never detach a replacement mouth selected by another owner/callback.
    if(n->isStickToMouth()&&n->getStickObject()==owner&&n->getStickPart()==mouth) n->endStickMouth();
    if(n->isAlive()) n->mMotionSpeed=speed;
}
}

bool pc_demon_capture(Navi* n, Creature* owner, CollPart* mouth, std::uint64_t token, unsigned slot) {
    if(binding.captain||!n||!owner||!mouth||!token||slot>=2||!mouth->isBouncySphereType()||!n->isAlive()||n->isStickTo()||n->mRope||
       !pc_demon_captain_admission_eligible(n)) return false;
    n->startStickMouth(owner,mouth);
    if(!n->isStickToMouth()||n->getStickObject()!=owner||n->getStickPart()!=mouth) {
        if(n->isStickToMouth()&&n->getStickObject()==owner&&n->getStickPart()==mouth) n->endStickMouth();
        return false;
    }
    binding={n,token,owner,mouth,slot,n->mMotionSpeed};
    escapeWindow.reset();
    n->releasePikis();
    if(!pc_demon_bound(n)) return false;
    n->mVelocity.set(0,0,0); n->mTargetVelocity.set(0,0,0); n->mVolatileVelocity.set(0,0,0);
    n->startMotion(PaniMotionInfo(PIKIANIM_Fall),PaniMotionInfo(PIKIANIM_Fall));
    return true;
}

bool pc_demon_forced_release(Navi* n, float damage, float speed) {
    if(!current(n)||!std::isfinite(damage)||damage<0||nextDropGeneration==std::numeric_limits<std::uint64_t>::max()) return false;
    detach(n);
    // P2 FallMeck zero-damage path: release first, then admission. A refusal
    // leaves a detached captain in Walk rather than reattaching stale ownership.
    return n->isAlive()&&!n->isStickTo()&&pc_demon_drop_begin(n,++nextDropGeneration,damage,speed);
}

bool pc_demon_bound(Navi* n) {
    if(!current(n)) return false;
    if(!n->isAlive()||!pc_demon_captain_admission_eligible(n)||n->mRope||!n->isStickToMouth()||
       n->getStickObject()!=binding.owner||n->getStickPart()!=binding.mouth) { detach(n); return false; }
    return true;
}
bool pc_demon_owned_by(Navi* n, Creature* owner) { return pc_demon_bound(n) && binding.owner==owner; }
void pc_demon_release(Navi* n) { detach(n); }
void pc_demon_reset(Navi* n) { detach(n); pc_demon_escape_reset(n); }
void pc_demon_owner_lost(std::uint64_t token) { if(token&&token==binding.ownerToken) detach(binding.captain); }
void pc_demon_scene_exit() { detach(binding.captain); pc_demon_escape_scene_exit(); escapeWindow.reset(); }
void pc_demon_forget() { binding={}; escapeWindow.reset(); }
void pc_demon_before_transition(Navi* n,int) { if(pc_demon_bound(n)) detach(n); }

bool pc_demon_escape_tick(Navi* n,bool edge,P2DemonRandom random,void* context) {
    if(!random||!pc_demon_bound(n)) return false;
    auto result=escapeWindow.step(true,edge,[&]{ return random(context); });
    n->mMotionSpeed=result.animationSpeed;
    if(!result.escape) return false;
    detach(n);
    // P2 SaraiExit has no FallMeck vertical assignment; its dedicated state
    // starts Fall, suppresses atari, and restores it on every exit path.
    return pc_demon_escape_begin(n);
}
bool pc_demon_suppress_atari(Navi* n) { return pc_demon_escape_active(n); }

// P1 mouth links retain ownership but do not follow P2 animated joints.
// Read only the exact live binding; the host revokes before disposing its parts.
bool pc_demon_capture_matrix(Navi* n, Matrix4f& out)
{
    if (!pc_demon_bound(n)) return false;
    const Matrix4f& joint = binding.mouth->mJointMatrix;
    for (int r=0; r<3; ++r) for (int c=0; c<4; ++c)
        if (!std::isfinite(joint.mMtx[r][c]) || std::fabs(joint.mMtx[r][c])>1.0e6f) return false;
    out.makeIdentity();
    // P2 non-OniKurage mouth attachment: jointWorld * Rz(pi/2).
    for (int r=0; r<3; ++r) {
        out.mMtx[r][0]=joint.mMtx[r][1];
        out.mMtx[r][1]=-joint.mMtx[r][0];
        out.mMtx[r][2]=joint.mMtx[r][2];
        out.mMtx[r][3]=joint.mMtx[r][3];
    }
    return true;
}
void pc_demon_follow_mouth(Navi* n)
{
    Matrix4f pose;
    if (!pc_demon_capture_matrix(n, pose)) return;
    n->mSRT.t.set(pose.mMtx[0][3],pose.mMtx[1][3],pose.mMtx[2][3]);
    n->mVelocity.set(0,0,0);
    n->mTargetVelocity.set(0,0,0);
    n->mVolatileVelocity.set(0,0,0);
}
