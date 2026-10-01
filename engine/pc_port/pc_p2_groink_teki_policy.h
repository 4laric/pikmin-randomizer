#pragma once
#include <istream>
#include <string>
#include "pc_p2_groink_carcass.h"

// Host-side binding descriptor for the Groink carcass sidecar.  Mirrors the
// family-sidecar config shape used by pc_p2_kurage_teki / pc_p2_mamuta: the
// room stager writes a one-line profile naming the generated actor to bind and
// the source carcass parameters (MiniHoudai fp11 gauge delay, fp12 respawn rate,
// max health).  The sidecar reads this at GameCoreSection::finalSetup.
namespace p2groink {
struct Binding {
    unsigned generator = 0;
    int type = 0;
    P2GroinkCarcassConfig carcass{};
    // Optional transport tail (lane 21 recipe): when the sidecar carries the
    // `transport` token, the corpse is driven to the Research Pod naturally
    // (free-mode grasp -> route -> delivery) instead of being regrown. Absent
    // for the natural-kill/short-gauge profile, which keeps its previous shape.
    bool transport = false;
};
// p2-groink-teki.txt:
//   P2_GROINK_TEKI_1
//   1
//   <generator> <type> <gaugeDelay> <recoverySeconds> <maxHealth> [transport]
inline bool read(std::istream& in, Binding& out) {
    std::string magic, tail;
    int count = 0;
    if (!(in >> magic >> count) || magic != "P2_GROINK_TEKI_1" || count != 1) return false;
    if (!(in >> out.generator >> out.type) || out.generator == 0) return false;
    if (!(in >> out.carcass.gaugeDelay >> out.carcass.recoverySeconds >> out.carcass.maxHealth)) return false;
    out.transport = false;
    if (in >> tail) {
        if (tail != "transport") return false;
        out.transport = true;
    }
    return true;
}
} // namespace p2groink
