#pragma once
class BTeki;
class PelletView;
class Graphics;
struct Matrix4f;

// Adult Orange Bulborb (BlueChappy, EnemyID 42), lane 42.
//
// Source: include/Game/Entities/BlueChappy.h (adult ChappyBase branch), sharing
// the "Chappy" model/anim/collision bank; distinct from the dwarf Kochappy
// identities 44/45 ("Kochappy" bank). Opt-in: only actors claimed by the
// generated-placement bridge (source 42) or listed in `p2-bluechappy-actors.txt`
// are registered. Every hook is a no-op for unregistered actors.
void pc_p2_bluechappy_setup();
void pc_p2_bluechappy_reset();
void pc_p2_bluechappy_forget(BTeki*);
float pc_p2_bluechappy_max_health(const BTeki*, float fallback);
const char* pc_p2_bluechappy_name(PelletView*);
bool pc_p2_bluechappy_registered(const BTeki*);
unsigned long pc_p2_bluechappy_count();

// Generated-placement bridge (lane 03/04 pattern): claim the single actor the
// randomizer spawned for source ID 42 and bind the adult Orange identity.
bool pc_p2_bluechappy_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned sourceId);
