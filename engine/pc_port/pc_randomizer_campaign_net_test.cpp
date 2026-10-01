// Netplay M4 lane B2 (issue #885): pc_randomizer.cpp's campaign functions in a
// netplay session, against stub session hooks, with real file I/O.
//
// Like pc_randomizer_outbox_io_test, this test defines the randomizer's weak
// session hooks strongly (a session with the external-state stream on, in
// the role given on the command line) plus a scripted day-end barrier
// (pc_netplay_save_barrier), and checks the files:
//
//   host        save_campaign_netplay writes the real checkpoint and hands
//               the barrier the exact .sav bytes; the host's outcome is
//               returned; a local card failure writes nothing and keeps the
//               generation; checkpoint_info reports the newest checkpoint and
//               the SHA-256 of its file.
//   client      the mirror checkpoint is <name>.sav.pending while the barrier
//               runs (fix round 1, C2) and becomes <name>.sav only after the
//               host's ok (SAVE_RESULT with the host's digest); a host failure
//               renames it to .sav.unconfirmed (never deleted), keeps the
//               generation and writes SAVE_FAIL; a local failure under a host
//               success follows the host (the generation still advances);
//               adopt re-reads the directory like a boot
//               (CAMPAIGN_RESUMED generation=<g>).
//   client-abandon  the barrier is abandoned (the session's exit 5/6 path
//               calls pc_randomizer_netplay_barrier_abandoned): the pending
//               checkpoint is retracted to .sav.unconfirmed and no .sav of
//               that generation exists (fix round 1, C2).
//   join-stale  netplay join mode: a foreign-fingerprint checkpoint and a
//               badly named .sav are set aside as *.sav.stale-<secs> at init
//               instead of failing, and the joiner continues as "none".
//   host-stale-foreign / host-stale-badname  (fix round 1, X8) the host keeps
//               the fatal behaviour: each role runs itself as a child process
//               over ONE planted file (a foreign-fingerprint .sav, or a badly
//               named .sav) and requires exit code 2 and the exact historical
//               message.
//
// Each role runs in its own process under a per-process folder
// <cwd>/campaign_net_<role>_<pid>/ (fix round 1, C11/E4: concurrent ctest
// runs cannot collide, and a folder that cannot be cleared fails loudly).

#include "pc_randomizer.h"
#include "netplay/pc_netplay_sha256.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#ifdef _WIN32
#include <process.h>
#define CAMPAIGN_NET_TEST_PID _getpid()
#else
#include <sys/wait.h>
#include <unistd.h>
#define CAMPAIGN_NET_TEST_PID getpid()
#endif

namespace {
bool gHost = true;
uint32_t gFrame = 0;
int gFailures = 0;
// Scripted barrier.
bool gBarrierHostOk = true;
bool gBarrierAbandon = false;
std::string gBarrierHostHex(64, 'a');
int gBarrierCalls = 0;
uint32_t gBarrierFrame = 0;
bool gBarrierLocalOk = false;
unsigned long long gBarrierGen = 0;
std::string gBarrierSav;
std::filesystem::path gCamp;
std::filesystem::path gRoot;

#define CHECK(cond, what)                                                   \
	do {                                                                    \
		if (!(cond)) {                                                      \
			std::printf("FAIL: %s (line %d)\n", what, __LINE__);            \
			++gFailures;                                                    \
		}                                                                   \
	} while (0)

std::string slurp(const std::filesystem::path& p)
{
	std::ifstream in(p, std::ios::binary);
	std::ostringstream s;
	s << in.rdbuf();
	return s.str();
}

const char* kToken = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff";
const char* kPrint = "ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100";
const char* kOther = "1111111111111111111111111111111111111111111111111111111111111111";

std::string sav_name(unsigned long long g)
{
	char n[32];
	std::snprintf(n, sizeof(n), "%020llu.sav", g);
	return n;
}

std::string sha_hex_file(const std::filesystem::path& p)
{
	const std::string b = slurp(p);
	uint8_t d[32];
	pc_netplay_sha::sha256(b.data(), b.size(), d);
	return pc_netplay_sha::hex(d, 32);
}

size_t count_prefix(const std::filesystem::path& dir, const std::string& prefix)
{
	size_t n = 0;
	std::error_code ec;
	for (const auto& e : std::filesystem::directory_iterator(dir, ec))
		if (e.path().filename().string().compare(0, prefix.size(), prefix) == 0) ++n;
	return n;
}

// Runs this executable with `role` as a child process, output to `out`;
// returns its exit code (-1 when it could not be run).
int run_child(const char* self, const std::string& role, const std::filesystem::path& out)
{
	// cmd.exe strips one outer pair of quotes, hence the extra pair.
	const std::string cmd = "\"\"" + std::string(self) + "\" " + role + " > \"" + out.string() + "\" 2>&1\"";
#ifdef _WIN32
	return std::system(cmd.c_str());
#else
	const int st = std::system(cmd.substr(1, cmd.size() - 2).c_str());
	return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
#endif
}
} // namespace

