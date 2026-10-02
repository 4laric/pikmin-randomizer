// Netplay M4 lane B1 (issue #885): see pc_randomizer_outbox.h.
#include "pc_randomizer_outbox.h"

#include <cstdio>
#include <cstring>
#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace pc_rand_outbox {

bool Queue::push(const Entry& e)
{
	if (mEntries.size() >= kMaxEntries) return false;
	mEntries.push_back(e);
	return true;
}

void Queue::take(std::vector<Entry>& out)
{
	out.clear();
	out.swap(mEntries);
}

// ---- mirror lines ----
namespace {

std::string frame_prefix(uint32_t frame)
{
	char buf[32];
	std::snprintf(buf, sizeof(buf), "FRAME %lu ", (unsigned long)frame);
	return buf;
}

std::string finish(std::string line)
{
	if (line.empty() || line.size() > kMaxLineLen) return std::string();
	for (char c : line) {
		const unsigned char u = (unsigned char)c;
		if (u < 0x20 || u > 0x7E) return std::string();
	}
	return line;
}

} // namespace

bool mirror_name_ok(const char* name)
{
	if (name == nullptr) return false;
	const size_t n = std::strlen(name);
	if (n == 0 || n > kMaxNameLen) return false;
	if (name[0] == ' ' || name[n - 1] == ' ') return false;
	for (size_t i = 0; i < n; ++i) {
		const unsigned char u = (unsigned char)name[i];
		if (u < 0x20 || u > 0x7E) return false;
		if (u == ' ' && i + 1 < n && name[i + 1] == ' ') return false;
	}
	return true;
}

std::string mirror_checked(uint32_t frame, const char* name)
{
	if (!mirror_name_ok(name)) return std::string();
	return finish(frame_prefix(frame) + "CHECKED " + name);
}

std::string mirror_deaths(uint32_t frame, uint32_t total)
{
	if (total > kMaxTotal) return std::string();
	char buf[48];
	std::snprintf(buf, sizeof(buf), "DEATHS %lu", (unsigned long)total);
	return finish(frame_prefix(frame) + buf);
}

std::string mirror_deathlink(uint32_t frame, uint32_t total)
{
	// Full uint32 DeathLink inventory; ordinary DEATHS retains kMaxTotal.
	char buf[48];
	std::snprintf(buf, sizeof(buf), "DEATHLINK %lu", (unsigned long)total);
	return finish(frame_prefix(frame) + buf);
}

std::string mirror_emperor(uint32_t frame) { return finish(frame_prefix(frame) + "EMPEROR"); }

std::string mirror_received(uint32_t frame, uint32_t index, uint32_t itemId)
{
	if (index > kMaxReceiveIndex || itemId > kMaxItemId) return std::string();
	char buf[64];
	std::snprintf(buf, sizeof(buf), "RECEIVED %lu %lu", (unsigned long)index, (unsigned long)itemId);
	return finish(frame_prefix(frame) + buf);
}

std::string mirror_save_result(uint32_t frame, unsigned long long gen, const char* shaHex)
{
	if (gen == 0 || shaHex == nullptr || std::strlen(shaHex) != 64) return std::string();
	for (size_t i = 0; i < 64; ++i) {
		const char c = shaHex[i];
		if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return std::string();
	}
	char buf[128];
	std::snprintf(buf, sizeof(buf), "SAVE_RESULT %llu %s", gen, shaHex);
	return finish(frame_prefix(frame) + buf);
}

std::string mirror_save_fail(uint32_t frame, unsigned long long gen)
{
	if (gen == 0) return std::string();
	char buf[48];
	std::snprintf(buf, sizeof(buf), "SAVE_FAIL %llu", gen);
	return finish(frame_prefix(frame) + buf);
}

// ---- session.json scanner ----
namespace {

constexpr int kMaxDepth = 32;

struct Scanner {
	const char* p;
	const char* end;
	std::string reason;

