#pragma once
// Netplay M3 UDP transport + lossy test wrapper (issue #880).
//
// Engine-free TU (Winsock + gekkonet.h + the C++ standard library only), so
// the host-run transport test can link it without the game. All netplay code
// here compiles as C++17 and includes only `gekkonet.h` from GekkoNet, which
// is C-compatible.
//
// Wire format: every datagram carries a 1-byte channel prefix:
//   0x01  handshake (session hello/ack; consumed by pc_netplay_session)
//   0x02  gekko     (GekkoNet packets; the only channel the GekkoNetAdapter
//                   sees)
// Unknown channels are dropped. Every declared length is bounded before use
// (kMaxDatagram); oversized datagrams are dropped, never truncated into a
// smaller buffer.
//
// Address format inside GekkoNetAddress: 6 bytes, IPv4 (network order) +
// port (network order). The session passes these to gekko_add_actor; this
// adapter is the only code that interprets them.

#include <stddef.h>
#include <stdint.h>

#include <string>
#include <vector>

// The only GekkoNet header our code includes (C-compatible, per the brief).
#include "gekkonet.h"

namespace pc_netplay_transport {
constexpr uint8_t kChannelHandshake = 0x01;
constexpr uint8_t kChannelGekko     = 0x02;
// M4 lane A bulk channel (issue #885): fragmented, acknowledged and
// length-bounded. Carries full randomizer snapshots, SAVE_RESULT and the
// host checkpoint (see pc_netplay_bulk below). Unknown channels are dropped.
constexpr uint8_t kChannelBulk      = 0x03;
constexpr size_t kMaxDatagram      = 4096;
constexpr size_t kAddrBytes        = 6; // IPv4 + port, network order
constexpr int kMaxRecvPerPoll      = 64;

// Parses "ip:port" (IPv4 dotted quad + decimal port). Returns false on any
// malformed input; outIp/outPort are untouched then.
bool parse_endpoint(const char* text, uint32_t* outIpHostOrder, uint16_t* outPort);

// Non-blocking Winsock UDP socket. Bind to a local port (0 = ephemeral);
// setPeer directs gekko-channel sends. All channel framing is explicit:
// send_payload prepends the channel byte; recv() returns only the payload
// bytes (channel stripped) tagged with the channel and sender.
class UdpSocket {
public:
	UdpSocket();
	~UdpSocket();

	UdpSocket(const UdpSocket&)            = delete;
	UdpSocket& operator=(const UdpSocket&) = delete;

	// Binds 0.0.0.0:port (port 0 = ephemeral). Returns false on failure.
	bool bind(uint16_t port);
	// Local port actually bound (0 when unbound).
	uint16_t local_port() const { return mLocalPort; }
 	// Sets the default remote for send_payload().
	bool set_peer(uint32_t ipHostOrder, uint16_t port);
	// Sends channel + payload to the peer. Returns false when no peer is
	// set, the frame exceeds kMaxDatagram, or the send fails.
	bool send_payload(uint8_t channel, const uint8_t* data, size_t len);
	// Sends channel + payload to an explicit endpoint.
	bool send_to(uint8_t channel, const uint8_t* data, size_t len, uint32_t ipHostOrder,
	             uint16_t port);

	struct Datagram {
		uint8_t channel = 0;
		std::vector<uint8_t> payload;
		uint32_t fromIpHostOrder = 0;
		uint16_t fromPort        = 0;
	};
	// Pumps the socket (up to kMaxRecvPerPoll datagrams). Never blocks.
	std::vector<Datagram> recv();

