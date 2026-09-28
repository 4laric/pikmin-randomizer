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
 pc_p2_captain::teardown();
 std::puts("PASS receiver authority: inactive, travel/reset, transfer, arrival, shrink/release, invalidation, callback reentry");
}
