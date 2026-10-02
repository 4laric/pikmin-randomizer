#pragma once
// Netplay M3 lockstep input record (issue #880): the GekkoNet `input_size`.
//
// Fixed, explicitly serialised 16-byte struct, little-endian, never a raw
// struct memcpy so the wire format is stable across compilers:
//   offset  size  field
//   0       2     buttons u16 (PAD_BUTTON_* bits)
//   2       1     stickX s8
//   3       1     stickY s8
//   4       1     substickX s8
//   5       1     substickY s8
//   6       1     triggerL u8
//   7       1     triggerR u8
//   8       2     control yaw u16, M2c quantisation (1/65536 turns)
//   10      1     flags u8 (0 unless M4: bits 0/1 randstate chunk, bit 2 HOLD)
//   11      5     zero padding to 16 bytes
//
// Engine-free and host-testable: only <cstdint>/<cstddef>. The session layer
// fills it from the local physical pad 0 sample plus the local control yaw,
// and injects received records into sControllerPad[0] (host/P1) and [1]
// (joiner/P2) plus the M2c yaw slots.

#include <cstddef>
#include <cstdint>

namespace pc_netplay_gekko {
constexpr size_t kInputBytes = 16;
constexpr uint8_t kFlagsNone = 0;
// M4 lane A randomizer snapshot stream (issue #885): the host carries one
// 168-byte PcRandState per 42 consecutive submits in the input spare bytes.
//   flags bit 0  HAS_CHUNK  this input carries a snapshot fragment
//   flags bit 1  CHUNK_LAST this fragment is index 41 (the last of 42)
//   pad[11]      fragment sequence: high 2 bits stream id (0), low 6 bits
//                fragment index 0..41 (see pc_netplay_randstate.h)
//   pad[12..15]  4 payload bytes (snapshot bytes idx*4 .. idx*4+3)
// The joiner never sets these bits. Inputs without HAS_CHUNK decode exactly
// as before (pad bytes zero), so the wire is unchanged when the stream is
// idle. Repeated or duplicate fragments decode as ordinary inputs whose
// fragment payload the reassembler ignores as a no-op.
constexpr uint8_t kFlagsRandChunk = 0x01;
constexpr uint8_t kFlagsRandLast = 0x02;
// M4 lane B1 synchronized HOLD (issue #885): the host sets this on exactly
// one submitted input (edge-triggered) when its randomizer link goes down.
// That input's GekkoNet frame H is the hold frame on both peers: both keep
// submitting through frame H+11 (kHoldLeadFrames 12 exceeds the maximum
// local delay 8), advance through H+11 and then stop until the host's
// RESUME snapshot (bulk kBulkRandFull) is in hand. The joiner never sets it.
constexpr uint8_t kFlagsHold = 0x04;
} // namespace pc_netplay_gekko

struct PcNetplayInput {
	uint16_t buttons = 0;
	int8_t stickX = 0;
	int8_t stickY = 0;
	int8_t substickX = 0;
	int8_t substickY = 0;
	uint8_t triggerL = 0;
	uint8_t triggerR = 0;
	uint16_t controlYaw = 0;
	uint8_t flags = 0;
	uint8_t fragSeq = 0;
	uint8_t fragData[4] = {};
};

// Encodes exactly 16 bytes. Returns bytes written (16).
inline size_t pc_netplay_input_encode(const PcNetplayInput& in, uint8_t out[16])
{
	out[0]  = (uint8_t)(in.buttons & 0xFF);
	out[1]  = (uint8_t)((in.buttons >> 8) & 0xFF);
	out[2]  = (uint8_t)in.stickX;
	out[3]  = (uint8_t)in.stickY;
	out[4]  = (uint8_t)in.substickX;
	out[5]  = (uint8_t)in.substickY;
	out[6]  = in.triggerL;
	out[7]  = in.triggerR;
	out[8]  = (uint8_t)(in.controlYaw & 0xFF);
	out[9]  = (uint8_t)((in.controlYaw >> 8) & 0xFF);
	out[10] = in.flags;
	out[11] = in.fragSeq;
	out[12] = in.fragData[0];
	out[13] = in.fragData[1];
	out[14] = in.fragData[2];
	out[15] = in.fragData[3];
	return pc_netplay_gekko::kInputBytes;
}

// Decodes from the first 16 bytes. Returns false when avail < 16.
inline bool pc_netplay_input_decode(const uint8_t* data, size_t avail, PcNetplayInput& out)
{
	if (data == nullptr || avail < pc_netplay_gekko::kInputBytes) return false;
	out.buttons   = (uint16_t)(data[0] | ((uint16_t)data[1] << 8));
	out.stickX    = (int8_t)data[2];
	out.stickY    = (int8_t)data[3];
	out.substickX = (int8_t)data[4];
	out.substickY = (int8_t)data[5];
	out.triggerL  = data[6];
	out.triggerR  = data[7];
	out.controlYaw = (uint16_t)(data[8] | ((uint16_t)data[9] << 8));
	out.flags     = data[10];
	out.fragSeq   = data[11];
	out.fragData[0] = data[12];
	out.fragData[1] = data[13];
	out.fragData[2] = data[14];
	out.fragData[3] = data[15];
	return true;
}

// Neutral (hands-off) input: no buttons, centred sticks, yaw 0.
inline PcNetplayInput pc_netplay_input_neutral()
{
	return PcNetplayInput();
}

// B2 residual (fix round 2): per-turn physical-pad accumulator. The driver
// samples the pad every loop turn but submits to GekkoNet at most one input
// per Advance, so a tap that starts and ends between two submit turns would
// be lost. Between submits the driver folds every sample into one of these:
// button bits OR-accumulate (a short tap is never lost), while the sticks,
// triggers and control yaw keep the latest sample (held state). take()
// returns the merged input and clears the button latch; sticks/yaw stay at
// their latest values (the next turn's sample overwrites them anyway).
// Scripted file inputs bypass this (one record is consumed per submit).
struct PcNetplayAccum {
	uint16_t buttons = 0;
	int8_t stickX = 0;
	int8_t stickY = 0;
	int8_t substickX = 0;
	int8_t substickY = 0;
	uint8_t triggerL = 0;
	uint8_t triggerR = 0;
	uint16_t controlYaw = 0;

	void reset()
	{
		buttons = 0;
		stickX = stickY = 0;
		substickX = substickY = 0;
		triggerL = triggerR = 0;
		controlYaw = 0;
	}

	void add(uint16_t b, int8_t sx, int8_t sy, int8_t cx, int8_t cy, uint8_t tl,
	         uint8_t tr, uint16_t yaw)
	{
		buttons |= b;
		stickX = sx;
		stickY = sy;
		substickX = cx;
		substickY = cy;
		triggerL = tl;
		triggerR = tr;
		controlYaw = yaw;
	}

	void add_input(const PcNetplayInput& in)
	{
		add(in.buttons, in.stickX, in.stickY, in.substickX, in.substickY,
		    in.triggerL, in.triggerR, in.controlYaw);
	}

	PcNetplayInput take()
	{
		PcNetplayInput out;
		out.buttons = buttons;
		out.stickX = stickX;
		out.stickY = stickY;
		out.substickX = substickX;
		out.substickY = substickY;
		out.triggerL = triggerL;
		out.triggerR = triggerR;
		out.controlYaw = controlYaw;
		out.flags = 0;
		buttons = 0; // clear the latch; sticks/yaw keep latest
		return out;
	}
};
