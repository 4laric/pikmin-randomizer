#pragma once
// Netplay M5a ICE transport + copy-paste connection codes (issue #887).
//
// Engine-free TU (libjuice C API + the C++ standard library only), so the
// host-run ICE test can link it without the game. Compiles as C++17 and
// includes only `gekkonet.h` from GekkoNet (C-compatible) for the adapter.
//
// Wire format: identical to pc_netplay_udp. Every datagram sent through
// juice_send() carries a 1-byte channel prefix:
//   0x01  handshake (session hello/ack; consumed by pc_netplay_session)
//   0x02  gekko     (GekkoNet packets; the only channel the adapter exposes)
//   0x03  bulk      (M4 lane B2, issue #885: the reliable bulk channel, the
//                   same pc_netplay_bulk::BulkChannel wire as over UDP;
//                   IceLink::drain_bulk hands it to the session)
// Unknown channels are dropped. Every declared length is bounded before use
// (kMaxDatagram); oversized datagrams are dropped, never truncated.
//
// libjuice invokes its callbacks on its own thread, so incoming datagrams go
// into a mutex-locked bounded queue that the session drains from the main
// thread.
//
// Connection codes: one line of base64url over a compact binary form, with a
// text version prefix and a CRC32:
//   "NPIX1-" + base64url(version:1 | kind:1('O' offer/'A' answer) |
//                         sdp_len:u16be | sdp | crc32:u32be)
// The SDP is libjuice's local description, which bundles all gathered
// candidates, so no trickle exchange is needed: one code each way.

#include <stddef.h>
#include <stdint.h>

#include <functional>
#include <string>
#include <vector>

// The only GekkoNet header our code includes (C-compatible, per the brief).
#include "gekkonet.h"
// libjuice C API (JUICE_STATIC: static link, no dllimport).
#include "juice/juice.h"

