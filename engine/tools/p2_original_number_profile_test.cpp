#include "pc_p2_original_number_profile.h"
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include <type_traits>
using namespace p2originalnumber;
static_assert(std::is_same<decltype(profile(1u)),const Profile*>::value,"profiles must remain immutable");
int main(){
 unsigned checks=0,failures=0;
 auto check=[&](bool ok,const char* name){++checks;if(!ok){++failures;std::printf("FAIL %s\n",name);}};
 const Profile* one=profile(Size::One);const Profile* five=profile(Size::Five);
 check(one&&five&&one!=five,"distinct literal profiles");
 if(!one||!five)return 1;
 check(profile(1u)==one&&profile(5u)==five,"typed and numeric lookup agree");
 check(one->size==Size::One&&one->carryMin==1&&one->carryMax==2&&one->matchingYield==2&&one->nonmatchingYield==1,"One carry and yields");
 check(one->radius==10.f&&one->pickRadius==10.f&&one->height==7.6f&&one->inertiaScaling==90.f,"One geometry and inertia");
 check(one->particleCount==0&&one->particleSize==.5f&&one->friction==.5f&&one->dynamics==Dynamics::Never,"One physical policy");
 check(five->size==Size::Five&&five->carryMin==5&&five->carryMax==10&&five->matchingYield==5&&five->nonmatchingYield==3,"Five carry and yields");
 check(five->radius==20.f&&five->pickRadius==20.f&&five->height==14.f&&five->inertiaScaling==200.f,"Five geometry and inertia");
 check(five->particleCount==4&&five->particleSize==1.f&&five->friction==.9f&&five->dynamics==Dynamics::Lod,"Five physical policy");
 check(std::strcmp(one->configName,"number1")==0&&std::strcmp(five->configName,"number5")==0&&std::strcmp(one->modelMember,"white1.bmd")==0&&std::strcmp(five->modelMember,"white2.bmd")==0,"literal resource names");
 const char* config="68613c8887a0855c97f545156ebe809b266dfe517568c3476ca2b9ebfb4177ac";
 check(std::strcmp(one->configSha256,config)==0&&std::strcmp(five->configSha256,config)==0,"verified config SHA256");
 check(std::strcmp(one->modelSha256,"4398d4785dbc740159f3cf304727d8655e89122f3be1cc3aca5259f5ee468f39")==0,"verified One model SHA256");
 check(std::strcmp(five->modelSha256,"bc941851d8e5191b77f55b2719ccd80c3ca97f84ee87c779671de7c355dd14cf")==0,"verified Five model SHA256");
 check(static_cast<unsigned>(Color::Blue)==0&&static_cast<unsigned>(Color::Red)==1&&static_cast<unsigned>(Color::Yellow)==2,"retail color numbering");
 for(Size size:{Size::One,Size::Five})for(unsigned p=0;p<3;++p)for(unsigned r=0;r<3;++r){
  unsigned out=999;const unsigned expected=size==Size::One?(p==r?2:1):(p==r?5:3);
  check(yield(size,static_cast<Color>(p),static_cast<Color>(r),out)&&out==expected,"all literal color pair yields");
 }
 for(unsigned invalid:{0u,2u,3u,4u,6u,10u,20u,257u,65535u})check(!profile(invalid),"unsupported sizes fail closed without narrowing");
 unsigned out=999;
 check(!yield(static_cast<Size>(0),Color::Blue,Color::Blue,out)&&out==999,"invalid size output unchanged");
 check(!yield(Size::One,static_cast<Color>(3),Color::Blue,out)&&out==999,"invalid pellet color output unchanged");
 check(!yield(Size::Five,Color::Red,static_cast<Color>(255),out)&&out==999,"invalid receiver color output unchanged");
 check(!validColor(static_cast<Color>(255)),"invalid color fail closed");
 std::printf("original_number_profile checks=%u failures=%u engine=0 animation=0 save=0\n",checks,failures);
 return failures?1:0;
}
