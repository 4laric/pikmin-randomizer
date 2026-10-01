#include "pc_coop_policy.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>

// Netplay M4 D-policy (issue #885). See pc_coop_policy.h for the rules.

bool pc_coop_any_live(const PcCoopCaptain caps[PC_COOP_CAPTAINS])
{
	for (int i = 0; i < PC_COOP_CAPTAINS; ++i)
		if (caps[i].live) return true;
	return false;
}

PcCoopHealPick pc_coop_pick_heal(const PcCoopCaptain caps[PC_COOP_CAPTAINS],
                                 const float prevHp[PC_COOP_CAPTAINS],
                                 const bool prevValid[PC_COOP_CAPTAINS])
{
	PcCoopHealPick pick = { 0, PC_COOP_HEAL_NONE };
	int triggers = 0, trigger = -1, lowest = -1;
	for (int i = 0; i < PC_COOP_CAPTAINS; ++i) {
		const PcCoopCaptain& c = caps[i];
		if (!c.live || !(c.hp < c.maxHp)) continue; // downed or full: never healed
		if (prevValid[i] && c.hp < prevHp[i]) {
			++triggers;
			trigger = i;
		}
		// Strict less-than keeps the lower index on a tie.
		if (lowest < 0 || c.hp < caps[lowest].hp) lowest = i;
	}
	if (lowest < 0) return pick;
	if (triggers == 1) {
		pick.captain = caps[trigger].id;
		pick.reason  = PC_COOP_HEAL_TRIGGER;
	} else {
		pick.captain = caps[lowest].id;
		pick.reason  = PC_COOP_HEAL_LOWEST;
	}
	return pick;
}

const char* pc_coop_heal_reason_name(PcCoopHealReason reason)
{
	switch (reason) {
	case PC_COOP_HEAL_TRIGGER: return "trigger";
	case PC_COOP_HEAL_LOWEST: return "lowest";
	default: return "none";
	}
}

const char* pc_coop_anchor_name(PcCoopAnchorKind kind)
{
	switch (kind) {
	case PC_COOP_ANCHOR_BOMB_TRAP: return "BOMB_TRAP";
	case PC_COOP_ANCHOR_PROGG: return "PROGG";
	case PC_COOP_ANCHOR_PRERELEASE: return "PRERELEASE";
	case PC_COOP_ANCHOR_FLOWERS: return "FLOWERS";
	default: return "?";
	}
}

void pc_coop_cursors_reset(PcCoopCursors& cursors)
{
	for (int k = 0; k < PC_COOP_ANCHOR_COUNT; ++k) cursors.next[k] = 1;
}

static int other_captain(int captain) { return captain == 1 ? 2 : 1; }

static int clamp_captain(int captain) { return captain == 2 ? 2 : 1; }

int pc_coop_anchor_order(const PcCoopCursors& cursors, PcCoopAnchorKind kind,
                         const bool live[PC_COOP_CAPTAINS], int order[PC_COOP_CAPTAINS])
{
	if (kind < 0 || kind >= PC_COOP_ANCHOR_COUNT) return 0;
	const int first = clamp_captain(cursors.next[kind]);
	const int second = other_captain(first);
	int n = 0;
	if (live[first - 1]) order[n++] = first;
	if (live[second - 1]) order[n++] = second;
	return n;
}

int pc_coop_anchor_advance(PcCoopCursors& cursors, PcCoopAnchorKind kind, int succeeded)
{
	if (kind < 0 || kind >= PC_COOP_ANCHOR_COUNT) return 1;
	cursors.next[kind] = other_captain(clamp_captain(succeeded));
	return cursors.next[kind];
}

