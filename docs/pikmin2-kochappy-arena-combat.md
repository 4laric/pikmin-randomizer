# Original Impact Site combat observation

Issue #120/#186. A separate private stage retains original map/collision/routes and the Red/control roster, adding20 native free-Pikmin generators parked away. Existing original-map identity/health/stored-birth validation and legitimate tutorial A-input handler remain.

Captain reposition at observation ticks1 and120 supplies70/80unit targeting stimuli. At240, the existing squad is deployed in a22unit circle around Red and switched through native changeMode(FreeMode). GenObjectPiki source spawnState1 is free; native free behavior chooses its own actions. No explicit attack action or enemy state/health/target/animation assignment is used. This is an engineered fixture stimulus, not a player-input combat test.

Target acquisition, chase state11, actual health decrease and native corpse creation are separate gates. The run stops60updates after corpse creation or at1800updates, retaining failed/unmeasured gates. Original map is not assumed flat. The private binary links frozen e704b268 objects and the previously validated private tutorial receiver object; it makes no claims about later production commits. Run the module with --stage, --exe, --output (new directory) and optional --seconds.

## Measured result

Private e704b268 run exits0 in15.89s, executable SHA256cf32f77c68d601c0bc13bae2ed723b469c46dba78e5f0fcc68803bb204e48985. Evidence output/p2-red-arena-combat/observe/evidence.json. Initial full stored birth positions and health remain Red200/control130. Observed135 targeted chase-state updates and65.59units displacement. Squad deployment tick240 leads to first health damage262, healthzero272, native corpse370; completion430. Both live and corpse Red render callbacks fire. No enemy state/health/target or explicit Pikmin attack actions were assigned. The final framebuffer was inspected but terrain occludes the corpse, so callback/render safety is measured without claiming a clear corpse visual comparison. Player-driven combat and delivery remain unmeasured.
