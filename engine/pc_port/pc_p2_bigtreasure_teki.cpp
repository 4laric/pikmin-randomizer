#include "pc_p2_bigtreasure_teki.h"
#include "pc_p2_sfx.h"
#include "pc_p2_bigtreasure_own.h"
#include "pc_p2_bigtreasure_map_trace.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_navi_select.h"
#include "pc_p2_species.h"
#include "pc_p2_animation.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_attack_fx_host.h"
#include "pc_p2_bigtreasure_fx.h"
#include "pc_p2_test_day_cycle.h"
#include "pc_bbft.h"
#include "Collision.h"
#include "Generator.h"
#include "GlobalGameOptions.h"
#include "Graphics.h"
#include "Interactions.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Shape.h"
#include "Texture.h"
#include "gameflow.h"
#include "gl/pc_gfx.h"
#include "system.h"
#include "teki.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>

extern Matrix4f invCamMat; // collInfo.cpp: camera inverse used by CollPart::getMatrix

namespace {
using namespace p2btown;

const char* weaponName(int w) {
    switch (w) {
    case P2BTWEAPON_Elec: return "elec";
    case P2BTWEAPON_Fire: return "fire";
    case P2BTWEAPON_Gas: return "gas";
    case P2BTWEAPON_Water: return "water";
    default: return "louie";
    }
}

struct DroppedWeapon {
    int weapon = -1;
    Vector3f pos, vel;
    bool resting = false;
};

// Own collision (#246 fix stage): the retail enemycoll.txt tree as real P1
// CollParts on the Titan, replacing the Swallow host's CollInfo while bound.
struct OwnColl {
    CollInfo* host = nullptr;          // the host's CollInfo, restored on forget
    CollInfo* own = nullptr;           // never freed (see restoreHostColl)
    std::vector<ObjCollInfo*> nodes;   // sColl order
    std::vector<CollPart*> parts;      // sColl order (nullptr if not built)
    bool unarmedCodes = false;         // tam1/tam2 switched to 'st__'
};

struct Binding {
    unsigned generator = 0;
    int sfxSteps = 0;          // gait step counter last voiced (#946)
    Vector3f hold;             // bind position: Stay/Land keep the host here
    Fsm fsm;
    OwnColl coll;
    int recvStim = 0, recvAccepted = 0, recvNaviFallback = 0;
    std::vector<Hit> pending;   // hits recorded by interactDefault since the last tick
    float debt = 0.0f;         // 30 Hz source clock debt
    float lastHealth = 0.0f;
    bool deadLogged = false;
    bool escaped = false;
    bool began = false;        // host death funnel ran (corpse pellet)
    float logTimer = 0.0f;
    int attacks = 0;
    bool emitLogged = false;
    int ignored = 0;
    std::vector<DroppedWeapon> dropped;
    std::map<const void*, int> recvCount;
    // Visual-only weapon effects (pc_p2_bigtreasure_fx.h): owner-killed on
    // attack end, state change, death, forget and reset.
    std::unique_ptr<p2attackfx::Emitter> fx; // lazily created; owner-kills every generator on destruction
    p2attackfx::Session fxSession;
    p2titanfx::State fxState;
    int waterShots = 0;
    std::vector<std::pair<unsigned, int>> waterDump; // probe-only frame dumps: (session tick, shot*10+phase)
    int fxEmits = 0;           // water shots this frame (sum of per-tick emits)
};
std::map<BTeki*, Binding> s;

Params sParams;
Bank sBank = defaultBank();
p2btown::Animator sAnimator;
bool sReady = false;
P2BigTreasureMapTrace* sTrace = nullptr;
std::vector<Shape*> sPoses[AnimCount];
// #246/#972 (owner 2026-09-30 "needs way more poses"): the dense bank (up to 48
// poses per clip) loads through the compact pose loader and draws through the
// shared #895 pose path (bracket + lerp into a private Shape per actor,
// crossfade on clip change). sPoses keeps the nearest-pose fallback.
p2posefamily::Bank sPoseBank("BIGTREASURE");
p2posefamily::Actors sPoseVis;
// Resident budget for the dense Titan bank. Measured on the retail extract
// (48 poses/clip, 1181 poses): largest clip 1.64 MiB, whole bank 41.4 MiB
// resident (4 full Shapes + 24 B per vertex-pair per other pose), so the
// shared 1 MiB per-clip default is raised to 2 MiB; the 48 MiB total stands.
constexpr std::size_t kTitanClipBytes = 2u * 1024u * 1024u;
Shape* sPellet[P2BTWEAPON_Count] = {};
bool sPosesLoaded = false;
std::map<BTeki*, int> sDrawLogged;
std::vector<CollNode> sColl;          // retail enemycoll.txt (pre-order)
bool sSetupDone = false;              // late spawns bind lazily after setup
std::set<BTeki*> sConsidered;         // actors already checked for a lazy bind
// Host CollInfo per actor that currently wears an own CollInfo. forget()
// restores it on the death funnel / pool reuse; reset() (stage boundary)
// restores every remaining entry and clears the map.
std::map<BTeki*, CollInfo*> sHostColl;

u32 fourcc(const std::string& id) {
    u32 v = 0;
    for (int i = 0; i < 4; ++i) v = (v << 8) | u32(static_cast<unsigned char>(i < int(id.size()) ? id[i] : '_'));
    return v;
}

int partOf(const Binding& b, const CollPart* part) {
    if (!part) return PartNone;
    for (std::size_t i = 0; i < b.coll.parts.size(); ++i)
        if (b.coll.parts[i] == part) {
            const int w = weaponForPartId(sColl[i].id);
            return w >= 0 ? w : PartOther;
        }
    return PartOther;
}

Binding* find(const BTeki* t) {
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? nullptr : &i->second;
}

Shape* loadPellet(const std::string& rel) {
    const std::string path = "assets/dataDir/courses/pikmin2room/" + rel;
    std::ifstream probe(path, std::ios::binary);
    if (!probe) return nullptr;
    Shape* shape = gameflow.loadShape(("courses/pikmin2room/" + rel).c_str(), true);
    if (shape)
        for (int t = 0; t < shape->mTexAttrCount; ++t)
            if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
    return shape;
}

bool loadInputs(bool bridge) {
    sParams = Params{};
    {
        std::ifstream in("p2-bigtreasure-parms.txt");
        std::string error;
        if (!in) {
            std::printf("P2_BIGTREASURE_PARMS_MISSING fallback=disc_defaults\n");
        } else if (!parseEnemyParm(in, sParams, error)) {
            std::printf("P2_BIGTREASURE_PARMS_INVALID reason=%s\n", error.c_str());
            return !pc_p2_setup_skip(bridge, "BigTreasure", "parms_invalid");
        }
    }
    std::printf("P2_BIGTREASURE_PARMS source_id=73 retail=%d health=%.1f move=%.1f turn=%.1f private=%.1f "
                "territory=%.1f sight=%.1f attack=%.1f ik_base=%.2f wait_e=%.2f wait_f=%.2f/%.2f wait_g=%.2f "
                "wait_w=%.2f atk_max=%.1f/%.1f/%.1f/%.1f\n",
                sParams.retail ? 1 : 0, sParams.health, sParams.moveSpeed, sParams.maxTurnAngle, sParams.privateRadius,
                sParams.territoryRadius, sParams.sightRadius, sParams.attackDamage, sParams.baseFactor, sParams.elecWait,
                sParams.fireWait1, sParams.fireWait2, sParams.gasWait, sParams.waterWait, sParams.elecAttackMax,
                sParams.fireAttackMax, sParams.gasAttackMax, sParams.waterAttackMax);
    {
        std::ifstream in("p2_bigtreasure_events.txt", std::ios::binary);
        std::string error;
        if (!in) {
            std::printf("P2_BIGTREASURE_EVENTS_MISSING\n");
            return !pc_p2_setup_skip(bridge, "BigTreasure", "events_missing");
        }
        try {
            const p2retail::Table table = p2retail::read(in);
            if (!sAnimator.load(table, error)) {
                std::printf("P2_BIGTREASURE_EVENTS_INVALID reason=%s\n", error.c_str());
                return !pc_p2_setup_skip(bridge, "BigTreasure", "events_invalid");
            }
        } catch (const std::exception&) {
            std::printf("P2_BIGTREASURE_EVENTS_INVALID reason=table\n");
            return !pc_p2_setup_skip(bridge, "BigTreasure", "events_invalid");
        }
    }
    {
        std::ifstream in("p2-bigtreasure-coll.txt");
        std::string error;
        if (!in) {
            std::printf("P2_BIGTREASURE_COLL_MISSING\n");
            return !pc_p2_setup_skip(bridge, "BigTreasure", "coll_missing");
        }
        if (!parseCollTree(in, sColl, error)) {
            std::printf("P2_BIGTREASURE_COLL_INVALID reason=%s\n", error.c_str());
            return !pc_p2_setup_skip(bridge, "BigTreasure", "coll_invalid");
        }
        std::printf("P2_BIGTREASURE_COLL nodes=%zu source=enemycoll.txt\n", sColl.size());
    }
    sBank = defaultBank();
    {
        std::ifstream in("p2-bigtreasure-bank.txt");
        std::string error;
        if (in && !parseBank(in, sBank, error)) {
            std::printf("P2_BIGTREASURE_BANK_INVALID reason=%s fallback=bind_pose draw=host\n", error.c_str());
            sBank = defaultBank();
        }
    }
    // Poses: bigtreasure_<clip>_<ii>.mod; slot 29 (Walk) reuses wait2's.
    for (auto& v : sPoses) v.clear();
    for (Shape*& p : sPellet) p = nullptr;
    sPosesLoaded = false;
    sPoseBank.reset();
    sPoseVis.clear();
    p2poseload::Shared shared;
    std::size_t total = 0, poses = 0, minPoses = 0, maxPoses = 0;
    p2poseload::Limits limits = p2poseload::defaultLimits();
    limits.clipBytes = kTitanClipBytes;
    bool ok = sBank.staged;
    for (int a = 0; ok && a < AnimCount; ++a) {
        if (a == AnimWait2_2) continue;
        const ClipBank& clip = sBank.clip[a];
        if (clip.poses.empty()) continue;
        std::vector<int> frames;
        for (const auto& pose : clip.poses) frames.push_back(pose.frame);
        // A clip whose last converted pose is before its final source frame
        // (dead: the body scales to nothing at the end, Singular animation
        // scale) is bank-valid over the converted span.
        const int duration = frames.back() + 1 < clip.frames ? frames.back() + 1 : clip.frames;
        std::string why;
        if (!p2posefamily::loadFamilyClip(sPoseBank, clip.name, std::string("bigtreasure_") + clip.name,
                                          int(clip.poses.size()), duration, frames, shared, total, sPoses[a], why, limits)) {
            std::printf("P2_BIGTREASURE_POSE_MISSING clip=%s reason=%s\n", clip.name.c_str(), why.c_str());
            ok = false;
            break;
        }
        poses += clip.poses.size();
        minPoses = minPoses ? std::min(minPoses, clip.poses.size()) : clip.poses.size();
        maxPoses = std::max(maxPoses, clip.poses.size());
    }
    if (ok) sPoses[AnimWait2_2] = sPoses[AnimWait2];
    if (!ok) for (auto& v : sPoses) v.clear();
    sPosesLoaded = ok && poses > 0;
    if (sPosesLoaded) {
        const p2motion::Tunables& tune = p2motion::tunables();
        std::printf("P2_BIGTREASURE_INTERPOLATION_READY interpolation=%d clips=%zu poses=%zu poses_per_clip=%zu..%zu "
                    "resident_bytes=%zu clip_limit=%zu total_limit=%zu crossfade_ms=%d gameplay_clock=P1\n",
                    int(tune.lerp && sPoseBank.ready()), sPoseBank.clipCount(), poses, minPoses, maxPoses, total,
                    limits.clipBytes, limits.totalBytes, int(tune.crossfadeSeconds * 1000.f + .5f));
    }
    int pellets = 0;
    for (int w = 0; w < P2BTWEAPON_Count && sPosesLoaded; ++w) {
        char rel[96];
        std::snprintf(rel, sizeof(rel), "bigtreasure_pellet_%s.mod", weaponName(w));
        sPellet[w] = loadPellet(rel);
        if (sPellet[w]) ++pellets;
    }
    std::printf("P2_BIGTREASURE_BANK staged=%d legs_staged=%d leg_distance=%.1f poses=%zu bytes=%zu pellets=%d draw=%s\n",
                sBank.staged ? 1 : 0, sBank.legs.staged ? 1 : 0, sBank.legs.distance, sPosesLoaded ? poses : std::size_t(0),
                total, pellets, sPosesLoaded ? "p2_model" : "host");
    std::fflush(stdout);
    return true;
}

// Snapshot in source manager order: captains, then Piki.
struct Snapshot {
    std::vector<Candidate> c;
    std::vector<Creature*> who;
};
void buildSnapshot(BTeki* self, const Binding& b, Snapshot& snap) {
    snap.c.clear();
    snap.who.clear();
    auto add = [&](Creature* cr, Candidate cand) {
        const Vector3f p = cr->getPosition();
        cand.id = std::uint64_t(snap.who.size() + 1);
        cand.pos = {p.x, p.y, p.z};
        cand.alive = cr->isAlive();
        snap.c.push_back(cand);
        snap.who.push_back(cr);
    };
    for (Navi* n : pc_p2_navis()) {
        if (!n) continue;
        Candidate cand;
        cand.navi = true;
        add(n, cand);
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p) continue;
            Candidate cand;
            cand.pikmin = true;
            Creature* stick = p->getStickObject();
            cand.stuckToSelf = stick == self;
            cand.stuckElsewhere = stick && stick != self;
            cand.stuckPart = stick == self ? partOf(b, p->getStickPart()) : PartNone;
            cand.blue = p->mColor == Blue;
            cand.buried = p->isBuried() || p->isStickToMouth();
            add(p, cand);
        }
    }
}
Creature* creatureFor(const Snapshot& snap, std::uint64_t id) {
    return id >= 1 && id <= snap.who.size() ? snap.who[std::size_t(id - 1)] : nullptr;
}

