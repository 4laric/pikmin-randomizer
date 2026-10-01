#include "pc_p2_kurage_visual.h"
#include "pc_p2_kurage_bank.h"
#include "pc_p2_pose_family.h"
#include "Graphics.h"
#include "Shape.h"
#include "Texture.h"
#include "gameflow.h"
#include "sysNew.h"
#include "teki.h"
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <map>
#include <set>
#include <algorithm>
#include <vector>
#include <string>
namespace {
Shape* sWait = nullptr;
Shape* sAttack = nullptr;
bool sReady = false;
// Converted per-motion poses.  Each is one static source pose; the host selects
// by the current FSM state so the drawn pose follows the source motion rather
// than only wait/attack.
std::map<std::string, Shape*> sShapes;
// Greater Spotted Jellyfloat (OniKurage, 72) poses, same names.
std::map<std::string, Shape*> sShapesGreater;
bool sReadyGreater = false;

// #972: sampled pose bank per variant (the static shapes above stay the
// fallback when no bank is staged or it fails to load).
struct Family {
    explicit Family(const char* tag) : bank(tag) {}
    p2posefamily::Bank bank;
    p2posefamily::Actors actors;
    p2kuragebank::Profile profile;
    std::set<const void*> measured; // actors whose private-Shape heap cost was logged
    // #1065 settled carcass pose per death clip: source frame + ground lift.
    struct Settled { bool ok = false; float frame = 0.f, lift = 0.f; };
    std::map<std::string, Settled> settled;
    bool attempted = false;
    void reset() {
        bank.reset(); actors.clear(); profile = p2kuragebank::Profile(); attempted = false; measured.clear();
        settled.clear();
    }
};
Family& family(bool greater)
{
    static Family lesser("KURAGE");
    static Family big("ONIKURAGE");
    return greater ? big : lesser;
}
Shape* load(const char* path)
{
    if (!std::filesystem::exists(std::filesystem::path("assets/dataDir") / path)) return nullptr;
    const int heap = gsys->setHeap(SYSHEAP_App);
    Shape* shape = gameflow.loadShape(path, true);
    if (shape)
        for (int i = 0; i < shape->mTexAttrCount; ++i)
            if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
    gsys->setHeap(heap);
    return shape;
}

// Loads the staged pose bank once per setup. Silent when none is staged (a
// content cache extracted before #972); a bad bank is reported and dropped so
// the static shapes keep drawing.
void loadBank(bool greater)
{
    Family& f = family(greater);
    if (f.attempted) return;
    f.attempted = true;
    const char* tag = greater ? "ONIKURAGE" : "KURAGE";
    std::ifstream in(greater ? "p2-onikurage-animation.txt" : "p2-kurage-animation.txt");
    if (!in) return;
    if (!p2kuragebank::parse(in, f.profile)) {
        f.profile = p2kuragebank::Profile();
        std::printf("P2_%s_ANIMATION_INVALID reason=profile fallback=static\n", tag);
        std::fflush(stdout);
        return;
    }
    const std::string prefix = greater ? "onikurage_" : "kurage_";
    p2poseload::Shared shared;
    std::size_t resident = 0;
    int poses = 0;
    const int heap = gsys->setHeap(SYSHEAP_App);
    const unsigned freeBefore = gsys->getHeap(SYSHEAP_App)->getFree();
    for (const p2kuragebank::Clip& clip : f.profile.clips) {
        std::vector<Shape*> shapes;
        std::string error;
        if (!p2posefamily::loadFamilyClip(f.bank, clip.name, prefix + clip.name, int(clip.frames.size()),
                                          clip.duration, clip.frames, shared, resident, shapes, error)) {
            gsys->setHeap(heap);
            std::printf("P2_%s_ANIMATION_INVALID clip=%s reason=%s fallback=static\n", tag, clip.name.c_str(),
                        error.c_str());
            std::fflush(stdout);
            f.reset();
            f.attempted = true;
            return;
        }
        poses += int(clip.frames.size());
    }
    const unsigned freeAfter = gsys->getHeap(SYSHEAP_App)->getFree();
    gsys->setHeap(heap);
    std::printf("P2_%s_ANIMATION_READY heap_bytes=%d clips=%zu poses=%d resident_bytes=%zu gameplay=unchanged\n", tag,
                int(freeBefore) - int(freeAfter), f.profile.clips.size(), poses, resident);
    std::fflush(stdout);
}
}
bool pc_p2_kurage_visual_setup()
{
    if (sReady) return true;
    Shape* wait = load("courses/pikmin2room/kurage_wait.mod");
    Shape* attack = load("courses/pikmin2room/kurage_attack.mod");
    if (!wait || !attack) return false;
    sWait = wait;
    sAttack = attack;
    sShapes["wait"] = wait;
    sShapes["attack"] = attack;
    // Optional source poses; a missing file simply keeps the wait/attack pair.
    static const char* const optional[] = { "move1", "move2", "type1", "type2",
        "flick1", "flick2", "dead1", "dead2" };
    int loaded = 0;
    for (const char* name : optional) {
        std::string path = std::string("courses/pikmin2room/kurage_") + name + ".mod";
        if (Shape* shape = load(path.c_str())) { sShapes[name] = shape; ++loaded; }
    }
    std::printf("P2_KURAGE_VISUAL_POSES optional_loaded=%d/%d\n", loaded, 8);
    std::fflush(stdout);
    loadBank(false);
    sReady = true;
    return true;
}
void pc_p2_kurage_visual_reset()
{
    family(false).reset();
    family(true).reset();
    sShapesGreater.clear();
    sReadyGreater = false;
    sWait = nullptr;
    sAttack = nullptr;
    sReady = false;
    sShapes.clear();
}
Shape* pc_p2_kurage_visual_wait_shape() { return sWait; }
Shape* pc_p2_kurage_visual_attack_shape() { return sAttack; }
Shape* pc_p2_kurage_visual_shape(const char* motionBase)
{
    if (!motionBase || !*motionBase) return nullptr;
    auto it = sShapes.find(motionBase);
    return it == sShapes.end() ? nullptr : it->second;
}
// p2kurage::State: Dead=0, Wait=1, Move=2, Chase=3, Attack=4, Fall=5, Land=6,
// Ground=7, TakeOff=8, FlyFlick=9, GroundFlick=10, Drop=11.
const char* pc_p2_kurage_visual_motion_for_state(int state)
{
    switch (state) {
    case 0: return "dead1";
    case 1: return "wait";
    case 2: return "move1";
    case 3: return "move1";
    case 4: return "attack";
    // Kurage.h AnimID: Land = move2, TakeOff = type1, Fall = type2 (wave 3
    // flyers corrected the Fall/Land/TakeOff pose mapping, #960).
    case 5: return "type2";
    case 6: return "move2";
    case 7: return "wait";
    case 8: return "type1";
    case 9: return "flick1";
    case 10: return "flick2";
    case 11: return "type2";
    default: return nullptr;
    }
}
bool pc_p2_kurage_visual_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse)
{
    if (!sReady || !actor) return false;
    Shape* shape = corpse || actor->mTekiAnimator->getCurrentMotionIndex() != TekiMotion::Attack ? sWait : sAttack;
    if (!shape) return false;
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}

