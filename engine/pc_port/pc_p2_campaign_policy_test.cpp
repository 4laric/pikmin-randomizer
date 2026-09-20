#include "pc_p2_campaign_policy.h"
#include <cassert>
#include <initializer_list>
int main() {
    const unsigned sources[] = {9,23,44,54,57,59,60,61,62,78,79};
    const int hosts[] = {3,3,3,24,0,3,3,3,3,0,3};
    for (unsigned i=0;i<11;++i) {
        for (int original=0;original<34;++original) {
            assert(p2campaign::hostType(sources[i],original,false)==hosts[i]);
            assert(p2campaign::hostType(sources[i],original,true)==original);
        }
    }
    for (unsigned source: {0u,1u,41u,45u,58u,99u,999u})
        assert(p2campaign::hostType(source,17,false)==17);
}