	void close();

private:
	intptr_t mSock = -1;
	uint16_t mLocalPort = 0;
	uint32_t mPeerIp = 0;
	uint16_t mPeerPort = 0;
	bool mHasPeer = false;
	// Fix round 2 (M1 follow-up): handshake-loss test hook. Drops the first
	// N handshake-channel (0x01) sends, reporting success to the caller so
	// the peer must recover via its Hello/Ack resends. N comes from
	// PIKMIN_NETPLAY_TEST_DROP_HS_FIRST_N (default 0 = no drop). Gekko
	// traffic (0x02) is never affected.
	unsigned mHsDropFirstN = 0;
	unsigned mHsSends = 0;
	bool mHsDropInit = false;
	// Fix round 3: handshake-channel test impairment. PIKMIN_NETPLAY_TEST_
	// LATENCY/JITTER/LOSS_MS/PCT apply to handshake datagrams too (receive-
	// side delay/loss, mirroring the LossyLink one-way model for gekko),
	// so DELAY=auto measures the impaired RTT. Gekko traffic is unaffected
	// here (it goes through LossyLink); unknown channels are dropped.
	bool mHsImpInit = false;
	double mHsLatMs = 0.0;
	double mHsJitMs = 0.0;
	double mHsLossPct = 0.0;
	uint64_t mHsRng = 0;
	struct HsDelayed {
		double deliverAtMs = 0.0;
		Datagram gram;
	};
	std::vector<HsDelayed> mHsDelayed;
	double hs_now_ms() const;
	double hs_draw_uniform(double lo, double hi);
	bool hs_draw_drop();
 };

// GekkoNet link: a UdpSocket filtered to the gekko channel, exposed as a
// GekkoNetAdapter. Address blobs are kAddrBytes (IPv4 + port, network
// order). Memory contract (see backend.cpp HandleData): receive_data()
// returns an array the adapter owns (GekkoNet never frees the array
// itself); every result struct, addr blob and payload is malloc'd and
// released through free_data().
class GekkoLink {
public:
	explicit GekkoLink(UdpSocket* sock);
	~GekkoLink();

	GekkoLink(const GekkoLink&)            = delete;
	GekkoLink& operator=(const GekkoLink&) = delete;

	GekkoNetAdapter* adapter();

	// Test hook: inject a received gekko payload without a socket.
	void inject_for_test(const uint8_t* data, size_t len);

	// Drains datagrams arrived on the handshake channel (0x01). The
	// session handshake pump calls this; GekkoNet never sees them.
	std::vector<UdpSocket::Datagram> drain_handshake();

	// Drains datagrams arrived on the bulk channel (0x03, M4 lane A). The
	// session bulk pump feeds these to its BulkChannel; GekkoNet never
	// sees them.
	std::vector<UdpSocket::Datagram> drain_bulk();

	// Called by the C send_data trampoline.
	void send_to_peer(uint32_t ipHostOrder, uint16_t port, const uint8_t* data, size_t len);
	void send_inner(uint32_t ipHostOrder, uint16_t port, const uint8_t* data, size_t len);
	// Called by the C receive_data trampoline.
	struct GekkoNetResult** receive_inner(int* length);

 private:
	UdpSocket* mSock;
	GekkoNetAdapter mAdapter;
	std::vector<struct GekkoNetResult*> mResults;
	std::vector<std::vector<uint8_t>> mInjected;
	std::vector<UdpSocket::Datagram> mGekkoPending;
	std::vector<UdpSocket::Datagram> mHandshakePending;
	std::vector<UdpSocket::Datagram> mBulkPending;
};

// Lossy wrapper adapter over any inner GekkoNetAdapter: one-way latency,
// jitter, loss % and reordering. Loss is applied once, on receive, so the
// configured lossPct is the effective one-way rate (m1). Parameters are
// explicit (the session reads PIKMIN_NETPLAY_TEST_LATENCY_MS / _JITTER_MS /
// _LOSS_PCT / _SEED); the randomness is a local std::mt19937 and never
// touches the sim RNG.
struct LossyParams {
	double latencyMs = 0.0; // base one-way delay
	double jitterMs  = 0.0; // extra uniform [0, jitterMs]
	double lossPct   = 0.0; // 0..100, dropped before delay
	double reorderExtraMs = 0.0; // share of packets held this much longer
	double reorderPct     = 0.0; // ... (0..100)
	uint32_t seed = 0;
};

class LossyLink {
public:
	LossyLink(GekkoNetAdapter* inner, const LossyParams& params);
	~LossyLink();

