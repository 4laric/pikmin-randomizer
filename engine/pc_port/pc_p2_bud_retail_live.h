#pragma once
#include "pc_p2_bud_live_floor.h"
#include "pc_p2_retail_cave_native.h"
namespace p2budorigin {
// Implemented by the actual Cave/Surface transition owner over its native
// authenticated/committed party graph. No default permission callbacks exist.
class NativeTravelReader {
public:
 virtual ~NativeTravelReader()=default;
 virtual bool carried(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const=0;
 virtual bool receive(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const=0;
 virtual bool retained(const Record&,std::string&)const=0;
};
class RetailLiveFloorReader final:public LiveFloorReader {
 const p2retail::NativeFloor& native;const NativeTravelReader* travel;
 p2retail::Snapshot physical;mutable Creation facts;bool bound=false;
public:
 explicit RetailLiveFloorReader(const p2retail::NativeFloor& n,const NativeTravelReader* t=nullptr):native(n),travel(t){}
 // Actual Installing facts only; never a caller-created scene Snapshot.
 bool initialize(std::string&);
 const Creation* current()const noexcept override;
 bool expectedBud(const Pom*,unsigned,const p2original::InstanceIdentity&,FloorIdentity&,std::string&)const override;
 bool emitted(const Record&,std::string&)const override;
 bool carried(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const override;
 bool receive(const Snapshot&,const std::vector<BodyBinding>&,std::string&)const override;
};
}
