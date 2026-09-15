#include "pc_p2_fuefuki_motion.h"

#include <fstream>
#include <set>
#include <string>

namespace {
const char* kClips[] = {
    "dead", "landing", "landfail", "move", "pivot",
    "wait", "whisle", "struggle", "jump", "carry",
};
constexpr int kClipCount = 10;
} // namespace

bool p2_fuefuki_motion_load(const char* path, P2FuefukiMotionBank& bank)
{
    bank = P2FuefukiMotionBank();
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
        bank = P2FuefukiMotionBank();
        return false;
    }
    if (bank.table.motions.size() != static_cast<std::size_t>(kClipCount)) {
        bank = P2FuefukiMotionBank();
        return false;
    }
    std::set<std::string> names;
    for (const p2retail::Motion& motion : bank.table.motions) {
        names.insert(motion.name.substr(0, motion.name.size() - 4));
    }
    for (const char* clip : kClips) {
        if (!names.count(clip)) {
            bank = P2FuefukiMotionBank();
            return false;
        }
    }
    bank.loaded = true;
    return true;
}

const char* p2_fuefuki_motion_clip_for_state(int state)
{
    switch (state) {
    case 0: return "dead";      // Dead
    case 1: return "jump";      // Stay (airborne)
    case 2: return "landing";   // Land (event feed uses the real clip)
    case 3: return "jump";      // Jump
    case 4: return "wait";      // Wait
    case 5: return "pivot";     // Turn
    case 6: return "move";      // Walk
    case 7: return "whisle";    // Whisle
    case 8: return "struggle";  // Struggle
    }
    return "wait";
}

const p2retail::Motion* p2_fuefuki_motion_find(const P2FuefukiMotionBank& bank,
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
