// Private real-GL display fixture; no production registration or receiver claims.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "App.h"
#include "Node.h"
#include "Graphics.h"
#include "GameCoreSection.h"
#include "Generator.h"
#include "Section.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Collision.h"
#include "Creature.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_gfx.h"
#include "pc_p2_kurage_arena.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_onikurage_teki.h"
#include "pc_p2_preview.h"
#include "teki.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "system.h"
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <string>

namespace {
bool sKillScenario = false, sTransferScenario = false, sStageExitScenario = false, sAdmissionScenario = false, sAutomaticBindingScenario = false, sOniKurageScenario = false, sIngestionScenario = false;
void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL KURAGE_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}
GameCoreSection* findCore(CoreNode* node, int depth = 0)
{
    if (!node || depth > 20) return nullptr;
    if (auto* core = dynamic_cast<GameCoreSection*>(node)) return core;
    for (auto* child = node->Child(); child; child = child->Next())
        if (auto* core = findCore(child, depth + 1)) return core;
    return nullptr;
}
void capture(const char* path)
{
    pc_gfx_flush_batch();
    auto bind = reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    require(bind != nullptr, "framebuffer entry point unavailable");
    GLint previous = 0; glGetIntegerv(GL_FRAMEBUFFER_BINDING, &previous); bind(GL_FRAMEBUFFER, 0);
    int width = 0, height = 0; SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(), &width, &height);
    std::vector<unsigned char> pixels(size_t(width) * size_t(height) * 3);
    glReadBuffer(GL_BACK); glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadBuffer(GL_BACK); glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
    bind(GL_FRAMEBUFFER, previous);
    require(glGetError() == GL_NO_ERROR, "capture GL error");
    bool visible = false; for (unsigned char value : pixels) visible |= value > 8;
    require(visible, "empty capture");
    FILE* file = std::fopen(path, "wb"); require(file != nullptr, "capture file");
    std::fprintf(file, "P6\n%d %d\n255\n", width, height);
    for (int y = height - 1; y >= 0; --y) std::fwrite(pixels.data() + size_t(y) * width * 3, 1, size_t(width) * 3, file);
    std::fclose(file);
}
class KurageApp final : public PlugPikiApp {
    int frames = 0, readyFrames = 0, admissionTicks = 0; bool setup = false, captured = false, ownerAlive = true, receiverTested = false;
    Piki* admissionPiki = nullptr;
    int ingestionTicks = 0, ingestionStage = 0;
    Piki* ingestionPiki = nullptr;
    class FixtureOwner final : public Creature {
    public:
        FixtureOwner() : Creature(nullptr) { }
        void refresh(Graphics&) override { }
        void doKill() override { }
    } replacement;
    CollPart replacementPart{};
    void setupReplacement() {
        replacement.mStickListHead = nullptr;
        replacement.mSRT.t.set(300, 200, 100); replacement.mSRT.s.set(1, 1, 1); replacement.mSRT.r.set(0, 0, 0);
        replacementPart.mPartType = PART_BoundSphere; replacementPart.mRadius = 20;
        replacementPart.mCentre.set(300, 200, 100); replacementPart.mJointMatrix.makeIdentity();
    }
public:
    int idle() override {
        int result = PlugPikiApp::idle(); require(++frames < 900, "timeout");
        if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if (sAutomaticBindingScenario) {
            if (!tekiMgr) return result;
            BTeki* generatedFrog = nullptr;
            Iterator it(tekiMgr); CI_LOOP(it) {
                Teki* teki = static_cast<Teki*>(*it);
                if (teki && teki->mTekiType == TEKI_Frog && teki->mGenerator && teki->mGenerator->_70 == 201001u) {
                    generatedFrog = static_cast<BTeki*>(teki);
                    break;
                }
            }
            if (!generatedFrog) return result;
            if (sOniKurageScenario) {
                require(pc_p2_onikurage_teki_is_bound(generatedFrog), "finalSetup sidecar bound generated OniKurage actor");
                require(pc_p2_onikurage_teki_mouth_slots() == 2, "OniKurage binds two captain mouth slots");
                std::puts("P2_ONIKURAGE_AUTO_BIND_PASS generator=201001 type=0 variant=Greater mouth_slots=2 source=GameCoreSection::finalSetup sidecar=p2-onikurage-teki.txt direct_bind_calls=0");
                std::fflush(stdout); std::_Exit(0);
            }
            require(pc_p2_kurage_teki_is_bound(generatedFrog), "finalSetup sidecar bound generated Frog");
            std::puts("P2_KURAGE_AUTO_BIND_PASS generator=201001 type=0 source=GameCoreSection::finalSetup sidecar=p2-kurage-teki.txt direct_bind_calls=0");
            std::fflush(stdout); std::_Exit(0);
        }
        if (!pc_p2_preview_ready() || !naviMgr || !naviMgr->getNavi() || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) return result;
        ++readyFrames;
        if (!setup) {
            int liveSquad = 0; Iterator squad(pikiMgr);
            CI_LOOP(squad) { if (static_cast<Piki*>(*squad)) ++liveSquad; }
            std::printf("P2_KURAGE_SQUAD live=%d\n", liveSquad); std::fflush(stdout);
            Navi* n = naviMgr->getNavi();
            n->resetPosition(Vector3f(0, 0, -250)); n->mFaceDirection = 0; n->mSRT.r.set(0, 0, 0);
            require(pc_p2_kurage_arena_setup("p2-kurage-arena.txt"), "arena setup"); setup = true;
            std::fprintf(stderr, "P2_KURAGE_RECEIVER_STEP setup\n");
            Creature* owner = pc_p2_kurage_arena_owner();
            CollPart* mouth = pc_p2_kurage_arena_mouth();
            require(owner && mouth && pc_p2_kurage_receiver_setup(owner, mouth), "actual host receiver setup");
            Piki* piki = static_cast<Piki*>(pikiMgr->birth()); require(piki != nullptr, "receiver piki birth");
            piki->init(n); piki->resetPosition(owner->mSRT.t); piki->mMode = PikiMode::AttackMode;
            std::printf("P2_KURAGE_RECEIVER_PRE alive=%d stick=%d may=%d mouth=%p owner=actual_kurage_host\n", int(piki->isAlive()), int(piki->isStickTo()), int(piki->mayIstick()), (void*)mouth);
            if (sAdmissionScenario) {
                piki->resetPosition(Vector3f(owner->mSRT.t.x, owner->mSRT.t.y - 30.0f, owner->mSRT.t.z));
                admissionPiki = piki;
                require(pc_p2_kurage_arena_begin_attack(), "retail attack clock start");
                // p2retail::due has SysShape's positive timer behavior: key 37
                // dispatches as the clock crosses into frame 38.
                require(pc_p2_kurage_arena_tick_attack(37.0f), "attack clock before key 37");
                require(!pc_p2_kurage_arena_attack_pose_active()
                    && pc_p2_kurage_arena_scan_admit(10.0f, 35.0f, 1, true) == 0
                    && pc_p2_kurage_receiver_count() == 0, "attack window closed before event 37");
                require(pc_p2_kurage_arena_tick_attack(1.0f), "attack clock key 37");
                require(pc_p2_kurage_arena_attack_pose_active()
                    && pc_p2_kurage_arena_scan_admit(10.0f, 35.0f, 1, true) == 1,
                    "source-shaped host admission scan");
                require(pc_p2_kurage_receiver_count() == 1 && pc_p2_kurage_receiver_stomach_count() == 0,
                    "mouth travel reserved before stomach");
                return result;
            }
            if (sIngestionScenario) {
                // InteractSuikomi-equivalent admission: the Piki is reserved for
                // mouth travel but has not entered the stomach yet.
                piki->resetPosition(Vector3f(owner->mSRT.t.x, owner->mSRT.t.y - 30.0f, owner->mSRT.t.z));
                ingestionPiki = piki;
                require(pc_p2_kurage_receiver_admit(piki), "ingestion mouth admission");
                require(pc_p2_kurage_receiver_count() == 1 && pc_p2_kurage_receiver_stomach_count() == 0
                    && pc_p2_kurage_receiver_controls(piki), "ingestion mouth travel reserved");
                return result;
            }
            require(pc_p2_kurage_receiver_capture(piki) && pc_p2_kurage_receiver_count() == 1, "receiver capture");
            if (sStageExitScenario) {
                // exitStage invalidates manager and stage-heap objects.  Do not
                // dereference Piki/owner pointers after it returns.
                const bool capturedBeforeExit = pc_p2_kurage_receiver_count() == 1;
                GameCoreSection* core = findCore(gameflow.mGameSection);
                require(capturedBeforeExit && core, "stage exit preconditions");
                core->exitStage();
                require(pc_p2_kurage_receiver_count() == 0, "stage exit receiver reset");
                std::puts("PASS KURAGE_RUNTIME receiver_stageexit"); std::fflush(stdout); std::_Exit(0);
            }
            if (sKillScenario) {
                piki->kill(false);
                require(!piki->isAlive() && !piki->isStickTo() && pc_p2_kurage_receiver_count() == 0, "receiver predeath revoke");
                receiverTested = true;
                return result;
            }
            if (sTransferScenario) {
                // A valid concrete Creature/CollPart pair, matching the live Demon
                // fixture, proves a receiver release cannot detach a newer owner.
                setupReplacement(); piki->endStickObject();
                piki->startStickObject(&replacement, &replacementPart, -1, 0.0f);
                require(piki->isAlive() && piki->isStickTo() && piki->getStickObject() == &replacement
                    && piki->getStickPart() == &replacementPart, "second owner attachment");
                pc_p2_kurage_receiver_update(0.0f, true, true, false);
                require(pc_p2_kurage_receiver_count() == 0 && piki->isAlive()
                    && piki->getStickObject() == &replacement && piki->getStickPart() == &replacementPart,
                    "update preserves second owner");
                pc_p2_kurage_receiver_owner_invalidated(owner);
                require(pc_p2_kurage_receiver_count() == 0 && piki->isAlive()
                    && piki->getStickObject() == &replacement && piki->getStickPart() == &replacementPart,
                    "owner invalidation preserves second owner");
                // Detach before the fixture-owned Creature and CollPart go away.
                piki->endStickObject();
                require(piki->isAlive() && !piki->isStickTo() && piki->getStickObject() == nullptr,
                    "second owner cleanup");
                std::puts("PASS KURAGE_RUNTIME receiver_transfer"); std::fflush(stdout); std::_Exit(0);
            }
            piki->endStickObject();
            pc_p2_kurage_receiver_update(1.0f, true, true, false);
            require(pc_p2_kurage_receiver_count() == 0, "receiver external replacement");
            require(piki->isAlive() && !piki->isStickTo() && piki->getStickObject() == nullptr, "receiver detach state");
            piki->mMode = PikiMode::AttackMode;
            require(pc_p2_kurage_receiver_capture(piki) && pc_p2_kurage_receiver_count() == 1, "receiver recapture");
            pc_p2_kurage_receiver_owner_invalidated(owner);
            require(pc_p2_kurage_receiver_count() == 0, "receiver owner invalidation");
            require(pc_p2_kurage_receiver_setup(owner, mouth), "receiver re-setup");
            piki->mMode = PikiMode::AttackMode;
            require(pc_p2_kurage_receiver_capture(piki) && pc_p2_kurage_receiver_count() == 1, "receiver post-invalidation capture");
            pc_p2_kurage_receiver_update(16.0f, true, true, false);
            require(piki->isAlive() && pc_p2_kurage_receiver_count() == 1
                && piki->mSRT.s.x == 1.0f, "receiver alive at stomach 16s");
            pc_p2_kurage_receiver_update(0.25f, true, true, false);
            require(piki->isAlive() && piki->mSRT.s.x == 0.5f, "receiver half scale at 16.25s");
            piki->endStickObject();
            pc_p2_kurage_receiver_update(0.0f, true, true, false);
            require(pc_p2_kurage_receiver_count() == 0 && piki->isAlive() && !piki->isStickTo()
                && piki->mSRT.s.x == 1.0f, "receiver external detach restores scale");
            piki->mMode = PikiMode::AttackMode;
            require(pc_p2_kurage_receiver_capture(piki), "receiver pause recapture");
            pc_p2_kurage_receiver_update(16.0f, true, true, false);
            pc_p2_kurage_receiver_update(0.25f, true, true, false);
            pc_p2_kurage_receiver_update(20.0f, true, true, true);
            require(piki->isAlive() && pc_p2_kurage_receiver_count() == 1
                && piki->mSRT.s.x == 0.5f, "receiver bitter paused shrink");
            pc_p2_kurage_receiver_update(20.0f, true, false, false);
            require(piki->isAlive() && pc_p2_kurage_receiver_count() == 1
                && piki->mSRT.s.x == 0.5f, "receiver zero-health paused shrink");
            pc_p2_kurage_receiver_owner_invalidated(owner);
            require(pc_p2_kurage_receiver_count() == 0 && piki->isAlive() && !piki->isStickTo()
                && piki->mSRT.s.x == 1.0f, "receiver release restores scale");
            require(pc_p2_kurage_receiver_setup(owner, mouth), "receiver shrink re-setup");
            piki->mMode = PikiMode::AttackMode;
            require(pc_p2_kurage_receiver_capture(piki), "receiver shrink recapture");
            pc_p2_kurage_receiver_update(16.0f, true, true, false);
            pc_p2_kurage_receiver_update(0.25f, true, true, false);
            require(piki->isAlive() && piki->mSRT.s.x == 0.5f, "receiver shrink second half scale");
            pc_p2_kurage_receiver_update(0.25f, true, true, false);
            require(pc_p2_kurage_receiver_count() == 0, "receiver dead at 16.5s");
            require(!piki->isAlive() && !piki->isStickTo() && piki->getStickObject() == nullptr, "receiver digest state");
            std::puts("P2_KURAGE_DIGEST_PASS alive16=1 half16_25=0.5 external_detach_scale=1 bitter_pause=1 health_pause=1 dead16_5=1 release_scale=1");
            receiverTested = true;
        }
        if (sAdmissionScenario) {
            ++admissionTicks;
            // The private host owns receiver lifecycle advancement.  It runs
            // after this frame, refreshes the live mouth target, and the next
            // normal Piki frame consumes that receiver-owned velocity.
            require(pc_p2_kurage_arena_update(0.025f, true), "host receiver lifecycle update");
            if (admissionTicks == 1) {
                require(admissionPiki->isAlive() && !admissionPiki->isStickTo()
                    && pc_p2_kurage_receiver_stomach_count() == 0, "mouth velocity armed before stomach");
            } else if (pc_p2_kurage_receiver_stomach_count() == 1) {
                require(admissionPiki->isAlive() && admissionPiki->isStickTo()
                    && pc_p2_kurage_receiver_stomach_count() == 1 && admissionPiki->mSRT.t.y >= 135.0f,
                    "real frame mouth arrival enters stomach");
                require(pc_p2_kurage_arena_tick_attack(30.0f), "attack clock key 67");
                require(!pc_p2_kurage_arena_attack_pose_active()
                    && pc_p2_kurage_arena_scan_admit(10.0f, 35.0f, 1, true) == 0,
                    "attack window closed at event 67");
                std::puts("P2_KURAGE_ADMISSION_PASS clock=attack.bca:120 key37=type2 key60=loop key67=type1 scan=1 mouth_velocity=600 attachment_enter=1 lifecycle=host_update string_stage=none window=37..67");
                std::puts("PASS KURAGE_RUNTIME receiver_admission"); std::fflush(stdout); std::_Exit(0);
            } else {
                require(admissionTicks < 12, "real frame mouth arrival timeout");
            }
            return result;
        }
        if (sIngestionScenario) {
            ++ingestionTicks;
            if (ingestionStage == 0) {
                // Source execMouth: mouth travel completes on a real host frame,
                // then the Piki captures the stomach and starts mKurageKillTime.
                require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "ingestion host update");
                if (pc_p2_kurage_receiver_stomach_count() == 1) {
                    require(ingestionPiki->isAlive() && ingestionPiki->isStickTo()
                        && ingestionPiki->getStickObject() == pc_p2_kurage_arena_owner()
                        && ingestionPiki->getStickPart() == pc_p2_kurage_arena_mouth(),
                        "ingestion stomach attachment");
                    ingestionStage = 1;
                } else {
                    require(ingestionTicks < 12, "ingestion mouth arrival timeout");
                }
                return result;
            }
            if (ingestionStage == 1) {
                pc_p2_kurage_receiver_update(16.0f, true, true, false);
                require(ingestionPiki->isAlive() && ingestionPiki->mSRT.s.x == 1.0f,
                    "ingestion kill timer armed at 16s");
                pc_p2_kurage_receiver_update(0.25f, true, true, false);
                require(ingestionPiki->isAlive() && ingestionPiki->mSRT.s.x == 0.5f,
                    "ingestion shrink half scale");
                ingestionStage = 2;
                return result;
            }
            // execStomach pauses: bitter and zero-health, then the owner-death
            // gate (health<=0 keeps the Piki; owner not alive cleans up).
            pc_p2_kurage_receiver_update(20.0f, true, true, true);
            pc_p2_kurage_receiver_update(20.0f, true, false, false);
            require(ingestionPiki->isAlive() && ingestionPiki->mSRT.s.x == 0.5f,
                "ingestion bitter and zero-health paused shrink");
            pc_p2_kurage_receiver_update(0.0f, false, false, false);
            require(pc_p2_kurage_receiver_count() == 0 && ingestionPiki->isAlive()
                && !ingestionPiki->isStickTo() && ingestionPiki->mSRT.s.x == 1.0f,
                "ingestion owner-death cleanup restores scale");
            require(pc_p2_kurage_receiver_setup(pc_p2_kurage_arena_owner(), pc_p2_kurage_arena_mouth()),
                "ingestion re-setup");
            ingestionPiki->mMode = PikiMode::AttackMode;
            require(pc_p2_kurage_receiver_capture(ingestionPiki), "ingestion recapture");
            pc_p2_kurage_receiver_update(16.0f, true, true, false);
            pc_p2_kurage_receiver_update(0.25f, true, true, false);
            require(ingestionPiki->isAlive() && ingestionPiki->mSRT.s.x == 0.5f,
                "ingestion shrink second half scale");
            pc_p2_kurage_receiver_update(0.25f, true, true, false);
            require(pc_p2_kurage_receiver_count() == 0 && !ingestionPiki->isAlive()
                && !ingestionPiki->isStickTo(), "ingestion shrink death");
            std::puts("P2_KURAGE_INGESTION_PASS admit=1 mouth_travel=1 stomach_attach=1 kill_time=16 shrink=0.5 bitter_pause=1 health_pause=1 owner_death_cleanup=1 shrink_death=1");
            std::puts("PASS KURAGE_RUNTIME receiver_ingestion"); std::fflush(stdout); std::_Exit(0);
            return result;
        }
        if (readyFrames > 240) {
            require(receiverTested, "receiver test missing");
            ownerAlive = false;
            pc_p2_kurage_receiver_owner_invalidated(naviMgr->getNavi());
            pc_p2_kurage_arena_reset();
        } else require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "host update");
        return result;
    }
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx); if (!setup) return;
        pc_p2_kurage_arena_draw(gfx);
        if (readyFrames == 180 && !captured) { capture("kurage-host-flight.ppm"); captured = true; }
        if (!ownerAlive) { require(captured, "flight capture missing"); capture("kurage-host-teardown.ppm"); std::puts("P2_KURAGE_DISPLAY_PASS ready_frames=240 owner_teardown=pass capture=disabled"); std::puts("PASS KURAGE_RUNTIME"); std::fflush(stdout); std::_Exit(0); }
    }
};
}
int main(int argc, char** argv)
{
    for (int i = 1; i < argc; ++i) {
        if (std::string(argv[i]) == "--receiver-kill") sKillScenario = true;
        if (std::string(argv[i]) == "--receiver-transfer") sTransferScenario = true;
        if (std::string(argv[i]) == "--receiver-stageexit") sStageExitScenario = true;
        if (std::string(argv[i]) == "--receiver-admission") sAdmissionScenario = true;
        if (std::string(argv[i]) == "--receiver-ingestion") sIngestionScenario = true;
        if (std::string(argv[i]) == "--receiver-automatic-binding") sAutomaticBindingScenario = true;
        if (std::string(argv[i]) == "--receiver-onikurage-binding") { sAutomaticBindingScenario = true; sOniKurageScenario = true; }
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady();
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    if (!pc_window_init("P2 Kurage display fixture", 960, 540)) return 3;
    pc_window_center();
    {
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        int width = 0, height = 0, x = 0, y = 0; SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds{0, 0, 0, 0}; SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(window), &bounds);
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
            && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        std::printf("P2_KURAGE_WINDOW size=%dx%d pos=%d,%d display=%dx%d centered=%d\n",
            width, height, x, y, bounds.w, bounds.h, int(centered));
        std::fflush(stdout);
    }
    pc_settings_init(); gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new KurageApp()); return 0;
}
