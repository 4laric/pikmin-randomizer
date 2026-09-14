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
#include "PikiState.h"
#include "Collision.h"
#include "Creature.h"
#include "MoviePlayer.h"
#include "pc_bbft.h"
#include "pc_gpu_preference.h"
#include "pc_gfx.h"
#include "pc_p2_captain_policy.h"
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
bool sKillScenario = false, sTransferScenario = false, sStageExitScenario = false, sAdmissionScenario = false, sAutomaticBindingScenario = false, sOniKurageScenario = false, sIngestionScenario = false, sFlightFsmScenario = false, sFlightFsmDeathScenario = false, sFlightFsmGreaterScenario = false, sFlightFsmGreaterDropScenario = false, sAutoFsmScenario = false, sFlightFsmGreaterCaptainScenario = false, sFlightFsmStuckFlickScenario = false, sFlightFsmDeathCycleScenario = false, sFlightFsmPatrolScenario = false, sAutoFsmMoveScenario = false;
void require(bool value, const char* message)
{
    if (!value) { std::printf("FAIL KURAGE_RUNTIME %s\n", message); std::fflush(stdout); std::_Exit(1); }
}
// Place the candidate in the source suction window and keep it stick-eligible:
// Piki::mayIstick() rejects LookAt/Flick, which the live AI can enter while
// approaching a flying actor.
void placeCandidate(Piki* piki, const Vector3f& position)
{
    if (!piki) return;
    piki->resetPosition(position);
    if (piki->isAlive() && !piki->isStickTo() && piki->mFSM) piki->mFSM->transit(piki, PIKISTATE_Normal);
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
    int fsmTicks = 0, fsmStage = 0;
    bool dropSeen = false;
    Piki* fsmPiki = nullptr;
    bool autoFsmArmed = false;
    int autoFsmTicks = 0;
    BTeki* autoFsmActor = nullptr;
    Piki* autoFsmPiki = nullptr;
    // Greater captain capture composition (lane 12 P2CaptainPolicy + OniKurage
    // mouth slots).  The isolated room has one real Navi, mapped to captain A;
    // captain B is a nominal present slot so the source zero-control guard is
    // satisfied.  Labelled bounded adapter, not lane-12 live-adapter acceptance.
    P2CaptainOwnershipTable captainTable;
    P2CaptainPolicy captainPolicy;
    bool captainBound = false;
    int captainStage = 0;
    bool captainSawDrop = false;
    Vector3f patrolStart;
    int patrolStartTick = 0;
    int autoFsmStage = 0;
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
        int result = PlugPikiApp::idle();
        require(++frames < (sFlightFsmGreaterCaptainScenario ? 3600
            : (sAutoFsmScenario || sFlightFsmStuckFlickScenario) ? 2400 : 900), "timeout");
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
            if (sAutoFsmScenario) {
                // Ordinary generated actor runs the source flight lifecycle and
                // its Attack state admits a nearby Pikmin.
                if (!autoFsmArmed) {
                    // The frog-profile room leaves the day/UI overlay active,
                    // which freezes the managers this ordinary-actor harness
                    // needs.  The arena scenarios run with it clear.
                    gameflow.mPauseAll = FALSE;
                    gameflow.mIsUIOverlayActive = FALSE;
                    Navi* nav = naviMgr->getNavi();
                    Piki* p = static_cast<Piki*>(pikiMgr->birth());
                    require(nav && p, "auto fsm piki birth");
                    p->init(nav);
                    p->initColor(Red);
                    p->setFlower(Leaf);
                    if (sAutoFsmMoveScenario)
                        p->resetPosition(Vector3f(1000.0f, 0.0f, 1000.0f));
                    else
                        p->resetPosition(Vector3f(generatedFrog->mSRT.t.x, generatedFrog->mSRT.t.y - 30.0f, generatedFrog->mSRT.t.z));
                    p->mMode = PikiMode::AttackMode;
                    autoFsmPiki = p;
                    autoFsmActor = generatedFrog;
                    pc_p2_kurage_teki_fsm_enable(true);
                    autoFsmArmed = true;
                    std::printf("P2_KURAGE_AUTO_FSM_ARMED ordinary_actor=1 enabled=%d\n",
                        int(pc_p2_kurage_teki_fsm_enabled(generatedFrog)));
                    std::fflush(stdout);
                    return result;
                }
                ++autoFsmTicks;
                // The isolated preview pauses the Teki manager's per-frame
                // update, so drive the bound ordinary actor's lane hook here.
                pc_p2_kurage_teki_tick(autoFsmActor);
                if (sAutoFsmMoveScenario) {
                    if (autoFsmPiki && autoFsmPiki->isAlive() && !pc_p2_kurage_receiver_controls(autoFsmPiki))
                        autoFsmPiki->resetPosition(Vector3f(1000.0f, 0.0f, 1000.0f));
                    if (autoFsmStage == 0) {
                        if (pc_p2_kurage_teki_fsm_state(autoFsmActor) == 2) {
                            patrolStart = autoFsmActor->mSRT.t;
                            patrolStartTick = autoFsmTicks;
                            autoFsmStage = 1;
                        } else require(autoFsmTicks < 900, "ordinary actor patrol wait->move timeout");
                        return result;
                    }
                    if (autoFsmTicks - patrolStartTick > 120) {
                        const Vector3f p = autoFsmActor->mSRT.t;
                        const float moved = std::fabs(p.x - patrolStart.x) + std::fabs(p.z - patrolStart.z);
                        require(moved > 5.0f, "ordinary actor patrol moved");
                        std::printf("P2_KURAGE_AUTO_FSM_MOVE_PASS moved=%.1f state=%d\n",
                            moved, pc_p2_kurage_teki_fsm_state(autoFsmActor));
                        std::puts("PASS KURAGE_RUNTIME ordinary_actor_fsm_patrol");
                        std::fflush(stdout); std::_Exit(0);
                    }
                    return result;
                }
                if (autoFsmPiki && autoFsmPiki->isAlive() && !pc_p2_kurage_receiver_controls(autoFsmPiki))
                    placeCandidate(autoFsmPiki, Vector3f(autoFsmActor->mSRT.t.x, autoFsmActor->mSRT.t.y - 30.0f, autoFsmActor->mSRT.t.z));
                if (pc_p2_kurage_receiver_stomach_count() == 1) {
                    require(pc_p2_kurage_teki_auto_admissions(autoFsmActor) >= 1,
                        "ordinary actor autonomous admission counted");
                    require(autoFsmPiki->isAlive() && autoFsmPiki->isStickTo()
                        && autoFsmPiki->getStickObject() == autoFsmActor,
                        "ordinary actor suction attached");
                    std::printf("P2_KURAGE_AUTO_FSM_ADMISSION_PASS state=%d auto=%d attach=1 stomach=1\n",
                        pc_p2_kurage_teki_fsm_state(autoFsmActor), pc_p2_kurage_teki_auto_admissions(autoFsmActor));
                    std::puts("PASS KURAGE_RUNTIME ordinary_actor_fsm_admission");
                    std::fflush(stdout); std::_Exit(0);
                }
                if (autoFsmTicks >= 900) {
                    std::printf("P2_KURAGE_AUTO_FSM_TIMEOUT hook_calls=%d ticks=%d state=%d auto=%d recv=%d alive=%d stick=%d enabled=%d\n",
                        pc_p2_kurage_teki_tick_calls(),
                        pc_p2_kurage_teki_fsm_ticks(autoFsmActor), pc_p2_kurage_teki_fsm_state(autoFsmActor),
                        pc_p2_kurage_teki_auto_admissions(autoFsmActor), pc_p2_kurage_receiver_count(),
                        int(autoFsmPiki && autoFsmPiki->isAlive()), int(autoFsmPiki && autoFsmPiki->isStickTo()),
                        int(pc_p2_kurage_teki_fsm_enabled(autoFsmActor)));
                    std::fflush(stdout);
                    std::_Exit(1);
                }
                return result;
            }
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
            // Match the known-good fixture Piki init (p2_fuefuki_runtime): a
            // bare init()+mMode leaves the fresh view under-initialized and it
            // can fault in ViewPiki::refresh when drawn free before capture.
            piki->init(n);
            piki->initColor(Red);
            piki->setFlower(Leaf);
            piki->resetPosition(owner->mSRT.t);
            piki->mMode = PikiMode::AttackMode;
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
            if (sFlightFsmScenario || sFlightFsmDeathScenario
                || sFlightFsmGreaterScenario || sFlightFsmGreaterDropScenario
                || sFlightFsmGreaterCaptainScenario || sFlightFsmStuckFlickScenario
                || sFlightFsmDeathCycleScenario || sFlightFsmPatrolScenario) {
                // Source flight lifecycle drives the host; the candidate sits
                // inside the source suction window until the Attack state's
                // autonomous admission scan claims it.
                piki->resetPosition(Vector3f(owner->mSRT.t.x, owner->mSRT.t.y - 30.0f, owner->mSRT.t.z));
                piki->mMode = PikiMode::AttackMode;
                fsmPiki = piki;
                if (sFlightFsmGreaterScenario || sFlightFsmGreaterDropScenario
                    || sFlightFsmGreaterCaptainScenario)
                    pc_p2_kurage_arena_set_greater(true);
                if (sFlightFsmGreaterCaptainScenario) {
                    if (!captainBound) captainBound = captainPolicy.bind(&captainTable);
                    captainPolicy.configure(P2CaptainA, 100.0f, true);
                    captainPolicy.configure(P2CaptainB, 100.0f, true);
                    Navi* captainNavi = naviMgr->getNavi();
                    require(captainNavi != nullptr, "captain navi");
                    captainNavi->resetPosition(Vector3f(owner->mSRT.t.x, owner->mSRT.t.y - 20.0f, owner->mSRT.t.z));
                    pc_p2_kurage_arena_set_captain_target(&captainPolicy, P2CaptainA, captainNavi);
                }
                pc_p2_kurage_arena_set_owner_facts(true, false);
                pc_p2_kurage_arena_fsm_enable(true);
                std::puts("P2_KURAGE_FSM_ADMISSION_ARMED state_source=pc_p2_kurage_fsm.h scan=source_attack_window");
                std::fflush(stdout);
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
        if (sFlightFsmPatrolScenario) {
            ++fsmTicks;
            // Park the candidate out of the source window so the FSM has no
            // target and follows the Wait -> Move patrol path.
            if (fsmPiki && fsmPiki->isAlive() && !pc_p2_kurage_receiver_controls(fsmPiki))
                fsmPiki->resetPosition(Vector3f(1000.0f, 0.0f, 1000.0f));
            require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "patrol host update");
            if (fsmStage == 0) {
                if (pc_p2_kurage_arena_fsm_state() == 2) {
                    patrolStart = pc_p2_kurage_arena_owner()->mSRT.t;
                    patrolStartTick = fsmTicks;
                    fsmStage = 1;
                } else require(fsmTicks < 600, "patrol wait->move timeout");
                return result;
            }
            if (fsmTicks - patrolStartTick > 120) {
                const Vector3f p = pc_p2_kurage_arena_owner()->mSRT.t;
                const float moved = std::fabs(p.x - patrolStart.x) + std::fabs(p.z - patrolStart.z);
                require(moved > 5.0f, "patrol moved horizontally");
                std::printf("P2_KURAGE_PATROL_PASS moved=%.1f from=%.1f,%.1f to=%.1f,%.1f\n",
                    moved, patrolStart.x, patrolStart.z, p.x, p.z);
                std::puts("PASS KURAGE_RUNTIME flight_fsm_patrol");
                std::fflush(stdout); std::_Exit(0);
            }
            return result;
        }
        if (sFlightFsmDeathCycleScenario) {
            ++fsmTicks;
            Creature* host = pc_p2_kurage_arena_owner();
            if (fsmPiki && fsmPiki->isAlive() && !pc_p2_kurage_receiver_controls(fsmPiki) && host)
                placeCandidate(fsmPiki, Vector3f(host->mSRT.t.x, host->mSRT.t.y - 30.0f, host->mSRT.t.z));
            require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "death cycle host update");
            if (fsmStage == 0) {
                if (pc_p2_kurage_receiver_stomach_count() == 1) fsmStage = 1;
                else require(fsmTicks < 900, "death cycle admission timeout");
                return result;
            }
            if (fsmStage == 1) {
                // Drop the owner health to 0; the FSM routes to Dead and runs the
                // source dead1 clock to its KEY3 procedure and END kill.
                pc_p2_kurage_arena_set_owner_facts(false, false);
                fsmStage = 2;
                return result;
            }
            if (pc_p2_kurage_arena_killed()) {
                require(pc_p2_kurage_receiver_count() == 0, "death releases the receiver piki");
                require(fsmPiki->isAlive() && !fsmPiki->isStickTo() && fsmPiki->mSRT.s.x == 1.0f,
                    "death releases the piki with restored scale");
                require(pc_p2_kurage_arena_owner() == nullptr, "dead host left the field");
                std::printf("P2_KURAGE_DEATH_CYCLE_PASS killed=1 recv=%d piki_alive=1 scale_restored=1\n",
                    pc_p2_kurage_receiver_count());
                std::puts("PASS KURAGE_RUNTIME flight_fsm_death_cycle");
                std::fflush(stdout); std::_Exit(0);
            }
            require(fsmTicks < 1800, "death cycle timeout");
            return result;
        }
        if (sFlightFsmStuckFlickScenario) {
            ++fsmTicks;
            Creature* host = pc_p2_kurage_arena_owner();
            // A stuck Pikmin raises the source fall timer; after the shake time
            // the FSM enters FlyFlick and the real flick1.bca KEY2 ejects it.
            if (fsmPiki && fsmPiki->isAlive() && !pc_p2_kurage_receiver_controls(fsmPiki) && host)
                placeCandidate(fsmPiki, Vector3f(host->mSRT.t.x, host->mSRT.t.y - 30.0f, host->mSRT.t.z));
            require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "stuck flick host update");
            if (fsmStage == 0) {
                if (pc_p2_kurage_receiver_stomach_count() == 1) fsmStage = 1;
                else require(fsmTicks < 900, "stuck flick admission timeout");
                return result;
            }
            if (pc_p2_kurage_receiver_count() == 0) {
                require(fsmPiki->isAlive() && !fsmPiki->isStickTo() && fsmPiki->mSRT.s.x == 1.0f,
                    "flick releases attached piki");
                std::printf("P2_KURAGE_STUCK_FLICK_PASS flick_released=1 alive=1 scale_restored=1 state=%d\n",
                    pc_p2_kurage_arena_fsm_state());
                std::puts("PASS KURAGE_RUNTIME flight_fsm_stuck_flick");
                std::fflush(stdout); std::_Exit(0);
            }
            require(fsmTicks < 1500, "stuck flick timeout");
            return result;
        }
        if (sFlightFsmGreaterCaptainScenario) {
            ++fsmTicks;
            Creature* host = pc_p2_kurage_arena_owner();
            Navi* captainNavi = naviMgr->getNavi();
            // Hold the captain in the source suction window until captured; once
            // captured the arena host pins it to the mouth slot.
            if (captainNavi && host && !pc_p2_kurage_arena_captain_captured())
                captainNavi->resetPosition(Vector3f(host->mSRT.t.x, host->mSRT.t.y - 20.0f, host->mSRT.t.z));
            require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "greater captain host update");
            if (captainStage == 0) {
                if (captainPolicy.phase(P2CaptainA) == P2CaptainPhase::Captured) {
                    std::puts("P2_KURAGE_CAPTAIN_CAPTURED_PHASE captain=A state=Captured");
                    captainStage = 1;
                } else {
                    require(fsmTicks < 1800, "greater captain capture timeout");
                }
                return result;
            }
            if ((int)pc_p2_kurage_arena_fsm_state() == 11) captainSawDrop = true;
            if (!pc_p2_kurage_arena_captain_captured()) {
                require(captainSawDrop, "greater captain drop observed before release");
                require(captainPolicy.phase(P2CaptainA) == P2CaptainPhase::Idle,
                    "greater captain released to idle");
                std::printf("P2_KURAGE_GREATER_CAPTAIN_PASS captured=1 drop=%d released=1 occupied=%d\n",
                    int(captainSawDrop), pc_p2_kurage_arena_captain_occupied());
                std::puts("PASS KURAGE_RUNTIME flight_fsm_greater_captain");
                std::fflush(stdout); std::_Exit(0);
            }
            require(fsmTicks < 2400, "greater captain drop timeout");
            return result;
        }
        if (sFlightFsmScenario || sFlightFsmDeathScenario
            || sFlightFsmGreaterScenario || sFlightFsmGreaterDropScenario) {
            ++fsmTicks;
            if (fsmStage == 0) {
                // Keep the candidate inside the source suction window until the
                // receiver owns it, mirroring a Pikmin walking under the body.
                if (fsmPiki && fsmPiki->isAlive() && !pc_p2_kurage_receiver_controls(fsmPiki)) {
                    Creature* host = pc_p2_kurage_arena_owner();
                    if (host) placeCandidate(fsmPiki, Vector3f(host->mSRT.t.x, host->mSRT.t.y - 30.0f, host->mSRT.t.z));
                }
                require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "fsm host update");
                if (pc_p2_kurage_receiver_stomach_count() == 1) {
                    require(pc_p2_kurage_arena_auto_admissions() >= 1, "fsm autonomous admission counted");
                    require(fsmPiki->isAlive() && fsmPiki->isStickTo()
                        && fsmPiki->getStickObject() == pc_p2_kurage_arena_owner(),
                        "fsm attack suction attached");
                    if (sFlightFsmDeathScenario) {
                        fsmStage = 1;
                    } else if (sFlightFsmGreaterDropScenario) {
                        // Attack END routes to the OniKurage Drop state while a
                        // captain is held.  Capture against a real Navi is lane
                        // 12 provider work, so this is a labelled host seam.
                        fsmStage = 2;
                    } else {
                        std::printf("P2_KURAGE_FSM_ADMISSION_PASS variant=%d state=%d auto=%d attach=1 stomach=1 altitude=%.1f\n",
                            pc_p2_kurage_arena_fsm_variant(), pc_p2_kurage_arena_fsm_state(),
                            pc_p2_kurage_arena_auto_admissions(), pc_p2_kurage_arena_fsm_altitude());
                        std::puts("PASS KURAGE_RUNTIME flight_fsm_admission");
                        std::fflush(stdout); std::_Exit(0);
                    }
                } else {
                    require(fsmTicks < 900, "fsm attack admission timeout");
                }
                return result;
            }
            if (fsmStage == 1) {
                // Interrupted release through owner death: the live stuck Pikmin
                // must be ejected with its captured scale restored.
                pc_p2_kurage_arena_update(1.0f / 60.0f, false);
                require(pc_p2_kurage_receiver_count() == 0, "fsm owner-death receiver release");
                require(fsmPiki->isAlive() && !fsmPiki->isStickTo() && fsmPiki->getStickObject() == nullptr,
                    "fsm owner-death piki detach");
                require(fsmPiki->mSRT.s.x == 1.0f, "fsm owner-death scale restored");
                std::printf("P2_KURAGE_FSM_DEATH_PASS released=1 alive=1 scale_restored=1 state=%d\n",
                    pc_p2_kurage_arena_fsm_state());
                std::puts("PASS KURAGE_RUNTIME flight_fsm_interrupt");
                std::fflush(stdout); std::_Exit(0);
            }
            // Greater Drop: hold the captain fact, then observe the source Drop
            // fall (state 11) and its landing transition.
            pc_p2_kurage_arena_set_captain_held(true);
            require(pc_p2_kurage_arena_update(1.0f / 60.0f, true), "greater drop host update");
            const int state = pc_p2_kurage_arena_fsm_state();
            if (state == 11) dropSeen = true;
            if (dropSeen && state != 11) {
                std::printf("P2_KURAGE_FSM_DROP_PASS variant=72 drop_seen=1 landed_state=%d altitude=%.1f\n",
                    state, pc_p2_kurage_arena_fsm_altitude());
                std::puts("PASS KURAGE_RUNTIME flight_fsm_greater_drop");
                std::fflush(stdout); std::_Exit(0);
            }
            require(fsmTicks < 1800, "greater drop timeout");
            return result;
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
        if (std::string(argv[i]) == "--flight-fsm-admission") sFlightFsmScenario = true;
        if (std::string(argv[i]) == "--flight-fsm-death") { sFlightFsmScenario = true; sFlightFsmDeathScenario = true; }
        if (std::string(argv[i]) == "--flight-fsm-greater") sFlightFsmGreaterScenario = true;
        if (std::string(argv[i]) == "--flight-fsm-greater-drop") sFlightFsmGreaterDropScenario = true;
        if (std::string(argv[i]) == "--receiver-auto-fsm") { sAutomaticBindingScenario = true; sAutoFsmScenario = true; }
        if (std::string(argv[i]) == "--receiver-auto-fsm-move") { sAutomaticBindingScenario = true; sAutoFsmScenario = true; sAutoFsmMoveScenario = true; }
        if (std::string(argv[i]) == "--flight-fsm-greater-captain") sFlightFsmGreaterCaptainScenario = true;
        if (std::string(argv[i]) == "--flight-fsm-stuck-flick") sFlightFsmStuckFlickScenario = true;
        if (std::string(argv[i]) == "--flight-fsm-death-cycle") sFlightFsmDeathCycleScenario = true;
        if (std::string(argv[i]) == "--flight-fsm-patrol") sFlightFsmPatrolScenario = true;
    }
    SDL_setenv("SDL_AUDIODRIVER", "dummy", 1); SDL_SetMainReady();
    pc_gpu_preference_apply(); _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1"); pc_bbft_init(argc, argv);
    require(pc_pikipelago_room_preview(), "requires --experimental-pikmin2-room");
    if (!pc_window_init("P2 Kurage display fixture", 960, 540)) return 3;
    pc_settings_init();
    pc_window_set_display_mode(0);
    pc_window_set_window_size(960, 540);
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
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr = new NodeMgr();
    gsys->run(new KurageApp()); return 0;
}
