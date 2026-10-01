// Netplay M4 lane B1 fix round 1 (issue #885): pc_randomizer.cpp's
// outbox-active paths against stub session hooks, with real file I/O.
//
// pc_randomizer.cpp reaches the netplay session only through weak hooks
// (null in engine-free builds). This test defines them strongly, so the
// randomizer believes a netplay session with the external-state stream is
// active, in the role given on the command line:
//
//   host            the host journals: checks.txt, benefits-used.txt,
//                   emperor.txt (via emperor.tmp), deaths.txt and the P2
//                   ordinary delivery ledger, exact bytes, written only at
//                   the flush; a streamed CHECKS echo of a journaled slot
//                   writes no second line; the session-start ledger message
//                   (deathsBase + receipts) always goes out; no mirror file.
//   client          no journal at all; mirror-events.txt exact bytes (LF
//                   only), each line with its event's own frame; a DEATHS
//                   total that happens before the first ledger message waits
//                   for it (no DEATHS with base 0).
//   client-unknown  a ledger message with the kLedgerBaseUnknown base
//                   suppresses every DEATHS line.
//   host-noledger   no session.json: the session-start message is still
//                   sent, with base 0 and no receipts.
//
// Each role runs in its own process (the randomizer state is per process)
// under <cwd>/outbox_io_<role>/, laid out like a runner session:
// sess/runs/run1/bootstrap.txt, sess/session.json, sess/campaign/.

#include "pc_randomizer.h"
#include "pc_randomizer_catalog.h"
#include "pc_randomizer_outbox.h"
#include "pc_p2_delivery_host.h"
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
#define OUTBOX_IO_TEST_PID _getpid()
#else
#include <unistd.h>
#define OUTBOX_IO_TEST_PID getpid()
#endif

namespace {
bool gHost = true;
uint32_t gFrame = 0;
std::vector<std::vector<uint8_t>> gLedgerSent;
int gFailures = 0;

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

#ifdef _WIN32
const char* kEol = "\r\n"; // the host journals keep their text-mode "a" writes
#else
const char* kEol = "\n";
#endif

const char* kToken = "00112233445566778899aabbccddeeff00112233445566778899aabbccddeeff";
const char* kPrint = "ffeeddccbbaa99887766554433221100ffeeddccbbaa99887766554433221100";

pc_randstate::PcRandState state(uint16_t deathLinks, std::initializer_list<unsigned> checkSlots)
{
	pc_randstate::PcRandState st;
    CHECK(pc_randomizer_get_net_state(&st), "authenticated bootstrap metadata");
	st.ver = pc_randstate::kVersion;
	st.ready = 1;
	st.repairs = 25;
	st.unlocks = 0;
	st.flarlic = 0;
	st.emperor = 0;
	st.deathLinks = deathLinks;
	for (size_t i = 0; i < pc_randstate::kCheckBytes; ++i) st.checks[i] = 0;
	for (unsigned slot : checkSlots) st.checks[slot / 8] |= (uint8_t)(1u << (slot % 8));
	for (int i = 0; i < 12; ++i) st.stats[i] = 0;
	for (int k = 0; k < 9; ++k) st.benefits[k] = 0;
	st.benefits[0] = 2; // two receipts of benefit kind 0
	st.gen = 1;
	return st;
}
} // namespace

// ---- strong definitions of pc_randomizer.cpp's weak session hooks ----
bool pc_netplay_session_active(void) { return true; }
bool pc_netplay_is_host(void) { return gHost; }
bool pc_netplay_randstate_stream_enabled(void) { return true; }
void pc_netplay_randstate_publish(const pc_randstate::PcRandState&) {}
bool pc_netplay_hold_active(void) { return false; }
void pc_netplay_mirror_ledger_send(const uint8_t* data, size_t len)
{
	gLedgerSent.emplace_back(data, data + len);
}
uint32_t pc_netplay_current_frame(void) { return gFrame; }

