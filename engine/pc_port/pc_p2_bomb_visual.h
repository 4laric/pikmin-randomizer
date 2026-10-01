#pragma once
// Shared P2 Bomb (bomb-rock) visuals: the bomb's own countdown life-gauge wheel
// and the P1 bomb-rock shape draw with the lit-fuse flash. Used by the Volatile
// Dweevil carrier (pc_p2_otakara.cpp) and meant for any other P2 actor that
// carries or drops a Bomb, e.g. the Careening Dirigibug bombs
// (pc_p2_bombsarai_own_teki.cpp). Output-only: nothing here touches sim state.
//
// Policy (engine-free, unit tested): pc_p2_bomb_telegraph.h. Source truth: the
// Bomb enemy drains mHealth by the frame time while lit (bombState.cpp:113-122),
// its life gauge is the ordinary EnemyBase gauge (enemyBase.cpp:2692-2710,
// ratio mHealth/mMaxHealth at fp27 = 35), the retail Bomb life is 4.5 s.
#include "pc_p2_bomb_telegraph.h"
#include "LifeGauge.h"

class Graphics;
class Matrix4f;
class Vector3f;

// Short-lived spark effects for a lit bomb. Every spawned generator is tracked,
// force-killed once older than maxAge, and all are killed at the blast (and on
// destruction), so no ember outlives the bomb. Engine-side (EffectMgr).
struct P2BombSparks {
    struct Live { void* gen; float age; };
    Live live[32];
    int count = 0;
    P2BombSparks() = default;
    P2BombSparks(const P2BombSparks&) { count = 0; } // copies never own generators
    P2BombSparks& operator=(const P2BombSparks&) { return *this; }
    ~P2BombSparks() { killAll(); }
    void spawn(int effect, float x, float y, float z);
    void update(float dt, float maxAge);
    void killAll();
};
// Engine-wide live particle generator count (for the "nothing left" log).
unsigned pc_p2_bomb_live_generators();

// One countdown wheel. Keep one per bomb; call draw() from a 2D pass
// (BTeki::refresh2d for a Teki carrier).
struct P2BombGauge {
    LifeGauge gauge;
    bool ready = false;
    // Draws the P1 life-gauge wheel (Wheel style, snap to target) above
    // bombWorldPos. health counts down from maxHealth (p2bombtelegraph::
    // kBombLife for a stock Bomb). Green at full, red near empty, like every
    // other enemy gauge.
    void draw(Graphics& gfx, const Vector3f& bombWorldPos, float health,
              float maxHealth = p2bombtelegraph::kBombLife);
};

// Draws the P1 bomb-rock shape (objects/bomb/bomb.mod, ItemMgr::mItemShapes[2])
// with view as its view-space matrix (camera look-at * the bomb world matrix).
// While flashing, the bomb materials are tinted by
// p2bombtelegraph::flashTint(flashOn, ratio) for this draw only and restored
// after, because the shape is shared with real P1 bomb rocks. Returns false when
// the shape is not loaded.
bool pc_p2_bomb_draw_shape(Graphics& gfx, const Matrix4f& view, bool flashing, bool flashOn, float ratio);
class Shape;
// The same lit-fuse flash for any bomb Shape (e.g. a Dirigibug bomb's private
// pose Shape): its materials are tinted for this draw only and restored after.
bool pc_p2_bomb_draw_tinted(Graphics& gfx, Shape& shape, const Matrix4f& view, bool flashing, bool flashOn, float ratio);
