#pragma once
// Hooks are inert unless BBFT or --randomizer-seed explicitly enables an adapter.
void pc_bbft_init(int argc, char** argv);
bool pc_bbft_enabled();
bool pc_bbft_hold();
// Agent test-run policy: background never holds for focus; visible shows the window without activating it.
bool pc_bbft_test_background();
bool pc_bbft_test_visible();
bool pc_bbft_focus_hold_policy(bool testBackgroundMode, bool foreground);
void pc_bbft_update();
void pc_bbft_warp();
bool pc_bbft_forest_access();
void pc_bbft_check(const char* name);
bool pc_bbft_checked(const char* name);
void pc_bbft_start_button(bool down);
bool pc_bbft_take_skip();
const char* pc_bbft_save_root();
void pc_bbft_milestone(const char* text);
bool pc_bbft_skip_tutorial();
bool pc_bbft_accept_input();

bool pc_bbft_progression();
bool pc_bbft_has(const char* name);
bool pc_bbft_color_access(int color);

void pc_bbft_onion_site(int color, float x, float z);
bool pc_bbft_near_onion_site(int color, float x, float z, float radius);

bool pc_bbft_shared_capabilities();
bool pc_bbft_bomb_rocks();

// Post-v0.1 isolated story-layout preview, never an AP session.
int pc_pikipelago_challenge_level();

bool pc_pikipelago_room_preview();
const char* pc_pikipelago_surface_course();
const char* pc_pikipelago_surface_stage();
