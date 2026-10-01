#pragma once
#include <cstdint>
class Navi;
class Creature;
class CollPart;

// Prototype single P1 captain bridge. Owner token is a generation-qualified
// host identity, not a pointer. Host must invalidate it before owner teardown.
// P1 CollPart has no mouth bit, so the caller must pass its already-selected
// mouth slot; this bridge only accepts its sphere/collision attachment shape.
bool pc_demon_capture(Navi* captain, Creature* owner, CollPart* mouth,
                      std::uint64_t ownerToken, unsigned slot);
// Uses a receiver-global monotonic generation so capture owners cannot revive
// an old registered-drop callback by reusing their own local token.
bool pc_demon_forced_release(Navi* captain, float damage, float retailFallMeckSpeed);
bool pc_demon_bound(Navi* captain);
bool pc_demon_owned_by(Navi* captain, Creature* owner);
void pc_demon_release(Navi* captain);
void pc_demon_reset(Navi* captain); // Before Navi::reset mutates native stick fields.
void pc_demon_owner_lost(std::uint64_t owner);
void pc_demon_scene_exit(); // Before manager/heap invalidation, while links are live.
void pc_demon_forget(); // After synchronous revocation; does not dereference.
void pc_demon_before_transition(Navi*, int nextState);
using P2DemonRandom = float (*)(void*);
bool pc_demon_escape_tick(Navi* captain, bool directionalDownEdge, P2DemonRandom random, void* context);
bool pc_demon_suppress_atari(Navi* captain);

class Matrix4f;
void pc_demon_follow_mouth(Navi*);
bool pc_demon_capture_matrix(Navi*, Matrix4f&);