bool pc_p2_kurage_visual_setup_greater()
{
    if (sReadyGreater) return true;
    Shape* wait = load("courses/pikmin2room/onikurage_wait.mod");
    Shape* attack = load("courses/pikmin2room/onikurage_attack.mod");
    if (!wait || !attack) return false;
    sShapesGreater["wait"] = wait;
    sShapesGreater["attack"] = attack;
    static const char* const optional[] = { "move1", "move2", "type1", "type2",
        "flick1", "flick2", "dead1", "dead2" };
    int loaded = 0;
    for (const char* name : optional) {
        std::string path = std::string("courses/pikmin2room/onikurage_") + name + ".mod";
        if (Shape* shape = load(path.c_str())) { sShapesGreater[name] = shape; ++loaded; }
    }
    std::printf("P2_ONIKURAGE_VISUAL_POSES optional_loaded=%d/%d\n", loaded, 8);
    std::fflush(stdout);
    loadBank(true);
    sReadyGreater = true;
    return true;
}
Shape* pc_p2_kurage_visual_shape_greater(const char* motionBase)
{
    if (!motionBase || !*motionBase) return nullptr;
    auto it = sShapesGreater.find(motionBase);
    return it == sShapesGreater.end() ? nullptr : it->second;
}

// #972 pose bank -------------------------------------------------------------
Shape* pc_p2_kurage_visual_pose(BTeki* actor, bool greater, const char* clip, float sourceFrame, unsigned token)
{
    if (!actor || !clip || !*clip) return nullptr;
    Family& f = family(greater);
    const p2kuragebank::Clip* entry = f.profile.find(clip);
    if (!entry || !f.bank.ready()) return nullptr;
    const float last = float(entry->duration - 1);
    if (!(sourceFrame > 0.0f)) sourceFrame = 0.0f;
    if (sourceFrame > last) sourceFrame = last;
    // The first draw of an actor creates its private Shape: log what that cost
    // in the application heap (#972 evidence; one line per actor).
    const bool first = f.measured.insert(actor).second;
    const unsigned before = first ? gsys->getHeap(SYSHEAP_App)->getFree() : 0u;
    Shape* shape = f.actors.draw(actor, f.bank, clip, sourceFrame, token);
    if (first) {
        const unsigned after = gsys->getHeap(SYSHEAP_App)->getFree();
        std::printf("P2_%s_PRIVATE_SHAPE token=%u heap_free_before=%u heap_free_after=%u bytes=%d created=%d\n",
                    greater ? "ONIKURAGE" : "KURAGE", token, before, after, int(before) - int(after),
                    int(shape != nullptr));
        std::fflush(stdout);
    }
    return shape;
}
bool pc_p2_kurage_visual_proom(bool greater, const char* clip, float sourceFrame, float out[3])
{
    if (!clip || !out) return false;
    Family& f = family(greater);
    const p2kuragebank::Clip* entry = f.bank.ready() ? f.profile.find(clip) : nullptr;
    if (!entry) return false;
    const auto v = p2kuragebank::proomAt(*entry, sourceFrame);
    out[0] = v[0];
    out[1] = v[1];
    out[2] = v[2];
    return true;
}
float pc_p2_kurage_visual_last_frame(bool greater, const char* clip)
{
    Family& f = family(greater);
    const p2kuragebank::Clip* entry = clip && f.bank.ready() ? f.profile.find(clip) : nullptr;
    return entry ? float(entry->duration - 1) : -1.0f;
}
void pc_p2_kurage_visual_forget(BTeki* actor)
{
    family(false).actors.forget(actor);
    family(true).actors.forget(actor);
    family(false).measured.erase(actor);
    family(true).measured.erase(actor);
}

