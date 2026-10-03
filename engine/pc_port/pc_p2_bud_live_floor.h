#pragma once
#include "pc_p2_bud_conversion_origin.h"
namespace p2budorigin {
enum class CreationPhase:unsigned { Installing=1,Committed=2 };
// Creation identity is issued by an actually installed native floor. It is NOT
// a selected card Proof and never acquires a fabricated generation/card hash.
struct Creation {
 std::string campaign,session,cave,visit,sourceSha,catalogSha,layoutSha;
 unsigned floor=0;std::uint64_t epoch=0,nativeSerial=0,sessionRevision=0;
 CreationPhase phase=CreationPhase::Installing;bool gameActive=false;
 bool valid()const noexcept;
 bool operator==(const Creation&)const noexcept;
};
// #1274/930 implements this over its ACTUAL NativeFloor/SceneOps owner. Bind it
// Installing permits callback registration after actual family bind; it grants
// no emission permission. Only Committed AND actual game-active permits output.
// current() returns a borrowed
// named-field record or nullptr; teardown/reselection revokes it BEFORE roots
// or pool addresses are reused. The current serial is a native owner lifetime,
// never a caller permission bit. The immutable session fields were paired with
// the real authenticated OriginalSession at floor installation.
class LiveFloorReader {
public:
 virtual ~LiveFloorReader()=default;
 virtual const Creation* current()const noexcept=0;
 // Exact installed source6 row/member/epoch/activation/instance + actual core
 // Pom identity/token. Must use the completed native birth census, not a
 // provider-supplied record or a descriptor hash pretending physical install.
 virtual bool expectedBud(const Pom*,unsigned,const p2original::InstanceIdentity&,FloorIdentity&,std::string&)const=0;
 // A converted output may outlive its parent. Check the owning native emission
 // ledger across the active travel destination; do not require parent alive.
 virtual bool emitted(const Record&,std::string&)const=0;
 // Complete actual transition-owned carried body census, AFTER source loss
 // observation, before physical teardown. No positional matching/cold proof.
 virtual bool carried(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const=0;
 virtual bool receive(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const=0;
};
}
