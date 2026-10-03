#pragma once
#include "pc_p2_original_pelplant.h"
#include <functional>
class BTeki;
class Graphics;
struct Matrix4f;
namespace p2original { namespace pelplant {
// Narrow concrete bridge. Course dispatcher owns this until all roots and
// captured cargo have been released. metColor must query actual first-met data.
class Native {
public:
 explicit Native(std::function<bool(unsigned)> metColor);
 ~Native();
 Native(const Native&)=delete;
 Native& operator=(const Native&)=delete;
 Provider& provider();
 // Stopped-engine actual-bank ownership control; never births game actors.
 bool geometryOwnershipControl(std::string&);
 bool owns(const Creature*)const;
 bool tick(BTeki*,float,std::string&);
 bool draw(BTeki*,Graphics&,const Matrix4f&);
 bool captured(const Pellet*)const;
 // Ordinary Pellet::update/isAtari/isFree hooks must skip their normal paths
 // while captured; drawing remains enabled at the authored capture transform.
 bool updateCaptured(Pellet*);
 bool drawCaptured(Pellet*,Graphics&,const Matrix4f&);
 void forgetPellet(Pellet*);
 // Called after source death END, outside the provider tick, so coordinated
 // course deathCount/retirement can release without destroying an active Host.
 void onDeath(std::function<bool(Creature*,std::string&)>);
 // Must query the owning original registry AFTER activation, preserving full
 // fingerprint/UID/ordinal/epoch/activation; session token is never durable ID.
 void onIdentity(std::function<bool(Creature*,std::string&,std::string&)>);
 void onOnion(std::function<void(Pellet*,unsigned,bool)>);
 bool observeOnion(Pellet*,unsigned&,bool&);
 void forgetCreature(Creature*);
private:
 struct Impl;
 std::unique_ptr<Impl> m;
};
} }
// Shared hook dispatch searches only explicitly registered Native instances.
// Return false means unrelated actor/cargo; malformed owned state fails closed.
bool pc_p2_original_pelplant_update(BTeki*);
bool pc_p2_original_pelplant_refresh(BTeki*,Graphics&);
bool pc_p2_original_pelplant_draw(BTeki*,Graphics&,const Matrix4f&);
bool pc_p2_original_pelplant_damage(BTeki*,float,const char special[4]);
bool pc_p2_original_pelplant_stick(BTeki*,const char special[4]);
bool pc_p2_original_pelplant_captured(const Pellet*);
bool pc_p2_original_pelplant_capture_update(Pellet*);
bool pc_p2_original_pelplant_capture_draw(Pellet*,Graphics&,const Matrix4f&);
bool pc_p2_original_pelplant_onion(Pellet*,unsigned& token,bool& duplicate);
void pc_p2_original_pelplant_forget_pellet(Pellet*);
void pc_p2_original_pelplant_forget_teki(BTeki*);
