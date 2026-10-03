#include "pc_p2_original_piki_init.h"
#include <cstdio>
#include <stdexcept>
#include <thread>
class Piki {};
namespace {
unsigned checks = 0;
void check(bool value) {
    ++checks;
    if (!value) throw std::runtime_error("original Piki initialization scope control failed");
}
}
int main() {
    Piki first, second;
    check(!pc_p2_original_piki_init_consume(&first));
    check(!pc_p2_original_piki_init_held(&first));
    check(!pc_p2_original_piki_init_held(nullptr));
    check(!pc_p2_original_piki_free_init_consume(&first));
    check(!pc_p2_original_piki_bore_init_consume(&first));
    {
        PcOriginalPikiInitScope invalid(nullptr);
        check(!invalid.valid());
        check(!pc_p2_original_piki_init_consume(nullptr));
        PcOriginalPikiInitScope scope(&first);
        check(scope.valid() && !scope.consumed());
        check(!pc_p2_original_piki_init_held(&first));
        check(!pc_p2_original_piki_free_init_consume(&first));
        check(!pc_p2_original_piki_bore_init_consume(&first));
        {
            PcOriginalPikiInitScope nested(&second);
            check(!nested.valid());
            check(!pc_p2_original_piki_init_consume(&second));
        }
        check(!pc_p2_original_piki_init_consume(&second));
        check(pc_p2_original_piki_init_consume(&first));
        check(scope.consumed());
        check(pc_p2_original_piki_init_held(&first));
        check(!pc_p2_original_piki_init_held(&second));
        check(!pc_p2_original_piki_free_init_consume(&second));
        check(!pc_p2_original_piki_bore_init_consume(&first));
        check(pc_p2_original_piki_free_init_consume(&first));
        check(!pc_p2_original_piki_free_init_consume(&first));
        check(!pc_p2_original_piki_bore_init_consume(&second));
        check(pc_p2_original_piki_bore_init_consume(&first));
        check(!pc_p2_original_piki_bore_init_consume(&first));
        check(!pc_p2_original_piki_init_consume(&first));
        PcOriginalPikiInitScope afterConsumed(&second);
        check(!afterConsumed.valid());
        bool otherThread = false;
        std::thread worker([&] {
            if (pc_p2_original_piki_init_consume(&first)) return;
            PcOriginalPikiInitScope local(&second);
            otherThread = local.valid() && pc_p2_original_piki_init_consume(&second);
        });
        worker.join();
        check(otherThread);
        check(!pc_p2_original_piki_init_consume(&second));
    }
    check(!pc_p2_original_piki_init_consume(&first));
    check(!pc_p2_original_piki_init_held(&first));
    check(!pc_p2_original_piki_free_init_consume(&first));
    check(!pc_p2_original_piki_bore_init_consume(&first));
    try {
        PcOriginalPikiInitScope scope(&second);
        check(scope.valid());
        throw 1; // Simulated physical init exception, distinct from assertions.
    } catch (int) {}
    check(!pc_p2_original_piki_init_consume(&second));
    {
        PcOriginalPikiInitScope recycled(&second);
        check(recycled.valid());
        check(pc_p2_original_piki_init_consume(&second));
    }
    check(!pc_p2_original_piki_init_consume(&second));
    std::printf("PASS original Piki exact-body initialization scope %u controls\n", checks);
}
