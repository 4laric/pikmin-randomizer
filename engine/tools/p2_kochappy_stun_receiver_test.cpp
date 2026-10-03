#include "pc_p2_kochappy_stun.h"
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_purple_impact_policy.h"
#include "TAI/Action.h"
#include "teki.h"
#include <cstdio>

// The real stun.cpp is compiled unchanged. Host/TAI and the own-FSM edge are
// deliberately stubbed; this is not a natural-impact or production-FSM test.
bool pc_p2_kochappy_fsm_suppress_ai(const BTeki* actor) { return actor->ownFSM; }
bool pc_p2_kochappy_fsm_stun_eligible(const BTeki* actor) { return actor->ownEligible; }
void pc_p2_kochappy_fsm_begin_stun(BTeki* actor) { ++actor->pauseCalls; }

#define CHECK(c) do { if (!(c)) { std::fprintf(stderr,"receiver check failed line %d: %s\n",__LINE__,#c); return __LINE__; } } while(false)

int main()
{
    const p2purpleimpact::Event event { 2, 3, 0, 0, 0 };
    Teki red;
    red.ownFSM = true;
    // A living own FSM may retain P1 birth-state0 and have no TAI strategy.
    // This is the original regression: P1-only eligibility rejected it.
    pc_p2_kochappy_stun_register(&red, 10.0f);
    CHECK(pc_p2_kochappy_stun_receive(&red,event,0.5f));
    CHECK(red.mStateID == 0 && red.strategy == nullptr && red.pauseCalls == 1);
    CHECK(red.mVelocity.y == 250 && red.mTargetVelocity.y == 250);
    CHECK(pc_p2_kochappy_stun_active(&red));
    for (int i=0;i<3;++i) CHECK(!pc_p2_kochappy_stun_step(&red,0.125f,1));
    CHECK(pc_p2_kochappy_stun_needs_fit_roll(&red));
    CHECK(!pc_p2_kochappy_stun_step(&red,0.125f,0));
    CHECK(!pc_p2_kochappy_stun_needs_fit_roll(&red));
    // Exact source threshold is strictly >10s; the entry step consumed0.125.
    for (int i=0;i<79;++i) CHECK(!pc_p2_kochappy_stun_step(&red,0.125f,1));
    CHECK(pc_p2_kochappy_stun_step(&red,0.125f,1));
    CHECK(!pc_p2_kochappy_stun_active(&red));

    // Reject own terminal phases through its authoritative FSM edge despite
    // a nominally eligible P1 state. No transition or receiver state mutation.
    red.ownEligible=false; red.mStateID=4;
    CHECK(!pc_p2_kochappy_stun_receive(&red,event,0));
    CHECK(!pc_p2_kochappy_stun_active(&red) && red.pauseCalls==1);
    red.ownEligible=true;
    red.mGroundTriangle=nullptr; CHECK(!pc_p2_kochappy_stun_receive(&red,event,0));
    red.mGroundTriangle=&red;
    red.invincible=true; CHECK(!pc_p2_kochappy_stun_receive(&red,event,0)); red.invincible=false;
    red.flying=true; CHECK(!pc_p2_kochappy_stun_receive(&red,event,0)); red.flying=false;
    red.mDeadState=1; CHECK(!pc_p2_kochappy_stun_receive(&red,event,0)); red.mDeadState=0;
    red.alive=false; CHECK(!pc_p2_kochappy_stun_receive(&red,event,0)); red.alive=true;

    // Orange's registered5s profile remains per actor, with the same edge.
    Teki orange; orange.ownFSM=true;
    pc_p2_kochappy_stun_register(&orange,5);
    CHECK(pc_p2_kochappy_stun_receive(&orange,event,0));
    for(int i=0;i<3;++i) CHECK(!pc_p2_kochappy_stun_step(&orange,0.125f,1));
    CHECK(!pc_p2_kochappy_stun_step(&orange,0.125f,0));
    for(int i=0;i<39;++i) CHECK(!pc_p2_kochappy_stun_step(&orange,0.125f,1));
    CHECK(pc_p2_kochappy_stun_step(&orange,0.125f,1));

    // Repeated impact preserves a positive Fit timer, even with a failed roll.
    CHECK(pc_p2_kochappy_stun_receive(&red,event,0));
    for(int i=0;i<3;++i) CHECK(!pc_p2_kochappy_stun_step(&red,0.125f,1));
    CHECK(!pc_p2_kochappy_stun_step(&red,4,0));
    CHECK(pc_p2_kochappy_stun_receive(&red,event,0));
    for(int i=0;i<3;++i) CHECK(!pc_p2_kochappy_stun_step(&red,0.125f,1));
    CHECK(!pc_p2_kochappy_stun_needs_fit_roll(&red));
    CHECK(!pc_p2_kochappy_stun_step(&red,6,1));
    CHECK(pc_p2_kochappy_stun_step(&red,0.125f,1));

    CHECK(pc_p2_kochappy_stun_receive(&red,event,0));
    pc_p2_kochappy_stun_interrupt(&red);
    CHECK(!pc_p2_kochappy_stun_active(&red));
    CHECK(pc_p2_kochappy_stun_step(&red,0.125f,0));
    pc_p2_kochappy_stun_forget(&red);
    CHECK(!pc_p2_kochappy_stun_receive(&red,event,0));
    pc_p2_kochappy_stun_register(&red,10); // same address, fresh receiver lifetime
    CHECK(pc_p2_kochappy_stun_receive(&red,event,0));
    for(int i=0;i<3;++i) CHECK(!pc_p2_kochappy_stun_step(&red,0.125f,1));
    CHECK(pc_p2_kochappy_stun_step(&red,0.125f,1)); // no old positive Fit timer

    // Unowned/P1 consumer still requires state4..16 and a real TAI transition.
    Teki legacy; TaiStrategy strategy; legacy.strategy=&strategy;
    pc_p2_kochappy_stun_register(&legacy,10);
    CHECK(!pc_p2_kochappy_stun_receive(&legacy,event,0));
    legacy.mStateID=4; strategy.allow=false;
    CHECK(!pc_p2_kochappy_stun_receive(&legacy,event,0));
    CHECK(strategy.transitions==1 && legacy.pauseCalls==0);
    strategy.allow=true;
    CHECK(pc_p2_kochappy_stun_receive(&legacy,event,0));
    CHECK(strategy.transitions==2 && legacy.mStateID==16 && legacy.pauseCalls==0);
    pc_p2_kochappy_stun_reset();
    CHECK(!pc_p2_kochappy_stun_active(&legacy));
    std::puts("P2_KOCHAPPY_RECEIVER_UNIT_PASS host_tai_fsm_edges=stubbed natural_acceptance=none");
}
