#include "pc_p2_groink_teki.h"
#include "pc_p2_groink_teki_policy.h"
#include "pc_p2_groink_carcass.h"
#include "pc_p2_preview.h"
#include "Generator.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Pellet.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "system.h"
#include "teki.h"
#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>

namespace {
struct Binding {
    unsigned generator;
    int type;
    P2GroinkCarcassConfig config;
    P2GroinkCarcass carcass;
    bool began = false;         // death observed -> carcass begin (doBecomeCarcass)
    bool terminal = false;      // RequestBirth emitted -> stop driving; birth pending lane 06/07
    bool gaugeShown = false;    // TEKIOPT_LifeGaugeVisible currently set
    bool pelletKilled = false;  // KillPellet emitted -> never re-dereference the recycled pellet
    int births = 0;
    bool transport = false;     // sidecar `transport` token: drive the carcass to the Pod
};
std::map<BTeki*, Binding> s;

// Lane 21 transport tail (mirrors the lane-27 landed recipe). After a natural
// free-mode squad kill the bound host's own corpse pellet is held at the kill
// site, the captain is parked beyond the 250u join-party range, and the
// survivors are re-ringed onto the corpse in FreeMode until a carrier latches.
// The carry itself stays natural: FreeMode grasp (Piki::graspSituation) ->
// aiTransport goal (pc_p2_preview_goal() = the Research Pod) -> pc_p2_preview
// delivery, which calls pc_p2_groink_receipt for `corpse:groink:<gen>`.
struct CarcassTail {
    bool active = false;
    bool delivered = false;
    bool captainParked = false;
    Pellet* pellet = nullptr;
    float originX = 0.0f, originZ = 0.0f;
    int probeTick = 0;
};
CarcassTail sTail;
constexpr float kPi = 3.14159265358979323846f;

void reformSurvivors() {
    if (!naviMgr || !pikiMgr || !naviMgr->getNavi()) return;
    Navi* n = naviMgr->getNavi();
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (p && p->isAlive()
            && (p->mMode == PikiMode::FreeMode || p->mMode == PikiMode::TransportMode))
            p->changeMode(PikiMode::FormationMode, n);
    }
}

void stepCarcassTransport(BTeki* t) {
    if (!sTail.active) return;
    // Once the Pod credited the carcass, stop the free roam so leftover
    // dead-Pikmin `pr01` number pellets are not carried to the Pod (the preview
    // denies unregistered cargo and would abort after the receipt landed).
    if (sTail.delivered) {
        reformSurvivors();
        std::printf("P2_GROINK_CARCASS_CORPSE_DELIVERED\n");
        std::fflush(stdout);
        sTail.active = false;
        sTail.pellet = nullptr;
        return;
    }
    if (!sTail.pellet) {
        sTail.pellet = t->mPellet;
        if (sTail.pellet && sTail.pellet->mConfig) {
            std::printf("P2_GROINK_CARCASS_CORPSE_CONFIG carry_min=%d carry_max=%d min_free_slot=%d alive=%d\n",
                        sTail.pellet->mConfig->mCarryMinPikis.mValue,
                        sTail.pellet->mConfig->mCarryMaxPikis.mValue,
                        sTail.pellet->getMinFreeSlotIndex(),
                        sTail.pellet->isAlive() ? 1 : 0);
        }
    }
    if (!sTail.pellet) return;
    // Hold the freshly spawned corpse at the kill site until a carrier latches:
    // its spawn velocity otherwise flings it clear of the ringed squad.
    if (sTail.pellet->getMinFreeSlotIndex() != -1) sTail.pellet->mVelocity.set(0.0f, 0.0f, 0.0f);
    if (sTail.pellet->mConfig) {
        if (sTail.pellet->mConfig->mCarryMaxPikis.mValue < 1) sTail.pellet->mConfig->mCarryMaxPikis.mValue = 6;
        // Fixture concession: the host's own area attack decimates the squad
        // (retail corpse carry_min is higher), so allow a single survivor to
        // haul. The carry itself stays natural (grasp -> route -> Pod credit).
        sTail.pellet->mConfig->mCarryMinPikis.mValue = 1;
    }
    if (naviMgr && pikiMgr && naviMgr->getNavi()) {
        Navi* n = naviMgr->getNavi();
        int carriers = 0, squad = 0;
        Iterator pc(pikiMgr);
        CI_LOOP(pc) {
            Piki* p = static_cast<Piki*>(*pc);
            if (!p || !p->isAlive()) continue;
            ++squad;
            if (p->mMode == PikiMode::TransportMode) ++carriers;
        }
        if (carriers == 0 && sTail.probeTick % 60 == 0) {
            Vector3f park(sTail.originX, 0.0f, sTail.originZ + 300.0f);
            park.y = mapMgr ? mapMgr->getMinY(park.x, park.z, true) : 0.0f;
            n->resetPosition(park);
            n->mVelocity.set(0.0f, 0.0f, 0.0f);
            if (!sTail.captainParked) {
                sTail.captainParked = true;
                std::printf("P2_GROINK_CARCASS_CAPTAIN_PARK x=%.3f z=%.3f\n", park.x, park.z);
            }
            int ring = 0;
            Iterator sq(pikiMgr);
            CI_LOOP(sq) {
                Piki* p = static_cast<Piki*>(*sq);
                if (!p || !p->isAlive()) continue;
                const float a = float(ring) * 2.0f * kPi / float(squad > 0 ? squad : 1);
                Vector3f pt(sTail.originX + 16.0f * std::sin(a), 0.0f,
                            sTail.originZ + 16.0f * std::cos(a));
                pt.y = mapMgr ? mapMgr->getMinY(pt.x, pt.z, true) : 0.0f;
                p->resetPosition(pt);
                p->changeMode(PikiMode::FreeMode, n);
                ++ring;
            }
            std::printf("P2_GROINK_CARCASS_FREE_RECRUIT count=%d carriers=%d squad=%d\n",
                        ring, carriers, squad);
        }
    }
    if (++sTail.probeTick % 30 == 0) {
        const Vector3f& cp = sTail.pellet->mSRT.t;
        const float dx = cp.x - sTail.originX, dz = cp.z - sTail.originZ;
        int transport = 0;
        if (pikiMgr) {
            Iterator tp(pikiMgr);
            CI_LOOP(tp) {
                Piki* p = static_cast<Piki*>(*tp);
                if (p && p->isAlive() && p->mMode == PikiMode::TransportMode) ++transport;
            }
        }
        std::printf("P2_GROINK_CARCASS_CORPSE tick=%d x=%.3f z=%.3f moved=%.3f carriers=%d\n",
                    sTail.probeTick, cp.x, cp.z, std::sqrt(dx * dx + dz * dz), transport);
    }
    std::fflush(stdout);
}

