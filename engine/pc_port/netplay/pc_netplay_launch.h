#pragma once
// Netplay launch lane (issue #887): the one-command launcher
// (--netplay-host-ice / --netplay-join-ice), resolved BEFORE engine init.
//
// Netplay builds only (compiled into the game exe when
// PIKMIN_NETPLAY_BUILD=ON; pc_main.cpp calls it under PIKI_NETPLAY_BUILD).
//
// Order of events (fix round, B1/B2/M1: the session setup is known before any
// engine init on both sides, so it is resolved there):
//   1. pc_netplay_launch_preinit(), first thing in main():
//      - parses the launcher switches and refuses bad combinations;
//      - host: reads --bootstrap <file> (bounded) or builds the default
//        new-game bootstrap; joiner: reads the offer code exactly once
//        (literal, @file, or @clipboard through the Win32 clipboard, since
//        SDL is not up yet) and decodes the v2 session bundle;
//      - P2 seeds (M4 lane B2): the joiner needs --netplay-p2-assets DIR;
//        the run gets a play/ working directory (see PcNetplayLaunch::p2);
//      - host --continue [run folder] (M5c lane C): the bootstrap, netplay
//        seed and newest agreed checkpoint come from the newest host run
//        folder with a day-end save both games agreed on; they are copied
//        into the new run folder below (no saved day: a new campaign);
//      - creates this run's private dir (per run AND per peer) and writes
//        the bootstrap two levels inside it, re-stamped with this peer's
//        SESSION token, so the randomizer's derived campaign dir is private;
//      - sets NECTAR_SAVE_DIR (private save root), the joiner's
//        PIKMIN_NETPLAY_SEED (the bundle's seed; the det reseed reads it),
//        the background-joystick hint for a gamepad peer, and the hidden-run
//        env for --netplay-test-hidden;
//      - appends `--randomizer-seed <run bootstrap>` to argv, so the
//        bootstrap goes through exactly the path a hand-run seed uses.
//   2. pc_bbft_init(argv) parses that bootstrap; the randomizer writes the
//      launcher's static ready state.txt (pc_netplay_launch_wants_local_state)
//      next to it: no Archipelago, the run_pair.py neutral profile.
//   3. pc_netplay_launch_post_settings(), right after pc_settings_init():
//      starts the settings session guard; the joiner adopts the host's
//      sim-relevant settings for this session only (never persisted).
//   4. pc_netplay_session_drive(): only the answer-code exchange (ICE data
//      only) is left for after init.
//
// Working directory: never changed for ordinary seeds. Players start the exe
// from their game folder; assets/ and pikmin_settings.conf stay
// cwd-relative, and every run-dir file is addressed by absolute path. A P2
// seed (M4 lane B2) changes it to <run>/play before pc_settings_init, with
// the settings file pinned to the original folder's pikmin_settings.conf.

#include <cstdint>
#include <string>

struct PcNetplayLaunch {
	bool active = false;       // --netplay-host-ice or --netplay-join-ice
	bool isHost = false;
	bool externalState = false; // explicit AP/Python authority; defaults remain local
	std::string requestedRunRoot; // explicit private base; never a reused run
	std::string runDir;        // absolute; private to this run and this peer
	std::string bootstrapPath; // absolute: <runDir>/session/runs/<token>/bootstrap.txt
	std::string campaignDir;   // absolute: <runDir>/session/campaign (derived)
	std::string saveDir;       // absolute: <runDir>/save (NECTAR_SAVE_DIR)
	std::string token;         // this peer's SESSION token (64 lowercase hex)
	std::string bootstrapSource; // "default", the --bootstrap path, or "offer bundle"
	// M4 lane B2 (issue #885): P2 seeds (ENEMY_P2 / P2_* tokens) run with
	// <runDir>/play as the working directory, set before pc_settings_init:
	// play/assets is a junction to the overlay (host: <bootstrap dir>/assets,
	// joiner: --netplay-p2-assets DIR) and the host copies its sidecar set
	// (p2-*.txt, sarai-*.txt) there; the joiner receives it in the transfer
	// phase. pikmin_settings.conf stays the original working directory's.
	bool p2 = false;
	std::string playDir;       // absolute; empty unless p2
	std::string p2AssetsDir;   // absolute overlay dir behind play/assets
	std::string settingsPath;  // absolute pinned settings file (p2 only)
	std::string offerCode;     // joiner: the offer text, read exactly once
	uint32_t seed = 0;         // netplay seed (host: env or 0; joiner: bundle)
	std::string configBlock;   // joiner: the host's m3-config-v1 block
	bool haveCaptains = false; // joiner: captains carried in the block
	int captainP1 = 0;
	int captainP2 = 1;
	std::string codeOut;       // --netplay-code-out <file>
	std::string answerIn;      // --netplay-answer-in <file> (host)
	// M5c lane C (issue #887): --continue [run folder] (host). The continued
	// run's bootstrap, netplay seed and newest agreed checkpoint (plus card and
	// ledgers, copied into this run's campaign dir) start this session; the
	// old run folder is only read. <runDir>/campaign-record.txt names the
	// day-end saves both games agreed on (pc_netplay_continue.h).
	bool continued = false;
	std::string continueFrom;  // the continued run folder
	unsigned long long continueGen = 0;
	int continueDay = 0;       // the day that checkpoint plays on from (0 = unknown)
	int continueDayEnded = 0;  // the day whose end it saved (0 = unknown)
	bool testHidden = false;   // --netplay-test-hidden
	uint64_t testTicks = 0;    // --netplay-test-ticks N
	// --netplay-input (any netplay mode; parsed here so the gamepad hint is
	// set before SDL_Init).
	std::string inputSpec;
	int inputKind  = 0; // pc_netplay_input_sel::Kind
	int inputIndex = 0;
};

// Resolves the launcher's session setup (see above). Rewrites *argc/*argv
// when a launcher switch is present; prints and exits with code 2 on a
// refusal. Without a launcher switch it only validates --netplay-input.
void pc_netplay_launch_preinit(int* argc, char*** argv);
// Settings guard + joiner adoption; call right after pc_settings_init().
void pc_netplay_launch_post_settings(void);
// The resolved setup (inactive when no launcher switch was given).
const PcNetplayLaunch& pc_netplay_launch_setup(void);
// Joiner: re-applies the host's captains after the session's co-op switch
// (which resets them) ran. No-op for the host and outside launcher mode.
void pc_netplay_launch_apply_captains(void);
// True only in local-authority launcher mode: writes a static ready state.txt
// (no Archipelago) next to the run bootstrap. Referenced weakly by
// pc_randomizer.cpp.
bool pc_netplay_launch_wants_local_state(void);

// In-exe self-tests for ctest (pc_netplay_launch_selftest.cpp):
//   nectar.exe --netplay-launch-selftest settings|input|input-session
// Returns the process exit code (0 = pass).
int pc_netplay_launch_selftest(int argc, char** argv);
