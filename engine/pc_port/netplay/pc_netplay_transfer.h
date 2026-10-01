#pragma once
// Netplay M4 lane B2 (issue #885): the handshake Hello v3, the checkpoint
// decision table, the checkpoint / P2 sidecar file bundles, the day-end
// SAVE_RESULT message and the digests they are checked against.
//
// Engine-free and header-only (the C++ standard library only), so the
// session includes it without a new game translation unit and
// pc_netplay_transfer_test links nothing else. Every payload is
// little-endian and every declared length is bounded before allocation.
// Bulk delivery is unordered: nothing here depends on arrival order (bundle
// messages carry their own index and count).
//
// Hello v3 (252 bytes; v1 was 108, v2 116). The 7-byte header and the
// refuse field at offset 107 are stable across versions, so a v1/v2 peer
// still refuses `protocol` fast:
//   0   magic "NPH3"            4
//   4   type (1 Hello, 2 Ack, 3 Refuse)
//   5   protocol u16            (3)
//   7   exe SHA-256             32
//   39  config SHA-256          32
//   71  bootstrap SHA-256       32  (SESSION line stripped)
//   103 netplay seed u32
//   107 refuse field u8
//   108 nonce u64
//   116 ckptGen u64             newest valid campaign checkpoint, 0 = none
//   124 ckptSha[32]             SHA-256 of that %020llu.sav file, zeros = none
//   156 cardSha[32]             card digest (card_digest), zeros = no card file
//   188 sidecarSha[32]          P2 sidecar digest (sidecar_digest), zeros = not P2
//   220 p2AssetsSha[32]         P2 overlay digest (assets_digest), zeros = not P2
//   252 end
//
// Bundle message (kBulkCheckpoint 0x12 / kBulkSidecars 0x16), at most
// kBulkMaxMessage (256 KiB):
//   u16 msgIndex, u16 msgCount, u16 fileCount, then fileCount records
//   {u16 nameLen, name, u32 len, bytes}. Names come from an exact allowlist
//   (checkpoint_name_ok / sidecar_name_ok); duplicates are refused.
//
// kBulkSaveResult 0x11 (host) / kBulkSaveAck 0x13 (client), 81 bytes:
//   u32 frame, u8 ok, u64 gen, u8 savSha[32], u8 cardSha[32],
//   u32 ledgerCount
//   (plan section 2b's 42-byte struct plus the card block digest; gen is
//   u64 like campaignGeneration). ledgerCount (fix round 1, X6): the host's
//   count of kBulkMirrorLedger messages queued this session, including the
//   save tick's flush; the client applies that many before it writes its
//   SAVE_RESULT mirror line. The client sends 0.
//
// kBulkTransferDone 0x15 (joiner to host), 73 bytes:
//   u8 flags (1 checkpoint adopted, 2 sidecars written), u64 gen,
//   u8 ckptSha[32], u8 sidecarSha[32].

#include "netplay/pc_netplay_sha256.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

