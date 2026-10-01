// Netplay M4 lane B2 unit test (issue #885): the engine-free pieces of the
// day-end save barrier, the checkpoint transfer and the P2 sidecar transfer
// (pc_netplay_transfer.h, pc_netplay_sha256.h):
//   1. SHA-256 against the FIPS 180-2 vectors;
//   2. Hello v3 encode/parse, the stable header, the refuse field at offset
//      107, and the refuse field names;
//   3. the checkpoint decision table (every row) and sidecars_needed;
//   4. the checkpoint and sidecar bundle codecs: allowlists, bounds,
//      oversize and malformed rejections, multi-message splits, the
//      unordered collector;
//   5. verify_checkpoint_set and the card / sidecar / overlay digests;
//   6. the SAVE_RESULT and TRANSFER_DONE codecs.

#include "netplay/pc_netplay_transfer.h"

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

namespace {

int sFailures = 0;
int sChecks = 0;

void check(bool ok, const char* what, int line)
{
	++sChecks;
	if (!ok) {
		++sFailures;
		std::printf("FAIL line %d: %s\n", line, what);
	}
}
#define CHECK(ok, what) check((ok), (what), __LINE__)

using namespace pc_netplay_xfer;

std::string sha_hex(const std::string& s)
{
	uint8_t d[32];
	pc_netplay_sha::sha256(s.data(), s.size(), d);
	return pc_netplay_sha::hex(d, 32);
}

void fill(uint8_t* p, uint8_t v)
{
	for (int i = 0; i < 32; ++i) p[i] = (uint8_t)(v + i);
}

Hello hello_with(uint64_t gen, uint8_t ckpt, uint8_t card)
{
	Hello h;
	h.ckptGen = gen;
	if (gen != 0) fill(h.ckptSha, ckpt);
	if (card != 0) fill(h.cardSha, card);
	return h;
}

std::vector<uint8_t> raw_bundle(uint16_t idx, uint16_t count, const std::vector<std::pair<std::string, std::string>>& files)
{
	std::vector<uint8_t> m(6);
	put_u16(m.data(), idx);
	put_u16(m.data() + 2, count);
	put_u16(m.data() + 4, (uint16_t)files.size());
	for (const auto& f : files) {
		uint8_t h[4];
		put_u16(h, (uint16_t)f.first.size());
		m.insert(m.end(), h, h + 2);
		m.insert(m.end(), f.first.begin(), f.first.end());
		put_u32(h, (uint32_t)f.second.size());
		m.insert(m.end(), h, h + 4);
		m.insert(m.end(), f.second.begin(), f.second.end());
	}
	return m;
}

} // namespace

