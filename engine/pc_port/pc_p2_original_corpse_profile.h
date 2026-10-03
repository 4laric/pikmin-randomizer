#pragma once
namespace p2original {
// Literal GPVE01 revision 0 user/Abe/Pellet/us/carcass_config.txt.
// Member SHA256 a76c476352cb0d7386a8ab448f0e35285cc8668f43f2b9189cfdd87b03de9de0.
// Null archive/bmd denotes the retained dead actor view, not a missing resource.
struct CorpseProfile {
 unsigned source,index; const char* name; unsigned minimum,maximum,seeds;
 float radius,pickRadius,height,inertia,offsetX,offsetY,offsetZ;
};
const CorpseProfile* corpseProfile(unsigned source);
bool corpseDisabled(unsigned source);
}
