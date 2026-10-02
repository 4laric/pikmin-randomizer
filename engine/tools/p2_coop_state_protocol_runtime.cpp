// #1148 admitted private fixture under development. No runtime acceptance yet.
// This wrapper retains the production entry point, including ICE bootstrap,
// deterministic initialization, session argv notification and settings adoption.
// The command file feeds only a real SDL virtual controller, never game state.
// Observations/readiness alone do not emit a gameplay PASS.
#include "App.h"
#include <SDL.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <fstream>
#include <sstream>
#include <cstdint>
#include <iterator>
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Camera.h"
#include "GameStat.h"
#include "GoalItem.h"
#include "Collision.h"
#include "PlayerState.h"
#include "ItemMgr.h"
#include "CPlate.h"
#include "AIConstant.h"
// Unchanged legacy inline UI helpers omit unused enum cases. Suppress that
// header's existing switch warnings only; all fixture/global flags stay strict.
#if defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wswitch"
#endif
#include "zen/DrawContainer.h"
#if defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
#include "pc_window.h"
#include "netplay/pc_netplay_launch.h"
#include "netplay/pc_input_log.h"
#include "pc_randomizer.h"
#include "pc_p2_preview.h"
#include "p2_fixture_captain_guard.h"
#include "p2_coop_fixture_input_snapshot.h"
extern std::uint32_t pc_netplay_current_frame(void);

namespace {
// Read-only protected-member access via a correctly typed base member pointer.
// No layout casts, fake derived object, callback, or menu/world write is used.
struct PlateObserver : CPlate {
    static unsigned count(const CPlate& plate) { return plate.*(&PlateObserver::mPlatePikiCount); }
};
struct ContainerObserver : zen::DrawContainer {
    static int stored(const zen::DrawContainer& win) { return win.*(&ContainerObserver::mInitialContainerCount); }
    static int squad(const zen::DrawContainer& win) { return win.*(&ContainerObserver::mInitialSquadCount); }
    static int field(const zen::DrawContainer& win) { return win.*(&ContainerObserver::mSquadTotalCount); }
    static int limit(const zen::DrawContainer& win) { return win.*(&ContainerObserver::mSquadTotalLimit); }
    static int delta(const zen::DrawContainer& win) { return win.*(&ContainerObserver::mTransferDelta); }
    static int displayedDelta(const zen::DrawContainer& win) { return win.*(&ContainerObserver::mDeltaPikiNum); }
};
void fixture_require(bool ok, const char* why) {
    if (ok) return;
    std::printf("COOP_PROTOCOL_FIXTURE_BLOCKED reason=%s\n", why);
    std::fflush(nullptr);
    std::_Exit(1);
}


// Read one immutable whole-command snapshot. The writer uses ReplaceFileW for
// an existing Windows path; a retained reader sees the complete previous file.
bool command_snapshot(const std::string& path, std::string& text) {
    char bytes[256];
    unsigned count = 0;
    const PcCoopSnapshotResult result = pc_coop_fixture_input_snapshot(
        path.c_str(), bytes, sizeof(bytes), &count);
    if (result == PC_COOP_SNAPSHOT_MISSING) return false;
    fixture_require(result != PC_COOP_SNAPSHOT_IO_ERROR, "SDL input snapshot I/O");
    fixture_require(result == PC_COOP_SNAPSHOT_OK, "SDL input command length");
    text.assign(bytes, count);
    return true;
}

class CoopProtocolFixtureApp : public PlugPikiApp {
    SDL_Joystick* mPad = nullptr;
    bool mCaptainInitialized[2] = {false, false};
    bool mForcedDownDelivered = false;
    unsigned mFrames = 0;
    int mLocalRole = 0;
    Uint64 mStarted = 0;
    Uint64 mLastInput = 0;
    std::uint64_t mInputSequence = 0;
    unsigned mButtons = 0;
    int mAxes[4] = {0, 0, 0, 0};
    std::string mInputPath;

