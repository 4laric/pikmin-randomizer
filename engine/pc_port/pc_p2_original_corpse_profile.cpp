#include "pc_p2_original_corpse_profile.h"
namespace p2original {
namespace {const CorpseProfile profiles[]={
 {1,1,"Kochappy",3,6,4,22.0f,13.0f,14.0f,200.0f,0.0f,0.0f,0.0f},
 {45,2,"YellowKochappy",3,6,4,22.0f,13.0f,14.0f,200.0f,0.0f,0.0f,0.0f},
 {44,3,"BlueKochappy",3,6,4,22.0f,13.0f,14.0f,200.0f,0.0f,0.0f,0.0f},
 {2,4,"Chappy",10,20,12,40.0f,30.0f,30.0f,700.0f,0.0f,0.0f,55.0f},
 {43,5,"YellowChappy",10,20,12,40.0f,30.0f,30.0f,700.0f,0.0f,0.0f,55.0f},
 {42,6,"BlueChappy",10,20,12,40.0f,30.0f,30.0f,700.0f,0.0f,0.0f,55.0f},
 {12,7,"UjiA",1,1,2,10.0f,10.0f,10.0f,90.0f,0.0f,0.0f,0.0f},
 {13,8,"UjiB",1,1,3,10.0f,10.0f,10.0f,90.0f,0.0f,0.0f,0.0f},
 {14,9,"Tobi",1,1,4,12.0f,12.0f,12.0f,90.0f,0.0f,0.0f,0.0f},
 {17,10,"Frog",7,14,8,30.0f,22.0f,14.0f,400.0f,-27.3f,0.0f,12.3f},
 {18,11,"MaroFrog",7,14,8,30.0f,22.0f,14.0f,400.0f,-0.6f,0.0f,-34.0f},
 {24,12,"Tank",7,15,8,25.0f,18.0f,10.0f,250.0f,32.3f,0.0f,-2.5f},
 {25,13,"Wtank",7,15,8,25.0f,18.0f,10.0f,250.0f,32.3f,0.0f,-2.5f},
 {23,14,"Sarai",3,6,4,20.0f,15.0f,10.0f,150.0f,0.0f,0.0f,0.0f},
 {32,15,"Demon",3,6,8,20.0f,15.0f,10.0f,150.0f,-4.265f,0.0f,-27.91f},
 {58,16,"BombSarai",3,6,8,20.0f,15.0f,10.0f,150.0f,10.5f,0.0f,-37.0f},
 {26,17,"Catfish",5,10,5,22.0f,15.0f,10.0f,150.0f,0.0f,0.0f,0.0f},
 {27,18,"Tadpole",1,1,1,10.0f,10.0f,8.0f,90.0f,0.0f,0.0f,0.0f},
 {28,19,"ElecBug",5,10,5,22.0f,13.0f,10.0f,200.0f,0.0f,0.0f,0.0f},
 {15,20,"Armor",8,16,8,25.0f,20.0f,12.0f,200.0f,0.0f,0.0f,0.0f},
 {30,21,"Queen",20,30,30,45.0f,45.0f,20.0f,800.0f,0.0f,0.0f,208.0f},
 {53,22,"KingChappy",20,30,30,35.0f,35.0f,30.0f,400.0f,0.0f,0.0f,-13.0f},
 {33,23,"FireChappy",10,20,12,45.0f,30.0f,35.0f,700.0f,0.0f,0.0f,55.0f},
 {35,24,"KumaChappy",10,20,12,45.0f,30.0f,35.0f,700.0f,0.0f,0.0f,55.0f},
 {41,25,"Fuefuki",3,6,5,20.0f,15.0f,10.0f,150.0f,0.0f,0.0f,0.0f},
 {38,26,"PanModoki",3,6,4,20.0f,15.0f,10.0f,200.0f,0.0f,0.0f,0.0f},
 {40,27,"OoPanModoki",10,20,4,45.0f,30.0f,35.0f,600.0f,0.0f,0.0f,0.0f},
 {54,28,"Miulin",7,15,8,30.0f,24.0f,15.0f,200.0f,0.0f,0.0f,0.0f},
 {59,29,"FireOtakara",3,6,5,20.0f,15.0f,20.0f,150.0f,0.0f,0.0f,0.0f},
 {60,30,"WaterOtakara",3,6,5,20.0f,15.0f,20.0f,150.0f,0.0f,0.0f,0.0f},
 {61,31,"GasOtakara",3,6,5,20.0f,15.0f,20.0f,150.0f,0.0f,0.0f,0.0f},
 {62,32,"ElecOtakara",3,6,5,20.0f,15.0f,20.0f,150.0f,0.0f,0.0f,0.0f},
 {65,33,"Imomushi",1,1,2,10.0f,7.0f,5.0f,90.0f,0.0f,0.0f,0.0f},
 {67,34,"LeafChappy",7,14,10,22.0f,15.0f,10.0f,200.0f,0.0f,0.0f,28.0f},
 {34,35,"SnakeCrow",5,10,15,20.0f,15.0f,15.0f,200.0f,0.0f,0.0f,122.5f},
 {70,36,"SnakeWhole",5,10,25,20.0f,15.0f,15.0f,200.0f,0.0f,0.0f,0.0f},
 {63,37,"Jigumo",5,8,8,25.0f,15.0f,15.0f,300.0f,0.0f,0.0f,0.0f},
 {76,38,"KumaKochappy",3,6,4,22.0f,15.0f,14.0f,200.0f,0.0f,0.0f,0.0f},
 {75,39,"Kabuto",7,15,8,34.0f,34.0f,20.0f,250.0f,29.0f,0.0f,0.0f},
 {96,40,"Fkabuto",7,15,8,34.0f,34.0f,20.0f,250.0f,29.0f,0.0f,0.0f},
 {95,41,"Rkabuto",7,15,8,34.0f,34.0f,20.0f,250.0f,29.0f,0.0f,0.0f},
 {71,42,"UmiMushi",3,6,25,22.0f,15.0f,14.0f,200.0f,-13.383f,0.0f,-67.5f},
 {101,43,"UmiMushiBlind",3,6,25,22.0f,15.0f,14.0f,200.0f,-13.383f,0.0f,-67.5f},
 {79,44,"Sokkuri",1,1,1,5.0f,5.0f,5.0f,100.0f,0.0f,0.0f,12.26f},
 {78,45,"MiniHoudai",10,20,12,45.0f,30.0f,35.0f,400.0f,0.0f,0.0f,0.0f},
 {97,46,"FminiHoudai",10,20,12,45.0f,30.0f,35.0f,400.0f,0.0f,0.0f,0.0f},
 {68,47,"TamagoMushi",1,1,2,10.0f,10.0f,8.0f,90.0f,0.0f,0.0f,0.0f},
 {77,48,"ShijimiChou",1,1,1,9.0f,9.0f,8.0f,90.0f,-5.5f,0.0f,-1.0f},
 {84,49,"Hana",10,20,12,25.0f,18.0f,10.0f,250.0f,0.0f,0.0f,0.0f},
 {94,50,"DangoMushi",20,30,30,45.0f,45.0f,20.0f,800.0f,0.0f,0.0f,0.0f},
};}
const CorpseProfile* corpseProfile(unsigned source){for(const auto& p:profiles)if(p.source==source)return &p;return nullptr;}
bool corpseDisabled(unsigned source){
 // Source onInit explicitly disables EB_LeaveCarcass (including inherited Pom,
 // Kogane and Rock families). Do not infer this from the P1 chassis settings.
 switch(source){case 0:case 3:case 4:case 5:case 6:case 7:case 8:case 9:case 10:case 11:
 case 16:case 19:case 20:case 21:case 22:case 29:case 31:case 36:case 37:
 case 55:case 56:case 57:case 66:case 69:case 72:case 73:case 74:case 82:
 case 46:case 47:case 48:case 49:case 50:case 51:case 52:case 80:case 81:
 case 83:case 85:case 86:case 87:case 88:case 89:case 90:case 91:case 92:
 case 93:case 98:case 99:return true;default:return false;}
}
}
