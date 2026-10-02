// See pc_gfx_deferred_tex.h. GL-free on purpose: this TU must keep compiling
// and linking on its own for the host contract test.

#include "pc_gfx_deferred_tex.h"

void PcDeferredTexStore::record_rgba(uintptr_t key, PcDeferredRgba def)
{
	tex_.erase(key);
	ci_.erase(key);
	rgba_[key] = std::move(def);
}

void PcDeferredTexStore::record_tex(uintptr_t key, PcDeferredTex def)
{
	rgba_.erase(key);
	ci_.erase(key);
	tex_[key] = std::move(def);
}

void PcDeferredTexStore::record_ci(uintptr_t key, PcDeferredCi def)
{
	rgba_.erase(key);
	tex_.erase(key);
	ci_[key] = std::move(def);
}

bool PcDeferredTexStore::take_rgba(uintptr_t key, PcDeferredRgba* out)
{
	auto it = rgba_.find(key);
	if (it == rgba_.end()) return false;
	if (out != nullptr) *out = std::move(it->second);
	rgba_.erase(it);
	tex_.erase(key);
	return true;
}

bool PcDeferredTexStore::take_tex(uintptr_t key, PcDeferredTex* out)
{
	auto it = tex_.find(key);
	if (it == tex_.end()) return false;
	if (out != nullptr) *out = std::move(it->second);
	tex_.erase(it);
	rgba_.erase(key);
	return true;
}

const PcDeferredCi* PcDeferredTexStore::find_ci(uintptr_t key) const
{
	auto it = ci_.find(key);
	return it != ci_.end() ? &it->second : nullptr;
}

void PcDeferredTexStore::erase_deferred(uintptr_t key)
{
	rgba_.erase(key);
	tex_.erase(key);
}

void PcDeferredTexStore::invalidate(uintptr_t key)
{
	rgba_.erase(key);
	tex_.erase(key);
	ci_.erase(key);
}

void PcDeferredTexStore::release(uintptr_t key)
{
	invalidate(key);
}

void PcDeferredTexStore::clear()
{
	rgba_.clear();
	tex_.clear();
	ci_.clear();
}

bool PcDeferredTexStore::empty() const
{
	return rgba_.empty() && tex_.empty() && ci_.empty();
}

size_t PcDeferredTexStore::rgba_size() const
{
	return rgba_.size();
}

size_t PcDeferredTexStore::tex_size() const
{
	return tex_.size();
}

size_t PcDeferredTexStore::ci_size() const
{
	return ci_.size();
}
