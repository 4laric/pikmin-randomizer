// Netplay M4 lane B1 (issue #885): engine-free unit test for the randomizer
// outbox module: queue order, mirror-events.txt line grammar (checked
// against the root randomizer/netplay_mirror.py parse_mirror_line rules),
// the session.json ledger scanner on real json.dumps(indent=2) output, the
// kBulkMirrorLedger codec bounds and the client RECEIVED sequencer.

#include "pc_randomizer_outbox.h"

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <thread>
#include <string>
#include <utility>
#include <vector>

namespace {

int sFailures = 0;

#define CHECK(cond, what)                                                        \
	do {                                                                         \
		if (!(cond)) {                                                           \
			std::printf("FAIL: %s (%s:%d)\n", what, __FILE__, __LINE__);         \
			++sFailures;                                                         \
		}                                                                        \
	} while (0)

// Mirrors parse_mirror_line's line-level rules: 1..256 printable ASCII,
// single-space separated, "FRAME <canonical u32> <TAG> ...".
bool grammar_ok(const std::string& line)
{
	if (line.empty() || line.size() > 256) return false;
	for (char c : line) {
		const unsigned char u = (unsigned char)c;
		if (u < 0x20 || u > 0x7E) return false;
	}
	if (line.front() == ' ' || line.back() == ' ' || line.find("  ") != std::string::npos) return false;
	if (line.compare(0, 6, "FRAME ") != 0) return false;
	const size_t sp = line.find(' ', 6);
	if (sp == std::string::npos) return false;
	const std::string frame = line.substr(6, sp - 6);
	if (frame.empty() || frame.size() > 10) return false;
	if (frame.size() > 1 && frame[0] == '0') return false;
	for (char c : frame)
		if (c < '0' || c > '9') return false;
	return true;
}

// Real json.dumps(obj, indent=2) + "\n" output (root randomizer/session.py
// Session.save), generated with Python 3.12.
const char kJsonSolo[] = R"JSON({
  "schema": 1,
  "fingerprint": "abababababababababababababababababababababababababababababababab",
  "checked": [],
  "received": [],
  "ap_identity": null
}
)JSON";

const char kJsonAp[] = R"JSON({
  "schema": 1,
  "fingerprint": "cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd",
  "checked": [
    "Pikmin: Bowsprit",
    "Population: 20 total Red Pikmin",
    "Weird \"quoted\" café \\ name"
  ],
  "received": [
    8,
    1,
    1,
    42,
    2147483647,
    0
  ],
  "ap_identity": {
    "seed_name": "X1",
    "slot": 1,
    "team": 0,
    "nested": {
      "received": [
        999
      ]
    }
  },
  "pikmin_deaths": 7,
  "death_links_received": 3
}
)JSON";

bool scan(const std::string& text, pc_rand_outbox::SessionLedger& out, std::string& reason)
{
	return pc_rand_outbox::scan_session_json(text.data(), text.size(), out, reason);
}

} // namespace

