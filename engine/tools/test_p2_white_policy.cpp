#include "pc_p2_white_policy.h"
#include <cassert>
#include <limits>

int main(){
    assert(p2_white_stats_valid({2.f,1.f,1.5f,1.5f,.5f,1.f,.7f,.35f,120.f}));
    assert(!p2_white_stats_valid({0.99f,1.f,1.5f,1.5f,.5f,1.f,.7f,.35f,120.f}));
    assert(!p2_white_stats_valid({2.f,std::numeric_limits<float>::quiet_NaN(),1.5f,1.5f,.5f,1.f,.7f,.35f,120.f}));
}
