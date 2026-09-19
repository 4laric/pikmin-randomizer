#pragma once

struct Navi;

// Attempt one native sprout conversion. No target is retained between calls.
bool pc_whistle_pluck(Navi* navi, float radius);
constexpr float PC_WHISTLE_PLUCK_INTERVAL = 0.08f;
