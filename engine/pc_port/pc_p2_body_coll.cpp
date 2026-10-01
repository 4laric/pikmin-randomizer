#include "pc_p2_body_coll.h"

#include "pc_p2_body_fit.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_flyer_coll.h"
#include "pc_p2_pose_bank.h"
#include "gl/pc_gfx.h"
#include "Collision.h"
#include "Creature.h"
#include "teki.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {

struct Species {
    p2bodyfit::Table table;
    bool drawUnscaled = false;  // the species draw normalises the host scale away (Queen)
};

struct Bound {
    std::string key;
    P2FlyerColl coll;
    p2bodyfit::Table table;  // actor copy, offsets scaled by the host scale at bind
    float scale = 1.0f;
    bool bound = false;
    bool released = false;
    int stuckLogged = 0;
    int maxStuck = 0;
};

std::map<std::string, Species> species;
std::set<std::string> missing;  // species whose rest pose could not be fitted (logged once)
std::map<BTeki*, Bound> actors;

bool enabled()
{
    static const bool on = [] {
        const char* e = std::getenv("PIKMIN_P2_BODY_COLL");
        return !(e && e[0] == '0');
    }();
    return on;
}

// Species whose own module runs the source FSM on the host and never reads a
// host collision part, and that are not airborne (flyers own their tree,
// pc_p2_flyer_coll.h). The Chappy family keeps the host tree: its mouth slot
// lives there. Proxies keep the P1 host AI and so the host tree.
std::set<std::string>& extraKeys()
{
    static std::set<std::string> keys;
    return keys;
}

// The Snagret snakes (SnakeCrow/SnakeWhole) are jointed multi-segment bodies: a rest-pose fit
// is poor (max gap 65 on a 145-long neck), so they stay on the host tree until a lane adds them
// through pc_p2_body_coll_manage() with its own verification.
// ground|Armor is NOT here (#1014): the Armor wears the exact retail armor/enemycoll.txt tree (only the
// head sphere `dmg1` is stickable and damageable; the shell is neither), which a whole-body fit cannot
// express; pc_p2_armor.cpp owns that tree.
// aquatic|UmiMushi and aquatic|UmiMushiBlind are NOT here (#995): the Bloyster wears the exact retail
// umimushi/enemycoll.txt tree (only the tail bulb `weak` is stickable, plus the tongue mouth slots),
// which a whole-body fit cannot express; pc_p2_umimushi.cpp owns that tree.
bool managedKey(const std::string& key)
{
    static const std::set<std::string> keys = {
        "ground|Hana",        "ground|Sokkuri",        "ground|ElecBug",
        "ground|TamagoMushi", "ground|Imomushi",       "aquatic|Catfish",  "aquatic|Tadpole",
        "aquatic|Jigumo",   "snagret|DangoMushi",
        "bulblax|Queen",
    };
    return keys.count(key) != 0 || extraKeys().count(key) != 0;
}

std::set<std::string>& unscaledExtra()
{
    static std::set<std::string> keys;
    return keys;
}

bool unscaledKey(const std::string& key) { return key == "bulblax|Queen" || unscaledExtra().count(key) != 0; }

bool loadStem(const std::string& stem, p2pose::Baked& out)
{
    std::ifstream in("assets/dataDir/courses/pikmin2room/" + stem + "_00.mod", std::ios::binary | std::ios::ate);
    if (!in) return false;
    const auto size = in.tellg();
    if (size <= 0 || size > 1024 * 1024) return false;
    in.seekg(0);
    std::vector<unsigned char> data(size_t(size), 0);
    if (!in.read(reinterpret_cast<char*>(data.data()), size)) return false;
    return p2pose::decodeBaked(data, out);
}

