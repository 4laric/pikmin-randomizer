#pragma once
// Pure J3D1btk1 (TTK1 texture-SRT) decoder + sampler for the Bulblax Queen
// texture-matrix animation (#239 remaining BTK item). Engine-independent and
// self-contained so it compiles under strict MinGW flags, mirroring
// pc_p2_envmap.h. Queen's queenchappy_model.btk (J3D1btk1, TTK1, 448 bytes,
// sha256 af0dde01...) animates TEXMTX0 for the specular stage.
//
// Layout (J3D): [J3D1btk1][u32 size][u32 sectionCount=1] then a 16-byte SVR1
// block, then TTK1:
//   0x00 'TTK1', 0x04 u32 sectionSize
//   0x08 u8 loopMode, 0x09 s8 angleScale, 0x0A u16 duration
//   0x0C u16 threeTimesMatrixAnims, 0x0E u16 scaleCount,
//   0x10 u16 rotCount, 0x12 u16 transCount,
//   0x14..0x30 u32 offsets relative to the TTK1 tag:
//     texMatAnim, index, stringTable, matIndex, center, scale, rotation,
//     translation (at 0x14,0x18,0x1C,0x20,0x24,0x28,0x2C,0x30).
// Each texMatAnim entry is 0x36 bytes = 27 u16 (U/V/W x scale/rot/trans,
// each (count, offset, tangentType)). Rotation tracks are s16 in the file and
// scale by 2^angleScale * 180/32768 to degrees; scale/translation are float.
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