int main()
{
	using namespace pc_rand_outbox;

	// 1. Queue keeps push order and drains completely.
	{
		Queue q;
		for (uint32_t i = 0; i < 5; ++i) {
			Entry e;
			e.kind = (i % 2) ? Kind::Death : Kind::Check;
			e.slot = i;
			e.total = 100 + i;
			CHECK(q.push(e), "push");
		}
		std::vector<Entry> got;
		q.take(got);
		CHECK(got.size() == 5 && q.size() == 0, "take drains");
		bool order = true;
		for (uint32_t i = 0; i < got.size(); ++i) order = order && got[i].slot == i && got[i].total == 100 + i;
		CHECK(order, "push order preserved");
		q.take(got);
		CHECK(got.empty(), "second take empty");
	}

	// 2. Mirror line formatting follows the root grammar exactly.
	{
		CHECK(mirror_checked(0, "Pikmin: Bowsprit") == "FRAME 0 CHECKED Pikmin: Bowsprit", "CHECKED line");
		CHECK(mirror_checked(4294967295u, "Population: 20 total Red Pikmin")
		          == "FRAME 4294967295 CHECKED Population: 20 total Red Pikmin",
		      "CHECKED max frame");
		CHECK(mirror_deaths(17, 0) == "FRAME 17 DEATHS 0", "DEATHS 0 canonical");
		CHECK(mirror_deaths(17, 1000000) == "FRAME 17 DEATHS 1000000", "DEATHS max");
		CHECK(mirror_deaths(17, 1000001).empty(), "DEATHS over range rejected");
		CHECK(mirror_deathlink(32, 3) == "FRAME 32 DEATHLINK 3", "DEATHLINK line");
		CHECK(mirror_deathlink(32, UINT32_MAX) == "FRAME 32 DEATHLINK 4294967295", "DEATHLINK uint32 maximum");
		CHECK(mirror_deathlink(32, 0x01020304) == "FRAME 32 DEATHLINK 16909060", "expanded DeathLink inventory reaches mirror");
		CHECK(mirror_emperor(99) == "FRAME 99 EMPEROR", "EMPEROR line");
		CHECK(mirror_received(40, 0, 8) == "FRAME 40 RECEIVED 0 8", "RECEIVED line");
		CHECK(mirror_received(40, 10000000, 2147483647u) == "FRAME 40 RECEIVED 10000000 2147483647",
		      "RECEIVED max");
		CHECK(mirror_received(40, 10000001, 1).empty(), "RECEIVED index over range");
		CHECK(mirror_received(40, 1, 2147483648u).empty(), "RECEIVED item over range");
		const char* sha = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
		CHECK(mirror_save_result(7, 18446744073709551615ull, sha)
		          == std::string("FRAME 7 SAVE_RESULT 18446744073709551615 ") + sha,
		      "SAVE_RESULT line");
		CHECK(mirror_save_result(7, 0, sha).empty(), "SAVE_RESULT gen 0 rejected");
		CHECK(mirror_save_result(7, 1, "0123456789ABCDEF0123456789abcdef0123456789abcdef0123456789abcdef").empty(),
		      "SAVE_RESULT uppercase digest rejected");
		CHECK(mirror_save_result(7, 1, "abc").empty(), "SAVE_RESULT short digest rejected");
		CHECK(mirror_save_fail(7, 2) == "FRAME 7 SAVE_FAIL 2", "SAVE_FAIL line");
		CHECK(mirror_save_fail(7, 0).empty(), "SAVE_FAIL gen 0 rejected");
		const std::string all[] = { mirror_checked(1, "A b"), mirror_deaths(2, 5), mirror_deathlink(3, 1),
		                            mirror_emperor(4), mirror_received(5, 2, 3), mirror_save_result(6, 1, sha),
		                            mirror_save_fail(7, 1) };
		for (const std::string& l : all) CHECK(grammar_ok(l), "every formatter obeys the line grammar");
		// Names: 1..128 printable ASCII, no edge or double spaces.
		CHECK(mirror_name_ok("x"), "1-char name ok");
		CHECK(!mirror_name_ok(""), "empty name rejected");
		CHECK(!mirror_name_ok(nullptr), "null name rejected");
		CHECK(!mirror_name_ok(" lead"), "leading space rejected");
		CHECK(!mirror_name_ok("trail "), "trailing space rejected");
		CHECK(!mirror_name_ok("double  space"), "double space rejected");
		CHECK(!mirror_name_ok("tab\there"), "control byte rejected");
		CHECK(!mirror_name_ok("caf\xc3\xa9"), "non-ASCII rejected");
		std::string n128(128, 'a'), n129(129, 'a');
		CHECK(mirror_name_ok(n128.c_str()), "128-char name ok");
		CHECK(!mirror_name_ok(n129.c_str()), "129-char name rejected");
		CHECK(mirror_checked(1, n129.c_str()).empty(), "unexpressible CHECKED is empty");
		CHECK(grammar_ok(mirror_checked(4294967295u, n128.c_str())), "longest CHECKED line fits 256");
	}

	// 3. session.json scanner on real json.dumps(indent=2) output.
	{
		SessionLedger l;
		std::string reason;
		CHECK(scan(kJsonSolo, l, reason), "solo session.json parses");
		CHECK(l.received.empty() && !l.haveDeaths && l.pikminDeaths == 0, "solo: no receipts, no deaths key");
		CHECK(scan(kJsonAp, l, reason), "AP session.json parses");
		const std::vector<uint32_t> want = { 8, 1, 1, 42, 2147483647u, 0 };
		CHECK(l.received == want, "AP: received list in index order (nested received ignored)");
		CHECK(l.haveDeaths && l.pikminDeaths == 7, "AP: pikmin_deaths");
		// CRLF line endings and a missing trailing newline are still JSON.
		std::string crlf;
		for (const char* c = kJsonAp; *c; ++c) {
			if (*c == '\n') crlf += '\r';
			crlf += *c;
		}
		CHECK(scan(crlf, l, reason) && l.received.size() == 6, "CRLF whitespace accepted");
		// Rejections (each must fail with a reason, never crash).
		const char* bad[] = {
			"",
			"[]",
			"{}",
			"{\"received\": [1, 2}",
			"{\"received\": [1, -2]}",
			"{\"received\": [1.5]}",
			"{\"received\": [1e3]}",
			"{\"received\": [2147483648]}",
			"{\"received\": [01]}",
			"{\"received\": \"1\"}",
			"{\"received\": [1], \"received\": [2]}",
			"{\"received\": [], \"pikmin_deaths\": -1}",
			"{\"received\": [], \"pikmin_deaths\": 1000001}",
			"{\"received\": [], \"pikmin_deaths\": 1, \"pikmin_deaths\": 2}",
			"{\"received\": []} x",
			"{\"received\": [], \"s\": \"unterminated}",
			"{\"received\": [], \"s\": \"bad \\q escape\"}",
			"{\"received\": [], \"s\": \"ctl \x01 byte\"}",
			"{\"received\": [], \"n\": tru}",
			"{\"received\": [], \"a\": [1,]}",
			"{\"received\": [] \"a\": 1}",
		};
		for (const char* b : bad) {
			const bool ok = scan(b, l, reason);
			CHECK(!ok && !reason.empty(), "malformed session.json rejected with a reason");
			if (ok) std::printf("  unexpectedly accepted: %s\n", b);
		}
		// Depth bound: 40 nested arrays are refused, 20 are fine.
		std::string deep = "{\"received\": [], \"x\": ";
		for (int i = 0; i < 40; ++i) deep += '[';
		for (int i = 0; i < 40; ++i) deep += ']';
		deep += '}';
		CHECK(!scan(deep, l, reason), "nesting deeper than 32 rejected");
		std::string ok20 = "{\"received\": [3], \"x\": ";
		for (int i = 0; i < 20; ++i) ok20 += '[';
		for (int i = 0; i < 20; ++i) ok20 += ']';
		ok20 += '}';
		CHECK(scan(ok20, l, reason) && l.received.size() == 1, "20 levels accepted");
		// Other value kinds are skipped.
		CHECK(scan("{\"a\": {\"b\": [true, false, null, -1.5e-3, \"s\"]}, \"received\": [5]}", l, reason)
		          && l.received.size() == 1 && l.received[0] == 5,
		      "other values skipped");
		// Size bound.
		std::string huge(kMaxSessionJson + 1, ' ');
		CHECK(!scan(huge, l, reason) && reason == "too large", "oversize input rejected before parsing");
	}

	// 4. kBulkMirrorLedger codec: exact length, every bound checked.
	{
		const uint32_t ids[] = { 8, 1, 1, 42 };
		std::vector<uint8_t> m = encode_ledger(7, 3, ids, 4);
		CHECK(m.size() == 12 + 16, "ledger size 12 + 4 x count");
		CHECK(m[0] == 7 && m[4] == 3 && m[8] == 4 && m[12] == 8 && m[24] == 42, "ledger LE layout");
		LedgerMsg d;
		CHECK(decode_ledger(m.data(), m.size(), d), "ledger decodes");
		CHECK(d.deathsBase == 7 && d.firstIndex == 3 && d.ids.size() == 4 && d.ids[3] == 42, "ledger round trip");
		std::vector<uint8_t> empty = encode_ledger(0, 0, nullptr, 0);
		CHECK(empty.size() == 12 && decode_ledger(empty.data(), empty.size(), d) && d.ids.empty(),
		      "empty ledger (base only) round trip");
		CHECK(encode_ledger(0, 0, ids, kLedgerMaxCount + 1).empty(), "encode refuses count > 4096");
		std::vector<uint8_t> t = m;
		t.pop_back();
		CHECK(!decode_ledger(t.data(), t.size(), d), "short payload rejected");
		t = m;
		t.push_back(0);
		CHECK(!decode_ledger(t.data(), t.size(), d), "long payload rejected");
		t = m;
		t[8] = 0x01;
		t[9] = 0x10; // count 4097
		CHECK(!decode_ledger(t.data(), t.size(), d), "count > 4096 rejected before allocation");
		t = m;
		t[11] = 0xFF; // count huge
		CHECK(!decode_ledger(t.data(), t.size(), d), "huge count rejected");
		t = m;
		t[15] = 0x80; // item id 2^31 + 8
		CHECK(!decode_ledger(t.data(), t.size(), d), "item id > 2^31-1 rejected");
		t = m;
		t[3] = 0x01; // deathsBase huge
		CHECK(!decode_ledger(t.data(), t.size(), d), "deathsBase over range rejected");
		std::vector<uint8_t> unk = encode_ledger(kLedgerBaseUnknown, 0, nullptr, 0);
		CHECK(decode_ledger(unk.data(), unk.size(), d) && d.deathsBase == kLedgerBaseUnknown,
		      "deathsBase 'unknown' sentinel accepted");
		t = m;
		t[0] = 0xFE;
		t[1] = 0xFF;
		t[2] = 0xFF;
		t[3] = 0xFF; // 0xFFFFFFFE: over range and not the sentinel
		CHECK(!decode_ledger(t.data(), t.size(), d), "deathsBase just below the sentinel rejected");
		t = m;
		t[7] = 0x01; // firstIndex 16M
		CHECK(!decode_ledger(t.data(), t.size(), d), "firstIndex over range rejected");
		CHECK(!decode_ledger(nullptr, 0, d) && !decode_ledger(m.data(), 11, d), "truncated header rejected");
	}

	// 5. RECEIVED sequencer: in order, no gaps, duplicates ignored, gaps held.
	{
		ReceivedSequencer q;
		std::vector<std::pair<uint32_t, uint32_t>> out;
		CHECK(q.offer(0, {}, out) && out.empty(), "empty message writes nothing");
		CHECK(q.offer(3, { 30, 31 }, out) && out.empty() && q.held() == 1, "gap message held");
		CHECK(q.offer(0, { 10, 11, 12 }, out), "first message");
		CHECK(out.size() == 5 && out[0] == std::make_pair(0u, 10u) && out[2] == std::make_pair(2u, 12u)
		          && out[3] == std::make_pair(3u, 30u) && out[4] == std::make_pair(4u, 31u),
		      "held message released in index order");
		CHECK(q.next_index() == 5 && q.held() == 0, "cursor at 5");
		CHECK(q.offer(0, { 10, 11, 12 }, out) && out.empty(), "duplicate ignored");
		CHECK(q.offer(4, { 31, 40, 41 }, out) && out.size() == 2 && out[0] == std::make_pair(5u, 40u),
		      "overlap writes only new indices");
		CHECK(q.next_index() == 7, "cursor at 7");
		ReceivedSequencer full;
		bool dropped = false;
		for (uint32_t i = 0; i < ReceivedSequencer::kMaxHeld + 1; ++i)
			if (!full.offer(10 + 2 * i, { 1 }, out)) dropped = true;
		CHECK(dropped && full.held() == ReceivedSequencer::kMaxHeld, "held messages are bounded");
	}

	// 6. Stream-host change stamp: two rewrites 20 ms apart (inside one
	// second) must give different stamps; a missing file reports false.
	{
		namespace fs = std::filesystem;
		const fs::path f = fs::temp_directory_path()
		    / ("pc_randomizer_outbox_test_stamp_"
		       + std::to_string((unsigned long long)std::chrono::steady_clock::now().time_since_epoch().count())
		       + ".txt");
		uint64_t a = 0, b = 0;
		{
			std::ofstream o(f);
			o << "one";
		}
		CHECK(file_write_stamp(f, &a), "stamp of an existing file");
		std::this_thread::sleep_for(std::chrono::milliseconds(20));
		{
			std::ofstream o(f);
			o << "two";
		}
		CHECK(file_write_stamp(f, &b), "stamp after a rewrite");
		CHECK(a != b, "rewrites 20 ms apart get different stamps (sub-second resolution)");
		std::error_code ec;
		fs::remove(f, ec);
		CHECK(!file_write_stamp(f, &a), "missing file has no stamp");
	}

	if (sFailures == 0) std::printf("pc_randomizer_outbox_test: PASS\n");
	else std::printf("pc_randomizer_outbox_test: %d FAILURES\n", sFailures);
	return sFailures == 0 ? 0 : 1;
}
