# #895 pose-fidelity evidence (claude/p2-pose-fidelity)

Root de0bb6d8+c7992cdc, native fork 9b3d11ed2+5df40bace. Evidence only; not code.

- `motion/`: offline replay of native bracket+lerp from the staged banks
  (`scripts/p2_pose_motion_evidence.py`). Each GIF: BEFORE nearest | BEFORE lerp | AFTER dense lerp.
  `*-motion.png`: largest vertex move per displayed 30 fps frame (spikes = pops) and the
  projected path of the most-moving vertex. `summary.json`: the numbers.
- `ingame/`: consecutive in-game frames (PIKMIN_FRAME_DUMP_EVERY=1) from the bot runs,
  cropped on screen centre once the bot engages its target. Left: baseline bake
  (groink-own-content) with PIKMIN_P2_INTERPOLATION=0; right: dense bake (p2vis-content-pose2),
  defaults. Same exe (native 9b3d11ed2, sha256 7e310bdd...), same seed per species.
- `density-audit-*.txt`: `scripts/p2_pose_density_audit.py` over the staged runs
  (base = groink-own-content, impl = first implementation's p2vis-content-pose, new = this fix).
- `loop-seam-audit.json`: `scripts/p2_loop_seam_audit.py` over the retail disc.