PcCoopAnchorAttempt pc_coop_anchor_try(PcCoopCursors& cursors, PcCoopAnchorKind kind,
                                       const bool live[PC_COOP_CAPTAINS], PcCoopPlaceFn place, void* ctx)
{
	PcCoopAnchorAttempt a;
	std::memset(&a, 0, sizeof(a));
	if (kind < 0 || kind >= PC_COOP_ANCHOR_COUNT || !place) return a;
	a.cursor = clamp_captain(cursors.next[kind]);
	a.next = a.cursor;
	if (!live[a.cursor - 1]) {
		a.skipCaptain[a.skipCount] = a.cursor;
		a.skipReason[a.skipCount++] = PC_COOP_SKIP_NOT_LIVE;
	}
	int order[PC_COOP_CAPTAINS];
	const int n = pc_coop_anchor_order(cursors, kind, live, order);
	for (int i = 0; i < n; ++i) {
		const PcCoopPlaceResult result = place(order[i], ctx);
		if (result == PC_COOP_PLACE_STOP) {
			a.captain = -1;
			return a;
		}
		if (result == PC_COOP_PLACE_CONSUMED) {
			a.captain = order[i];
			a.next = pc_coop_anchor_advance(cursors, kind, order[i]);
			return a;
		}
		if (a.skipCount < PC_COOP_CAPTAINS) {
			a.skipCaptain[a.skipCount] = order[i];
			a.skipReason[a.skipCount++] = PC_COOP_SKIP_PLACEMENT;
		}
	}
	return a;
}

const char* pc_coop_skip_reason_name(PcCoopSkipReason reason)
{
	switch (reason) {
	case PC_COOP_SKIP_NOT_LIVE: return "not-live";
	case PC_COOP_SKIP_PLACEMENT: return "placement";
	default: return "?";
	}
}

bool pc_coop_stage_changed(bool started, const PcCoopStageKey& prev, const PcCoopStageKey& cur, const char** reason)
{
	const char* why = nullptr;
	if (!started) why = "start";
	else if (cur.stage != prev.stage) why = "stage";
	else if (cur.day != prev.day) why = "day";
	else if (cur.timeOfDay < prev.timeOfDay) why = "clock";
	if (reason) *reason = why;
	return why != nullptr;
}

// Locale-independent unsigned decimal: digits only.
static bool parse_uint(const char*& p, unsigned& out)
{
	if (*p < '0' || *p > '9') return false;
	unsigned long long v = 0;
	while (*p >= '0' && *p <= '9') {
		v = v * 10 + unsigned(*p - '0');
		if (v > 0xFFFFFFFFull) return false;
		++p;
	}
	out = unsigned(v);
	return true;
}

// Locale-independent fraction in [0, 1]: `0`, `1`, `0.5`, `.25`, `1.0`.
static bool parse_fraction(const char*& p, float& out)
{
	unsigned whole = 0;
	bool digits = false;
	if (*p >= '0' && *p <= '9') {
		if (!parse_uint(p, whole)) return false;
		digits = true;
	}
	double v = double(whole);
	if (*p == '.') {
		++p;
		double scale = 0.1;
		while (*p >= '0' && *p <= '9') {
			v += scale * double(*p - '0');
			scale *= 0.1;
			digits = true;
			++p;
		}
	}
	if (!digits || v < 0.0 || v > 1.0) return false;
	out = float(v);
	return true;
}

static void skip_blanks(const char*& p)
{
	while (*p == ' ' || *p == '\t') ++p;
}

static bool at_line_end(const char* p) { return *p == '\0' || *p == '\n' || *p == '\r' || *p == '#'; }

static bool parse_word(const char*& p, const char* word)
{
	const size_t n = std::strlen(word);
	if (std::strncmp(p, word, n) != 0) return false;
	const char c = p[n];
	if (!(c == ' ' || c == '\t' || c == '\0' || c == '\n' || c == '\r' || c == '#')) return false;
	p += n;
	return true;
}

