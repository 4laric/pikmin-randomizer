#include "pc_p2_ivory_budget.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

int main() {
    P2IvoryBudget budget{2};
    for (int i = 0; i < 8; ++i) {
        assert(budget.accepts(true));
        budget.completed(true);
    }
    assert(budget.slots == 0 && budget.births == 8);
    assert(budget.accepts(false));
    // Allocation failure deliberately does not call completed().
    assert(budget.slots == 0 && budget.births == 8);
    budget.completed(false);
    budget.completed(true);
    assert(budget.slots == 1 && budget.births == 10);
    budget.completed(false);
    assert(!budget.accepts(false));
    assert(budget.accepts(true)); // refund a same-species input in this batch
    budget.completed(true);
    assert(budget.slots == 2 && budget.births == 12);
    // A subsequent callback after the last slot cannot resurrect an exhausted bud.
    P2IvoryBudget exhausted{2 - budget.slots};
    assert(!exhausted.accepts(true) && !exhausted.accepts(false));
    P2IvoryBudget invalid{-1};
    assert(!invalid.accepts(true) && !invalid.accepts(false));
}
