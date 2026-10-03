#pragma once
#include "pc_p2_retail_cave_context.h"
#include "pc_p2_original_pod_sources.h"
#include <functional>
class Pellet;
struct PelletGoalState;
struct Suckable;

namespace p2originalpod {
// Retail Onyon type 3, object bank 1. Ship type 4 belongs to the surface owner.
using SourceInput=std::function<bool(const std::string& role,std::string& bytes,std::string& error)>;
struct Config {
 p2retail::Snapshot floor;
 // Authenticated authored-layout BaseGen type 7 placement, radians. Never
 // infer the source scene from an Onion, preview receiver or active P1 stage.
 unsigned unit=0,slot=0,baseGenType=7;
 float x=0,y=0,z=0,yaw=0;
 // Required selected-input getter; no file-path or cache fallback. These are
 // canonical INPUT roles, and the model is parsed from the exact verified bytes.
 SourceInput input;
 std::string model=convertedModelRole;
 std::string sourceArchive=archiveRole,sourceModel=originalModelRole;
 std::string sourceCollision=originalCollisionRole,sourceTexts=originalTextsRole;
 // Independently issues the original source epoch/activation. Borrowed for
 // the floor's lifetime, never the same untrusted cargo input copied back.
 p2retail::FloorIdentityAuthority* births=nullptr;
};
// Owner checks original session, selected SAVE fingerprint, cave floor and
// layout incarnation on every query; an input descriptor alone grants nothing.
using ContextProvider=std::function<bool(const p2retail::SceneIdentity&,p2retail::Snapshot&)>;
using CompletedCallback=std::function<bool(Pellet*,Suckable*,std::string&)>;
// Read-only graph capture. No ledger copy, synthetic consumption or save
// authority. Until SAVE provides an atomic cargo/ledger transaction, pending
// entries must continue to reject card writes and floor exits.
struct PendingCargo {p2retail::BirthIdentity birth;unsigned phase=0;bool transaction=false;};
struct Snapshot {unsigned version=1;p2retail::Snapshot floor;unsigned unit=0,slot=0;
 std::vector<PendingCargo> pending;bool committed=false;};
struct UncollectedCargo {Pellet* actor=nullptr;p2retail::BirthIdentity birth;};
// Floor/cargo/SAVE owner verifies and retains the actual uncollected native
// graph before authorizing boundary release. No implicit success provider.
using RetainUncollected=std::function<bool(const p2retail::Snapshot&,
                        const std::vector<UncollectedCargo>&,std::string&)>;
}
// Additive API; never activates implicitly or creates an economy ledger.
bool pc_p2_original_pod_preflight(const p2originalpod::Config&,
                                p2originalpod::ContextProvider,std::string&);
bool pc_p2_original_pod_birth(const p2originalpod::Config&,
                            p2originalpod::ContextProvider,std::string&);
// Floor owner commits only after all geometry/content/exit bindings succeed.
bool pc_p2_original_pod_commit_floor(const p2retail::SceneIdentity&,std::string&);
// Rollback only before commit and before any observable suction/receipt.
bool pc_p2_original_pod_abort_prepared(const p2retail::SceneIdentity&,std::string&);
bool pc_p2_original_pod_context(Suckable*,const p2retail::SceneIdentity&,p2retail::Snapshot&);
// Raw lifetime observation only. Unlike context lookup, false means no native
// preparation is owned; it cannot grant source, receipt or SAVE authority.
bool pc_p2_original_pod_owned();
// Read-only rollback phase check, including resource-only preparation. The
// actual abort still validates its own phase; this issues no receipt authority.
bool pc_p2_original_pod_can_abort_prepared(const p2retail::SceneIdentity&);
Suckable* pc_p2_original_pod_goal(const p2retail::SceneIdentity&);
bool pc_p2_original_pod_bind_cargo(Pellet*,const p2retail::BirthIdentity&,
                                 const p2retail::SceneIdentity&,
                                 p2originalpod::CompletedCallback,std::string&);
bool pc_p2_original_pod_owns(const Pellet*);
Suckable* pc_p2_original_pod_goal_for(Pellet*);
// True only within the callback emitted by native completed suction. There is
// no caller-supplied integer event token. Verify before committing the ledger.
bool pc_p2_original_pod_completed(Pellet*,Suckable*,const p2retail::SceneIdentity&);
// Active carry/suction/lost bindings and receipt commits are transactions.
// Ground cargo is captured separately; it is never a consumed receipt.
unsigned pc_p2_original_pod_pending();
bool pc_p2_original_pod_snapshot(const p2retail::SceneIdentity&,p2originalpod::Snapshot&);
// Plain release still refuses any unfinished cargo. This explicit boundary
// variant admits only quiescent ground cargo retained by the owning floor.
bool pc_p2_original_pod_release_uncollected(const p2retail::SceneIdentity&,
                                          p2originalpod::RetainUncollected,std::string&);
bool pc_p2_original_pod_release(std::string&);

// Only the actual native goal state may issue receipt authority. Consumers
// cannot invoke these transitions or construct a synthetic completion token.
struct P2OriginalPodNativeSeam {
private:
 friend struct PelletGoalState;
 static void begin(Pellet*);
 static bool done(Pellet*,const PelletGoalState&);
 static void cleanup(Pellet*);
};
void pc_p2_original_pod_forget_pellet(Pellet*);
