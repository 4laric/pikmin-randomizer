#include "pc_bbft.h"
#include "pc_randomizer.h"
#include <cstdlib>
#include <cstring>
#include <cstdio>
#include <chrono>
#include <string>
#ifdef _WIN32
#include "bbft/bbft_transport.h"
#endif
static bool enabled = false;
static int challengeLevel = -1;
static bool p2RoomPreview = false;
bool pc_pikipelago_room_preview() { return p2RoomPreview; }
int pc_pikipelago_challenge_level() { return challengeLevel; }
static bool testBackground = false;
void pc_bbft_milestone(const char* text) {
    if (!enabled) return;
    std::printf("[BBFT] %s\n", text);
#ifdef _WIN32
    bbft_logf("%s", text);
#endif
}
const char* pc_bbft_save_root() {
    if (pc_randomizer_enabled()) return pc_randomizer_save_root();
    if (!enabled && challengeLevel < 0) return "save";
    // A quick-boot run must never reuse a user's named memory-card slot.
    static const std::string session = "save/bbft_sessions/" + std::to_string(
        std::chrono::system_clock::now().time_since_epoch().count());
    return session.c_str();
}
static bool startDown = false, skipRequested = false;
void pc_bbft_start_button(bool down) {
    skipRequested = pc_bbft_accept_input() && down && !startDown;
    startDown = down;
}
bool pc_bbft_take_skip() {
    bool result = skipRequested;
    skipRequested = false;
    return result;
}
void pc_bbft_init(int argc, char** argv) {
    for (int i=1; i<argc; ++i) {
        if (!std::strcmp(argv[i], "--experimental-pikmin2-room")) {
            if (challengeLevel >= 0) { std::fprintf(stderr,"Only one experimental preview may be selected\n"); std::exit(2); }
            p2RoomPreview = true; challengeLevel = 0;
        } else if (!std::strcmp(argv[i], "--experimental-challenge-level")) {
            if (++i>=argc || challengeLevel>=0 || std::strlen(argv[i])!=1 || argv[i][0]<'0' || argv[i][0]>'4') {
                std::fprintf(stderr,"--experimental-challenge-level requires one ID 0-4\n"); std::exit(2);
            }
            challengeLevel=argv[i][0]-'0';
        }
    }
    if (challengeLevel>=0) {
        for(int i=1;i<argc;++i) if(!std::strcmp(argv[i],"--randomizer-seed") || !std::strcmp(argv[i],"--bbft-port")) {
            std::fprintf(stderr,"Challenge layout preview cannot use AP or BBFT sessions\n"); std::exit(2);
        }
        return;
    }
    if (pc_randomizer_init(argc, argv)) { enabled = true; return; }
#ifdef _WIN32
    const char* port = std::getenv("BBFT_PORT");
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--bbft-port") == 0) {
            if (++i >= argc) { std::fprintf(stderr, "--bbft-port needs a port\n"); std::exit(2); }
            port = argv[i];
        }
    }
    if (port && *port) {
        char* end = nullptr;
        long value = std::strtol(port, &end, 10);
        if (*end || value < 1 || value > 65535) { std::fprintf(stderr, "Invalid BBFT port\n"); std::exit(2); }
        enabled = true;
        bbft_transport_init("pikmin", nullptr, nullptr);
        const char* test = std::getenv("PIKMIN_BBFT_TEST_BACKGROUND");
        testBackground = test && !std::strcmp(test, "1");
        if (testBackground) pc_bbft_milestone("TEST_BACKGROUND_ENABLED input_still_requires_foreground");
    }