const Binding* find(const BTeki* t) {
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? nullptr : &i->second;
}
// Preview-only bound-host max-life cap (see the header note).
constexpr float kHostLifeClamp = 120.0f;
} // namespace

void pc_p2_groink_teki_reset() { s.clear(); sTail = CarcassTail{}; }

void pc_p2_groink_teki_forget(BTeki* t) {
    if (t) s.erase(t);
}

bool pc_p2_groink_teki_is_bound(const BTeki* t) { return t && find(t) != nullptr; }
float pc_p2_groink_teki_timer(const BTeki* t) {
    const Binding* b = find(t);
    return b ? b->carcass.timer() : 0.0f;
}
float pc_p2_groink_teki_health(const BTeki* t) {
    const Binding* b = find(t);
    return b ? b->carcass.health() : 0.0f;
}
int pc_p2_groink_teki_births(const BTeki* t) {
    const Binding* b = find(t);
    return b ? b->births : 0;
}
int pc_p2_groink_teki_total_births() { return p2_groink_carcass_total_births(); }
bool pc_p2_groink_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    const Binding* b = find(static_cast<BTeki*>(view));
    if (!b) return false;
    generator = b->generator;
    // The preview calls this from pc_p2_preview_deliver when the carried
    // carcass reaches the Pod; record it so the transport tail re-forms the
    // survivors on the next tick and stops the free roam.
    if (sTail.active) sTail.delivered = true;
    return true;
}
float pc_p2_groink_teki_param_f(const BTeki* teki, int idx, float fallback) {
    if (idx != TPF_Life || !pc_pikipelago_room_preview()) return fallback;
    if (!find(teki)) return fallback;
    return fallback < kHostLifeClamp ? fallback : kHostLifeClamp;
}

void pc_p2_groink_teki_setup() {
    pc_p2_groink_teki_reset();
    std::ifstream in("p2-groink-teki.txt");
    if (!in) return;
    p2groink::Binding cfg{};
    if (!p2groink::read(in, cfg) || !tekiMgr) std::abort();
    // Fail closed on an unusable carcass config before any actor is bound.
    { P2GroinkCarcass probe; if (!probe.become(cfg.carcass)) std::abort(); }
    unsigned gen = cfg.generator;
    int type = cfg.type;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        auto* t = static_cast<Teki*>(*it);
        if (!t || !t->mGenerator || t->mGenerator->_70 != gen) continue;
        if (t->mTekiType != type || s.size()) std::abort();
        // A host that leaves no corpse dies through dieSoon -> kill -> doKill,
        // which runs pc_p2_forget_teki on the death frame and erases this binding
        // before RequestBirth can ever fire (tekibteki.cpp:681-721, 742-749).
        // Only a LeaveCorpse host survives death as a revivable carcass pellet.
        if (t->getParameterI(TPI_CorpseType) != TEKICORPSE_LeaveCorpse) {
            std::printf("P2_GROINK_CARCASS_UNBOUND generator=%u type=%d reason=no_corpse\n", gen, type);
            continue;
        }
        s.emplace(static_cast<BTeki*>(t), Binding{gen, type, cfg.carcass, {}, false, false, false, false, 0, cfg.transport});
        std::printf("P2_GROINK_CARCASS_READY generator=%u type=%d gauge_delay=%.3f recovery=%.3f max_health=%.3f\n",
                    gen, type, cfg.carcass.gaugeDelay, cfg.carcass.recoverySeconds, cfg.carcass.maxHealth);
    }
}

