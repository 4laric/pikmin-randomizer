// #1215: compile the production dispatch with a receiver spy, and guard both
// engine-bound call sites. This proves dispatch/rejection propagation, not the
// engine receiver's gameplay, invulnerability, scaling or fatal-hit behavior.
#include "pc_p2_mamuta_navi_hit.h"
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <limits>

#ifndef P2_MAMUTA_SOURCE_ROOT
#define P2_MAMUTA_SOURCE_ROOT "."
#endif
int failures = 0;
int checks = 0;
void check(bool ok, const char* message) {
    ++checks;
    if (!ok) { ++failures; std::printf("FAIL %s\n", message); }
}
int main(int argc, char** argv) {
    Creature actor;
    Navi navi;
    check(!pc_p2_mamuta_hit_navi(nullptr, &navi, 5), "missing owner rejected");
    check(!pc_p2_mamuta_hit_navi(&actor, nullptr, 5), "missing captain rejected");
    navi.alive = false;
    check(!pc_p2_mamuta_hit_navi(&actor, &navi, 5), "dead captain rejected");
    navi.alive = true;
    for (float damage : {0.0f, -1.0f, std::numeric_limits<float>::quiet_NaN()})
        check(!pc_p2_mamuta_hit_navi(&actor, &navi, damage), "nonpositive or NaN damage rejected");
    check(navi.calls == 0, "invalid hit never dispatched");
    navi.accepts = false;
    check(!pc_p2_mamuta_hit_navi(&actor, &navi, 5), "receiver rejection propagated");
    check(navi.calls == 1 && navi.owner == &actor && navi.damage == 5, "rejected hit still uses receiver");
    check(navi.mHealth == 100, "dispatcher never changes health on rejected hit");
    navi.accepts = true;
    check(pc_p2_mamuta_hit_navi(&actor, &navi, 7.5f), "receiver acceptance propagated");
    check(navi.calls == 2 && navi.owner == &actor && navi.damage == 7.5f, "configured damage and owner preserved");
    check(navi.mHealth == 100, "receiver exclusively owns accepted health change");
    const std::string root = argc > 1 ? argv[1] : P2_MAMUTA_SOURCE_ROOT;
    for (const char* file : {"pc_port/pc_p2_mamuta_fsm.cpp", "pc_port/pc_p2_mamuta_rules.cpp"}) {
        std::ifstream in(root + "/" + file);
        check(bool(in), "production source available");
        std::ostringstream text; text << in.rdbuf();
        const std::string source = text.str();
        check(source.find("pc_p2_mamuta_hit_navi(") != std::string::npos, "production path dispatches through tested helper");
        check(source.find("navi->mHealth -=") == std::string::npos, "production path has no raw health subtraction");
        check(source.find("navi->startDamageEffect()") == std::string::npos, "dispatcher does not bypass receiver effects");
    }
    std::printf("%s p2_mamuta_navi_hit_test checks=%d\n", failures ? "FAIL" : "PASS", checks);
    return failures ? 1 : 0;
}