// Diagnostic census of the field Pikmin around the Titan (mode/state/stick),
// logged at Dead entry and when the corpse forms.
void pikiCensus(const Binding& b, BTeki* t, const char* when) {
    if (!pikiMgr) return;
    int alive = 0, stuck = 0, near = 0, formation = 0, free = 0, transport = 0, other = 0;
    std::map<int, int> states;
    const Vector3f me = t->getPosition();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        ++alive;
        if (p->getStickObject() == t) ++stuck;
        const Vector3f q = p->getPosition();
        const float dx = q.x - me.x, dz = q.z - me.z;
        if (dx * dx + dz * dz < 300.0f * 300.0f) ++near;
        if (p->mMode == PikiMode::FormationMode) ++formation;
        else if (p->mMode == PikiMode::FreeMode) ++free;
        else if (p->mMode == PikiMode::TransportMode) ++transport;
        else ++other;
        ++states[p->getState()];
    }
    std::printf("P2_BIGTREASURE_PIKI_CENSUS generator=%u source_id=73 when=%s alive=%d stuck=%d near=%d formation=%d "
                "free=%d transport=%d other=%d states=",
                b.generator, when, alive, stuck, near, formation, free, transport, other);
    for (const auto& kv : states) std::printf("%d:%d,", kv.first, kv.second);
    std::printf("\n");
}

