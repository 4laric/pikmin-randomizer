// Engine-free protocol consumer. Actual actor/save acceptance belongs to #1079.
#include "pc_randomizer.h"
#include "pc_p2_second_captain.h"
#include <cstdio>
int pc_p2_proxy_host(unsigned) { return -1; }
int main(int argc, char** argv)
{
    const bool initialized = pc_randomizer_init(argc, argv);
    std::printf("CAPTAIN_BOOTSTRAP enabled=%d second=%d requested=%d capacity=%d\n", initialized,
                pc_randomizer_second_captain(), pc_p2_captain::second_captain_requested(),
                pc_p2_captain::navi_capacity());
    return 0;
}
