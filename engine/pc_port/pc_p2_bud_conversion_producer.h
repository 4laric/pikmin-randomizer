#pragma once
#include "pc_p2_bud_conversion_origin.h"
#include <limits>
#include <cstdlib>
namespace p2budorigin {
// Register snapshotCallback/headCallback through the real
// pc_p2_original_pom_set_head_callback AFTER core bind and BEFORE start.
// Owner keeps this object, authority and native selected proof reader alive.
// species reads the ACTUAL initialized head; fatal must not allocate or throw.
// A failed final callback is an invariant breach AFTER donor consumption, never
// permission to silently drop the emitted head or fabricate an origin.
class Producer {
 struct Reservation {const Pom* pom;const Piki* donor;p2original::InstanceIdentity bud;unsigned token;Donor origin;PendingEmission pending;};
 Registry& registry;const Authority& authority;
 unsigned (*species)(const PikiHeadItem*)noexcept;
 void (*fatal)(const char*)noexcept;
 std::map<std::string,Reservation> pending;
 std::uint64_t serial=0;
public:
 Producer(Registry& r,const Authority& a,unsigned(*s)(const PikiHeadItem*)noexcept,void(*f)(const char*)noexcept):registry(r),authority(a),species(s),fatal(f){}
 // Reversible reservations are discarded at teardown/capacity retry. No donor
 // tombstone is committed here, and receipts are LOCAL opaque capabilities,
 // never persisted source identities or a replacement for selected proof.
 void cancel()noexcept{pending.clear();}
 static bool snapshotCallback(const Pom* pom,const p2original::InstanceIdentity& bud,unsigned token,const Piki* donor,std::string& receipt,void* context){
  auto* self=static_cast<Producer*>(context);if(!self||!self->species||!self->fatal)return false;
  try {
   Donor origin;std::string error;
   if(!self->authority.donor(donor,origin,error)||!valid(origin))return false;
   // A retry may follow another successful donor output. Re-prepare from the
   // CURRENT registry instead of retaining an old whole-state reservation.
   for(auto i=self->pending.begin();i!=self->pending.end();){if(i->second.donor==donor)i=self->pending.erase(i);else ++i;}
   if(self->serial==std::numeric_limits<std::uint64_t>::max())return false;
   PendingEmission prepared;
   if(!self->registry.prepare(pom,token,bud,donor,3,origin.species==3,prepared,error))return false;
   const auto key="bud-reservation:"+std::to_string(++self->serial);
   self->pending.emplace(key,Reservation{pom,donor,bud,token,std::move(origin),std::move(prepared)});
   receipt=key;return true;
  }catch(...){return false;}
 }
 static void headCallback(const Pom* pom,const p2original::InstanceIdentity& bud,unsigned token,unsigned ordinal,PikiHeadItem* head,bool refunded,const std::string& receipt,void* context)noexcept{
  auto* self=static_cast<Producer*>(context);
  if(!self||!self->species||!self->fatal)std::abort();
  auto found=self->pending.find(receipt);
  if(found==self->pending.end()||found->second.pom!=pom||!(found->second.bud==bud)||found->second.token!=token){self->fatal("source6 output has no exact prepared donor reservation");return;}
  const char* reason=nullptr;
  if(!self->registry.adopt(std::move(found->second.pending),head,ordinal,self->species(head),refunded,reason)){self->fatal(reason?reason:"source6 output adoption failed");return;}
  self->pending.erase(found); // frees only; no donor pointer escapes this event.
 }
};
}
