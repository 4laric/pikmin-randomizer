// Dense Empress Bulblax / larva pose bank (#972). Engine-free; necessary, never
// admission evidence. Covers: the 24 poses-per-clip bound in both parsers, the
// extractor's frame layout (pikmin2_animation.sample_frames) satisfying the
// shared pose-family contract, and the shared p2pose/p2motion blend the Queen
// and larva draw now use (24 poses halve the nearest-pose error of the old 12).
#include "pc_p2_pose_motion.h"
#include "pc_p2_queen_own.h"
#include "pc_p2_queen_policy.h"

#include <cassert>
#include <cmath>
#include <cstdio>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace {
// pikmin2_animation.sample_frames(duration, limit)
std::vector<int> sampleFrames(int duration, int limit) {
    const int count = duration < limit ? duration : limit;
    std::vector<int> out;
    for (int i = 0; i < count; ++i)
        out.push_back(int(std::lround(double(i) * double(duration - 1) / double(count > 1 ? count - 1 : 1))));
    return out;
}
// p2posefamily::Bank::validFrames (P2_BANK_FRAMES_1: 0 first, duration-1 last, rising)
bool validFrames(const std::vector<int>& f, int duration) {
    if (f.empty() || f.front() != 0 || f.back() != duration - 1) return false;
    for (std::size_t i = 1; i < f.size(); ++i)
        if (f[i] <= f[i - 1]) return false;
    return true;
}
struct Row { const char* who; const char* name; int frames; };
const Row kClips[] = {{"queen", "dead", 140}, {"queen", "sleep", 210}, {"queen", "wait1", 30}, {"queen", "damage", 50},
                      {"queen", "flick", 60}, {"queen", "rolling_l", 110}, {"queen", "rolling_r", 110},
                      {"queen", "born", 28}, {"queen", "carry", 40}, {"baby", "dead", 100}, {"baby", "deadpress", 80},
                      {"baby", "move", 12}, {"baby", "attack", 70}, {"baby", "attackfail", 20}, {"baby", "born", 35}};

std::string bankText(int limit, int poseOverride = 0) {
    std::ostringstream out;
    out << "P2_QUEEN_BANK_1\n";
    for (const Row& r : kClips) {
        const std::vector<int> f = sampleFrames(r.frames, limit);
        out << "clip " << r.who << ' ' << r.name << ' ' << r.frames << " 0 " << (poseOverride ? poseOverride : int(f.size()));
        if (poseOverride) {
            for (int i = 0; i < poseOverride; ++i) out << ' ' << i;
        } else {
            for (int v : f) out << ' ' << v;
        }
        out << '\n';
    }
    out << "end\n";
    return out.str();
}
p2pose::Pose line(float x) { return p2pose::Pose{{{x, 0, 0}}, {{0, 1, 0}}}; }
}  // namespace

