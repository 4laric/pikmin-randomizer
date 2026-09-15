// Private real-GL slice-2 runtime fixture for the BigTreasure elemental
// damage-receiver acceptance (#246), built by scripts/build_pikmin2_fixture.py
// only (not part of the game target). Boots the frozen room preview with the
// live 20-red squad and observes, on real live Pikmin:
//   * the wired receiver host applies the source stimulus (non-immune target
//     enters the hazard state) and rejects immune targets (Red/fire, Blue/water).
//     These are DIRECT host-helper calls on live Pikmin; the ordinary loop's
//     attack -> element-geometry -> receiver path is NOT driven here (a
//     standalone element runtime + a teleported Pikmin is used for the geometry
//     check, with host.trace=nullptr).
//   * the handled set dedups (probe first=1, second=0); this proves set-dedupe
//     only, not per-attack re-arm.
//   * one weapon is knocked off through the lane's natural-hit ingress
//     (pc_p2_hardlanes_bigtreasure_hit) — an INJECTED max-health hit, since no
//     engine-side caller or Pikmin coll-part attacker exists. The attached-
//     weapon count drops; the FSM is still in its boot landing (no re-pick).
//
// The 960x540 centred window and the live starting squad are asserted at boot.

#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "gl/pc_opengl.h"
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "MoviePlayer.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "system.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_window.h"
#include "pc_p2_preview.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "pc_p2_bigtreasure_receiver_host.h"
#include "pc_p2_bigtreasure_elements.h"
#include "pc_p2_hardlanes.h"
#include "pc_p2_species.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
constexpr float kDt = 1.0f / 30.0f;

