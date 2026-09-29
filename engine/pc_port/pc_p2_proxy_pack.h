#pragma once

// Pack-generator token policy (#871 finding 5 / integration finding 5).
// One pack generator births several tekis sharing a single campaign token
// (dwarf-bulborb / sheargrub groups). For the proxy family in bridge mode a
// repeated token binds EVERY live member and counts the token once; the five
// existing families (and preview) keep the duplicate-generator abort.
// Engine-free so the contract is unit-testable without the engine.
namespace p2proxy {
enum class TokenAction { Bind, Fail };
inline TokenAction tokenAction(bool softProxy, bool isRepeat) {
    if (!isRepeat) return TokenAction::Bind;
    return softProxy ? TokenAction::Bind : TokenAction::Fail;
}
}  // namespace p2proxy
