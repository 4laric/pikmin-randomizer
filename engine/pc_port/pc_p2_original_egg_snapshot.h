#pragma once
#include "pc_p2_original_egg.h"
#include "pc_p2_original_resource_contents.h"
namespace p2original { namespace egg {
struct Snapshot {
 p2originalresource::SourceIdentity identity;
 std::string resourceFingerprint;
 unsigned state=0; // Literal EGG_Wait is the only source FSM state.
 Position position,velocity,targetVelocity,scale{1,1,1};float facing=0;
 float health=0,flickTimer=0,sourceFrame=0;bool stopped=true;
 Flags flags;
 bool dependent=false,captured=false,falling=false,dropGroup=false;
 bool contentsGenerated=false,effectsEmitted=false,killRequested=false;
 // Capture dependency graph identity, never an address or a matrix pointer.
 bool hasParent=false;p2originalresource::SourceIdentity parentIdentity;
};
struct SnapshotContext {
 p2originalresource::SourceIdentity identity;
 std::string resourceFingerprint;float maxHealth=0;
 bool dependent=false,dropGroup=false;
 // Restorer must bind the actual authoritative graph before preflight/apply.
 bool actualCaptureBound=false;p2originalresource::SourceIdentity actualParent;
 Position capturePosition;
};
bool validateSnapshot(const Snapshot&,const SnapshotContext&,std::string&);
} }