// #1065: settled carcass pose. Source Jellyfloats leave no carcass (the death
// clip ends in the burst, every joint scaled to nothing); the port's carried
// carcass rests in the flattest visible pose of the clip it died in, lifted onto
// the ground (p2kuragebank::settledIndex / groundLift).
Shape* pc_p2_kurage_visual_corpse(BTeki* actor, bool greater, const char* deathClip, unsigned token, float& lift)
{
    lift = 0.0f;
    if (!actor || !deathClip) return nullptr;
    Family& f = family(greater);
    const p2posefamily::Clip* clip = f.bank.ready() ? f.bank.clip(deathClip) : nullptr;
    if (!clip || clip->poses.size() != clip->frames.size()) return nullptr;
    auto it = f.settled.find(deathClip);
    if (it == f.settled.end()) {
        std::vector<p2kuragebank::Extent> extents;
        for (const p2pose::Pose& pose : clip->poses) {
            p2kuragebank::Extent e;
            if (!pose.positions.empty()) {
                float lo[3] = {pose.positions[0].x, pose.positions[0].y, pose.positions[0].z};
                float hi[3] = {lo[0], lo[1], lo[2]};
                for (const p2pose::Vec& q : pose.positions) {
                    const float c[3] = {q.x, q.y, q.z};
                    for (int k = 0; k < 3; ++k) { lo[k] = std::min(lo[k], c[k]); hi[k] = std::max(hi[k], c[k]); }
                }
                e.minY = lo[1];
                e.maxY = hi[1];
                e.width = std::max(hi[0] - lo[0], hi[2] - lo[2]);
            }
            extents.push_back(e);
        }
        Family::Settled st;
        const int index = p2kuragebank::settledIndex(extents);
        if (index >= 0) {
            st.ok = true;
            st.frame = float(clip->frames[std::size_t(index)]);
            st.lift = p2kuragebank::groundLift(extents[std::size_t(index)]);
        }
        std::printf("P2_%s_CORPSE_POSE clip=%s settled=%d index=%d frame=%.0f lift=%.1f height=%.1f width=%.1f "
                    "source_carcass=0\n",
                    greater ? "ONIKURAGE" : "KURAGE", deathClip, int(st.ok), index, st.frame, st.lift,
                    index >= 0 ? extents[std::size_t(index)].maxY - extents[std::size_t(index)].minY : 0.0f,
                    index >= 0 ? extents[std::size_t(index)].width : 0.0f);
        std::fflush(stdout);
        it = f.settled.emplace(deathClip, st).first;
    }
    if (!it->second.ok) return nullptr;
    Shape* shape = pc_p2_kurage_visual_pose(actor, greater, deathClip, it->second.frame, token);
    if (shape) lift = it->second.lift;
    return shape;
}
