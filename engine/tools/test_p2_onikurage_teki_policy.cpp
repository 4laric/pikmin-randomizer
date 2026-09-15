#include "pc_p2_onikurage_teki_policy.h"
#include <sstream>
int main()
{
    p2onikurage::Binding b{};
    std::istringstream ok("P2_ONIKURAGE_TEKI_1 1 7 0");
    if (!p2onikurage::read(ok, b) || b.generator != 7 || b.type != 0) return 1;
    for (const char* s : { "P2_ONIKURAGE_TEKI_1 2 7 0", "P2_ONIKURAGE_TEKI_1 1 7 3", "bad",
                           "P2_KURAGE_TEKI_1 1 7 0" }) {
        std::istringstream x(s);
        if (p2onikurage::read(x, b)) return 2;
    }
    std::istringstream zero("P2_ONIKURAGE_TEKI_1 1 0 0");
    if (p2onikurage::read(zero, b)) return 3;
    return 0;
}
