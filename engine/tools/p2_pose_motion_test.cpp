// Unit tests for the central P2 pose-playback helpers (#895):
// nearest rounding, move/wait hysteresis, crossfade progression, Shape slots
// and loop-endpoint bracketing.
#include "pc_p2_pose_motion.h"
#include "pc_p2_animation.h"
#include "pc_p2_batch2_clock.h"

#include <cmath>
#include <cstdlib>
#include <iostream>

namespace {
unsigned checks = 0;
void require(bool ok, const char* what) {
    ++checks;
    if (!ok) {
        std::cerr << "FAIL " << checks << ": " << what << '\n';
        std::exit(1);
    }
}
bool near(float a, float b) { return std::fabs(a - b) < 1e-4f; }
p2pose::Pose pose(float x) { return p2pose::Pose{{{x, 0, 0}}, {{1, 0, 0}}}; }
}  // namespace

int main() {
    // Nearest rounding (never truncation).
    require(p2motion::nearestIndex(0.f, 3) == 0, "phase 0");
    require(p2motion::nearestIndex(0.24f, 3) == 0, "0.24 -> 0");
    require(p2motion::nearestIndex(0.26f, 3) == 1, "0.26 -> 1 (truncation gave 0)");
    require(p2motion::nearestIndex(0.9f, 3) == 2, "0.9 -> 2 (truncation gave 1)");
    require(p2motion::nearestIndex(1.f, 3) == 2, "phase 1");
    require(p2motion::nearestIndex(2.f, 3) == 2, "clamped high");
    require(p2motion::nearestIndex(NAN, 3) == 0, "nan");
    require(p2motion::nearestIndex(.7f, 1) == 0, "single pose");
    p2animation::Clip v1;
    v1.count = 3;
    v1.duration = 60;
    require(v1.index(0.9f) == 2, "Clip::index v1 rounds");
    require(v1.index(0.2f) == 0, "Clip::index v1 low");
    require(v1.index(0.1f, true) == 2, "corpse holds last");

    // Move/wait hysteresis + dwell.
    p2motion::Tunables t;
    t.moveEnter = 1.5f;
    t.moveLeave = 0.5f;
    t.minDwellSeconds = 0.25f;
    p2motion::MoveGate gate;
    require(!gate.update(1.2f, 1 / 30.f, t) && !gate.moving(), "below enter stays wait");
    require(gate.update(2.f, 1 / 30.f, t) && gate.moving(), "enter move");
    require(!gate.update(0.1f, 0.1f, t) && gate.moving(), "dwell holds move");
    require(!gate.update(1.0f, 0.2f, t) && gate.moving(), "between thresholds stays move");
    require(gate.update(0.2f, 0.1f, t) && !gate.moving(), "leave after dwell");
    require(!gate.update(1.4f, 1.f, t) && !gate.moving(), "hysteresis band stays wait");
    gate.reset();
    require(gate.update(3.f, 0.f, t) && gate.moving(), "fresh gate switches immediately");

    // Crossfade progression.
    p2motion::Fade fade;
    require(!fade.active() && near(fade.weight(), 1.f), "idle fade weight 1");
    require(!fade.begin(pose(0), 0.f) && !fade.active(), "zero duration disables");
    require(fade.begin(pose(0), 0.2f) && fade.active(), "begin");
    p2pose::Pose out;
    require(fade.mix(pose(10), out) && near(out.positions[0].x, 0.f), "t=0 shows old pose");
    fade.advance(0.1f);
    require(near(fade.progress(), 0.5f) && near(fade.weight(), 0.5f), "midpoint");
    require(fade.mix(pose(10), out) && near(out.positions[0].x, 5.f), "midpoint mix");
    fade.advance(0.05f);
    require(fade.weight() > 0.5f && fade.weight() < 1.f, "monotonic");
    fade.advance(1.f);
    require(!fade.mix(pose(10), out) && !fade.active(), "finished fade stops");
    require(fade.begin(pose(0), 0.2f), "restart");
    p2pose::Pose mismatched{{{0, 0, 0}, {1, 1, 1}}, {{1, 0, 0}, {1, 0, 0}}};
    require(!fade.mix(mismatched, out) && !fade.active(), "mismatched topology cancels");

    // Shape slots.
    auto slots = p2motion::shapeSlots(16, 4);
    require(slots.size() == 4 && slots.front() == 0 && slots.back() == 15, "slots spread");
    require(p2motion::isSlot(slots, 0) && p2motion::isSlot(slots, 15) && !p2motion::isSlot(slots, 1), "isSlot");
    require(p2motion::nearestSlot(slots, 1) == 0 && p2motion::nearestSlot(slots, 14) == 15, "nearestSlot");
    require(p2motion::shapeSlots(3, 4).size() == 3, "small clip loads all");
    require(p2motion::shapeSlots(5, 1).size() == 1, "one slot");
    require(p2motion::poseBytes(pose(0)) == 2 * sizeof(p2pose::Vec), "pose bytes");

    // Interval: lerp vs nearest; loop endpoints bracket exactly (dense banks
    // sample both frame 0 and duration-1, so a P1 loop wrap is continuous).
    const std::vector<int> frames = p2batch2clock::uniformFrames(16, 61);
    require(frames.front() == 0 && frames.back() == 60 && frames.size() == 16, "uniform endpoints");
    p2pose::Interval span;
    require(p2motion::interval(frames, 2.f, true, span) && span.left == 0 && span.right == 1 && near(span.weight, 0.5f),
            "lerp interval");
    require(p2motion::interval(frames, 3.f, false, span) && span.left == 1 && span.right == 1, "nearest interval");
    require(p2motion::interval(frames, 60.f, true, span) && span.left == 15 && span.right == 15, "loop end");
    require(p2motion::interval(frames, 0.f, true, span) && span.left == 0 && span.right == 0, "loop start");

    std::cout << "p2_pose_motion_test OK checks=" << checks << '\n';
    return 0;
}
