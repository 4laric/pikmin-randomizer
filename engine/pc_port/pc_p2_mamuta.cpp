// Optional P2 Mamuta static anchors on exact P1 Miurin actors. Gameplay stays P1.
#include "pc_p2_mamuta.h"
#include "pc_p2_mamuta_policy.h"
#include "pc_p2_mamuta_rules.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <map>
#include <set>
#include <vector>
#include <fstream>
#include <cstdio>
#include <cstdlib>
static_assert(TEKI_Miurin == 24 && TekiMotion::Dead == 0 && TekiMotion::Wait1 == 2
              && TekiMotion::Type1 == 10 && TekiMotion::Type2 == 11 && TekiMotion::Type3 == 12,
              "Mamuta static anchor policy must track native enum values");
namespace {
const char* names[] = {"wait", "dead", "attack1"};
Shape* shapes[3] = {};
std::map<BTeki*, unsigned> actors;
std::set<std::pair<BTeki*, int>> logged;
size_t bytesTotal = 0;
void fail() { std::fputs("P2_MAMUTA invalid profile\n", stderr); std::abort(); }
Shape* load(const char* clip) {
    std::string name = std::string("miulin_") + clip + ".mod";
    std::ifstream file("assets/dataDir/courses/pikmin2room/" + name, std::ios::binary | std::ios::ate);
    if (!file) fail();
    auto size = file.tellg();
    if (size <= 0 || size > 16*1024*1024 || bytesTotal + size_t(size) > 48*1024*1024) fail();
    bytesTotal += size_t(size); file.seekg(0);
    std::vector<unsigned char> data(size_t(size), 0), resources;
    if (!file.read(reinterpret_cast<char*>(data.data()), size) || !p2animation::resources(data, resources)) fail();
    Shape* shape = gameflow.loadShape(("courses/pikmin2room/" + name).c_str(), true);
    if (!shape) fail();
    for (int t=0; t<shape->mTexAttrCount; ++t)
        if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
    return shape;
}
}
void pc_p2_mamuta_reset() { actors.clear(); logged.clear(); for (auto& s: shapes) s=nullptr; bytesTotal=0; pc_p2_mamuta_rules_reset(); }
bool pc_p2_mamuta_is_bound(BTeki* actor) { return actors.find(actor) != actors.end(); }
bool pc_p2_mamuta_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    auto it = actors.find(static_cast<BTeki*>(view));
    if (it == actors.end()) return false;
    generator = it->second;
    return true;
}
void pc_p2_mamuta_forget(BTeki* actor) {
    actors.erase(actor);
    for (int k=0; k<3; ++k) logged.erase({actor,k});
}
void pc_p2_mamuta_setup() {
    pc_p2_mamuta_reset();
    if (!pc_pikipelago_room_preview()) return;
    std::ifstream in("p2-mamuta-actors.txt"); if (!in) return;
    std::string word; int count;
    if (!(in>>word>>count) || word!="P2_MAMUTA_ACTORS_1" || count<1 || count>100 || !tekiMgr) fail();
    std::set<unsigned> wanted, found;
    for (int i=0; i<count; ++i) {
        unsigned long long id;
        if (!(in>>id>>word) || id>0xffffffffULL || word!="Miulin" || !wanted.insert(unsigned(id)).second) fail();
    }
    if (in>>word) fail();
    Iterator it(tekiMgr); CI_LOOP(it) {
        Teki* actor=static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator || !wanted.count(actor->mGenerator->_70)) continue;
        unsigned id=actor->mGenerator->_70;
        if (actor->mTekiType!=TEKI_Miurin || !found.insert(id).second) fail();
        actors.emplace(actor,id);
    }
    if (found!=wanted) fail();
    pc_p2_mamuta_rules_setup();
    for (int k=0; k<3; ++k) shapes[k]=load(names[k]);
    for (const auto& e: actors) std::printf("P2_MAMUTA_READY generator=%u native_type=24 xyz=%.6f,%.6f,%.6f P1_proxy_static_anchors_no_P2_planting\n", e.second,e.first->mSRT.t.x,e.first->mSRT.t.y,e.first->mSRT.t.z);
}
bool pc_p2_mamuta_draw(BTeki* actor, Graphics& gfx, const Matrix4f& view, bool corpse) {
    auto entry=actors.find(actor);
    if (entry==actors.end() || !gfx.mCamera || !actor->mTekiAnimator) return false;
    int k=p2mamuta::anchor(actor->mTekiType,actor->mTekiAnimator->getCurrentMotionIndex(),corpse);
    if (k<0 || !shapes[k]) return false;
    shapes[k]->updateAnim(gfx,view,nullptr,actor);
    shapes[k]->drawshape(gfx,*gfx.mCamera,nullptr);
    if (logged.insert({actor,k}).second) std::printf("P2_MAMUTA_DRAW generator=%u anchor=%s static_pose P1_gameplay_unchanged\n",entry->second,names[k]);
    return true;
}