void logState(const Binding& b, const Transition& tr, BTeki* t) {
    const Vector3f p = t->getPosition();
    std::printf("P2_BIGTREASURE_FSM generator=%u source_id=73 from=%s state=%s x=%.1f z=%.1f health=%.1f weapons=%d "
                "hp=%.0f/%.0f/%.0f/%.0f anim=%s\n",
                b.generator, stateName(tr.from), stateName(tr.to), p.x, p.z, t->mHealth, b.fsm.ownership().weaponCount(),
                b.fsm.ownership().weaponHealth(0), b.fsm.ownership().weaponHealth(1), b.fsm.ownership().weaponHealth(2),
                b.fsm.ownership().weaponHealth(3), animClipName(b.fsm.animator().anim()) ? animClipName(b.fsm.animator().anim()) : "-");
}

bool stimulateElement(BTeki* t, Creature* c, const ElementHit& eh) {
    // BigTreasureAttack.cpp receivers: Pikmin take the element stimulus;
    // captains fall back to a flick/zero-damage attack when they refuse it.
    bool accepted = false;
    const P2BigTreasureReceiverHit& hit = eh.hit;
    switch (hit.stimulus) {
    case P2BigTreasureReceiverStimulus::Fire: accepted = c->stimulate(InteractFire(t, hit.damage)); break;
    case P2BigTreasureReceiverStimulus::Gas: accepted = c->stimulate(InteractGas(t, hit.damage)); break;
    case P2BigTreasureReceiverStimulus::Water: accepted = c->stimulate(InteractBubble(t, 0.0f)); break;
    case P2BigTreasureReceiverStimulus::Elec: {
        Vector3f dir(hit.direction.x, hit.direction.y, hit.direction.z);
        accepted = c->stimulate(InteractDenki(t, hit.damage, &dir));
        break;
    }
    case P2BigTreasureReceiverStimulus::None: return false;
    }
    if (!accepted && eh.navi) {
        // Every element (gas included): flick with *_NAVI_FLICK_CHANCE, else a
        // 0-damage attack (BigTreasureAttack.cpp fire/gas/bubble/elec loops).
        if (eh.naviFlick) c->stimulate(InteractFlick(t, 0.0f, 0.0f, FLICK_BACKWARDS_ANGLE));
        else c->stimulate(InteractAttack(t, nullptr, 0.0f, false));
    }
    return accepted;
}

void applyOutput(BTeki* t, Binding& b, const Snapshot& snap, const TickOutput& o) {
    for (const Transition& tr : o.entered) {
        logState(b, tr, t);
        // P1 Beady Long Legs bank approximation (output-only, #946).
        if (tr.to == State::Dead) pc_p2_sfx(73, b.generator, p2sfx::Event::Dead, t);
        if (tr.to == State::Flick) pc_p2_sfx(73, b.generator, p2sfx::Event::Flick, t);
        if (tr.to == State::Land) pc_p2_sfx(73, b.generator, p2sfx::Event::Step, t);
        if (tr.to == State::Dead && !b.deadLogged) {
            b.deadLogged = true;
            // StateDead::init -> deathProcedure -> setAlive(false): stuck
            // Pikmin let go (aiAttack drops a non-alive stick target) and no
            // further hit lands. The host death funnel runs at KEYEVENT_END.
            pikiCensus(b, t, "dead_enter");
            t->clearTekiOption(TEKIOPT_Alive);
            std::printf("P2_BIGTREASURE_DEAD generator=%u source_id=73 health=%.1f weapons=%d\n", b.generator,
                        t->mHealth, b.fsm.ownership().weaponCount());
        }
        if (tr.to == State::Attack) b.emitLogged = false;
    }
    for (int w = 0; w < P2BTWEAPON_Count; ++w) {
        if (!o.weaponHits[w]) continue;
        pc_p2_test_day_cycle_note("hurt");
        pc_p2_sfx(73, b.generator, p2sfx::Event::Damage, t);
        std::printf("P2_BIGTREASURE_DAMAGE generator=%u source_id=73 part=%s hits=%d damage=%.1f hp=%.1f state=%s%s\n",
                    b.generator, weaponName(w), o.weaponHits[w], o.weaponDamage[w], b.fsm.ownership().weaponHealth(w),
                    stateName(b.fsm.state()), o.pinchSmoke[w] ? " pinch=1" : "");
    }
    if (o.ignoredHits) b.ignored += o.ignoredHits;
    if (!o.flick.empty() || (o.flickReason && o.flick.empty())) {
        int done = 0;
        for (auto id : o.flick)
            if (Creature* c = creatureFor(snap, id))
                if (c->isAlive() && c->getStickObject() == t
                    && c->stimulate(InteractFlick(t, o.flickKnockback, o.flickDamage, o.flickAngle))) ++done;
        if (o.flickReason)
            std::printf("P2_BIGTREASURE_FLICK generator=%u source_id=73 reason=%s flicked=%d/%zu knockback=%.1f\n",
                        b.generator, o.flickReason, done, o.flick.size(), o.flickKnockback);
    }
    if (o.pickedWeapon >= 0)
        std::printf("P2_BIGTREASURE_PICK generator=%u source_id=73 weapon=%s hp=%.0f/%.0f/%.0f/%.0f\n", b.generator,
                    weaponName(o.pickedWeapon), b.fsm.ownership().weaponHealth(0), b.fsm.ownership().weaponHealth(1),
                    b.fsm.ownership().weaponHealth(2), b.fsm.ownership().weaponHealth(3));
    if (o.attackStarted >= 0) {
        ++b.attacks;
        {
            p2sfx::Event ev = p2sfx::Event::Elec;
            if (o.attackStarted == P2BTWEAPON_Fire) ev = p2sfx::Event::Fire;
            else if (o.attackStarted == P2BTWEAPON_Water) ev = p2sfx::Event::Water;
            else if (o.attackStarted == P2BTWEAPON_Gas) ev = p2sfx::Event::Gas;
            pc_p2_sfx(73, b.generator, ev, t);
        }
        b.recvCount.clear();
        std::printf("P2_BIGTREASURE_ATTACK_START generator=%u source_id=73 weapon=%s variant=%d hp=%.1f n=%d\n",
                    b.generator, weaponName(o.attackStarted), o.fireVariant,
                    b.fsm.ownership().weaponHealth(o.attackStarted), b.attacks);
    }
    if (o.attackNodes > 0 && !b.emitLogged) {
        b.emitLogged = true;
        std::printf("P2_BIGTREASURE_ATTACK_EMIT generator=%u source_id=73 weapon=%s nodes=%d\n", b.generator,
                    weaponName(b.fsm.elements().activeWeapon()), o.attackNodes);
    }
    if (o.attackFinished) {
        std::printf("P2_BIGTREASURE_ATTACK_FINISH generator=%u source_id=73 stimulated=%d accepted=%d navi_fallback=%d\n",
                    b.generator, b.recvStim, b.recvAccepted, b.recvNaviFallback);
        b.recvStim = b.recvAccepted = b.recvNaviFallback = 0;
    }
    for (const ElementHit& eh : o.elementHits) {
        Creature* c = creatureFor(snap, eh.id);
        if (!c || !c->isAlive()) continue;
        const bool accepted = stimulateElement(t, c, eh);
        ++b.recvStim;
        if (accepted) ++b.recvAccepted;
        if (!accepted && eh.navi) ++b.recvNaviFallback;
        // Source re-stimulates every update; log the first contact and the
        // first acceptance per target per attack.
        int& seen = b.recvCount[c];
        const int bit = accepted ? 2 : 1;
        if (seen & bit) continue;
        seen |= bit;
        std::printf("P2_BIGTREASURE_RECV generator=%u source_id=73 weapon=%s target=%s color=%d accepted=%d%s\n",
                    b.generator, p2_bigtreasure_receiver_stimulus_name(eh.hit.stimulus), eh.navi ? "navi" : "piki",
                    eh.navi ? -1 : int(static_cast<Piki*>(c)->mColor), accepted ? 1 : 0,
                    !accepted && eh.navi ? (eh.naviFlick ? " fallback=flick" : " fallback=attack0") : "");
    }
    for (const Drop& d : o.drops) {
        if (d.weapon >= 0) {
            int parts = 0;
            for (auto id : o.partFlick)
                if (Creature* c = creatureFor(snap, id))
                    if (c->isAlive() && c->getStickObject() == t
                        && c->stimulate(InteractFlick(t, 10.0f, 0.0f, o.partFlickAngle))) ++parts;
            DroppedWeapon dw;
            dw.weapon = d.weapon;
            dw.pos = Vector3f(d.position.x, d.position.y, d.position.z);
            dw.vel = Vector3f(d.velocity.x, d.velocity.y, d.velocity.z);
            b.dropped.push_back(dw);
            std::printf("P2_BIGTREASURE_WEAPON_DROP generator=%u source_id=73 weapon=%s x=%.1f y=%.1f z=%.1f vy=%.1f "
                        "part_flick=%d/%zu remaining=%d state=%s\n",
                        b.generator, weaponName(d.weapon), d.position.x, d.position.y, d.position.z, d.velocity.y, parts,
                        o.partFlick.size(), b.fsm.ownership().weaponCount(), stateName(b.fsm.state()));
        } else {
            std::printf("P2_BIGTREASURE_RELEASE generator=%u source_id=73 item=louie x=%.1f y=%.1f z=%.1f vy=%.1f "
                        "throwup=%d carryable=0\n",
                        b.generator, d.position.x, d.position.y, d.position.z, d.velocity.y, o.throwupItem ? 1 : 0);
        }
    }
}

