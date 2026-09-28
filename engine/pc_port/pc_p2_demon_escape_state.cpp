#include "pc_p2_demon_escape_state.h"
#include "pc_p2_demon_admission.h"
#include "Navi.h"
#include "NaviState.h"
#include "NaviMgr.h"
#include "PaniPikiAnimator.h"

namespace {
class EscapeState final : public NaviState {
public:
    Navi* captain=nullptr;
    EscapeState():NaviState(NAVISTATE_DemonEscape) {}
    void init(Navi* n) override {
        if(n!=captain) { n->mStateMachine->transit(n,NAVISTATE_Walk); return; }
        n->startMotion(PaniMotionInfo(PIKIANIM_Fall),PaniMotionInfo(PIKIANIM_Fall));
    }
    void exec(Navi* n) override {
        if(n!=captain) return;
        if(n->mGroundTriangle) n->mStateMachine->transit(n,NAVISTATE_Walk);
    }
    void procBounceMsg(Navi* n,MsgBounce*) override {
        if(n==captain) n->mStateMachine->transit(n,NAVISTATE_Walk);
    }
    void cleanup(Navi*) override { captain=nullptr; }
};
EscapeState* state(Navi* n) {
    if(!n||!n->mStateMachine||n->mStateMachine->mStateLimit<=NAVISTATE_DemonEscape) return nullptr;
    int i=n->mStateMachine->mStateIndexes[NAVISTATE_DemonEscape];
    return i>=0&&i<n->mStateMachine->mStateCount ? dynamic_cast<EscapeState*>(n->mStateMachine->mStates[i]) : nullptr;
}
}
NaviState* pc_demon_escape_state_create() { return new EscapeState(); }
bool pc_demon_escape_begin(Navi* n) {
    auto* s=state(n);
    if(!s||s->captain||!n->isAlive()||n->isStickTo()||n->mRope||!pc_demon_captain_admission_eligible(n)) return false;
    s->captain=n;
    n->mGroundTriangle=nullptr;
    n->mPreviousTriangle=nullptr;
    n->mStateMachine->transit(n,NAVISTATE_DemonEscape);
    if(n->getCurrState()!=s) { s->captain=nullptr; return false; }
    return true;
}
bool pc_demon_escape_active(Navi* n) { auto* s=state(n); return s&&s->captain==n&&n->getCurrState()==s; }
void pc_demon_escape_reset(Navi* n) {
    auto* s=state(n); if(!s||s->captain!=n) return;
    s->captain=nullptr;
}
void pc_demon_escape_scene_exit() {
    // States remain allocated until the app heap is reset; revoke without a
    // transition while all manager-owned Navis are still valid.
    if(!naviMgr) return;
    Iterator it(naviMgr);
    for(it.first();!it.isDone();it.next()) pc_demon_escape_reset(static_cast<Navi*>(*it));
}
