// Executes the production receiver against observable engine doubles, with the
// production captain squad-capture seam bound (lane 12, #130;
// codex/p2-lane12-review c29ec8398 port). This checks authority/callback
// behavior; it is not gameplay or physics evidence.
//
// Single translation unit: the stub engine doubles (engine.h) come first and
// the real engine headers are neutralized by pre-defining their include
// guards, so the production pc_p2_kurage_receiver.cpp + pc_p2_captain.cpp
// compile against the same stub types the test drives. No new files: the
// production headers are engine-free forward declarations.
#include "engine.h"
// Neutralize the real engine headers now shadowed by the stub above.
#define _CREATURE_H
#define _NAVIMGR_H
#define _PIKI_H
#define _PIKIMGR_H
#define _PIKISTATE_H
#define _SYSTEM_H
#define _PIKIAI_H
#define _OBJECTMGR_H
#define _NAVISTATE_H
#define _KONTROLLER_H
#define _PCAM_CAMERAMANAGER_H
#define _GAMEFLOW_H
#define _CINEMATICPLAYER_H
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_captain.h"
#include "pc_p2_kurage_receiver.cpp"
#include "pc_p2_captain.cpp"
#include <cassert>
#include <cstdint>
#include <cstdio>
static void zero(const Piki& p){assert(p.mVelocity.x==0 && p.mVelocity.y==0 && p.mVelocity.z==0);assert(p.mTargetVelocity.x==0 && p.mTargetVelocity.y==0 && p.mTargetVelocity.z==0);}
int main(){
 Creature owner,replacement;CollPart mouth,other;
 mouth.mCentre={0,100,0};
 Piki p, fresh, control;
 PikiMgr manager; manager.entries={&p,&fresh,&control}; pikiMgr=&manager;
 NaviMgr navis; naviMgr=&navis;
 navis.navi.mHealth=100.0f;
 p.mNavi=control.mNavi=fresh.mNavi=navis.getNavi();
 assert(pc_p2_captain::setup_from_navi_mgr());
 assert(!pc_p2_kurage_receiver_controls(&p));
 assert(pc_p2_kurage_receiver_setup(&owner,&mouth));
 assert(pc_p2_kurage_receiver_admit(&p));
 // Squad capture bound to this receiver tick: only the target leaves the
 // squad, its formation action was abandoned, control is preserved.
 assert(p.mNavi==nullptr && control.mNavi==navis.getNavi());
 assert(p.mActiveAction->cleanups==1);
 assert(pc_p2_captain::captive_count()==1);
 assert(pc_p2_captain::is_captive_for(2, &p)); // first setup tick: 1 -> 2
 assert(pc_p2_kurage_receiver_controls(&p));
 pc_p2_kurage_receiver_update(.01f,true,true,false);
 assert(p.mVelocity.y==600 && p.mTargetVelocity.y==600);
 // Reset during travel must stop motion despite generation revocation.
 pc_p2_kurage_receiver_reset();zero(p);
 assert(pc_p2_captain::captive_count()==0 && control.mNavi==navis.getNavi());
 assert(!pc_p2_captain::is_captive_for(2, &p));
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
 assert(pc_p2_captain::captive_count()==0 && control.mNavi==navis.getNavi());
 // Wave 3 flyers (#960): several Jellyfloats hold Pikmin independently, and a
 // Pikmin that is mid-throw (PikiFlyingState reads mNavi every tick) is never
 // captured.
 {
  Creature ownerB;CollPart mouthB;mouthB.mCentre={0,100,0};
  p.owner=nullptr;p.part=nullptr;p.alive=true;p.mNavi=navis.getNavi();
  fresh.owner=nullptr;fresh.part=nullptr;fresh.alive=true;fresh.mNavi=navis.getNavi();
  assert(pc_p2_kurage_receiver_register(&owner,&mouth) && pc_p2_kurage_receiver_register(&ownerB,&mouthB));
  assert(pc_p2_kurage_receiver_admit_for(&owner,&p) && pc_p2_kurage_receiver_admit_for(&ownerB,&fresh));
  assert(pc_p2_kurage_receiver_count_for(&owner)==1 && pc_p2_kurage_receiver_count_for(&ownerB)==1);
  assert(pc_p2_kurage_receiver_controls(&p) && pc_p2_kurage_receiver_controls(&fresh));
  // Each owner's update drives only its own Pikmin.
  p.mSRT.t={0,0,0};fresh.mSRT.t={0,0,0};
  p.mVelocity={0,0,0};p.mTargetVelocity={0,0,0};fresh.mVelocity={0,0,0};fresh.mTargetVelocity={0,0,0};
  pc_p2_kurage_receiver_update_for(&owner,.01f,true,true,false);
  assert(p.mVelocity.y==600 && fresh.mVelocity.y!=600);
  // One Jellyfloat dying releases its Pikmin and leaves the other's untouched.
  pc_p2_kurage_receiver_owner_invalidated(&owner);
  assert(!pc_p2_kurage_receiver_controls(&p) && pc_p2_kurage_receiver_controls(&fresh));
  assert(pc_p2_kurage_receiver_count_for(&ownerB)==1);
  // Thrown Pikmin keep their captain: the flying state still needs it.
  control.mState=PIKISTATE_Flying;
  assert(!pc_p2_kurage_receiver_admit_for(&ownerB,&control) && control.mNavi==navis.getNavi());
  control.mState=PIKISTATE_Normal;
  pc_p2_kurage_receiver_reset();
  assert(pc_p2_kurage_receiver_count()==0 && pc_p2_captain::captive_count()==0);
 }
 // #960 owner playtest: the campaign OWN Jellyfloat takes a standing Pikmin (the source
 // suckPikmin has no mayIstick gate), pulls it to the `suck` part itself and holds it
 // inside the stomach; a legacy owner keeps the old gate; a thrown Pikmin is never taken.
 {
  Creature ownO,ownL;CollPart mouthO,mouthL;
  mouthO.mCentre={0,100,0};mouthO.mRadius=15;ownO.mSRT.t={0,70,0};
  mouthL.mCentre={0,100,0};mouthL.mRadius=15;
  for(Piki* q:{&p,&fresh,&control}){q->owner=nullptr;q->part=nullptr;q->alive=true;q->mNavi=navis.getNavi();q->stickable=false;q->mState=PIKISTATE_Normal;q->mSRT.t={0,0,0};q->mAttachPosition={9,9,9};}
  assert(pc_p2_kurage_receiver_register(&ownO,&mouthO) && pc_p2_kurage_receiver_register(&ownL,&mouthL));
  pc_p2_kurage_receiver_configure_own(&ownO,24.0f);
  assert(!pc_p2_kurage_receiver_admit_for(&ownL,&p));            // legacy owner: standing Pikmin refused
  assert(pc_p2_kurage_receiver_admit_for(&ownO,&p));             // OWN owner: standing Pikmin taken
  control.mState=PIKISTATE_Flying;
  assert(!pc_p2_kurage_receiver_admit_for(&ownO,&control));      // mid-throw: never
  control.mState=PIKISTATE_Normal;
  // Travel heads for the part itself, not the bottom of its sphere.
  pc_p2_kurage_receiver_update_for(&ownO,.01f,true,true,false);
  assert(p.mVelocity.y==600);
  p.mSRT.t={0,95,0};p.mVelocity={0,0,0};p.mTargetVelocity={0,0,0};
  pc_p2_kurage_receiver_update_for(&ownO,.01f,true,true,false);
  assert(pc_p2_kurage_receiver_stomach_count_for(&ownO)==1);
  // First held Pikmin rests on the part centre, the next ones on a ring inside the sphere.
  assert(p.mAttachPosition.x==0 && p.mAttachPosition.y==0 && p.mAttachPosition.z==0);
  fresh.mSRT.t={0,95,0};
  assert(pc_p2_kurage_receiver_admit_for(&ownO,&fresh));
  pc_p2_kurage_receiver_update_for(&ownO,.01f,true,true,false);
  assert(fresh.mAttachPosition.y==0 && std::fabs(fresh.mAttachPosition.x)+std::fabs(fresh.mAttachPosition.z)>1.0f);
  assert(std::sqrt(fresh.mAttachPosition.x*fresh.mAttachPosition.x+fresh.mAttachPosition.z*fresh.mAttachPosition.z)<mouthO.mRadius);
  pc_p2_kurage_receiver_reset();
  assert(pc_p2_kurage_receiver_count()==0 && pc_p2_captain::captive_count()==0);
 }
 pc_p2_captain::teardown();
 std::puts("PASS receiver authority: inactive, travel/reset, transfer, arrival, shrink/release, invalidation, callback reentry");
}
