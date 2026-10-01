#pragma once
#include <istream>
namespace p2kingteki {
// P2_KING_TEKI_1 <count> <generator> <type>
// Binds the Emperor Bulblax (enemy 53) to one generated ordinary Teki host so
// ordinary free-Pikmin attacks reach it through the engine InteractAttack path.
// The host reuses the generated actor's TEKI type (Chappy=3 by default, the same
// carcass path the preview Pod already rebind-scans). Malformed input fails closed.
struct Binding { unsigned generator; int type; };
inline bool read(std::istream& in, Binding& out) {
    std::string magic, tail; int count;
    if (!(in >> magic >> count) || magic != "P2_KING_TEKI_1" || count != 1) return false;
    if (!(in >> out.generator >> out.type) || out.generator == 0) return false;
    return !(in >> tail);
}
}