namespace pc_netplay_ice {
constexpr uint8_t kChannelHandshake = 0x01;
constexpr uint8_t kChannelGekko     = 0x02;
constexpr uint8_t kChannelBulk      = 0x03; // M4 lane B2
constexpr size_t kMaxDatagram      = 4096;
constexpr size_t kAddrBytes        = 6; // fixed placeholder blob over ICE
constexpr int kMaxRecvPerPoll      = 64;

// ---- network configuration (env-driven) ----

struct StunServer {
	std::string host;
	uint16_t port = 0;
};

struct TurnServer {
	std::string host;
	uint16_t port = 0;
	std::string user;
	std::string pass;
};

struct IceNetConfig {
	// libjuice v1.7.4 exposes a single STUN server per agent, so the agent
	// uses stun.front(); the rest is kept for logging/future fallback.
	std::vector<StunServer> stun;
	std::vector<TurnServer> turn;
	uint16_t portBegin = 0; // local port range (0/0 = ephemeral)
	uint16_t portEnd   = 0;
	bool turnOnly      = false; // no STUN + relay candidates only
	// Optional libjuice bind address (juice_config_t.bind_address). Empty =
	// default (any). Set via PIKMIN_NETPLAY_ICE_BIND (for example
	// "127.0.0.1"). The lab TURN-only pair binds the TURN server to a
	// distinct loopback address (127.0.0.2) so per-IP TURN permissions
	// block the direct path and relay<->relay is forced.
	std::string bindAddress;
};

// Defaults per the brief: STUN stun.l.google.com:19302 then
// stun.cloudflare.com:3478; no TURN; ephemeral local ports. Overridable:
//   PIKMIN_NETPLAY_STUN     "host:port[,host:port...]" ("none" = no STUN)
//   PIKMIN_NETPLAY_TURN     "host:port:user:pass[,...]" (empty = none)
//   PIKMIN_NETPLAY_ICE_PORT_BEGIN / _END
//   PIKMIN_NETPLAY_ICE_TURN_ONLY=1
//   PIKMIN_NETPLAY_ICE_BIND "ip" (empty = any; libjuice bind_address)
//   PIKMIN_NETPLAY_ICE_TIMEOUT_MS (connect wait; default 600000, 10 min, so a
//     normal human copy-paste round trip fits; pair tool passes its own value)
//   PIKMIN_NETPLAY_ICE_GATHER_TIMEOUT_MS (default 15000)
IceNetConfig ice_net_config_from_env();
// True when an ICE selected-local description is a relay candidate. Used to
// enforce TURN-only mode after COMPLETED (both peers must select relay).
bool ice_selected_local_is_relay(const std::string& selectedLocal);

// ---- connection codes ----

// True when an "a=candidate:..." SDP line is a relay candidate.
bool ice_candidate_line_is_relay(const std::string& line);
// Drops every non-relay "a=candidate:" line from an SDP (TURN-only mode).
std::string ice_filter_relay_candidates(const std::string& sdp);
bool ice_sdp_has_relay(const std::string& sdp);

// Encodes kind+sdp into the "NPIX1-..." code. Fails on empty/oversized SDP.
bool ice_encode_code(bool isOffer, const std::string& sdp, std::string* out,
                     std::string* err);
// Strict decode: prefix, base64, bounds, version, kind, length, CRC. On
// failure returns false with a one-line reason in *err (never throws).
bool ice_decode_code(const std::string& text, bool* isOffer, std::string* sdp,
                     std::string* err);

// ---- session bundle (launch lane, issue #887) ----
//
// The v2 offer code ("NPIX2-...") carries the whole session setup, so the
// joiner needs no file from the host:
//   "NPIX2-" + base64url(version:1=0x02 | kind:1('O') |
//                         sdp_len:u16be | cfg_len:u16be | boot_len:u16be |
//                         seed:u32be | sdp | cfg | boot | crc32:u32be)
//   sdp  = libjuice local description (<= 8192 bytes, as v1)
//   cfg  = host sim-relevant settings block, the m3-config-v1 text the M3
//          handshake hashes (<= 8192 bytes; the joiner adopts it for the
//          session only, never writing its settings file)
//   boot = host bootstrap file bytes, raw (<= 65535 bytes, the u16 field's
//          range; a stock bootstrap is ~10 lines, so compression would save
//          nothing and the bytes are stored verbatim; the joiner re-stamps
//          the SESSION line exactly like the root M4c helper
//          randomizer/netplay_mirror.py restamp_bootstrap_for_peer)
//   seed = the netplay seed (u32be)
// Every length is bounded before allocation; the CRC and strict checks of
// v1 are kept. Answers stay v1 ("NPIX1-..."); only offers have a v2 form.
struct SessionBundle {
	uint32_t seed = 0;
	std::string configText;
	std::string bootstrapBytes;
};

// Upper bounds enforced before any allocation in the v2 decode path. Every
// length travels in a u16 field, so every cap must fit one (m1: a 65536
// cap used to encode as length 0 and fail every decode).
constexpr size_t kMaxBundleSdpBytes    = 8192;
constexpr size_t kMaxBundleConfigBytes = 8192;
constexpr size_t kMaxBundleBootBytes   = 65535;
static_assert(kMaxBundleSdpBytes <= 0xFFFF, "v2 SDP length is a u16 field");
static_assert(kMaxBundleConfigBytes <= 0xFFFF, "v2 config length is a u16 field");
static_assert(kMaxBundleBootBytes <= 0xFFFF, "v2 bootstrap length is a u16 field");
// Largest v2 offer text: "NPIX2-" + base64url of the largest raw form
// (12-byte header + the three maxima + CRC). Codes longer than this are
// refused before decoding.
constexpr size_t kMaxOfferV2Chars =
    6 + ((12 + kMaxBundleSdpBytes + kMaxBundleConfigBytes + kMaxBundleBootBytes + 4 + 2) / 3) * 4;

// Encodes an offer SDP plus the session bundle into the "NPIX2-..." code.
bool ice_encode_offer_v2(const std::string& sdp, const SessionBundle& bundle,
                         std::string* out, std::string* err);
// Strict decode of an "NPIX2-..." offer code. On failure returns false with
// a one-line reason in *err (never throws).
bool ice_decode_offer_v2(const std::string& text, std::string* sdp, SessionBundle* bundle,
                         std::string* err);

// Reads a code from a CLI value: "@file" reads the file (trimmed, bounded:
// a file larger than any valid code is refused unread), anything else is
// the literal code (trimmed).
bool ice_read_code_arg(const std::string& arg, std::string* code, std::string* err);
// Writes a code to a file atomically (a temporary file next to it, then a
// rename over the target), so a reader polling the path never sees a
// partial code. No-op when path is empty.
bool ice_write_code_file(const std::string& path, const std::string& code,
                         std::string* err);

// ---- agent socket (same send/receive surface as UdpSocket) ----

class IceSocket {
public:
	IceSocket();
	~IceSocket();

