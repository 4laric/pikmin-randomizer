#pragma once
#include <cmath>
namespace p2original { namespace cannon {
// EnemyFunc::flickNearbyPikmin and flickStickPikmin add PI to faceDir.
// InteractFlick receivers apply velocity (-sin(angle), -cos(angle)).
inline float pikminFlickAngle(float face, bool backwards, float sentinel){
 if(backwards)return sentinel;
 constexpr float pi=3.14159265358979323846f;
 float angle=std::fmod(face+pi,2.0f*pi);if(angle<0)angle+=2.0f*pi;
 return angle;
}
enum class FlickKey {None,Flick,FlickDead};
// KabutoState::StateFlick checks death at KEYEVENT_2, after flicking.
// The authored key is frame30, observed at posed frame31 (30 Hz).
inline FlickKey flickKey(bool delivered,float time,float health){
 if(delivered||time<(31.0f/30.0f-1e-4f))return FlickKey::None;
 return health<=0.0f?FlickKey::FlickDead:FlickKey::Flick;
}
} }
