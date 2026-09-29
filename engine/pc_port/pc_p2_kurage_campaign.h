#pragma once
// Kurage (source 57) campaign-vs-fixture gate + hover/tail tuning (#871).
//
// Engine-free so native tests can pin the contract without booting the game:
//   * campaign mode  = seed bridge WITHOUT the isolated room preview
//     (mirrors pc_p2_batch2.cpp's `bridge` definition). The playtested
//     campaign seed runs here: no captain/Pikmin teleports, no forced mode
//     changes, no carry-limit or pellet mutations, no per-tick ground pin or
//     seek toward Pikmin.
//   * fixture mode   = room preview or any non-bridge run (staged
//     p2-kurage-teki.txt sidecar, PIKMIN_P2_KURAGE_SHOWCASE, the
//     p2_kurage_* fixtures). The labelled concessions (groundAndSeal,
//     captain park + free recruit ring) stay EXACTLY as today here because
//     the natural-engagement and transport fixtures depend on them.
namespace p2kurage_campaign {

// Jellyfloat cruise height above the map. Source ProperParms fp01 is 90.0f,
// but the P1 Frog host's melee/attack volume only reaches near the ground, so
// the campaign visual floats low (30-60u per the brief) while the host body
// stays grounded and killable. The on-screen model is offset; the actor and
// its collision are untouched.
constexpr float kHoverHeight = 40.0f;
constexpr float kHoverMin = 30.0f;
constexpr float kHoverMax = 60.0f;

// Corpse-tail bookkeeping runs once per frame on the corpse actor's own tick
// (not once per teki per frame). At 60 fps this interval logs the CORPSE line
// about once per second.
constexpr int kCorpseProbeIntervalFrames = 60;

inline bool isCampaignMode(bool bridge, bool roomPreview) { return bridge && !roomPreview; }
inline bool fixtureConcessionsAllowed(bool bridge, bool roomPreview)
{
    return !isCampaignMode(bridge, roomPreview);
}
inline bool corpseProbeDue(int tick) { return tick > 0 && tick % kCorpseProbeIntervalFrames == 0; }

} // namespace p2kurage_campaign