    void input() {
        if (!mInputPath.empty()) {
            std::string text;
            if (command_snapshot(mInputPath, text)) {
                fixture_require(text.size() < 256, "SDL input command length");
                std::istringstream stream(text);
                std::string tag, end, extra;
                unsigned long long sequence = 0;
                unsigned buttons = 0;
                int x = 0, y = 0, cx = 0, cy = 0;
                fixture_require(bool(stream >> tag >> sequence >> buttons >> x >> y >> cx >> cy >> end)
                    && tag == "SDL1" && end == "END" && !(stream >> extra), "SDL input grammar");
                fixture_require(sequence > 0 && sequence >= mInputSequence
                    && buttons < (1u << SDL_CONTROLLER_BUTTON_MAX)
                    && x >= -32768 && x <= 32767 && y >= -32768 && y <= 32767
                    && cx >= -32768 && cx <= 32767 && cy >= -32768 && cy <= 32767,
                    "SDL input bounds/order");
                const std::string canonical = "SDL1 " + std::to_string(sequence) + " "
                    + std::to_string(buttons) + " " + std::to_string(x) + " " + std::to_string(y)
                    + " " + std::to_string(cx) + " " + std::to_string(cy) + " END\n";
                fixture_require(text == canonical, "SDL input canonical ASCII/LF");
                if (sequence > mInputSequence) {
                    mInputSequence = sequence; mButtons = buttons;
                    mAxes[0] = x; mAxes[1] = y; mAxes[2] = cx; mAxes[3] = cy;
                    mLastInput = SDL_GetTicks64();
                }
            }
        }
        // A stopped orchestrator cannot leave a held movement/throw command.
        if (!mLastInput || SDL_GetTicks64() - mLastInput > 500) {
            mButtons = 0;
            for (int& axis : mAxes) axis = 0;
        }
        pc_window_input_assign(mLocalRole, PC_INPUT_DEV_GAMEPAD, SDL_JoystickInstanceID(mPad));
        pc_window_input_assign(1 - mLocalRole, PC_INPUT_DEV_NONE, -1);
        for (int b = 0; b < SDL_CONTROLLER_BUTTON_MAX; ++b)
            SDL_JoystickSetVirtualButton(mPad, b, (mButtons >> b) & 1u);
        SDL_JoystickSetVirtualAxis(mPad, SDL_CONTROLLER_AXIS_LEFTX, Sint16(mAxes[0]));
        SDL_JoystickSetVirtualAxis(mPad, SDL_CONTROLLER_AXIS_LEFTY, Sint16(mAxes[1]));
        SDL_JoystickSetVirtualAxis(mPad, SDL_CONTROLLER_AXIS_RIGHTX, Sint16(mAxes[2]));
        SDL_JoystickSetVirtualAxis(mPad, SDL_CONTROLLER_AXIS_RIGHTY, Sint16(mAxes[3]));
        SDL_JoystickUpdate();
    }
public:
    CoopProtocolFixtureApp() : PlugPikiApp(), mStarted(SDL_GetTicks64()) {
        const PcNetplayLaunch& launch = pc_netplay_launch_setup();
        fixture_require(launch.active && launch.externalState, "requires actual ICE external-state launcher");
        pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
        pc_window_set_window_size(960, 540);
        pc_window_center();
        SDL_Window* window = SDL_GL_GetCurrentWindow();
        fixture_require(window != nullptr, "actual SDL GL window");
        int width = 0, height = 0, x = 0, y = 0;
        SDL_GetWindowSize(window, &width, &height);
        SDL_GetWindowPosition(window, &x, &y);
        SDL_Rect bounds;
        const int display = SDL_GetWindowDisplayIndex(window);
        fixture_require(display >= 0 && SDL_GetDisplayBounds(display, &bounds) == 0, "actual display bounds");
        const bool centered = std::abs(x - (bounds.x + (bounds.w - width) / 2)) <= 2
                           && std::abs(y - (bounds.y + (bounds.h - height) / 2)) <= 2;
        const bool windowed = !(SDL_GetWindowFlags(window) & SDL_WINDOW_FULLSCREEN);
        fixture_require(width == 960 && height == 540 && centered && windowed, "actual SDL window geometry");
        std::printf("COOP_PROTOCOL_FIXTURE_WINDOW measured=1 width=%d height=%d centered=%d windowed=%d x=%d y=%d display=%d bounds=%d,%d,%d,%d hidden=%d\n",
                    width, height, int(centered), int(windowed), x, y, display,
                    bounds.x, bounds.y, bounds.w, bounds.h, int(bool(SDL_GetWindowFlags(window) & SDL_WINDOW_HIDDEN)));
        mLocalRole = launch.isHost ? 0 : 1;
        if (const char* path = std::getenv("PIKMIN_COOP_FIXTURE_INPUT")) mInputPath = path;
        // Production post-settings/ICE setup has already completed. This device
        // feeds the local SDL polling path; no source-input script is used.
        const int device = SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,
            SDL_CONTROLLER_AXIS_MAX, SDL_CONTROLLER_BUTTON_MAX, 0);
        fixture_require(device >= 0, "SDL virtual controller creation");
        char guid[64];
        SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device), guid, sizeof(guid));
        const std::string mapping = std::string(guid) +
            ",Protocol acceptance local pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,"
            "start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,"
            "dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,"
            "rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
        fixture_require(SDL_GameControllerAddMapping(mapping.c_str()) >= 0, "SDL mapping");
        mPad = SDL_JoystickOpen(device);
        fixture_require(mPad != nullptr, "SDL virtual controller open");
        pc_window_input_assign(mLocalRole, PC_INPUT_DEV_GAMEPAD, SDL_JoystickInstanceID(mPad));
        pc_window_input_assign(1 - mLocalRole, PC_INPUT_DEV_NONE, -1);
        std::printf("COOP_PROTOCOL_FIXTURE_INPUT role=%d actual_SDL=1 source_script=0 command_file=%s\n",
                    mLocalRole, mInputPath.c_str());
    }

    int idle() override {
        // Native simulation always runs first. Guard precedes readiness,
        // pause/movie and manager early returns. Check both initialized captains.
        const int result = PlugPikiApp::idle();
        ++mFrames;
        for (int i = 0; i < 2; ++i) {
            Navi* n = naviMgr ? naviMgr->getNavi(i) : nullptr;
            if (n && n->getCurrState()) mCaptainInitialized[i] = true;
            if (!mCaptainInitialized[i]) continue;
            // Explicit guard-negative instrumentation only. Positive launch
            // scrubs this variable. The real initialized engine captain is
            // made down and immediately evaluated by the ordinary guard.
            const char* force = std::getenv("PIKMIN_COOP_FIXTURE_FORCE_DOWN_CAPTAIN");
            if (n && n->getCurrState() && force && !mForcedDownDelivered && force[0] == char('0' + i) && force[1] == '\0') {
                n->mHealth = 0.f;
                mForcedDownDelivered = true;
                std::printf("COOP_PROTOCOL_GUARD_NEGATIVE actual_initialized_captain=%d frame=%u\n", i, mFrames);
            }
            const bool missing = !naviMgr || !n || !n->getCurrState();
            const bool dead = missing || naviMgr->isNaviDead(n)
                || n->getCurrState()->getID() == NAVISTATE_Dead;
            p2_fixture_require_captain(GameStat::orimaDead != 0, dead,
                n ? n->mHealth : 0.f, int(mFrames));
        }
        fixture_require(SDL_GetTicks64() - mStarted < 60000, "60 second local ceiling");
        fixture_require(mFrames < 5000, "frame ceiling");
        input();
        // UI and world counts are sampled on every authoritative engine frame,
        // including closing animation. Reading never refreshes their counters.
        for (int captain = 0; captain < 2; ++captain) {
            Navi* n = naviMgr ? naviMgr->getNavi(captain) : nullptr;
            zen::DrawContainer* menu = captain == 1 && containerWindow2 ? containerWindow2 : containerWindow;
            if (!n || !n->getCurrState() || !menu) continue;
            GoalItem* onion = n->mGoalItem;
            if (n->getCurrState()->getID() != NAVISTATE_Container && menu->getStatus() == zen::DrawContainer::STATE_Wait) continue;
            std::printf("COOP_PROTOCOL_ONION sim_frame=%u role=%d captain=%d state=%d menu=%d "
                "stored=%d available=%d pending_onion=%d pending_all=%d live=%d cap=%d "
                "display_stored=%d display_squad=%d menu_stored=%d menu_squad=%d menu_field=%d menu_limit=%d "
                "delta=%d displayed_delta=%d formation=%u onion_color=%d onion_xyz=%.3f,%.3f,%.3f\n",
                pc_netplay_current_frame(), mLocalRole, captain, n->getCurrState()->getID(), int(menu->getStatus()),
                onion ? onion->getTotalStorePikis() : -1,
                onion ? onion->getTotalStorePikis() - onion->mPikisToExit : -1,
                onion ? onion->mPikisToExit : -1, itemMgr ? itemMgr->getContainerExitCount() : -1,
                int(GameStat::mapPikis), int(AICONST.mMaxPikisOnField()),
                menu->getContainerPikiDisp(), menu->getMyPikiDisp(), ContainerObserver::stored(*menu),
                ContainerObserver::squad(*menu), ContainerObserver::field(*menu), ContainerObserver::limit(*menu),
                ContainerObserver::delta(*menu), ContainerObserver::displayedDelta(*menu),
                n->mPlateMgr ? PlateObserver::count(*n->mPlateMgr) : 0u,
                onion ? int(onion->mOnionColour) : -1,
                onion ? onion->mSRT.t.x : 0.f, onion ? onion->mSRT.t.y : 0.f, onion ? onion->mSRT.t.z : 0.f);
            std::fflush(nullptr);
        }
        if (mFrames % 15 == 0) {
            // Read-only approach facts from the actual owner-filtered GoalItem,
            // including its real 'cont' sphere. No lookup assigns mGoalItem,
            // updates GameStat, enters UI, or changes collision/stock/world.
            for (int captain = 0; captain < 2; ++captain) {
                Navi* n = naviMgr ? naviMgr->getNavi(captain) : nullptr;
                if (!n || !n->getCurrState()) continue;
                const Vector3f naviCentre = n->getCentre();
                float yawSin = 0.f, yawCos = 1.f;
                const bool yawValid = pc_netplay_control_yaw(n->mNaviID, &yawSin, &yawCos);
                for (int color = 0; color < 3; ++color) {
                    GoalItem* goal = itemMgr ? itemMgr->pcGetContainer(color, n->mNaviID) : nullptr;
                    const bool pod = goal && pc_p2_preview_is_pod(goal);
                    CollPart* cont = goal && !pod && goal->mCollInfo && goal->mCollInfo->hasInfo()
                        ? goal->mCollInfo->getSphere('cont') : nullptr;
                    std::printf("COOP_PROTOCOL_GOAL sim_frame=%u role=%d captain=%d color=%d present=%d pod=%d cont_present=%d ordinary_candidate=%d "
                        "navi_center=%.3f,%.3f,%.3f yaw_valid=%d yaw_sin=%.7f yaw_cos=%.7f goal_xyz=%.3f,%.3f,%.3f cont_xyz=%.3f,%.3f,%.3f radius=%.3f navi_size=%.3f stored=%d "
                        "pending_onion=%d radar_unlocked=%d\n",
                        pc_netplay_current_frame(), mLocalRole, captain, color, int(goal != nullptr), int(pod), int(cont != nullptr), int(goal && !pod && cont),
                        naviCentre.x, naviCentre.y, naviCentre.z, int(yawValid), yawSin, yawCos,
                        goal ? goal->mSRT.t.x : 0.f, goal ? goal->mSRT.t.y : 0.f, goal ? goal->mSRT.t.z : 0.f,
                        cont ? cont->mCentre.x : 0.f, cont ? cont->mCentre.y : 0.f, cont ? cont->mCentre.z : 0.f,
                        cont ? cont->mRadius : 0.f, n->getSize(), goal ? goal->getTotalStorePikis() : -1,
                        goal ? goal->mPikisToExit : -1, playerState ? int(playerState->hasRadar()) : -1);
                }
            }
            int alive = 0;
            if (pikiMgr) { Iterator it(pikiMgr); CI_LOOP(it) { if (static_cast<Piki*>(*it)->isAlive()) ++alive; } }
            for (int captain = 0; captain < 2; ++captain) {
            Navi* p1 = naviMgr ? naviMgr->getNavi(captain) : nullptr;
            if (p1 && p1->getCurrState() && p1->controlCamera()) {
                const Vector3f& axis = p1->controlCamera()->mViewXAxis;
                std::printf("COOP_PROTOCOL_OBSERVE frame=%u sim_frame=%u role=%d captain=%d alive=%d state=%d hp=%.3f followers=%d "
                            "xyz=%.3f,%.3f,%.3f cursor=%.3f,%.3f,%.3f camera=%.5f,%.5f,%.5f input_sequence=%llu\n",
                            mFrames, pc_netplay_current_frame(), mLocalRole, captain, alive, p1->getCurrState()->getID(), p1->mHealth,
                            p1->getPlatePikis(), p1->mSRT.t.x, p1->mSRT.t.y, p1->mSRT.t.z,
                            p1->mCursorWorldPos.x, p1->mCursorWorldPos.y, p1->mCursorWorldPos.z,
                            axis.x, axis.y, axis.z, static_cast<unsigned long long>(mInputSequence));
                std::fflush(nullptr);
            }
            }
            pc_randstate::PcRandState inventory;
            if (pc_randomizer_get_net_state(&inventory)) {
                std::uint8_t wire[pc_randstate::kStateBytes];
                fixture_require(pc_randstate::encode(inventory, wire) == sizeof(wire), "read-only inventory encoding");
                std::printf("COOP_PROTOCOL_INVENTORY sim_frame=%u role=%d hash=%016llx wire=",
                    pc_netplay_current_frame(), mLocalRole,
                    static_cast<unsigned long long>(pc_randomizer_hash()));
                for (std::uint8_t byte : wire) std::printf("%02x", unsigned(byte));
                std::printf("\n");
            }
            if (pikiMgr) {
                int index = 0; Iterator it(pikiMgr);
                CI_LOOP(it) {
                    Piki* p = static_cast<Piki*>(*it);
                    int owner = -1;
                    if (naviMgr && p->mNavi == naviMgr->getNavi(0)) owner = 0;
                    else if (naviMgr && p->mNavi == naviMgr->getNavi(1)) owner = 1;
                    std::printf("COOP_PROTOCOL_PIKI sim_frame=%u role=%d index=%d alive=%d color=%u maturity=%d owner=%d xyz=%.3f,%.3f,%.3f\n",
                        pc_netplay_current_frame(), mLocalRole, index++, int(p->isAlive()),
                        unsigned(p->mColor), p->mHappa, owner, p->mSRT.t.x, p->mSRT.t.y, p->mSRT.t.z);
                }
            }
            std::fflush(nullptr);
        }
        return result;
    }
};
}

// App.h was included above, so this substitution only changes the production
// new-app expression. There is one main and one copy of production GPU exports.
// The harness sets window/audio/background environment before process startup.
#define PlugPikiApp CoopProtocolFixtureApp
#include "../pc_port/pc_main.cpp"
#undef PlugPikiApp