bool fitPose(const std::string& key, const p2pose::Pose& rest)
{
    Species s;
    s.drawUnscaled = unscaledKey(key);
    p2bodyfit::Table t;
    const auto& v = rest.positions;
    if (!p2bodyfit::fit(v.size(), [&v](std::size_t i) { return p2bodyfit::V3{v[i].x, v[i].y, v[i].z}; }, t)) {
        std::printf("P2_BODY_COLL_FIT key=%s ok=0 vertices=%zu\n", key.c_str(), v.size());
        std::fflush(stdout);
        return false;
    }
    s.table = t;
    species[key] = s;
    std::printf("P2_BODY_COLL_FIT key=%s ok=1 vertices=%zu spheres=%d bounds=%.1f,%.1f,%.1f..%.1f,%.1f,%.1f "
                "root_r=%.1f mean_gap=%.2f max_gap=%.2f",
                key.c_str(), v.size(), t.count - 1, double(t.bounds[0]), double(t.bounds[1]), double(t.bounds[2]),
                double(t.bounds[3]), double(t.bounds[4]), double(t.bounds[5]), double(t.spheres[0].radius),
                double(t.meanGap), double(t.maxGap));
    for (int i = 1; i < t.count; ++i)
        std::printf(" %s=r%.1f@(%.1f,%.1f,%.1f)", t.spheres[i].id, double(t.spheres[i].radius),
                    double(t.spheres[i].offset.x), double(t.spheres[i].offset.y), double(t.spheres[i].offset.z));
    std::printf("\n");
    std::fflush(stdout);
    return true;
}

// Species with no draw-family bank the module can see load their own rest pose.
const Species* speciesFor(const std::string& key)
{
    auto it = species.find(key);
    if (it != species.end()) return &it->second;
    if (key == "bulblax|Queen" && !missing.count(key)) {
        p2pose::Baked rest;
        if (loadStem("bulblax_Queen_wait1", rest) && fitPose(key, rest.pose)) return &species[key];
        missing.insert(key);
        std::printf("P2_BODY_COLL_FIT key=%s ok=0 reason=rest_pose_missing\n", key.c_str());
        std::fflush(stdout);
    }
    return nullptr;
}

p2flyer::Vec3 pos(const Vector3f& v) { return p2flyer::Vec3{v.x, v.y, v.z}; }

}  // namespace

void pc_p2_body_coll_manage(const std::string& key, bool drawUnscaled)
{
    extraKeys().insert(key);
    if (drawUnscaled) unscaledExtra().insert(key);
}

void pc_p2_body_coll_reset()
{
    // Actor trees are never freed (stuck Pikmin may hold part pointers); the stage teardown
    // that calls this has already cleared the actors.
    actors.clear();
    species.clear();
    missing.clear();
}

void pc_p2_body_coll_forget(BTeki* actor)
{
    auto it = actors.find(actor);
    if (it == actors.end()) return;
    it->second.coll.detach(actor);
    actors.erase(it);
}

bool pc_p2_body_coll_register_pose(const std::string& key, const p2pose::Pose& rest)
{
    if (!managedKey(key)) return false;
    if (species.count(key)) return true;
    return fitPose(key, rest);
}

void pc_p2_body_coll_assign(BTeki* actor, const std::string& key)
{
    if (!actor || !managedKey(key)) return;
    if (actors.count(actor)) return;
    Bound b;
    b.key = key;
    actors.emplace(actor, std::move(b));
}

bool pc_p2_body_coll_bound(const BTeki* actor)
{
    auto it = actors.find(const_cast<BTeki*>(actor));
    return it != actors.end() && it->second.bound && !it->second.released;
}

