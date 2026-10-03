#include "pc_p2_original_number_profile.h"

namespace p2originalnumber {
namespace {
// GPVE01 revision 0: user/Abe/Pellet/us/pelletlist_us.szs,
// member numberpellet_config.txt. Models are members of pellet.szs.
constexpr const char configSha[]="68613c8887a0855c97f545156ebe809b266dfe517568c3476ca2b9ebfb4177ac";
constexpr Profile one{Size::One,1,2,2,1,10.f,10.f,7.6f,90.f,0,.5f,.5f,
 Dynamics::Never,"number1","white1.bmd",configSha,
 "4398d4785dbc740159f3cf304727d8655e89122f3be1cc3aca5259f5ee468f39"};
constexpr Profile five{Size::Five,5,10,5,3,20.f,20.f,14.f,200.f,4,1.f,.9f,
 Dynamics::Lod,"number5","white2.bmd",configSha,
 "bc941851d8e5191b77f55b2719ccd80c3ca97f84ee87c779671de7c355dd14cf"};
}
const Profile* profile(unsigned number) noexcept {
 switch(number){case 1:return &one;case 5:return &five;default:return nullptr;}
}
const Profile* profile(Size size) noexcept {return profile(static_cast<unsigned>(size));}
bool validColor(Color color) noexcept {return static_cast<unsigned>(color)<3;}
bool yield(Size size,Color pelletColor,Color receiverColor,unsigned& out) noexcept {
 const Profile* p=profile(size);
 if(!p||!validColor(pelletColor)||!validColor(receiverColor))return false;
 out=pelletColor==receiverColor?p->matchingYield:p->nonmatchingYield;
 return true;
}
}
