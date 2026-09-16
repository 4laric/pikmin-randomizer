#pragma once
#include <istream>
namespace p2onikurage {
// Private sidecar binding for the bounded OniKurage host. The magic deliberately
// differs from Kurage's `P2_KURAGE_TEKI_1` so a fixture can select the Greater
// variant without a production manager key. `type` stays 0 because the bounded
// host reuses the generated actor's TEKI type (e.g. Frog) as a stand-in.
struct Binding { unsigned generator; int type; };
inline bool read(std::istream& in, Binding& out)
{
    std::string magic, tail;
    int count;
    if (!(in >> magic >> count) || magic != "P2_ONIKURAGE_TEKI_1" || count != 1) return false;
    if (!(in >> out.generator >> out.type) || out.generator == 0 || out.type != 0) return false;
    return !(in >> tail);
}
} // namespace p2onikurage
