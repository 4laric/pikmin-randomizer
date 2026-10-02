// Netplay M5a ICE transport + copy-paste connection codes (issue #887). See
// the header for the wire/code contract. Engine-free: libjuice C API + STL
// only (mutex, chrono, threads for waits; no game, no SDL, no Winsock).

#include "netplay/pc_netplay_ice.h"

#include "juice/juice.h"

#include <stdlib.h>
#include <string.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <mutex>
#include <thread>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

// The ICE channel/size contract must match the UDP transport exactly: the
// session talks to either transport through hs_send/hs_drain, and the wire
// prefix is shared. Reuse-by-value with a compile-time check (m9).
#include "netplay/pc_netplay_udp.h"
static_assert(pc_netplay_ice::kChannelHandshake
                  == pc_netplay_transport::kChannelHandshake,
              "ICE/UDP handshake channel must match");
static_assert(pc_netplay_ice::kChannelGekko == pc_netplay_transport::kChannelGekko,
              "ICE/UDP gekko channel must match");
static_assert(pc_netplay_ice::kChannelBulk == pc_netplay_transport::kChannelBulk,
              "ICE/UDP bulk channel must match");
static_assert(pc_netplay_ice::kMaxDatagram == pc_netplay_transport::kMaxDatagram,
              "ICE/UDP max datagram must match");
static_assert(pc_netplay_ice::kAddrBytes == pc_netplay_transport::kAddrBytes,
              "ICE/UDP addr bytes must match");

