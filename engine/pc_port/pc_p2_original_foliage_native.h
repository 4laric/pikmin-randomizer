#pragma once
#include "pc_p2_original_foliage.h"
class BTeki; class Graphics; struct Matrix4f;
namespace p2original { namespace shijimi { class Native; } }
namespace p2original { namespace foliage {
// Real manager-owned scenery: chassis allocation/cleanup only, no borrowed AI,
// host species drops or host geometry. Original GroupCourse owns identities.
class Native {
public:
 Native(); ~Native();
 Native(const Native&)=delete; Native& operator=(const Native&)=delete;
 Provider& provider();
 bool attachSentinel(shijimi::Native&,std::string&);
 bool owns(const Creature*)const;
 bool tick(BTeki*,float,std::string&);
 bool draw(BTeki*,Graphics&,const Matrix4f&,bool postShadow=false);
 void postShadow(Graphics&);
 std::size_t watageParticles()const;
 unsigned watageEmissions()const;
 unsigned watageDrawQuads()const;
 void requestWatageCameraControl();
 bool collision(BTeki*,Creature*,std::string&);
 bool earthquake(BTeki*,std::string&);
 void forget(Creature*);
 bool geometryOwnershipControl(std::string&);
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
bool pc_p2_original_foliage_update(BTeki*);
bool pc_p2_original_foliage_refresh(BTeki*,Graphics&);
bool pc_p2_original_foliage_draw(BTeki*,Graphics&,const Matrix4f&);
bool pc_p2_original_foliage_collision(BTeki*,Creature*);
bool pc_p2_original_foliage_owned(const Creature*);
bool pc_p2_original_foliage_earthquake(BTeki*);
void pc_p2_original_foliage_forget(BTeki*);

void pc_p2_original_foliage_post_shadow(Graphics&);

