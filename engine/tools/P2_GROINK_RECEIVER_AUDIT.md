# Groink live receiver compatibility audit

Read-only audit for #205/#208. P2 source revision
632af93787b9c95b63f0c13be32b161375ce3a96; P1 baseline native 756515d5.
No receiver implementation or accepted live damage is claimed here.

P2 InteractBomb takes (owner, damage, Vector3f*) and inherits its impulse from
InteractWind (include/Game/Interaction.h:569). P1 InteractBomb instead takes
(owner, damage, CollPart*) (include/Interactions.h:100). A direct substitution
cannot carry the source impulse.

P1 receiver differences:

- Piki Bomb (src/plugPikiKando/interactBattle.cpp:33) subtracts damage and
  enters Flick with fixed intensity 180, deriving direction from owner and
  target positions. P2 uses the provided vector and its Blow state argument.
- Navi Bomb (src/plugPikiKando/navi.cpp:2695) subtracts damage and uses Flick
  intensity 100; it cannot receive the desired direction. P2 NaviFlickArg
  carries the vector and damage.
- Teki Bomb (src/plugPikiNakata/tekiinteraction.cpp:39) multiplies damage by
  TPF_BombDamageRate before InteractAttack; this differs from P2 bombCallBack
  and does not establish that a requested 100 reaches the target unchanged.
- P1 Wind does accept a velocity vector and copies it to target velocity
  fields (interactBattle.cpp:218 and navi.cpp:2554). It nevertheless has
  different rejection states and immunity semantics, including Piki stuck
  handling and the P2 Purple/Repugnant Appendage distinctions.

Next receiver bridge must accept exact policy command, target kind, owner,
damage and impulse. Either implement dedicated typed receiver/state handling
or explicitly label a P1 compatibility approximation. Calling P1 Bomb then
Wind is not proven equivalent: first dispatch changes target state and can
alter second-dispatch eligibility. Do not overwrite velocity blindly after
a rejected hit. Record requested and accepted interactions separately, with
health/state/velocity before and after. Test immunity, repeated hits, owner
identity and teardown before natural-combat acceptance.

Terminal Wind can use InteractWind(owner, computedImpulse, 0, nullptr) only
as an explicitly scoped P1 behavior approximation. Retain the classifier's
source species/owner filtering; generic stimulate does not provide it.
