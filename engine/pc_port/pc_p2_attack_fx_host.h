#pragma once
// Engine side of the shared P2 attack-effect helpers (pc_p2_attack_fx.h).
// One Emitter per actor (or per poisoned Pikmin): every generator it creates
// carries the Emitter's own callback as owner, so stopAll() can force-finish
// exactly this actor's generators (zen::particleManager::killGenerator by
// callback, the BurnEffect::kill pattern) without touching anyone else's and
// without holding generator pointers that the pool may have recycled.
#include "pc_p2_attack_fx.h"

namespace p2attackfx {

// Authored-emission looks (Look::burst == false, e.g. EFF_Tank_Fire) run for
// their own authored length; re-create them this often while the attack is
// active instead of every tick.
constexpr unsigned AUTHORED_REFRESH_TICKS = 8;

class Emitter {
public:
    Emitter();
    ~Emitter();
    Emitter(const Emitter&) = delete;
    Emitter& operator=(const Emitter&) = delete;

    // Creates the points of one tick. `tick` is the session tick index (drives
    // the authored-emission refresh cadence). Returns the generators created.
    unsigned emit(Element e, const Point* pts, int n, unsigned tick);
    // Same as emit() with an explicit look (a one-off puff the element table does not
    // cover, e.g. the poisoned-Pikmin head cloud).
    unsigned emitLook(const Look& look, const Point* pts, int n);
    // Force-finishes every generator this emitter created. Returns how many it
    // had created since the previous stopAll (for the START/STOP evidence).
    unsigned stopAll();
    unsigned created() const { return made_; }

private:
    void* owner_ = nullptr;
    unsigned made_ = 0;
};

} // namespace p2attackfx
