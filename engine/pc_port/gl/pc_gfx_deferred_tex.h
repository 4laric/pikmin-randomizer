// Deferred texture-init store for the authoritative pass (issues #879 #880).
//
// GL-free and GX-free: metadata is plain integers and every entry owns its
// source bytes, so host tests link this TU directly instead of modelling it.
// pc_gfx.cpp is the only production user: it converts the GX enums to ints
// on record and back on upload.
//
// Ownership rule (fix2 M2): entries are move-only and the source bytes are
// read only through bytes(). A take moves the entry out before the map node
// is erased, so the bytes stay alive in the caller's local; no pointer into
// a map entry ever outlives that entry.

#pragma once

#include <cstdint>
#include <unordered_map>
#include <vector>

struct PcDeferredRgba {
	std::vector<uint8_t> rgba;
	uint16_t width = 0;
	uint16_t height = 0;
	int32_t wrapS = 0;
	int32_t wrapT = 0;
};

struct PcDeferredTex {
	uint16_t width = 0;
	uint16_t height = 0;
	uint32_t format = 0;
	int32_t wrapS = 0;
	int32_t wrapT = 0;
	bool mipmap = false;
	// Non-owned source, used only when the layout is unknown and no copy
	// could be taken. Null whenever owned is populated.
	const uint8_t* alias = nullptr;
	// Owned copy of the raw GX bytes; wins over alias.
	std::vector<uint8_t> owned;
	// Fix3 R2-5: the game's original source pointer, for signature equality
	// only and never dereferenced. The drain uploads from bytes() and then
	// stores this pointer in the texture signature, so the no-change
	// early-out compares the live game pointer and no signature points at
	// the freed owned copy.
	const void* sigImage = nullptr;
	PcDeferredTex() = default;
	PcDeferredTex(const PcDeferredTex&) = delete;
	PcDeferredTex& operator=(const PcDeferredTex&) = delete;
	PcDeferredTex(PcDeferredTex&&) = default;
	PcDeferredTex& operator=(PcDeferredTex&&) = default;
	const uint8_t* bytes() const { return owned.empty() ? alias : owned.data(); }
};

struct PcDeferredCi {
	const uint8_t* alias = nullptr;
	uint16_t width = 0;
	uint16_t height = 0;
	int32_t format = 0;
	int32_t wrapS = 0;
	int32_t wrapT = 0;
	uint32_t tlutName = 0;
	bool mipmap = false;
	// Fix3 R2-6: recorded by a deferred (auth or forced) init, as opposed to
	// a presentation-side CI init waiting for its palette. Only deferred
	// entries count as drains when presentation uploads them.
	bool deferred = false;
	// Owned copy of the raw GX bytes; wins over alias.
	std::vector<uint8_t> owned;
	PcDeferredCi() = default;
	PcDeferredCi(const PcDeferredCi&) = delete;
	PcDeferredCi& operator=(const PcDeferredCi&) = delete;
	PcDeferredCi(PcDeferredCi&&) = default;
	PcDeferredCi& operator=(PcDeferredCi&&) = default;
	const uint8_t* bytes() const { return owned.empty() ? alias : owned.data(); }
};

// The three pending maps (CI description, deferred RGBA, deferred palettised)
// with the mutual-exclusion rule: an authoritative-pass init for a key erases
// the rivals before it records, so a stale CI description can never shadow a
// newer non-CI init for a reused address (and vice versa).
class PcDeferredTexStore {
public:
	void record_rgba(uintptr_t key, PcDeferredRgba def);
	void record_tex(uintptr_t key, PcDeferredTex def);
	void record_ci(uintptr_t key, PcDeferredCi def);
	// Move the entry out and drop the rival deferred entry. The CI map is
	// left alone: the caller consults it first, and a CI description whose
	// palette has not loaded yet must survive a deferred take.
	bool take_rgba(uintptr_t key, PcDeferredRgba* out);
	bool take_tex(uintptr_t key, PcDeferredTex* out);
	const PcDeferredCi* find_ci(uintptr_t key) const;
	// A real (presentation) upload supersedes a stale deferred entry.
	void erase_deferred(uintptr_t key);
	// Authoritative-pass re-init: drop every pending record for the key.
	void invalidate(uintptr_t key);
	// Release: every per-key record is freed, even with no live GL entry.
	void release(uintptr_t key);
	void clear();
	bool empty() const;
	size_t rgba_size() const;
	size_t tex_size() const;
	size_t ci_size() const;

private:
	std::unordered_map<uintptr_t, PcDeferredRgba> rgba_;
	std::unordered_map<uintptr_t, PcDeferredTex> tex_;
	std::unordered_map<uintptr_t, PcDeferredCi> ci_;
};
