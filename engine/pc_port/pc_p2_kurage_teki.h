#pragma once
class BTeki;
class Graphics;
class Matrix4f;
class PelletView;
void pc_p2_kurage_teki_setup();
void pc_p2_kurage_teki_tick(BTeki*);
void pc_p2_kurage_teki_forget(BTeki*);
void pc_p2_kurage_teki_reset();
// Read-only lifecycle probe for the native runtime fixture.  Binding remains
// owned by GameCoreSection::finalSetup and the Teki lifecycle hooks.
bool pc_p2_kurage_teki_is_bound(const BTeki*);
bool pc_p2_kurage_teki_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Opt-in ordinary-actor authority: when enabled, the bound generated actor runs
// the transcribed source flight lifecycle (pc_p2_kurage_fsm.h) and its Attack
// state autonomously drives the suction admission scan instead of only drawing.
// Default off; existing binding-only consumers are unchanged.
void pc_p2_kurage_teki_fsm_enable(bool enable);
bool pc_p2_kurage_teki_fsm_enabled(const BTeki*);
int pc_p2_kurage_teki_fsm_state(const BTeki*);
int pc_p2_kurage_teki_auto_admissions(const BTeki*);
int pc_p2_kurage_teki_fsm_ticks(const BTeki*);
int pc_p2_kurage_teki_tick_calls();
// Ordinary corpse receipt (lane 29, #243). Resolves the delivered dead-body
// PelletView of a bound Lesser Jellyfloat (source ID 57) back to its generator
// so the Pod reward path can credit the corpse. Drop semantics: the source has
// no family-local reward function (enemyBase.cpp::onKill supplies a BDT_Normal
// corpse); the reward amount remains the Pod's configured corpseValue. Returns
// false for any body not owned by a bound Kurage.
bool pc_p2_kurage_receipt(PelletView* view, unsigned& generator);
int pc_p2_kurage_bound_count();
