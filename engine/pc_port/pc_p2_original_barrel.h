#pragma once
#include <array>
#include <string>
#include <vector>
#include <cstdint>
namespace p2original {
struct BarrelRecord {
    unsigned uid=0,reserved=3;
    std::string sourceKey,sourceSha;
    int resurrectionDays=0,dayLimit=-1;
    float life=4000;
    std::array<float,3> position{},offset{},rotation{};
};
enum class BarrelPhase { Normal, Dying, Retired };
struct BarrelState {
    BarrelPhase phase=BarrelPhase::Normal;
    float health=4000,animationFrame=0;
};
bool validateBarrel(const BarrelRecord&,std::string&);
std::string barrelDigest(const BarrelRecord&);
bool readBarrels(const std::string&,std::vector<BarrelRecord>&,std::string&);
bool barrelStateValid(const BarrelRecord&,const BarrelState&,float deadDuration,std::string&);
bool barrelDamage(BarrelState&,float);
// Returns true exactly once when the real death clip reaches its terminal key.
bool barrelAnimate(BarrelState&,float dt,float deadDuration);
bool barrelExport(const BarrelRecord&,const BarrelState&,float deadDuration,std::vector<std::uint8_t>&,std::string&);
bool barrelImport(const BarrelRecord&,const std::vector<std::uint8_t>&,float deadDuration,BarrelState&,std::string&);
}
