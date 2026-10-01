// Standalone policy test for pc_p2_btk.h (pure J3D1btk1/TTK1 decoder, #239).
// Builds a synthetic TTK1 with known tracks, then (if P2_BTK_FILE is set)
// parses the real private Queen BTK and checks the TEXMTX0 sample is finite.
#include "pc_p2_btk.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <vector>

using namespace p2btk;

static void put16(std::vector<unsigned char>& b, size_t at, unsigned v)
{
	b[at]     = (unsigned char)(v >> 8);
	b[at + 1] = (unsigned char)(v & 0xff);
}
static void put32(std::vector<unsigned char>& b, size_t at, unsigned v)
{
	b[at]     = (unsigned char)(v >> 24);
	b[at + 1] = (unsigned char)(v >> 16);
	b[at + 2] = (unsigned char)(v >> 8);
	b[at + 3] = (unsigned char)(v & 0xff);
}
static void putf(std::vector<unsigned char>& b, size_t at, float v)
{
	unsigned u;
	std::memcpy(&u, &v, 4);
	put32(b, at, u);
}

static std::vector<unsigned char> synthetic()
{
	std::vector<unsigned char> b(0xE8, 0);
	std::memcpy(&b[0], "J3D1btk1", 8);
	std::memcpy(&b[0x10], "SVR1", 4);
	std::memcpy(&b[0x20], "TTK1", 4);
	put32(b, 8, 0xE8);
	put32(b, 0x0C, 1);
	put32(b, 0x24, 0xE8 - 0x20);
	b[0x28] = 0;                 // loop mode
	b[0x29] = 0;                 // angle scale
	put16(b, 0x2A, 30);          // duration
	put16(b, 0x2C, 3);           // three times matrix anims (1 animation)
	put16(b, 0x2E, 3);           // scale count
	put16(b, 0x30, 3);           // rotation count
	put16(b, 0x32, 3);           // translation count
	put32(b, 0x34, 0x60);        // texmat anim offset
	put32(b, 0x38, 0x98);        // index offset
	put32(b, 0x3C, 0x9B);        // string table (unused)
	put32(b, 0x40, 0x9A);        // mat index offset
	put32(b, 0x44, 0x9C);        // center offset
	put32(b, 0x48, 0xA8);        // scale offset
	put32(b, 0x4C, 0xB4);        // rotation offset
	put32(b, 0x50, 0xBC);        // translation offset
	// texmat anim table: nine (count, offset, tangentType) triples.
	const int counts[9]   = { 1, 1, 1, 1, 1, 1, 1, 1, 1 };
	const int offsets[9]  = { 0, 0, 0, 1, 1, 1, 2, 2, 2 };
	for (int c = 0; c < 9; ++c) {
		put16(b, 0x80 + c * 6, (unsigned)counts[c]);
		put16(b, 0x80 + c * 6 + 2, (unsigned)offsets[c]);
		put16(b, 0x80 + c * 6 + 4, 0);
	}
	put16(b, 0xB8, 0);           // animation index 0
	b[0xBA] = 0;                 // TEXMTX0
	putf(b, 0xC8, 2.0f);
	putf(b, 0xCC, 3.0f);
	putf(b, 0xD0, 4.0f);
	put16(b, 0xD4, 16384);       // 90 degrees at angle scale 0
	put16(b, 0xD6, 0);
	put16(b, 0xD8, 0);
	putf(b, 0xDC, 1.5f);
	putf(b, 0xE0, 0.0f);
	putf(b, 0xE4, 0.0f);
	putf(b, 0xBC, 0.5f);         // center
	putf(b, 0xC0, 0.5f);
	putf(b, 0xC4, 0.5f);
	return b;
}

int main()
{
	Animation anim;
	const std::vector<unsigned char> raw = synthetic();
	assert(parse(raw.data(), raw.size(), anim));
	assert(anim.duration == 30 && anim.matrices.size() == 1);
	assert(anim.matrices[0].matrixIndex == 0);
	float s[3], r[3], t[3];
	assert(sample(anim, 0, 0.0f, s, r, t));
	assert(s[0] == 2.0f && s[1] == 3.0f && s[2] == 4.0f);
	assert(r[0] > 89.9f && r[0] < 90.1f && r[1] == 0.0f && r[2] == 0.0f);
	assert(t[0] == 1.5f && t[1] == 0.0f && t[2] == 0.0f);
	assert(!sample(anim, 3, 0.0f, s, r, t)); // no TEXMTX3 in the file
	// Malformed inputs are rejected, not thrown.
	assert(!parse(nullptr, 0, anim));
	assert(!parse(raw.data(), 12, anim));
	std::vector<unsigned char> wrong = raw;
	wrong[0] = 'X';
	assert(!parse(wrong.data(), wrong.size(), anim));

	// Optional: parse the real private Queen BTK and check TEXMTX0 is finite.
	const char* file = std::getenv("P2_BTK_FILE");
	if (file) {
		std::ifstream in(file, std::ios::binary | std::ios::ate);
		assert(in.good());
		const std::streamsize size = in.tellg();
		in.seekg(0);
		std::vector<unsigned char> data((size_t)size);
		assert(in.read(reinterpret_cast<char*>(data.data()), size));
		Animation real;
		assert(parse(data.data(), data.size(), real));
		assert(!real.matrices.empty());
		assert(sample(real, 0, 0.0f, s, r, t));
		assert(sample(real, 0, float(real.duration) * 0.5f, s, r, t));
		assert(sample(real, 0, float(real.duration), s, r, t));
		std::printf("P2_BTK_POLICY file=%s matrices=%zu duration=%d "
		            "scale=%.4f,%.4f,%.4f rot=%.4f,%.4f,%.4f trans=%.4f,%.4f,%.4f\n",
		            file, real.matrices.size(), real.duration, s[0], s[1], s[2], r[0], r[1], r[2], t[0], t[1], t[2]);
	}
	std::puts("P2_BTK_POLICY_PASS synthetic_parse_sample_reject");
	return 0;
}
