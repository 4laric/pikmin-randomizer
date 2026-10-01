#include "pc_p2_demon_pose_bank.h"
#include <cassert>
#include <fstream>
int main(int argc, char** argv) {
    assert(argc == 1 || argc == 3);
    const char* input = argc == 3 ? argv[1] : "demon-pose-test.txt";
    const char* invalid = argc == 3 ? argv[2] : "demon-pose-invalid.txt";
    if (argc == 1) {
        std::ofstream out(input); out << "P2_DEMON_MOUTHS_1 " << std::string(64, 'a') << " 2\n";
        for (int frame : {0, 17}) { out << frame; for (int i=0; i<24; ++i) out << ' ' << frame+i; out << '\n'; }
    }
    P2DemonPoseBank bank;
    assert(bank.load(input));
    const auto* zero = bank.exact(0);
    const auto* hit = bank.exact(17);
    assert(zero && hit && !bank.exact(18));
    const auto saved = hit->values;
    assert(zero->values != saved);
    { std::ofstream bad(invalid); bad << "P2_DEMON_MOUTHS_1 " << std::string(64, 'a') << " 129"; }
    assert(!bank.load(invalid));
    assert(bank.exact(17)->values == saved);
    { std::ofstream bad(invalid); bad << "P2_DEMON_MOUTHS_1 " << std::string(64, 'a') << " 1 0 nan"; }
    assert(!bank.load(invalid));
    assert(bank.exact(17)->values == saved);
    if (argc == 1) { std::remove(input); std::remove(invalid); }
}
