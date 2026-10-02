#pragma once
// Netplay M4 lane B1 (issue #885): confirmed-frame outbox for the randomizer's
// external writes, the client mirror line grammar, the session.json ledger
// scanner and the kBulkMirrorLedger codec.
//
// Engine-free (only the C++ standard library), so pc_randomizer_outbox_test
// links it without the game. pc_randomizer.cpp owns the sim-side pushes and
// the actual file I/O; this module holds the queue, formats mirror lines,
// parses session.json and encodes/decodes the bulk ledger message.
//
// Outbox model (M4 plan section 3). While a netplay session runs with the
// external-state stream on, every external write site makes its sim-side
// change immediately and identically on both peers, then pushes an Entry
// here instead of touching a file. pc_randomizer_outbox_flush(frame) runs
// once per Advance, after the state hash: the host writes each entry with its
// legacy format and durability (checks.txt, benefits-used.txt, emperor.txt,
// deaths.txt, the P2 delivery ledger); the client writes no journal and turns
// the entries into mirror-events.txt lines instead. Each Entry carries the
// frame of the Advance that pushed it (Entry::frame, stamped at push time
// from the session's current Advance frame), so a flush from anywhere (the
// per-Advance flush, or the campaign save inside a tick) writes every
// mirror line with its own event frame.
//
// mirror-events.txt grammar (root randomizer/netplay_mirror.py
// parse_mirror_line is the reference parser): printable ASCII, one event per
// line, 1..256 bytes, '\n' terminated, single spaces, canonical decimals.
//   FRAME <frame> RECEIVED <index> <item_id>
//   FRAME <frame> CHECKED <location>
//   FRAME <frame> DEATHS <total>
//   FRAME <frame> DEATHLINK <total>
//   FRAME <frame> EMPEROR
//   FRAME <frame> SAVE_RESULT <gen> <digest>
//   FRAME <frame> SAVE_FAIL <gen>
// Every formatter below returns the line WITHOUT the '\n' terminator, or an
// empty string when an argument cannot be expressed in the grammar.

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace pc_rand_outbox {

enum class Kind : uint8_t {
	Check,          // native collection: host checks.txt line, client CHECKED
	CheckApplied,   // streamed CHECKS apply added a slot: client CHECKED only
	Benefit,        // benefit consumed: host benefits-used.txt line only
	Emperor,        // native Emperor defeat: host emperor.txt, client EMPEROR
	EmperorApplied, // streamed EMPEROR latch: client EMPEROR only
	Death,          // ordinary Pikmin death: host deaths.txt, client DEATHS
	DeathLink,      // applied DeathLink total rose: client DEATHLINK only
	P2Delivery,     // bound P2 corpse delivered: host ledger deliver only
};

struct Entry {
	Kind kind = Kind::Check;
	uint32_t slot = 0;       // Check / CheckApplied
	int32_t benefitKind = 0; // Benefit
	uint32_t count = 0;      // Benefit (consumed count after this use)
	uint32_t total = 0;      // Death (run total) / DeathLink (session total)
	uint32_t p2Source = 0;   // P2Delivery
	int32_t p2Type = 0;
	int32_t p2Stage = 0;
	uint32_t p2Generator = 0;
	uint32_t frame = 0;      // Advance frame of the push (mirror line frame)
};

// Bounded FIFO. The sim pushes at most a handful of entries per tick; a
// flush drains everything. The bound only guards against a runaway producer
// (a push past it is reported by the caller as a fatal fail()).
class Queue {
public:
	static constexpr size_t kMaxEntries = 65536;
	bool push(const Entry& e);
	void take(std::vector<Entry>& out);
	size_t size() const { return mEntries.size(); }
	void clear() { mEntries.clear(); }

private:
	std::vector<Entry> mEntries;
};

// ---- mirror-events.txt line formatting ----
constexpr size_t kMaxLineLen = 256;
constexpr size_t kMaxNameLen = 128;
constexpr uint32_t kMaxReceiveIndex = 10000000;
constexpr uint32_t kMaxItemId = 2147483647u;
constexpr uint32_t kMaxTotal = 1000000;

// True when `name` can be a CHECKED location: 1..128 printable ASCII bytes
// (0x20..0x7E), no leading/trailing space and no double space (the reference
// parser splits on single spaces and rejects empty parts).
bool mirror_name_ok(const char* name);
std::string mirror_checked(uint32_t frame, const char* name);
std::string mirror_deaths(uint32_t frame, uint32_t total);
std::string mirror_deathlink(uint32_t frame, uint32_t total);
std::string mirror_emperor(uint32_t frame);
std::string mirror_received(uint32_t frame, uint32_t index, uint32_t itemId);
// gen 1..18446744073709551615; sha_hex exactly 64 lowercase hex characters.
std::string mirror_save_result(uint32_t frame, unsigned long long gen, const char* shaHex);
std::string mirror_save_fail(uint32_t frame, unsigned long long gen);

// ---- session.json ledger scanner ----
// Strict minimal JSON reader for the runner's session.json (root
// randomizer/session.py writes it with json.dumps(indent=2)). It validates
// the whole document as JSON (objects, arrays, strings with escapes,
// numbers, true/false/null; depth <= 32; size <= kMaxSessionJson) and
// extracts only two top-level keys:
//   "received": [int, ...]   required; each 0..kMaxItemId, at most
//                            kMaxReceiveIndex entries
//   "pikmin_deaths": int     optional (absent -> 0, haveDeaths false);
//                            0..kMaxTotal
// Anything else is skipped. Returns false with a short reason on any
// malformed input, duplicate extracted key or out-of-range value.
constexpr size_t kMaxSessionJson = 8u * 1024u * 1024u;
struct SessionLedger {
	std::vector<uint32_t> received;
	uint32_t pikminDeaths = 0;
	bool haveDeaths = false;
};
bool scan_session_json(const char* data, size_t len, SessionLedger& out, std::string& reason);

// ---- kBulkMirrorLedger (bulk type 0x14) codec ----
// Little-endian: u32 deathsBase, u32 firstIndex, u32 count (<= 4096),
// count x u32 item id. The length is exactly 12 + 4 * count; every bound is
// checked before any allocation.
constexpr uint8_t kBulkMirrorLedger = 0x14;
constexpr uint32_t kLedgerMaxCount = 4096;
// deathsBase value meaning "the host could not establish the base": the
// runner's session.json existed at session start but could not be read, so
// any base the host learns later may already include this run's credited
// deaths. The client then writes no DEATHS lines at all (a wrong absolute
// total would be an over-count or a fatal retraction for the M4c runner).
constexpr uint32_t kLedgerBaseUnknown = 0xFFFFFFFFu;
struct LedgerMsg {
	uint32_t deathsBase = 0;
	uint32_t firstIndex = 0;
	std::vector<uint32_t> ids;
};
std::vector<uint8_t> encode_ledger(uint32_t deathsBase, uint32_t firstIndex, const uint32_t* ids,
                                   uint32_t count);
bool decode_ledger(const uint8_t* data, size_t len, LedgerMsg& out);

// Client RECEIVED sequencer. Bulk delivery is unordered, so a ledger message
// may arrive before the one that precedes it. offer() stores the message,
// then emits every receipt that continues the written sequence without a
// gap (index order, starting at 0). Indices already written are ignored; a
// message that would leave a gap is held until the missing one arrives
// (at most kMaxHeld held messages; beyond that the newest is dropped and
// offer() returns false).
class ReceivedSequencer {
public:
	static constexpr size_t kMaxHeld = 64;
	bool offer(uint32_t firstIndex, const std::vector<uint32_t>& ids,
	           std::vector<std::pair<uint32_t, uint32_t>>& out);
	uint32_t next_index() const { return mNext; }
	size_t held() const { return mHeld.size(); }
	void reset()
	{
		mNext = 0;
		mHeld.clear();
	}

private:
	uint32_t mNext = 0;
	std::map<uint32_t, std::vector<uint32_t>> mHeld; // firstIndex -> ids
};

// ---- stream-host state.txt change stamp ----
// The stream host must notice every state.txt rewrite. libstdc++ on MinGW
// implements std::filesystem::last_write_time through stat (whole seconds),
// so two rewrites inside one second looked identical and the second was
// only seen at the next rewrite in a later second (or never, for a writer
// that rewrites only on change); back-to-back changes coalesced into one
// generation. On Windows this reads the 100 ns FILETIME last-write time
// (GetFileAttributesExW); elsewhere it falls back to last_write_time.
// Returns false when the file cannot be stat'ed (missing).
bool file_write_stamp(const std::filesystem::path& path, uint64_t* out);

} // namespace pc_rand_outbox
