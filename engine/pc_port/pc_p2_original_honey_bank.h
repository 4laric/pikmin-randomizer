#pragma once
#include "pc_p2_original_honey_native.h"
#include <array>
namespace p2originalresource { namespace honey {
// Actual private retail bank backend. Gameplay/stock Services forward only
// their mechanical methods here and retain their own authoritative ownership.
class SourceBank {
public:
 SourceBank();~SourceBank();
 bool resources(Resources&,std::string&);
 bool motion(Actor&,unsigned,std::string&);
 bool advance(Actor&,Shape&,float,std::vector<int>&,std::string&);
 bool collisionCentre(const Actor&,P2EggVec3&,std::string&);
 bool captureAnimation(const Actor&,std::string&,std::string&)const;
 bool validateAnimation(Phase,const std::string&,std::string&)const;
 // Read the seven verified ItemHoney clocks for pure checkpoint validation.
 bool sourceClocks(std::array<ReceiverClip,7>&,std::string&)const;
 bool restoreAnimation(Actor&,const std::string&,std::string&);
 void forget(Actor&);
 const std::string& fingerprint()const;
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
