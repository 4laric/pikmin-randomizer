// Standalone probe for the batch-2 sampled-clock consumer adoption (#431).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_batch2_clock.cpp -o p2_batch2_clock.exe
//
// Validates that the converted clock clip preserves the legacy uniform pose
// selection and that the cursor delivers authored events exactly once per
// forward crossing, independently of which pose is displayed.
#include "../pc_port/pc_p2_batch2_clock.h"

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {

int failures = 0;

bool check(bool ok, const char* what) {
    if (!ok) {
        std::fprintf(stderr, "FAIL %s\n", what);
        ++failures;
    }
    return ok;
}

p2batch2clock::Row makeRow(const char* name, int frames, int poses,
                           std::vector<p2sampled::Event> events) {
    p2batch2clock::Row row;
    row.name = name;
    row.sourceFrames = frames;
    row.poseCount = poses;
    row.events = std::move(events);
    return row;
}

std::size_t countEvent(const std::vector<p2sampled::Occurrence>& events, const char* key) {
    std::size_t n = 0;
    for (const p2sampled::Occurrence& event : events) {
        if (event.key == key) {
            ++n;
        }
    }
    return n;
}

void testUniformProjection() {
    p2batch2clock::Row row = makeRow("move", 30, 10, {});
    p2sampled::Clip clip = p2batch2clock::makeClip(row);
    check(clip.valid(), "uniform clip valid");

    p2animation::Clip legacy;
    legacy.name = "move";
    legacy.count = 10;
    legacy.duration = 30;  // frames empty => uniform compatibility path

    for (int i = 0; i <= 40; ++i) {
        const float phase = float(i) / 40.f;
        const double source = double(phase) * double(clip.poses.duration - 1);
        check(clip.poseIndex(source) == legacy.index(phase), "uniform projection matches legacy");
    }

    check(clip.poseIndex(-5.0) == legacy.index(0.f), "negative source clamps");
    check(clip.poseIndex(1e9) == legacy.index(1.f), "overflow source clamps");
}

void testParseEvents() {
    std::vector<p2sampled::Event> events;
    check(p2batch2clock::parseEvents("-", events), "dash event token");
    check(events.empty(), "no events for dash");

    events.clear();
    check(p2batch2clock::parseEvents("3:attack,10:die", events), "parse event list");
    check(events.size() == 2, "two events");
    check(events[0].frame == 3 && events[0].key == "attack", "first event frame/key");
    check(events[1].frame == 10 && events[1].key == "die", "second event frame/key");

    std::vector<p2sampled::Event> bad;
    check(!p2batch2clock::parseEvents("x:bad", bad), "reject non-numeric frame");
    check(!p2batch2clock::parseEvents("5", bad), "reject missing key");
    check(!p2batch2clock::parseEvents("5:", bad), "reject empty key");
}

void testExactlyOnce() {
    p2batch2clock::Row row = makeRow("attack", 20, 5,
                                     {p2sampled::Event{5, "hit"}, p2sampled::Event{12, "die"}});
    p2sampled::Clip clip = p2batch2clock::makeClip(row);
    check(clip.valid(), "event clip valid");

    p2batch2clock::Cursor cursor;
    check(cursor.start(clip), "cursor start");

    std::vector<p2sampled::Occurrence> firstCycle;
    const double samples[] = {0.0, 2.0, 5.0, 9.0, 13.0, 19.0};
    for (double frame : samples) {
        p2batch2clock::Step step = cursor.stepTo(frame);
        check(step.ok, "forward step ok");
        for (const auto& event : step.events) {
            firstCycle.push_back(event);
        }
    }
    check(countEvent(firstCycle, "hit") == 1, "hit fires exactly once per cycle");
    check(countEvent(firstCycle, "die") == 1, "die fires exactly once per cycle");

    std::vector<p2sampled::Occurrence> secondCycle;
    const double wrap[] = {1.0, 6.0, 13.0, 19.0};
    for (double frame : wrap) {
        p2batch2clock::Step step = cursor.stepTo(frame);
        check(step.ok, "wrap step ok");
        for (const auto& event : step.events) {
            secondCycle.push_back(event);
        }
    }
    check(countEvent(secondCycle, "hit") == 1, "hit refires next cycle only once");
    check(countEvent(secondCycle, "die") == 1, "die refires next cycle only once");
}

void testPoseEventIndependence() {
    p2batch2clock::Row row = makeRow("move", 40, 20, {p2sampled::Event{20, "step"}});
    p2sampled::Clip clip = p2batch2clock::makeClip(row);
    p2batch2clock::Cursor cursor;
    check(cursor.start(clip), "independent cursor start");

    bool poseChangedWithoutEvent = false;
    std::size_t lastPose = cursor.stepTo(0.0).pose;
    for (double frame = 1.0; frame <= 19.0; frame += 1.0) {
        p2batch2clock::Step step = cursor.stepTo(frame);
        check(step.ok, "independence step ok");
        check(step.events.empty(), "no event before crossing");
        if (step.pose != lastPose) {
            poseChangedWithoutEvent = true;
        }
        lastPose = step.pose;
    }
    check(poseChangedWithoutEvent, "pose changes with no event");

    p2batch2clock::Step crossing = cursor.stepTo(20.0);
    check(countEvent(crossing.events, "step") == 1, "event fires at crossing");
}

void testClipChangeRestart() {
    p2batch2clock::Row a = makeRow("wait", 10, 4, {});
    p2batch2clock::Row b = makeRow("move", 10, 4, {p2sampled::Event{0, "start"}});
    p2batch2clock::Cursor cursor;
    check(cursor.start(p2batch2clock::makeClip(a)), "first clip start");
    check(cursor.stepTo(3.0).ok, "first clip step");
    check(cursor.start(p2batch2clock::makeClip(b)), "clip change starts anew");
    p2batch2clock::Step step = cursor.stepTo(1.0);
    check(step.ok, "new clip step ok");
    check(countEvent(step.events, "start") == 1, "clip-entry event delivered once");
}

}  // namespace

int main() {
    testUniformProjection();
    testParseEvents();
    testExactlyOnce();
    testPoseEventIndependence();
    testClipChangeRestart();
    if (failures == 0) {
        std::printf("PASS p2_batch2_clock\n");
        return 0;
    }
    std::fprintf(stderr, "FAIL p2_batch2_clock: %d failures\n", failures);
    return 1;
}
