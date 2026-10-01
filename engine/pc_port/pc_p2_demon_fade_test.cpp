// Bumbling Snitchbug (Demon 32) living-body smoothing regression. Engine-free.
// A clip change begins a crossfade whose time only moves when the owner calls
// advance(); the Demon update used to skip that call, so the body stayed at
// weight 0 on the previous clip's pose. Checks the Fade contract and that
// P2SaraiHost::updateDemon still advances the fade.
#include "pc_p2_pose_motion.h"

#include <cassert>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#ifndef DEMON_SOURCE
#error DEMON_SOURCE must name pc_p2_sarai_demon.cpp
#endif

namespace {
p2pose::Pose pose(float v) {
    p2pose::Pose p;
    p.positions.assign(3, p2pose::Vec{v, v, v});
    p.normals.assign(3, p2pose::Vec{0.f, 1.f, 0.f});
    return p;
}
} // namespace

int main() {
    p2motion::Fade fade;
    assert(fade.begin(pose(0.f), 0.15f));
    // Never advanced: the new clip never gains weight (the frozen-body defect).
    assert(fade.active() && fade.weight() == 0.f);
    p2pose::Pose out;
    assert(fade.mix(pose(1.f), out) && out.positions[0].x == 0.f);
    // Advanced from the simulation: reaches the new clip and finishes.
    fade.advance(0.075f);
    assert(fade.progress() > 0.49f && fade.progress() < 0.51f);
    fade.advance(0.1f);
    assert(fade.progress() == 1.f);
    assert(!fade.mix(pose(1.f), out) && !fade.active());

    std::ifstream in(DEMON_SOURCE);
    assert(in.good());
    std::stringstream ss; ss << in.rdbuf();
    const std::string src = ss.str();
    const std::size_t fn = src.find("void P2SaraiHost::updateDemon()");
    assert(fn != std::string::npos);
    const std::size_t adv = src.find("advanceSmooth(dt)", fn);
    const std::size_t startMotion = src.find("startDemonMotion(out.motion)", fn);
    assert(adv != std::string::npos && startMotion != std::string::npos && adv < startMotion);
    std::puts("p2_demon_fade_test PASS");
    return 0;
}
