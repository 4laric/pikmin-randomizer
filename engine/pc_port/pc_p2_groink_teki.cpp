#include "pc_p2_groink_teki.h"
#include "pc_p2_groink_teki_policy.h"
#include "pc_p2_groink_carcass.h"
#include "Generator.h"
#include "Pellet.h"
#include "system.h"
#include "teki.h"
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
};
std::map<BTeki*, Binding> s;

const Binding* find(const BTeki* t) {
    auto i = s.find(const_cast<BTeki*>(t));
    return i == s.end() ? nullptr : &i->second;
}
} // namespace

// Process-wide RequestBirth tally. It deliberately lives outside the per-actor
// map so a deferred pellet kill (which erases the binding via forget on the BIRTH
// frame) cannot zero it before the runtime fixture reads the result.
static int sTotalBirths = 0;

void pc_p2_groink_teki_reset() { s.clear(); }

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
int pc_p2_groink_teki_total_births() { return sTotalBirths; }

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
        s.emplace(static_cast<BTeki*>(t), Binding{gen, type, cfg.carcass, {}, false, false, false, false, 0});
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
        std::printf("P2_GROINK_CARCASS_BECOME generator=%u pos=%.3f,%.3f,%.3f face_dir=%.3f\n",
                    b.generator, t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z, t->getDirection());
    }
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
            ++sTotalBirths;
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