namespace pc_netplay_ice {
namespace {

double now_ms()
{
	using namespace std::chrono;
	return duration<double, std::milli>(steady_clock::now().time_since_epoch()).count();
}

const char* getenv_nonempty(const char* name)
{
	const char* v = std::getenv(name);
	return (v != nullptr && *v != '\0') ? v : nullptr;
}

std::string trim(const std::string& s)
{
	size_t b = 0;
	while (b < s.size() && (s[b] == ' ' || s[b] == '\t' || s[b] == '\r' || s[b] == '\n'))
		++b;
	size_t e = s.size();
	while (e > b && (s[e - 1] == ' ' || s[e - 1] == '\t' || s[e - 1] == '\r' || s[e - 1] == '\n'))
		--e;
	return s.substr(b, e - b);
}

bool parse_host_port(const std::string& text, std::string* host, uint16_t* port)
{
	size_t colon = text.rfind(':');
	if (colon == std::string::npos || colon == 0 || colon + 1 >= text.size()) return false;
	std::string h = text.substr(0, colon);
	std::string p = text.substr(colon + 1);
	if (h.empty() || h.size() > 253 || p.empty() || p.size() > 5) return false;
	for (char c : p) {
		if (c < '0' || c > '9') return false;
	}
	long n = strtol(p.c_str(), nullptr, 10);
	if (n <= 0 || n > 65535) return false;
	*host = h;
	*port = (uint16_t)n;
	return true;
}

// ---- CRC32 (IEEE 802.3, written fresh; the vendored crc32.c is internal to
// libjuice and not linked as an API) ----

uint32_t crc32_of(const uint8_t* data, size_t len)
{
	// Thread-safe lazy init (m13): libjuice callbacks run on their own
	// thread, so two agents could race the old non-atomic flag.
	static std::once_flag once;
	static uint32_t table[256];
	std::call_once(once, []() {
		for (uint32_t i = 0; i < 256; ++i) {
			uint32_t c = i;
			for (int k = 0; k < 8; ++k) c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
			table[i] = c;
		}
	});
	uint32_t c = 0xFFFFFFFFu;
	for (size_t i = 0; i < len; ++i) c = table[(c ^ data[i]) & 0xFF] ^ (c >> 8);
	return c ^ 0xFFFFFFFFu;
}

// ---- base64url (RFC 4648 §5, unpadded output, padded input accepted) ----

int b64_value(char c)
{
	if (c >= 'A' && c <= 'Z') return c - 'A';
	if (c >= 'a' && c <= 'z') return c - 'a' + 26;
	if (c >= '0' && c <= '9') return c - '0' + 52;
	if (c == '-') return 62;
	if (c == '_') return 63;
	if (c == '=') return -2; // padding
	return -1;
}

std::string b64url_encode(const uint8_t* data, size_t len)
{
	static const char* digits = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_";
	std::string out;
	out.reserve((len + 2) / 3 * 4);
	for (size_t i = 0; i < len; i += 3) {
		uint32_t n = (uint32_t)data[i] << 16;
		size_t rem = len - i;
		if (rem > 1) n |= (uint32_t)data[i + 1] << 8;
		if (rem > 2) n |= data[i + 2];
		out.push_back(digits[(n >> 18) & 63]);
		out.push_back(digits[(n >> 12) & 63]);
		if (rem > 1) out.push_back(digits[(n >> 6) & 63]);
		if (rem > 2) out.push_back(digits[n & 63]);
	}
	return out;
}

bool b64url_decode(const std::string& text, std::vector<uint8_t>* out, std::string* err)
{
	out->clear();
	// Launch lane: the v2 offer bundles SDP + settings + bootstrap, so the
	// alphabet layer accepts up to 128 KiB of base64 (the v1 code check
	// above still caps v1 codes at 16 KiB of text, and both decoders bound
	// the raw bytes after decoding).
	if (text.empty() || text.size() > 131072) {
		*err = "bad length";
		return false;
	}
	// Length without padding must not be 1 mod 4.
	size_t pad = 0;
	while (pad < text.size() && text[text.size() - 1 - pad] == '=') ++pad;
	if (pad > 2) {
		*err = "bad padding";
		return false;
	}
	const size_t body = text.size() - pad;
	if (body % 4 == 1) {
		*err = "bad length";
		return false;
	}
	uint32_t acc = 0;
	int bits = 0;
	for (size_t i = 0; i < body; ++i) {
		int v = b64_value(text[i]);
		if (v < 0) {
			*err = "bad alphabet";
			return false;
		}
		acc = (acc << 6) | (uint32_t)v;
		bits += 6;
		if (bits >= 8) {
			bits -= 8;
			out->push_back((uint8_t)((acc >> bits) & 0xFF));
		}
	}
	return true;
}

constexpr size_t kMaxSdpBytes = 8192;
constexpr size_t kMaxRawBytes = 12288;
static_assert(kMaxSdpBytes == kMaxBundleSdpBytes, "v1 and v2 share the SDP cap");

} // namespace

IceNetConfig ice_net_config_from_env()
{
	IceNetConfig cfg;
	const char* stun = getenv_nonempty("PIKMIN_NETPLAY_STUN");
	const std::string stunText =
	    stun != nullptr ? stun : "stun.l.google.com:19302,stun.cloudflare.com:3478";
	// PIKMIN_NETPLAY_STUN=none: no STUN at all (host candidates only). Used
	// by tests so no external network is required; humans get the default
	// public servers above.
	const std::string stunLower = [&]() {
		std::string l = trim(stunText);
		for (size_t i = 0; i < l.size(); ++i)
			if (l[i] >= 'A' && l[i] <= 'Z') l[i] = (char)(l[i] + 32);
		return l;
	}();
	if (stunLower == "none" || stunLower == "off" || stunLower == "empty") {
		// No STUN servers.
	} else {
		size_t pos = 0;
		while (pos <= stunText.size()) {
			size_t comma = stunText.find(',', pos);
			std::string entry =
			    trim(comma == std::string::npos ? stunText.substr(pos)
			                                    : stunText.substr(pos, comma - pos));
			if (!entry.empty()) {
				StunServer s;
				if (parse_host_port(entry, &s.host, &s.port)) cfg.stun.push_back(s);
			}
			if (comma == std::string::npos) break;
			pos = comma + 1;
		}
	} // end else: a STUN list was given
	if (const char* turn = getenv_nonempty("PIKMIN_NETPLAY_TURN")) {
		std::string text(turn);
		size_t p = 0;
		while (p <= text.size()) {
			size_t comma = text.find(',', p);
			std::string entry =
			    trim(comma == std::string::npos ? text.substr(p) : text.substr(p, comma - p));
			if (!entry.empty()) {
				// host:port:user:pass (hostname/IPv4 only: no ':' inside).
				size_t c1 = entry.find(':');
				size_t c2 = c1 == std::string::npos ? std::string::npos : entry.find(':', c1 + 1);
				size_t c3 = c2 == std::string::npos ? std::string::npos : entry.find(':', c2 + 1);
				TurnServer t;
				bool ok = c1 != std::string::npos && c2 != std::string::npos
				     && c3 != std::string::npos && entry.find(':', c3 + 1) == std::string::npos;
				if (ok) {
					long port = strtol(entry.substr(c1 + 1, c2 - c1 - 1).c_str(), nullptr, 10);
					t.host = entry.substr(0, c1);
					t.user = entry.substr(c2 + 1, c3 - c2 - 1);
					t.pass = entry.substr(c3 + 1);
					ok = !t.host.empty() && port > 0 && port <= 65535 && !t.user.empty()
					    && !t.pass.empty();
					if (ok) t.port = (uint16_t)port;
				}
				if (ok) {
					cfg.turn.push_back(t);
				} else {
					printf("[netplay] ice: ignoring malformed TURN entry (want "
					       "host:port:user:pass)\n");
					fflush(stdout);
				}
			}
			if (comma == std::string::npos) break;
			p = comma + 1;
		}
	}
	auto read_port = [](const char* name) -> uint16_t {
		const char* v = getenv_nonempty(name);
		if (v == nullptr) return 0;
		char* end  = nullptr;
		long n     = strtol(v, &end, 10);
		if (end == v || *end != '\0' || n < 0 || n > 65535) return 0;
		return (uint16_t)n;
	};
	cfg.portBegin = read_port("PIKMIN_NETPLAY_ICE_PORT_BEGIN");
	cfg.portEnd   = read_port("PIKMIN_NETPLAY_ICE_PORT_END");
	// m6: a single bound means a single port (libjuice wants begin<=end;
	// begin>0,end=0 would make retries negative and fail with only a
	// generic gather error).
	if (cfg.portBegin != 0 && cfg.portEnd == 0) cfg.portEnd = cfg.portBegin;
	if (cfg.portBegin == 0 && cfg.portEnd != 0) cfg.portBegin = cfg.portEnd;
	if (cfg.portEnd != 0 && cfg.portBegin > cfg.portEnd) cfg.portBegin = cfg.portEnd;
	if (const char* bind = getenv_nonempty("PIKMIN_NETPLAY_ICE_BIND"))
		cfg.bindAddress = trim(bind);
	if (const char* to = getenv_nonempty("PIKMIN_NETPLAY_ICE_TURN_ONLY"))
		cfg.turnOnly = (to[0] == '1' && to[1] == '\0');
	if (cfg.turnOnly) cfg.stun.clear(); // relay-only: no STUN by design
	return cfg;
}

bool ice_candidate_line_is_relay(const std::string& line)
{
	// m13: a single substring covers both LF and CRLF forms (" typ relay"
	// is a prefix of " typ relay\r").
	return line.find(" typ relay") != std::string::npos;
}

bool ice_selected_local_is_relay(const std::string& selectedLocal)
{
	return selectedLocal.find("typ relay") != std::string::npos;
}

std::string ice_filter_relay_candidates(const std::string& sdp)
{
	// Split on LF, tolerating CRLF: strip a trailing CR before matching,
	// then rejoin with CRLF. A CRLF input without candidate lines
	// round-trips byte-identically (m5: the trailing empty segment after a
	// final "\r\n" is skipped, so no extra blank line is emitted).
	std::string out;
	size_t pos = 0;
	while (pos <= sdp.size()) {
		size_t eol = sdp.find('\n', pos);
		std::string line =
		    (eol == std::string::npos) ? sdp.substr(pos) : sdp.substr(pos, eol - pos);
		if (!line.empty() && line[line.size() - 1] == '\r') line.resize(line.size() - 1);
		// m5: skip the empty trailing segment after a final newline, so a
		// CRLF input with no filtering round-trips byte-identically.
		if (line.empty() && pos == sdp.size()) break;
		bool isCandidate = line.compare(0, 12, "a=candidate:") == 0;
		if (!isCandidate || ice_candidate_line_is_relay(line)) {
			out += line;
			out += "\r\n";
		}
		if (eol == std::string::npos) break;
		pos = eol + 1;
	}
	// Drop the trailing CRLF when the input had no trailing newline, so a
	// CRLF input round-trips exactly.
	if (!sdp.empty() && sdp[sdp.size() - 1] != '\n' && out.size() >= 2
	    && out.compare(out.size() - 2, 2, "\r\n") == 0)
		out.resize(out.size() - 2);
	return out;
}

bool ice_sdp_has_relay(const std::string& sdp)
{
	size_t pos = 0;
	while (pos <= sdp.size()) {
		size_t eol = sdp.find('\n', pos);
		std::string line =
		    (eol == std::string::npos) ? sdp.substr(pos) : sdp.substr(pos, eol - pos);
		if (line.compare(0, 12, "a=candidate:") == 0 && ice_candidate_line_is_relay(line))
			return true;
		if (eol == std::string::npos) break;
		pos = eol + 1;
	}
	return false;
}

bool ice_encode_code(bool isOffer, const std::string& sdp, std::string* out, std::string* err)
{
	if (sdp.empty() || sdp.size() > kMaxSdpBytes) {
		if (err != nullptr) *err = "SDP empty or oversized";
		return false;
	}
	std::vector<uint8_t> raw;
	raw.reserve(sdp.size() + 8);
	raw.push_back(0x01); // version
	raw.push_back(isOffer ? (uint8_t)'O' : (uint8_t)'A');
	raw.push_back((uint8_t)((sdp.size() >> 8) & 0xFF));
	raw.push_back((uint8_t)(sdp.size() & 0xFF));
	raw.insert(raw.end(), sdp.begin(), sdp.end());
	uint32_t crc = crc32_of(raw.data(), raw.size());
	raw.push_back((uint8_t)((crc >> 24) & 0xFF));
	raw.push_back((uint8_t)((crc >> 16) & 0xFF));
	raw.push_back((uint8_t)((crc >> 8) & 0xFF));
	raw.push_back((uint8_t)(crc & 0xFF));
	*out = "NPIX1-" + b64url_encode(raw.data(), raw.size());
	return true;
}

bool ice_decode_code(const std::string& text, bool* isOffer, std::string* sdp, std::string* err)
{
	auto fail = [&](const char* why) {
		if (err != nullptr) *err = std::string("bad ICE code: ") + why;
		return false;
	};
	std::string t = trim(text);
	if (t.compare(0, 6, "NPIX1-") != 0) return fail("missing NPIX1- version prefix");
	if (t.size() > 6 + 16384) return fail("too long (limit 16384)");
	std::vector<uint8_t> raw;
	std::string derr;
	if (!b64url_decode(t.substr(6), &raw, &derr)) return fail(derr.c_str());
	if (raw.size() < 2 + 2 + 1 + 4) return fail("too short");
	if (raw.size() > kMaxRawBytes) return fail("too long");
	if (raw[0] != 0x01) return fail("unsupported version");
	if (raw[1] != 'O' && raw[1] != 'A') return fail("bad kind");
	const size_t sdpLen = ((size_t)raw[2] << 8) | raw[3];
	if (4 + sdpLen + 4 != raw.size()) return fail("length mismatch");
	if (sdpLen == 0 || sdpLen > kMaxSdpBytes) return fail("bad SDP length");
	uint32_t want = ((uint32_t)raw[4 + sdpLen] << 24) | ((uint32_t)raw[4 + sdpLen + 1] << 16)
	    | ((uint32_t)raw[4 + sdpLen + 2] << 8) | raw[4 + sdpLen + 3];
	if (crc32_of(raw.data(), 4 + sdpLen) != want) return fail("CRC mismatch");
	*isOffer = (raw[1] == 'O');
	*sdp     = std::string(raw.begin() + 4, raw.begin() + 4 + sdpLen);
	if (sdp->find("a=ice-ufrag:") == std::string::npos
	    || sdp->find("a=ice-pwd:") == std::string::npos)
		return fail("SDP missing ice credentials");
	return true;
}

// ---- v2 offer codes (session bundle; launch lane) ----

bool ice_encode_offer_v2(const std::string& sdp, const SessionBundle& bundle, std::string* out,
                         std::string* err)
{
	if (sdp.empty() || sdp.size() > kMaxSdpBytes) {
		if (err != nullptr) *err = "SDP empty or oversized";
		return false;
	}
	if (bundle.configText.size() > kMaxBundleConfigBytes) {
		if (err != nullptr) *err = "session config block oversized";
		return false;
	}
	if (bundle.bootstrapBytes.size() > kMaxBundleBootBytes) {
		if (err != nullptr) *err = "bootstrap bytes oversized";
		return false;
	}
	std::vector<uint8_t> raw;
	raw.reserve(12 + sdp.size() + bundle.configText.size() + bundle.bootstrapBytes.size());
	raw.push_back(0x02); // version
	raw.push_back((uint8_t)'O');
	raw.push_back((uint8_t)((sdp.size() >> 8) & 0xFF));
	raw.push_back((uint8_t)(sdp.size() & 0xFF));
	raw.push_back((uint8_t)((bundle.configText.size() >> 8) & 0xFF));
	raw.push_back((uint8_t)(bundle.configText.size() & 0xFF));
	raw.push_back((uint8_t)((bundle.bootstrapBytes.size() >> 8) & 0xFF));
	raw.push_back((uint8_t)(bundle.bootstrapBytes.size() & 0xFF));
	raw.push_back((uint8_t)((bundle.seed >> 24) & 0xFF));
	raw.push_back((uint8_t)((bundle.seed >> 16) & 0xFF));
	raw.push_back((uint8_t)((bundle.seed >> 8) & 0xFF));
	raw.push_back((uint8_t)(bundle.seed & 0xFF));
	raw.insert(raw.end(), sdp.begin(), sdp.end());
	raw.insert(raw.end(), bundle.configText.begin(), bundle.configText.end());
	raw.insert(raw.end(), bundle.bootstrapBytes.begin(), bundle.bootstrapBytes.end());
	uint32_t crc = crc32_of(raw.data(), raw.size());
	raw.push_back((uint8_t)((crc >> 24) & 0xFF));
	raw.push_back((uint8_t)((crc >> 16) & 0xFF));
	raw.push_back((uint8_t)((crc >> 8) & 0xFF));
	raw.push_back((uint8_t)(crc & 0xFF));
	*out = "NPIX2-" + b64url_encode(raw.data(), raw.size());
	return true;
}

bool ice_decode_offer_v2(const std::string& text, std::string* sdp, SessionBundle* bundle,
                         std::string* err)
{
	auto fail = [&](const char* why) {
		if (err != nullptr) *err = std::string("bad ICE code: ") + why;
		return false;
	};
	std::string t = trim(text);
	if (t.compare(0, 6, "NPIX2-") != 0) return fail("missing NPIX2- version prefix");
	// Bounded before decoding: no valid v2 offer is longer than this.
	if (t.size() > kMaxOfferV2Chars)
		return fail(("too long (limit " + std::to_string(kMaxOfferV2Chars) + ")").c_str());
	std::vector<uint8_t> raw;
	std::string derr;
	if (!b64url_decode(t.substr(6), &raw, &derr)) return fail(derr.c_str());
	// Header: version + kind + 3 lengths + seed = 12 bytes, plus CRC 4.
	if (raw.size() < 12 + 4) return fail("too short");
	if (raw.size() > 12 + kMaxSdpBytes + kMaxBundleConfigBytes + kMaxBundleBootBytes + 4)
		return fail("too long");
	if (raw[0] != 0x02) return fail("unsupported version");
	if (raw[1] != 'O') return fail("bad kind");
	const size_t sdpLen = ((size_t)raw[2] << 8) | raw[3];
	const size_t cfgLen = ((size_t)raw[4] << 8) | raw[5];
	const size_t bootLen = ((size_t)raw[6] << 8) | raw[7];
	// Bound every length before allocation or slicing.
	if (sdpLen == 0 || sdpLen > kMaxSdpBytes) return fail("bad SDP length");
	if (cfgLen == 0 || cfgLen > kMaxBundleConfigBytes) return fail("bad session config length");
	if (bootLen > kMaxBundleBootBytes) return fail("bad bootstrap length");
	if (12 + sdpLen + cfgLen + bootLen + 4 != raw.size()) return fail("length mismatch");
	uint32_t want = ((uint32_t)raw[12 + sdpLen + cfgLen + bootLen] << 24)
	    | ((uint32_t)raw[12 + sdpLen + cfgLen + bootLen + 1] << 16)
	    | ((uint32_t)raw[12 + sdpLen + cfgLen + bootLen + 2] << 8)
	    | raw[12 + sdpLen + cfgLen + bootLen + 3];
	if (crc32_of(raw.data(), 12 + sdpLen + cfgLen + bootLen) != want) return fail("CRC mismatch");
	const uint32_t seed = ((uint32_t)raw[8] << 24) | ((uint32_t)raw[9] << 16)
	    | ((uint32_t)raw[10] << 8) | raw[11];
	*sdp = std::string(raw.begin() + 12, raw.begin() + 12 + sdpLen);
	bundle->configText =
	    std::string(raw.begin() + 12 + sdpLen, raw.begin() + 12 + sdpLen + cfgLen);
	bundle->bootstrapBytes = std::string(raw.begin() + 12 + sdpLen + cfgLen,
	                                     raw.begin() + 12 + sdpLen + cfgLen + bootLen);
	bundle->seed = seed;
	if (sdp->find("a=ice-ufrag:") == std::string::npos
	    || sdp->find("a=ice-pwd:") == std::string::npos)
		return fail("SDP missing ice credentials");
	return true;
}

bool ice_read_code_arg(const std::string& arg, std::string* code, std::string* err)
{
	std::string a = trim(arg);
	if (a.size() > 1 && a[0] == '@') {
		std::string path = a.substr(1);
		FILE* f          = fopen(path.c_str(), "rb");
		if (f == nullptr) {
			if (err != nullptr) *err = "cannot open code file " + path;
			return false;
		}
		// Bounded read: a file larger than the longest valid code (plus
		// whitespace slack) is refused instead of read in full.
		const size_t kMaxCodeFileBytes = kMaxOfferV2Chars + 4096;
		std::string raw;
		char chunk[4096];
		bool tooBig = false;
		while (true) {
			size_t n = fread(chunk, 1, sizeof(chunk), f);
			if (n > 0) raw.append(chunk, n);
			if (raw.size() > kMaxCodeFileBytes) {
				tooBig = true;
				break;
			}
			if (n < sizeof(chunk)) break;
		}
		fclose(f);
		if (tooBig) {
			if (err != nullptr) *err = "code file is too large to be a connection code: " + path;
			return false;
		}
		*code = trim(raw);
		if (code->empty()) {
			if (err != nullptr) *err = "code file is empty: " + path;
			return false;
		}
		return true;
	}
	*code = a;
	if (code->empty()) {
		if (err != nullptr) *err = "empty code";
		return false;
	}
	return true;
}

bool ice_write_code_file(const std::string& path, const std::string& code, std::string* err)
{
	if (path.empty()) return true;
	// m9: write a temporary file next to the target, then rename it over the
	// target, so a reader polling the path sees either nothing or the whole
	// code (never an empty or half-written file).
	const std::string tmp = path + ".tmp";
	FILE* f               = fopen(tmp.c_str(), "wb");
	if (f == nullptr) {
		if (err != nullptr) *err = "cannot write code file " + tmp;
		return false;
	}
	bool ok = fwrite(code.c_str(), 1, code.size(), f) == code.size()
	    && fwrite("\n", 1, 1, f) == 1;
	ok = (fclose(f) == 0) && ok;
	if (!ok) {
		remove(tmp.c_str());
		if (err != nullptr) *err = "short write to " + tmp;
		return false;
	}
#ifdef _WIN32
	const bool moved =
	    MoveFileExA(tmp.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
	const bool moved = rename(tmp.c_str(), path.c_str()) == 0;
#endif
	if (!moved) {
		remove(tmp.c_str());
		if (err != nullptr) *err = "cannot rename " + tmp + " to " + path;
		return false;
	}
	return true;
}

// ---- IceSocket ----

IceSocket::IceSocket() : mMutex(new std::mutex()) {}

IceSocket::~IceSocket() { close(); }

void IceSocket::close()
{
	std::mutex* mu = (std::mutex*)mMutex;
	if (mu == nullptr) return;
	juice_agent_t* a = nullptr;
	{
		// Callbacks only hold the mutex briefly and never block on it, so
		// taking it here and releasing before juice_destroy cannot deadlock.
		std::lock_guard<std::mutex> lock(*mu);
		a       = mAgent;
		mAgent  = nullptr;
		mClosed = true;
	}
	// Destroy outside the lock: libjuice joins its threads here, and a
	// racing callback may be waiting on mMutex.
	if (a != nullptr) juice_destroy(a);
	delete mu;
	mMutex = nullptr;
}

void IceSocket::on_state(juice_agent_t* /*agent*/, juice_state_t state, void* userPtr)
{
	IceSocket* self = (IceSocket*)userPtr;
	if (self == nullptr || self->mMutex == nullptr) return;
	juice_agent_t* a = nullptr;
	{
		std::lock_guard<std::mutex> lock(*(std::mutex*)self->mMutex);
		if (self->mClosed) return;
		self->mState = (int)state;
		a            = self->mAgent;
	}
	// Log + query outside our lock. libjuice's API is thread-safe and these
	// calls never re-enter our callbacks synchronously.
	printf("[netplay] ice state: %s\n", juice_state_to_string(state));
	fflush(stdout);
	if (state == JUICE_STATE_COMPLETED && a != nullptr) {
		char local[JUICE_MAX_CANDIDATE_SDP_STRING_LEN];
		char remote[JUICE_MAX_CANDIDATE_SDP_STRING_LEN];
		local[0] = remote[0] = '\0';
		std::string ls, rs;
		if (juice_get_selected_candidates(a, local, sizeof(local), remote, sizeof(remote))
		    == JUICE_ERR_SUCCESS) {
			ls = local;
			rs = remote;
		} else {
			char la[JUICE_MAX_ADDRESS_STRING_LEN], ra[JUICE_MAX_ADDRESS_STRING_LEN];
			if (juice_get_selected_addresses(a, la, sizeof(la), ra, sizeof(ra))
			    == JUICE_ERR_SUCCESS) {
				ls = std::string("addr ") + la;
				rs = std::string("addr ") + ra;
			}
		}
		std::lock_guard<std::mutex> lock(*(std::mutex*)self->mMutex);
		if (self->mClosed) return;
		self->mSelectedLocal  = ls;
		self->mSelectedRemote = rs;
		// m2: connect time from apply_remote() (both descriptions known),
		// falling back to creation only when no remote was applied.
		if (self->mCompletedMs < 0) {
			const double base =
			    self->mConnectStartMs > 0 ? self->mConnectStartMs : self->mCreateMs;
			if (base > 0) self->mCompletedMs = now_ms() - base;
		}
		printf("[netplay] ice selected: local [%s] remote [%s]\n", ls.c_str(), rs.c_str());
		if (self->mCompletedMs >= 0)
			printf("[netplay] ice completed in %.0fms\n", self->mCompletedMs);
		fflush(stdout);
		return;
	}
	if (state == JUICE_STATE_FAILED) {
		printf("[netplay] ice failed: no working candidate pair\n");
		fflush(stdout);
	}
}

void IceSocket::on_candidate(juice_agent_t* /*agent*/, const char* sdp, void* userPtr)
{
	IceSocket* self = (IceSocket*)userPtr;
	if (self == nullptr || self->mMutex == nullptr || sdp == nullptr) return;
	std::lock_guard<std::mutex> lock(*(std::mutex*)self->mMutex);
	if (self->mClosed) return;
	if (self->mLocalCandidates.size() < 64) self->mLocalCandidates.emplace_back(sdp);
}

void IceSocket::on_gathering_done(juice_agent_t* /*agent*/, void* userPtr)
{
	IceSocket* self = (IceSocket*)userPtr;
	if (self == nullptr || self->mMutex == nullptr) return;
	std::lock_guard<std::mutex> lock(*(std::mutex*)self->mMutex);
	self->mGatheringDone = true;
}

void IceSocket::on_recv(juice_agent_t* /*agent*/, const char* data, size_t size, void* userPtr)
{
	IceSocket* self = (IceSocket*)userPtr;
	if (self == nullptr || self->mMutex == nullptr || data == nullptr) return;
	if (size < 2 || size > kMaxDatagram) return; // channel + payload; bounded
	std::lock_guard<std::mutex> lock(*(std::mutex*)self->mMutex);
	if (self->mClosed || self->mAgent == nullptr) return;
	if (self->mQueue.size() >= 512) self->mQueue.erase(self->mQueue.begin());
	Datagram d;
	d.channel         = (uint8_t)data[0];
	d.payload.assign((const uint8_t*)data + 1, (const uint8_t*)data + size);
	d.fromIpHostOrder = 0x7F000001;
	d.fromPort        = 1;
	self->mQueue.push_back(std::move(d));
}

bool IceSocket::create_agent(const IceNetConfig& cfg, std::string* err)
{
	if (mAgent != nullptr) {
		if (err != nullptr) *err = "agent already created";
		return false;
	}
	if (const char* dbg = getenv_nonempty("PIKMIN_NETPLAY_ICE_DEBUG")) {
		if (dbg[0] == '1' && dbg[1] == '\0') juice_set_log_level(JUICE_LOG_LEVEL_VERBOSE);
	} else {
		juice_set_log_level(JUICE_LOG_LEVEL_WARN);
	}
	juice_config_t jc;
	memset(&jc, 0, sizeof(jc));
	// Default (POLL) concurrency: the investigator's loopback smoke test used
	// defaults and reached completed in 17 ms; callbacks still arrive on
	// libjuice's thread, hence the locked queue.
	jc.concurrency_mode = JUICE_CONCURRENCY_MODE_POLL;
	std::string stunHost;
	if (!cfg.stun.empty()) {
		stunHost              = cfg.stun.front().host;
		jc.stun_server_host   = stunHost.c_str();
		jc.stun_server_port   = cfg.stun.front().port;
	}
	std::string bindHost = cfg.bindAddress;
	if (!bindHost.empty()) jc.bind_address = bindHost.c_str();
	std::vector<juice_turn_server_t> turn;
	for (size_t i = 0; i < cfg.turn.size(); ++i) {
		juice_turn_server_t ts;
		memset(&ts, 0, sizeof(ts));
		// agent_create deep-copies every string, so pointing at cfg (which
		// outlives the agent) is safe.
		ts.host     = cfg.turn[i].host.c_str();
		ts.port     = cfg.turn[i].port;
		ts.username = cfg.turn[i].user.c_str();
		ts.password = cfg.turn[i].pass.c_str();
		turn.push_back(ts);
	}
	if (!turn.empty()) {
		jc.turn_servers       = turn.data();
		jc.turn_servers_count = (int)turn.size();
	}
	jc.local_port_range_begin = cfg.portBegin;
	jc.local_port_range_end   = cfg.portEnd;
	jc.cb_state_changed       = &IceSocket::on_state;
	jc.cb_candidate           = &IceSocket::on_candidate;
	jc.cb_gathering_done      = &IceSocket::on_gathering_done;
	jc.cb_recv                = &IceSocket::on_recv;
	jc.user_ptr               = this;
	mTurnOnly                 = cfg.turnOnly;
	juice_agent_t* a          = juice_create(&jc);
	if (a == nullptr) {
		if (err != nullptr) *err = "juice_create failed";
		return false;
	}
	mAgent   = a;
	mCreated = true;
	mCreateMs = now_ms();
	return true;
}

bool IceSocket::wait_gathering_done(double timeoutMs, std::string* err,
                                    std::function<void()> pump)
{
	// M3: pump the caller's window ~every 50 ms so Windows never marks the
	// game "Not Responding" during the (up to 15 s) gather.
	const double start = now_ms();
	double lastPump    = 0;
	while (true) {
		{
			std::lock_guard<std::mutex> lock(*(std::mutex*)mMutex);
			if (mGatheringDone) return true;
		}
		if (now_ms() - start > timeoutMs) {
			if (err != nullptr) *err = "candidate gathering timed out";
			return false;
		}
		if (pump && now_ms() - lastPump > 50) {
			pump();
			lastPump = now_ms();
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(5));
	}
}

bool IceSocket::local_description(std::string* out, std::string* err)
{
	char buf[JUICE_MAX_SDP_STRING_LEN];
	if (juice_get_local_description(mAgent, buf, sizeof(buf)) != JUICE_ERR_SUCCESS) {
		if (err != nullptr) *err = "juice_get_local_description failed";
		return false;
	}
	*out = buf;
	return true;
}

bool IceSocket::apply_remote(const std::string& sdp, bool turnOnly, std::string* err)
{
	std::string use = sdp;
	if (turnOnly) {
		use = ice_filter_relay_candidates(sdp);
		// No candidate lines at all (or none relay): keep going; the
		// connect wait will fail with a clear message.
	}
	// m2: the ICE connect clock starts when both descriptions are known
	// (not at agent creation, which includes the human copy-paste).
	mConnectStartMs = now_ms();
	if (juice_set_remote_description(mAgent, use.c_str()) != JUICE_ERR_SUCCESS) {
		if (err != nullptr) *err = "juice_set_remote_description failed";
		return false;
	}
	// Our codes bundle every candidate in the description (no trickle), so
	// mark the remote side done right away.
	juice_set_remote_gathering_done(mAgent);
	return true;
}

double ice_gather_timeout_ms()
{
	const char* v = getenv_nonempty("PIKMIN_NETPLAY_ICE_GATHER_TIMEOUT_MS");
	if (v != nullptr) {
		char* end = nullptr;
		double n  = strtod(v, &end);
		if (end != v && *end == '\0' && n >= 1000 && n <= 600000) return n;
	}
	return 15000.0;
}

bool IceSocket::host_create_offer(const IceNetConfig& cfg, std::string* offerOut,
                                    std::string* err, std::function<void()> pump)
{
	if (!create_agent(cfg, err)) return false;
	if (juice_gather_candidates(mAgent) != JUICE_ERR_SUCCESS) {
		if (err != nullptr)
			*err = "juice_gather_candidates failed (port range "
			    + std::to_string(cfg.portBegin) + "-" + std::to_string(cfg.portEnd)
			    + (cfg.bindAddress.empty() ? "" : ", bind " + cfg.bindAddress) + ")";
		return false;
	}
	if (!wait_gathering_done(ice_gather_timeout_ms(), err, pump)) return false;
	std::string sdp;
	if (!local_description(&sdp, err)) return false;
	if (cfg.turnOnly) {
		if (!ice_sdp_has_relay(sdp)) {
			if (err != nullptr)
				*err = "TURN-only mode gathered no relay candidates; is the TURN "
				       "server reachable (PIKMIN_NETPLAY_TURN)?";
			return false;
		}
		sdp = ice_filter_relay_candidates(sdp);
		printf("[netplay] ice: TURN-only mode, host candidates filtered out\n");
		fflush(stdout);
	}
	return ice_encode_code(true, sdp, offerOut, err);
}

bool IceSocket::host_create_offer_v2(const IceNetConfig& cfg, const SessionBundle& bundle,
                                     std::string* offerOut, std::string* err,
                                     std::function<void()> pump)
{
	if (!create_agent(cfg, err)) return false;
	if (juice_gather_candidates(mAgent) != JUICE_ERR_SUCCESS) {
		if (err != nullptr)
			*err = "juice_gather_candidates failed (port range "
			    + std::to_string(cfg.portBegin) + "-" + std::to_string(cfg.portEnd)
			    + (cfg.bindAddress.empty() ? "" : ", bind " + cfg.bindAddress) + ")";
		return false;
	}
	if (!wait_gathering_done(ice_gather_timeout_ms(), err, pump)) return false;
	std::string sdp;
	if (!local_description(&sdp, err)) return false;
	if (cfg.turnOnly) {
		if (!ice_sdp_has_relay(sdp)) {
			if (err != nullptr)
				*err = "TURN-only mode gathered no relay candidates; is the TURN "
				       "server reachable (PIKMIN_NETPLAY_TURN)?";
			return false;
		}
		sdp = ice_filter_relay_candidates(sdp);
		printf("[netplay] ice: TURN-only mode, host candidates filtered out\n");
		fflush(stdout);
	}
	return ice_encode_offer_v2(sdp, bundle, offerOut, err);
}

bool IceSocket::join_create_answer(const IceNetConfig& cfg, const std::string& offer,
                                   std::string* answerOut, std::string* err,
                                   std::function<void()> pump, SessionBundle* bundleOut)
{
	bool isOffer = false;
	std::string offerSdp;
	// Launch lane: v2 bundle offers ("NPIX2-...") carry the session setup;
	// v1 offers ("NPIX1-...") decode exactly as before.
	if (trim(offer).compare(0, 6, "NPIX2-") == 0) {
		SessionBundle bundle;
		if (!ice_decode_offer_v2(offer, &offerSdp, &bundle, err)) return false;
		if (bundleOut != nullptr) *bundleOut = bundle;
	} else {
		if (!ice_decode_code(offer, &isOffer, &offerSdp, err)) return false;
		if (!isOffer) {
			if (err != nullptr) *err = "bad ICE code: expected an offer, got an answer";
			return false;
		}
		if (bundleOut != nullptr) *bundleOut = SessionBundle();
	}
	// NOTE: set_remote BEFORE local_description so this side takes the
	// controlled role (RFC 8445 6.1.1); the host does the reverse.
	if (!create_agent(cfg, err)) return false;
	if (!apply_remote(offerSdp, cfg.turnOnly, err)) return false;
	if (juice_gather_candidates(mAgent) != JUICE_ERR_SUCCESS) {
		if (err != nullptr)
			*err = "juice_gather_candidates failed (port range "
			    + std::to_string(cfg.portBegin) + "-" + std::to_string(cfg.portEnd)
			    + (cfg.bindAddress.empty() ? "" : ", bind " + cfg.bindAddress) + ")";
		return false;
	}
	if (!wait_gathering_done(ice_gather_timeout_ms(), err, pump)) return false;
	std::string sdp;
	if (!local_description(&sdp, err)) return false;
	if (cfg.turnOnly) {
		// M1/m13: the joiner must also gather a relay candidate of its
		// own; otherwise it would wait the full connect timeout.
		if (!ice_sdp_has_relay(sdp)) {
			if (err != nullptr)
				*err = "TURN-only mode gathered no relay candidates; is the TURN "
				       "server reachable (PIKMIN_NETPLAY_TURN)?";
			return false;
		}
		sdp = ice_filter_relay_candidates(sdp);
		printf("[netplay] ice: TURN-only mode, host candidates filtered out\n");
		fflush(stdout);
	}
	return ice_encode_code(false, sdp, answerOut, err);
}

bool IceSocket::host_apply_answer(const std::string& answer, std::string* err)
{
	bool isOffer = true;
	std::string sdp;
	if (!ice_decode_code(answer, &isOffer, &sdp, err)) return false;
	if (isOffer) {
		if (err != nullptr) *err = "bad ICE code: expected an answer, got an offer";
		return false;
	}
	return apply_remote(sdp, mTurnOnly, err);
}

bool IceSocket::wait_connected(double timeoutMs, double* completedMsOut, std::string* err,
                               std::function<void()> pump)
{
	// M3: pump the caller's window ~every 50 ms while waiting.
	const double start = now_ms();
	double lastPump    = 0;
	while (true) {
		int st = 0;
		{
			std::lock_guard<std::mutex> lock(*(std::mutex*)mMutex);
			if (mCompletedMs >= 0) {
				// M1: TURN-only mode must select a relay candidate locally;
				// otherwise the direct path leaked through (loopback
				// per-IP permissions) and the run proves nothing.
				if (mTurnOnly && !ice_selected_local_is_relay(mSelectedLocal)) {
					if (err != nullptr)
						*err = std::string("TURN-only violated: selected local is not relay: ")
						    + (mSelectedLocal.empty() ? "<unknown>" : mSelectedLocal);
					return false;
				}
				if (completedMsOut != nullptr) *completedMsOut = mCompletedMs;
				return true;
			}
			st = mState;
		}
		if (st == (int)JUICE_STATE_FAILED) {
			if (err != nullptr) *err = "ICE failed: no working candidate pair";
			return false;
		}
		if (now_ms() - start > timeoutMs) {
			if (err != nullptr) *err = "ICE connect timed out";
			return false;
		}
		if (pump && now_ms() - lastPump > 50) {
			pump();
			lastPump = now_ms();
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(10));
	}
}

bool IceSocket::send_payload(uint8_t channel, const uint8_t* data, size_t len)
{
	if (mAgent == nullptr || len + 1 > kMaxDatagram) return false;
	if (len > 0 && data == nullptr) return false;
	uint8_t frame[kMaxDatagram];
	frame[0] = channel;
	if (len > 0) memcpy(frame + 1, data, len);
	return juice_send(mAgent, (const char*)frame, len + 1) == JUICE_ERR_SUCCESS;
}

bool IceSocket::send_to(uint8_t channel, const uint8_t* data, size_t len, uint32_t /*ip*/,
                        uint16_t /*port*/)
{
	// The agent is connected 1:1; the address is ignored by design.
	return send_payload(channel, data, len);
}

std::vector<IceSocket::Datagram> IceSocket::recv()
{
	std::vector<Datagram> out;
	if (mMutex == nullptr) return out;
	std::lock_guard<std::mutex> lock(*(std::mutex*)mMutex);
	// m13: move a batch at once instead of erasing the front per element
	// (O(n^2) on the bounded queue).
	const size_t n =
	    mQueue.size() < (size_t)kMaxRecvPerPoll ? mQueue.size() : (size_t)kMaxRecvPerPoll;
	out.reserve(n);
	for (size_t i = 0; i < n; ++i) out.push_back(std::move(mQueue[i]));
	mQueue.erase(mQueue.begin(), mQueue.begin() + (ptrdiff_t)n);
	return out;
}

std::string IceSocket::selected_local() const
{
	if (mMutex == nullptr) return std::string();
	std::lock_guard<std::mutex> lock(*(std::mutex*)mMutex);
	return mSelectedLocal;
}

std::string IceSocket::selected_remote() const
{
	if (mMutex == nullptr) return std::string();
	std::lock_guard<std::mutex> lock(*(std::mutex*)mMutex);
	return mSelectedRemote;
}

std::string IceSocket::state_str() const
{
	if (mMutex == nullptr) return "closed";
	std::lock_guard<std::mutex> lock(*(std::mutex*)mMutex);
	if (mAgent == nullptr) return "closed";
	return juice_state_to_string((juice_state_t)mState);
}

double IceSocket::completed_ms() const
{
	if (mMutex == nullptr) return -1;
	std::lock_guard<std::mutex> lock(*(std::mutex*)mMutex);
	return mCompletedMs;
}

// ---- IceLink ----

namespace {
IceLink* g_ice_send_link = nullptr;
IceLink* g_ice_recv_link = nullptr;

void ice_send_trampoline(GekkoNetAddress* addr, const char* data, int length)
{
	if (g_ice_send_link == nullptr) return;
	if (addr == nullptr || data == nullptr || length <= 0) return;
	// Connected agent: the blob content is ignored (kept for GekkoNet's
	// actor routing only).
	g_ice_send_link->send_to_peer(0x7F000001, 1, (const uint8_t*)data, (size_t)length);
}

GekkoNetResult** ice_receive_trampoline(int* length)
{
	if (length == nullptr || g_ice_recv_link == nullptr) {
		if (length != nullptr) *length = 0;
		return nullptr;
	}
	return g_ice_recv_link->receive_inner(length);
}

void ice_free_trampoline(void* data_ptr) { free(data_ptr); }
} // namespace

IceLink::IceLink(IceSocket* sock) : mSock(sock)
{
	mAdapter.send_data    = ice_send_trampoline;
	mAdapter.receive_data = ice_receive_trampoline;
	mAdapter.free_data    = ice_free_trampoline;
	g_ice_send_link       = this;
	g_ice_recv_link       = this;
}

IceLink::~IceLink()
{
	if (g_ice_send_link == this) g_ice_send_link = nullptr;
	if (g_ice_recv_link == this) g_ice_recv_link = nullptr;
}

GekkoNetAdapter* IceLink::adapter() { return &mAdapter; }

void IceLink::send_to_peer(uint32_t /*ip*/, uint16_t /*port*/, const uint8_t* data, size_t len)
{
	if (mSock == nullptr) return;
	mSock->send_payload(kChannelGekko, data, len);
}

constexpr size_t kMaxPendingQueue = 512;

// M4 lane B2 (issue #885): one routing step for every drain, now with the
// bulk channel. Each queue is capped at kMaxPendingQueue (oldest dropped);
// a bulk payload is bounded like over UDP (the BulkChannel validator drops
// anything malformed, never a truncated copy).
void IceLink::route(std::vector<IceSocket::Datagram>& grams)
{
	for (IceSocket::Datagram& g : grams) {
		if (g.channel == kChannelGekko) {
			mGekkoPending.push_back(std::move(g));
		} else if (g.channel == kChannelHandshake) {
			mHandshakePending.push_back(std::move(g));
		} else if (g.channel == kChannelBulk) {
			if (g.payload.size() + 1 <= kMaxDatagram) mBulkPending.push_back(std::move(g));
		}
		// Unknown channels are dropped.
	}
	auto cap = [](std::vector<IceSocket::Datagram>& q) {
		if (q.size() > kMaxPendingQueue) q.erase(q.begin(), q.begin() + (q.size() - kMaxPendingQueue));
	};
	cap(mGekkoPending);
	cap(mHandshakePending);
	cap(mBulkPending);
}

GekkoNetResult** IceLink::receive_inner(int* length)
{
	mResults.clear();
	if (mSock != nullptr) {
		std::vector<IceSocket::Datagram> grams = mSock->recv();
		route(grams);
	}
	auto emit = [&](const uint8_t* payload, size_t len) {
		if (len > kMaxDatagram - 1) return; // bounded before use
		GekkoNetResult* res = (GekkoNetResult*)malloc(sizeof(GekkoNetResult));
		uint8_t* addrBuf    = (uint8_t*)malloc(kAddrBytes);
		void* payBuf        = len > 0 ? malloc(len) : nullptr;
		if (res == nullptr || addrBuf == nullptr || (len > 0 && payBuf == nullptr)) {
			free(res);
			free(addrBuf);
			free(payBuf);
			return;
		}
		// Fixed placeholder: 127.0.0.1:1. Both directions synthesise the
		// same blob, so GekkoNet's routing sees one stable peer.
		addrBuf[0] = 127;
		addrBuf[1] = 0;
		addrBuf[2] = 0;
		addrBuf[3] = 1;
		addrBuf[4] = 0;
		addrBuf[5] = 1;
		if (len > 0) memcpy(payBuf, payload, len);
		res->addr.data = addrBuf;
		res->addr.size = (unsigned)kAddrBytes;
		res->data_len  = (unsigned)len;
		res->data      = payBuf;
		mResults.push_back(res);
	};
	for (IceSocket::Datagram& g : mGekkoPending) emit(g.payload.data(), g.payload.size());
	mGekkoPending.clear();
	*length = (int)mResults.size();
	return mResults.empty() ? nullptr : mResults.data();
}

std::vector<IceSocket::Datagram> IceLink::drain_handshake()
{
	if (mSock != nullptr) {
		std::vector<IceSocket::Datagram> grams = mSock->recv();
		route(grams);
	}
	std::vector<IceSocket::Datagram> out;
	out.swap(mHandshakePending);
	return out;
}

std::vector<IceSocket::Datagram> IceLink::drain_bulk()
{
	// Same pump-on-drain as the handshake queue, so bulk bytes are not stuck
	// behind an idle GekkoNet poll (and flow before GekkoNet exists: the
	// checkpoint transfer runs between the handshake and the session).
	if (mSock != nullptr) {
		std::vector<IceSocket::Datagram> grams = mSock->recv();
		route(grams);
	}
	std::vector<IceSocket::Datagram> out;
	out.swap(mBulkPending);
	return out;
}

// ---- one-shot signalling orchestration ----

double ice_connect_timeout_ms()
{
	const char* v = getenv_nonempty("PIKMIN_NETPLAY_ICE_TIMEOUT_MS");
	if (v != nullptr) {
		char* end = nullptr;
		double n  = strtod(v, &end);
		if (end != v && *end == '\0' && n >= 1000 && n <= 1800000) return n;
	}
	// M3: 10 min by default, so a normal human copy-paste round trip fits.
	// The pair tool passes an explicit (shorter) timeout for bounded tests.
	return 600000.0;
}

void ice_print_code(const char* kind, const std::string& code)
{
	// The code itself is exactly one line; the tag line names it for the
	// pair tool (and for humans copying from a console).
	printf("[netplay] ice %s code:\n%s\n", kind, code.c_str());
	fflush(stdout);
}

bool ice_emit_code(const char* kind, const std::string& code, std::string* err)
{
	ice_print_code(kind, code);
	const char* out = getenv_nonempty("PIKMIN_NETPLAY_ICE_CODE_OUT");
	if (out != nullptr && !ice_write_code_file(out, code, err)) return false;
	return true;
}

bool ice_poll_answer_file(const std::string& path, double timeoutMs, std::function<void()> pump,
                          std::string* answerOut, std::string* err)
{
	const double start   = now_ms();
	double lastPump      = 0;
	std::string lastErr, lastSeen;
	while (true) {
		FILE* f = fopen(path.c_str(), "rb");
		if (f != nullptr) {
			std::string raw;
			char chunk[4096];
			while (true) {
				size_t n = fread(chunk, 1, sizeof(chunk), f);
				if (n > 0) raw.append(chunk, n);
				if (n < sizeof(chunk)) break;
			}
			fclose(f);
			std::string t = trim(raw);
			if (!t.empty()) {
				bool isOffer = true;
				std::string sdp, derr;
				if (ice_decode_code(t, &isOffer, &sdp, &derr) && !isOffer) {
					*answerOut = t;
					return true;
				}
				// m7 (cheap part): a mangled answer must not fail silently
				// until the timeout. Log each new content's decode error.
				if (t != lastSeen) {
					lastSeen = t;
					lastErr  = derr;
					printf("[netplay] ice: answer file not yet valid (%s), waiting\n",
					       derr.c_str());
					fflush(stdout);
				}
			}
		}
		if (now_ms() - start > timeoutMs) {
			if (err != nullptr) {
				*err = "timed out waiting for the answer code in " + path
				     + (lastErr.empty() ? "" : " (last decode: " + lastErr + ")");
			}
			return false;
		}
		if (pump && now_ms() - lastPump > 50) {
			pump();
			lastPump = now_ms();
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(100));
	}
}

bool ice_read_answer_stdin(std::function<void()> pump, std::string* answerOut, std::string* err)
{
	printf("[netplay] ice: paste the joiner's answer code, then Enter:\n");
	fflush(stdout);
	// M3+m8: stdin blocks indefinitely (a human may take minutes), so read
	// on a helper thread while the main thread keeps pumping the window.
	// m8: valid codes can reach ~11k chars; accept a full line up to 16390
	// (answers are ~221 chars; the slack only bounds a runaway paste).
	// m4: one bad paste must not end the host. Every line is decoded; a bad
	// one prints why and the prompt repeats. Only EOF ends the wait.
	const size_t kMaxAnswerChars = 16390;
	std::string answer;
	std::string lastErr;
	std::atomic<bool> done(false);
	std::thread reader([&]() {
		while (true) {
			std::string acc;
			acc.reserve(1024);
			int c         = 0;
			bool overflow = false;
			while ((c = getchar()) != EOF && c != '\n') {
				if (acc.size() >= kMaxAnswerChars) {
					overflow = true;
					continue; // drain the rest of the runaway line
				}
				acc.push_back((char)c);
			}
			const std::string line = trim(acc);
			if (overflow) {
				lastErr = "bad ICE code: pasted line longer than " + std::to_string(kMaxAnswerChars)
				        + " characters";
			} else if (!line.empty()) {
				bool isOffer = true;
				std::string sdp, derr;
				if (line.compare(0, 6, "NPIX2-") == 0) {
					lastErr = "bad ICE code: that is an offer code (NPIX2-); paste the joiner's "
					          "answer code (NPIX1-...) instead";
				} else if (!ice_decode_code(line, &isOffer, &sdp, &derr)) {
					lastErr = derr;
				} else if (isOffer) {
					lastErr = "bad ICE code: expected an answer, got an offer";
				} else {
					answer = line;
					done   = true;
					return;
				}
			}
			if (c == EOF) {
				done = true;
				return;
			}
			if (!line.empty() || overflow) {
				printf("[netplay] ice: %s\n[netplay] ice: paste the joiner's answer code again, "
				       "then Enter:\n",
				       lastErr.c_str());
				fflush(stdout);
			}
		}
	});
	while (!done) {
		if (pump) pump();
		std::this_thread::sleep_for(std::chrono::milliseconds(50));
	}
	reader.join();
	if (answer.empty()) {
		if (err != nullptr)
			*err = lastErr.empty() ? std::string("no answer code on stdin")
			                       : "no valid answer code on stdin (last: " + lastErr + ")";
		return false;
	}
	*answerOut = answer;
	return true;
}

bool ice_host_session(const IceNetConfig& cfg, std::function<void()> pump, IceSocket* outSock,
                      std::string* err)
{
	if (outSock == nullptr) {
		if (err != nullptr) *err = "no socket";
		return false;
	}
	std::string offer;
	if (!outSock->host_create_offer(cfg, &offer, err, pump)) return false;
	if (!ice_emit_code("offer", offer, err)) return false;
	std::string answer;
	if (const char* in = getenv_nonempty("PIKMIN_NETPLAY_ICE_ANSWER_IN")) {
		if (!ice_poll_answer_file(in, ice_connect_timeout_ms(), pump, &answer, err)) return false;
	} else {
		if (!ice_read_answer_stdin(pump, &answer, err)) return false;
	}
	if (!outSock->host_apply_answer(answer, err)) return false;
	double completedMs = -1;
	if (!outSock->wait_connected(ice_connect_timeout_ms(), &completedMs, err, pump)) return false;
	printf("[netplay] ice transport ready (connect %.0fms)\n", completedMs);
	fflush(stdout);
	return true;
}

bool ice_join_session(const IceNetConfig& cfg, const std::string& offerArg,
                      std::function<void()> pump, IceSocket* outSock, std::string* err)
{
	if (outSock == nullptr) {
		if (err != nullptr) *err = "no socket";
		return false;
	}
	std::string offer;
	if (!ice_read_code_arg(offerArg, &offer, err)) return false;
	std::string answer;
	// M3: the joiner pumps while gathering (was: (void)pump, never pumped).
	if (!outSock->join_create_answer(cfg, offer, &answer, err, pump)) return false;
	if (!ice_emit_code("answer", answer, err)) return false;
	double completedMs = -1;
	if (!outSock->wait_connected(ice_connect_timeout_ms(), &completedMs, err, pump)) return false;
	printf("[netplay] ice transport ready (connect %.0fms)\n", completedMs);
	fflush(stdout);
	return true;
}

} // namespace pc_netplay_ice
