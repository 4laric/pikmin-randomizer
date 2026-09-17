#pragma once
class BTeki;

// Otakara joint-matrix capture hook (#700).
//
// Observation-only scan of live Chappy-vehicle (otakara carrier class) Teki
// actors: reads each carrier's Shape joint world matrices and emits
// P2_OTAKARA_JOINT_CAPTURE markers with per-joint world positions. The host
// Chappy model carries no named "otakara" joint, so the hook enumerates the
// carrier's real joint list instead of inventing one; the consumer (#573
// Bombotakara93) selects its carry joint from the observed set.
//
// Fail-closed: a carrier with no Shape, no joints, or no finite joint matrix
// emits P2_OTAKARA_JOINT_ABSENT and never crashes, never mutates actor state,
// and never substantiates a capture. Absence alone can never satisfy ready().
//
// The #573 Bombotakara93 consumer calls pc_p2_otakara_joint_capture_poll()
// on its bound carrier (bound through the established otakara generator
// chain); this fixture calls it every guarded idle tick. New files only;
// no shared-hook changes.
void pc_p2_otakara_joint_capture_setup();
void pc_p2_otakara_joint_capture_reset();

// Scan live carriers and capture joint world matrices, emitting markers.
// Safe to call every idle tick; full per-joint output is throttled to first
// sighting plus a periodic re-capture.
void pc_p2_otakara_joint_capture_poll();

// Fixture observability (read-only, no state change).
int pc_p2_otakara_joint_capture_actor_count();
int pc_p2_otakara_joint_capture_joint_count();
unsigned pc_p2_otakara_joint_capture_last_generator();
bool pc_p2_otakara_joint_capture_ready();
