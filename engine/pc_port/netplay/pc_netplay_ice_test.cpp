// Netplay M5a host-run ICE test (issue #887).
//
// Two libjuice agents in one process connect with host candidates only
// (no STUN/TURN, so no external network is required). m4: libjuice excludes
// 127.x candidates unless JUICE_ENABLE_LOCALHOST_ADDRESS=1, so the selected
// pair is normally a LAN host candidate (for example 192.168.x), not
// loopback. The test therefore needs a live non-loopback IPv4 interface and
// may fail offline or on CI without one:
//   1. connection-code encode/decode round-trips, and garbage is rejected;
//   2. the copy-paste flow (offer -> answer -> apply) reaches COMPLETED on
//      both agents;
//   3. a 64 KiB transfer through the channel interface (1-byte channel
//      prefix, kChannelGekko) arrives intact, plus a handshake-channel
//      ping-pong.
// Engine-free: links juice + pc_netplay_ice only (plus gekkonet headers for
// the IceLink adapter type).

#include "netplay/pc_netplay_ice.h"

#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <thread>
#include <vector>
#include <chrono>

namespace {

int sFailures = 0;

void check(bool ok, const char* what, int line)
{
	if (!ok) {
		++sFailures;
		std::printf("FAIL line %d: %s\n", line, what);
	}
}
#define CHECK(ok, what) check((ok), (what), __LINE__)

const char* kFakeSdp =
    "a=ice-ufrag:hostUfrag1234\r\n"
    "a=ice-pwd:hostPasswordPassword1234567890\r\n"
    "a=candidate:1 1 UDP 2113937151 192.168.2.61 50001 typ host\r\n"
    "a=candidate:2 1 UDP 16777215 74.125.250.129 19302 typ srflx\r\n"
    "a=end-of-candidates\r\n"
    "a=ice-options:ice2\r\n";

} // namespace