int pc_coop_events_parse(const char* text, PcCoopEvent* out, int max, int* badLine)
{
	if (badLine) *badLine = 0;
	if (!text) return 0;
	int count = 0, lineNo = 0;
	const char* p = text;
	while (*p) {
		++lineNo;
		const char* line = p;
		while (*p && *p != '\n') ++p;
		const char* next = *p ? p + 1 : p;
		const char* q = line;
		skip_blanks(q);
		if (!at_line_end(q)) {
			PcCoopEvent ev;
			std::memset(&ev, 0, sizeof(ev));
			// Ticks are 1-based: tick 0 would never fire, so it is rejected.
			bool ok = parse_uint(q, ev.tick) && ev.tick > 0;
			skip_blanks(q);
			if (ok && parse_word(q, "HP")) {
				ev.kind = PC_COOP_EVENT_HP;
				skip_blanks(q);
				unsigned cap = 0;
				ok = parse_uint(q, cap) && (cap == 1 || cap == 2);
				ev.captain = int(cap);
				skip_blanks(q);
				ok = ok && parse_fraction(q, ev.fraction);
				if (ok) std::snprintf(ev.text, sizeof(ev.text), "HP %d %.3f", ev.captain, double(ev.fraction));
			} else if (ok && parse_word(q, "DOWN")) {
				ev.kind = PC_COOP_EVENT_DOWN;
				skip_blanks(q);
				unsigned cap = 0;
				ok = parse_uint(q, cap) && (cap == 1 || cap == 2);
				ev.captain = int(cap);
				if (ok) std::snprintf(ev.text, sizeof(ev.text), "DOWN %d", ev.captain);
			} else if (ok && parse_word(q, "SQUAD")) {
				ev.kind = PC_COOP_EVENT_SQUAD;
				skip_blanks(q);
				unsigned cap = 0, n = 0;
				ok = parse_uint(q, cap) && (cap == 1 || cap == 2);
				ev.captain = int(cap);
				skip_blanks(q);
				ok = ok && parse_uint(q, n) && n >= 1 && n <= PC_COOP_EVENT_SQUAD_MAX;
				ev.count = int(n);
				if (ok) std::snprintf(ev.text, sizeof(ev.text), "SQUAD %d %d", ev.captain, ev.count);
			} else if (ok && parse_word(q, "DISMISS")) {
				ev.kind = PC_COOP_EVENT_DISMISS;
				skip_blanks(q);
				unsigned cap = 0;
				ok = parse_uint(q, cap) && (cap == 1 || cap == 2);
				ev.captain = int(cap);
				if (ok) std::snprintf(ev.text, sizeof(ev.text), "DISMISS %d", ev.captain);
			} else if (ok && parse_word(q, "HOME")) {
				ev.kind = PC_COOP_EVENT_HOME;
				skip_blanks(q);
				unsigned cap = 0;
				ok = parse_uint(q, cap) && (cap == 1 || cap == 2);
				ev.captain = int(cap);
				if (ok) std::snprintf(ev.text, sizeof(ev.text), "HOME %d", ev.captain);
			} else if (ok && parse_word(q, "SUNSET")) {
				ev.kind = PC_COOP_EVENT_SUNSET;
				std::snprintf(ev.text, sizeof(ev.text), "SUNSET");
			} else {
				ok = false;
			}
			skip_blanks(q);
			if (!ok || !at_line_end(q) || count >= max) {
				if (badLine) *badLine = lineNo;
				return -1;
			}
			out[count++] = ev;
		}
		p = next;
	}
	return count;
}

int pc_coop_events_load(const char* path, PcCoopEvent* out, int max, const char** why, int* badLine)
{
	if (why) *why = nullptr;
	if (badLine) *badLine = 0;
	FILE* file = path ? std::fopen(path, "rb") : nullptr;
	if (!file) {
		if (why) *why = "unreadable";
		return -1;
	}
	// One byte past the limit tells "exactly at the limit" from "too large".
	static char text[PC_COOP_EVENTS_FILE_MAX + 2];
	const size_t got = std::fread(text, 1, PC_COOP_EVENTS_FILE_MAX + 1, file);
	std::fclose(file);
	if (got > PC_COOP_EVENTS_FILE_MAX) {
		if (why) *why = "too-large";
		return -1;
	}
	text[got] = '\0';
	if (std::memchr(text, '\0', got)) {
		if (why) *why = "bad-line";
		return -1;
	}
	const int count = pc_coop_events_parse(text, out, max, badLine);
	if (count < 0 && why) *why = "bad-line";
	return count;
}

