#include "PikiAI.h"
#include "pc_blue_rescue.h"
#include "pc_p2_species.h"
#include <cassert>
#include <cstdio>

RouteMgr manager; RouteMgr* routeMgr = &manager;
System systemStub; System* gsys = &systemStub;
PikiMgr roster; PikiMgr* pikiMgr = &roster;
int pc_p2_species(const Piki* p) { return p->species; }

int main() {
    Piki blue, red, other;
    blue.state = PIKISTATE_Normal; red.species = P2SpeciesRed;
    ActRescue rescue(&blue); TopAction top; top.action = &rescue;
    blue.mActiveAction = &top; roster.actors = {&blue, &red};
    WayPoint dry; dry.mPosition = {50, 0, 0}; manager.waypoint = &dry;
    auto pickup = [&] {
        red.state = PIKISTATE_Drown;
        rescue.init(&red); rescue.initRescue(); rescue.animationKeyUpdated({KEY_Action0});
        assert(rescue.exec() == ACTOUT_Continue);
        assert(red.state == PIKISTATE_WaterHanged && pc_blue_rescue_owned(&red, &blue));
    };
    assert(!pc_blue_rescue_tick(&red)); // captain-held fallback, no rescue registration
    rescue.init(&red); rescue.initRescue(); rescue.animationKeyUpdated({KEY_Action0});
    manager.waypoint = nullptr;
    assert(rescue.exec() == ACTOUT_Fail && red.state == PIKISTATE_Drown);
    assert(!pc_blue_rescue_owned(&red, &blue)); manager.waypoint = &dry;
    pickup(); assert(pc_blue_rescue_tick(&red));
    assert(red.state == PIKISTATE_WaterHanged); // no captain is present in the doubles
    assert(!pc_blue_rescue_begin(&red, &blue)); // cannot replace an existing owner
    Piki secondBlue; secondBlue.state = PIKISTATE_Normal;
    ActRescue secondRescue(&secondBlue); TopAction secondTop; secondTop.action = &secondRescue;
    secondBlue.mActiveAction = &secondTop; roster.actors.push_back(&secondBlue);
    secondRescue.init(&red); secondRescue.initRescue(); secondRescue.animationKeyUpdated({KEY_Action0});
    assert(secondRescue.exec() == ACTOUT_Fail && pc_blue_rescue_owned(&red, &blue));
    secondRescue.cleanup(); assert(red.state == PIKISTATE_WaterHanged);
    pc_blue_rescue_release(&red, &other); assert(pc_blue_rescue_owned(&red, &blue));
    rescue.cleanup(); assert(red.state == PIKISTATE_Normal && !pc_blue_rescue_owned(&red, &blue));

    pickup(); top.mCurrActionIdx = PikiAction::NOACTION;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal);
    top.mCurrActionIdx = PikiAction::Rescue;
    pickup(); top.action = nullptr;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal); top.action = &rescue;
    pickup(); blue.mActiveAction = nullptr;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal); blue.mActiveAction = &top;
    pickup(); blue.alive = false;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal); blue.alive = true;
    pickup(); blue.state = PIKISTATE_Flying;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal); blue.state = PIKISTATE_Normal;
    pickup(); blue.species = P2SpeciesPurple;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal); blue.species = P2SpeciesBlue;
    pickup(); roster.actors = {&red};
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal);
    roster.actors = {&blue, &red};
    pickup(); rescue.mDrowningPiki = &other;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal);
    pickup(); rescue.mState = ActRescue::STATE_Approach;
    assert(pc_blue_rescue_tick(&red) && red.state == PIKISTATE_Normal);

    pickup(); red.mFSM->transit(&red, PIKISTATE_Normal); // ordinary whistle/FSM interruption
    Vector3f before = red.mSRT.t;
    assert(rescue.exec() == ACTOUT_Fail && red.mSRT.t.x == before.x && red.mSRT.t.z == before.z);
    assert(!pc_blue_rescue_owned(&red, &blue));
    pickup(); rescue.init(&other); // action reuse must release an old held victim
    assert(red.state == PIKISTATE_Normal && !pc_blue_rescue_owned(&red, &blue));
    pickup(); assert(rescue.exec() == ACTOUT_Continue && rescue.mState == ActRescue::STATE_Throw);
    rescue.mThrowReady = false; rescue.mGotAnimationAction = true;
    assert(rescue.exec() == ACTOUT_Continue && red.state == PIKISTATE_Flying);
    assert(!pc_blue_rescue_owned(&red, &blue));
    rescue.mAnimationFinished = true; assert(rescue.exec() == ACTOUT_Success); rescue.cleanup();
    assert(red.state == PIKISTATE_Flying); // release must not undo a completed throw

    red.state = PIKISTATE_WaterHanged;
    assert(!pc_blue_rescue_begin(&red, reinterpret_cast<Piki*>(1))); // absent pointer never dereferenced
    pikiMgr = nullptr; assert(!pc_blue_rescue_begin(&red, &blue)); pikiMgr = &roster;
    assert(!pc_blue_rescue_tick(&red));
    std::puts("PASS actual Blue rescue ownership, interruption, reuse and completed throw");
}
