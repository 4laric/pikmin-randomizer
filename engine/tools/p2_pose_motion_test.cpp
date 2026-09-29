// Unit tests for the central P2 pose-playback helpers (#895):
// nearest rounding, move/wait hysteresis (legacy enter threshold), crossfade
// progression, Shape slots, loop-endpoint bracketing, loop-seam continuity,
// P1 loop-wrap presentation and stale-display fade guards.
#include "pc_p2_pose_motion.h"
#include "pc_p2_animation.h"
#include "pc_p2_batch2_clock.h"

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <vector>

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

    // Defaults: entering move keeps the legacy `speed2 > 1` threshold; the
    // 0.5..1.0 band is the hysteresis for an actor already moving.
    {
        const p2motion::Tunables d;
        require(near(d.moveEnter, 1.f) && near(d.moveLeave, .5f), "legacy enter threshold");
        p2motion::MoveGate g;
        require(!g.update(1.f, 1.f, d) && !g.moving(), "speed2 == 1 stays wait (legacy strict >)");
        require(g.update(1.01f, 1.f, d) && g.moving(), "speed2 > 1 enters move (legacy)");
        require(!g.update(.7f, 1.f, d) && g.moving(), "slow actor already moving keeps move");
        require(g.update(.4f, 1.f, d) && !g.moving(), "below leave returns to wait");
    }

    // Loop seam (#895): retail P2 loops step duration-1 -> 0 in one source
    // frame (scripts/p2_loop_seam_audit.py). A seam no larger than a few
    // per-frame steps is continuous; a jump (one-shot act, root-motion flight)
    // gets a wrap blend.
    {
        // A cyclic sway whose last frame is one step before frame 0, versus a
        // root-motion clip that moves 1 unit per frame and jumps back 59.
        std::vector<p2pose::Pose> sway, jump;
        const std::vector<int> f16 = p2batch2clock::uniformFrames(16, 60);
        for (int i = 0; i < 16; ++i) {
            const float t = float(f16[size_t(i)]) / 60.f * 6.2831853f;
            sway.push_back(pose(10.f * std::sin(t)));
            jump.push_back(pose(float(f16[size_t(i)])));
        }
        auto at = [](const std::vector<p2pose::Pose>& v) {
            return [&v](std::size_t i) -> const p2pose::Pose& { return v[i]; };
        };
        require(p2motion::seamContinuous(sway.size(), at(sway), f16), "cyclic sway seam continuous");
        require(!p2motion::seamContinuous(jump.size(), at(jump), f16), "root-motion seam discontinuous");
        std::vector<p2pose::Pose> still(16, pose(3.f));
        require(p2motion::seamContinuous(still.size(), at(still), f16), "still clip never flagged");
        require(p2motion::seamContinuous(1, at(still), {0}), "single pose trivially continuous");

        require(p2motion::isWrap(58.f, 1.f, 59), "wrap detected");
        require(!p2motion::isWrap(20.f, 22.f, 59), "forward is not a wrap");
        require(!p2motion::isWrap(30.f, 25.f, 59), "small backstep is not a wrap");
        require(!p2motion::isWrap(-1.f, 0.f, 59), "first draw is not a wrap");

        // Presenter across a P1 wrap. Continuous seam: no fade, frame 0 shows
        // at once and the last -> first step is one ordinary sway step.
        p2motion::Tunables tn;
        tn.crossfadeSeconds = 0.2f;
        p2motion::Presenter view;
        p2motion::Shown sh = view.select("wait", sway.size(), at(sway), f16, 55.f, true, tn);
        require(sh.pose && !sh.crossfadeStarted && !sh.wrapBlend, "first draw: no fade");
        view.commit(*sh.pose);
        view.advance(1 / 30.f);
        sh = view.select("wait", sway.size(), at(sway), f16, 59.f, true, tn);
        view.commit(*sh.pose);
        const float atEnd = sh.pose->positions[0].x;
        view.advance(1 / 30.f);
        sh = view.select("wait", sway.size(), at(sway), f16, 0.f, true, tn);
        require(sh.pose && !sh.wrapBlend && !view.fade.active(), "continuous seam wraps without a blend");
        require(near(sh.pose->positions[0].x, 0.f), "wrap shows frame 0");
        const float swayStep = 10.f * 6.2831853f / 60.f;  // max |d/dframe| of the sway
        require(std::fabs(sh.pose->positions[0].x - atEnd) <= 1.5f * swayStep, "wrap step is one ordinary step");
        view.commit(*sh.pose);

        // Discontinuous seam: the wrap blends from the displayed end pose.
        p2motion::Presenter rm;
        sh = rm.select("fly", jump.size(), at(jump), f16, 59.f, false, tn);
        rm.commit(*sh.pose);
        rm.advance(1 / 30.f);
        sh = rm.select("fly", jump.size(), at(jump), f16, 0.f, false, tn);
        require(sh.pose && sh.wrapBlend && rm.fade.active(), "discontinuous seam starts a wrap blend");
        require(near(sh.pose->positions[0].x, 59.f), "wrap blend starts from the displayed pose (no pop)");
        rm.commit(*sh.pose);
        rm.advance(0.1f);
        sh = rm.select("fly", jump.size(), at(jump), f16, 3.f, false, tn);
        require(sh.pose->positions[0].x > 3.f && sh.pose->positions[0].x < 59.f, "wrap blend in progress");
        rm.commit(*sh.pose);
        rm.advance(0.2f);
        sh = rm.select("fly", jump.size(), at(jump), f16, 9.f, false, tn);
        require(near(sh.pose->positions[0].x, 9.f) && !rm.fade.active(), "wrap blend completes");

        // Clip change crossfades from a fresh display...
        p2motion::Presenter cf;
        sh = cf.select("wait", sway.size(), at(sway), f16, 15.f, true, tn);
        cf.commit(*sh.pose);
        const float shownX = sh.pose->positions[0].x;
        cf.advance(1 / 30.f);
        sh = cf.select("move", jump.size(), at(jump), f16, 40.f, true, tn);
        require(sh.crossfadeStarted && near(sh.pose->positions[0].x, shownX), "clip change fades from display");
        cf.commit(*sh.pose);
        // ...but never from a stale one (actor off-screen for a while).
        cf.advance(1.f);
        require(!cf.fresh(), "display goes stale while not drawn");
        sh = cf.select("wait", sway.size(), at(sway), f16, 30.f, true, tn);
        require(!sh.crossfadeStarted && !cf.fade.active() && sh.pose == &cf.scratch,
                "stale display: direct switch, no fade");
        cf.commit(*sh.pose);
        // A fade in flight is dropped (not finished from stale data) once the
        // actor stops being drawn for longer than the stale window (a 5 s fade
        // would still be running after 1 s).
        tn.crossfadeSeconds = 5.f;
        cf.advance(1 / 30.f);
        sh = cf.select("move", jump.size(), at(jump), f16, 10.f, true, tn);
        require(sh.crossfadeStarted && cf.fade.active(), "fade in flight");
        cf.commit(*sh.pose);
        cf.advance(1.f);
        sh = cf.select("move", jump.size(), at(jump), f16, 12.f, true, tn);
        require(!cf.fade.active() && near(sh.pose->positions[0].x, 12.f), "stale fade dropped");
    }

    // Death clips that collapse to a point (retail Sokkuri/UmiMushi/Snake
    // dead): playback and the corpse stop at the last visible pose.
    {
        auto blob = [](float s) {
            return p2pose::Pose{{{-s, 0, 0}, {s, 2 * s, s}}, {{1, 0, 0}, {1, 0, 0}}};
        };
        std::vector<p2pose::Pose> shrink{blob(10), blob(9), blob(6), blob(1), blob(0.0001f)};
        auto at = [&shrink](std::size_t i) -> const p2pose::Pose& { return shrink[i]; };
        require(p2motion::visibleEnd(shrink.size(), at) == 2, "collapsed tail excluded (6 >= 20% of 10, 1 < 20%)");
        std::vector<p2pose::Pose> steady{blob(10), blob(9), blob(10)};
        auto st = [&steady](std::size_t i) -> const p2pose::Pose& { return steady[i]; };
        require(p2motion::visibleEnd(steady.size(), st) == 2, "no collapse keeps the last pose");
        require(p2motion::isDeathClip("dead") && p2motion::isDeathClip("dead1") && p2motion::isDeathClip("pdead1")
                    && p2motion::isDeathClip("dead_p") && !p2motion::isDeathClip("hide1")
                    && !p2motion::isDeathClip("wait1"),
                "death clip names");
    }

    std::cout << "p2_pose_motion_test OK checks=" << checks << '\n';
    return 0;
}
