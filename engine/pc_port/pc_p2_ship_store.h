#pragma once
#include <istream>
#include <ostream>

// Separate from P1's three Onion compartments. Saved inside the same immutable
// generation as the native card, never in an independently committed sidecar.
namespace p2ship {
constexpr int Capacity = 100000;
struct Store {
    int counts[2][3] = {}; // Purple, White; Leaf, Bud, Flower
    static bool valid(int species, int maturity) {
        return species >= 3 && species <= 4 && maturity >= 0 && maturity < 3;
    }
    int total() const {
        int n = 0;
        for (const auto& row : counts) for (int c : row) n += c;
        return n;
    }
    bool add(int species, int maturity) {
        if (!valid(species, maturity) || total() >= Capacity) return false;
        ++counts[species - 3][maturity]; return true;
    }
    bool take(int species, int maturity) {
        if (!valid(species, maturity) || !counts[species - 3][maturity]) return false;
        --counts[species - 3][maturity]; return true;
    }
    bool read(std::istream& in) {
        Store next;
        for (auto& row : next.counts) for (int& c : row)
            if (!(in >> c) || c < 0 || c > Capacity) return false;
        if (next.total() > Capacity) return false;
        *this = next; return true;
    }
    void write(std::ostream& out) const {
        for (const auto& row : counts) for (int c : row) out << ' ' << c;
    }
};
inline Store stock;
}
