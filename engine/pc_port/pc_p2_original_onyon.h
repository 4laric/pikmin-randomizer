#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>
namespace p2original {
// Original GenItem ('0002'), ItemOnyon local version '0001'.  Not EnemyRecord.
struct OnyonRecord {
 std::uint32_t uid=0, reserved=0;
 std::string sourceKey, sourceSha;
 int resurrectionDays=0, dayLimit=-1, index=0, afterBoot=1;
 std::array<float,3> position{},offset{},rotation{}; // literal floats, degrees
};
bool validateOnyon(const OnyonRecord&,std::string&);
bool onyonEligible(const OnyonRecord&,std::uint8_t discoveredContainers);
std::string onyonDigest(const OnyonRecord&);
bool parseOnyons(const std::string& bytes,std::vector<OnyonRecord>&,std::string&);
bool readOnyons(const std::string& path,std::vector<OnyonRecord>&,std::string&);
bool readOnyonsFromBytes(const std::string& bytes,std::vector<OnyonRecord>&,std::string&);
}
