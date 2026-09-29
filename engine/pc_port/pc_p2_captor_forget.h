#pragma once
// One engine seam for every P2 captor's Piki forget hook (#886): called from
// Creature::kill (death) and PikiMgr::birth (pool-slot reuse) so a held-mouth
// registration can never outlive, or be inherited by, the Pikmin it named.
class Piki;
void pc_p2_armor_forget_piki(Piki*);
void pc_p2_jigumo_forget_piki(Piki*);
void pc_p2_snakejoint_forget_piki(Piki*);
void pc_p2_umimushi_forget_piki(Piki*);
void pc_p2_uji_forget_piki(Piki*);

inline void pc_p2_captor_forget_piki(Piki* piki)
{
    pc_p2_armor_forget_piki(piki);
    pc_p2_jigumo_forget_piki(piki);
    pc_p2_snakejoint_forget_piki(piki);
    pc_p2_umimushi_forget_piki(piki);
    pc_p2_uji_forget_piki(piki);
}