namespace p2btk {

struct Key {
	float time;
	float value;
	float tangentIn;
	float tangentOut;
};

struct Track {
	std::vector<Key> keys;
};

// U, V, W component tracks plus the matrix centre.
struct MatrixAnim {
	int matrixIndex = 0;
	float center[3] = { 0.0f, 0.0f, 0.0f };
	Track scale[3];
	Track rotation[3];
	Track translation[3];
};

struct Animation {
	int loopMode = 0;
	int angleScale = 0;
	int duration = 0;
	std::vector<MatrixAnim> matrices;
};

inline uint16_t u16(const unsigned char* p) { return uint16_t((p[0] << 8) | p[1]); }
inline int16_t s16(const unsigned char* p) { return int16_t((p[0] << 8) | p[1]); }
inline uint32_t u32(const unsigned char* p)
{
	return (uint32_t(p[0]) << 24) | (uint32_t(p[1]) << 16) | (uint32_t(p[2]) << 8) | uint32_t(p[3]);
}
inline float f32(const unsigned char* p)
{
	uint32_t v = u32(p);
	float f;
	std::memcpy(&f, &v, 4);
	return f;
}

// Cubic Hermite between the bracketing keys, using the stored slope tangents.
inline float evaluate(const Track& track, float frame)
{
	if (track.keys.empty()) return 0.0f;
	if (frame <= track.keys.front().time) return track.keys.front().value;
	if (frame >= track.keys.back().time) return track.keys.back().value;
	for (size_t i = 1; i < track.keys.size(); ++i) {
		const Key& a = track.keys[i - 1];
		const Key& b = track.keys[i];
		if (frame <= b.time) {
			const float span = b.time - a.time;
			if (!(span > 0.0f)) return b.value;
			const float u  = (frame - a.time) / span;
			const float u2 = u * u;
			const float u3 = u2 * u;
			const float h00 = 2.0f * u3 - 3.0f * u2 + 1.0f;
			const float h10 = u3 - 2.0f * u2 + u;
			const float h01 = -2.0f * u3 + 3.0f * u2;
			const float h11 = u3 - u2;
			return h00 * a.value + h10 * span * a.tangentOut + h01 * b.value + h11 * span * b.tangentIn;
		}
	}
	return track.keys.back().value;
}

inline void readTrack(Track& track, const unsigned char* base, int count, int offset, int tangentType, bool rotation, float rotScale)
{
	if (count < 1 || count > 4096) return;
	if (count == 1) {
		float raw = rotation ? float(s16(base + 2 * offset)) * rotScale : f32(base + 4 * offset);
		track.keys.push_back(Key { 0.0f, raw, 0.0f, 0.0f });
		return;
	}
	const int stride = tangentType == 1 ? 4 : 3;
	for (int j = 0; j < count; ++j) {
		const int at = offset + j * stride;
		Key k;
		if (rotation) {
			k.time        = float(s16(base + 2 * at));
			k.value       = float(s16(base + 2 * (at + 1))) * rotScale;
			k.tangentIn   = float(s16(base + 2 * (at + 2))) * rotScale;
			k.tangentOut  = tangentType == 1 ? float(s16(base + 2 * (at + 3))) * rotScale : k.tangentIn;
		} else {
			k.time       = f32(base + 4 * at);
			k.value      = f32(base + 4 * (at + 1));
			k.tangentIn  = f32(base + 4 * (at + 2));
			k.tangentOut = tangentType == 1 ? f32(base + 4 * (at + 3)) : k.tangentIn;
		}
		if (!std::isfinite(k.time) || !std::isfinite(k.value) || !std::isfinite(k.tangentIn) || !std::isfinite(k.tangentOut)) return;
		track.keys.push_back(k);
	}
}

// Parse a J3D1btk1 buffer; returns false on malformed data (never throws).
inline bool parse(const unsigned char* data, size_t size, Animation& out)
{
	if (data == nullptr || size < 0x80 || std::memcmp(data, "J3D1btk1", 8) != 0) return false;
	if (u32(data + 8) != size) return false;
	const size_t ttk = 0x20;
	if (std::memcmp(data + ttk, "TTK1", 4) != 0 || size < ttk + 0x34) return false;
	const unsigned char* t = data + ttk;
	out.loopMode   = t[8];
	out.angleScale = int8_t(t[9]);
	out.duration   = u16(t + 10);
	const int animCount  = int(u16(t + 12)) / 3;
	const int scaleCount = int(u16(t + 14));
	const int rotCount   = int(u16(t + 16));
	const int transCount = int(u16(t + 18));
	if (animCount < 1 || animCount > 64 || scaleCount < 0 || rotCount < 0 || transCount < 0) return false;
	const size_t texMatAnim  = ttk + u32(t + 20);
	const size_t matIndexOff = ttk + u32(t + 32);
	const size_t centerOff   = ttk + u32(t + 36);
	const size_t scaleOff    = ttk + u32(t + 40);
	const size_t rotOff      = ttk + u32(t + 44);
	const size_t transOff    = ttk + u32(t + 48);
	if (texMatAnim + size_t(animCount) * 0x36 > size) return false;
	if (matIndexOff + size_t(animCount) > size) return false;
	if (centerOff + size_t(animCount) * 12 > size) return false;
	if (scaleOff + size_t(scaleCount) * 4 > size) return false;
	if (rotOff + size_t(rotCount) * 2 > size) return false;
	if (transOff + size_t(transCount) * 4 > size) return false;
	const float rotScale = std::pow(2.0f, float(out.angleScale)) * (180.0f / 32768.0f);
	out.matrices.clear();
	for (int i = 0; i < animCount; ++i) {
		MatrixAnim m;
		m.matrixIndex = data[matIndexOff + i];
		for (int c = 0; c < 3; ++c) {
			m.center[c] = f32(data + centerOff + 12 * i + 4 * c);
			if (!std::isfinite(m.center[c])) return false;
		}
		const unsigned char* e = data + texMatAnim + size_t(i) * 0x36;
		// Table order is U(scale,rot,trans), V(scale,rot,trans), W(...).
		for (int comp = 0; comp < 9; ++comp) {
			const int axis       = comp % 3;
			const int count      = int(u16(e + comp * 6));
			const int offset     = int(u16(e + comp * 6 + 2));
			const int tangentType = int(u16(e + comp * 6 + 4));
			if (axis == 0) {
				readTrack(m.scale[comp / 3], data + scaleOff, count, offset, tangentType, false, rotScale);
			} else if (axis == 1) {
				readTrack(m.rotation[comp / 3], data + rotOff, count, offset, tangentType, true, rotScale);
			} else {
				readTrack(m.translation[comp / 3], data + transOff, count, offset, tangentType, false, rotScale);
			}
		}
		out.matrices.push_back(m);
	}
	return true;
}

// Sample one animated matrix at a source frame into scale/rotation(deg)/translation.
inline bool sample(const Animation& anim, int matrixIndex, float frame, float scale[3], float rotation[3], float translation[3])
{
	for (const auto& m : anim.matrices) {
		if (m.matrixIndex != matrixIndex) continue;
		if (!std::isfinite(frame)) return false;
		for (int c = 0; c < 3; ++c) {
			scale[c]       = evaluate(m.scale[c], frame);
			rotation[c]    = evaluate(m.rotation[c], frame);
			translation[c] = evaluate(m.translation[c], frame);
			if (!std::isfinite(scale[c]) || !std::isfinite(rotation[c]) || !std::isfinite(translation[c])) return false;
		}
		return true;
	}
	return false;
}

} // namespace p2btk