	IceSocket(const IceSocket&)            = delete;
	IceSocket& operator=(const IceSocket&) = delete;

	// --- signalling (each drives gathering + waits internally) ---
	// Host: creates the agent, gathers, returns the offer code. Pumps
	// pump() while gathering so the window stays alive (M3).
	bool host_create_offer(const IceNetConfig& cfg, std::string* offerOut,
	                       std::string* err,
	                       std::function<void()> pump = std::function<void()>());
	// Host v2: same, but the offer is an "NPIX2-..." bundle code carrying
	// the session setup (seed, host config block, bootstrap bytes).
	bool host_create_offer_v2(const IceNetConfig& cfg, const SessionBundle& bundle,
	                          std::string* offerOut, std::string* err,
	                          std::function<void()> pump = std::function<void()>());
	// Joiner: validates the offer, creates the agent, gathers, returns the
	// answer code. Pumps pump() while gathering (M3). Accepts both v1
	// ("NPIX1-...") and v2 bundle ("NPIX2-...") offers; when the offer is
	// v2 and bundleOut is non-null, the session bundle (seed, host config
	// block, bootstrap bytes) is returned there for the session to adopt.
	bool join_create_answer(const IceNetConfig& cfg, const std::string& offer,
	                        std::string* answerOut, std::string* err,
	                        std::function<void()> pump = std::function<void()>(),
	                        SessionBundle* bundleOut = nullptr);
	// Host: validates the answer and applies it to the agent.
	bool host_apply_answer(const std::string& answer, std::string* err);
	// Blocks (polling) until JUICE_STATE_COMPLETED, FAILED, or timeoutMs.
	// On success sets *completedMsOut to ms from apply_remote() (the ICE
	// connect time, not counting the human copy-paste; falls back to agent
	// creation when no remote was applied). Pumps pump() ~every 50 ms so
	// the SDL window stays alive. In TURN-only mode fails with a clear
	// "TURN-only violated" error unless the selected local candidate is a
	// relay candidate.
	bool wait_connected(double timeoutMs, double* completedMsOut, std::string* err,
	                    std::function<void()> pump = std::function<void()>());

	// --- transport surface ---
	// Sends channel + payload through the ICE agent. Returns false when not
	// connected, the frame exceeds kMaxDatagram, or the send fails.
	bool send_payload(uint8_t channel, const uint8_t* data, size_t len);
	// Address is ignored: the agent is connected 1:1. Kept so the session
	// can call the same shape it uses for UDP.
	bool send_to(uint8_t channel, const uint8_t* data, size_t len, uint32_t ipHostOrder,
	             uint16_t port);

	struct Datagram {
		uint8_t channel = 0;
		std::vector<uint8_t> payload;
		uint32_t fromIpHostOrder = 0; // always 127.0.0.1 over ICE
		uint16_t fromPort        = 0; // always 1 over ICE
	};
	// Drains the receive queue (up to kMaxRecvPerPoll). Never blocks.
	std::vector<Datagram> recv();

	void close();

	// Diagnostics for the session log / pair tool.
	std::string selected_local() const;
	std::string selected_remote() const;
	std::string state_str() const;
	double completed_ms() const; // -1 until COMPLETED

private:
	// Callbacks (run on libjuice's thread; lock mMutex, never block).
	static void on_state(juice_agent_t* agent, juice_state_t state, void* userPtr);
	static void on_candidate(juice_agent_t* agent, const char* sdp, void* userPtr);
	static void on_gathering_done(juice_agent_t* agent, void* userPtr);
	static void on_recv(juice_agent_t* agent, const char* data, size_t size, void* userPtr);

	bool create_agent(const IceNetConfig& cfg, std::string* err);
	bool wait_gathering_done(double timeoutMs, std::string* err,
	                         std::function<void()> pump = std::function<void()>());
	bool local_description(std::string* out, std::string* err);
	bool apply_remote(const std::string& sdp, bool turnOnly, std::string* err);