// setupBigTreasureCollision (BigTreasure.cpp:671-700): a dropped weapon's
// part turns '_t__' with radius 0 (radius applied in updateColl); tam1/tam2
// are '_t__' while any weapon is captured and 'st__' once none is.
void setupCollisionCodes(Binding& b) {
    if (!b.coll.own) return;
    const bool unarmed = b.fsm.ownership().weaponCount() == 0;
    for (std::size_t i = 0; i < b.coll.nodes.size(); ++i) {
        ObjCollInfo* n = b.coll.nodes[i];
        const std::string& id = sColl[i].id;
        const int w = weaponForPartId(id);
        if (w >= 0 && !b.fsm.ownership().isWeaponAttached(w)) n->mCode.setID('_t__');
        if (id == "tam1" || id == "tam2") n->mCode.setID(unarmed ? 'st__' : '_t__');
    }
    if (unarmed && !b.coll.unarmedCodes) {
        b.coll.unarmedCodes = true;
        std::printf("P2_BIGTREASURE_COLL_UNARMED generator=%u source_id=73 tam=st__\n", b.generator);
    }
}

void updateColl(BTeki* t, Binding& b) {
    if (!b.coll.own) return;
    // CollPart::getMatrix() = invCamMat * mJointMatrix (+ centre). Give every
    // part mJointMatrix = R(invCamMat)^T * yaw so gameplay reads (stuck
    // Pikmin) get the Titan yaw whether or not it was drawn this frame; the
    // draw pass writes the same product for its own camera.
    {
        Matrix4f yaw, camRot, camYaw;
        yaw.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, t->getDirection(), 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
        camRot.makeIdentity();
        for (int r = 0; r < 3; ++r)
            for (int c = 0; c < 3; ++c) camRot.mMtx[r][c] = invCamMat.mMtx[c][r];
        camRot.multiplyTo(yaw, camYaw);
        for (CollPart* part : b.coll.parts)
            if (part) part->mJointMatrix = camYaw;
    }
    for (std::size_t i = 0; i < b.coll.parts.size(); ++i) {
        CollPart* part = b.coll.parts[i];
        if (!part) continue;
        const CollNode& n = sColl[i];
        const Vec3 c = b.fsm.collCentre(n);
        part->mCentre.set(c.x, c.y, c.z);
        const int w = weaponForPartId(n.id);
        part->mRadius = w >= 0 && !b.fsm.ownership().isWeaponAttached(w) ? 0.0f : n.radius;
    }
}

bool buildColl(BTeki* t, Binding& b) {
    if (sColl.empty() || !t->mCollInfo) return false;
    OwnColl& oc = b.coll;
    oc.nodes.clear();
    oc.parts.clear();
    for (const CollNode& n : sColl) {
        auto* node = new ObjCollInfo();
        node->mId.setID(fourcc(n.id));
        node->mCode.setID(fourcc(n.code));
        node->mRadius = n.radius;
        node->mCentrePosition.set(n.offset.x, n.offset.y, n.offset.z);
        node->mJointIndex = n.joint;
        oc.nodes.push_back(node);
    }
    for (std::size_t i = 0; i < sColl.size(); ++i)
        if (sColl[i].parent >= 0) oc.nodes[std::size_t(sColl[i].parent)]->add(oc.nodes[i]);
    const int capacity = int(sColl.size()) + 1 > 32 ? int(sColl.size()) + 1 : 32; // >= any host tree (22)
    oc.own = new CollInfo(capacity);
    oc.own->initInfoTree(oc.nodes[0]);
    int tubes = 0;
    for (std::size_t i = 0; i < sColl.size(); ++i) {
        CollPart* part = oc.own->getSphere(fourcc(sColl[i].id));
        if (part) {
            part->mIsUpdateActive = false; // no parent shape: updateColl owns centre/radius
            part->mJointMatrix = Matrix4f::ident;
        }
        oc.parts.push_back(part);
    }
    // setupCollision: makeTubeTree on the four leg roots (child chains).
    for (const char* leg : {"lft1", "lht1", "rft1", "rht1"}) {
        int depth = 0;
        for (CollPart* p = oc.own->getSphere(fourcc(leg)); p && p->getChild(); p = p->getChild()) ++depth;
        if (depth > 0) {
            oc.own->makeTubesChild(fourcc(leg), depth);
            ++tubes;
        }
    }
    oc.host = t->mCollInfo;
    t->mCollInfo = oc.own;
    // onInit disableEvent(EB_PlatformCollEnabled): the Titan has no platform
    // collision. The Swallow host's back platforms would otherwise report
    // contacts whose part our tree cannot resolve (null CollEvent part).
    t->mPlatMgr.release();
    sHostColl[t] = oc.host;
    setupCollisionCodes(b);
    updateColl(t, b);
    std::printf("P2_BIGTREASURE_COLL_BIND generator=%u source_id=73 parts=%zu tubes=%d host_parts_replaced=1\n",
                b.generator, oc.parts.size(), tubes);
    return true;
}

void restoreHostColl(BTeki* t) {
    // The own CollInfo is intentionally never freed: stuck Pikmin may still
    // hold CollPart pointers into it, and a pooled actor re-inits whatever
    // mCollInfo it holds.
    auto i = sHostColl.find(t);
    if (i == sHostColl.end()) return;
    if (i->second) t->mCollInfo = i->second;
    sHostColl.erase(i);
}