namespace pc_netplay_xfer {

// ---- handshake ----
constexpr char kHsMagic[4]       = { 'N', 'P', 'H', '3' };
constexpr uint16_t kProtocolV3   = 3; // historical peers
constexpr uint16_t kProtocolV4   = 4; // complete codec3
constexpr size_t kHsHeaderLen    = 7;   // magic + type + proto, every version
constexpr size_t kHsLenV1        = 108; // v1: no nonce
constexpr size_t kHsLenV2        = 116; // v2: + nonce
constexpr size_t kHsLenV3        = 252; // v3: + checkpoint / card / sidecar / assets
constexpr size_t kHsRefuseOffset = 107; // fixed in every version
constexpr uint8_t kHsHello       = 1;
constexpr uint8_t kHsAck         = 2;
constexpr uint8_t kHsRefuse      = 3;

constexpr uint8_t kFieldProto      = 1;
constexpr uint8_t kFieldExe        = 2;
constexpr uint8_t kFieldConfig     = 3;
constexpr uint8_t kFieldBootstrap  = 4;
constexpr uint8_t kFieldSeed       = 5;
constexpr uint8_t kFieldCheckpoint = 6;
constexpr uint8_t kFieldSidecars   = 7;
constexpr uint8_t kFieldP2Assets   = 8;

inline const char* field_name(uint8_t f)
{
	switch (f) {
	case kFieldProto: return "protocol";
	case kFieldExe: return "exe";
	case kFieldConfig: return "config";
	case kFieldBootstrap: return "bootstrap";
	case kFieldSeed: return "seed";
	case kFieldCheckpoint: return "checkpoint";
	case kFieldSidecars: return "sidecars";
	case kFieldP2Assets: return "p2assets";
	default: return "unknown";
	}
}

struct Hello {
	uint8_t exe[32]         = {};
	uint8_t cfg[32]         = {};
	uint8_t boot[32]        = {};
	uint32_t seed           = 0;
	uint64_t nonce          = 0; // Hello: fresh send nonce; Ack: echoed Hello nonce
	uint64_t ckptGen        = 0;
	uint8_t ckptSha[32]     = {};
	uint8_t cardSha[32]     = {};
	uint8_t sidecarSha[32]  = {};
	uint8_t p2AssetsSha[32] = {};
};

inline void put_u16(uint8_t* p, uint16_t v)
{
	p[0] = (uint8_t)(v & 0xFF);
	p[1] = (uint8_t)(v >> 8);
}
inline void put_u32(uint8_t* p, uint32_t v)
{
	for (int b = 0; b < 4; ++b) p[b] = (uint8_t)((v >> (b * 8)) & 0xFF);
}
inline void put_u64(uint8_t* p, uint64_t v)
{
	for (int b = 0; b < 8; ++b) p[b] = (uint8_t)((v >> (b * 8)) & 0xFF);
}
inline uint16_t get_u16(const uint8_t* p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
inline uint32_t get_u32(const uint8_t* p)
{
	return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
inline uint64_t get_u64(const uint8_t* p)
{
	uint64_t v = 0;
	for (int b = 0; b < 8; ++b) v |= (uint64_t)p[b] << (b * 8);
	return v;
}

inline void encode_hello(uint8_t type, uint16_t proto, const Hello& h, uint8_t refuse, uint8_t out[kHsLenV3])
{
	std::memcpy(out, kHsMagic, 4);
	out[4] = type;
	put_u16(out + 5, proto);
	std::memcpy(out + 7, h.exe, 32);
	std::memcpy(out + 39, h.cfg, 32);
	std::memcpy(out + 71, h.boot, 32);
	put_u32(out + 103, h.seed);
	out[kHsRefuseOffset] = refuse;
	put_u64(out + 108, h.nonce);
	put_u64(out + 116, h.ckptGen);
	std::memcpy(out + 124, h.ckptSha, 32);
	std::memcpy(out + 156, h.cardSha, 32);
	std::memcpy(out + 188, h.sidecarSha, 32);
	std::memcpy(out + 220, h.p2AssetsSha, 32);
}

// Stable header parse, valid for any version length.
inline bool decode_hello_header(const uint8_t* p, size_t len, uint8_t* type, uint16_t* proto)
{
	if (p == nullptr || len < kHsHeaderLen || std::memcmp(p, kHsMagic, 4) != 0) return false;
	*type  = p[4];
	*proto = get_u16(p + 5);
	return true;
}

// Full v3 parse: exact length only.
inline bool decode_hello(const uint8_t* p, size_t len, uint8_t* type, uint16_t* proto, Hello* h,
                         uint8_t* refuse)
{
	if (len != kHsLenV3 || !decode_hello_header(p, len, type, proto)) return false;
	std::memcpy(h->exe, p + 7, 32);
	std::memcpy(h->cfg, p + 39, 32);
	std::memcpy(h->boot, p + 71, 32);
	h->seed = get_u32(p + 103);
	*refuse = p[kHsRefuseOffset];
	h->nonce   = get_u64(p + 108);
	h->ckptGen = get_u64(p + 116);
	std::memcpy(h->ckptSha, p + 124, 32);
	std::memcpy(h->cardSha, p + 156, 32);
	std::memcpy(h->sidecarSha, p + 188, 32);
	std::memcpy(h->p2AssetsSha, p + 220, 32);
	return true;
}

// ---- checkpoint decision table (plan section 6b) ----
//
//   host        joiner                               action
//   none        none (same card)                     none
//   G, S        G, S, same card                      in-sync
//   G           none, or gen < G                     transfer
//   G, S        G, S, different card                 transfer (card files only change)
//   none        none, different card                 transfer (the host's card set, maybe empty)
//   G           gen > G, or G with a different sha   refuse checkpoint
//   none        a checkpoint                         refuse checkpoint
//
// A joiner's stale (foreign-fingerprint, damaged or badly named) checkpoint
// is set aside at init and reported as none. Both peers compute this from
// both Hellos, so they always agree.
enum class CkptAction { None, InSync, Transfer, Refuse };

inline const char* action_name(CkptAction a)
{
	switch (a) {
	case CkptAction::None: return "none";
	case CkptAction::InSync: return "in-sync";
	case CkptAction::Transfer: return "transfer";
	case CkptAction::Refuse: return "refuse";
	}
	return "refuse";
}

inline CkptAction decide_checkpoint(const Hello& host, const Hello& joiner, const char** why = nullptr)
{
	auto say = [&](const char* w) {
		if (why != nullptr) *why = w;
	};
	const bool hostHas  = host.ckptGen != 0;
	const bool joinHas  = joiner.ckptGen != 0;
	const bool sameCard = std::memcmp(host.cardSha, joiner.cardSha, 32) == 0;
	if (!hostHas && joinHas) {
		say("the joiner has a checkpoint for this seed but the host has none (the host is behind)");
		return CkptAction::Refuse;
	}
	if (!hostHas) {
		say(sameCard ? "neither peer has a checkpoint" : "no checkpoint; the joiner takes the host's card set");
		return sameCard ? CkptAction::None : CkptAction::Transfer;
	}
	if (!joinHas || joiner.ckptGen < host.ckptGen) {
		say("the joiner is behind the host");
		return CkptAction::Transfer;
	}
	if (joiner.ckptGen > host.ckptGen) {
		say("the joiner is ahead of the host (the host is behind)");
		return CkptAction::Refuse;
	}
	if (std::memcmp(host.ckptSha, joiner.ckptSha, 32) != 0) {
		say("same generation with different checkpoint bytes (the worlds forked)");
		return CkptAction::Refuse;
	}
	say(sameCard ? "same checkpoint and card" : "same checkpoint, different card files");
	return sameCard ? CkptAction::InSync : CkptAction::Transfer;
}

// True when the joiner must receive the host's P2 sidecar set (fix round 1,
// C13: in every mode, and also when the host's set is empty and the
// joiner's is not, so the joiner's extra files are set aside).
inline bool sidecars_needed(const Hello& host, const Hello& joiner)
{
	return std::memcmp(host.sidecarSha, joiner.sidecarSha, 32) != 0;
}

// ---- file bundles ----
struct File {
	std::string name;
	std::string bytes;
};

enum class BundleKind { Checkpoint, Sidecars };

constexpr size_t kMaxBundleMessage   = 262144; // == pc_netplay_bulk::kBulkMaxMessage
constexpr size_t kBundleHeaderLen    = 6;      // msgIndex, msgCount, fileCount
constexpr size_t kMaxBundleName      = 128;
constexpr size_t kMaxBundleFiles     = 256;    // per bundle (all messages)
constexpr size_t kMaxBundleMessages  = 16;
// A file travels in one message: 256 KiB minus the message and record
// headers (a 256 KiB bulk message holds at most this much file data).
constexpr size_t kMaxBundleFileBytes = kMaxBundleMessage - kBundleHeaderLen - 2 - kMaxBundleName - 4;
constexpr size_t kMaxSidecarTotal    = 2u * 1024u * 1024u; // 2 MiB per sidecar set
constexpr size_t kMaxCheckpointTotal = 1024u * 1024u;      // .sav + card files

inline bool is_digit(char c) { return c >= '0' && c <= '9'; }

// `^\d{20}\.sav$`
inline bool is_checkpoint_sav_name(const std::string& n)
{
	if (n.size() != 24 || n.compare(20, 4, ".sav") != 0) return false;
	for (size_t i = 0; i < 20; ++i)
		if (!is_digit(n[i])) return false;
	return true;
}

constexpr const char* kCardDataName = "card/card0/Pikmin dataFile";
constexpr const char* kCardMetaName = "card/card0/.meta_Pikmin dataFile";

inline bool checkpoint_name_ok(const std::string& n)
{
	return is_checkpoint_sav_name(n) || n == kCardDataName || n == kCardMetaName;
}

// The files the native P2 code opens relative to the working directory
// (fix round 1, E3; derived with
//   grep -rhno '"[A-Za-z0-9_./-]*\.\(txt\|json\)"' pc_port/pc_p2_*.cpp):
//   `^(p2|sarai|demon)-[a-z0-9-]+\.txt$`  (demon-*: pc_p2_demon_host.cpp)
//   `^damagumo-[a-z0-9-]+\.json$`        (pc_p2_dangomushi.cpp)
//   `p2_bigtreasure_events.txt`           (pc_p2_hardlanes.cpp)
// p2-binding-receipt.json, *-install.json and overlay-manifest.json are never
// read by the native code and stay out.
inline bool sidecar_name_ok(const std::string& n)
{
	if (n.size() > kMaxBundleName) return false;
	if (n == "p2_bigtreasure_events.txt") return true;
	size_t start = 0, end = 0;
	if (n.size() > 5 && n.compare(n.size() - 4, 4, ".txt") == 0) {
		end = n.size() - 4;
		if (n.compare(0, 3, "p2-") == 0) start = 3;
		else if (n.compare(0, 6, "sarai-") == 0) start = 6;
		else if (n.compare(0, 6, "demon-") == 0) start = 6;
		else return false;
	} else if (n.size() > 5 && n.compare(n.size() - 5, 5, ".json") == 0) {
		end = n.size() - 5;
		if (n.compare(0, 9, "damagumo-") == 0) start = 9;
		else return false;
	} else {
		return false;
	}
	if (end <= start) return false;
	for (size_t i = start; i < end; ++i) {
		const char c = n[i];
		if (!((c >= 'a' && c <= 'z') || is_digit(c) || c == '-')) return false;
	}
	return true;
}

// Names directly in campaign/card/card0/ that the card stub writes for this
// game (card_stubs.cpp dataPath/metaPath with basecardname "Pikmin
// dataFile"). Anything else there cannot travel (fix round 1, C9).
inline bool card_file_name_ok(const std::string& n)
{
	return n == "Pikmin dataFile" || n == ".meta_Pikmin dataFile";
}

inline bool name_ok(BundleKind kind, const std::string& n)
{
	return kind == BundleKind::Checkpoint ? checkpoint_name_ok(n) : sidecar_name_ok(n);
}

// Sorted by name, names unique and allowed, sizes and totals within bounds.
inline bool validate_set(BundleKind kind, const std::vector<File>& files, std::string* err)
{
	auto fail = [&](const std::string& w) {
		if (err != nullptr) *err = w;
		return false;
	};
	if (files.size() > kMaxBundleFiles) return fail("too many files");
	size_t total = 0;
	for (size_t i = 0; i < files.size(); ++i) {
		const File& f = files[i];
		if (!name_ok(kind, f.name)) return fail("file name not allowed: " + f.name);
		if (i > 0 && !(files[i - 1].name < f.name)) return fail("files not sorted or duplicated: " + f.name);
		if (f.bytes.size() > kMaxBundleFileBytes) return fail("file too large: " + f.name);
		total += f.bytes.size();
	}
	if (total > (kind == BundleKind::Sidecars ? kMaxSidecarTotal : kMaxCheckpointTotal))
		return fail("file set too large");
	return true;
}

inline void sort_files(std::vector<File>& files)
{
	std::sort(files.begin(), files.end(), [](const File& a, const File& b) { return a.name < b.name; });
}

// Splits a validated, sorted set into messages of at most kMaxBundleMessage
// bytes, in name order (an empty set is one message with 0 files).
inline bool encode_bundle(BundleKind kind, const std::vector<File>& files,
                          std::vector<std::vector<uint8_t>>* out, std::string* err)
{
	if (!validate_set(kind, files, err)) return false;
	std::vector<std::vector<const File*>> groups(1);
	size_t used = kBundleHeaderLen;
	for (const File& f : files) {
		const size_t rec = 2 + f.name.size() + 4 + f.bytes.size();
		if (used + rec > kMaxBundleMessage && !groups.back().empty()) {
			groups.emplace_back();
			used = kBundleHeaderLen;
		}
		groups.back().push_back(&f);
		used += rec;
	}
	if (groups.size() > kMaxBundleMessages) {
		if (err != nullptr) *err = "file set needs too many messages";
		return false;
	}
	out->clear();
	for (size_t g = 0; g < groups.size(); ++g) {
		std::vector<uint8_t> m(kBundleHeaderLen);
		put_u16(m.data(), (uint16_t)g);
		put_u16(m.data() + 2, (uint16_t)groups.size());
		put_u16(m.data() + 4, (uint16_t)groups[g].size());
		for (const File* f : groups[g]) {
			uint8_t hdr[4];
			put_u16(hdr, (uint16_t)f->name.size());
			m.insert(m.end(), hdr, hdr + 2);
			m.insert(m.end(), f->name.begin(), f->name.end());
			put_u32(hdr, (uint32_t)f->bytes.size());
			m.insert(m.end(), hdr, hdr + 4);
			m.insert(m.end(), f->bytes.begin(), f->bytes.end());
		}
		out->push_back(std::move(m));
	}
	return true;
}

struct BundleMsg {
	uint16_t index = 0;
	uint16_t count = 0;
	std::vector<File> files;
};

// Strict decode of one bundle message: every length is checked against the
// remaining bytes and its bound before anything is allocated.
inline bool decode_bundle(BundleKind kind, const uint8_t* p, size_t len, BundleMsg* out, std::string* err)
{
	auto fail = [&](const std::string& w) {
		if (err != nullptr) *err = w;
		return false;
	};
	if (p == nullptr || len < kBundleHeaderLen || len > kMaxBundleMessage) return fail("bad bundle length");
	out->index = get_u16(p);
	out->count = get_u16(p + 2);
	const uint16_t files = get_u16(p + 4);
	if (out->count == 0 || out->count > kMaxBundleMessages || out->index >= out->count)
		return fail("bad bundle message index/count");
	if (files > kMaxBundleFiles) return fail("too many files in a bundle message");
	out->files.clear();
	size_t off = kBundleHeaderLen;
	for (uint16_t i = 0; i < files; ++i) {
		if (len - off < 2) return fail("truncated file name length");
		const uint16_t nameLen = get_u16(p + off);
		off += 2;
		if (nameLen == 0 || nameLen > kMaxBundleName) return fail("bad file name length");
		if (len - off < nameLen) return fail("truncated file name");
		File f;
		f.name.assign(reinterpret_cast<const char*>(p + off), nameLen);
		off += nameLen;
		if (!name_ok(kind, f.name)) return fail("file name not allowed: " + f.name);
		for (const File& prev : out->files)
			if (prev.name == f.name) return fail("duplicate file: " + f.name);
		if (len - off < 4) return fail("truncated file length");
		const uint32_t fileLen = get_u32(p + off);
		off += 4;
		if (fileLen > kMaxBundleFileBytes) return fail("file too large: " + f.name);
		if (len - off < fileLen) return fail("truncated file bytes: " + f.name);
		f.bytes.assign(reinterpret_cast<const char*>(p + off), fileLen);
		off += fileLen;
		out->files.push_back(std::move(f));
	}
	if (off != len) return fail("trailing bytes after the last file");
	return true;
}

// Joiner side: collects the messages of one bundle in any arrival order.
// complete() once every index 0..count-1 arrived; files() is then the
// sorted union. A message that disagrees with an earlier one on the count
// or repeats a file is refused.
struct BundleCollector {
	uint16_t count = 0;
	std::vector<bool> have;
	std::map<std::string, std::string> byName;
	size_t total = 0;

	bool add(BundleKind kind, const BundleMsg& m, std::string* err)
	{
		if (count == 0) {
			count = m.count;
			have.assign(count, false);
		}
		if (m.count != count) {
			if (err != nullptr) *err = "bundle message count changed";
			return false;
		}
		if (have[m.index]) return true; // duplicate delivery: no-op
		for (const File& f : m.files) {
			if (byName.count(f.name) != 0) {
				if (err != nullptr) *err = "file repeated across bundle messages: " + f.name;
				return false;
			}
			total += f.bytes.size();
			if (total > (kind == BundleKind::Sidecars ? kMaxSidecarTotal : kMaxCheckpointTotal)) {
				if (err != nullptr) *err = "bundle too large";
				return false;
			}
			byName[f.name] = f.bytes;
		}
		have[m.index] = true;
		return true;
	}
	bool complete() const
	{
		if (count == 0) return false;
		for (bool h : have)
			if (!h) return false;
		return true;
	}
	std::vector<File> files() const
	{
		std::vector<File> out;
		for (const auto& kv : byName) out.push_back(File{ kv.first, kv.second });
		return out; // std::map order == name order
	}
};

// ---- digests (all zeros for an empty set) ----
inline void zero32(uint8_t out[32]) { std::memset(out, 0, 32); }

// Card digest: SHA-256 over (u16 nameLen, name, u32 len, bytes) records of
// the card files, sorted by name (names are relative to card0/).
inline void card_digest(const std::vector<File>& sortedFiles, uint8_t out[32])
{
	if (sortedFiles.empty()) {
		zero32(out);
		return;
	}
	pc_netplay_sha::Sha256 s;
	for (const File& f : sortedFiles) {
		uint8_t hdr[4];
		put_u16(hdr, (uint16_t)f.name.size());
		s.update(hdr, 2);
		s.update(f.name.data(), f.name.size());
		put_u32(hdr, (uint32_t)f.bytes.size());
		s.update(hdr, 4);
		s.update(f.bytes.data(), f.bytes.size());
	}
	s.final(out);
}

// Sidecar digest: SHA-256 over (u16 nameLen, name, u32 len, SHA-256 of the
// file) records, sorted by name.
inline void sidecar_digest(const std::vector<File>& sortedFiles, uint8_t out[32])
{
	if (sortedFiles.empty()) {
		zero32(out);
		return;
	}
	pc_netplay_sha::Sha256 s;
	for (const File& f : sortedFiles) {
		uint8_t hdr[4];
		uint8_t sha[32];
		pc_netplay_sha::sha256(f.bytes.data(), f.bytes.size(), sha);
		put_u16(hdr, (uint16_t)f.name.size());
		s.update(hdr, 2);
		s.update(f.name.data(), f.name.size());
		put_u32(hdr, (uint32_t)f.bytes.size());
		s.update(hdr, 4);
		s.update(sha, 32);
	}
	s.final(out);
}

// P2 overlay digest: SHA-256 over (u16 pathLen, relative path, file SHA-256)
// records sorted by path ('/'-separated, relative to assets/). The overlay
// content itself is never sent.
struct AssetEntry {
	std::string path;
	uint8_t sha[32];
};
inline void assets_digest(std::vector<AssetEntry> entries, uint8_t out[32])
{
	if (entries.empty()) {
		zero32(out);
		return;
	}
	std::sort(entries.begin(), entries.end(), [](const AssetEntry& a, const AssetEntry& b) { return a.path < b.path; });
	pc_netplay_sha::Sha256 s;
	for (const AssetEntry& e : entries) {
		uint8_t hdr[2];
		put_u16(hdr, (uint16_t)e.path.size());
		s.update(hdr, 2);
		s.update(e.path.data(), e.path.size());
		s.update(e.sha, 32);
	}
	s.final(out);
}

// ---- day-end SAVE_RESULT / SAVE_ACK ----
constexpr size_t kSaveResultLen = 4 + 1 + 8 + 32 + 32 + 4; // 81
struct SaveResult {
	uint32_t frame     = 0;
	uint8_t ok         = 0;
	uint64_t gen       = 0;
	uint8_t savSha[32] = {};
	uint8_t cardSha[32] = {};
	uint32_t ledgerCount = 0;
};
inline std::vector<uint8_t> encode_save_result(const SaveResult& r)
{
	std::vector<uint8_t> m(kSaveResultLen);
	put_u32(m.data(), r.frame);
	m[4] = r.ok;
	put_u64(m.data() + 5, r.gen);
	std::memcpy(m.data() + 13, r.savSha, 32);
	std::memcpy(m.data() + 45, r.cardSha, 32);
	put_u32(m.data() + 77, r.ledgerCount);
	return m;
}
inline bool decode_save_result(const uint8_t* p, size_t len, SaveResult* r)
{
	if (p == nullptr || len != kSaveResultLen || p[4] > 1) return false;
	r->frame = get_u32(p);
	r->ok    = p[4];
	r->gen   = get_u64(p + 5);
	std::memcpy(r->savSha, p + 13, 32);
	std::memcpy(r->cardSha, p + 45, 32);
	r->ledgerCount = get_u32(p + 77);
	return true;
}

// The day-end barrier's desync checks (fix round 1, C1/C6), one pure
// function so both roles apply exactly the same rules to the same pair of
// results (host and client each pass their own as `mine`): the generation,
// then the 0x8000 game-file block digest (whatever the ok flags), then,
// when both checkpoints were written, the checkpoint file digest.
enum class BarrierVerdict { Agree, GenMismatch, BlockMismatch, DigestMismatch };
inline BarrierVerdict barrier_verdict(const SaveResult& mine, const SaveResult& peer)
{
	if (mine.gen != peer.gen) return BarrierVerdict::GenMismatch;
	if (std::memcmp(mine.cardSha, peer.cardSha, 32) != 0) return BarrierVerdict::BlockMismatch;
	if (mine.ok && peer.ok && std::memcmp(mine.savSha, peer.savSha, 32) != 0) return BarrierVerdict::DigestMismatch;
	return BarrierVerdict::Agree;
}

// ---- kBulkTransferDone ----
constexpr uint8_t kDoneCheckpoint = 1;
constexpr uint8_t kDoneSidecars   = 2;
constexpr size_t kTransferDoneLen = 1 + 8 + 32 + 32; // 73
struct TransferDone {
	uint8_t flags          = 0;
	uint64_t gen           = 0;
	uint8_t ckptSha[32]    = {};
	uint8_t sidecarSha[32] = {};
};
inline std::vector<uint8_t> encode_transfer_done(const TransferDone& d)
{
	std::vector<uint8_t> m(kTransferDoneLen);
	m[0] = d.flags;
	put_u64(m.data() + 1, d.gen);
	std::memcpy(m.data() + 9, d.ckptSha, 32);
	std::memcpy(m.data() + 41, d.sidecarSha, 32);
	return m;
}
inline bool decode_transfer_done(const uint8_t* p, size_t len, TransferDone* d)
{
	if (p == nullptr || len != kTransferDoneLen || (p[0] & ~(kDoneCheckpoint | kDoneSidecars)) != 0) return false;
	d->flags = p[0];
	d->gen   = get_u64(p + 1);
	std::memcpy(d->ckptSha, p + 9, 32);
	std::memcpy(d->sidecarSha, p + 41, 32);
	return true;
}

// ---- joiner checks for a completed checkpoint bundle ----
// The set must hold exactly: the host's checkpoint (when it has one), named
// %020llu.sav for ckptGen with SHA-256 == ckptSha, and card files whose
// card_digest (over names relative to card0/) equals cardSha.
inline bool verify_checkpoint_set(const std::vector<File>& files, const Hello& host, std::string* err)
{
	auto fail = [&](const std::string& w) {
		if (err != nullptr) *err = w;
		return false;
	};
	char want[32];
	std::snprintf(want, sizeof(want), "%020llu.sav", (unsigned long long)host.ckptGen);
	bool haveSav = false;
	std::vector<File> card;
	for (const File& f : files) {
		if (is_checkpoint_sav_name(f.name)) {
			if (host.ckptGen == 0 || f.name != want) return fail("unexpected checkpoint file " + f.name);
			uint8_t sha[32];
			pc_netplay_sha::sha256(f.bytes.data(), f.bytes.size(), sha);
			if (std::memcmp(sha, host.ckptSha, 32) != 0) return fail("checkpoint " + f.name + " does not match the host's digest");
			haveSav = true;
		} else {
			card.push_back(File{ f.name.substr(std::strlen("card/card0/")), f.bytes });
		}
	}
	if (host.ckptGen != 0 && !haveSav) return fail(std::string("the host's checkpoint ") + want + " is missing");
	sort_files(card);
	uint8_t cs[32];
	card_digest(card, cs);
	if (std::memcmp(cs, host.cardSha, 32) != 0) return fail("card files do not match the host's card digest");
	return true;
}

} // namespace pc_netplay_xfer
