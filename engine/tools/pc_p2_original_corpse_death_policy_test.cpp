#include "pc_p2_original_corpse_death_policy.h"
#include <cstdio>
using namespace p2original;
int main(){unsigned failures=0,checks=0;auto check=[&](bool ok,const char* text){++checks;if(!ok){++failures;std::printf("FAIL %s\n",text);}};
 const std::string catalog(64,'a');InstanceIdentity id{catalog,0x52000123u,0,1,1};CorpseDeathPolicy policy(catalog);std::string e;
 check(policy.ordinaryAllowed(id),"normal source activation retains corpse");
 check(policy.select(id,CorpseDeathCause::StoneShatter,e)&&!policy.ordinaryAllowed(id)&&policy.size()==1,"stone suppresses exact activation");
 check(policy.select(id,CorpseDeathCause::StoneShatter,e)&&policy.size()==1,"duplicate cause idempotent");
 auto next=id;++next.epoch;check(policy.ordinaryAllowed(next),"next respawn remains ordinary");
 next=id;++next.activation;check(policy.ordinaryAllowed(next),"next activation remains ordinary");
 next=id;++next.ordinal;check(policy.ordinaryAllowed(next),"other instance remains ordinary");
 next=id;++next.generator;check(policy.ordinaryAllowed(next),"other generator remains ordinary");
 next=id;next.catalog=std::string(64,'b');check(!policy.select(next,CorpseDeathCause::StoneShatter,e)&&policy.size()==1,"cross catalog cause atomic refusal");
 check(!policy.select(id,static_cast<CorpseDeathCause>(2),e)&&policy.size()==1,"unknown cause atomic refusal");
 next=id;next.epoch=0;check(!policy.select(next,CorpseDeathCause::StoneShatter,e),"zero epoch refused");
 next=id;next.activation=0;check(!policy.select(next,CorpseDeathCause::StoneShatter,e),"zero activation refused");
 next=id;next.ordinal=10;check(!policy.select(next,CorpseDeathCause::StoneShatter,e),"out of catalog instance range refused");
 next=id;next.generator=1;check(!policy.select(next,CorpseDeathCause::StoneShatter,e),"non source UID refused");
 CorpseDeathPolicy fresh(catalog);check(fresh.ordinaryAllowed(id),"explicit fresh session clears policy");
 for(std::size_t i=2;i<=corpseSnapshotMaxRecords;++i){next=id;next.epoch=i;check(policy.select(next,CorpseDeathCause::StoneShatter,e),"bounded cause admission");}
 check(policy.size()==corpseSnapshotMaxRecords,"cause capacity exact");
 next=id;next.epoch=corpseSnapshotMaxRecords+1;check(!policy.select(next,CorpseDeathCause::StoneShatter,e)&&policy.ordinaryAllowed(next),"over cap refusal preserves new activation");
 check(policy.select(id,CorpseDeathCause::StoneShatter,e),"duplicate still accepted at cap");
 std::printf("%s P2_ORIGINAL_CORPSE_DEATH_POLICY checks=%u failures=%u\n",failures?"FAIL":"PASS",checks,failures);return failures?1:0;
}
