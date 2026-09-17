#pragma once
// Port Bomb birth hook notifier (lane bomb-birth-hook-notifier-port-native,
// #715; #186 review before shared-line landing).
//
// Strong definition site for pc_p2_bomb_birth_hook_notify(), which the engine
// (pikmin2-research generalEnemyMgr.cpp, #677 hook) declares weak and calls
// from the Bomb/BombOtakara manager-create arms. Linked into pikmin_pc, the
// strong definition overrides the weak no-op so live Bomb births notify the
// port birth seam. Engine-free (only <cstdio>); safe in every target.
//
// The engine arms already filter to Bomb-family IDs, so this notifier is a
// faithful pipe: it records every call in a bounded ring and prints the
// receipt marker. It never invents births and never touches gameplay state.
// The test accessors below exist so the provider fixture can verify the pipe
// without parsing stdout; they are tiny, side-effect-free reads plus reset.
void pc_p2_bomb_birth_hook_notify(int enemyID);

// Test-support observation (fixture use; harmless in the engine link).
int p2_bomb_notifier_count();
int p2_bomb_notifier_last();
void p2_bomb_notifier_reset();
