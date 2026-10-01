#include "pc_p2_campaign_actor.h"
// P2 Mamuta source pose banks on exact P1 Miurin actors. In bridge-mode
// campaign sessions the P2 FSM (pc_p2_mamuta_fsm) owns registered actors and
// the P1 host AI is suppressed; outside bridge (room preview without
// p2-mamuta-fsm.txt) gameplay stays P1.
#include "pc_p2_mamuta.h"
#include "pc_p2_mamuta_fsm.h"
#include "pc_p2_mamuta_policy.h"
#include "pc_p2_mamuta_rules.h"
#include "pc_p2_animation.h"
#include "pc_p2_pose_family.h"
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
#include <cmath>
static_assert(TEKI_Miurin == 24 && TekiMotion::Dead == 0 && TekiMotion::Wait1 == 2
              && TekiMotion::WaitAct1 == 4 && TekiMotion::Move1 == 6 && TekiMotion::Attack == 8
              && TekiMotion::Flick == 9 && TekiMotion::Type1 == 10 && TekiMotion::Type5 == 14,
              "Mamuta source anchor policy must track native enum values");
namespace {
const char* names[] = {"wait", "waitact", "move", "attack0", "attack1", "attack4",
                       "flick", "dead", "type5"};
constexpr int kClips = 9;
constexpr int kMaxPoses = p2mamuta::kMaxPoses; // dense import banks (even + event frames)
static_assert(kClips == p2mamuta::kClips, "Mamuta clip bank and policy disagree");
std::vector<Shape*> banks[kClips];
bool animated[kClips] = {};
int sourceFrames[kClips] = {};     // clip length in source frames, 0 = unknown
std::vector<int> sampleFrames[kClips];
std::vector<int> eventFrames[kClips];
std::map<BTeki*, unsigned> actors;
std::set<std::pair<BTeki*, int>> logged;
size_t bytesTotal = 0;
p2poseload::Shared poseShared;                 // #895 compact loader state
p2posefamily::Bank poseBank("MAMUTA");         // #895 lerp + crossfade
p2posefamily::Actors poseVis;
void fail() { std::fputs("P2_MAMUTA invalid profile\n", stderr); std::abort(); }
Shape* loadOne(const std::string& name) {
    std::ifstream file("assets/dataDir/courses/pikmin2room/" + name, std::ios::binary | std::ios::ate);
    if (!file) return nullptr;
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
int clipIndex(const std::string& name) {
    for (int k=0; k<kClips; ++k) if (name == names[k]) return k;
    return -1;
}
// Load `miulin_<clip>_00.mod`..`_NN.mod` as a time-sampled bank through the
// compact loader (#895: a few Shapes per clip plus decoded vectors, so dense
// banks fit the resident budget; the Shapes stay the nearest-pose fallback).
// The pose count comes from the manifest when present, else from the files
// on disk. A single-pose legacy install still loads as a one-frame bank.
void loadBank(int k) {
    const std::string base = std::string("miulin_") + names[k];
    int count = int(sampleFrames[k].size());
    if (!count) {
        while (count < kMaxPoses && std::ifstream(p2poseload::stemPath(true, base, count), std::ios::binary)) ++count;
    }
    if (count > 0) {
        std::string error;
        const int duration = sourceFrames[k] > 0 ? sourceFrames[k] : count;
        if (!p2posefamily::loadFamilyClip(poseBank, names[k], base, count, duration, sampleFrames[k], poseShared,
                                          bytesTotal, banks[k], error)) {
            std::fprintf(stderr, "P2_MAMUTA_BANK_INVALID clip=%s reason=%s\n", names[k], error.c_str());
            fail();
        }
        animated[k] = banks[k].size() > 1;
        return;
    }
    Shape* pose = loadOne(base + ".mod");
    if (!pose) fail();
    banks[k].push_back(pose);
    animated[k] = false;
}
// Optional bank manifest carrying the clip length, sampled source frames and
// gameplay event frames, so the observer can place the strike at its sampled
// event frame instead of a uniform pose index.
void loadManifest() {
    std::ifstream in("p2-mamuta-bank.txt");
    if (!in) return;
    std::string magic, word; int count = 0;
    if (!(in >> magic >> count) || magic != "P2_MAMUTA_BANK_1" || count != kClips) fail();
    for (int row = 0; row < count; ++row) {
        std::string name; int source = 0, poseCount = 0, eventCount = 0;
        if (!(in >> word >> name >> source >> poseCount >> eventCount) || word != "clip") fail();
        const int k = clipIndex(name);
        if (k < 0 || source < 1 || poseCount < 1 || poseCount > kMaxPoses || eventCount < 0) fail();
        sourceFrames[k] = source;
        if (!(in >> word) || word != "frames") fail();
        sampleFrames[k].resize(poseCount);
        for (int i = 0; i < poseCount; ++i) {
            if (!(in >> sampleFrames[k][i])) fail();
            if (sampleFrames[k][i] < 0 || sampleFrames[k][i] >= source) fail();
            if (i && sampleFrames[k][i] <= sampleFrames[k][i-1]) fail();
        }
        if (!(in >> word) || word != "events") fail();
        eventFrames[k].resize(eventCount);
        for (int i = 0; i < eventCount; ++i) {
            if (!(in >> eventFrames[k][i])) fail();
            if (eventFrames[k][i] < 0 || eventFrames[k][i] >= source) fail();
        }
    }
    if (in >> word) fail();
}
}
void pc_p2_mamuta_reset() {
    actors.clear(); logged.clear();
    poseShared = p2poseload::Shared(); poseBank.reset(); poseVis.clear();
    for (int k=0; k<kClips; ++k) {
        banks[k].clear(); animated[k]=false; sourceFrames[k]=0;
        sampleFrames[k].clear(); eventFrames[k].clear();
    }
    bytesTotal=0; pc_p2_mamuta_rules_reset();
}
bool pc_p2_mamuta_is_bound(BTeki* actor) { return actors.find(actor) != actors.end(); }
bool pc_p2_mamuta_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    auto it = actors.find(static_cast<BTeki*>(view));
    if (it == actors.end()) return false;
    generator = it->second;
    return true;
}
void pc_p2_mamuta_forget(BTeki* actor) {
    actors.erase(actor); poseVis.forget(actor);
    for (int k=0; k<kClips; ++k) logged.erase({actor,k});
}
void pc_p2_mamuta_setup() {
    pc_p2_mamuta_reset();
    if (!pc_pikipelago_room_preview() && !pc_randomizer_p2_bridge()) return;
    std::ifstream in("p2-mamuta-actors.txt"); if (!in) return;
    std::string word; int count;
    if (!(in>>word>>count) || word!="P2_MAMUTA_ACTORS_1" || count<1 || count>100 || !tekiMgr) fail();
    std::set<unsigned> wanted, found;
    for (int i=0; i<count; ++i) {
        unsigned long long id;
        if (!(in>>id>>word) || id>0xffffffffULL || word!="Miulin" || !wanted.insert(unsigned(id)).second) fail();
    }
    if (in>>word) fail();
    if (pc_randomizer_p2_bridge()) {
        wanted = pc_p2_campaign_ids(54);
        if (wanted.empty()) return;
    }
    Iterator it(tekiMgr); CI_LOOP(it) {
        Teki* actor=static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator || !wanted.count(pc_p2_campaign_token(actor))) continue;
        unsigned id=pc_p2_campaign_token(actor);
        if (actor->mTekiType!=TEKI_Miurin) {
            // #948: wrong vehicle (protected slot, pack generator, proxy
            // override). Refuse this actor with a reason; never abort a campaign.
            if (!pc_randomizer_p2_bridge()) fail();
            std::printf("P2_MAMUTA_UNBOUND generator=%u source_id=54 type=%d reason=host_type_mismatch\n", id, int(actor->mTekiType));
            std::fflush(stdout);
            continue;
        }
        if (!found.insert(id).second) {
            if (!pc_randomizer_p2_bridge()) fail();
            std::printf("P2_MAMUTA_UNBOUND generator=%u source_id=54 reason=duplicate_generator\n", id);
            std::fflush(stdout);
            continue;
        }
        actors.emplace(actor,id);
    }
    if (found!=wanted) {
        if (!pc_randomizer_p2_bridge()) fail();
        // Campaign actors span areas/days; a bound id with no live actor
        // here is expected. Report it and bind the ones that are present.
        std::printf("P2_MAMUTA_MISSING source_id=54 wanted=%zu found=%zu\n", wanted.size(), found.size());
        std::fflush(stdout);
        if (found.empty()) return;
    }
    pc_p2_mamuta_rules_setup();
    loadManifest();
    for (int k=0; k<kClips; ++k) loadBank(k);
    for (const auto& e: actors) {
        // deliv4 (#871): lane-06 ordinary-delivery source bind so
        // GoalItem::suckMe grants onion:p2:54 instead of suppressing the P1
        // host CHECK (bc6/bc7 hauled the corpse with carriers>0 but no receipt:
        // P2_P1_CHECK_SUPPRESSED host_type=24). Mirrors Otakara/Kurage/ElecBug.
        // Single-use: consumed on delivery, cleared on forget/recycle.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(e.first), 54, e.second);
        std::printf("P2_MAMUTA_DELIVERY_BIND generator=%u source_id=54\n", e.second);
        // own44b (#871): the bank binding is gameplay-neutral; in bridge mode
        // (and not room preview, or with p2-mamuta-fsm.txt) pc_p2_mamuta_fsm
        // owns the actor and the P1 host AI is suppressed (BTeki::doAI
        // early-return at src/plugPikiNakata/tekibteki.cpp:639, driven
        // per-frame by BTeki::update at tekibteki.cpp:522 - same pattern as
        // pc_p2_armor_suppress_ai at tekibteki.cpp:660). Predicate exactly
        // matches pc_p2_mamuta_fsm_setup's bridge gate.
        const bool fsmOwns = (pc_randomizer_p2_bridge() && !pc_pikipelago_room_preview()) || std::ifstream("p2-mamuta-fsm.txt").good();
        std::printf("P2_MAMUTA_READY generator=%u native_type=24 xyz=%.6f,%.6f,%.6f %s\n", e.second,e.first->mSRT.t.x,e.first->mSRT.t.y,e.first->mSRT.t.z,
            fsmOwns ? "source_pose_banks_FSM_owned_P2_planting" : "P1_proxy_source_pose_banks_no_P2_planting");
    }
}
bool pc_p2_mamuta_draw(BTeki* actor, Graphics& gfx, const Matrix4f& view, bool corpse) {
    auto entry=actors.find(actor);
    if (entry==actors.end() || !gfx.mCamera || !actor->mTekiAnimator) return false;
    const int motion=actor->mTekiAnimator->getCurrentMotionIndex();
    int k=p2mamuta::anchor(actor->mTekiType,motion,corpse);
    if (k<0 || banks[k].empty()) return false;
    const int poses = int(banks[k].size());
    int index = 0;
    float srcFrame = 0.0f;
    if (animated[k] && poses > 1) {
        const int frames = actor->mTekiAnimator->getFrameCount();
        const int counter = actor->mTekiAnimator->getCounter();
        if (frames > 1 && counter >= 0) {
            float phase = float(counter) / float(frames - 1);
            if (phase < 0.0f) phase = 0.0f;
            if (phase > 1.0f) phase = 1.0f;
            if (sourceFrames[k] > 0 && int(sampleFrames[k].size()) == poses) {
                // Source-frame timeline: place each sampled pose at its true
                // source frame (and its event frame) rather than a uniform index.
                srcFrame = phase * float(sourceFrames[k] - 1);
                const int selected = p2mamuta::selectSample(srcFrame, sampleFrames[k].data(), poses);
                if (selected < 0) return false;
                index = selected;
            } else {
                index = int(phase * float(poses - 1) + 0.5f);
                if (index >= poses) index = poses - 1;
            }
        }
    }
    Shape* shape = banks[k][index];
    if (animated[k] && poses > 1) {
        // #895: lerp + crossfade into a private Shape; nearest pose stays the fallback.
        const int frames = actor->mTekiAnimator->getFrameCount();
        const float counter = actor->mTekiAnimator->getCounter();
        float phase = frames > 1 && std::isfinite(counter) ? counter / float(frames - 1) : 0.0f;
        phase = phase < 0.0f ? 0.0f : (phase > 1.0f ? 1.0f : phase);
        const p2posefamily::Clip* clip = poseBank.clip(names[k]);
        if (clip) {
            const float frame = corpse ? float(clip->duration - 1) : phase * float(clip->duration - 1);
            if (Shape* smooth = poseVis.draw(actor, poseBank, names[k], frame, entry->second)) shape = smooth;
        }
    }
    shape->updateAnim(gfx,view,nullptr,actor);
    shape->drawshape(gfx,*gfx.mCamera,nullptr);
    if (logged.insert({actor,k}).second)
        std::printf("P2_MAMUTA_DRAW generator=%u anchor=%s poses=%d animated=%d src_frame=%.1f sample=%d events=%d %s\n",
                    entry->second,names[k],poses,int(animated[k]),srcFrame,index,int(eventFrames[k].size()),
                    pc_p2_mamuta_fsm_suppress_ai(actor) ? "OWN_FSM_driven" : "P1_gameplay_unchanged");
    return true;
}