int main()
{
	// 1. SHA-256 (FIPS 180-2 examples + the 56-byte padding edge).
	CHECK(sha_hex("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "sha256 empty");
	CHECK(sha_hex("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "sha256 abc");
	CHECK(sha_hex("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq")
	          == "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
	      "sha256 448-bit message (the 56-byte padding edge)");
	{
		pc_netplay_sha::Sha256 s;
		const std::string chunk(1000, 'a');
		for (int i = 0; i < 1000; ++i) s.update(chunk.data(), chunk.size());
		uint8_t d[32];
		s.final(d);
		CHECK(pc_netplay_sha::hex(d, 32) == "cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0",
		      "sha256 one million 'a' in 1000-byte updates");
	}

	// 2. Hello v3.
	{
		Hello h;
		fill(h.exe, 1);
		fill(h.cfg, 2);
		fill(h.boot, 3);
		h.seed    = 0xA1B2C3D4u;
		h.nonce   = 0x1122334455667788ull;
		h.ckptGen = 0x0102030405060708ull;
		fill(h.ckptSha, 4);
		fill(h.cardSha, 5);
		fill(h.sidecarSha, 6);
		fill(h.p2AssetsSha, 7);
		uint8_t wire[kHsLenV3];
		encode_hello(kHsAck, kProtocolV3, h, kFieldSidecars, wire);
		CHECK(kHsLenV3 == 252 && kHsRefuseOffset == 107, "v3 length 252, refuse field at 107");
		CHECK(std::memcmp(wire, "NPH3", 4) == 0 && wire[4] == kHsAck && wire[5] == 3 && wire[6] == 0, "stable header");
		CHECK(wire[107] == kFieldSidecars, "refuse field at offset 107");
		CHECK(wire[116] == 0x08 && wire[123] == 0x01, "ckptGen little-endian at 116");
		CHECK(wire[124] == 4 && wire[156] == 5 && wire[188] == 6 && wire[220] == 7, "digest offsets 124/156/188/220");
		uint8_t type = 0, refuse = 0;
		uint16_t proto = 0;
		Hello g;
		CHECK(decode_hello(wire, sizeof(wire), &type, &proto, &g, &refuse), "v3 decode");
		CHECK(type == kHsAck && proto == 3 && refuse == kFieldSidecars && g.seed == h.seed && g.nonce == h.nonce
		          && g.ckptGen == h.ckptGen && std::memcmp(g.exe, h.exe, 32) == 0 && std::memcmp(g.cfg, h.cfg, 32) == 0
		          && std::memcmp(g.boot, h.boot, 32) == 0 && std::memcmp(g.ckptSha, h.ckptSha, 32) == 0
		          && std::memcmp(g.cardSha, h.cardSha, 32) == 0 && std::memcmp(g.sidecarSha, h.sidecarSha, 32) == 0
		          && std::memcmp(g.p2AssetsSha, h.p2AssetsSha, 32) == 0,
		      "v3 round trip");
        encode_hello(kHsAck, kProtocolV4, h, 0, wire);
        CHECK(decode_hello(wire, sizeof(wire), &type, &proto, &g, &refuse) && proto == 4,
              "codec3 uses protocol4 without changing the stable header/layout");
        for (uint16_t remote : {kProtocolV3, kProtocolV4}) {
            encode_hello(kHsHello, remote, h, 0, wire);
            CHECK(decode_hello_header(wire, sizeof(wire), &type, &proto) && proto == remote,
                  "old and current protocol identifiable before full body parsing");
            CHECK((proto != kProtocolV4) == (remote == kProtocolV3), "version3 cannot enter version4 session");
        }
        encode_hello(kHsAck, kProtocolV3, h, kFieldSidecars, wire); // Restore the legacy vector after protocol4 checks.
		CHECK(!decode_hello(wire, kHsLenV2, &type, &proto, &g, &refuse), "a v2-length frame is not a v3 Hello");
		CHECK(!decode_hello(wire, kHsLenV1, &type, &proto, &g, &refuse), "a v1-length frame is not a v3 Hello");
		CHECK(!decode_hello(wire, kHsLenV3 + 1, &type, &proto, &g, &refuse), "an over-long frame is refused");
		CHECK(decode_hello_header(wire, kHsLenV1, &type, &proto) && proto == 3,
		      "the stable header parses at any version length (fast protocol refusal)");
		wire[2] = 'X';
		CHECK(!decode_hello_header(wire, sizeof(wire), &type, &proto)
		          && !decode_hello(wire, sizeof(wire), &type, &proto, &g, &refuse),
		      "bad magic refused");
		CHECK(!decode_hello_header(wire, 6, &type, &proto), "a frame shorter than the header is refused");
		CHECK(std::strcmp(field_name(kFieldCheckpoint), "checkpoint") == 0
		          && std::strcmp(field_name(kFieldSidecars), "sidecars") == 0
		          && std::strcmp(field_name(kFieldP2Assets), "p2assets") == 0
		          && std::strcmp(field_name(kFieldSeed), "seed") == 0 && std::strcmp(field_name(99), "unknown") == 0,
		      "refuse field names 6/7/8");
		CHECK(kFieldCheckpoint == 6 && kFieldSidecars == 7 && kFieldP2Assets == 8, "refuse field ids");
	}

	// 3. Decision table.
	{
		const char* why = nullptr;
		CHECK(decide_checkpoint(hello_with(0, 0, 0), hello_with(0, 0, 0), &why) == CkptAction::None, "none/none");
		CHECK(decide_checkpoint(hello_with(0, 0, 9), hello_with(0, 0, 9)) == CkptAction::None, "none/none same card");
		CHECK(decide_checkpoint(hello_with(0, 0, 9), hello_with(0, 0, 8)) == CkptAction::Transfer,
		      "none/none, different card: the joiner takes the host's card set");
		CHECK(decide_checkpoint(hello_with(3, 1, 9), hello_with(3, 1, 9)) == CkptAction::InSync, "G,S / G,S in-sync");
		CHECK(decide_checkpoint(hello_with(3, 1, 9), hello_with(3, 1, 8)) == CkptAction::Transfer,
		      "G,S / G,S with a different card: transfer");
		CHECK(decide_checkpoint(hello_with(3, 1, 9), hello_with(0, 0, 0)) == CkptAction::Transfer, "G / none: transfer");
		CHECK(decide_checkpoint(hello_with(3, 1, 9), hello_with(2, 5, 9)) == CkptAction::Transfer, "G / older: transfer");
		CHECK(decide_checkpoint(hello_with(3, 1, 9), hello_with(4, 1, 9)) == CkptAction::Refuse, "G / newer: refuse");
		CHECK(decide_checkpoint(hello_with(3, 1, 9), hello_with(3, 2, 9)) == CkptAction::Refuse,
		      "G / same gen, different sha: refuse (forked)");
		CHECK(decide_checkpoint(hello_with(0, 0, 0), hello_with(1, 1, 9), &why) == CkptAction::Refuse && why != nullptr,
		      "none / a checkpoint: refuse (the host is behind)");
		CHECK(std::strcmp(action_name(CkptAction::InSync), "in-sync") == 0
		          && std::strcmp(action_name(CkptAction::Transfer), "transfer") == 0
		          && std::strcmp(action_name(CkptAction::None), "none") == 0,
		      "action names");
		Hello a, b;
		CHECK(!sidecars_needed(a, b), "no sidecars: nothing to send");
		fill(a.sidecarSha, 3);
		CHECK(sidecars_needed(a, b), "host sidecars, joiner none: send");
		std::memcpy(b.sidecarSha, a.sidecarSha, 32);
		CHECK(!sidecars_needed(a, b), "same sidecar digest: nothing to send");
		// Fix round 1 (C13): an empty host set against a non-empty joiner set
		// is a transfer too (the joiner's files are set aside).
		Hello c;
		CHECK(sidecars_needed(c, b), "host none, joiner sidecars: send the empty set");
	}

	// 4. Bundles.
	{
		CHECK(checkpoint_name_ok("00000000000000000001.sav") && checkpoint_name_ok(kCardDataName)
		          && checkpoint_name_ok(kCardMetaName),
		      "checkpoint allowlist accepts the exact names");
		CHECK(!checkpoint_name_ok("0000000000000000001.sav") && !checkpoint_name_ok("0000000000000000000a.sav")
		          && !checkpoint_name_ok("00000000000000000001.sav.stale-1") && !checkpoint_name_ok("../00000000000000000001.sav")
		          && !checkpoint_name_ok("card/card0/Other") && !checkpoint_name_ok("card/card1/Pikmin dataFile")
		          && !checkpoint_name_ok("p2-delivery-receipts.txt"),
		      "checkpoint allowlist refuses everything else");
		CHECK(sidecar_name_ok("p2-aquatic-actors.txt") && sidecar_name_ok("sarai-waitact1-poses.txt")
		          && sidecar_name_ok("p2-x.txt"),
		      "sidecar regex accepts p2-/sarai- names");
		// Fix round 1 (E3): every file the P2 code opens cwd-relative.
		CHECK(sidecar_name_ok("demon-mouths.txt") && sidecar_name_ok("demon-waitact2-poses.txt")
		          && sidecar_name_ok("demon-host-bindings.txt") && sidecar_name_ok("damagumo-family.json")
		          && sidecar_name_ok("damagumo-slot-312004.json") && sidecar_name_ok("p2_bigtreasure_events.txt")
		          && sidecar_name_ok("p2-flora-receipts.txt"),
		      "sidecar allowlist accepts demon-*.txt, damagumo-*.json, p2_bigtreasure_events.txt");
		CHECK(!sidecar_name_ok("p2-.txt") && !sidecar_name_ok("p2-Upper.txt") && !sidecar_name_ok("p2-a.json")
		          && !sidecar_name_ok("p2_a.txt") && !sidecar_name_ok("demon-.txt") && !sidecar_name_ok("../p2-a.txt")
		          && !sidecar_name_ok("p2-a b.txt") && !sidecar_name_ok("p2-binding-receipt.json")
		          && !sidecar_name_ok("damagumo-.json") && !sidecar_name_ok("damagumo-family.txt")
		          && !sidecar_name_ok("demon-a.json") && !sidecar_name_ok("aquatic-install.json")
		          && !sidecar_name_ok("overlay-manifest.json") && !sidecar_name_ok("p2_bigtreasure_events.txt.tmp")
		          && !sidecar_name_ok("p2-a.txt.tmp") && !sidecar_name_ok(std::string(200, 'a')),
		      "sidecar allowlist refuses everything else");
		CHECK(card_file_name_ok("Pikmin dataFile") && card_file_name_ok(".meta_Pikmin dataFile")
		          && !card_file_name_ok("Pikmin dataFile.xfer-tmp") && !card_file_name_ok("Other")
		          && !card_file_name_ok("card0/Pikmin dataFile"),
		      "card file names: exactly the two the card stub writes");

		// Round trip, split over several messages.
		std::vector<File> set;
		set.push_back(File{ "00000000000000000002.sav", std::string(33000, 'S') });
		set.push_back(File{ kCardMetaName, std::string(108, 'M') });
		set.push_back(File{ kCardDataName, std::string(155648, 'C') });
		sort_files(set);
		std::vector<std::vector<uint8_t>> msgs;
		std::string err;
		CHECK(encode_bundle(BundleKind::Checkpoint, set, &msgs, &err) && msgs.size() == 1,
		      "a real checkpoint set (sav + 152 KiB card + meta) fits one message");
		CHECK(!msgs.empty() && msgs[0].size() <= kMaxBundleMessage, "within 256 KiB");
		BundleMsg m;
		CHECK(!msgs.empty() && decode_bundle(BundleKind::Checkpoint, msgs[0].data(), msgs[0].size(), &m, &err)
		          && m.index == 0 && m.count == 1 && m.files.size() == 3,
		      "decode");
		std::vector<File> big;
		for (int i = 0; i < 12; ++i) {
			char n[32];
			std::snprintf(n, sizeof(n), "p2-file-%02d.txt", i);
			big.push_back(File{ n, std::string(150000, (char)('a' + i)) });
		}
		std::vector<std::vector<uint8_t>> bmsgs;
		CHECK(encode_bundle(BundleKind::Sidecars, big, &bmsgs, &err) && bmsgs.size() >= 7,
		      "a 1.7 MiB sidecar set splits into several <= 256 KiB messages");
		BundleCollector col;
		bool addOk = true;
		for (size_t i = bmsgs.size(); i-- > 0;) {
			BundleMsg bm;
			addOk = addOk && decode_bundle(BundleKind::Sidecars, bmsgs[i].data(), bmsgs[i].size(), &bm, &err)
			     && bm.count == bmsgs.size() && col.add(BundleKind::Sidecars, bm, &err);
			if (i == bmsgs.size() - 1) CHECK(!col.complete() || bmsgs.size() == 1, "incomplete after one message");
			addOk = addOk && col.add(BundleKind::Sidecars, bm, &err); // duplicate delivery: no-op
		}
		CHECK(addOk && col.complete(), "collector completes in reverse arrival order, duplicates are no-ops");
		const std::vector<File> got = col.files();
		bool same = got.size() == big.size();
		for (size_t i = 0; same && i < got.size(); ++i) same = got[i].name == big[i].name && got[i].bytes == big[i].bytes;
		CHECK(same, "collector reassembles the exact sorted set");
		uint8_t d1[32], d2[32];
		sidecar_digest(big, d1);
		sidecar_digest(got, d2);
		CHECK(std::memcmp(d1, d2, 32) == 0, "sidecar digest round trip");

		// Rejections.
		std::vector<File> bad = { File{ "p2-a.txt", "x" }, File{ "p2-a.txt", "y" } };
		CHECK(!encode_bundle(BundleKind::Sidecars, bad, &msgs, &err), "duplicate names refused");
		bad = { File{ "p2-b.txt", "x" }, File{ "p2-a.txt", "y" } };
		CHECK(!encode_bundle(BundleKind::Sidecars, bad, &msgs, &err), "unsorted set refused");
		bad = { File{ "p2-a.txt", std::string(kMaxBundleFileBytes + 1, 'x') } };
		CHECK(!encode_bundle(BundleKind::Sidecars, bad, &msgs, &err), "oversize file refused");
		bad.clear();
		for (int i = 0; i < 9; ++i) {
			char n[32];
			std::snprintf(n, sizeof(n), "p2-t%d.txt", i);
			bad.push_back(File{ n, std::string(250000, 'z') });
		}
		CHECK(!encode_bundle(BundleKind::Sidecars, bad, &msgs, &err), "sidecar set over 2 MiB refused");
		bad = { File{ "evil.dll", "x" } };
		CHECK(!encode_bundle(BundleKind::Checkpoint, bad, &msgs, &err), "name outside the checkpoint allowlist refused");
		CHECK(!encode_bundle(BundleKind::Sidecars, set, &msgs, &err), "checkpoint names are not sidecars");

		BundleMsg x;
		std::vector<uint8_t> r = raw_bundle(0, 1, { { "p2-a.txt", "hello" } });
		CHECK(decode_bundle(BundleKind::Sidecars, r.data(), r.size(), &x, &err), "raw bundle decodes");
		std::vector<uint8_t> t = r;
		t.push_back(0);
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "trailing byte refused");
		t = r;
		t.pop_back();
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "truncated file bytes refused");
		CHECK(!decode_bundle(BundleKind::Sidecars, r.data(), 5, &x, &err), "truncated header refused");
		t = r;
		put_u32(t.data() + 6 + 2 + 8, 0xFFFFFFF0u);
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err),
		      "a huge declared file length is refused before allocation");
		t = r;
		put_u16(t.data() + 6, 0);
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "zero name length refused");
		t = r;
		put_u16(t.data() + 6, 500);
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "over-long name length refused");
		t = raw_bundle(1, 1, { { "p2-a.txt", "x" } });
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "index >= count refused");
		t = raw_bundle(0, 0, {});
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "count 0 refused");
		t = raw_bundle(0, 17, {});
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "too many messages refused");
		t = raw_bundle(0, 1, { { "p2-a.txt", "x" }, { "p2-a.txt", "y" } });
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "duplicate file in a message refused");
		t = raw_bundle(0, 1, { { "../p2-a.txt", "x" } });
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err), "path traversal refused");
		t = raw_bundle(0, 1, { { "card/card0/Pikmin dataFile", "x" } });
		CHECK(!decode_bundle(BundleKind::Sidecars, t.data(), t.size(), &x, &err)
		          && decode_bundle(BundleKind::Checkpoint, t.data(), t.size(), &x, &err),
		      "the kind's allowlist applies");
		std::vector<uint8_t> huge(kMaxBundleMessage + 1, 0);
		CHECK(!decode_bundle(BundleKind::Checkpoint, huge.data(), huge.size(), &x, &err), "message over 256 KiB refused");
		BundleCollector c2;
		BundleMsg a1, a2;
		std::vector<uint8_t> m1 = raw_bundle(0, 2, { { "p2-a.txt", "x" } });
		std::vector<uint8_t> m2 = raw_bundle(1, 3, { { "p2-b.txt", "y" } });
		decode_bundle(BundleKind::Sidecars, m1.data(), m1.size(), &a1, &err);
		decode_bundle(BundleKind::Sidecars, m2.data(), m2.size(), &a2, &err);
		CHECK(c2.add(BundleKind::Sidecars, a1, &err) && !c2.add(BundleKind::Sidecars, a2, &err),
		      "a message with another count is refused");
		BundleCollector c3;
		std::vector<uint8_t> m3 = raw_bundle(1, 2, { { "p2-a.txt", "z" } });
		BundleMsg a3;
		decode_bundle(BundleKind::Sidecars, m3.data(), m3.size(), &a3, &err);
		CHECK(c3.add(BundleKind::Sidecars, a1, &err) && !c3.add(BundleKind::Sidecars, a3, &err),
		      "a file repeated across messages is refused");
	}

	// 5. verify_checkpoint_set + digests.
	{
		const std::string sav(33000, 'S');
		std::vector<File> card = { File{ ".meta_Pikmin dataFile", std::string(108, 'M') },
			                       File{ "Pikmin dataFile", std::string(1000, 'C') } };
		sort_files(card);
		Hello host;
		host.ckptGen = 2;
		pc_netplay_sha::sha256(sav.data(), sav.size(), host.ckptSha);
		card_digest(card, host.cardSha);
		std::vector<File> files = { File{ "00000000000000000002.sav", sav } };
		for (const File& f : card) files.push_back(File{ "card/card0/" + f.name, f.bytes });
		sort_files(files);
		std::string err;
		CHECK(verify_checkpoint_set(files, host, &err), "the host's exact set verifies");
		std::vector<File> f2 = files;
		for (File& f : f2)
			if (f.name == "00000000000000000002.sav") f.bytes[5] ^= 1;
		CHECK(!verify_checkpoint_set(f2, host, &err), "a changed checkpoint byte is refused");
		f2 = files;
		for (File& f : f2)
			if (f.name == kCardDataName) f.bytes[5] ^= 1;
		CHECK(!verify_checkpoint_set(f2, host, &err), "a changed card byte is refused");
		f2.clear();
		for (const File& f : files)
			if (f.name != "00000000000000000002.sav") f2.push_back(f);
		CHECK(!verify_checkpoint_set(f2, host, &err), "a missing checkpoint is refused");
		f2 = files;
		for (File& f : f2)
			if (f.name == "00000000000000000002.sav") f.name = "00000000000000000003.sav";
		sort_files(f2);
		CHECK(!verify_checkpoint_set(f2, host, &err), "a checkpoint of another generation is refused");
		f2.clear();
		for (const File& f : files)
			if (f.name != kCardMetaName) f2.push_back(f);
		CHECK(!verify_checkpoint_set(f2, host, &err), "a missing card file is refused");
		Hello none;
		CHECK(verify_checkpoint_set(std::vector<File>(), none, &err), "no checkpoint, no card: the empty set verifies");
		uint8_t z[32];
		card_digest(std::vector<File>(), z);
		CHECK(pc_netplay_sha::is_zero(z, 32), "empty card digest is zeros");
		sidecar_digest(std::vector<File>(), z);
		CHECK(pc_netplay_sha::is_zero(z, 32), "empty sidecar digest is zeros");
		std::vector<AssetEntry> e1(2), e2(2);
		e1[0].path = "dataDir/courses/pikmin2room/a.mod";
		fill(e1[0].sha, 1);
		e1[1].path = "p2-x.txt";
		fill(e1[1].sha, 2);
		e2[0] = e1[1];
		e2[1] = e1[0];
		uint8_t a1[32], a2[32];
		assets_digest(e1, a1);
		assets_digest(e2, a2);
		CHECK(std::memcmp(a1, a2, 32) == 0 && !pc_netplay_sha::is_zero(a1, 32), "overlay digest is order independent");
		e2[1].sha[0] ^= 1;
		assets_digest(e2, a2);
		CHECK(std::memcmp(a1, a2, 32) != 0, "one changed overlay file changes the digest");
		std::vector<File> s1 = { File{ "p2-a.txt", "one" } }, s2 = { File{ "p2-a.txt", "two" } };
		uint8_t d1[32], d2[32];
		sidecar_digest(s1, d1);
		sidecar_digest(s2, d2);
		CHECK(std::memcmp(d1, d2, 32) != 0, "one changed sidecar changes the digest");
	}

	// 6. SAVE_RESULT / TRANSFER_DONE.
	{
		SaveResult r;
		r.frame = 27100;
		r.ok    = 1;
		r.gen   = 7;
		fill(r.savSha, 9);
		fill(r.cardSha, 10);
		r.ledgerCount = 0x01020304u;
		const std::vector<uint8_t> w = encode_save_result(r);
		CHECK(w.size() == 81 && kSaveResultLen == 81, "SAVE_RESULT is 81 bytes");
		CHECK(w[77] == 4 && w[78] == 3 && w[79] == 2 && w[80] == 1, "ledgerCount is a little-endian u32 at 77");
		SaveResult g;
		CHECK(decode_save_result(w.data(), w.size(), &g) && g.frame == 27100 && g.ok == 1 && g.gen == 7
		          && std::memcmp(g.savSha, r.savSha, 32) == 0 && std::memcmp(g.cardSha, r.cardSha, 32) == 0
		          && g.ledgerCount == 0x01020304u,
		      "SAVE_RESULT round trip");
		CHECK(!decode_save_result(w.data(), 80, &g) && !decode_save_result(w.data(), 77, &g),
		      "short (and the old 77-byte) SAVE_RESULT refused");
		// Fix round 1 (C1/C6): the barrier verdict is the same function on both
		// roles; every mismatch must be seen from either side.
		{
			SaveResult h = r, c = r; // host and client, agreeing
			auto both = [&](BarrierVerdict want) {
				return barrier_verdict(h, c) == want && barrier_verdict(c, h) == want;
			};
			CHECK(both(BarrierVerdict::Agree), "agreeing results: agree on both roles");
			c.savSha[5] ^= 1;
			CHECK(both(BarrierVerdict::DigestMismatch), "both ok, different .sav digest: mismatch on the host too");
			c.ok = 0;
			CHECK(both(BarrierVerdict::Agree), "a failed local write: its (zero) .sav digest is not compared");
			c.ok = 1;
			std::memcpy(c.savSha, h.savSha, 32);
			c.cardSha[0] ^= 1;
			CHECK(both(BarrierVerdict::BlockMismatch), "different game-file block: mismatch on both roles");
			c.ok = 0;
			CHECK(both(BarrierVerdict::BlockMismatch), "block mismatch whatever the ok flags");
			std::memcpy(c.cardSha, h.cardSha, 32);
			c.ok  = 1;
			c.gen = h.gen + 1;
			CHECK(both(BarrierVerdict::GenMismatch), "different generation: mismatch on both roles");
		}
		std::vector<uint8_t> bad = w;
		bad[4]                   = 2;
		CHECK(!decode_save_result(bad.data(), bad.size(), &g), "ok must be 0 or 1");
		TransferDone d;
		d.flags = kDoneCheckpoint | kDoneSidecars;
		d.gen   = 3;
		fill(d.ckptSha, 1);
		fill(d.sidecarSha, 2);
		const std::vector<uint8_t> dw = encode_transfer_done(d);
		TransferDone e;
		CHECK(dw.size() == 73 && decode_transfer_done(dw.data(), dw.size(), &e) && e.flags == 3 && e.gen == 3
		          && std::memcmp(e.ckptSha, d.ckptSha, 32) == 0 && std::memcmp(e.sidecarSha, d.sidecarSha, 32) == 0,
		      "TRANSFER_DONE round trip");
		bad = dw;
		bad[0] = 4;
		CHECK(!decode_transfer_done(bad.data(), bad.size(), &e) && !decode_transfer_done(dw.data(), 72, &e),
		      "unknown flags / short TRANSFER_DONE refused");
	}

	std::printf("pc_netplay_transfer_test: %s (%d checks, %d failures)\n", sFailures == 0 ? "PASS" : "FAIL", sChecks,
	            sFailures);
	return sFailures == 0 ? 0 : 1;
}
