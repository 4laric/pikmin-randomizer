#include "pc_p2_mamuta_policy.h"

#include <cassert>
#include <cstddef>
#include <cstdio>
#include <vector>

// Lane 19 (#221) Mamuta source pose-bank policy test. Engine-free: no Shape,
// Graphics or Teki is constructed. The same p2mamuta::anchor/selectSample calls
// the live pc_p2_mamuta.cpp draw drives are exercised here.

namespace {

const int kStrikeSourceFrames = 24; // attack1 clip length, frames 0..23
const int kStrikeFrame = 4;         // attack1 strike event frame

// A representative dense ground-strike (attack1) bank: even source frames plus
// the attack1 event frames. The importer samples 8-10 poses per clip, which is
// why the bank cap had to rise.
std::vector<int> strikeBank()
{
    std::vector<int> frames;
    for (int f = 0; f < kStrikeSourceFrames; f += 2) frames.push_back(f);
    for (int e = 0; e < kStrikeSourceFrames; e += kStrikeFrame) { // event frames 0 and 4
        bool present = false;
        for (std::size_t i = 0; i < frames.size(); ++i)
            if (frames[i] == e) present = true;
        if (!present) {
            std::size_t at = 0;
            while (at < frames.size() && frames[at] < e) ++at;
            frames.insert(frames.begin() + std::ptrdiff_t(at), e);
        }
    }
    return frames;
}

void test_sampled_ground_strike_bank_non_empty()
{
    const std::vector<int> bank = strikeBank();
    assert(!bank.empty());
    assert(bank.size() <= std::size_t(p2mamuta::kMaxPoses)); // bank count <= cap
    bool hasStrike = false;
    for (std::size_t i = 0; i < bank.size(); ++i) {
        assert(bank[i] >= 0 && bank[i] < kStrikeSourceFrames);
        if (i) assert(bank[i] > bank[i - 1]); // strictly ascending source frames
        if (bank[i] == kStrikeFrame) hasStrike = true;
    }
    assert(hasStrike);
    // The ground strike is the Attack1 clip and the bank carries its frames.
    assert(p2mamuta::anchor(24, 10, false) == p2mamuta::Attack1);
    assert(p2mamuta::anchor(24, 11, false) == p2mamuta::Attack1);
    assert(p2mamuta::anchor(24, 12, false) == p2mamuta::Attack1);
}

void test_strike_frame_equals_source_frame_index()
{
    const std::vector<int> bank = strikeBank();
    const int poses = int(bank.size());
    const int selected = p2mamuta::selectSample(float(kStrikeFrame), bank.data(), poses);
    assert(selected >= 0 && selected < poses);
    // Strike timing is the source-frame timeline: the sampled pose whose source
    // frame equals the event frame is the one selected, not a uniform index.
    assert(bank[selected] == kStrikeFrame);

    assert(bank[p2mamuta::selectSample(0.0f, bank.data(), poses)] == 0);
    assert(bank[p2mamuta::selectSample(float(kStrikeSourceFrames - 2), bank.data(), poses)]
           == kStrikeSourceFrames - 2);
    // Between frames it snaps to the nearer sample; a tie keeps the earlier one.
    assert(bank[p2mamuta::selectSample(5.0f, bank.data(), poses)] == 4);
    // Past the end clamps to the last sampled pose.
    assert(p2mamuta::selectSample(float(kStrikeSourceFrames + 50), bank.data(), poses) == poses - 1);
}

void test_bank_count_cap()
{
    static_assert(p2mamuta::kMaxPoses >= 8, "dense banks hold at least 8 poses");

    std::vector<int> frames;
    for (int i = 0; i <= p2mamuta::kMaxPoses; ++i) frames.push_back(i);
    // A bank over the cap is refused, not silently walked.
    assert(p2mamuta::selectSample(0.0f, frames.data(), int(frames.size())) == -1);
    // A usable bank at the cap is accepted.
    assert(p2mamuta::selectSample(0.0f, frames.data(), p2mamuta::kMaxPoses) == 0);
    // Empty and null banks are refused.
    assert(p2mamuta::selectSample(0.0f, nullptr, 0) == -1);
    assert(p2mamuta::selectSample(0.0f, nullptr, 3) == -1);
}

void test_anchor_motion_mapping()
{
    assert(p2mamuta::anchor(23, 2, false) == -1);             // not a Miurin
    assert(p2mamuta::anchor(24, 0, false) == p2mamuta::Dead); // corpse motion
    assert(p2mamuta::anchor(24, 2, true) == p2mamuta::Dead);  // corpse flag
    assert(p2mamuta::anchor(24, 2, false) == p2mamuta::Wait);
    assert(p2mamuta::anchor(24, 4, false) == p2mamuta::WaitAct);
    assert(p2mamuta::anchor(24, 6, false) == p2mamuta::Move);
    assert(p2mamuta::anchor(24, 9, false) == p2mamuta::Flick);
    assert(p2mamuta::anchor(24, 13, false) == p2mamuta::Attack4);
    assert(p2mamuta::anchor(24, 14, false) == p2mamuta::Type5);
    assert(p2mamuta::anchor(24, 99, false) == -1);
}

} // namespace

int main()
{
    test_sampled_ground_strike_bank_non_empty();
    test_strike_frame_equals_source_frame_index();
    test_bank_count_cap();
    test_anchor_motion_mapping();
    std::puts("PASS P2_MAMUTA_POLICY");
    return 0;
}
