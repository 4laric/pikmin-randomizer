// Engine glue for the P2 flyer body collision (wave 3 flyers, #960).
//
// A bound P2 flyer runs on a P1 host actor (BTeki). The host wears a retail
// enemycoll tree instead of its vehicle's (joint spheres sampled during the
// vehicle's own draw, which never happens once the P2 model is drawn), so that
// (a) thrown Pikmin latch onto the hovering body and (b) the spheres follow the
// host every simulated tick without depending on the draw. Same mechanism as
// the Demon anchor (pc_p2_sarai_demon.cpp, #215), factored so more flyers can
// reuse it. Parts are update-inactive: follow() owns centre/radius/matrix.
#pragma once

#include "pc_p2_flyer.h"

class BTeki;
class CollInfo;
class CollPart;

class P2FlyerColl {
public:
    // Builds the own tree from `table` and swaps it onto `actor` (the vehicle
    // tree is kept for release()). Returns false when already bound or the
    // actor has no CollInfo.
    bool bind(BTeki* actor, const p2flyer::Sphere* table, int count);
    // Seats every sphere on the body for the actor at `root` facing `yaw`.
    void follow(BTeki* actor, const p2flyer::Vec3& root, float yaw, const p2flyer::Vec3& body, float scale);
    // Gives the actor its vehicle CollInfo back (the own tree is never freed:
    // stuck Pikmin may still hold its CollPart pointers) and seats the vehicle
    // carcass/bounding spheres on the dead body.
    void release(BTeki* actor, const p2flyer::Vec3& deadCentre);
    // Non-destructive detach used from destructors/teardown.
    void detach(BTeki* actor);
    bool bound() const { return mOwn != nullptr; }
    // The live CollPart of table entry `index` (nullptr when unbound/out of range).
    CollPart* part(int index) const { return index >= 0 && index < mCount ? mParts[index] : nullptr; }
    bool released() const { return mReleased; }

private:
    CollInfo* mVehicle = nullptr;
    CollInfo* mOwn = nullptr;
    CollPart* mParts[p2flyer::kMaxSpheres] = {};
    const p2flyer::Sphere* mTable = nullptr;
    int mCount = 0;
    bool mReleased = false;
};
