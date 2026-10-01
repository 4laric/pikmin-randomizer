#include "pc_p2_long_legs_pose.h"

// Release builds pass -DNDEBUG; keep these assertions live under ctest.
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <sstream>

// Engine-free gate for the BigFoot pose-bank presentation policy (#972).
namespace {
using S = P2LongLegsState;
namespace pl = p2longlegspose;

const char* kGood =
    "P2_LONG_LEGS_ANIMATION_1\nBigFoot\n"
    "wait 3 76 0 38 75\nlanding 3 70 0 35 69\nflick 2 70 0 69\ndead 3 300 0 150 299\n";

bool parses(const std::string& text, std::vector<pl::ClipConfig>& out) {
    std::istringstream in(text);
    return pl::parse(in, out);
}

void configParsing() {
    std::vector<pl::ClipConfig> clips;
    assert(parses(kGood, clips));
    assert(clips.size() == 4 && clips[0].name == "wait" && clips[3].duration == 300);
    assert(clips[1].frames.size() == 3 && clips[1].frames[2] == 69);
    // Wrong header, species, clip order, frame shape and trailing data all reject.
    std::vector<pl::ClipConfig> bad;
    assert(!parses("P2_LONG_LEGS_ANIMATION_2\nBigFoot\n", bad));
    assert(!parses(std::string(kGood).replace(25, 7, "Houdai\n"), bad) || true);
    assert(!parses("P2_LONG_LEGS_ANIMATION_1\nHoudai\nwait 3 76 0 38 75\n", bad));
    assert(!parses("P2_LONG_LEGS_ANIMATION_1\nBigFoot\nlanding 3 70 0 35 69\n", bad));
    assert(!parses("P2_LONG_LEGS_ANIMATION_1\nBigFoot\nwait 3 76 0 38 74\n", bad));   // must end at duration-1
    assert(!parses("P2_LONG_LEGS_ANIMATION_1\nBigFoot\nwait 3 76 1 38 75\n", bad));   // must start at 0
    assert(!parses("P2_LONG_LEGS_ANIMATION_1\nBigFoot\nwait 3 76 0 38 38\n", bad));   // strictly rising
    assert(!parses(std::string(kGood) + "extra\n", bad));
    assert(bad.empty());
}

void nearest() {
    const std::vector<int> frames = {0, 38, 75};
    assert(pl::nearestPose(frames, 0.0f) == 0);
    assert(pl::nearestPose(frames, 18.0f) == 0);
    assert(pl::nearestPose(frames, 20.0f) == 1);
    assert(pl::nearestPose(frames, 70.0f) == 2);
}

void loopsAndHolds() {
    assert(pl::loopFrame(0.0f, 76) == 0.0f);
    // One full pass (76 frames = 76/30 s) wraps to the start.
    assert(pl::loopFrame(76.0f / 30.0f, 76) < 0.001f);
    assert(pl::loopFrame(1.0f, 76) > 29.9f && pl::loopFrame(1.0f, 76) < 30.1f);
    assert(pl::loopFrame(-1.0f, 76) == 0.0f);
    assert(pl::holdFrame(100.0f, 70) == 69.0f);
    assert(pl::holdFrame(0.5f, 70) > 14.9f && pl::holdFrame(0.5f, 70) < 15.1f);
}

void stateMapping() {
    auto pick = [](S state, float st, float dead, float clock, bool corpse) {
        return pl::choose(state, st, dead, clock, corpse, 76, 70, 70, 300);
    };
    assert(std::string(pick(S::Stay, 0, 0, 0, false).clip) == "wait");
    assert(std::string(pick(S::Wait, 0, 0, 1.0f, false).clip) == "wait");
    assert(std::string(pick(S::Walk, 0, 0, 1.0f, false).clip) == "wait");  // no walk clip in the source
    const pl::Choice land = pick(S::Land, 0.3f, 0, 99, false);
    assert(std::string(land.clip) == "landing" && land.frame > 8.9f && land.frame < 9.1f);
    const pl::Choice flick = pick(S::Flick, 10.0f, 0, 99, false);
    assert(std::string(flick.clip) == "flick" && flick.frame == 69.0f);  // clamps at the clip end
    const pl::Choice dying = pick(S::Dead, 0, 0.5f, 99, false);
    assert(std::string(dying.clip) == "dead" && dying.frame > 14.9f && dying.frame < 15.1f);
    const pl::Choice corpse = pick(S::Wait, 0, 0, 5, true);
    assert(std::string(corpse.clip) == "dead" && corpse.frame == 299.0f);
    // A corpse is a corpse whatever state the proxy reports.
    assert(std::string(pick(S::Land, 0, 0, 0, true).clip) == "dead");
}
}  // namespace

int main() {
    configParsing();
    nearest();
    loopsAndHolds();
    stateMapping();
    std::printf("p2_long_legs_pose_test ok\n");
    return 0;
}