void pc_p2_body_coll_update(BTeki* actor)
{
    if (!actor) return;
    auto it = actors.find(actor);
    if (it == actors.end()) {
        // Queen: the actor is identified by its campaign source (the Queen draw
        // family loads its own poses, so no bank assigns it).
        if (actor->mGenerator && pc_p2_campaign_source(actor) == 30) {
            pc_p2_body_coll_assign(actor, "bulblax|Queen");
            it = actors.find(actor);
        }
        if (it == actors.end()) return;
    }
    Bound& b = it->second;
    if (b.released) return;
    const bool dead = actor->mHealth <= 0.0f || actor->mDeadState != 0;
    if (!b.bound) {
        // PIKMIN_P2_BODY_COLL=0 keeps the host tree (the actor stays registered for the stick log).
        const Species* sp = dead || !enabled() ? nullptr : speciesFor(b.key);
        if (!sp || !actor->mCollInfo) return;
        b.table = sp->table;
        b.scale = sp->drawUnscaled ? 1.0f : actor->mSRT.s.x;
        if (!(b.scale > 0.01f && b.scale < 100.0f)) b.scale = 1.0f;
        for (int i = 0; i < b.table.count; ++i) {
            b.table.spheres[i].offset.x *= b.scale;
            b.table.spheres[i].offset.y *= b.scale;
            b.table.spheres[i].offset.z *= b.scale;
        }
        const float hostRoot = actor->mCollInfo->hasInfo() && actor->mCollInfo->getBoundingSphere()
            ? actor->mCollInfo->getBoundingSphere()->mRadius
            : -1.0f;
        if (!b.coll.bind(actor, b.table.spheres, b.table.count)) {
            b.released = true;
            return;
        }
        b.bound = true;
        std::printf("P2_BODY_COLL_BIND key=%s generator=%u source=%u spheres=%d scale=%.2f host_root_r=%.1f "
                    "own_root_r=%.1f\n",
                    b.key.c_str(), pc_p2_campaign_token(actor), pc_p2_campaign_source(actor), b.table.count - 1,
                    double(b.scale), double(hostRoot), double(b.table.spheres[0].radius * b.scale));
        std::fflush(stdout);
    }
    if (dead) {
        // The host funnel (die/dieSoon) needs its own tree for the carcass and cent parts.
        const p2flyer::Vec3 root = pos(actor->getPosition());
        const p2flyer::Vec3 c = p2flyer::sphereCentre(b.table.spheres, b.table.count, 0, root, actor->getDirection(),
                                                      p2flyer::Vec3{});
        b.coll.release(actor, c);
        b.released = true;
        std::printf("P2_BODY_COLL_RELEASE key=%s generator=%u max_stuck=%d\n", b.key.c_str(),
                    pc_p2_campaign_token(actor), b.maxStuck);
        std::fflush(stdout);
        return;
    }
    b.coll.follow(actor, pos(actor->getPosition()), actor->getDirection(), p2flyer::Vec3{}, b.scale);
}

void pc_p2_body_coll_note_stick(Creature* sticker, Creature* target, CollPart* part)
{
    if (!sticker || !target || !target->isTeki() || !part) return;
    BTeki* teki = static_cast<BTeki*>(target);
    auto it = actors.find(teki);
    // A registered species logs with and without the own tree (A/B evidence).
    if (it == actors.end()) return;
    Bound& b = it->second;
    int stuck = 0;
    for (Creature* c = teki->mStickListHead; c; c = c->mNextSticker)
        if (c->isPiki()) ++stuck;
    if (stuck > b.maxStuck) b.maxStuck = stuck;
    if (b.stuckLogged >= 24) return;
    ++b.stuckLogged;
    const Vector3f p = sticker->mSRT.t;
    const float dx = p.x - part->mCentre.x, dy = p.y - part->mCentre.y, dz = p.z - part->mCentre.z;
    const float dist = std::sqrt(dx * dx + dy * dy + dz * dz);
    const Vector3f a = sticker->mAttachPosition;
    std::printf("P2_STICK key=%s generator=%u own_tree=%d part=%s radius=%.1f centre=(%.1f,%.1f,%.1f) "
                "pikmin=(%.1f,%.1f,%.1f) dist=%.1f surface_gap=%.1f attach_local=(%.1f,%.1f,%.1f) "
                "attach_len=%.1f stuck=%d target=(%.1f,%.1f,%.1f) yaw=%.2f\n",
                b.key.c_str(), pc_p2_campaign_token(teki), b.bound && !b.released ? 1 : 0,
                part->mCollInfo ? part->mCollInfo->mId.mStringID : "?", double(part->mRadius), double(part->mCentre.x),
                double(part->mCentre.y), double(part->mCentre.z), double(p.x), double(p.y), double(p.z), double(dist),
                double(dist - part->mRadius), double(a.x), double(a.y), double(a.z),
                double(std::sqrt(a.x * a.x + a.y * a.y + a.z * a.z)), stuck, double(teki->mSRT.t.x),
                double(teki->mSRT.t.y), double(teki->mSRT.t.z), double(teki->getDirection()));
    std::fflush(stdout);
    // Probe screenshots (PIKMIN_P2_PROXY_SHOT): once per species/tree mode when three and six are latched.
    if (stuck == 3 || stuck == 6) {
        std::string name = "x|";
        const size_t bar = b.key.find('|');
        name += (bar == std::string::npos ? b.key : b.key.substr(bar + 1));
        name += b.bound && !b.released ? "_stick_fit" : "_stick_host";
        name += stuck == 3 ? "3" : "6";
        pc_gfx_proxy_shot_notify_after(name.c_str(), 3);
    }
}
