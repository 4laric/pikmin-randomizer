#include "../pc_port/pc_p2_sampled_clock.h"

#include <cmath>
#include <cstdio>
#include <sstream>
#include <string>

namespace {
int checks = 0;

bool check(bool value, const char* label)
{
    ++checks;
    if (value) return true;
    std::fprintf(stderr, "FAIL %s\n", label);
    return false;
}

p2sampled::Clip makeClip(const char* name, int duration, std::vector<int> frames,
                         std::vector<p2sampled::Event> events, double loopBegin = 0.0,
                         double loopEnd = -1.0)
{
    p2sampled::Clip clip;
    clip.poses.name = name;
    clip.poses.duration = duration;
    clip.poses.frames = std::move(frames);
    clip.poses.count = int(clip.poses.frames.size());
    clip.events = std::move(events);
    clip.loopBegin = loopBegin;
    clip.loopEnd = loopEnd;
    return clip;
}

std::string text(const std::vector<p2sampled::Occurrence>& events)
{
    std::string out;
    for (const auto& event : events) {
        if (!out.empty()) out += ',';
        out += std::to_string(event.frame) + ":" + event.key;
        if (out.size() > 96) break;
    }
    return out;
}
}  // namespace

int main()
{
    bool ok = true;

    // Pose selection and event exposure are independent.
    struct P {
        int frame;
        std::size_t pose;
    };
    const P projections[] = {
        {3, 0}, {7, 1}, {12, 1}, {15, 1}, {17, 2}, {27, 3}, {29, 3},
    };
    for (const P& row : projections) {
        auto clip = makeClip("proj", 30, {0, 10, 20, 29}, {{2, "intro"}, {12, "loop"}});
        p2sampled::Clock clock;
        ok &= check(clock.start(clip), "start projection clip");
        ok &= check(clock.seek(double(row.frame)), "seek projection clip");
        ok &= check(clock.poseIndex() == row.pose, "pose index is frame-only");
    }
    {
        auto clip = makeClip("proj", 30, {0, 10, 20, 29}, {{2, "intro"}, {12, "loop"}});
        p2sampled::Clock clock;
        clock.start(clip);
        ok &= check(text(clock.advance(3.0).events) == "2:intro", "crossed event is frame-only");
        ok &= check(clock.poseIndex() == 0, "pose at 3 is first pose");
        ok &= check(text(clock.advance(10.0).events) == "12:loop", "second crossing");
        ok &= check(clock.poseIndex() == 1, "pose at 13 is second pose");
    }

    // Equivalent split and combined advances emit the same events.
    {
        auto clip = makeClip("split", 30, {0, 10, 20, 29}, {{4, "a"}, {18, "b"}});
        p2sampled::Clock split, combined;
        split.start(clip);
        combined.start(clip);
        std::string splitText, combinedText;
        for (int i = 0; i < 10; ++i) splitText += text(split.advance(1.0).events);
        combinedText = text(combined.advance(10.0).events);
        ok &= check(splitText == combinedText, "split/combined events match");
        ok &= check(split.frame() == combined.frame() && split.frame() == 10.0,
                    "split/combined frame matches");
    }

    // Loop plays its intro once and repeats the loop region.
    {
        auto clip = makeClip("loop", 30, {0, 10, 20, 29}, {{2, "intro"}, {12, "loop"}}, 10, 30);
        p2sampled::Clock clock;
        clock.start(clip);
        std::string seen;
        for (int i = 0; i < 50; ++i) seen += text(clock.advance(1.0).events);
        int intro = 0, loop = 0;
        for (std::size_t at = 0; (at = seen.find("intro", at)) != std::string::npos; at += 5) ++intro;
        for (std::size_t at = 0; (at = seen.find("loop", at)) != std::string::npos; at += 4) ++loop;
        ok &= check(intro == 1, "loop intro fires once");
        ok &= check(loop == 2, "loop events fire per cycle");
        ok &= check(clock.cycle() == 2, "loop cycle count");
        ok &= check(clock.frame() >= 10.0 && clock.frame() < 30.0, "loop frame in region");
    }

    // One-shot completion clamps the pose frame.
    {
        auto clip = makeClip("done", 30, {0, 10, 20, 29}, {{29, "end"}});
        p2sampled::Clock clock;
        clock.start(clip);
        p2sampled::Batch batch = clock.advance(40.0);
        ok &= check(bool(batch) && batch.events.size() == 1 && batch.events[0].key == "end",
                    "one-shot end event");
        ok &= check(clock.finished(), "one-shot finished");
        ok &= check(clock.poseFrame() == 29.0 && clock.poseIndex() == 3, "finished pose clamped");
        ok &= check(clock.advance(5.0).events.empty(), "finished emits nothing further");
    }

    // Budget rejection changes no state.
    {
        auto clip = makeClip("budget", 1, {0}, {{0, "tick"}}, 0, 1);
        p2sampled::Clock clock;
        clock.start(clip);
        const double before = clock.frame();
        p2sampled::Batch batch = clock.advance(300.0);
        ok &= check(!batch && batch.error == p2sampled::Error::Budget, "budget rejected");
        ok &= check(clock.frame() == before && clock.cycle() == 0, "budget state preserved");
    }

    // Invalid input and invalid clips are refused without mutation.
    {
        auto bad = makeClip("bad", 10, {0, 4, 4}, {});
        p2sampled::Clock clock;
        ok &= check(!clock.start(bad), "unsorted poses refused");
        auto clip = makeClip("idle", 10, {0, 4}, {});
        clock.start(clip);
        ok &= check(clock.advance(-1.0).error == p2sampled::Error::InvalidAdvance,
                    "negative advance refused");
        ok &= check(clock.advance(std::nan("")).error == p2sampled::Error::InvalidAdvance,
                    "NaN advance refused");
        ok &= check(clock.frame() == 0.0, "invalid advance preserves state");
    }

    // Canonical text parses and drives the same selection.
    {
        std::istringstream in(
            "P2_ANIM_CLOCK_1 1\n"
            "clip move1 30 0 -1 4 2\n"
            "poses 0 10 20 29\n"
            "event 2 intro\n"
            "event 12 loop\n");
        std::vector<p2sampled::Clip> clips;
        const bool parsed = p2sampled::parse(in, clips);
        ok &= check(parsed, "canonical text parses");
        ok &= check(parsed && clips.size() == 1 && clips[0].poses.count == 4,
                    "canonical clip shape");
        p2sampled::Clock clock;
        clock.start(clips[0]);
        p2sampled::Batch batch = clock.advance(13.0);
        ok &= check(text(batch.events) == "2:intro,12:loop", "canonical events crossed");
        ok &= check(clock.poseIndex() == 1, "canonical pose selection");
        std::istringstream trailing("P2_ANIM_CLOCK_1 0 junk");
        std::vector<p2sampled::Clip> none;
        ok &= check(!p2sampled::parse(trailing, none), "trailing text refused");
    }

    if (ok) std::printf("PASS p2_sampled_clock: %d checks\n", checks);
    return ok ? 0 : 1;
}
