#pragma once
class Controller;
class Graphics;
// F11 opens the ordinary native file-selection UI for an explicitly enabled
// settled surface checkpoint. F1 stays unchanged. Unsupported scenes refuse.
void pc_p2_surface_save_scene_setup();
void pc_p2_surface_save_sources_loaded();
void pc_p2_surface_save_sources_preinit();
void pc_p2_surface_save_scene_exit();
bool pc_p2_surface_save_update(Controller*);
void pc_p2_surface_save_request();
void pc_p2_surface_save_draw(Graphics&);
bool pc_p2_surface_save_resume_scene();
bool pc_p2_surface_save_owns_heads();
bool pc_p2_surface_save_living_scene();
void pc_p2_surface_save_before_day_cleanup();

#include "pc_p2_original_piki_origin.h"
// Selected surface proof is available only during physical party restoration.
bool pc_p2_surface_save_survivor_permit(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,std::uint64_t*,std::uint8_t[32]);
bool pc_p2_surface_save_survivor_body(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,OriginalPikiBodyState&,std::uint64_t*,std::uint8_t[32]);
