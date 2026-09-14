#include "pc_p2_kurage_teki.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_kurage_teki_policy.h"
#include "pc_p2_kurage_visual.h"
#include "Collision.h"
#include "Generator.h"
#include "system.h"
#include "teki.h"
#include <cstdio>
#include <fstream>
#include <map>
namespace { struct Binding { unsigned generator; int type; CollPart mouth; }; std::map<BTeki*,Binding> s;
void revoke(BTeki* t){ auto i=s.find(t); if(i==s.end())return; pc_p2_kurage_receiver_owner_invalidated(t); s.erase(i); }
void refresh(BTeki* t, Binding& b){ b.mouth.mPartType=PART_BoundSphere;b.mouth.mRadius=15.0f;b.mouth.mCentre=t->mSRT.t;b.mouth.mJointMatrix.makeIdentity(); }
}
void pc_p2_kurage_teki_reset(){ for(auto& x:s)pc_p2_kurage_receiver_owner_invalidated(x.first);s.clear(); }
void pc_p2_kurage_teki_forget(BTeki* t){if(t)revoke(t);}
bool pc_p2_kurage_teki_is_bound(const BTeki* t){return t&&s.count(const_cast<BTeki*>(t));}
void pc_p2_kurage_teki_setup(){ pc_p2_kurage_teki_reset();std::ifstream in("p2-kurage-teki.txt");if(!in)return;p2kurage::Binding cfg{};if(!p2kurage::read(in,cfg)||!tekiMgr)std::abort();unsigned gen=cfg.generator;int type=cfg.type;Iterator it(tekiMgr);CI_LOOP(it){auto* t=static_cast<Teki*>(*it);if(!t||!t->mGenerator||t->mGenerator->_70!=gen)continue;if(t->mTekiType!=type||s.size())std::abort();if(!pc_p2_kurage_visual_setup())std::abort();auto inserted=s.emplace(static_cast<BTeki*>(t),Binding{gen,type,{}});Binding& b=inserted.first->second;refresh(t,b);if(!pc_p2_kurage_receiver_setup(t,&b.mouth))std::abort();std::printf("P2_KURAGE_TEKI_READY generator=%u type=%d binding=private_adapter\n",gen,type);} }
void pc_p2_kurage_teki_tick(BTeki* t){auto i=s.find(t);if(i==s.end())return;if(!t->isAlive()){revoke(t);return;}refresh(t,i->second);pc_p2_kurage_receiver_update(gsys->getFrameTime(),true,t->mHealth>0.0f,false);}
bool pc_p2_kurage_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& matrix, bool corpse){if(!s.count(t))return false;return pc_p2_kurage_visual_draw(t,gfx,matrix,corpse);}