int main(int argc, char** argv)
{
	setvbuf(stdout, nullptr, _IONBF, 0);
	const std::string role = argc > 1 ? argv[1] : "";
	if (role != "host" && role != "client" && role != "client-unknown" && role != "host-noledger") {
		std::printf("usage: pc_randomizer_outbox_io_test host|client|client-unknown|host-noledger\n");
		return 2;
	}
	gHost = role == "host" || role == "host-noledger";
	namespace fs = std::filesystem;
	// B2 fix round 1 (E4): a per-process fixture folder, so concurrent ctest
	// runs in one build dir cannot collide; a folder that cannot be cleared
	// fails loudly instead of leaving stale state behind.
	const fs::path root = fs::current_path() / ("outbox_io_" + role + "_" + std::to_string(OUTBOX_IO_TEST_PID));
	std::error_code ec;
	fs::remove_all(root, ec);
	if (ec) {
		std::printf("FAIL: cannot clear the fixture folder %s: %s\n", root.string().c_str(), ec.message().c_str());
		return 1;
	}
	const fs::path sess = root / "sess";
	const fs::path run = sess / "runs" / "run1";
	fs::create_directories(run);
	fs::create_directories(sess / "campaign");
	{
		std::ofstream b(run / "bootstrap.txt", std::ios::binary);
		b << "PIKMIN_RANDOMIZER 9\nSESSION " << kToken << "\nFINGERPRINT " << kPrint
		  << "\nPROFILE foh-day2\nCATALOG gameplay-checks-v9\nPLACEMENT identity-v1\nGOAL emperor25\n"
		     "DAYS repeat-day29-v1\nCOLOR red\nCHECKSET 6\nENEMIES 0\nBENEFITS 1\nDEATHLINK 1\nEND\n";
	}
	if (role != "host-noledger") {
		// Exactly what root session.py writes: json.dumps(obj, indent=2).
		std::ofstream j(sess / "session.json", std::ios::binary);
		j << "{\n  \"received\": [\n    8,\n    1,\n    42\n  ],\n  \"pikmin_deaths\": 5\n}";
	}
	std::string seedArg = (run / "bootstrap.txt").string();
	char arg0[] = "pc_randomizer_outbox_io_test";
	char arg1[] = "--randomizer-seed";
	char* args[] = { arg0, arg1, seedArg.data(), nullptr };
	CHECK(pc_randomizer_init(3, args), "init with the test bootstrap");
	const char* nameA = randomizerColorCollectionNames[3];
	const char* nameB = randomizerColorCollectionNames[5];

	if (gHost) {
		// Session start: no state.txt, so the forced publish reports false
		// (the session HOLDs from its first input); the ledger's first
		// message always goes out.
		CHECK(!pc_randomizer_force_net_publish(), "force publish without state.txt reports missing state");
		CHECK(gLedgerSent.size() == 1, "exactly one session-start ledger message");
		if (!gLedgerSent.empty()) {
			pc_rand_outbox::LedgerMsg m;
			CHECK(pc_rand_outbox::decode_ledger(gLedgerSent[0].data(), gLedgerSent[0].size(), m), "ledger decodes");
			if (role == "host") {
				CHECK(m.deathsBase == 5 && m.firstIndex == 0 && m.ids.size() == 3 && m.ids[0] == 8
				          && m.ids[1] == 1 && m.ids[2] == 42,
				      "session-start ledger: base 5, receipts 8 1 42");
			} else {
				CHECK(m.deathsBase == 0 && m.firstIndex == 0 && m.ids.empty(),
				      "no session.json: session-start ledger with base 0 and no receipts");
			}
		}
		gFrame = 40;
		CHECK(pc_randomizer_apply_net_state(state(0, {})), "baseline apply");
		gFrame = 100;
		pc_randomizer_check(nameA);
		CHECK(!fs::exists(run / "checks.txt"), "checks.txt untouched before the flush");
		pc_randomizer_outbox_flush(100);
		CHECK(slurp(run / "checks.txt") == "3" + std::string(kEol), "checks.txt: one line after the flush");
		gFrame = 110;
		CHECK(pc_randomizer_consume_benefit((PcBenefit)0), "benefit consumed");
		CHECK(!fs::exists(run / "benefits-used.txt"), "benefits-used.txt untouched before the flush");
		pc_randomizer_outbox_flush(110);
		CHECK(slurp(run / "benefits-used.txt") == std::string(kPrint) + " 0 1" + kEol,
		      "benefits-used.txt: fingerprint kind count");
		CHECK(pc_randomizer_consume_benefit((PcBenefit)0), "second benefit consumed");
		CHECK(!pc_randomizer_consume_benefit((PcBenefit)0), "no third benefit (two received)");
		pc_randomizer_outbox_flush(110);
		CHECK(slurp(run / "benefits-used.txt")
		          == std::string(kPrint) + " 0 1" + kEol + kPrint + " 0 2" + kEol,
		      "benefits-used.txt: second line");
		gFrame = 120;
		pc_randomizer_observe_pikmin_death(nullptr);
		pc_randomizer_observe_pikmin_death(nullptr);
		CHECK(!fs::exists(run / "deaths.txt"), "deaths.txt untouched before the flush");
		pc_randomizer_outbox_flush(120);
		CHECK(slurp(run / "deaths.txt") == "1" + std::string(kEol) + "2" + kEol, "deaths.txt: running totals");
		// A streamed CHECKS echo of the journaled slot (3) plus a new AP slot
		// (5), and a DeathLink rise: no second checks.txt line, nothing else
		// written on the host.
		gFrame = 130;
		CHECK(pc_randomizer_apply_net_state(state(2, { 3, 5 })), "streamed echo apply");
		pc_randomizer_outbox_flush(130);
		CHECK(slurp(run / "checks.txt") == "3" + std::string(kEol), "streamed echo: no second checks.txt line");
		CHECK(pc_randomizer_checked(nameB), "streamed slot is in the sim set");
		gFrame = 140;
		pc_randomizer_emperor_defeated();
		CHECK(!fs::exists(run / "emperor.txt"), "emperor.txt untouched before the flush");
		pc_randomizer_outbox_flush(140);
		CHECK(slurp(run / "emperor.txt")
		          == "EMPEROR_DEFEATED " + std::string(kToken) + " " + kPrint + kEol,
		      "emperor.txt: token and fingerprint");
		CHECK(!fs::exists(run / "emperor.tmp"), "emperor.tmp renamed away");
		// P2 ordinary delivery: Granted on the sim side at once; the host
		// delivers to the ledger at the flush.
		int teki = 0;
		gFrame = 150;
		pc_randomizer_p2_bind_source(&teki, 1, 777);
		CHECK(pc_randomizer_p2_corpse_delivered(&teki, 5, 1, true), "P2 delivery returns true");
		CHECK(pc_randomizer_p2_receipt_seen(777), "P2 receipt generator recorded on the sim side");
		const fs::path ledger = sess / "campaign" / "p2-delivery-receipts.txt";
		pc_randomizer_outbox_flush(150);
		CHECK(fs::exists(ledger) && fs::file_size(ledger) > 0, "P2 ledger written at the flush");
		{
			P2DeliveryHostHandle h = pc_p2_delivery_host_open(ledger.string().c_str());
			CHECK(h != nullptr, "P2 ledger reopens");
			if (h)
				CHECK(pc_p2_delivery_host_deliver(h, kPrint, 1, 5, 1, 777, "corpse") == P2DeliveryHostResult::Duplicate,
				      "P2 ledger already holds the flushed delivery (duplicate on replay)");
		}
		CHECK(!fs::exists(run / "mirror-events.txt"), "host never writes mirror-events.txt");
		// A later session.json rewrite with a new receipt is picked up by
		// the stream-host poll even though state.txt never changed.
		if (role == "host") {
			const size_t before = gLedgerSent.size();
			{
				std::ofstream j(sess / "session.json", std::ios::binary);
				j << "{\n  \"received\": [\n    8,\n    1,\n    42,\n    9\n  ],\n  \"pikmin_deaths\": 7\n}";
			}
			fs::last_write_time(sess / "session.json", fs::file_time_type::clock::now() + std::chrono::seconds(5));
			pc_randomizer_update();
			CHECK(gLedgerSent.size() == before + 1, "session.json rewrite sends one ledger message");
			if (gLedgerSent.size() == before + 1) {
				pc_rand_outbox::LedgerMsg m;
				CHECK(pc_rand_outbox::decode_ledger(gLedgerSent.back().data(), gLedgerSent.back().size(), m)
				          && m.deathsBase == 5 && m.firstIndex == 3 && m.ids.size() == 1 && m.ids[0] == 9,
				      "later ledger: only the new receipt, base still the session-start 5");
			}
			pc_randomizer_update();
			CHECK(gLedgerSent.size() == before + 1, "unchanged session.json sends nothing");
		}
	} else {
		gFrame = 40;
		CHECK(pc_randomizer_apply_net_state(state(0, {})), "baseline apply");
		gFrame = 50;
		pc_randomizer_observe_pikmin_death(nullptr); // before any ledger message
		pc_randomizer_outbox_flush(50);
		CHECK(!fs::exists(run / "mirror-events.txt") || slurp(run / "mirror-events.txt").find("DEATHS") == std::string::npos,
		      "no DEATHS line before the ledger");
		gFrame = 60;
		pc_randomizer_check(nameA);
		pc_randomizer_outbox_flush(60);
		const uint32_t base = role == "client" ? 5u : pc_rand_outbox::kLedgerBaseUnknown;
		const uint32_t ids[] = { 8, 1, 42 };
		std::vector<uint8_t> m = pc_rand_outbox::encode_ledger(base, 0, ids, 3);
		pc_randomizer_mirror_ledger_receive(m.data(), m.size(), 70);
		gFrame = 80;
		pc_randomizer_observe_pikmin_death(nullptr);
		gFrame = 85;
		CHECK(pc_randomizer_consume_benefit((PcBenefit)0), "client consumes the benefit on the sim side");
		gFrame = 90;
		pc_randomizer_emperor_defeated();
		int teki = 0;
		pc_randomizer_p2_bind_source(&teki, 1, 777);
		CHECK(pc_randomizer_p2_corpse_delivered(&teki, 5, 1, true), "client P2 delivery returns true (no ledger I/O)");
		// Flushed late on purpose: every line keeps its own push frame.
		gFrame = 95;
		pc_randomizer_outbox_flush(95);
		gFrame = 100;
		CHECK(pc_randomizer_apply_net_state(state(2, { 3, 5 })), "streamed apply with DeathLink rise");
		pc_randomizer_outbox_flush(100);
		std::string want = "FRAME 60 CHECKED " + std::string(nameA) + "\n";
		if (role == "client") want += "FRAME 60 DEATHS 6\n"; // pending since frame 50, clamped to non-decreasing
		want += "FRAME 70 RECEIVED 0 8\nFRAME 70 RECEIVED 1 1\nFRAME 70 RECEIVED 2 42\n";
		if (role == "client") want += "FRAME 80 DEATHS 7\n";
		want += "FRAME 90 EMPEROR\n";
		want += "FRAME 100 DEATHLINK 2\nFRAME 100 CHECKED " + std::string(nameB) + "\n";
		const std::string got = slurp(run / "mirror-events.txt");
		CHECK(got == want, "mirror-events.txt exact bytes");
		if (got != want) std::printf("--- want\n%s--- got\n%s---\n", want.c_str(), got.c_str());
		CHECK(got.find('\r') == std::string::npos, "mirror-events.txt has no CR");
		for (const char* f : { "checks.txt", "deaths.txt", "emperor.txt", "emperor.tmp", "benefits-used.txt" })
			CHECK(!fs::exists(run / f), "client writes no journal");
		CHECK(!fs::exists(sess / "campaign" / "p2-delivery-receipts.txt"), "client never opens the P2 ledger");
		CHECK(gLedgerSent.empty(), "client sends no ledger");
	}
	if (gFailures) {
		std::printf("pc_randomizer_outbox_io_test %s: %d FAILED\n", role.c_str(), gFailures);
		return 1;
	}
	std::printf("pc_randomizer_outbox_io_test %s: PASS\n", role.c_str());
	fs::remove_all(root, ec); // best effort; the folder name is unique per process
	return 0;
}
