// Executes the production receiver against observable engine doubles.
// This checks authority/callback behavior; it is not gameplay or physics evidence.
#include "engine.h"
#include "pc_p2_kurage_receiver.h"
#include <cassert>
#include <cstdio>
static void zero(const Piki& p){assert(p.mVelocity.x==0 && p.mVelocity.y==0 && p.mVelocity.z==0);assert(p.mTargetVelocity.x==0 && p.mTargetVelocity.y==0 && p.mTargetVelocity.z==0);}
int main(){
 Creature owner,replacement;CollPart mouth,other;
 mouth.mCentre={0,100,0};
 Piki p;
 assert(!pc_p2_kurage_receiver_controls(&p));
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));
 assert(pc_p2_kurage_receiver_admit(&p));
 assert(pc_p2_kurage_receiver_controls(&p));
 pc_p2_kurage_receiver_update(.01f,true,true,false);
 assert(p.mVelocity.y==600 && p.mTargetVelocity.y==600);
 // Reset during travel must stop motion despite generation revocation.
 pc_p2_kurage_receiver_reset();zero(p);
 assert(!pc_p2_kurage_receiver_controls(&p) && pc_p2_kurage_receiver_count()==0);
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));
 assert(pc_p2_kurage_receiver_admit(&p));
 pc_p2_kurage_receiver_update(.01f,true,true,false);
 pc_p2_kurage_receiver_owner_invalidated(&owner);zero(p);
 // External ownership wins immediately, before the receiver's next update.
 for(bool stomach:{false,true}){
  assert(pc_p2_kurage_receiver_setup(&owner,&mouth));
  assert(stomach?pc_p2_kurage_receiver_capture(&p):pc_p2_kurage_receiver_admit(&p));
  p.owner=&replacement;p.part=&other;p.mVelocity={1,2,3};p.mTargetVelocity={4,5,6};p.mSRT.s={2,3,4};
  assert(!pc_p2_kurage_receiver_controls(&p));
  pc_p2_kurage_receiver_update(.01f,true,true,false);
  assert(pc_p2_kurage_receiver_count()==0 && p.owner==&replacement && p.part==&other);
  assert(p.mVelocity.y==2 && p.mTargetVelocity.y==5 && p.mSRT.s.y==3);
  p.owner=nullptr;p.part=nullptr;
 }
 // Source-shaped arrival transitions to stomach and clears travel motion.
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));
 assert(pc_p2_kurage_receiver_admit(&p));
 p.mSRT.t={0,85,0};
 pc_p2_kurage_receiver_update(.01f,true,true,false);zero(p);
 assert(pc_p2_kurage_receiver_stomach_count()==1 && pc_p2_kurage_receiver_controls(&p));
 pc_p2_kurage_receiver_update(16,true,true,false);
 pc_p2_kurage_receiver_update(.25f,true,true,false);assert(p.mSRT.s.y==1.5f);
 pc_p2_kurage_receiver_reset();assert(p.mSRT.s.y==3 && !p.isStickTo());zero(p);
 // Death invalidation must not resurrect or touch a recycled Piki.
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));
 assert(pc_p2_kurage_receiver_admit(&p));
 pc_p2_kurage_receiver_piki_invalidated(&p);
 p.alive=false;p.mVelocity={7,8,9};
 pc_p2_kurage_receiver_reset();assert(p.mVelocity.y==8 && !pc_p2_kurage_receiver_controls(&p));
 p.alive=true;
 // Revocation occurs before callbacks, and a new receiver survives old reset.
 Piki fresh;
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));
 assert(pc_p2_kurage_receiver_capture(&p));
 p.detached=[&]{assert(!pc_p2_kurage_receiver_controls(&p));assert(pc_p2_kurage_receiver_setup(&replacement,&other));assert(pc_p2_kurage_receiver_admit(&fresh));};
 pc_p2_kurage_receiver_reset();p.detached={};
 assert(pc_p2_kurage_receiver_controls(&fresh) && pc_p2_kurage_receiver_count()==1);
 pc_p2_kurage_receiver_reset();
 // A post-detach callback may attach a new owner; never apply the old kill.
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));assert(pc_p2_kurage_receiver_capture(&p));
 p.detached=[&]{p.owner=&replacement;p.part=&other;};
 pc_p2_kurage_receiver_update(16,true,true,false);pc_p2_kurage_receiver_update(.5f,true,true,false);
 assert(p.alive && p.kills==0 && p.owner==&replacement);p.detached={};
 pc_p2_kurage_receiver_reset();
 // A callback can recapture the same, still-unattached Piki for mouth travel.
 p.owner=nullptr;p.part=nullptr;
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));assert(pc_p2_kurage_receiver_capture(&p));
 p.detached=[&]{assert(pc_p2_kurage_receiver_admit(&p));};
 pc_p2_kurage_receiver_update(16,true,true,false);pc_p2_kurage_receiver_update(.5f,true,true,false);
 assert(p.alive && p.kills==0 && pc_p2_kurage_receiver_controls(&p));
 p.detached={};pc_p2_kurage_receiver_reset();
 std::puts("PASS receiver authority: inactive, travel/reset, transfer, arrival, shrink/release, invalidation, callback reentry");
}