void stepDropped(Binding& b, float dt) {
    for (DroppedWeapon& d : b.dropped) {
        if (d.resting) continue;
        d.vel.y -= 490.0f * dt; // visual pop only (not a P1 pellet)
        d.pos.x += d.vel.x * dt;
        d.pos.y += d.vel.y * dt;
        d.pos.z += d.vel.z * dt;
        const float ground = mapMgr ? mapMgr->getMinY(d.pos.x, d.pos.z, true) : 0.0f;
        if (d.pos.y <= ground) {
            d.pos.y = ground;
            d.resting = true;
        }
    }
}

const char* fxEndName(p2attackfx::EndReason r) { return p2attackfx::endReasonName(r); }

void stopFx(Binding& b, p2attackfx::EndReason why) {
    const p2attackfx::Element element = b.fxSession.element;
    const unsigned ticks = b.fxSession.ticks, points = b.fxSession.points;
    if (!b.fxSession.end()) return;
    const unsigned created = b.fx ? b.fx->stopAll() : 0u;
    b.fxState.reset();
    std::printf("P2_BIGTREASURE_FX_STOP generator=%u source_id=73 element=%s reason=%s ticks=%u points=%u generators=%u "
                "outstanding=%u\n",
                b.generator, p2attackfx::elementName(element), fxEndName(why), ticks, points, created,
                b.fxSession.outstanding());
    std::fflush(stdout);
}

// TEST-ONLY effect gallery (PIKMIN_P2_TEST_FX_GALLERY=<id,id,...>): spawns each P1 effect id by
// the captain at scale 1 and 3 with its authored emission, dumps one frame, then kills it, so the
// Monster Pump look can be chosen from what each candidate really draws. Unset in every normal run.
void galleryTick() {
    static const char* env = std::getenv("PIKMIN_P2_TEST_FX_GALLERY");
    if (!env || !*env || !effectMgr) return;
    static std::vector<int> ids;
    static std::size_t at = 0;
    static unsigned frame = 0;
    static p2attackfx::Emitter fx;
    if (ids.empty() && frame == 0) {
        std::string text(env), word;
        for (std::size_t i = 0; i <= text.size(); ++i) {
            if (i == text.size() || text[i] == ',') { if (!word.empty()) ids.push_back(std::atoi(word.c_str())); word.clear(); }
            else word += text[i];
        }
    }
    ++frame;
    Navi* navi0 = nullptr;
    for (Navi* n : pc_p2_navis()) { navi0 = n; break; }
    if (frame < 240 || at >= ids.size() || !navi0) return;
    const unsigned phase = (frame - 240) % 60;
    const Vector3f np = navi0->getPosition();
    if (phase == 0) {
        p2attackfx::Point pts[2] = {{p2attackfx::Kind::Body, np.x - 12.0f, np.y + 6.0f, np.z + 30.0f, 1.0f, 0.0f, 1.0f},
                                    {p2attackfx::Kind::Body, np.x + 22.0f, np.y + 6.0f, np.z + 30.0f, 1.0f, 0.0f, 1.0f}};
        fx.emitLook(p2attackfx::Look{ids[at], 0, false, 0, 1.0f}, pts, 1);
        fx.emitLook(p2attackfx::Look{ids[at], 0, false, 0, 3.0f}, pts + 1, 1);
    } else if (phase == 14) {
        char key[40];
        std::snprintf(key, sizeof(key), "Gal_%03d", ids[at]);
        pc_gfx_proxy_shot_now(key);
        std::printf("P2_FX_GALLERY id=%d\n", ids[at]);
    } else if (phase == 45) {
        fx.stopAll();
        ++at;
    }
}

// Emit this frame's weapon effects, or stop them. Reads the element runtime
// only; never writes simulation state (visual only).
void updateFx(BTeki* t, Binding& b) {
    galleryTick();
    const P2BigTreasureElementRuntime& rt = b.fsm.elements();
    if (!rt.active() || t->mHealth <= 0.0f) {
        if (b.fxSession.active) {
            const State st = b.fsm.state();
            stopFx(b, (t->mHealth <= 0.0f || st == State::Dead) ? p2attackfx::EndReason::Death
                                                                 : st == State::PutItem ? p2attackfx::EndReason::AttackEnd
                                                                                        : p2attackfx::EndReason::StateChange);
        }
        b.fxEmits = 0;
        return;
    }
    p2titanfx::Legs legs;
    if (b.fsm.gait().active()) {
        legs.set = true;
        const Vec3 hip = b.fsm.jointPoint(JointKosi, {0.0f, -20.0f, 0.0f});
        for (int l = 0; l < 4; ++l) {
            const Vec3& f = b.fsm.gait().foot(l);
            legs.hip[l][0] = hip.x; legs.hip[l][1] = hip.y; legs.hip[l][2] = hip.z;
            legs.foot[l][0] = f.x; legs.foot[l][1] = t->mSRT.t.y + 12.0f; legs.foot[l][2] = f.z;
        }
    }
    P2BigTreasureElementStats stats;
    stats.emits = b.fxEmits;
    b.fxEmits = 0;
    p2attackfx::Element element = p2attackfx::Element::Fire;
    // A different weapon starting without the previous one ending is a state change.
    if (b.fxSession.active) {
        p2attackfx::Element now = b.fxSession.element;
        if (p2titanfx::elementFor(rt.activeWeapon(), now) && now != b.fxSession.element) stopFx(b, p2attackfx::EndReason::StateChange);
    }
    p2attackfx::Point pts[p2titanfx::MAX_POINTS];
    const int n = p2titanfx::layout(rt, stats, legs, b.fxState, element, pts);
    if (b.fxSession.begin(element)) {
        std::printf("P2_BIGTREASURE_FX_START generator=%u source_id=73 element=%s visual_only=1\n", b.generator,
                    p2attackfx::elementName(element));
    }
    if (b.fxSession.active && b.fxSession.ticks == 0 && element == p2attackfx::Element::WaterBall) {
        // Monster Pump look: the chosen default, or a TEST-ONLY override to compare candidates
        // (PIKMIN_P2_TEST_WATER_LOOK=<index> | cycle: one look per water attack).
        static int sWaterAttacks = 0;
        const char* pick = std::getenv("PIKMIN_P2_TEST_WATER_LOOK");
        if (pick && *pick) {
            p2attackfx::waterVariant() = std::string(pick) == "cycle" ? sWaterAttacks % p2attackfx::WATER_LOOKS : std::atoi(pick);
        }
        ++sWaterAttacks;
        b.waterShots = 0;
        b.waterDump.clear();
        std::printf("P2_BIGTREASURE_WATER_LOOK generator=%u variant=%d name=%s\n", b.generator, p2attackfx::waterVariant(),
                    p2attackfx::waterLook(p2attackfx::waterVariant()).name);
    }
    if (element == p2attackfx::Element::WaterBall && stats.emits > 0) {
        // Frame each shot (probe-only dumps): in flight, then around the burst.
        ++b.waterShots;
        if (b.waterShots <= 4) {
            b.waterDump.push_back({b.fxSession.ticks + 9, b.waterShots * 10 + 1});
            b.waterDump.push_back({b.fxSession.ticks + 26, b.waterShots * 10 + 2});
        }
    }
    for (std::size_t wd = 0; wd < b.waterDump.size();) {
        if (b.waterDump[wd].first == b.fxSession.ticks) {
            char key[64];
            std::snprintf(key, sizeof(key), "TitanWater_v%d_s%d_%c", p2attackfx::waterVariant(), b.waterDump[wd].second / 10,
                          b.waterDump[wd].second % 10 == 1 ? 'a' : 'b');
            pc_gfx_proxy_shot_now(key);
            b.waterDump.erase(b.waterDump.begin() + long(wd));
        } else {
            ++wd;
        }
    }
    const unsigned tick = b.fxSession.ticks;
    if (!b.fx) b.fx = std::make_unique<p2attackfx::Emitter>();
    const unsigned live = effectMgr ? effectMgr->getLiveGeneratorCount() : 0u;
    const unsigned made = b.fx->emit(element, pts, n, tick);
    if (tick == 30 || tick == 90)
        std::printf("P2_BIGTREASURE_FX_POOL generator=%u element=%s tick=%u live_before=%u points=%d made=%u cap=%d\n",
                    b.generator, p2attackfx::elementName(element), tick, live, n, made, p2attackfx::MAX_LIVE_GENERATORS);
    b.fxSession.note(unsigned(n), made);
    if (n > 0 && b.fxSession.generators == made && made > 0) {
        std::printf("P2_BIGTREASURE_FX generator=%u source_id=73 element=%s points=%d generators=%u first=%.1f,%.1f,%.1f "
                    "dir=%.3f,%.3f visual_only=1\n",
                    b.generator, p2attackfx::elementName(element), n, made, pts[0].x, pts[0].y, pts[0].z, pts[0].dx,
                    pts[0].dz);
    }
    // Probe-only frame dumps (PIKMIN_P2_PROXY_SHOT directory): a fixed set of session ticks.
    static const unsigned kShots[] = {4, 10, 18, 28, 44, 64, 90, 120};
    for (unsigned k : kShots)
        if (b.fxSession.ticks == k) {
            char key[56];
            std::snprintf(key, sizeof(key), "TitanFx_%s_%03u", p2attackfx::elementName(element), k);
            pc_gfx_proxy_shot_now(key);
        }
    std::fflush(stdout);
}

