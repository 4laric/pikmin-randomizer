#include "pc_p2_surface_water_drain.h"
#include <cassert>
#include <cstdio>
#include <limits>
int main() {
    p2water::Box box{0,{0,0,0},{100,50,100},50};
    p2water::Drain d; d.id=0;
    assert(p2water::validDrain(d,0));
    assert(p2water::containsDrained(box,d,50,47,50,0));
    assert(p2water::startDrain(d));
    assert(!p2water::startDrain(d));
    p2water::updateDrain(d,1);
    assert(d.lowered==0 && d.timer==5); // old timer, not new timer
    p2water::updateDrain(d,1);
    assert(d.lowered==-5 && d.timer==10);
    assert(!p2water::containsDrained(box,d,50,47,50,0));
    assert(p2water::containsDrained(box,d,50,-1000,50,0)); // retail no bottom
    auto saved=d;
    p2water::updateDrain(d,0);
    p2water::updateDrain(d,std::numeric_limits<float>::quiet_NaN());
    assert(d.lowered==saved.lowered && d.timer==saved.timer);
    std::vector<p2water::Drain> live{p2water::Drain{0},p2water::Drain{1}};
    auto second=saved; second.id=1;
    p2water::DrainSnapshot state{"tutorial","exact-source",{saved,second}};
    auto wrong=state; wrong.course="forest";
    assert(!p2water::restoreDrains(wrong,"tutorial","exact-source",live));
    wrong=state; wrong.sourceSha="other-source";
    assert(!p2water::restoreDrains(wrong,"tutorial","exact-source",live));
    wrong=state; wrong.boxes[1].lowered=1;
    assert(!p2water::restoreDrains(wrong,"tutorial","exact-source",live));
    assert(live[0].phase==p2water::Phase::Active && live[1].phase==p2water::Phase::Active);
    assert(!p2water::restoreDrains(state,"tutorial","",live));
    assert(p2water::restoreDrains(state,"tutorial","exact-source",live));
    auto restored=live[0];
    for(int i=0;i<100 && d.phase!=p2water::Phase::Dead;++i) {
        p2water::updateDrain(d,0.25f); p2water::updateDrain(restored,0.25f);
        assert(d.lowered==restored.lowered && d.timer==restored.timer && d.phase==restored.phase);
        assert(p2water::validDrain(d,0));
    }
    assert(d.phase==p2water::Phase::Dead && d.lowered==-100);
    assert(!p2water::containsDrained(box,d,50,-1000,50,0));
    assert(!p2water::startDrain(d));
    auto bad=d; bad.id=1; assert(!p2water::validDrain(bad,0));
    bad=d; bad.lowered=-99; assert(!p2water::validDrain(bad,0));
    bad=saved; bad.goal=-50; assert(!p2water::validDrain(bad,0));
    bad=saved; bad.timer=1e30f; assert(!p2water::validDrain(bad,0));
    std::puts("PASS ORIGINAL_WATER_DRAIN_STATE source_update_order=1 typed_restore=1 atomic_reject=1 dead_unlinked_query=1 natural_gameplay=0");
}
