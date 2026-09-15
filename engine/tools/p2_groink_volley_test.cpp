#include "pc_p2_groink_volley.h"
#include "pc_p2_groink_clock.h"
#include <cstdio>
#include <cstdlib>
#include <limits>

namespace {
void check(bool value, const char* message) {
    if (!value) { std::fprintf(stderr, "FAIL %s\n", message); std::exit(1); }
}
constexpr float dt = P2GroinkPolicy::kSourceDelta;
const P2GroinkMuzzle muzzle{{1,0,0},{0,1,0},{0,0,1},{0,40,0}};
const std::array<P2GroinkVec3,3> samples{{{0.5f,0.5f,0.5f},{0,0.5f,0},{1,0.5f,1}}};
struct Trace {
    unsigned calls = 0, hitMask = 0, rejectMask = 0;
    static bool run(void* raw, const P2GroinkVec3& p, const P2GroinkVec3& v,
                    float delta, float radius, P2GroinkTraceResult& result) {
        auto& t = *static_cast<Trace*>(raw);
        check(delta == dt && radius == 10, "source step and sphere");
        const unsigned bit = 1u << t.calls++;
        if (t.rejectMask & bit) return false;
        result = {};
        result.position = {p.x+v.x*delta,p.y+v.y*delta,p.z+v.z*delta};
        result.velocity = v;
        if (t.hitMask & bit) {
            result.floor = true;
            result.hasGroundY = true;
            result.groundY = 0;
            result.position.y = 10;
        }
        return true;
    }
};
bool invalidVelocity(void*, const P2GroinkVec3& p, const P2GroinkVec3&, float, float,
                     P2GroinkTraceResult& result) {
    result = {};
    result.position = p;
    result.velocity.x = std::numeric_limits<float>::infinity();
    return true;
}
}

int main() {
    P2GroinkVolley pool;
    check(pool.emit(muzzle,100,samples).count == 3, "first three shells");
    check(pool.shell(0).primary && !pool.shell(1).primary && !pool.shell(2).primary, "one primary per volley");
    check(pool.shell(0).position.x == 25 && pool.shell(2).position.x == 25, "shared pre-spread muzzle origin");
    check(pool.shell(1).velocity.z < 0 && pool.shell(2).velocity.z > 0, "independent spread");
    check(pool.emit(muzzle,100,samples).count == 3 && pool.activeCount() == 6, "overlapping volleys");
    check(pool.shell(3).primary && !pool.shell(4).primary, "second primary");
    auto full = pool.emit(muzzle,100,samples);
    check(full.valid && full.count == 0 && pool.activeCount() == 6, "pool exhaustion drops emission");
    Trace partial{0, (1u<<1)|(1u<<4), 0};
    check(pool.update({},dt,Trace::run,&partial) && partial.calls == 6, "each original node advances once");
    check(pool.activeCount() == 4 && pool.terminalCount() == 2, "independent terminals");
    check(pool.terminals()[0].slot == 1 && pool.terminals()[1].slot == 4, "source list terminal order");
    check(pool.terminals()[0].step.valid && pool.terminals()[0].step.end.y == 0, "retained final y-minus-ten sweep");
    check(pool.emit(muzzle,100,samples).count == 2, "partial capacity is not all-or-nothing");
    check(pool.shell(1).primary && !pool.shell(4).primary, "reused primary assignment");
    check(pool.terminalCount() == 2 && !pool.terminals()[0].primary, "reuse preserves prior terminal metadata");
    Trace all{0,63,0};
    check(pool.update({},dt,Trace::run,&all) && pool.terminalCount() == 6 && pool.activeCount() == 0, "simultaneous six terminal receipts");
    const std::size_t order[]{0,2,3,5,1,4};
    for (unsigned i=0;i<6;++i) check(pool.terminals()[i].slot == order[i], "FIFO active traversal after reuse");
    pool.reset();
    auto bad = samples; bad[1].x = std::numeric_limits<float>::quiet_NaN();
    check(!pool.emit(muzzle,100,bad).valid && pool.activeCount() == 0, "invalid spread rejects atomically");
    check(!pool.emit(muzzle,-1,samples).valid, "negative speed rejected");
    auto degenerate = muzzle; degenerate.column0 = {};
    check(!pool.emit(degenerate,100,samples).valid, "zero emission axis rejected");
    pool.emit(muzzle,100,samples);
    const auto before = pool.shell(0);
    check(!pool.update({},dt,nullptr,nullptr) && !pool.update({},0.1f,Trace::run,nullptr), "invalid tick rejected before callback");
    check(pool.shell(0).position.x == before.position.x && pool.activeCount() == 3, "rejected tick immutable");
    Trace refused{0,0,1};
    check(!pool.update({},dt,Trace::run,&refused) && refused.calls == 3, "failed trace does not skip other shells");
    check(pool.activeCount() == 2 && pool.terminalCount() == 1, "failed shell recycled");
    check(!pool.terminals()[0].step.valid && pool.terminals()[0].step.reason == P2GroinkTerminalReason::Invalid, "failed trace has no invented valid sweep");
    check(pool.terminals()[0].step.start.x == pool.terminals()[0].step.end.x, "failed trace does not move through terrain");
    check(!pool.update({},dt,invalidVelocity,nullptr) && pool.activeCount() == 0
          && pool.terminalCount() == 2, "malformed successful trace recycles each affected shell");
    check(!pool.terminals()[0].step.valid && !pool.terminals()[1].step.valid, "nonfinite velocity cannot become valid damage sweep");
    pool.reset();
    check(pool.activeCount() == 0 && pool.terminalCount() == 0, "scene reset");
    pool.emit(muzzle,100,samples);
    P2GroinkSourceClock clock;
    Trace free;
    for (int i=0;i<60;++i)
        for (int ticks=clock.step(1.0/60.0,true);ticks>0;--ticks) {
            free.calls=0;
            check(pool.update({},dt,Trace::run,&free) && free.calls==3, "60 Hz host drives all three at 30 Hz");
        }
    check(std::fabs(pool.shell(0).position.x-125) < 0.001f, "one second source movement");
    check(clock.step(0.2,false)==0 && clock.step(0,true)==0, "pause adds no volley steps");
    std::puts("p2_groink_volley_test PASS");
}