// Live tick. Returns true once the host teardown ran.
bool ownTick(BTeki* t, Binding& b, float dt) {
    // hardConstraintOn: the source Titan is never pushed. Weight 0 stops P1
    // collision impulses (getiMass() == 0) and no knockback velocity is kept.
    // While the IK runs the host position is never written: it follows the IK centre
    // through the velocity below, exactly as BigTreasure::doUpdate sets
    // mPosition = IKSystemMgr::mCentrePosition. (An earlier standing-anchor
    // pin sampled "moving" from the last source sub-tick; #246 review.)
    t->mVolatileVelocity.x = t->mVolatileVelocity.z = 0.0f;
    // Before Land's startProgramedIK the IK is off and the source Titan does
    // not move at all (Stay/Land at its birth point); the P1 host would
    // otherwise settle a few units on the arena slope. Keyed on the FSM
    // state, not on sampled velocity. Once the IK runs, the host tracks the
    // IK centre through the velocity below and is never written.
    if (!b.fsm.gait().active()) {
        t->mSRT.t.x = b.hold.x;
        t->mSRT.t.z = b.hold.z;
    }
    b.debt += dt;
    int ticks = int(b.debt / kSourceDelta);
    if (ticks > 4) ticks = 4;
    b.debt -= float(ticks) * kSourceDelta;
    if (b.debt > 1.0f) b.debt = 0.0f;
    // Every InteractAttack stored damage on the suppressed host; the core
    // owns where it goes (weapons or, unarmed, the body). Non-Piki sources are
    // ignored (source damageCallBack requires creature->isPiki()).
    t->mStoredDamage = 0.0f;
    if (ticks <= 0) return false;
    Snapshot snap;
    buildSnapshot(t, b, snap);
    bool kill = false;
    for (int k = 0; k < ticks && !kill; ++k) {
        TickInput in;
        const Vector3f pos = t->getPosition();
        in.position = {pos.x, pos.y, pos.z};
        in.health = t->mHealth;
        in.groundY = mapMgr ? mapMgr->getMinY(pos.x, pos.z, true) : pos.y;
        in.candidates = snap.c.data();
        in.count = snap.c.size();
        in.hits = k == 0 ? b.pending.data() : nullptr;
        in.hitCount = k == 0 ? b.pending.size() : 0;
        if (sTrace) {
            in.element.context = sTrace;
            in.element.trace = P2BigTreasureMapTrace::trace;
            in.element.ground = P2BigTreasureMapTrace::ground;
        }
        const float before = t->mHealth;
        const TickOutput o = b.fsm.tick(in);
        if (k == 0) b.pending.clear();
        if (!o.valid) break;
        if (o.bodyDamage > 0.0f) {
            t->mStoredDamage = o.bodyDamage;
            t->makeDamaged();
            if (t->mHealth > 0.0f) pc_p2_sfx(73, b.generator, p2sfx::Event::Damage, t);
            std::printf("P2_BIGTREASURE_BODY_DAMAGE generator=%u source_id=73 health=%.1f prior=%.1f hits=%d weapons=%d\n",
                        b.generator, t->mHealth, before, o.bodyHits, b.fsm.ownership().weaponCount());
        }
        applyOutput(t, b, snap, o);
        b.fxEmits += o.attackEmits;
        // Movement/facing are the gait's; the P1 host integrates them.
        t->setDirection(o.faceDir);
        const Vector3f drive(o.velocity.x, 0.0f, o.velocity.z);
        t->inputDrive(drive);
        t->mVelocity.x = drive.x;
        t->mVelocity.z = drive.z;
        kill = o.killRequest;
        if (!o.drops.empty()) setupCollisionCodes(b);
    }
    updateColl(t, b);
    updateFx(t, b);
    stepDropped(b, dt);
    // One footstep per gait step (BigTreasure.cpp PSSE_EN_BIGTAKARA_WALK per foot).
    if (b.fsm.gait().steps() != b.sfxSteps) {
        b.sfxSteps = b.fsm.gait().steps();
        pc_p2_sfx(73, b.generator, p2sfx::Event::Step, t);
    }
    if (t->mHealth > 0.0f) t->updateLifeGauge();
    b.logTimer += dt;
    if (b.logTimer >= 1.0f) {
        b.logTimer = 0.0f;
        const Vector3f p = t->getPosition();
        const Fsm& f = b.fsm;
        int stuck = 0, onWeapon = 0, onBody = 0;
        for (const Candidate& c : snap.c) {
            if (!(c.stuckToSelf && c.alive)) continue;
            ++stuck;
            if (c.stuckPart >= 0) ++onWeapon;
            else if (c.stuckPart == PartOther) ++onBody;
        }
        std::printf("P2_BIGTREASURE_POS generator=%u source_id=73 state=%s anim=%s frame=%.0f x=%.1f z=%.1f face=%.2f "
                    "target=%.1f,%.1f home=%.1f,%.1f health=%.1f weapons=%d hp=%.0f/%.0f/%.0f/%.0f stuck=%d steps=%d "
                    "stuck_weapon=%d stuck_body=%d ik=%d flick=%.0f limit=%.2f ignored=%d centre=%.1f,%.1f trace=%.1f,%.1f\n",
                    b.generator, stateName(f.state()), animClipName(f.animator().anim()) ? animClipName(f.animator().anim()) : "-",
                    f.animator().frame(), p.x, p.z, t->getDirection(), f.targetPosition().x, f.targetPosition().z,
                    f.home().x, f.home().z, t->mHealth, f.ownership().weaponCount(), f.ownership().weaponHealth(0),
                    f.ownership().weaponHealth(1), f.ownership().weaponHealth(2), f.ownership().weaponHealth(3), stuck,
                    f.gait().steps(), onWeapon, onBody, f.gait().active() ? 1 : 0, f.flickTimer(), f.attackLimitTimer(), b.ignored,
                    f.gait().centre().x, f.gait().centre().z, f.gait().traceCentre().x, f.gait().traceCentre().z);
    }
    std::fflush(stdout);
    if (kill && !b.escaped) {
        // Dead KEYEVENT_END -> kill(). The host death funnel (die + dieSoon)
        // runs in the suppressed doAI, hence pcEscapeNow (Groink pattern).
        b.escaped = true;
        t->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
        t->mVelocity.x = t->mVelocity.z = 0.0f;
        std::printf("P2_BIGTREASURE_ESCAPE generator=%u source_id=73 native=host_escape_now health=%.1f\n", b.generator,
                    t->mHealth);
        std::fflush(stdout);
        t->pcEscapeNow();
        return true;
    }
    return false;
}
} // namespace