void pc_p2_groink_teki_tick(BTeki* t) {
    auto i = s.find(t);
    if (i == s.end()) return;
    Binding& b = i->second;
    if (b.terminal) return;
    const float dt = gsys->getFrameTime();
    // A carcass begins the moment the live actor drops to death (mHealth <= 0),
    // mirroring doBecomeCarcass.  The regrowth timeline is then read from the
    // actor's own update cadence and pellet presence, not injected.
    if (!b.began) {
        if (t->mHealth > 0.0f) return; // still alive: no carcass yet
        if (!b.carcass.become(b.config)) {
            std::fputs("P2_GROINK_CARCASS invalid config\n", stderr);
            std::abort();
        }
        b.began = true;
        if (b.transport) {
            sTail.active = true;
            sTail.delivered = false;
            sTail.captainParked = false;
            sTail.pellet = nullptr;
            sTail.originX = t->mSRT.t.x;
            sTail.originZ = t->mSRT.t.z;
            sTail.probeTick = 0;
        }
        std::printf("P2_GROINK_CARCASS_BECOME generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f\n",
                    b.generator, t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z, t->getDirection());
    }
    // Natural carcass -> Pod carry (transport profile only).
    if (b.transport) stepCarcassTransport(t);
    // The carcass "pellet" is the actor's own corpse pellet (PelletView::mPellet).
    // Once KillPellet has fired the pellet slot may be recycled by pelletMgr, so
    // it is never re-dereferenced after that (defensive; see the kill note below).
    const bool pelletAlive = !b.pelletKilled && t->mPellet != nullptr && t->mPellet->isAlive();
    // gaugeManager is bound to the P1 life-gauge manager. ActivateGauge only
    // toggles TEKIOPT_LifeGaugeVisible; BTeki::update runs updateLifeGauge only
    // while mDeadState == 0, so on a corpse the toggle is inert (not updated),
    // and the regrowth amount is surfaced via pc_p2_groink_teki_health()/markers,
    // not the on-screen ring (a real health regrowth is a lane 06/07 concern).
    const P2GroinkCarcassStep step = b.carcass.step(dt, pelletAlive, /*gaugeManager=*/true, /*activeTick=*/true);
    if (!step.valid) return;
    // Snapshot and log every command BEFORE the pellet is killed. Killing the
    // pellet runs Pellet::doKill -> viewKill -> BTeki::doKill ->
    // pc_p2_forget_teki, which erases this binding (and clears the actor), so no
    // field of `t` or `b` may be read after the kill. The kill is done last.
    bool killPellet = false;
    for (std::size_t k = 0; k < step.count; ++k) {
        switch (step.commands[k]) {
        case P2GroinkCarcassCommand::ActivateGauge:
            if (!b.gaugeShown) { t->setTekiOption(TEKIOPT_LifeGaugeVisible); b.gaugeShown = true; }
            std::printf("P2_GROINK_CARCASS_GAUGE_ACTIVE generator=%u timer=%.3f\n", b.generator, b.carcass.timer());
            break;
        case P2GroinkCarcassCommand::DeactivateGauge:
            if (b.gaugeShown) { t->clearTekiOption(TEKIOPT_LifeGaugeVisible); b.gaugeShown = false; }
            std::printf("P2_GROINK_CARCASS_GAUGE_INACTIVE generator=%u\n", b.generator);
            break;
        case P2GroinkCarcassCommand::KillPellet:
            killPellet = true;
            std::printf("P2_GROINK_CARCASS_KILL_PELLET generator=%u health=%.3f\n", b.generator, b.carcass.health());
            break;
        case P2GroinkCarcassCommand::RequestBirth: {
            P2GroinkCarcassBirth born;
            born.position = { t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z };
            born.faceDir = t->getDirection();
            // EnemyBirthArg existence duration / Piklopedia flag belong to the
            // lane 06/07 manager birth; the sidecar records the surviving host
            // identity but leaves that birth to the shared actor hook.
            born.existenceLength = -1.0f;
            born.inPiklopedia = false;
            ++b.births;
            p2_groink_carcass_note_birth();
            std::printf("P2_GROINK_CARCASS_BIRTH generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f existence_length=%.3f in_piklopedia=%d health=%.3f\n",
                        b.generator, born.position.x, born.position.y, born.position.z,
                        born.faceDir, born.existenceLength, born.inPiklopedia ? 1 : 0,
                        b.carcass.health());
            // Records the descriptor and stops driving. On a P1 host the pellet
            // kill below also tears down the actor + pellet, so the binding is
            // erased and "stop ticking" is moot; the replacement birth itself is
            // pending lane 06/07.
            b.terminal = true;
            break;
        }
        }
    }
    // Kill the pellet last, after every marker is recorded and every field read;
    // never touch `t` or `b` again (the kill erases the binding on a P1 host).
    if (killPellet) {
        b.pelletKilled = true; // still valid here; the kill below erases the binding on a P1 host
        if (t->mPellet) t->mPellet->kill(false);
    }
}
