# Purple ordinary save smoke profile (#1128)

`sdl_acquire` and `natural_resume` retain their 60-second child limit.
`sdl_save_resume` launches an `sdl_dayend` child with a 120-second whole
cutoff. The compiled fixture independently observes steady-clock time since
fixture entry: acquisition must verify before 60 seconds; that exact one-way
transition starts a further 60-second ordinary-save phase. Missing, duplicate,
late, backwards or nonfinite observations fail. The wrapper requires matching
phase evidence and real save/card oracles before launching a distinct fresh
`natural_resume` process, which remains limited to 60 seconds.

The ordinary sunset path lets its movies finish without requesting a skip.
The legal Forest sunset and takeoff movies have authored durations of 599 and
359 frames at 30 fps (about 31.93 seconds together), before diary/save UI.
Actual Purple09b acquired at 47.743 seconds and requested sunset at 47.776;
its old 60-second whole bound left only 12.224 seconds. The inherited fixture
requested a phase-zero skip, while the native safety guard retained phase-one
takeoff (~11.967 seconds). That failure preceded diary and card creation.
Its logs remain failure evidence; this profile is not gameplay acceptance.

Initial withdrawal remains fixture-assisted. No clock, stock, card, actor or
game-state injection is added. Normal menu, diary reveal/advance, native card
write, exact saved identity and fresh-process resume remain required.