int main() {
    // 1. Native bank parser: 24 poses per clip accepted, 25 rejected.
    static_assert(p2queenown::kMaxPosesPerClip == 24 && p2queen::MaxPosesPerClip == 24, "dense default");
    {
        p2queenown::Bank bank;
        p2queenown::Params params;
        std::string error;
        std::istringstream in(bankText(24));
        assert(p2queenown::parseBank(in, bank, params, error));
        assert(bank.clip[p2queenown::AnimDead].poses.size() == 24);
        assert(bank.clip[p2queenown::AnimWait].poses.size() == 24);  // 30 source frames
        assert(bank.clip[p2queenown::AnimBorn].poses.size() == 24);  // 28 source frames
        assert(bank.baby[p2queenown::BabyAnimMove].poses.size() == 12);  // every source frame kept
        assert(bank.baby[p2queenown::BabyAnimAttackFail].poses.size() == 20);
        std::istringstream in25(bankText(24, 25));
        p2queenown::Bank other;
        assert(!p2queenown::parseBank(in25, other, params, error));
        assert(error.rfind("poses:", 0) == 0);
    }
    // 2. The old 12-pose bank still parses (a stale content cache is legal input).
    {
        p2queenown::Bank bank;
        p2queenown::Params params;
        std::string error;
        std::istringstream in(bankText(12));
        assert(p2queenown::parseBank(in, bank, params, error));
        assert(bank.clip[p2queenown::AnimDead].poses.size() == 12);
    }
    // 3. Extractor frame layout satisfies the pose-family frames contract at 24.
    for (const Row& r : kClips) {
        const std::vector<int> f = sampleFrames(r.frames, 24);
        assert(int(f.size()) == (r.frames < 24 ? r.frames : 24));
        assert(validFrames(f, r.frames));
    }
    // 4. Actor-profile policy (room preview): 24 accepted, 25 rejected.
    {
        auto config = [](int poses) {
            std::ostringstream out;
            out << "P2_QUEEN_ACTOR_1\n11\n";
            const struct { int enemy; const char* name; int frames; } rows[] = {
                {30, "dead", 140}, {30, "sleep", 210}, {30, "wait1", 30}, {30, "damage", 50}, {30, "flick", 60},
                {30, "rolling_l", 110}, {30, "rolling_r", 110}, {30, "born", 28}, {31, "born", 35},
                {31, "move", 12}, {31, "dead", 100}};
            for (const auto& r : rows) {
                const int n = poses < r.frames ? poses : r.frames;
                out << r.enemy << ' ' << r.name << ' ' << r.frames << ' ' << (poses > r.frames ? n : poses);
                for (int i = 0; i < (poses > r.frames ? n : poses); ++i) out << ' ' << i;
                out << '\n';
            }
            out << "1\n230010 default 1 0 0 0 0\n";
            return out.str();
        };
        std::istringstream ok(config(24));
        const p2queen::ActorConfig cfg = p2queen::readActorConfig(ok);
        assert(cfg.clip(30, "dead")->frames.size() == 24);
        bool threw = false;
        try {
            std::istringstream bad(config(25));
            p2queen::readActorConfig(bad);
        } catch (const std::runtime_error&) { threw = true; }
        assert(threw);
    }
    // 5. Shared blend on a Queen-sized clip: dead (140 frames), poses move
    // linearly with the source frame (x = 3 * frame). Lerp is exact; nearest
    // pose error is bounded by half the sampled-frame gap, and 24 poses halve it.
    {
        auto worstNearest = [](int limit) {
            const std::vector<int> f = sampleFrames(140, limit);
            std::vector<p2pose::Pose> poses;
            for (int v : f) poses.push_back(line(3.0f * float(v)));
            p2motion::Tunables tune;
            double worst = 0;
            for (int i = 0; i <= 139 * 4; ++i) {
                const float frame = float(i) / 4.0f;
                p2pose::Interval span;
                assert(p2motion::interval(f, frame, false, span));
                worst = std::fmax(worst, std::fabs(double(poses[span.left].positions[0].x) - 3.0 * double(frame)));
            }
            (void)tune;
            return worst;
        };
        const double sparse = worstNearest(12), dense = worstNearest(24);
        assert(dense < sparse * 0.6);

        const std::vector<int> f = sampleFrames(140, 24);
        std::vector<p2pose::Pose> poses;
        for (int v : f) poses.push_back(line(3.0f * float(v)));
        p2motion::Tunables tune;
        p2motion::Presenter presenter;
        auto at = [&](std::size_t i) -> const p2pose::Pose& { return poses[i]; };
        for (float frame : {0.0f, 3.25f, 47.5f, 100.7f, 139.0f}) {
            const p2motion::Shown shown = presenter.select("dead", poses.size(), at, f, frame, true, tune);
            assert(shown.pose && std::fabs(shown.pose->positions[0].x - 3.0f * frame) < 1e-3f);
            presenter.commit(*shown.pose);
        }
        // PIKMIN_P2_INTERPOLATION=0: same bank, nearest pose, no smoothing.
        tune.lerp = false;
        p2motion::Presenter nearest;
        const p2motion::Shown flat = nearest.select("dead", poses.size(), at, f, 47.5f, true, tune);
        assert(flat.pose && flat.span.left == flat.span.right);
        // Deterministic: the same frame always yields the same geometry.
        tune.lerp = true;
        p2motion::Presenter a, b;
        const auto sa = a.select("dead", poses.size(), at, f, 71.3f, true, tune);
        const auto sb = b.select("dead", poses.size(), at, f, 71.3f, true, tune);
        assert(sa.pose && sb.pose && sa.pose->positions[0].x == sb.pose->positions[0].x);
    }
    std::puts("p2_queen_pose_test ok");
    return 0;
}