// ---- strong definitions of pc_randomizer.cpp's weak session hooks ----
bool pc_netplay_session_active(void) { return true; }
bool pc_netplay_is_host(void) { return gHost; }
bool pc_netplay_randstate_stream_enabled(void) { return true; }
void pc_netplay_randstate_publish(const pc_randstate::PcRandState&) {}
bool pc_netplay_hold_active(void) { return false; }
void pc_netplay_mirror_ledger_send(const uint8_t*, size_t) {}
uint32_t pc_netplay_current_frame(void) { return gFrame; }
void pc_netplay_abort_desync(const char* why)
{
	std::printf("pc_randomizer_campaign_net_test: unexpected desync abort: %s\n", why);
	std::exit(5);
}
bool pc_netplay_save_barrier(uint32_t frame, bool localOk, unsigned long long gen, const uint8_t* sav, size_t savLen,
                             const uint8_t*, size_t blockLen, bool* hostOk, char hostSavHex[65])
{
	++gBarrierCalls;
	gBarrierFrame   = frame;
	gBarrierLocalOk = localOk;
	gBarrierGen     = gen;
	gBarrierSav.assign(reinterpret_cast<const char*>(sav), savLen);
	CHECK(blockLen == 32768, "the barrier gets the 0x8000 game-file block");
	if (gHost) {
		*hostOk = localOk;
		std::string hx(64, '0');
		if (localOk) {
			uint8_t d[32];
			pc_netplay_sha::sha256(sav, savLen, d);
			hx = pc_netplay_sha::hex(d, 32);
		}
		std::memcpy(hostSavHex, hx.c_str(), 65);
		return true;
	}
	// Client (fix round 1, C2): while the barrier runs, no .sav of this
	// generation exists; the mirror is the .pending file, with these bytes.
	if (localOk) {
		CHECK(!std::filesystem::exists(gCamp / sav_name(gen)), "no unconfirmed .sav during the barrier");
		CHECK(slurp(gCamp / (sav_name(gen) + ".pending")) == gBarrierSav,
		      "the pending mirror checkpoint holds the bytes handed to the barrier");
	}
	if (gBarrierAbandon) {
		// The session's exit 5/6 path: retract, then the process exits.
		pc_randomizer_netplay_barrier_abandoned();
		CHECK(!std::filesystem::exists(gCamp / sav_name(gen)) && !std::filesystem::exists(gCamp / (sav_name(gen) + ".pending"))
		          && std::filesystem::exists(gCamp / (sav_name(gen) + ".unconfirmed")),
		      "an abandoned barrier retracts the pending checkpoint to .unconfirmed");
		uint64_t g = 9;
		uint8_t sha[32];
		CHECK(pc_randomizer_checkpoint_info(&g, sha) && g == gen - 1,
		      "after the retraction the newest checkpoint is the last agreed one");
		std::printf("pc_randomizer_campaign_net_test client-abandon: %s (%d failures)\n",
		            gFailures == 0 ? "PASS" : "FAIL", gFailures);
		std::error_code ec;
		if (gFailures == 0) std::filesystem::remove_all(gRoot, ec); // best effort
		std::exit(gFailures == 0 ? 0 : 1);
	}
	*hostOk = gBarrierHostOk;
	std::memcpy(hostSavHex, gBarrierHostHex.c_str(), 65);
	return true;
}

