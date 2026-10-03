#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>
namespace p2original {
// Literal GenItem0002/Cave0002 payload. fg00..fg09 retain source parameter
// type/value pairs; presentation does not reinterpret them as cap mechanics.
struct CaveRecord {
    std::uint32_t uid=0,reserved=0;
    std::string sourceKey,sourceSha,caveFile,unitsFile,caveId;
    int resurrectionDays=0,dayLimit=-1;
    std::array<float,3> position{},offset{},rotation{};
    std::array<unsigned,10> parameterTypes{};
    std::array<float,10> parameters{};
};
bool validateCave(const CaveRecord&,std::string&);
std::string caveDigest(const CaveRecord&);
bool readCaves(const std::string&,std::vector<CaveRecord>&,std::string&);
// Parse the exact bytes returned by the selected source-session authority.
bool parseCaves(const std::string&,std::vector<CaveRecord>&,std::string&);
bool caveCache(const CaveRecord&,std::vector<std::uint8_t>&,std::string&);
bool caveRestore(const CaveRecord&,const std::vector<std::uint8_t>&,std::string&);
}