#endif
}
bool pc_bbft_enabled() { return enabled || challengeLevel >= 0; }
bool pc_bbft_skip_tutorial() {
    if (challengeLevel >= 0) return true;
    if (pc_randomizer_enabled()) return true;
#ifdef _WIN32
    return enabled && bbft_pikmin_skip_tutorial();
#else
    return false;
#endif
}
void pc_bbft_update() {
    if (pc_randomizer_enabled()) { pc_randomizer_update(); return; }
#ifdef _WIN32
    if (enabled) bbft_transport_update();
#endif
}
bool pc_bbft_hold() {
    if (pc_randomizer_enabled()) {
#ifdef _WIN32
        const char* background = std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND");
        return !pc_randomizer_ready() || (!(background && !std::strcmp(background, "1")) && !bbft_is_foreground());
#else
        return !pc_randomizer_ready();
#endif
    }
#ifdef _WIN32
    return enabled && (!bbft_state_ready() || bbft_warp_held() || (!testBackground && !bbft_is_foreground())
        || (bbft_region_unlocks() && !bbft_has("Pikmin Access")));
#else
    return false;
#endif
}
bool pc_bbft_accept_input() {
#ifdef _WIN32
    return !enabled || (bbft_is_foreground() && !pc_bbft_hold());
#else
    return true;
#endif
}
void pc_bbft_warp() {
    if (pc_randomizer_enabled()) return; // No cross-game switching in standalone mode.
#ifdef _WIN32
    if (enabled && pc_bbft_accept_input()) bbft_warp_out();
#endif
}
bool pc_bbft_forest_access() {
    if (pc_randomizer_enabled()) return pc_randomizer_has("Pikmin: Forest of Hope Access");
#ifdef _WIN32
    return !enabled || pc_bbft_skip_tutorial() || bbft_has("Pikmin: Forest of Hope Access");
#else
    return true;
#endif
}
void pc_bbft_check(const char* name) {
    if (pc_randomizer_enabled()) { pc_randomizer_check(name); return; }
#ifdef _WIN32
    if (enabled) bbft_check(name);
#endif
}
bool pc_bbft_checked(const char* name) {
    if (pc_randomizer_enabled()) return pc_randomizer_checked(name);
#ifdef _WIN32
    return enabled && bbft_checked(name);
#else
    return false;
#endif
}

bool pc_bbft_progression() {
    if (pc_randomizer_enabled()) return true;
#ifdef _WIN32
    return enabled && bbft_pikmin_progression();
#else
    return false;
#endif
}
bool pc_bbft_has(const char* name) {
    if (pc_randomizer_enabled()) return pc_randomizer_has(name);
#ifdef _WIN32
    return !enabled || bbft_has(name);
#else
    return true;
#endif
}
bool pc_bbft_color_access(int color) {
    // Engine colors: blue=0, red=1, yellow=2.
    if (pc_randomizer_enabled()) return (color == 0 && pc_randomizer_has("Blue Onion"))
        || (color == 1 && pc_randomizer_has("Red Onion")) || (color == 2 && pc_randomizer_has("Yellow Onion"));
    return !pc_bbft_progression() || color == 1 ||
        (color == 0 && pc_bbft_has(pc_bbft_shared_capabilities() ? "Zora Tunic" : "Blue Onion")) ||
        (color == 2 && pc_bbft_has("Yellow Onion"));
}

static bool onionSiteKnown[3] = {};
static float onionSiteX[3], onionSiteZ[3];
void pc_bbft_onion_site(int color, float x, float z) {
    if (!pc_bbft_progression() || color < 0 || color > 2) return;
    onionSiteKnown[color] = true; onionSiteX[color] = x; onionSiteZ[color] = z;
}
bool pc_bbft_near_onion_site(int color, float x, float z, float radius) {
    if (color < 0 || color > 2 || !onionSiteKnown[color]) return false;
    const float dx = x-onionSiteX[color], dz = z-onionSiteZ[color];
    return dx*dx+dz*dz <= radius*radius;
}

bool pc_bbft_shared_capabilities() {
    if (pc_randomizer_enabled()) return false;
#ifdef _WIN32
    return enabled && bbft_shared_capabilities();
#else
    return false;
#endif
}
bool pc_bbft_bomb_rocks() {
    return !pc_bbft_shared_capabilities() || (pc_bbft_has("Yellow Onion") && pc_bbft_has("Bomb Bag"));
}
