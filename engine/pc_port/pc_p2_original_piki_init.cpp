#include "pc_p2_original_piki_init.h"
namespace {
thread_local PcOriginalPikiInitScope* activeScope = nullptr;
}
PcOriginalPikiInitScope::PcOriginalPikiInitScope(Piki* body) noexcept {
    if (!body || activeScope) return;
    mBody = body;
    mActive = true;
    activeScope = this;
}
PcOriginalPikiInitScope::~PcOriginalPikiInitScope() {
    if (mActive && activeScope == this) activeScope = nullptr;
}
bool pc_p2_original_piki_init_consume(Piki* body) noexcept {
    if (!body || !activeScope || !activeScope->mActive || activeScope->mConsumed
        || activeScope->mBody != body) return false;
    activeScope->mConsumed = true;
    return true;
}
bool pc_p2_original_piki_free_init_consume(Piki* body) noexcept {
    if (!body || !activeScope || activeScope->mBody != body || !activeScope->mConsumed
        || activeScope->mFreeConsumed) return false;
    activeScope->mFreeConsumed = true;
    return true;
}
bool pc_p2_original_piki_bore_init_consume(Piki* body) noexcept {
    if (!body || !activeScope || activeScope->mBody != body || !activeScope->mFreeConsumed
        || activeScope->mBoreConsumed) return false;
    activeScope->mBoreConsumed = true;
    return true;
}
bool pc_p2_original_piki_init_held(const Piki* body) noexcept {
    return body && activeScope && activeScope->mActive && activeScope->mConsumed && activeScope->mBody == body;
}
