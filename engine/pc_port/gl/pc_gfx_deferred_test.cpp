// Host test for the polish deferred texture-init store (issues #879 #880).
//
// Unlike the earlier contract model, this links the real unit
// (pc_gfx_deferred_tex.cpp) and exercises its record / take / invalidate /
// release paths, including the fix2 M2 regression: a taken owned entry must
// keep correct bytes after the map node is gone (the old code copied the
// struct, so the copy's pointer still aimed at the erased entry's buffer).
//
// Uses the check()/failures pattern (never bare assert(): Release defines
// NDEBUG).

#include "pc_gfx_deferred_tex.h"

#include <cstdint>
#include <cstdio>
#include <type_traits>
#include <vector>

static int failures = 0;

static void check(bool condition, const char* message)
{
	if (!condition) {
		std::fprintf(stderr, "FAIL: %s\n", message);
		++failures;
	}
}

static PcDeferredTex make_tex(uint8_t fill, size_t len)
{
	PcDeferredTex def;
	def.width = 8;
	def.height = 8;
	def.format = 3;
	def.wrapS = 1;
	def.wrapT = 1;
	def.mipmap = false;
	def.alias = nullptr;
	def.owned.assign(len, fill);
	return def;
}

int main()
{
	static_assert(!std::is_copy_constructible<PcDeferredTex>::value,
	              "PcDeferredTex must be move-only (M2)");
	static_assert(!std::is_copy_assignable<PcDeferredTex>::value,
	              "PcDeferredTex must be move-only (M2)");
	static_assert(!std::is_copy_constructible<PcDeferredCi>::value,
	              "PcDeferredCi must be move-only (M2)");
	static_assert(std::is_move_constructible<PcDeferredTex>::value,
	              "PcDeferredTex must stay movable for take");

	PcDeferredTexStore store;

	// 1. Record an owned entry, take it, erase it: bytes stay correct after
	// the map node is gone (the M2 use-after-free regression).
	const uintptr_t k1 = 0x1001;
	const std::vector<uint8_t> want { 1, 2, 3, 4, 5, 6, 7, 8 };
	{
		PcDeferredTex def = make_tex(0, 0);
		def.owned = want;
		store.record_tex(k1, std::move(def));
	}
	check(store.tex_size() == 1, "record_tex must retain the entry");
	PcDeferredTex taken;
	check(store.take_tex(k1, &taken), "take_tex must take a recorded entry");
	check(store.empty(), "take must leave the store empty");
	check(taken.bytes() != nullptr, "taken entry must expose bytes");
	{
		bool match = taken.owned.size() == want.size();
		for (size_t i = 0; match && i < want.size(); ++i) match = taken.bytes()[i] == want[i];
		check(match, "taken bytes must still be correct after the erase (M2)");
	}
	check(!store.take_tex(k1, &taken), "second take must miss");

	// 1b. Same for the RGBA path (already move-based, pinned here).
	const uintptr_t k1b = 0x100b;
	{
		PcDeferredRgba def;
		def.width = 2;
		def.height = 2;
		def.rgba = want;
		store.record_rgba(k1b, std::move(def));
	}
	PcDeferredRgba takenRgba;
	check(store.take_rgba(k1b, &takenRgba), "take_rgba must take a recorded entry");
	check(store.empty(), "rgba take must leave the store empty");
	check(takenRgba.rgba == want, "taken rgba bytes must match");

	// 2. A re-init during the authoritative pass invalidates the stale
	// entry: CI once, then non-CI for the same key (heap reuse), and back.
	const uintptr_t k2 = 0x2002;
	{
		PcDeferredCi ci;
		ci.width = 8;
		ci.height = 8;
		ci.format = 5;
		ci.owned = want;
		store.record_ci(k2, std::move(ci));
	}
	check(store.find_ci(k2) != nullptr, "record_ci must retain the CI description");
	store.record_tex(k2, make_tex(9, 8));
	check(store.find_ci(k2) == nullptr,
	      "non-CI re-init must erase the stale CI entry (M2)");
	check(store.tex_size() == 1, "non-CI re-init must retain its own parameters");
	store.record_rgba(k2, PcDeferredRgba());
	check(store.tex_size() == 0 && store.rgba_size() == 1,
	      "rgba re-init must supersede a pending tex defer");
	{
		PcDeferredCi ci;
		ci.width = 4;
		ci.height = 4;
		store.record_ci(k2, std::move(ci));
	}
	check(store.rgba_size() == 0 && store.find_ci(k2) != nullptr,
	      "CI re-init must supersede a pending rgba defer");
	// A take of one deferred kind drops the rival deferred entry.
	store.record_tex(k2, make_tex(7, 4));
	PcDeferredTex rival;
	check(store.take_tex(k2, &rival), "take must succeed with a rival present");
	check(store.empty(), "take must drop the rival deferred entry");

	// 3. Release clears everything, even with entries in all three maps on
	// distinct keys.
	const uintptr_t k3a = 0x300a, k3b = 0x300b, k3c = 0x300c;
	store.record_tex(k3a, make_tex(1, 4));
	store.record_rgba(k3b, PcDeferredRgba());
	{
		PcDeferredCi ci;
		store.record_ci(k3c, std::move(ci));
	}
	store.release(k3a);
	store.release(k3b);
	store.release(k3c);
	check(store.empty(), "release must clear every per-key record (m4)");
	store.record_tex(k3a, make_tex(2, 4));
	store.clear();
	check(store.empty(), "clear must empty the store");

	// 4. bytes() prefers the owned copy over a stale alias.
	PcDeferredTex aliased;
	aliased.alias = want.data();
	aliased.owned = want;
	check(aliased.bytes() == aliased.owned.data(),
	      "bytes() must read the owned copy, never the alias, when populated");

	// 5. Fix3 R2-5: the deferred tex entry carries the game's original source
	// pointer for the texture signature. The take must preserve it, and it
	// must be distinct from bytes() (the owned copy, which dies with the
	// taken local): the drain stores sigImage, never bytes(), in the signature.
	const uintptr_t k5 = 0x5005;
	static const uint8_t gameBuf[4] = { 9, 8, 7, 6 };
	{
		PcDeferredTex def = make_tex(0, 0);
		def.owned.assign(gameBuf, gameBuf + sizeof(gameBuf));
		def.sigImage = static_cast<const void*>(gameBuf);
		store.record_tex(k5, std::move(def));
	}
	PcDeferredTex taken5;
	check(store.take_tex(k5, &taken5), "take must succeed for the sigImage entry");
	check(taken5.sigImage == static_cast<const void*>(gameBuf),
	      "take must preserve the original source pointer (R2-5)");
	check(static_cast<const void*>(taken5.bytes()) != taken5.sigImage,
	      "the owned copy must not alias the game's source pointer (R2-5)");
	{
		bool match = taken5.owned.size() == sizeof(gameBuf);
		for (size_t i = 0; match && i < sizeof(gameBuf); ++i) match = taken5.bytes()[i] == gameBuf[i];
		check(match, "sigImage entry bytes must still match after the take");
	}

	// 6. Fix3 R2-6: the CI "deferred" mark survives record and lookup, and
	// defaults to false (a presentation-side CI init is not a deferred one).
	const uintptr_t k6a = 0x600a, k6b = 0x600b;
	{
		PcDeferredCi ci;
		ci.deferred = true;
		store.record_ci(k6a, std::move(ci));
		store.record_ci(k6b, PcDeferredCi());
	}
	check(store.find_ci(k6a) != nullptr && store.find_ci(k6a)->deferred,
	      "a deferred CI record must keep its mark");
	check(store.find_ci(k6b) != nullptr && !store.find_ci(k6b)->deferred,
	      "a presentation-side CI record must not be marked deferred");
	store.clear();

	std::printf("PcGfxDeferred: %s\n", failures ? "FAILED" : "all tests passed");
	return failures ? 1 : 0;
}
