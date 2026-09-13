#pragma once
#include <string>

enum class P2CaveEntryProfile { Invalid, Tutorial, BeastsFloor2, BeastsFloor3, BeastsFloor4 };
inline P2CaveEntryProfile p2_cave_entry_profile(const std::string& version, int floor, const std::string& token) {
    if(token.empty() || token.find_first_not_of("0123456789abcdef")!=std::string::npos)return P2CaveEntryProfile::Invalid;
    if(version=="P2_CAVE_ENTRY_1" && (floor==1 || floor==2) && token.size()==32)return P2CaveEntryProfile::Tutorial;
    if(token.size()!=64)return P2CaveEntryProfile::Invalid;
    if(version=="P2_BEASTS_ENTRY_1" && floor==2)return P2CaveEntryProfile::BeastsFloor2;
    if(version=="P2_BEASTS_FLOOR3_ENTRY_1" && floor==3)return P2CaveEntryProfile::BeastsFloor3;
    if(version=="P2_BEASTS_FLOOR4_ENTRY_1" && floor==4)return P2CaveEntryProfile::BeastsFloor4;
    return P2CaveEntryProfile::Invalid;
}
