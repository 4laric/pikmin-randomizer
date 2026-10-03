#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>
namespace p2original {
struct GateRecord {
 std::uint32_t uid=0,reserved=3;
 std::string sourceKey,sourceSha;
 int resurrectionDays=0,dayLimit=-1,color=0;
 float segmentLife=100;
 std::array<float,3> position{},offset{},rotation{};
};
bool validateGate(const GateRecord&,std::string&);
std::string gateDigest(const GateRecord&);
bool parseGates(const std::string& bytes,std::vector<GateRecord>&,std::string&);
bool readGates(const std::string&,std::vector<GateRecord>&,std::string&);
// Retail itemGate.cpp: damage is accumulated, consumed in Damaged::exec,
// a segment falls only below zero, and advances only at its animation key.
enum class GatePhase {Wait, Damaged, Down, Open};
enum class GateAction {None, DamageMotion, DownMotion, Idle, Open};
struct GateState {
 GatePhase phase=GatePhase::Wait;
 float health=100,damage=0,animationFrame=0;
 unsigned segmentsDown=0;
 bool damageAnimationFinished=false;
};
GateState gateInitial(const GateRecord&);
bool gateStateValid(const GateRecord&,const GateState&,std::string&);
GateAction gateDamage(GateState&,float);
GateAction gateExec(GateState&);
GateAction gateAnimationKey(const GateRecord&,GateState&);
bool gateSettled(const GateRecord&,const GateState&,std::string&);
bool gateExport(const GateRecord&,const GateState&,std::vector<std::uint8_t>&,std::string&);
bool gateImport(const GateRecord&,const std::vector<std::uint8_t>&,GateState&,std::string&);
}
