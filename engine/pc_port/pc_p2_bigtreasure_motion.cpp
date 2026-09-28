#include "pc_p2_bigtreasure_motion.h"

#include <fstream>
#include <set>
#include <string>

namespace {
const char* kClips[] = {
    "appear", "appear2", "wait1", "preattackf", "attackf", "attackendf",
    "preattackfr", "attackfr", "attackendfr", "preattackfl", "attackfl",
    "attackendfl", "preattackfb", "attackfb", "attackendfb", "preattackw",
    "attackw", "attackendw", "preattackg", "attackg", "attackendg",
    "preattacke", "attacke", "attackende", "dropitem", "wait2", "flick",
    "dead", "move1",
};
constexpr int kClipCount = 29;
} // namespace

bool p2_bigtreasure_motion_load(const char* path, P2BigTreasureMotionBank& bank)
{
    bank = P2BigTreasureMotionBank();
    if (!path || !*path) {
        return false;
    }
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        return false;
    }
    try {
        bank.table = p2retail::read(input);
    } catch (const std::exception&) {
        bank = P2BigTreasureMotionBank();
        return false;
    }
    if (bank.table.motions.size() != kClipCount) {
        bank = P2BigTreasureMotionBank();
        return false;
    }
    std::set<std::string> names;
    for (const p2retail::Motion& motion : bank.table.motions) {
        names.insert(motion.name.substr(0, motion.name.size() - 4));
    }
    for (const char* clip : kClips) {
        if (!names.count(clip)) {
            bank = P2BigTreasureMotionBank();
            return false;
        }
    }
    bank.loaded = true;
    return true;
}

const p2retail::Motion* p2_bigtreasure_motion_find(const P2BigTreasureMotionBank& bank,
                                                   const char* name)
{
    if (!bank.loaded || !name) {
        return nullptr;
    }
    const std::string wanted = std::string(name) + ".bca";
    for (const p2retail::Motion& motion : bank.table.motions) {
        if (motion.name == wanted) {
            return &motion;
        }
    }
    return nullptr;
}