	LossyLink(const LossyLink&)            = delete;
	LossyLink& operator=(const LossyLink&) = delete;

	GekkoNetAdapter* adapter();

	// Called by the C trampolines. Instances are distinguished by a small
	// static slot (M3 runs at most two sessions per process: the transport
	// test; production runs one).
	void send_inner(struct GekkoNetAddress* addr, const char* data, int length);
	struct GekkoNetResult** receive_inner(int* length);
	int slot() const { return mSlot; }

private:
	GekkoNetAdapter* mInner;
	GekkoNetAdapter mAdapter;
	LossyParams mParams;
	int mSlot = 0;
	std::vector<struct GekkoNetResult*> mResults;
	struct Delayed {
		double deliverAtMs = 0.0;
		struct GekkoNetResult* res = nullptr;
	};
	std::vector<Delayed> mPending;
	// Local RNG state (opaque; defined in the .cpp so this header stays
	// engine-free without <random> in the interface).
	struct Rng;
	Rng* mRng;

	static double now_ms();
	double draw_delay_ms();
	bool draw_drop();
};
} // namespace pc_netplay_transport

// Netplay M4 lane A reliable bulk channel over datagrams with channel byte
// 0x03 (issue #885). Fragmented (<=1024 payload bytes per fragment),
// acknowledged per fragment, and with every declared length bounded before
// allocation (max message 256 KiB).
//
// Wire format (all multi-byte fields little-endian):
//   DATA: [0]=type (0x10..0x1F), [1..2]=msgId, [3..4]=fragIdx,
//         [5..6]=fragCount, [7..10]=totalLen, [11..]=payload (<=1024 B;
//         exactly 1024 except the last fragment, which carries the remainder)
//   ACK:  [0]=0x7F, [1..2]=msgId, [3..4]=fragIdx (5 bytes)
// Data types are the range 0x10..0x1F (M4 plan section 2b plus lane B):
//   kBulkRandFull=0x10 (B1 RESUME: u32 resumeFrame + 64-byte PcRandState),
//   kBulkSaveResult=0x11, kBulkCheckpoint=0x12 (B2),
//   kBulkMirrorLedger=0x14 (B1 client mirror RECEIVED/deathsBase ledger).
//
// Engine-free like the rest of this TU. The session owns one endpoint per
// peer and pumps it each turn; the unit test drives two endpoints over a
// lossy in-memory queue. Ordering: messages complete independently, in the
// order their last fragment arrives; delivery order across messages is NOT
// guaranteed (lane B sequences SaveResult/Checkpoint itself if it needs
// order).
//
// Retransmit (M4 lane B1, lane A review m2 remainder): per-fragment
// exponential backoff 100, 200, 400, 800 ms, then capped at 1000 ms; the
// schedule belongs to the fragment and ends when it is acked. At most
// kBulkMaxInFlight (32) unacked data fragments are in flight across the
// whole channel (a fragment is in flight from its first send until its
// ack); a fragment never sent waits for window room. Acks are exempt from
// the window and are sent once per received data fragment. So a 100%
// blackout of T seconds costs at most 32 x (retransmits per fragment in T)
// datagrams, e.g. <= 32 x 5 in 3 s, instead of every fragment every 100 ms.
// The queue depths (4 outbound messages, 8 inbound) bound the rest.
namespace pc_netplay_bulk {
constexpr uint8_t kBulkRandFull = 0x10;
constexpr uint8_t kBulkSaveResult = 0x11;
constexpr uint8_t kBulkCheckpoint = 0x12;
constexpr uint8_t kBulkMirrorLedger = 0x14;
constexpr uint8_t kBulkDataFirst = 0x10; // data types are 0x10..0x1F
constexpr uint8_t kBulkDataLast = 0x1F;
constexpr uint8_t kBulkAck = 0x7F;
constexpr size_t kBulkMaxPayload = 1024;
constexpr size_t kBulkMaxMessage = 262144; // 256 KiB, hard bound before alloc
constexpr size_t kBulkMaxFrags = kBulkMaxMessage / kBulkMaxPayload; // 256
constexpr double kBulkResendMs = 100.0;     // first retransmit interval
constexpr double kBulkResendMaxMs = 1000.0; // backoff cap
constexpr size_t kBulkMaxInFlight = 32;     // unacked data fragments, channel-wide
constexpr double kBulkPartialTimeoutMs = 30000.0; // abandoned reassembly TTL

class BulkChannel {
public:
	BulkChannel();

