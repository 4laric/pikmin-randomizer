#pragma once
// #1022 Breadbug lair (PanHouse nest) presentation policy (engine-free).
//
// P2 PanModokiBase::Obj::birth (plugProjectMorimuraU/panModoki.cpp:55) births
// a Nest::Obj (EnemyID_PanHouse) at the Breadbug's birth position and facing,
// scaled by the proper parm fp00 "nest scale" (retail PanModoki 1.0,
// OoPanModoki 2.0); Nest::Mgr draws enemy/data/PanHouse/model.szs. onKill
// (panModoki.cpp:687) calls killNest(), so the nest goes away when the
// Breadbug dies. The native port draws the same model at the same place as a
// static, collision-free visual; gameplay (the FSM's home point) is unchanged.
#include <cmath>
namespace p2breadbugnest {
// Drawn while the Breadbug is bound and alive and the model was staged.
inline bool visible(bool bound, bool escaped, int deadState, bool modelLoaded) {
    return bound && !escaped && deadState == 0 && modelLoaded;
}
// Retail fp00 range is 0..5 (PanModokiBase.h Parm "nest scale"); anything
// non-finite or non-positive falls back to the retail default 1.0.
inline float scale(float nestScale) {
    if (!std::isfinite(nestScale) || !(nestScale > 0.0f)) return 1.0f;
    return nestScale > 5.0f ? 5.0f : nestScale;
}
}  // namespace p2breadbugnest
