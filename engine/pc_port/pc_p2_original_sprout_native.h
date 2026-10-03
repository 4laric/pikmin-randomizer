#pragma once
#include "pc_p2_original_onyon_lineage.h"
class GoalItem;
class PikiHeadItem;
class Piki;
struct PcOriginalSproutOrigin {p2originalonyon::Root root;std::uint64_t memberSerial=0;};
// Explicit campaign boundary refuses a living graph/pending rewards.
bool pc_p2_original_sprout_new_session(std::string&);
// Caller supplies actual retained corpse/typed numeric cause before native queue
// increment. No UID/color alone or count-only stock can manufacture ancestry.
bool pc_p2_original_sprout_reward(GoalItem*,const p2originalonyon::SeedCause&,unsigned,std::string&);
bool pc_p2_original_sprout_reward_prepare(GoalItem*,const p2originalonyon::SeedCause&,unsigned,p2originalonyon::RewardPlan&,std::string&);
void pc_p2_original_sprout_reward_commit(GoalItem*,const p2originalonyon::RewardPlan&);
bool pc_p2_original_sprout_owner(GoalItem*,PcOriginalSproutOrigin&,std::string&);
void pc_p2_original_sprout_bind(PikiHeadItem*,GoalItem*,const PcOriginalSproutOrigin&);
void pc_p2_original_sprout_store(GoalItem*,const PcOriginalSproutOrigin&);
bool pc_p2_original_sprout_query(const PikiHeadItem*,PcOriginalSproutOrigin&);
bool pc_p2_original_sprout_color(const PikiHeadItem*,int);
bool pc_p2_original_sprout_owned(const PikiHeadItem*);
// Persistent SAVE discriminator. A failed full read never removes this tag.
bool pc_p2_original_sprout_head_tag(const PikiHeadItem*)noexcept;
p2originalonyon::QueryResult pc_p2_original_sprout_head_query(const PikiHeadItem*,p2originalonyon::MemberRecord&,std::uint64_t&,std::string&);
void pc_p2_original_sprout_to_body(PikiHeadItem*,Piki*);
void pc_p2_original_sprout_forget(PikiHeadItem*);
p2originalonyon::QueryResult pc_p2_original_sprout_body_query(const Piki*,p2originalonyon::MemberRecord&,std::uint64_t&,std::string&);
void pc_p2_original_sprout_body_forget(Piki*);
bool pc_p2_original_sprout_body_owned(const Piki*)noexcept;
bool pc_p2_original_sprout_body_lifetime(const Piki*,std::uint64_t&)noexcept;
bool pc_p2_original_sprout_body_recruited(Piki*,std::uint64_t);
void pc_p2_original_sprout_scene_exit()noexcept;
bool pc_p2_original_sprout_install_reader()noexcept;
std::string pc_p2_original_sprout_campaign();
bool pc_p2_original_sprout_deposit(GoalItem*,Piki*,std::string&);
bool pc_p2_original_sprout_stock(GoalItem*,p2originalonyon::MemberRecord&,std::string&);
void pc_p2_original_sprout_withdraw(GoalItem*,Piki*,const p2originalonyon::MemberRecord&);
// Ordinary unload retains stored lineage; no physical SAVE restore here.
// Early read-only HEAD/pending guard; permits BODY observation and retirement
// later, after Party observer. No current campaign resolution or tag removal.
bool pc_p2_original_sprout_preflight_course_finish(std::string&);
bool pc_p2_original_sprout_unload(std::string&);