void pc_p2_bigtreasure_teki_reset() {
    const int before = int(s.size());
    // Stage boundary (pc_p2_reset_all_teki runs while every stage creature is
    // still valid): hand each bound actor its host CollInfo back and drop the
    // map. Keeping entries across the stage heap reset let the next day's
    // TekiMgr::newTeki -> forget write yesterday's freed CollInfo into a new
    // Teki that reused the address (#246 re-entry review).
    int restored = 0;
    for (auto& e : sHostColl) {
        if (e.first && e.second) {
            e.first->mCollInfo = e.second;
            ++restored;
        }
    }
    sHostColl.clear();
    for (auto& e : s) stopFx(e.second, p2attackfx::EndReason::Reset);
    s.clear();
    sDrawLogged.clear();
    sConsidered.clear();
    sSetupDone = false;
    sPoseVis.clear();
    sPoseBank.reset();
    for (auto& v : sPoses) v.clear();
    for (Shape*& p : sPellet) p = nullptr;
    sPosesLoaded = false;
    sReady = false;
    if (before > 0 || restored > 0) {
        std::printf("P2_BIGTREASURE_TEKI_RESET bound_before=%d host_coll_restored=%d\n", before, restored);
        std::fflush(stdout);
    }
}

void pc_p2_bigtreasure_teki_forget(BTeki* t) {
    if (!t) return;
    restoreHostColl(t);
    sConsidered.erase(t);
    {
        auto fxIt = s.find(t);
        if (fxIt != s.end()) stopFx(fxIt->second, p2attackfx::EndReason::Forget);
    }
    {
        auto it = s.find(t);
        if (it != s.end() && it->second.began) pc_p2_test_day_cycle_note("delivered");
    }
    if (s.erase(t) > 0) {
        std::printf("P2_BIGTREASURE_TEKI_FORGET remaining=%d\n", int(s.size()));
        std::fflush(stdout);
    }
    sDrawLogged.erase(t);
    sPoseVis.forget(t);
}

bool pc_p2_bigtreasure_teki_is_bound(const BTeki* t) { return t && find(t) != nullptr; }

void pc_p2_bigtreasure_attack(BTeki* teki, Creature* attacker, float damage, CollPart* part) {
    Binding* b = find(teki);
    if (!b || b->began || !attacker) return;
    Hit h;
    h.part = partOf(*b, part);
    h.damage = damage;
    h.fromPiki = attacker->isPiki();
    if (b->pending.size() < 512) b->pending.push_back(h);
}

float pc_p2_bigtreasure_teki_param_f(const BTeki* teki, int idx, float fallback) {
    const Binding* b = find(teki);
    if (!b || b->began) return fallback;
    switch (idx) {
    case TPF_Life:
        return b->fsm.params().health;
    case TPF_Weight:
        return 0.0f; // hardConstraintOn: getiMass() == 0, never pushed
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
    case TPF_LifeRecoverRate:
        return 0.0f;
    default:
        return fallback;
    }
}

float pc_p2_bigtreasure_teki_effective_health(const BTeki* teki, float fallback) {
    const Binding* b = find(teki);
    if (!b || b->began || b->deadLogged) return fallback;
    float hp = fallback;
    for (int w = 0; w < P2BTWEAPON_Count; ++w) hp += b->fsm.ownership().weaponHealth(w);
    return hp;
}

bool pc_p2_bigtreasure_teki_aim_point(const BTeki* teki, float x, float z, float* outX, float* outZ) {
    const Binding* b = find(teki);
    if (!b || b->began || b->deadLogged || !outX || !outZ) return false;
    float best = -1.0f;
    for (int w = 0; w < P2BTWEAPON_Count; ++w) {
        if (!b->fsm.ownership().isWeaponAttached(w)) continue;
        const Vec3 p = b->fsm.jointWorld(w);
        const float d = (p.x - x) * (p.x - x) + (p.z - z) * (p.z - z);
        if (best < 0.0f || d < best) {
            best = d;
            *outX = p.x;
            *outZ = p.z;
        }
    }
    return best >= 0.0f;
}

bool pc_p2_bigtreasure_teki_suppress_ai(const BTeki* teki) {
    const Binding* b = find(teki);
    return b && !b->began;
}

namespace {
bool bindActor(BTeki* t, const char* when) {
    const unsigned gen = pc_p2_campaign_token(t);
    Binding& b = s[t];
    b = Binding{};
    b.generator = gen;
    const Vector3f pos = t->getPosition();
    b.hold = pos;
    b.fsm.init(sParams, sBank, sAnimator, {pos.x, pos.y, pos.z}, t->getDirection(), (gen * 2654435761u) | 1u);
    {   // TEST-ONLY weapon order for evidence runs; unset in every normal run.
        const char* order = std::getenv("PIKMIN_P2_TEST_BIGTREASURE_WEAPONS");
        if (order && *order) {
            int seq[8], n = 0;
            std::string text(order), word;
            for (std::size_t i = 0; i <= text.size() && n < 8; ++i) {
                if (i == text.size() || text[i] == ',') {
                    if (word == "elec") seq[n++] = P2BTWEAPON_Elec;
                    else if (word == "fire") seq[n++] = P2BTWEAPON_Fire;
                    else if (word == "gas") seq[n++] = P2BTWEAPON_Gas;
                    else if (word == "water") seq[n++] = P2BTWEAPON_Water;
                    word.clear();
                } else word += text[i];
            }
            b.fsm.setForcedWeaponOrder(seq, n);
            std::printf("P2_BIGTREASURE_TEST_WEAPON_ORDER generator=%u order=%s TEST-ONLY\n", gen, order);
        }
    }
    t->mHealth = sParams.health;
    b.lastHealth = t->mHealth;
    if (!buildColl(t, b)) {
        std::printf("P2_BIGTREASURE_COLL_BIND_FAILED generator=%u source_id=73\n", gen);
        s.erase(t);
        return false;
    }
    const int corpse = t->getParameterI(TPI_CorpseType);
    std::printf("P2_BIGTREASURE_BIND generator=%u source_id=73 host_type=%d health=%.1f weapons=%d louie=1 "
                "state=%s draw=%s corpse_type=%d x=%.1f z=%.1f when=%s\n",
                gen, int(t->mTekiType), t->mHealth, b.fsm.ownership().weaponCount(), stateName(b.fsm.state()),
                sPosesLoaded ? "p2_model" : "host", corpse, pos.x, pos.z, when);
    // Ordinary-delivery bridge (lane 06): the corpse substitute the owner
    // must approve -- the host's LeaveCorpse pellet grants onion:p2:73.
    pc_randomizer_p2_bind_source(static_cast<PelletView*>(t), 73u, gen);
    std::printf("P2_BIGTREASURE_DELIVERY_BIND generator=%u source_id=73 reward=host_corpse_substitute\n", gen);
    std::fflush(stdout);
    return true;
}

bool prepare(bool bridge) {
    if (sReady) return true;
    if (!loadInputs(bridge)) return false;
    if (!sTrace) sTrace = new P2BigTreasureMapTrace;
    sTrace->reset(mapMgr);
    sReady = true;
    return true;
}
} // namespace

