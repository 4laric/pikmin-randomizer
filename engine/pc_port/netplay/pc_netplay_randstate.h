#pragma once
// Co-op complete external state, codec3 (#1148). Explicit little-endian168-byte
// snapshot:512 check bits, optional progression and TheLynk inventory. Existing
// seed/AP/save formats are unchanged; session protocol4 binds this wire layout.
#include <cstddef>
#include <cstdint>
namespace pc_randstate {
constexpr size_t kCheckBytes = 64;
constexpr size_t kCheckSlots = kCheckBytes * 8;
constexpr size_t kStateBytes = 168;
constexpr size_t kPayloadBytes = 164;
constexpr uint8_t kVersion = 3;
constexpr size_t kFragCount = 42;
constexpr size_t kFragBytes = 4;
constexpr uint32_t kFirstApplyFrame = 64;
constexpr uint8_t kStreamId = 0;
constexpr uint16_t kFeatureMask = 0x03ff;
// Pad byte11 keeps the packet16 bytes: high2 bits stream, low6 index.
inline uint8_t frag_seq_make(uint8_t idx) { return uint8_t((kStreamId << 6) | (idx & 0x3f)); }
inline uint8_t frag_seq_stream(uint8_t seq) { return uint8_t(seq >> 6); }
inline uint8_t frag_seq_index(uint8_t seq) { return uint8_t(seq & 0x3f); }
struct PcRandState {
    uint8_t ver = kVersion, mode = 1;
    uint16_t features = 0, checkCount = 512;
    uint8_t schema = 9;
    uint8_t ready = 0, repairs = 0, unlocks = 0, flarlic = 0;
    uint8_t emperor = 0, dayLength = 0, whistlePluck = 0;
    uint32_t deathLinks = 0, thelynkParts = 0;
    uint8_t checks[kCheckBytes] = {}, stats[12] = {}, maturity[3] = {};
    uint16_t benefits[9] = {}, thelynkBonuses[18] = {};
    uint32_t gen = 0, crc = 0;
};
uint32_t crc32(const uint8_t* data, size_t len);
size_t encode(const PcRandState& st, uint8_t out[kStateBytes]);
// Structural validation is atomic. Mode/bootstrap monotonicity is validated by
// pc_randomizer_apply_net_state before any simulation state changes.
bool decode(const uint8_t* data, size_t avail, PcRandState& out);
bool payload_equal(const PcRandState& a, const PcRandState& b);
class Reassembler {
public:
	Reassembler();

	// Feed one fragment carried by the Advance for `frame`. Has no effect
	// unless hasChunk is set. `seq` is the pad[11] sequence byte, `payload`
	// the 4 pad[12..15] bytes, `last` the CHUNK_LAST flag (advisory only:
	// completion is mask-driven so a lost flag bit cannot stall the
	// stream; a last flag on a non-final index is ignored).
	void feed(bool hasChunk, uint8_t seq, const uint8_t payload[kFragBytes], bool last,
	          uint32_t frame);

	// True when a snapshot completed and is waiting for its apply frame.
	bool has_pending() const { return mHasPending; }
	uint32_t pending_gen() const { return mPendingGen; }
	// The frame whose tick-start must apply the pending snapshot (F+1 where
	// F is the frame whose Advance completed the transfer).
	uint32_t pending_frame() const { return mPendingFrame; }
	const PcRandState& pending() const { return mPending; }

	// Applies (consumes) the pending snapshot. The caller performs the
	// actual sim apply, then records the generation. Returns false when
	// nothing was pending.
	bool take_pending(PcRandState& out);
	void mark_applied(uint32_t gen);
	// M4 lane B1 RESUME: drops a pending snapshot whose generation is
	// <= gen (the bulk RESUME snapshot supersedes it). Returns true when one
	// was dropped.
	bool discard_pending_upto(uint32_t gen);

	uint32_t applied_gen() const { return mAppliedGen; }
	void reset();

private:
	uint8_t mSlots[kStateBytes] = {};
	uint64_t mMask = 0; // bit i set when fragment i received
	uint32_t mAppliedGen = 0;
	bool mHasPending = false;
	uint32_t mPendingGen = 0;
	uint32_t mPendingFrame = 0;
	PcRandState mPending = {};
};

} // namespace pc_randstate
