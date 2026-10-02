# Direct bounded cave play (issue930)

This original engineered floor starts20Red and uses a private local cave session.
It does not read campaign/AP saves. Use a desktop with SDL display/audio support.
Python3.12+ and psutil are required for the launcher capacity check.

Build only the native generator (two small translation units):

```sh
cmake -S tools/cave-generator -B output/cave-generator -G Ninja
cmake --build output/cave-generator -j2
```

Stage with legal private P1 assets, privately extracted Pod/treasure files,
the production game executable and generator. Linux uses nectar.real beside its
production lib/ directory; Windows uses nectar.exe beside its four DLLs. Use a NEW
output directory. Linux staging traces the supported host ELF loader with the
package library directory and refuses missing dependencies.

```sh
python3 scripts/stage_pikmin2_playable_cave.py --assets /private/assets --pod /private/pod --exe /private/nectar-linux/nectar.real --generator output/cave-generator/cave_generator --output output/cave930 --seed 930 --slot Player1 --salt 0
python3 scripts/play_pikmin2_cave.py output/cave930
```

Windows: invoke scripts with `py -3.12` or use the staged Play.cmd.
Linux: use the staged Play.sh. The launcher checks actual machine headroom,
holds an OS session lock, and retains its own child for bounded interrupt cleanup.
A repeated launch refuses an already running game for this session.
Native logs, treasure receipts and floor-boundary checkpoints stay in session/.
Relaunch the SAME package to resume; do not edit checkpoint files.

Human route (not yet gameplay acceptance):

1. Confirm centered960x540, healthy captain and20Red.
2. At Blue bud(-100,100), ordinary throws/contact and native auto-pluck acquire
   TWOBlues:18Red+2Blue, no pending sprouts.
3. Dismiss Reds on dry starting side. Select Blues and collect water treasure
   at(0,-500) by ordinary throw/swarm. Wait physical Pod delivery and exactly one
   native water receipt. This item requires one carrier.
4. Move Blues through water choke(400,0) to far segment(800,0). At Yellow bud
   (900,100), convert ONEBlue:18Red+1Blue+1Yellow. No stock/actor setters.
5. Reach far hole and F6/ordinary confirmation. Require actual native transfer
   and bud budgets. Relaunch to verify mixed-stock restore and water item absent.

Reds may remain dry: the boundary captures all living survivors, not proof the
whole mixed squad crossed water. Stop on captain loss, survivor loss, pending
sprouts, missing receipt or refusal. This is local engineered cave mechanics,
not retail geometry or campaign SAVE acceptance.
