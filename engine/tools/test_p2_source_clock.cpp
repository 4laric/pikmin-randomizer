#include "pc_p2_source_clock.h"
#include "pc_p2_bulblax_visual_policy.h"
#include "pc_p2_tank_phase.h"
#include <iostream>
#include <sstream>
#include <stdexcept>

using namespace p2source;
static int checks = 0;
static void require(bool ok) { ++checks; if (!ok) throw std::runtime_error("check " + std::to_string(checks)); }
static void ids(const Batch& b, std::initializer_list<unsigned> expected) {
    require(bool(b)); require(b.events.size() == expected.size());
    std::size_t i=0; for (unsigned id : expected) require(b.events[i++].id == id);
}
int main() {
    Clock clock;
    require(clock.advance(1).error == Error::Inactive);
    Clip once{10, false, 0, 0, {{0,1},{2,2},{2,3},{9,4}}};
    require(clock.start(once)); ids(clock.advance(0), {});
    clock.pause(true); ids(clock.advance(4), {}); require(clock.frame() == 0);
    clock.pause(false); ids(clock.advance(1), {1}); ids(clock.advance(1), {2,3});
    ids(clock.advance(0), {}); ids(clock.advance(7), {4});
    require(!clock.finished()); ids(clock.advance(100), {});
    require(clock.finished() && clock.frame() == 10 && clock.poseFrame() == 9);
    ids(clock.advance(100), {});

    require(clock.restart()); auto old = clock.advance(2); ids(old, {1,2,3});
    require(clock.seek(1)); require(!clock.current(old)); ids(clock.advance(1), {2,3});
    require(clock.seek(2)); ids(clock.advance(0.5), {}); // Seek never replays its destination.
    old = clock.advance(0); clock.cancel(); require(!clock.current(old));
    require(clock.start(once)); require(!clock.current(old));
    require(!clock.seek(-1)); require(!clock.seek(11));
    auto gen = clock.generation(); auto invalid = once; invalid.events[1].frame = -1;
    require(!clock.start(invalid)); require(clock.generation() == gen && clock.frame() == 0);
    invalid=once; invalid.events.push_back({1,9}); require(!Clock::valid(invalid));
    invalid=once; invalid.duration=0; require(!Clock::valid(invalid));
    invalid=once; invalid.events.resize(Clock::MaxEvents+1); require(!Clock::valid(invalid));
    require(clock.advance(-1).error == Error::InvalidAdvance);
    require(clock.advance(std::numeric_limits<double>::infinity()).error == Error::InvalidAdvance);
    require(clock.advanceSeconds(1, 0).error == Error::InvalidAdvance);
    require(clock.advanceSeconds(std::numeric_limits<double>::max(), 30).error == Error::InvalidAdvance);
    require(clock.frame() == 0);
    ids(clock.advanceSeconds(0.1, 20), {1,2,3}); require(clock.frame() == 2);

    Clip loop{10, true, 4, 8, {{0,1},{3,2},{4,3},{7,4}}};
    require(clock.start(loop)); auto b=clock.advance(9); ids(b,{1,2,3,4,3});
    require(clock.frame()==5 && clock.cycle()==1 && b.events.back().cycle==1);
    ids(clock.advance(7),{4,3,4,3}); require(clock.frame()==4 && clock.cycle()==3);
    invalid=loop; invalid.loopEnd=invalid.loopBegin; require(!Clock::valid(invalid));
    invalid=loop; invalid.events.push_back({9,5}); require(!Clock::valid(invalid));
    require(!clock.seek(8));
    Clock split, whole; require(split.start(loop) && whole.start(loop));
    auto all=whole.advance(40); std::vector<Occurrence> parts;
    for(int i=0;i<40;++i) {auto part=split.advance(1); parts.insert(parts.end(),part.events.begin(),part.events.end());}
    require(parts.size()==all.events.size());
    for(std::size_t i=0;i<parts.size();++i) require(parts[i].id==all.events[i].id && parts[i].cycle==all.events[i].cycle);
    require(split.frame()==whole.frame() && split.cycle()==whole.cycle());

    Clip tiny{1,true,0,1,{{0,1}}}; require(clock.start(tiny));
    b=clock.advance(Clock::MaxWraps+1); require(b.error==Error::Budget && b.events.empty());
    require(clock.frame()==0 && clock.cycle()==0); ids(clock.advance(1),{1,1});
    Clip crowded{2,true,0,2,{}};
    crowded.events.resize(Clock::MaxEvents, {0,1}); require(clock.start(crowded));
    b=clock.advance(2); require(b.error==Error::Budget && b.events.empty() && clock.frame()==0);
    b=clock.advance(1); require(bool(b) && b.events.size()==Clock::MaxEvents);

    // Real existing display parser/selector consumes the new clock without edits.
    // Event 42 is an engineering marker, not a claim about Queen attack metadata.
    std::istringstream profile("P2_BULBLAX_VISUAL_1 1 30 wait1 30 3 0 15 29 1 1 30 wait1 0 0 0 0");
    auto visual=p2bulblax::read(profile); const auto& bank=visual.clips[0];
    Clip display{double(bank.duration),true,0,double(bank.duration),{{10,42}}};
    require(clock.start(display)); b=clock.advance(12); ids(b,{42});
    require(bank.index(float(clock.poseFrame()))==1); // Pose 15, event at unsampled 10.
    ids(clock.advance(0),{}); require(bank.index(float(clock.poseFrame()))==1);
    ids(clock.advance(28),{42}); require(clock.frame()==10 && clock.cycle()==1);

    // Tank's P1 counter remains authoritative; feed the mapped positive delta.
    float mapped=0; require(p2tankvisual::frame(15,31,61,mapped) && mapped==30);
    require(clock.start(Clip{61,false,0,0,{{20,7}}})); ids(clock.advance(mapped),{7});
    require(clock.frame()==mapped); // No wall-clock drive in parallel.
    std::cout << "PASS source clock: " << checks << " checks, Bulblax/Tank consumer examples\n";
}
