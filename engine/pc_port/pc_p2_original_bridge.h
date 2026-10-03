#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>
namespace p2original {
// Literal GenItem 0002 / brdg local0001; no P1 shape index or AP identity.
struct BridgeRecord {
 std::uint32_t uid=0,reserved=3;
 std::string sourceKey,sourceSha;
 int resurrectionDays=0,dayLimit=-1,type=0;
 float stageLife=3000;
 std::array<float,3> position{},offset{},rotation{};
};
struct BridgeState {
 int stage=0;
 std::array<float,15> health{};
 unsigned extensionTicks=0;
};
int bridgeStageCount(int type);
bool validateBridge(const BridgeRecord&,std::string&);
std::string bridgeDigest(const BridgeRecord&);
bool readBridges(const std::string&,std::vector<BridgeRecord>&,std::string&);
BridgeState bridgeInitial(const BridgeRecord&);
bool bridgeStateValid(const BridgeRecord&,const BridgeState&,std::string&);
bool bridgeAttack(const BridgeRecord&,BridgeState&,float);
bool bridgeTick(const BridgeRecord&,BridgeState&);
bool bridgeBreak(const BridgeRecord&,BridgeState&,float);
// Includes pending 40-tick extension. Atomic import validates before assignment.
bool bridgeExport(const BridgeRecord&,const BridgeState&,std::vector<std::uint8_t>&,std::string&);
bool bridgeImport(const BridgeRecord&,const std::vector<std::uint8_t>&,BridgeState&,std::string&);
std::array<float,3> bridgeStagePosition(const BridgeRecord&,int);
}