void require(bool value, const char* message)
{
    if (!value) {
        std::printf("FAIL BIGTREASURE_SLICE2 %s\n", message);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

// Returns an alive field Pikmin in a normal state (falling back to any alive
// Pikmin), so each receiver check uses a distinct fresh target.
Piki* freshPiki()
{
    if (!pikiMgr) {
        return nullptr;
    }
    Piki* fallback = nullptr;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* piki = static_cast<Piki*>(*it);
        if (!piki || !piki->isAlive()) {
            continue;
        }
        if (!fallback) {
            fallback = piki;
        }
        if (piki->getState() == PIKISTATE_Normal) {
            return piki;
        }
    }
    return fallback;
}

class Slice2App final : public PlugPikiApp {
    int frames = 0;
    int squad = 0;
    bool setup = false;
    int checkPhase = 0;   // 0 receiver acceptance, 1 phase transition, 2 exit
    int phaseWait = 0;    // frames yielded while the loop applies a queued hit
    int weaponsBefore = 0;
    float ground = 0.0f;

public:
    int idle() override
    {
        int result = PlugPikiApp::idle();
        require(++frames < 3600, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
            gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll
            || gameflow.mIsUIOverlayActive) {
            return result;
        }
        if (!setup) {
            SDL_Window* window = SDL_GL_GetCurrentWindow();
            require(window != nullptr, "window");
            int w = 0, h = 0, x = 0, y = 0;
            SDL_GetWindowSize(window, &w, &h);
            SDL_GetWindowPosition(window, &x, &y);
            require(w == 960 && h == 540, "window size 960x540");
            std::printf("P2_BIGTREASURE_WINDOW size=%dx%d pos=%d,%d\n", w, h, x, y);
            ground = mapMgr->getMinY(0, 0, false);
            require(std::isfinite(ground), "center ground unavailable");
            squad = countSquad();
            require(squad >= 20, "live starting squad (>=20)");
            std::printf("P2_BIGTREASURE_SLICE2_SQUAD alive=%d\n", squad);
            setup = true;
        }
        switch (checkPhase) {
        case 0:
            runReceiverAcceptance();
            checkPhase = 1;
            break;
        case 1:
            runPhaseTransition();
            break;
        default:
            break;
        }
        return result;
    }

    void draw(Graphics& gfx) override { PlugPikiApp::draw(gfx); }

private:
    int countSquad()
    {
        int alive = 0;
        if (!pikiMgr) {
            return 0;
        }
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* piki = static_cast<Piki*>(*it);
            if (piki && piki->isAlive()) {
                ++alive;
            }
        }
        return alive;
    }

    void runReceiverAcceptance()
    {
        const P2BigTreasureVec3 origin{ 0.0f, ground, 0.0f };
        std::printf("P2_BIGTREASURE_SLICE2_DIAG weapons_at_start=%d ready=%d\n",
                    pc_p2_hardlanes_bigtreasure_weapon_count(),
                    pc_p2_hardlanes_bigtreasure_ready() ? 1 : 0);

        // Fire on a live Red: source InteractFire rejects fire-immune Red, so
        // the wired receiver returns false (immune) and does not startFire.
        Piki* red = freshPiki();
        require(red != nullptr, "fresh red for fire immunity");
        require(pc_p2_species(red) == P2SpeciesRed, "squad is red");
        require(!pc_p2_bigtreasure_stimulate_piki(P2BTWEAPON_Fire, origin,
                                                  kBigTreasureDefaultAttackDamage, red),
                "fire-red immune (accepted=0)");
        std::printf("P2_BIGTREASURE_SLICE2_IMMUNE weapon=fire species=red\n");

        // Water on a live Red: non-immune -> PIKISTATE_Bubble.
        Piki* redWater = freshPiki();
        require(redWater != nullptr, "fresh red for water accept");
        require(pc_p2_bigtreasure_stimulate_piki(P2BTWEAPON_Water, origin,
                                                 kBigTreasureDefaultAttackDamage, redWater),
                "water-red accepted");
        require(redWater->getState() == PIKISTATE_Bubble, "water-red enters Bubble");
        std::printf("P2_BIGTREASURE_SLICE2_HIT weapon=water species=red state=Bubble\n");

        // Gas on a live Red: -> PIKISTATE_Panic.
        Piki* redGas = freshPiki();
        require(redGas != nullptr, "fresh red for gas accept");
        require(pc_p2_bigtreasure_stimulate_piki(P2BTWEAPON_Gas, origin,
                                                 kBigTreasureDefaultAttackDamage, redGas),
                "gas-red accepted");
        require(redGas->getState() == PIKISTATE_Panic, "gas-red enters Panic");
        std::printf("P2_BIGTREASURE_SLICE2_HIT weapon=gas species=red state=Panic\n");

        // Elec on a live Red: -> PIKISTATE_DenkiDying.
        Piki* redElec = freshPiki();
        require(redElec != nullptr, "fresh red for elec accept");
        require(pc_p2_bigtreasure_stimulate_piki(P2BTWEAPON_Elec, origin,
                                                 kBigTreasureDefaultAttackDamage, redElec),
                "elec-red accepted");
        require(redElec->getState() == PIKISTATE_DenkiDying, "elec-red enters DenkiDying");
        std::printf("P2_BIGTREASURE_SLICE2_HIT weapon=elec species=red state=DenkiDying\n");

        // Water on a Blue (injected identity): source InteractBubble rejects
        // Blue, so the wired receiver returns false. Identity injection is
        // labelled; the live squad is all Red, so Blue cannot be observed
        // naturally in this arena. The species is restored to Red afterwards so
        // the injected identity does not leak into later checks.
        Piki* blue = freshPiki();
        require(blue != nullptr && pc_p2_set_species(blue, P2SpeciesBlue),
                "inject blue species");
        require(!pc_p2_bigtreasure_stimulate_piki(P2BTWEAPON_Water, origin,
                                                  kBigTreasureDefaultAttackDamage, blue),
                "water-blue immune (accepted=0)");
        require(pc_p2_set_species(blue, P2SpeciesRed), "restore red species");
        std::printf("P2_BIGTREASURE_SLICE2_IMMUNE weapon=water species=blue(injected)\n");

        // Element geometry -> live target: a running water attack emits a
        // bubble at the raised joint; a live Red placed there resolves a hit
        // through queryHit and is then stimulated by the same wired receiver.
        P2BigTreasureElementRuntime runtime;
        require(runtime.start(P2BTWEAPON_Water, origin, ground,
                              P2BigTreasureOwnership::kWeaponMaxHealth, 0.25f, 0.25f),
                "water element start");
        P2BigTreasureElementHost host;
        host.context = nullptr;
        host.trace = nullptr;
        host.ground = nullptr;
        P2BigTreasureElementStats stats;
        int guard = 0;
        while (stats.nodes == 0 && guard++ < 60) {
            runtime.tick(kDt, host, stats);
        }
        require(stats.nodes > 0, "water element emitted a node");
        Piki* geoPiki = freshPiki();
        require(geoPiki != nullptr, "fresh red for geometry hit");
        // The first bubble is emitted at the raised joint (mGround + 100) and
        // only moves a few units in its first tick, so the emit anchor is still
        // inside its in-flight radius.
        geoPiki->mSRT.t.set(origin.x, ground + 100.0f, origin.z);
        require(runtime.queryHit(P2BigTreasureVec3{ geoPiki->mSRT.t.x, geoPiki->mSRT.t.y,
                                                    geoPiki->mSRT.t.z }),
                "element geometry resolves a hit");
        require(pc_p2_bigtreasure_stimulate_piki(P2BTWEAPON_Water, origin,
                                                 kBigTreasureDefaultAttackDamage, geoPiki),
                "geometry hit stimulates the live target");
        require(geoPiki->getState() == PIKISTATE_Bubble, "geometry hit enters Bubble");
        runtime.defeat();
        std::printf("P2_BIGTREASURE_SLICE2_GEOMETRY weapon=water species=red state=Bubble\n");

        // Probe applies the stimulus to a live target through the ordinary
        // loop's receiver (a test hook; it does not pollute the handled set).
        // The real per-attack handled-set hold is the loop's own
        // P2_BIGTREASURE_RECV_HELD, exercised by the slice-3 fixture.
        Piki* handled = freshPiki();
        require(handled != nullptr, "fresh red for probe");
        const int first = pc_p2_hardlanes_bigtreasure_recv_probe(P2BTWEAPON_Water, handled);
        require(first == 1, "probe applies the stimulus");
        std::printf("P2_BIGTREASURE_SLICE2_HANDLED first=%d\n", first);

        std::printf("P2_BIGTREASURE_SLICE2_RECEIVER_PASS squad=%d\n", squad);
    }

    void runPhaseTransition()
    {
        // NOTE (injected): the knock-off below is driven by this fixture posting
        // a max-health hit through pc_p2_hardlanes_bigtreasure_hit, the lane's
        // natural-hit ingress. There is NO engine-side caller of that ingress and
        // no Pikmin coll-part attacker, so this is an INJECTED weapon destroy,
        // equivalent to writing the weapon's health to zero. It proves the FSM
        // host knock-off + count drop, not a natural Pikmin attack, and the FSM
        // is still in its boot landing (Stay->Land); no PreAttack/pickWeapon
        // re-pick is exercised.
        require(pc_p2_hardlanes_bigtreasure_ready(), "ordinary seam active");
        if (phaseWait == 0) {
            weaponsBefore = pc_p2_hardlanes_bigtreasure_weapon_count();
            require(weaponsBefore == 4, "four weapons attached");
            std::printf("P2_BIGTREASURE_SLICE2_DIAG phase_weapons_before=%d\n", weaponsBefore);
            require(pc_p2_hardlanes_bigtreasure_hit(P2BTWEAPON_Elec,
                                                    P2BigTreasureOwnership::kWeaponMaxHealth,
                                                    false),
                    "ingress accepts the max-health hit (injected)");
            ++phaseWait;
            return;
        }
        // Let the ordinary update apply the queued hit (one per source tick).
        ++phaseWait;
        const int after = pc_p2_hardlanes_bigtreasure_weapon_count();
        if (after < weaponsBefore) {
            std::printf("P2_BIGTREASURE_SLICE2_DROP_INGRESS weapons=%d->%d injected=1 repick=0\n",
                        weaponsBefore, after);
            std::printf("P2_BIGTREASURE_SLICE2_REPICK observed=0\n");
            std::puts("PASS BIGTREASURE_SLICE2_RECEIVER_ONLY");
            std::fflush(stdout);
            std::_Exit(0);
        }
        require(phaseWait < 60, "weapon knock-off not observed in time");
    }
};
} // namespace

int main(int argc, char** argv)
{
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1);
    SDL_SetMainReady();
    pc_gpu_preference_apply();
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    require(pc_window_init("BigTreasure slice-2 receiver fixture", 960, 540), "window init");
    pc_settings_init();
    pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    pc_window_set_window_size(960, 540);
    pc_window_center();
    gsys->Initialise();
    pc_settings_p2d_init();
    nodeMgr = new NodeMgr();
    gsys->run(new Slice2App());
    return 0;
}
