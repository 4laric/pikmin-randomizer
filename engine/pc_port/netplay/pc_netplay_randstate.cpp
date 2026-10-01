// Netplay M4 lane A randomizer snapshot codec + reassembler (issue #885).
// See pc_netplay_randstate.h for the layout and the determinism contract.
// Engine-free: <cstdint>/<cstddef>/<cstring>/<cstdio> only.

#include "netplay/pc_netplay_randstate.h"

#include <cstdio>
#include <cstring>

namespace pc_randstate {
namespace {

uint32_t crc_table_entry(unsigned i)
{
	uint32_t c = i;
	for (int k = 0; k < 8; ++k) c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
	return c;
}

constexpr size_t kGenOff = 160; // gen u32 offset in the v3 wire layout
constexpr size_t kCrcOff = 164; // crc u32 offset in the v3 wire layout

} // namespace

uint32_t crc32(const uint8_t* data, size_t len)
{
	uint32_t crc = 0xFFFFFFFFu;
	for (size_t i = 0; i < len; ++i) {
		const uint8_t b = data != nullptr ? data[i] : 0;
		crc = crc_table_entry((crc ^ b) & 0xFF) ^ (crc >> 8);
	}
	return crc ^ 0xFFFFFFFFu;
}

namespace {
void put16(uint8_t* p, uint16_t x) { p[0]=uint8_t(x); p[1]=uint8_t(x>>8); }
void put32(uint8_t* p, uint32_t x) { for (int i=0;i<4;++i) p[i]=uint8_t(x>>(8*i)); }
uint16_t get16(const uint8_t* p) { return uint16_t(p[0]) | uint16_t(p[1])<<8; }
uint32_t get32(const uint8_t* p) { uint32_t x=0;for(int i=0;i<4;++i)x|=uint32_t(p[i])<<(8*i);return x; }
}
size_t encode(const PcRandState& st, uint8_t out[kStateBytes]) {
    if (!out) return 0;
    std::memset(out,0,kStateBytes);
    out[0]=st.ver;out[1]=st.mode;put16(out+2,st.features);put16(out+4,st.checkCount);out[6]=st.schema;
    out[8]=st.ready;out[9]=st.repairs;out[10]=st.unlocks;out[11]=st.flarlic;
    out[12]=st.emperor;out[13]=st.dayLength;out[14]=st.whistlePluck;
    put32(out+16,st.deathLinks);put32(out+20,st.thelynkParts);
    std::memcpy(out+24,st.checks,kCheckBytes);std::memcpy(out+88,st.stats,12);std::memcpy(out+100,st.maturity,3);
    for(int i=0;i<9;++i)put16(out+104+2*i,st.benefits[i]);
    for(int i=0;i<18;++i)put16(out+122+2*i,st.thelynkBonuses[i]);
    put32(out+kGenOff,st.gen);put32(out+kCrcOff,crc32(out,kPayloadBytes));return kStateBytes;
}
bool decode(const uint8_t* data, size_t avail, PcRandState& out) {
    if(!data || avail!=kStateBytes || data[0]!=kVersion || data[1]<1 || data[1]>2) return false;
    if(data[7]||data[15]||data[103]||data[158]||data[159])return false;
    if((get16(data+2)&~kFeatureMask)!=0 || !get16(data+4)||get16(data+4)>kCheckSlots)return false;
    if((data[1]==1 && (data[6]<1||data[6]>9)) || (data[1]==2 && data[6]!=1))return false;
    if(data[8]>1||data[12]>1||data[14]>1||data[9]>(data[1]==2?30:25))return false;
    const uint32_t want=get32(data+kCrcOff);if(crc32(data,kPayloadBytes)!=want)return false;
    PcRandState st;st.ver=data[0];st.mode=data[1];st.features=get16(data+2);st.checkCount=get16(data+4);st.schema=data[6];
    st.ready=data[8];st.repairs=data[9];st.unlocks=data[10];st.flarlic=data[11];
    st.emperor=data[12];st.dayLength=data[13];st.whistlePluck=data[14];
    st.deathLinks=get32(data+16);st.thelynkParts=get32(data+20);
    if(st.thelynkParts>>30)return false;
    std::memcpy(st.checks,data+24,kCheckBytes);std::memcpy(st.stats,data+88,12);std::memcpy(st.maturity,data+100,3);
    for(unsigned i=st.checkCount;i<kCheckSlots;++i)if(st.checks[i/8]&(1u<<(i%8)))return false;
    for(int i=0;i<9;++i)st.benefits[i]=get16(data+104+2*i);
    for(int i=0;i<18;++i)st.thelynkBonuses[i]=get16(data+122+2*i);
    st.gen=get32(data+kGenOff);st.crc=want;if(!st.gen)return false;
    out=st;return true;
}
bool payload_equal(const PcRandState& a, const PcRandState& b) {
    uint8_t x[kStateBytes],y[kStateBytes];encode(a,x);encode(b,y);
    return std::memcmp(x,y,kGenOff)==0;
}

Reassembler::Reassembler() { reset(); }

void Reassembler::reset()
{
	memset(mSlots, 0, sizeof(mSlots));
	mMask = 0;
	mAppliedGen = 0;
	mHasPending = false;
	mPendingGen = 0;
	mPendingFrame = 0;
	mPending = PcRandState();
}

void Reassembler::feed(bool hasChunk, uint8_t seq, const uint8_t payload[kFragBytes], bool last,
                       uint32_t frame)
{
	// `last` is advisory: completion is mask-driven (all42 present), so a
	// lost CHUNK_LAST bit cannot stall the stream. A last flag on a
	// non-final index is ignored rather than acted on.
	(void)last;
	if (!hasChunk || payload == nullptr) return;
	if (frag_seq_stream(seq) != kStreamId) return;
	const uint8_t idx = frag_seq_index(seq);
	if (idx >= kFragCount) return;
	if (idx == 0 && mMask != 0 && mMask != 0x01u) {
		// Generation boundary (M1 fix): the sender emits each
		// generation's fragments consecutively starting at 0 and never
		// interrupts an in-flight generation, so a fragment 0 arriving
		// mid-transfer opens a new generation. Drop the partial buffer
		// identically on both peers and start the new one. (A bare
		// duplicate of frag 0 with nothing else buffered is still a
		// no-op below.)
		memset(mSlots, 0, sizeof(mSlots));
		mMask = 0;
	}
	if (mMask & (uint64_t(1) << idx)) return; // duplicate fragment: no-op
	for (size_t i = 0; i < kFragBytes; ++i) mSlots[idx * kFragBytes + i] = payload[i];
	mMask |= (uint64_t(1) << idx);
	if (mMask != ((uint64_t(1) << kFragCount) - 1)) return; // incomplete: wait
	PcRandState st;
	if (!decode(mSlots, sizeof(mSlots), st)) {
		// Corrupt transfer: drop it identically on both peers rather than
		// applying garbage, and say so. The generation is read straight
		// off the wire so the operator can see which update died.
		const uint32_t wireGen = (uint32_t)mSlots[kGenOff]
		    | ((uint32_t)mSlots[kGenOff + 1] << 8) | ((uint32_t)mSlots[kGenOff + 2] << 16)
		    | ((uint32_t)mSlots[kGenOff + 3] << 24);
		std::printf("[netplay] randstate gen=%u dropped: decode failed\n", wireGen);
		std::fflush(stdout);
		memset(mSlots, 0, sizeof(mSlots));
		mMask = 0;
		return;
	}
	memset(mSlots, 0, sizeof(mSlots));
	mMask = 0;
	if (st.gen <= mAppliedGen) return; // stale or replayed generation: no-op
	// An unconsumed newer snapshot is also an ordering watermark. Replaying
	// it cannot postpone its apply frame, and older snapshots cannot replace it.
	if (mHasPending && st.gen <= mPendingGen) return;
	// A newer generation replaces an unconsumed pending one only when it
	// completes later; both peers see the same stream, so the pending slot
	// stays identical.
	mPending = st;
	mPendingGen = st.gen;
	mPendingFrame = frame + 1; // apply at the start of the tick for frame F+1
	if (mAppliedGen == 0) {
		// B1 first-apply rule: delay-independent first snapshot frame.
		if (mPendingFrame > kFirstApplyFrame) {
			std::printf("[netplay] randstate gen=%u first apply late: frame=%u > %u\n", st.gen,
			            mPendingFrame, kFirstApplyFrame);
			std::fflush(stdout);
		} else {
			mPendingFrame = kFirstApplyFrame;
		}
	}
	mHasPending = true;
}

bool Reassembler::discard_pending_upto(uint32_t gen)
{
	if (!mHasPending || mPendingGen > gen) return false;
	mHasPending = false;
	return true;
}

bool Reassembler::take_pending(PcRandState& out)
{
	if (!mHasPending) return false;
	out = mPending;
	mHasPending = false;
	return true;
}

void Reassembler::mark_applied(uint32_t gen)
{
	if (gen > mAppliedGen) mAppliedGen = gen;
}

} // namespace pc_randstate
