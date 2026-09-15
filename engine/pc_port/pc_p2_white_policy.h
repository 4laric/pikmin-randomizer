#pragma once
#include <cmath>

struct P2WhiteStats {
    float movement = 0;
    float attack = 0;
    float scale = 0;
    float carryPower = 0;
    float budBonus = 0;
    float flowerBonus = 0;
    float carryMaxFactor = 0;
    float carryMinFactor = 0;
    float baseRunSpeed = 0;
};

inline bool p2_white_stats_valid(const P2WhiteStats& value) {
    return std::isfinite(value.movement) && value.movement >= 1 && value.movement <= 3
        && std::isfinite(value.attack) && value.attack >= 1 && value.attack <= 30
        && std::isfinite(value.scale) && value.scale > 0 && value.scale <= 2
        && std::isfinite(value.carryPower) && value.carryPower >= 0 && value.carryPower <= 5
        && std::isfinite(value.budBonus) && value.budBonus >= 0 && value.budBonus <= 2
        && std::isfinite(value.flowerBonus) && value.flowerBonus >= 0 && value.flowerBonus <= 2
        && std::isfinite(value.carryMaxFactor) && value.carryMaxFactor >= 0 && value.carryMaxFactor <= 2
        && std::isfinite(value.carryMinFactor) && value.carryMinFactor >= 0 && value.carryMinFactor <= 2
        && std::isfinite(value.baseRunSpeed) && value.baseRunSpeed > 0 && value.baseRunSpeed <= 500;
}