	bool fail(const char* why)
	{
		if (reason.empty()) reason = why;
		return false;
	}
	void ws()
	{
		while (p < end && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')) ++p;
	}
	bool lit(const char* word)
	{
		const size_t n = std::strlen(word);
		if ((size_t)(end - p) < n || std::memcmp(p, word, n) != 0) return fail("bad literal");
		p += n;
		return true;
	}
	// Parses a JSON string; stores the decoded ASCII text in `out` when
	// non-null (non-ASCII escapes are kept as '?', which only matters for
	// key comparison and never matches the extracted keys).
	bool string(std::string* out)
	{
		if (p >= end || *p != '"') return fail("expected string");
		++p;
		for (;;) {
			if (p >= end) return fail("unterminated string");
			const unsigned char c = (unsigned char)*p++;
			if (c == '"') return true;
			if (c < 0x20) return fail("control byte in string");
			if (c != '\\') {
				if (out) out->push_back((char)c);
				continue;
			}
			if (p >= end) return fail("bad escape");
			const char e = *p++;
			switch (e) {
			case '"': case '\\': case '/':
				if (out) out->push_back(e);
				break;
			case 'b': case 'f': case 'n': case 'r': case 't':
				if (out) out->push_back('?');
				break;
			case 'u': {
				if (end - p < 4) return fail("bad unicode escape");
				unsigned v = 0;
				for (int i = 0; i < 4; ++i) {
					const char h = *p++;
					v <<= 4;
					if (h >= '0' && h <= '9') v |= (unsigned)(h - '0');
					else if (h >= 'a' && h <= 'f') v |= (unsigned)(h - 'a' + 10);
					else if (h >= 'A' && h <= 'F') v |= (unsigned)(h - 'A' + 10);
					else return fail("bad unicode escape");
				}
				if (out) out->push_back(v >= 0x20 && v < 0x7F ? (char)v : '?');
				break;
			}
			default:
				return fail("bad escape");
			}
		}
	}
	// Parses a JSON number. When `value` is non-null the number must be a
	// canonical non-negative integer that fits `limit`.
	bool number(uint64_t* value, uint64_t limit)
	{
		const char* start = p;
		bool neg = false, frac = false;
		if (p < end && *p == '-') { neg = true; ++p; }
		if (p >= end || !(*p >= '0' && *p <= '9')) return fail("bad number");
		if (*p == '0') {
			++p;
		} else {
			while (p < end && *p >= '0' && *p <= '9') ++p;
		}
		if (p < end && *p == '.') {
			frac = true;
			++p;
			if (p >= end || !(*p >= '0' && *p <= '9')) return fail("bad number");
			while (p < end && *p >= '0' && *p <= '9') ++p;
		}
		if (p < end && (*p == 'e' || *p == 'E')) {
			frac = true;
			++p;
			if (p < end && (*p == '+' || *p == '-')) ++p;
			if (p >= end || !(*p >= '0' && *p <= '9')) return fail("bad number");
			while (p < end && *p >= '0' && *p <= '9') ++p;
		}
		if (value == nullptr) return true;
		if (neg || frac) return fail("expected a non-negative integer");
		if (p - start > 12) return fail("integer out of range");
		uint64_t v = 0;
		for (const char* q = start; q < p; ++q) v = v * 10 + (uint64_t)(*q - '0');
		if (v > limit) return fail("integer out of range");
		*value = v;
		return true;
	}
	bool value(int depth)
	{
		if (depth > kMaxDepth) return fail("nesting too deep");
		ws();
		if (p >= end) return fail("unexpected end");
		const char c = *p;
		if (c == '{') return object(depth + 1, nullptr);
		if (c == '[') {
			++p;
			ws();
			if (p < end && *p == ']') { ++p; return true; }
			for (;;) {
				if (!value(depth + 1)) return false;
				ws();
				if (p < end && *p == ',') { ++p; continue; }
				if (p < end && *p == ']') { ++p; return true; }
				return fail("bad array");
			}
		}
		if (c == '"') return string(nullptr);
		if (c == 't') return lit("true");
		if (c == 'f') return lit("false");
		if (c == 'n') return lit("null");
		return number(nullptr, 0);
	}
	bool int_array(std::vector<uint32_t>& out)
	{
		ws();
		if (p >= end || *p != '[') return fail("received is not an array");
		++p;
		ws();
		if (p < end && *p == ']') { ++p; return true; }
		for (;;) {
			ws();
			uint64_t v = 0;
			if (!number(&v, kMaxItemId)) return fail("received holds a non item id");
			if (out.size() >= kMaxReceiveIndex) return fail("received is too long");
			out.push_back((uint32_t)v);
			ws();
			if (p < end && *p == ',') { ++p; continue; }
			if (p < end && *p == ']') { ++p; return true; }
			return fail("bad received array");
		}
	}
	// Top-level object when `ledger` is non-null: extracts the two keys.
	bool object(int depth, SessionLedger* ledger)
	{
		if (depth > kMaxDepth) return fail("nesting too deep");
		ws();
		if (p >= end || *p != '{') return fail("expected object");
		++p;
		ws();
		bool haveReceived = false;
		if (p < end && *p == '}') {
			++p;
			if (ledger != nullptr) return fail("missing received");
			return true;
		}
		for (;;) {
			ws();
			std::string key;
			if (!string(&key)) return false;
			ws();
			if (p >= end || *p != ':') return fail("expected colon");
			++p;
			ws();
			if (ledger != nullptr && key == "received") {
				if (haveReceived) return fail("duplicate received");
				haveReceived = true;
				if (!int_array(ledger->received)) return false;
			} else if (ledger != nullptr && key == "pikmin_deaths") {
				if (ledger->haveDeaths) return fail("duplicate pikmin_deaths");
				uint64_t v = 0;
				if (!number(&v, kMaxTotal)) return fail("bad pikmin_deaths");
				ledger->pikminDeaths = (uint32_t)v;
				ledger->haveDeaths = true;
			} else if (!value(depth)) {
				return false;
			}
			ws();
			if (p < end && *p == ',') { ++p; continue; }
			if (p < end && *p == '}') { ++p; break; }
			return fail("bad object");
		}
		if (ledger != nullptr && !haveReceived) return fail("missing received");
		return true;
	}
};

void put32(std::vector<uint8_t>& v, uint32_t x)
{
	v.push_back((uint8_t)(x & 0xFF));
	v.push_back((uint8_t)((x >> 8) & 0xFF));
	v.push_back((uint8_t)((x >> 16) & 0xFF));
	v.push_back((uint8_t)((x >> 24) & 0xFF));
}

uint32_t get32(const uint8_t* p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

} // namespace

bool scan_session_json(const char* data, size_t len, SessionLedger& out, std::string& reason)
{
	out = SessionLedger();
	reason.clear();
	if (data == nullptr || len == 0) {
		reason = "empty";
		return false;
	}
	if (len > kMaxSessionJson) {
		reason = "too large";
		return false;
	}
	Scanner s{ data, data + len, std::string() };
	SessionLedger ledger;
	if (!s.object(1, &ledger)) {
		reason = s.reason.empty() ? "malformed" : s.reason;
		return false;
	}
	s.ws();
	if (s.p != s.end) {
		reason = "trailing data";
		return false;
	}
	out = std::move(ledger);
	return true;
}

std::vector<uint8_t> encode_ledger(uint32_t deathsBase, uint32_t firstIndex, const uint32_t* ids,
                                   uint32_t count)
{
	std::vector<uint8_t> out;
	if (count > kLedgerMaxCount || (count > 0 && ids == nullptr)) return out;
	out.reserve(12 + 4 * (size_t)count);
	put32(out, deathsBase);
	put32(out, firstIndex);
	put32(out, count);
	for (uint32_t i = 0; i < count; ++i) put32(out, ids[i]);
	return out;
}

bool decode_ledger(const uint8_t* data, size_t len, LedgerMsg& out)
{
	if (data == nullptr || len < 12) return false;
	const uint32_t deathsBase = get32(data);
	const uint32_t firstIndex = get32(data + 4);
	const uint32_t count = get32(data + 8);
	if (count > kLedgerMaxCount) return false;
	if (len != 12 + 4 * (size_t)count) return false;
	if (deathsBase > kMaxTotal && deathsBase != kLedgerBaseUnknown) return false;
	if ((uint64_t)firstIndex + count > (uint64_t)kMaxReceiveIndex) return false;
	std::vector<uint32_t> ids;
	ids.reserve(count);
	for (uint32_t i = 0; i < count; ++i) {
		const uint32_t id = get32(data + 12 + 4 * (size_t)i);
		if (id > kMaxItemId) return false;
		ids.push_back(id);
	}
	out.deathsBase = deathsBase;
	out.firstIndex = firstIndex;
	out.ids = std::move(ids);
	return true;
}

bool ReceivedSequencer::offer(uint32_t firstIndex, const std::vector<uint32_t>& ids,
                              std::vector<std::pair<uint32_t, uint32_t>>& out)
{
	out.clear();
	bool accepted = true;
	const uint64_t endIndex = (uint64_t)firstIndex + ids.size();
	if (!ids.empty() && endIndex > mNext) {
		auto it = mHeld.find(firstIndex);
		if (it != mHeld.end()) {
			if (ids.size() > it->second.size()) it->second = ids; // keep the longer copy
		} else if (mHeld.size() >= kMaxHeld) {
			accepted = false;
		} else {
			mHeld.emplace(firstIndex, ids);
		}
	}
	bool progress = true;
	while (progress) {
		progress = false;
		for (auto it = mHeld.begin(); it != mHeld.end();) {
			const uint64_t first = it->first;
			const uint64_t last = first + it->second.size(); // exclusive
			if (last <= mNext) {
				it = mHeld.erase(it); // fully written already
				continue;
			}
			if (first <= mNext) {
				for (uint64_t idx = mNext; idx < last; ++idx)
					out.emplace_back((uint32_t)idx, it->second[(size_t)(idx - first)]);
				mNext = (uint32_t)last;
				it = mHeld.erase(it);
				progress = true;
				continue;
			}
			++it; // gap: wait for the missing message
		}
	}
	return accepted;
}

bool file_write_stamp(const std::filesystem::path& path, uint64_t* out)
{
	if (out == nullptr) return false;
#ifdef _WIN32
	WIN32_FILE_ATTRIBUTE_DATA data;
	if (!GetFileAttributesExW(path.wstring().c_str(), GetFileExInfoStandard, &data)) return false;
	*out = ((uint64_t)data.ftLastWriteTime.dwHighDateTime << 32) | (uint64_t)data.ftLastWriteTime.dwLowDateTime;
	return true;
#else
	std::error_code ec;
	const auto t = std::filesystem::last_write_time(path, ec);
	if (ec) return false;
	*out = (uint64_t)t.time_since_epoch().count();
	return true;
#endif
}

} // namespace pc_rand_outbox