	mutable void* mMutex = nullptr; // std::mutex* (opaque: header stays light)
	juice_agent_t* mAgent = nullptr;
	bool mCreated = false;
	bool mGatheringDone = false;
	int mState = 0;
	std::vector<std::string> mLocalCandidates;
	std::vector<Datagram> mQueue;
	std::string mSelectedLocal;
	std::string mSelectedRemote;
	double mCreateMs = 0;
	double mConnectStartMs = 0; // set in apply_remote (both descriptions known)
	double mCompletedMs = -1;
	bool mTurnOnly = false;
	bool mClosed = false;
};

// GekkoNet link over an IceSocket, mirroring GekkoLink: the session drains
// handshake bytes itself, and GekkoNet sees only the gekko channel through
// the adapter. Address blobs are the fixed kAddrBytes placeholder
// (127.0.0.1:1); the ICE agent is connected 1:1, so delivery ignores the
// content, but GekkoNet matches actors by blob equality, so the session must
// register the remote actor with these exact bytes (it does: 0x7F000001:1).
// Same malloc/free contract as GekkoLink.
class IceLink {
public:
	explicit IceLink(IceSocket* sock);
	~IceLink();

	IceLink(const IceLink&)            = delete;
	IceLink& operator=(const IceLink&) = delete;

	GekkoNetAdapter* adapter();

	// Drains datagrams arrived on the handshake channel (0x01). The
	// session handshake pump calls this; GekkoNet never sees them.
	std::vector<IceSocket::Datagram> drain_handshake();

	// Drains datagrams arrived on the bulk channel (0x03, M4 lane B2),
	// like GekkoLink::drain_bulk: pumps the socket once, then hands the
	// bulk queue to the session's BulkChannel. GekkoNet never sees them.
	std::vector<IceSocket::Datagram> drain_bulk();

	// Called by the C send_data trampoline.
	void send_to_peer(uint32_t ipHostOrder, uint16_t port, const uint8_t* data, size_t len);
	// Called by the C receive_data trampoline.
	struct GekkoNetResult** receive_inner(int* length);

private:
	// Routes one received datagram to its channel queue (unknown channels
	// are dropped), then caps every queue.
	void route(std::vector<IceSocket::Datagram>& grams);

	IceSocket* mSock;
	GekkoNetAdapter mAdapter;
	std::vector<struct GekkoNetResult*> mResults;
	std::vector<IceSocket::Datagram> mGekkoPending;
	std::vector<IceSocket::Datagram> mHandshakePending;
	std::vector<IceSocket::Datagram> mBulkPending;
};

// ---- one-shot signalling orchestration (called by the session) ----

// Blocking host flow: offer print (+ optional CODE_OUT file), then answer
// from PIKMIN_NETPLAY_ICE_ANSWER_IN (polled) or stdin, then wait_connected.
// pump() is invoked ~every 50 ms while waiting (the session pumps the
// window). Prints the offer/answer codes and the ice state/pair log lines.
bool ice_host_session(const IceNetConfig& cfg, std::function<void()> pump, IceSocket* outSock,
                      std::string* err);

// Shared one-shot pieces, also used by the launch-lane one-command flows
// (declared here; defined in pc_netplay_ice.cpp):
// PIKMIN_NETPLAY_ICE_TIMEOUT_MS (default 600000 = 10 min).
double ice_connect_timeout_ms();
// Polls a file until it holds a valid answer code (logs each new decode
// error instead of failing silently).
bool ice_poll_answer_file(const std::string& path, double timeoutMs, std::function<void()> pump,
                          std::string* answerOut, std::string* err);
// Reads answer-code lines from stdin on a helper thread while pump() keeps
// the window alive. A line that is not a valid answer (garbage, a
// truncated paste, an offer code) prints its decode error and re-prompts
// (m4: one bad paste must not end the host); only EOF with no valid answer
// fails.
bool ice_read_answer_stdin(std::function<void()> pump, std::string* answerOut,
                           std::string* err);
// Blocking joiner flow: offerArg is the offer code or @file; prints + writes
// the answer code, then wait_connected.
bool ice_join_session(const IceNetConfig& cfg, const std::string& offerArg,
                      std::function<void()> pump, IceSocket* outSock, std::string* err);

} // namespace pc_netplay_ice