void pc_p2_bigtreasure_teki_setup() {
    pc_p2_bigtreasure_teki_reset();
    const bool bridge = pc_randomizer_p2_bridge();
    if (!bridge || !tekiMgr) return;
    sSetupDone = true;
    bool any = false;
    {
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            auto* t = static_cast<Teki*>(*it);
            if (t && t->mGenerator && pc_p2_campaign_source(t) == 73) any = true;
        }
    }
    if (!any) return;
    if (!prepare(bridge)) return;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator || pc_p2_campaign_source(t) != 73) continue;
        sConsidered.insert(t);
        bindActor(t, "setup");
    }
}

void pc_p2_bigtreasure_teki_tick(BTeki* t) {
    auto i = s.find(t);
    if (i == s.end()) {
        // Late spawn (respawn / later generator): bind on its first live tick
        // after setup. Each actor lifetime is considered once.
        if (!sSetupDone || !t || t->mTekiType != TEKI_Swallow || t->mDeadState != 0 || !t->isHostAlive()) return;
        if (!sConsidered.insert(t).second) return;
        if (!t->mGenerator || pc_p2_campaign_source(t) != 73) return;
        if (!prepare(pc_randomizer_p2_bridge())) return;
        bindActor(t, "late_spawn");
        return;
    }
    Binding& b = i->second;
    const float dt = gsys ? gsys->getFrameTime() : 0.0f;
    if (b.began) {
        // Corpse phase: periodic Pikmin census for the carry diagnosis.
        b.logTimer += dt;
        if (b.logTimer >= 5.0f) {
            b.logTimer = 0.0f;
            pikiCensus(b, t, "corpse_phase");
            std::fflush(stdout);
        }
        return;
    }
    if (t->mDeadState == 0) {
        if (!(dt > 0.0f && dt < 0.5f)) return;
        ownTick(t, b, dt); // may run the host teardown; never touch b after it
        return;
    }
    if (!b.escaped) {
        // Something outside the FSM called die(): finish the teardown here or
        // the corpse would never pelletize (dieSoon only runs in doAI).
        b.escaped = true;
        std::printf("P2_BIGTREASURE_ESCAPE generator=%u source_id=73 native=host_die_external\n", b.generator);
        std::fflush(stdout);
        t->pcEscapeNow();
        return;
    }
    if (!b.began && (t->mPellet || t->mHealth <= 0.0f)) {
        b.began = true;
        std::printf("P2_BIGTREASURE_CORPSE generator=%u source_id=73 pellet=%d x=%.1f z=%.1f\n", b.generator,
                    t->mPellet ? 1 : 0, t->mSRT.t.x, t->mSRT.t.z);
        pikiCensus(b, t, "corpse");
        std::fflush(stdout);
    }
}

bool pc_p2_bigtreasure_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& view, bool corpse) {
    auto i = s.find(t);
    if (i == s.end() || !sPosesLoaded || !gfx.mCamera) return false;
    Binding& b = i->second;
    if (b.coll.own && gfx.mCamera) {
        // CollPart::getMatrix() = invCamMat * mJointMatrix with the centre as
        // translation: give our parts the Titan yaw in the same camera frame.
        invCamMat = gfx.mCamera->mInverseLookAtMtx;
        Matrix4f yaw, camYaw;
        yaw.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, t->getDirection(), 0.0f), Vector3f(0.0f, 0.0f, 0.0f));
        gfx.mCamera->mLookAtMtx.multiplyTo(yaw, camYaw);
        for (CollPart* part : b.coll.parts)
            if (part) part->mJointMatrix = camYaw;
    }
    const bool dead = corpse || b.began || t->mDeadState != 0;
    // The source draws the living body at the IK trace centre, a damped
    // spring behind the foot-average centre that the host (mPosition)
    // follows (BigTreasure::doAnimationIKSystem). view = L * T(host) R S, so
    // moving the model by d is view + L_rot * d in the translation column.
    Matrix4f bodyView = view;
    if (!dead && b.fsm.gait().active()) {
        const Vec3& tr = b.fsm.gait().traceCentre();
        const float d[3] = {tr.x - t->mSRT.t.x, 0.0f, tr.z - t->mSRT.t.z};
        const Matrix4f& L = gfx.mCamera->mLookAtMtx;
        for (int r = 0; r < 3; ++r) bodyView.mMtx[r][3] += L.mMtx[r][0] * d[0] + L.mMtx[r][2] * d[2];
    }
    int anim = b.fsm.animator().anim();
    float frame = b.fsm.animator().frame();
    bool last = false;
    if (dead) {
        anim = AnimDead;
        last = true;
    }
    if (anim < 0 || anim >= AnimCount || sPoses[anim].empty()) {
        anim = AnimWait1;
        frame = 0.0f;
        if (sPoses[anim].empty()) return false;
    }
    const auto& poses = sBank.clip[anim].poses;
    std::size_t best = last ? sPoses[anim].size() - 1 : 0;
    if (!last)
        for (std::size_t k = 1; k < poses.size() && k < sPoses[anim].size(); ++k)
            if (std::fabs(float(poses[k].frame) - frame) < std::fabs(float(poses[best].frame) - frame)) best = k;
    Shape* shape = sPoses[anim][best];
    {   // #972: lerp + crossfade into a private Shape; the nearest pose stays the fallback.
        const auto& clipBank = sBank.clip[anim];
        const float duration = float(clipBank.frames > 1 ? clipBank.frames : 2);
        const float drawFrame = last ? duration - 1.0f
                                     : (std::isfinite(frame) ? std::max(0.0f, std::min(duration - 1.0f, frame)) : 0.0f);
        if (Shape* smooth = sPoseVis.draw(t, sPoseBank, clipBank.name, drawFrame, b.generator)) shape = smooth;
    }
    shape->updateAnim(gfx, bodyView, nullptr, t);
    pc_gfx_specular_family_scope(1);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    // Captured weapons ride the staged pose's otakara_* joint (model space).
    int drawn = 0;
    if (!dead) {
        for (int w = 0; w < P2BTWEAPON_Count; ++w) {
            if (!sPellet[w] || !b.fsm.ownership().isWeaponAttached(w)) continue;
            const Mat34& jm = b.fsm.jointModel(w);
            Matrix4f joint;
            for (int r = 0; r < 3; ++r)
                for (int c = 0; c < 4; ++c) joint.mMtx[r][c] = jm.m[r][c];
            joint.mMtx[3][0] = joint.mMtx[3][1] = joint.mMtx[3][2] = 0.0f;
            joint.mMtx[3][3] = 1.0f;
            Matrix4f pelletView;
            bodyView.multiplyTo(joint, pelletView);
            sPellet[w]->updateAnim(gfx, pelletView, nullptr, nullptr);
            sPellet[w]->drawshape(gfx, *gfx.mCamera, nullptr);
            ++drawn;
        }
    }
    // Knocked-off weapons rest where they fell (visual; not carryable yet).
    for (const DroppedWeapon& d : b.dropped) {
        if (!sPellet[d.weapon]) continue;
        Matrix4f world, pelletView;
        world.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, 0.0f, 0.0f), d.pos);
        gfx.mCamera->mLookAtMtx.multiplyTo(world, pelletView);
        sPellet[d.weapon]->updateAnim(gfx, pelletView, nullptr, nullptr);
        sPellet[d.weapon]->drawshape(gfx, *gfx.mCamera, nullptr);
    }
    pc_gfx_specular_family_scope(0);
    int& logged = sDrawLogged[t];
    const int bit = dead ? 2 : 1;
    if (!(logged & bit)) {
        logged |= bit;
        std::printf("P2_BIGTREASURE_DRAW generator=%u source_id=73 corpse=%d clip=%s pose=%zu weapons_drawn=%d "
                    "model=p2_bigtreasure scale=%.2f\n",
                    b.generator, dead ? 1 : 0, sBank.clip[anim].name.c_str(), best, drawn, t->mSRT.s.x);
        std::fflush(stdout);
    }
    return true;
}
