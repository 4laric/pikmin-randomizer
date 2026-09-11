// Shared BBFT API. No game headers required.
#ifndef BBFT_TRANSPORT_H
#define BBFT_TRANSPORT_H
#ifdef __cplusplus
extern "C" {
#endif
// Optional callbacks handle game-specific file records, after a successful open.
void bbft_transport_init(const char *game, void (*file_reset)(void), void (*file_line)(char *));
void bbft_transport_update(void);
void bbft_check(const char *location_name);
// Union of locally reported checks and the latest remote checked snapshot.
int bbft_checked(const char *location_name);
// First successful file read or authoritative TCP state received.
int bbft_state_ready(void);
// Opt-in AP region gates; missing flag preserves legacy behavior.
int bbft_region_unlocks(void);
int bbft_pikmin_skip_tutorial(void);
int bbft_pikmin_progression(void);
int bbft_separate_cannons(void);
int bbft_shared_capabilities(void);
int bbft_mario_abilities(void);
int bbft_skulltula_checks(void);
int bbft_has(const char *item);
int bbft_count(const char *item);
int bbft_lock(const char *lock_id);
void bbft_warp_out(void);
int bbft_warp_held(void);
int bbft_is_foreground(void);
void bbft_logf(const char *fmt, ...);
// Pop one notification into a caller buffer; returns 1, or 0 if empty/invalid.
// Entries hold up to 255 bytes plus NUL; a full 64-entry queue drops oldest.
int bbft_next_notification(char *text, int capacity);
// Latest hub destination, consumed once; adapters defer unsafe transitions.
int bbft_take_destination(char *text, int capacity);
#ifdef __cplusplus
}
#endif
#endif
