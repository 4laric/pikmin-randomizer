#pragma once
// Existing captain knockout threshold; sprouts count toward surviving population.
inline const char* p2_beasts_failure_reason(bool beasts, int floor, float captainHealth,
                                            bool livingPikmin, bool livingSprouts) {
    if(!beasts || floor!=3)return nullptr;
    if(captainHealth<=1.f)return "knockout";
    if(!livingPikmin && !livingSprouts)return "extinction";
    return nullptr;
}