	// Resets all session state (send queue, partial reassemblies, ack
	// queue, completed queue, done ids, msgId counter). The session calls
	// this on session start so a previous session's msgIds and partials
	// cannot collide with the new one's (u16 msgIds restart at 1).
	void reset();

	// Queues one message for reliable delivery. Returns false when the
	// type is not a data type, len is 0 or exceeds kBulkMaxMessage, or the
	// (bounded, 4-deep) send queue is full.
	bool send(uint8_t type, const uint8_t* data, size_t len);

	// Feeds one received 0x03 payload (channel byte already stripped).
	// Malformed or out-of-bound datagrams are dropped, never acted on.
	// nowMs stamps new partial reassemblies for the sweep() TTL below.
	void on_receive(const uint8_t* data, size_t len, double nowMs);

	// Drops partial inbound reassemblies older than kBulkPartialTimeoutMs,
	// so abandoned transfers cannot wedge the bounded (8-deep) receiver.
	void sweep(double nowMs);

	// Outgoing 0x03 payloads due at nowMs (pending acks, then due data
	// fragments). The caller sends each on the bulk channel. Acks are
	// emitted once; an unacked data fragment is retransmitted on its
	// backoff schedule (100/200/400/800/1000 ms), and new fragments are
	// first sent only while fewer than kBulkMaxInFlight are in flight.
	std::vector<std::vector<uint8_t>> poll_outgoing(double nowMs);
	// True when send() has room for one more message (4-deep queue).
	bool can_send() const { return mOut.size() < 4; }

	struct Message {
		uint8_t type = 0;
		std::vector<uint8_t> data;
	};
	// Completed inbound messages since the last call.
	std::vector<Message> poll_complete();

	// Test hooks.
	size_t send_acked_frags() const;
	size_t send_total_frags() const;
	size_t send_in_flight() const;
	// Data datagrams re-sent (not first sends) since construction/reset.
	uint64_t resend_count() const { return mResends; }

private:
	struct OutFrag {
		std::vector<uint8_t> bytes; // full DATA datagram payload
		bool acked = false;
		bool sent = false;       // first send done (in flight until acked)
		double lastSendMs = -1e18;
		double nextSendMs = 0.0; // due time of the next retransmit
		unsigned sends = 0;      // transmissions so far (backoff exponent)
	};
	struct OutMsg {
		uint16_t msgId = 0;
		std::vector<OutFrag> frags;
	};
	struct InMsg {
		uint8_t type = 0;
		uint16_t msgId = 0;
		uint16_t count = 0;
		uint32_t totalLen = 0;
		std::vector<uint8_t> bytes;
		std::vector<bool> have;
		uint16_t got = 0;
		bool done = false;
		double firstSeenMs = 0.0;
	};
	uint16_t mNextMsgId = 1;
	std::vector<OutMsg> mOut;
	std::vector<InMsg> mIn; // bounded to 8 partial reassemblies
	std::vector<std::vector<uint8_t>> mAckQueue;
	std::vector<Message> mComplete;
	std::vector<uint16_t> mDoneIds; // recently completed msgIds (dup re-ack)
	uint64_t mResends = 0;
};
} // namespace pc_netplay_bulk