const char* pc_coop_events_knob_path()
{
#if defined(PIKI_NETPLAY_BUILD) && PIKI_NETPLAY_BUILD
	const char* background = std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND");
	if (!background || std::strcmp(background, "1") != 0) return nullptr;
	const char* path = std::getenv("PIKMIN_NETPLAY_TEST_COOP_EVENTS");
	return path && *path ? path : nullptr;
#else
	return nullptr;
#endif
}

// Netplay gapfix C (issue #885): config and state hashes, perturb knob.
namespace {
constexpr uint64_t kCoopFnvOffset = 14695981039346656037ULL;
constexpr uint64_t kCoopFnvPrime = 1099511628211ULL;

void coop_fnv(uint64_t& h, const void* data, size_t len)
{
	const unsigned char* p = static_cast<const unsigned char*>(data);
	for (size_t i = 0; i < len; ++i) {
		h ^= p[i];
		h *= kCoopFnvPrime;
	}
}

void coop_fnv_u32(uint64_t& h, uint32_t v)
{
	unsigned char b[4];
	for (int i = 0; i < 4; ++i) b[i] = static_cast<unsigned char>((v >> (i * 8)) & 0xFF);
	coop_fnv(h, b, 4);
}

void coop_fnv_f32(uint64_t& h, float v)
{
	uint32_t bits = 0;
	std::memcpy(&bits, &v, sizeof(bits));
	coop_fnv_u32(h, bits);
}
} // namespace

uint64_t pc_coop_events_file_hash(const char* path)
{
	if (!path) return 0;
	uint64_t h = kCoopFnvOffset;
	FILE* file = std::fopen(path, "rb");
	if (!file) return h;
	unsigned char chunk[4096];
	size_t got = 0;
	while ((got = std::fread(chunk, 1, sizeof(chunk), file)) > 0) coop_fnv(h, chunk, got);
	std::fclose(file);
	return h;
}

uint64_t pc_coop_events_config_hash() { return pc_coop_events_file_hash(pc_coop_events_knob_path()); }

uint64_t pc_coop_state_hash(const PcCoopHashState& s)
{
	uint64_t h = kCoopFnvOffset;
	coop_fnv_u32(h, s.started ? 1u : 0u);
	coop_fnv_u32(h, static_cast<uint32_t>(s.key.stage));
	coop_fnv_u32(h, static_cast<uint32_t>(s.key.day));
	coop_fnv_f32(h, s.key.timeOfDay);
	coop_fnv_u32(h, s.tick);
	for (int k = 0; k < PC_COOP_ANCHOR_COUNT; ++k) coop_fnv_u32(h, static_cast<uint32_t>(s.cursors.next[k]));
	for (int i = 0; i < PC_COOP_CAPTAINS; ++i) coop_fnv_f32(h, s.prevHp[i]);
	for (int i = 0; i < PC_COOP_CAPTAINS; ++i) coop_fnv_u32(h, s.prevValid[i] ? 1u : 0u);
	for (int i = 0; i < PC_COOP_COOLDOWNS; ++i) coop_fnv_f32(h, s.cooldown[i]);
	return h ? h : 1; // 0 stays "nothing folded"
}

unsigned pc_coop_perturb_knob_tick()
{
#if defined(PIKI_NETPLAY_BUILD) && PIKI_NETPLAY_BUILD
	const char* background = std::getenv("PIKMIN_RANDOMIZER_TEST_BACKGROUND");
	if (!background || std::strcmp(background, "1") != 0) return 0;
	const char* text = std::getenv("PIKMIN_NETPLAY_TEST_COOP_PERTURB");
	if (!text || !*text) return 0;
	const char* p = text;
	unsigned tick = 0;
	if (!parse_uint(p, tick) || *p != '\0') return 0;
	return tick;
#else
	return 0;
#endif
}
