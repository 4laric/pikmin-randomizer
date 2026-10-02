#include "pc_onion_transfer_policy.h"
#include <cassert>
#include <climits>
#include <cstdio>
using namespace pc_onion_transfer;
int main() {
    Counts c{30, 10000, 20, 100, 100, 100};
    assert(clamp(-10, c) == 0);             // field full when menu opens
    c.field = 90; assert(clamp(-10, c) == -10); // death/deposit frees space
    c.field = 98; assert(clamp(-10, c) == -2);  // births/pending exits shrink space
    c.field = 105; assert(clamp(-10, c) == 0 && clamp(0, c) == 0);
    assert(clamp(10, c) == 10);             // overfull field permits intended deposit
    c.squad = 3; assert(clamp(10, c) == 3); // eligible owner squad shrinks/death
    c.stock = 9999; assert(clamp(10, c) == 1);
    c.stock = 10001; assert(clamp(10, c) == 0); // no accidental withdrawal
    c = {3, 10000, 20, 100, 90, 100};
    assert(clamp(-10, c) == -3); c.stock = 15; assert(clamp(-10, c) == -10);
    // Two menus may select against the same free room. Confirmation reserves
    // space before the second closing menu revalidates in that authority tick.
    c = {20, 10000, 0, 100, 95, 100};
    const int first = clamp(-5, c); assert(first == -5);
    c.field -= first; c.stock += first;
    assert(clamp(-5, c) == 0);
    Counts otherOwner{20, 10000, 0, 50, 20, 50};
    assert(clamp(-5, otherOwner) == -5); // independent VS owner budget
    c = {INT_MAX, INT_MAX, 0, INT_MAX, 0, INT_MAX};
    assert(clamp(INT_MIN, c) == -INT_MAX);
    assert(clamp(-5, {-1, 10, -1, 10, -1, 10}) == 0);
    unsigned cases = 0;
    for (int stock=0; stock<6; ++stock) for (int squad=0; squad<6; ++squad)
    for (int field=0; field<8; ++field) for (int requested=-8; requested<=8; ++requested) {
        Counts limits{stock, 4, squad, 4, field, 4};
        const int result = clamp(requested, limits);
        assert(requested < 0 ? result <= 0 && result >= requested : result >= 0 && result <= requested);
        if (result < 0) {
            assert(stock + result >= 0 && squad - result <= 4 && field - result <= 4);
        } else if (result > 0) {
            assert(squad - result >= 0 && stock + result <= 4);
        }
        assert(clamp(result, limits) == result);
        ++cases;
    }
    std::printf("PASS onion transfer policy: %u exhaustive invariant cases plus live/race/VS/overflow scenarios\n", cases);
}
