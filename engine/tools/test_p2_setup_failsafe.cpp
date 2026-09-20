// p2_setup_failsafe_test (#440): campaign species setups must degrade instead
// of aborting in bridge mode.
//
// In bridge mode (`pc_randomizer_p2_bridge()` true) a failed staged setup calls
// pc_p2_setup_skip(), logs one `P2_SETUP_SKIP <species> <reason>` line to stderr
// and returns true so the setup leaves the species' actors as P1 stand-ins. In
// fixture mode it aborts (fail-closed). This test is engine-free: it exercises
// the guard directly and, for Kogane, the real staged sidecar reader the setup
// gates on (p2kogane::read). The Otakara setup gate is the actor-type/roster
// check; the guard call for "Otakara" is asserted with a missing/malformed
// staged file. Fixture-mode abort is verified in a child process.
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_kogane_policy.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

namespace {

// Child process entry: a fixture-mode (bridge == false) failure must abort.
int fixture_abort_probe() {
    pc_p2_setup_skip(false, "Kogane", "fixture_fail_closed");
    return 0;
}

std::string slurp(const char* path) {
    std::ifstream in(path);
    return std::string((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

} // namespace

int main(int argc, char** argv) {
    if (argc > 1 && std::strcmp(argv[1], "--fixture-abort") == 0) return fixture_abort_probe();

    // Capture the guard's stderr markers for the rest of the run.
    const char* log = "p2_setup_failsafe_stderr.log";
    std::remove(log);
    std::freopen(log, "w", stderr);

    // A missing staged sidecar must not be fatal in bridge mode.
    std::remove("p2-kogane-native.txt");
    std::ifstream missing("p2-kogane-native.txt");
    assert(!missing);
    assert(pc_p2_setup_skip(true, "Kogane", "staged_file_missing"));

    // A malformed staged sidecar is rejected by the real Kogane reader the
    // setup gates on, and must then skip (not abort) in bridge mode.
    {
        std::istringstream malformed("P2_KOGANE_NATIVE_1 karada 60 actors 1 not-an-actor");
        p2kogane::Config config;
        assert(!p2kogane::read(malformed, config));
    }
    assert(pc_p2_setup_skip(true, "Kogane", "staged_file_malformed"));

    // Otakara's staged roster is p2-dweevil-actors.txt; a missing file returns
    // early, and an unexpected actor or incomplete roster now skips in bridge
    // mode through the same guard.
    std::remove("p2-dweevil-actors.txt");
    std::ifstream otakaraMissing("p2-dweevil-actors.txt");
    assert(!otakaraMissing);
    assert(pc_p2_setup_skip(true, "Otakara", "staged_file_missing"));
    assert(pc_p2_setup_skip(true, "Otakara", "actor_type_mismatch"));
    assert(pc_p2_setup_skip(true, "Otakara", "actor_roster_incomplete"));

    std::fflush(stderr);
    const std::string captured = slurp(log);
    assert(captured.find("P2_SETUP_SKIP Kogane staged_file_missing") != std::string::npos);
    assert(captured.find("P2_SETUP_SKIP Kogane staged_file_malformed") != std::string::npos);
    assert(captured.find("P2_SETUP_SKIP Otakara staged_file_missing") != std::string::npos);
    assert(captured.find("P2_SETUP_SKIP Otakara actor_type_mismatch") != std::string::npos);
    assert(captured.find("P2_SETUP_SKIP Otakara actor_roster_incomplete") != std::string::npos);

    // Fixture mode still fails closed: the child aborts, so its exit status is
    // abnormal. This preserves the existing fail-closed fixture behaviour.
    const std::string command = "\"" + std::string(argv[0]) + "\" --fixture-abort";
    const int status = std::system(command.c_str());
    assert(status != 0);

    std::puts("PASS p2_setup_failsafe_test");
    return 0;
}
