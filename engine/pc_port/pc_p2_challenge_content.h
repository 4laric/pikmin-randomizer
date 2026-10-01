#pragma once
// P2 challenge stage content wiring (lane kusachi-content-engine-wiring-native,
// #728; #186 review before shared-line landing).
//
// Binds the selected challenge stage's roster content into the live squad so a
// real boot reports content_wired>0. Called per-tick from pc_bbft_update()
// through a null-by-default hook (same link-safety contract as the challenge
// runtime hook: pc_bbft.cpp stays engine-free; this engine-dependent module
// lives only in pikmin_pc and the replacement fixture link, never in
// pc_bbft_test).
//
// Test-only content binding: converting live pikis to the roster color is a
// private-fixture action (labeled, never shipped) so the #533 consumer can
// observe stage content. It uses only the public Piki::setColor API, which
// validates the color and falls back safely. Maturity matching is follow-on
// work, recorded in the packet, not claimed here.
struct P2ChallengeContentStatus {
    int wired;
    int total;
    int targetColor;
};

// Per-tick content update. Inert (silent) unless a valid stage row is selected.
void p2_challenge_content_update();

// Last bound content count for fixtures to poll (fail-closed runs).
// Returns 0 until content has been bound at least once.
int p2_challenge_content_wired();

// Per-frame content hook type. The pikmin_pc content module registers its
// update at startup; pc_bbft_update() invokes it when set, inert otherwise.
using P2ChallengeContentHook = void (*)();
void p2_challenge_content_set_hook(P2ChallengeContentHook hook);