int main()
{
	using namespace pc_netplay_ice;

	// 1. Code round trip + strict rejection.
	{
		std::string offer, answer, err, sdp;
		bool isOffer = false;
		CHECK(ice_encode_code(true, kFakeSdp, &offer, &err), "encode offer");
		CHECK(ice_encode_code(false, kFakeSdp, &answer, &err), "encode answer");
		CHECK(offer.compare(0, 6, "NPIX1-") == 0 && offer.find('\n') == std::string::npos,
		      "offer is one line with version prefix");
		CHECK(ice_decode_code(offer, &isOffer, &sdp, &err) && isOffer && sdp == kFakeSdp,
		      "offer round trip");
		CHECK(ice_decode_code(answer, &isOffer, &sdp, &err) && !isOffer && sdp == kFakeSdp,
		      "answer round trip");
		// Garbage is rejected with a reason.
		const char* bad[] = {
			"",
			"not-a-code",
			"NPIX1-",
			"NPIX1-!!!not-base64!!!",
			"NPIX0-AAAA",
		};
		for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); ++i) {
			bool io = false;
			std::string s, e;
			CHECK(!ice_decode_code(bad[i], &io, &s, &e) && !e.empty(), "garbage rejected");
		}
		// Corrupted payload (flip a base64 char) fails the CRC/length check.
		{
			std::string corrupt = offer;
			CHECK(corrupt.size() > 12, "offer long enough to corrupt");
			corrupt[12] = (corrupt[12] == 'A' ? 'B' : 'A');
			bool io = false;
			std::string s, e;
			CHECK(!ice_decode_code(corrupt, &io, &s, &e), "corrupted code rejected");
		}
		// Truncated code is rejected.
		{
			bool io = false;
			std::string s, e;
			CHECK(!ice_decode_code(offer.substr(0, offer.size() / 2), &io, &s, &e),
			      "truncated code rejected");
		}
		// Role confusion is caught by the socket layer, but kinds decode.
		CHECK(offer != answer, "offer and answer differ");
	}

	// 1b. v2 bundle offer round trip + strict rejection (launch lane).
	{
		SessionBundle bundle;
		bundle.seed            = 0x12345678;
		bundle.configText      = "m3-config-v1;fpsMode=0;chainActions=1;";
		bundle.bootstrapBytes  = "PIKMIN_RANDOMIZER 5\nSESSION abc\nFINGERPRINT abc\nEND\n";
		std::string offer2, err, sdp;
		SessionBundle got;
		CHECK(ice_encode_offer_v2(kFakeSdp, bundle, &offer2, &err), "encode v2 offer");
		CHECK(offer2.compare(0, 6, "NPIX2-") == 0 && offer2.find('\n') == std::string::npos,
		      "v2 offer is one line with version prefix");
		CHECK(ice_decode_offer_v2(offer2, &sdp, &got, &err) && sdp == kFakeSdp,
		      "v2 offer SDP round trip");
		CHECK(got.seed == bundle.seed && got.configText == bundle.configText
		          && got.bootstrapBytes == bundle.bootstrapBytes,
		      "v2 offer bundle round trip");
		std::printf("ice_test: v2 offer bytes=%llu\n", (unsigned long long)offer2.size());
		// Empty bootstrap is allowed (plain non-randomizer boot).
		{
			SessionBundle emptyBoot = bundle;
			emptyBoot.bootstrapBytes.clear();
			std::string enc, e2, s2;
			SessionBundle g2;
			CHECK(ice_encode_offer_v2(kFakeSdp, emptyBoot, &enc, &e2), "encode v2 empty boot");
			CHECK(ice_decode_offer_v2(enc, &s2, &g2, &e2) && g2.bootstrapBytes.empty()
			          && g2.seed == bundle.seed && g2.configText == bundle.configText,
			      "v2 empty bootstrap round trip");
		}
		// Garbage is rejected with a reason.
		const char* bad2[] = {
			"",
			"not-a-code",
			"NPIX2-",
			"NPIX2-!!!not-base64!!!",
			"NPIX1-AAAA", // wrong prefix family
			"NPIX2-AAAA", // valid alphabet, too short
		};
		for (size_t i = 0; i < sizeof(bad2) / sizeof(bad2[0]); ++i) {
			std::string s, e;
			SessionBundle g;
			CHECK(!ice_decode_offer_v2(bad2[i], &s, &g, &e) && !e.empty(),
			      "v2 garbage rejected");
		}
		// Corrupted payload (flip a base64 char) fails the CRC/length check.
		{
			std::string corrupt = offer2;
			CHECK(corrupt.size() > 12, "v2 offer long enough to corrupt");
			corrupt[12] = (corrupt[12] == 'A' ? 'B' : 'A');
			std::string s, e;
			SessionBundle g;
			CHECK(!ice_decode_offer_v2(corrupt, &s, &g, &e), "v2 corrupted code rejected");
		}
		// Truncated code is rejected.
		{
			std::string s, e;
			SessionBundle g;
			CHECK(!ice_decode_offer_v2(offer2.substr(0, offer2.size() / 2), &s, &g, &e),
			      "v2 truncated code rejected");
		}
		// Oversized config block is refused at encode time (bounded before use).
		{
			SessionBundle huge = bundle;
			huge.configText.assign(kMaxBundleConfigBytes + 1, 'x');
			std::string enc, e;
			CHECK(!ice_encode_offer_v2(kFakeSdp, huge, &enc, &e) && !e.empty(),
			      "v2 oversized config refused");
		}
		// m1 boundaries: every length is a u16 field, so the bootstrap cap is
		// 65535. A 65535-byte bootstrap round-trips; 65536 is refused at
		// encode time (it used to encode as length 0 and fail every decode).
		{
			SessionBundle edge = bundle;
			edge.bootstrapBytes.assign(kMaxBundleBootBytes, 'b');
			std::string enc, e, s2;
			SessionBundle g;
			CHECK(kMaxBundleBootBytes == 65535, "bootstrap cap is 65535");
			CHECK(ice_encode_offer_v2(kFakeSdp, edge, &enc, &e), "65535-byte bootstrap encodes");
			CHECK(ice_decode_offer_v2(enc, &s2, &g, &e) && g.bootstrapBytes == edge.bootstrapBytes,
			      "65535-byte bootstrap round-trips");
			CHECK(enc.size() <= kMaxOfferV2Chars, "largest-bootstrap offer fits the text cap");
			std::printf("ice_test: v2 offer with a 65535 B bootstrap = %llu chars (cap %llu)\n",
			            (unsigned long long)enc.size(), (unsigned long long)kMaxOfferV2Chars);
			edge.bootstrapBytes.push_back('b');
			CHECK(!ice_encode_offer_v2(kFakeSdp, edge, &enc, &e) && !e.empty(),
			      "65536-byte bootstrap refused at encode");
		}
		// Text longer than the cap is refused before decoding.
		{
			std::string tooLong = "NPIX2-" + std::string(kMaxOfferV2Chars, 'A');
			std::string s2, e;
			SessionBundle g;
			CHECK(!ice_decode_offer_v2(tooLong, &s2, &g, &e) && e.find("too long") != std::string::npos,
			      "v2 text over the cap refused");
		}
		// cfgLen = 0 is refused (the launcher always sends the config block).
		{
			SessionBundle noCfg = bundle;
			noCfg.configText.clear();
			std::string enc, e, s2;
			SessionBundle g;
			CHECK(ice_encode_offer_v2(kFakeSdp, noCfg, &enc, &e), "encode with an empty config block");
			CHECK(!ice_decode_offer_v2(enc, &s2, &g, &e) && e.find("config length") != std::string::npos,
			      "v2 cfgLen=0 refused at decode");
		}
		// A v1 answer (or offer) fed to the v2 decoder is refused by prefix.
		{
			std::string ans, e, s2;
			SessionBundle g;
			CHECK(ice_encode_code(false, kFakeSdp, &ans, &e), "encode a v1 answer");
			CHECK(!ice_decode_offer_v2(ans, &s2, &g, &e) && e.find("NPIX2-") != std::string::npos,
			      "v1 answer refused by the v2 decoder");
		}
		// m9: code files are written atomically (tmp + rename, no tmp left);
		// @file reads are bounded (a file larger than any code is refused).
		{
			const std::string path = "pc_netplay_ice_test_code.txt";
			std::string e, got;
			CHECK(ice_write_code_file(path, offer2, &e), "atomic code-file write");
			FILE* tmp = std::fopen((path + ".tmp").c_str(), "rb");
			CHECK(tmp == nullptr, "no temporary file left behind");
			if (tmp != nullptr) std::fclose(tmp);
			CHECK(ice_read_code_arg("@" + path, &got, &e) && got == offer2, "@file reads the code back");
			FILE* f = std::fopen(path.c_str(), "wb");
			if (f != nullptr) {
				const std::string junk(kMaxOfferV2Chars + 8192, 'A');
				std::fwrite(junk.data(), 1, junk.size(), f);
				std::fclose(f);
			}
			CHECK(!ice_read_code_arg("@" + path, &got, &e) && e.find("too large") != std::string::npos,
			      "@file larger than any code refused");
			std::remove(path.c_str());
		}
	}

	// 2. Relay filter unit checks on synthetic SDP.
	{
		CHECK(ice_candidate_line_is_relay("a=candidate:3 1 UDP 41819903 10.0.0.5 50002 typ relay"),
		      "relay line detected");
		CHECK(!ice_candidate_line_is_relay(
		          "a=candidate:1 1 UDP 2113937151 192.168.2.61 50001 typ host"),
		      "host line is not relay");
		std::string filtered = ice_filter_relay_candidates(kFakeSdp);
		CHECK(filtered.find(" typ host") == std::string::npos, "host filtered out");
		CHECK(filtered.find(" typ srflx") == std::string::npos, "srflx filtered out");
		CHECK(filtered.find("a=ice-ufrag:") != std::string::npos, "ufrag kept");
		// m5: no extra blank line is emitted for a trailing newline.
		CHECK(filtered.empty() || filtered.compare(filtered.size() - 4, 4, "\r\n\r\n") != 0,
		      "no trailing blank line");
		{
			const std::string noCand = "a=ice-ufrag:x\r\na=ice-pwd:y\r\n";
			CHECK(ice_filter_relay_candidates(noCand) == noCand, "CRLF round trip");
		}
		CHECK(!ice_sdp_has_relay(kFakeSdp), "fake SDP has no relay");
		CHECK(ice_sdp_has_relay("a=candidate:3 1 UDP 1 10.0.0.5 9 typ relay\r\n"),
		      "relay SDP detected");
	}

	// 3. In-process loopback pair with host candidates only.
	IceNetConfig cfg; // no STUN, no TURN: host candidates over loopback
	IceSocket hostSock, joinSock;
	{
		std::string offer, answer, err;
		CHECK(hostSock.host_create_offer(cfg, &offer, &err), "host offer gathers");
		if (!offer.empty()) std::printf("ice_test: offer bytes=%llu\n", (unsigned long long)offer.size());
		bool isOffer = false;
		std::string sdp;
		CHECK(ice_decode_code(offer, &isOffer, &sdp, &err) && isOffer, "offer decodes");
		CHECK(joinSock.join_create_answer(cfg, offer, &answer, &err), "join answer gathers");
		if (!answer.empty())
			std::printf("ice_test: answer bytes=%llu\n", (unsigned long long)answer.size());
		CHECK(hostSock.host_apply_answer(answer, &err), "host applies answer");
		double hostMs = -1, joinMs = -1;
		CHECK(hostSock.wait_connected(30000, &hostMs, &err), "host completed");
		CHECK(joinSock.wait_connected(30000, &joinMs, &err), "join completed");
		std::printf("ice_test: completed host=%.0fms join=%.0fms\n", hostMs, joinMs);
		CHECK(hostMs >= 0 && joinMs >= 0, "completed times reported");
	}

	// 4. 64 KiB through the channel interface + handshake ping-pong.
	{
		// 64 KiB in 1024-byte payloads; first 4 bytes of each payload are
		// the big-endian chunk index so order can be verified.
		const size_t kChunks = 64, kPayload = 1024;
		std::vector<uint8_t> want(64 * 1024);
		for (size_t i = 0; i < want.size(); ++i) want[i] = (uint8_t)((i * 2654435761u) >> 8);
		for (size_t c = 0; c < kChunks; ++c) {
			uint8_t payload[kPayload];
			payload[0] = (uint8_t)((c >> 24) & 0xFF);
			payload[1] = (uint8_t)((c >> 16) & 0xFF);
			payload[2] = (uint8_t)((c >> 8) & 0xFF);
			payload[3] = (uint8_t)(c & 0xFF);
			for (size_t i = 4; i < kPayload; ++i)
				payload[i] = want[c * kPayload + i];
			CHECK(hostSock.send_payload(kChannelGekko, payload, kPayload), "gekko send");
		}
		std::vector<uint8_t> got(64 * 1024, 0);
		std::vector<char> seen(kChunks, 0);
		size_t gotChunks = 0;
		const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(20);
		while (gotChunks < kChunks && std::chrono::steady_clock::now() < deadline) {
			std::vector<IceSocket::Datagram> grams = joinSock.recv();
			if (grams.empty()) {
				std::this_thread::sleep_for(std::chrono::milliseconds(2));
				continue;
			}
			for (size_t i = 0; i < grams.size(); ++i) {
				CHECK(grams[i].channel == kChannelGekko, "gekko channel intact");
				if (grams[i].payload.size() != kPayload) continue;
				size_t c = ((size_t)grams[i].payload[0] << 24)
				    | ((size_t)grams[i].payload[1] << 16)
				    | ((size_t)grams[i].payload[2] << 8) | grams[i].payload[3];
				if (c >= kChunks || seen[c]) continue;
				seen[c] = 1;
				++gotChunks;
				memcpy(got.data() + c * kPayload + 4, grams[i].payload.data() + 4,
				       kPayload - 4);
			}
		}
		CHECK(gotChunks == kChunks, "all 64 chunks arrived");
		bool intact = (gotChunks == kChunks);
		if (intact) {
			for (size_t c = 0; c < kChunks && intact; ++c) {
				for (size_t i = 4; i < kPayload; ++i) {
					if (got[c * kPayload + i] != want[c * kPayload + i]) {
						intact = false;
						break;
					}
				}
			}
		}
		CHECK(intact, "64 KiB intact");
		// Reverse direction over the handshake channel.
		const uint8_t ping[5] = { 'p', 'i', 'n', 'g', '!' };
		CHECK(joinSock.send_payload(kChannelHandshake, ping, sizeof(ping)), "hs send");
		bool pong = false;
		const auto d2 = std::chrono::steady_clock::now() + std::chrono::seconds(10);
		while (!pong && std::chrono::steady_clock::now() < d2) {
			std::vector<IceSocket::Datagram> grams = hostSock.recv();
			if (grams.empty()) {
				std::this_thread::sleep_for(std::chrono::milliseconds(2));
				continue;
			}
			for (size_t i = 0; i < grams.size(); ++i) {
				if (grams[i].channel == kChannelHandshake && grams[i].payload.size() == 5
				    && memcmp(grams[i].payload.data(), ping, 5) == 0)
					pong = true;
			}
		}
		CHECK(pong, "handshake ping-pong");
	}

	// 5. m9: IceLink (GekkoNet adapter) round trip over the same pair.
	{
		IceLink joinLink(&joinSock);
		const uint8_t hello[6] = { 'g', 'e', 'k', 'k', 'o', '!' };
		CHECK(hostSock.send_payload(kChannelGekko, hello, sizeof(hello)), "icelink send");
		bool gotIt = false;
		const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
		while (!gotIt && std::chrono::steady_clock::now() < deadline) {
			int n = 0;
			GekkoNetResult** res = joinLink.receive_inner(&n);
			for (int i = 0; i < n; ++i) {
				if (res[i] != nullptr && res[i]->data_len == sizeof(hello)
				    && res[i]->data != nullptr
				    && memcmp(res[i]->data, hello, sizeof(hello)) == 0
				    && res[i]->addr.size == kAddrBytes)
					gotIt = true;
				// receive_inner owns the results; release via the adapter.
				if (res[i] != nullptr) {
					free(res[i]->addr.data);
					free(res[i]->data);
					free(res[i]);
				}
			}
			if (!gotIt) std::this_thread::sleep_for(std::chrono::milliseconds(2));
		}
		CHECK(gotIt, "icelink adapter round trip");
	}

	// 6. M4 lane B2 (issue #885): the bulk channel 0x03 over ICE. Three bulk
	// datagrams (one of them the largest valid payload, kMaxDatagram - 1
	// bytes) plus a gekko and a handshake datagram go host -> joiner; the
	// joiner's IceLink::drain_bulk returns exactly the bulk ones, intact and in
	// order, while the gekko one still reaches the adapter and the handshake
	// one drain_handshake. An unknown channel (0x09) is dropped.
	{
		IceLink joinLink(&joinSock);
		std::vector<std::vector<uint8_t>> bulk;
		bulk.push_back(std::vector<uint8_t>{ 0x10, 1, 0, 0, 0, 1, 0 });
		bulk.push_back(std::vector<uint8_t>(kMaxDatagram - 1, 0x5A));
		bulk.push_back(std::vector<uint8_t>{ 0x7F, 1, 0, 0, 0 });
		const uint8_t gk[4]    = { 'g', 'k', '0', '3' };
		const uint8_t hs[4]    = { 'h', 's', '0', '3' };
		const uint8_t junk[3]  = { 'x', 'y', 'z' };
		for (const auto& b : bulk) CHECK(hostSock.send_payload(kChannelBulk, b.data(), b.size()), "bulk send");
		CHECK(hostSock.send_payload(kChannelGekko, gk, sizeof(gk)), "gekko send (bulk section)");
		CHECK(hostSock.send_payload(kChannelHandshake, hs, sizeof(hs)), "hs send (bulk section)");
		CHECK(hostSock.send_payload(0x09, junk, sizeof(junk)), "unknown-channel send");
		CHECK(!hostSock.send_payload(kChannelBulk, bulk[1].data(), kMaxDatagram), "oversized bulk refused by the sender");
		std::vector<std::vector<uint8_t>> gotBulk;
		bool gotGk = false, gotHs = false, gotJunk = false;
		const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
		while ((gotBulk.size() < bulk.size() || !gotGk || !gotHs) && std::chrono::steady_clock::now() < deadline) {
			for (IceSocket::Datagram& g : joinLink.drain_bulk()) {
				if (g.channel != kChannelBulk) gotJunk = true;
				gotBulk.push_back(g.payload);
			}
			for (IceSocket::Datagram& g : joinLink.drain_handshake()) {
				if (g.channel == kChannelHandshake && g.payload.size() == sizeof(hs)
				    && memcmp(g.payload.data(), hs, sizeof(hs)) == 0)
					gotHs = true;
				else gotJunk = true;
			}
			int n = 0;
			GekkoNetResult** res = joinLink.receive_inner(&n);
			for (int i = 0; i < n; ++i) {
				if (res[i] == nullptr) continue;
				if (res[i]->data_len == sizeof(gk) && memcmp(res[i]->data, gk, sizeof(gk)) == 0) gotGk = true;
				else gotJunk = true;
				free(res[i]->addr.data);
				free(res[i]->data);
				free(res[i]);
			}
			if (gotBulk.size() < bulk.size() || !gotGk || !gotHs)
				std::this_thread::sleep_for(std::chrono::milliseconds(2));
		}
		CHECK(gotBulk.size() == bulk.size(), "bulk datagrams drained");
		bool intact = gotBulk.size() == bulk.size();
		for (size_t i = 0; intact && i < bulk.size(); ++i) intact = gotBulk[i] == bulk[i];
		CHECK(intact, "bulk payloads intact and in order (largest valid payload included)");
		CHECK(gotGk, "gekko datagram still reaches the adapter");
		CHECK(gotHs, "handshake datagram still reaches drain_handshake");
		CHECK(!gotJunk, "no datagram on the wrong queue; unknown channel dropped");
		std::printf("bulk over ice: %llu datagrams (max %llu B) drained on channel 0x03\n",
		            (unsigned long long)gotBulk.size(), (unsigned long long)(kMaxDatagram - 1));
	}

	if (sFailures == 0) std::printf("pc_netplay_ice_test: PASS\n");
	else std::printf("pc_netplay_ice_test: %d FAILURES\n", sFailures);
	return sFailures == 0 ? 0 : 1;
}