int main(int argc, char** argv)
{
	setvbuf(stdout, nullptr, _IONBF, 0);
	const std::string role = argc > 1 ? argv[1] : "";
	const bool known = role == "host" || role == "client" || role == "client-abandon" || role == "join-stale"
	                || role == "host-stale-foreign" || role == "host-stale-badname"
	                || role == "host-stale-foreign-child" || role == "host-stale-badname-child";
	if (!known) {
		std::printf("usage: pc_randomizer_campaign_net_test host|client|client-abandon|join-stale|"
		            "host-stale-foreign|host-stale-badname\n");
		return 2;
	}
	namespace fs = std::filesystem;
	if (role == "host-stale-foreign" || role == "host-stale-badname") {
		// Parent: the fatal path must exit 2 with the historical message.
		const std::string tag = std::to_string(CAMPAIGN_NET_TEST_PID);
		const fs::path out = fs::current_path() / ("campaign_net_" + role + "_" + tag + ".log");
		// The child uses this process's pid as its folder tag, so the parent
		// can remove the child's fixture folder afterwards.
		const int rc = run_child(argv[0], role + "-child " + tag, out);
		const std::string text = slurp(out);
		const std::string want = role == "host-stale-foreign"
		                           ? "[Pikmin Randomizer] campaign checkpoint header/seed mismatch; preserve campaign files for recovery"
		                           : "[Pikmin Randomizer] invalid campaign checkpoint filename";
		CHECK(rc == 2, "the host exits 2 on a stale checkpoint");
		CHECK(text.find(want) != std::string::npos, "the historical fatal message");
		CHECK(text.find("REACHED") == std::string::npos, "init never returned");
		std::printf("child exit %d, output:\n%s", rc, text.c_str());
		std::error_code ec;
		fs::remove(out, ec);
		if (gFailures == 0) fs::remove_all(fs::current_path() / ("campaign_net_" + role + "-child_" + tag), ec);
		std::printf("pc_randomizer_campaign_net_test %s: %s (%d failures)\n", role.c_str(),
		            gFailures == 0 ? "PASS" : "FAIL", gFailures);
		return gFailures == 0 ? 0 : 1;
	}
	gHost = role == "host" || role == "host-stale-foreign-child" || role == "host-stale-badname-child";
	// A child role gets its folder tag from the parent (argv[2]).
	const std::string tag = argc > 2 ? std::string(argv[2]) : std::to_string(CAMPAIGN_NET_TEST_PID);
	const fs::path root = fs::current_path() / ("campaign_net_" + role + "_" + tag);
	gRoot = root;
	std::error_code ec;
	fs::remove_all(root, ec);
	if (ec) {
		std::printf("FAIL: cannot clear the fixture folder %s: %s\n", root.string().c_str(), ec.message().c_str());
		return 1;
	}
	const fs::path sess = root / "sess";
	const fs::path run = sess / "runs" / "run1";
	const fs::path camp = sess / "campaign";
	gCamp = camp;
	fs::create_directories(run, ec);
	fs::create_directories(camp, ec);
	if (ec || !fs::is_directory(run) || !fs::is_directory(camp)) {
		std::printf("FAIL: cannot create the fixture folders under %s\n", root.string().c_str());
		return 1;
	}
	{
		std::ofstream b(run / "bootstrap.txt", std::ios::binary);
		b << "PIKMIN_RANDOMIZER 9\nSESSION " << kToken << "\nFINGERPRINT " << kPrint
		  << "\nPROFILE foh-day2\nCATALOG gameplay-checks-v9\nPLACEMENT identity-v1\nGOAL emperor25\n"
		     "DAYS repeat-day29-v1\nCOLOR red\nCHECKSET 6\nENEMIES 0\nEND\n";
	}
	if (role == "join-stale" || role == "host-stale-foreign-child") {
		// A foreign campaign (another seed's fingerprint).
		std::ofstream f(camp / sav_name(1), std::ios::binary);
		f << "PIKMIN_CAMPAIGN_1 " << kOther << " 1 0 0 0 123\n" << std::string(32768, 'x');
	}
	if (role == "join-stale" || role == "host-stale-badname-child") {
		// A badly named .sav.
		std::ofstream g(camp / "notes.sav", std::ios::binary);
		g << "junk";
	}
	std::string seedArg = (run / "bootstrap.txt").string();
	char arg0[] = "pc_randomizer_campaign_net_test";
	char arg1[] = "--randomizer-seed";
	char* args[] = { arg0, arg1, seedArg.data(), nullptr };
	CHECK(pc_randomizer_init(3, args), "init with the test bootstrap");
	if (role == "host-stale-foreign-child" || role == "host-stale-badname-child") {
		// Never reached: init must have exited 2.
		std::printf("REACHED past init\n");
		return 0;
	}
	if (role == "join-stale") {
		CHECK(!fs::exists(camp / sav_name(1)) && !fs::exists(camp / "notes.sav"), "stale .sav files set aside");
		CHECK(count_prefix(camp, sav_name(1) + ".stale-") == 1 && count_prefix(camp, "notes.sav.stale-") == 1,
		      "renamed to *.sav.stale-<secs>, never deleted");
		CHECK(!pc_randomizer_resumed(), "the joiner continues as none");
		uint64_t gen = 7;
		uint8_t sha[32];
		std::memset(sha, 0xAB, 32);
		CHECK(pc_randomizer_checkpoint_info(&gen, sha) && gen == 0 && pc_netplay_sha::is_zero(sha, 32),
		      "checkpoint info: none after the set-aside");
	}

	std::vector<char> block(32768);
	for (size_t i = 0; i < block.size(); ++i) block[i] = (char)(i * 7 + 3);
	CHECK(pc_randomizer_netplay_save_barrier_active(), "barrier active in a stream session with the hook");

	if (role == "host") {
		gFrame = 27000;
		CHECK(pc_randomizer_save_campaign_netplay(block.data(), true), "host save: host ok");
		CHECK(fs::exists(camp / sav_name(1)) && !fs::exists(camp / (sav_name(1) + ".pending")),
		      "host checkpoint gen 1 written under its real name");
		CHECK(gBarrierCalls == 1 && gBarrierFrame == 27000 && gBarrierLocalOk && gBarrierGen == 1,
		      "barrier called with frame 27000, gen 1, local ok");
		CHECK(gBarrierSav == slurp(camp / sav_name(1)), "the barrier hashes the exact .sav bytes");
		uint64_t gen = 0;
		uint8_t sha[32];
		CHECK(pc_randomizer_checkpoint_info(&gen, sha) && gen == 1 && pc_netplay_sha::hex(sha, 32) == sha_hex_file(camp / sav_name(1)),
		      "checkpoint info: gen 1 and the file's SHA-256");
		gFrame = 60000;
		CHECK(!pc_randomizer_save_campaign_netplay(block.data(), false), "host card failure: not ok");
		CHECK(!fs::exists(camp / sav_name(2)) && gBarrierGen == 2 && !gBarrierLocalOk,
		      "no checkpoint written; the barrier still reports gen 2, not ok");
		gFrame = 90000;
		CHECK(pc_randomizer_save_campaign_netplay(block.data(), true), "next host save ok");
		CHECK(fs::exists(camp / sav_name(2)), "the generation did not advance on the failure (gen 2 now)");
		CHECK(!fs::exists(run / "mirror-events.txt"), "the host writes no mirror");
	}
	if (role == "client-abandon") {
		gFrame = 27000;
		CHECK(pc_randomizer_save_campaign_netplay(block.data(), true), "client: host ok (gen 1)");
		gBarrierAbandon = true;
		gFrame          = 60000;
		pc_randomizer_save_campaign_netplay(block.data(), true); // exits from the barrier stub
		std::printf("FAIL: the abandoned barrier returned\n");
		return 1;
	}
	if (role == "client" || role == "join-stale") {
		const std::string hostHex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
		gBarrierHostHex = hostHex;
		gBarrierHostOk  = true;
		gFrame          = 27000;
		CHECK(pc_randomizer_save_campaign_netplay(block.data(), true), "client: host ok");
		CHECK(fs::exists(camp / sav_name(1)) && !fs::exists(camp / (sav_name(1) + ".pending")),
		      "mirror checkpoint gen 1 published under its real name after the host's ok");
		gBarrierHostOk = false;
		gFrame         = 60000;
		CHECK(!pc_randomizer_save_campaign_netplay(block.data(), true), "client: host failed");
		CHECK(!fs::exists(camp / sav_name(2)) && !fs::exists(camp / (sav_name(2) + ".pending"))
		          && fs::exists(camp / (sav_name(2) + ".unconfirmed")),
		      "the unconfirmed mirror checkpoint is renamed, never deleted");
		gBarrierHostOk = true;
		gFrame         = 90000;
		CHECK(pc_randomizer_save_campaign_netplay(block.data(), false), "client local failure: follows the host");
		CHECK(gBarrierGen == 2 && !fs::exists(camp / sav_name(2)),
		      "the retracted generation is reused (gen 2); nothing written locally");
		gFrame = 120000;
		CHECK(pc_randomizer_save_campaign_netplay(block.data(), true), "next client save");
		CHECK(gBarrierGen == 3 && fs::exists(camp / sav_name(3)), "after following the host the generation advanced (gen 3)");
		const std::string mirror = slurp(run / "mirror-events.txt");
		const std::string want = "FRAME 27000 SAVE_RESULT 1 " + hostHex + "\nFRAME 60000 SAVE_FAIL 2\nFRAME 90000 SAVE_RESULT 2 "
		                       + hostHex + "\nFRAME 120000 SAVE_RESULT 3 " + hostHex + "\n";
		CHECK(mirror == want, "mirror-events.txt: SAVE_RESULT / SAVE_FAIL lines, LF only");
		if (mirror != want) std::printf("mirror was:\n%s", mirror.c_str());
		// Adoption re-reads the directory like a boot.
		CHECK(pc_randomizer_adopt_checkpoint() && pc_randomizer_resumed(), "adopt resumes the newest checkpoint");
		uint64_t gen = 0;
		uint8_t sha[32];
		CHECK(pc_randomizer_checkpoint_info(&gen, sha) && gen == 3, "checkpoint info: gen 3");
	}

	std::printf("pc_randomizer_campaign_net_test %s: %s (%d failures)\n", role.c_str(), gFailures == 0 ? "PASS" : "FAIL",
	            gFailures);
	if (gFailures == 0) fs::remove_all(root, ec); // best effort; the name is unique per process
	return gFailures == 0 ? 0 : 1;
}
