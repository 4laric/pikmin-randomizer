#include "pc_p2_original_corpse_ledger.h"
#include <cstdio>
#include <limits>
using namespace p2original;
int main(){
 unsigned checks=0, failures=0;
 auto check=[&](bool ok,const char* name){++checks;if(!ok){++failures;std::printf("FAIL %s\n",name);}};
 const std::string sha(64,'a');InstanceIdentity id{sha,0x52000123u,0,1,1};
 CorpseLedger ledger(sha);int pellet=0,other=0;std::uint64_t handle=0,second=123;
 std::string error;CorpseRecord record;unsigned grant=999;
 check(ledger.birth(&pellet,id,26,5,handle,error),"birth source corpse");
 check(ledger.lookup(&pellet,handle,record)&&!record.consumed&&record.yield==5,"birth never grants");
 check(!ledger.birth(&other,id,26,5,second,error)&&second==123,"duplicate logical identity");
 auto next=id;next.ordinal=1;
 check(!ledger.birth(&pellet,next,26,5,second,error)&&ledger.snapshot().records.size()==1,"duplicate pointer is atomic");
 check(!ledger.deliver(&pellet,handle+1,grant,error)&&grant==0,"stale handle no grant");
 check(!ledger.deliver(&other,handle,grant,error)&&grant==0,"unknown pointer no grant");
 // No actor registry/pointer is consulted here: native actor retirement cannot
 // erase the independently bound corpse receipt.
 check(ledger.deliver(&pellet,handle,grant,error)&&grant==5,"ordinary Onion yield");
 check(ledger.deliver(&pellet,handle,grant,error)&&grant==0,"duplicate suction no second yield");
 check(ledger.lookup(&pellet,handle,record)&&record.consumed,"consumed retained");
 check(!ledger.forgetPellet(&pellet,handle+1),"stale retirement refused");
 check(ledger.forgetPellet(&pellet,handle),"pellet retires");
 check(!ledger.rebind(&pellet,id,second,error),"consumed resurrection refused");
 check(!ledger.birth(&pellet,id,26,5,second,error),"consumed rebirth refused");
 check(ledger.birth(&pellet,next,26,5,second,error)&&second!=handle,"address reuse new identity");
 check(!ledger.deliver(&pellet,handle,grant,error)&&grant==0,"old address handle remains stale");
 check(ledger.forgetPellet(&pellet,second)&&ledger.rebind(&other,next,handle,error),"unconsumed detached rebind");
 check(!ledger.rebind(&pellet,next,second,error),"same receipt cannot have two pointers");

 const auto saved=ledger.snapshot();
 auto verifier=[&](const CorpseRecord& r,std::string& e){if(r.identity.generator!=id.generator||r.identity.ordinal>1||r.sourceType!=26||r.yield!=5){e="not an audited catalog corpse";return false;}return true;};
 std::vector<std::uint8_t> bytes;
 check(encodeCorpseSnapshot(saved,bytes,error)&&bytes.size()==146,"encode bounded schema1");
 CorpseSnapshot decoded;
 check(decodeCorpseSnapshot(bytes,decoded,error)&&decoded.records.size()==2&&decoded.records[0].consumed&&!decoded.records[1].consumed,"consumed and pending roundtrip");
 CorpseLedger resumed(sha);
 check(resumed.restore(decoded,verifier,error),"fresh authenticated-by-caller restore");
 check(!resumed.lookup(&other,handle,record),"addresses never restored");
 check(!resumed.rebind(&pellet,id,second,error),"consumed restored receipt refused");
 check(resumed.rebind(&pellet,next,second,error),"pending restored receipt bound");
 check(resumed.deliver(&pellet,second,grant,error)&&grant==5,"restored pending grants once");
 check(resumed.deliver(&pellet,second,grant,error)&&grant==0,"restored duplicate suppression");
 check(!resumed.restore(saved,verifier,error),"live ledger rewind refused");
 CorpseLedger wrong(std::string(64,'b'));
 check(!wrong.restore(saved,verifier,error)&&wrong.snapshot().records.empty(),"crosscatalog rejected");
 CorpseLedger rejected(sha);auto bad=saved;bad.records[1].yield=6;
 check(!rejected.restore(bad,verifier,error)&&rejected.snapshot().records.empty(),"profile mismatch atomic restore");
 check(!rejected.restore(saved,{},error),"missing verifier refused");
 check(rejected.restore(saved,verifier,error),"failure leaves clean restore target");
 auto checkBad=[&](CorpseSnapshot malformed,const char* name){CorpseLedger fresh(sha);std::vector<std::uint8_t> sentinel{99};check(!fresh.restore(malformed,verifier,error)&&fresh.snapshot().records.empty(),name);check(!encodeCorpseSnapshot(malformed,sentinel,error)&&sentinel==std::vector<std::uint8_t>{99},"failed encode unchanged");};
 bad=saved;bad.schema=2;checkBad(bad,"unknown schema");
 bad=saved;bad.records.push_back(bad.records[0]);checkBad(bad,"duplicate serialized ID");
 bad=saved;bad.records[0].identity.catalog=std::string(64,'b');checkBad(bad,"mixed catalog record");
 bad=saved;bad.records[0].identity.generator=42;checkBad(bad,"nonoriginal generator");
 bad=saved;bad.records[0].identity.ordinal=10;checkBad(bad,"invalid ordinal");
 bad=saved;bad.records[0].identity.epoch=0;checkBad(bad,"invalid epoch");
 bad=saved;bad.records[0].identity.activation=0;checkBad(bad,"invalid activation");
 bad=saved;bad.records[0].sourceType=55;checkBad(bad,"Withering has no corpse");
 bad=saved;bad.records[0].yield=0;checkBad(bad,"zero yield invalid");
 bad=saved;bad.records[0].yield=65536;checkBad(bad,"unbounded yield invalid");
 bad=saved;bad.catalog="invalid";checkBad(bad,"invalid fingerprint");
 auto checkPayload=[&](std::vector<std::uint8_t> malformed,const char* name){CorpseSnapshot output=saved;check(!decodeCorpseSnapshot(malformed,output,error)&&output.records.size()==2&&output.catalog==sha,name);};
 auto corrupt=bytes;corrupt[0]^=1;checkPayload(corrupt,"magic rejected");
 corrupt=bytes;corrupt[8]=2;checkPayload(corrupt,"payload schema rejected");
 corrupt=bytes;corrupt[12]='z';checkPayload(corrupt,"payload fingerprint rejected");
 corrupt=bytes;corrupt[76]=3;checkPayload(corrupt,"count mismatch rejected");
 corrupt=bytes;corrupt[76]=255;corrupt[77]=255;corrupt[78]=255;corrupt[79]=255;checkPayload(corrupt,"oversized count rejected");
 corrupt=bytes;corrupt[112]=2;checkPayload(corrupt,"boolean rejected");
 corrupt=bytes;corrupt.push_back(0);checkPayload(corrupt,"trailing bytes rejected");
 for(std::size_t n=0;n<bytes.size();++n){corrupt.assign(bytes.begin(),bytes.begin()+n);checkPayload(corrupt,"truncated payload rejected");}
 // Maximum 64-bit source epoch/activation must roundtrip without truncation.
 auto wide=saved;wide.records.resize(1);wide.records[0].identity.epoch=std::numeric_limits<std::uint64_t>::max();wide.records[0].identity.activation=std::numeric_limits<std::uint64_t>::max();
 check(encodeCorpseSnapshot(wide,bytes,error)&&decodeCorpseSnapshot(bytes,decoded,error)&&decoded.records[0].identity==wide.records[0].identity,"64 bit identities roundtrip");
 CorpseLedger invalid("bad");check(!invalid.birth(&pellet,id,26,5,handle,error),"invalid configured catalog refused");
 CorpseLedger empty(sha);check(!empty.birth(nullptr,id,26,5,handle,error)&&empty.snapshot().records.empty(),"null birth atomic");
 // The runtime cap and serialization cap coincide, including consumed/detached
 // tombstones. No accepted runtime receipt can make the save unencodable.
 CorpseLedger bounded(sha);bool filled=true;
 for(std::size_t i=0;i<corpseSnapshotMaxRecords;++i){
  auto entry=id;entry.generator=0x52000000u+static_cast<unsigned>(i);
  if(!bounded.birth(&pellet,entry,26,5,handle,error)||!bounded.deliver(&pellet,handle,grant,error)||grant!=5||!bounded.forgetPellet(&pellet,handle)){filled=false;break;}
 }
 check(filled&&bounded.snapshot().records.size()==corpseSnapshotMaxRecords,"runtime fills through maximum tombstones");
 const auto full=bounded.snapshot();
 check(encodeCorpseSnapshot(full,bytes,error)&&bytes.size()<=corpsePayloadMaxBytes&&decodeCorpseSnapshot(bytes,decoded,error),"maximum runtime snapshot encodable");
 auto overflowId=id;overflowId.generator=0x52000000u+static_cast<unsigned>(corpseSnapshotMaxRecords);
 second=123;
 check(!bounded.birth(&pellet,overflowId,26,5,second,error)&&second==123&&bounded.snapshot().records.size()==corpseSnapshotMaxRecords,"runtime overflow atomic refusal");
 auto overfull=full;auto extra=full.records.front();extra.identity=overflowId;overfull.records.push_back(extra);
 auto previous=bytes;
 check(!encodeCorpseSnapshot(overfull,bytes,error)&&bytes==previous,"snapshot count overflow atomic refusal");
 CorpseLedger overflowRestore(sha);auto allow=[](const CorpseRecord&,std::string&){return true;};
 check(!overflowRestore.restore(overfull,allow,error)&&overflowRestore.snapshot().records.empty(),"restore count overflow atomic refusal");
 checkPayload(std::vector<std::uint8_t>(corpsePayloadMaxBytes+1,0),"payload above 1MiB refused");
 std::printf("original_corpse_ledger checks=%u failures=%u engine=0 authentication=caller\n",checks,failures);
 return failures?1:0;
}
