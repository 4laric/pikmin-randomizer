# Netplay co-op: how to play (one copy-paste code each way)

Two players on two PCs can play one co-op session by exchanging one code in
each direction: the host sends an **offer code**, the joiner sends back an
**answer code**. Nobody sets environment variables or copies files. One
player can also test alone with two windows on one PC (see below). There is
no hosted matchmaking or relay service: the codes are the whole connection
setup.

## What both players need

- The **same netplay build** of `nectar.exe` (a build configured with
  `-DPIKMIN_NETPLAY_BUILD=ON`). The handshake hashes the running exe, so
  even a one-byte difference refuses with `[netplay] handshake refused: exe`.
  A build tree's `bin\nectar.exe` also needs the MinGW runtime DLLs
  (`SDL2.dll`, `libstdc++-6.dll`, `libgcc_s_seh-1.dll`,
  `libwinpthread-1.dll`) next to it or on `PATH`; an installed game folder
  already has them.
- **Their own game data.** The game reads `assets\` (the game data) and
  `pikmin_settings.conf` (your settings) from the folder you start it from,
  its *working directory*. Start the exe from your game folder (the one
  holding `assets\`), or put a junction named `assets` pointing at your
  game data into the folder you start from. The launcher never changes the
  working directory, except for seeds with P2 enemies (see below).
- A network path between the two PCs (see Troubleshooting).

## What the game does for you

When you start with `--netplay-host-ice` or `--netplay-join-ice`, the game
sets the whole session up before anything else loads:

- It creates a **private run folder** for this session and this player:
  `netplay\run-<date>-<time>-<host|join>-pid<id>\` next to the exe (or
  `%LOCALAPPDATA%\Nectar\netplay\` when the exe folder is read-only, or when
  its path is longer than about 105 characters, which the run's files would
  not fit under Windows' 259-character path limit; the game prints one line
  saying where it writes, and `--continue` looks in both places). Every
  session gets a new one; it is never reused. Inside it:
  - `session\runs\<token>\bootstrap.txt`: the session's seed file, with this
    player's own `SESSION` line, plus the game's `state.txt`/`hello.txt`;
  - `session\campaign\`: this session's memory card (`card\card0`) and
    day-end campaign files;
  - `save\`: the private save folder (`NECTAR_SAVE_DIR`, used for the
    shader cache);
  - `launch.txt` (what the session used), `settings-at-start.conf` (a copy
    of your settings file as it was), and `offer.txt` or `answer.txt` (the
    code this player produced).
- Your own memory card and your saves are **never used or written**: the
  session plays on the run folder's card.
- **Settings.** The host's sim-relevant settings (the ones that change how
  the game plays: mods such as chain actions or no tripping, the Pikmin
  limit, day length, and so on) are the session's. The joiner adopts them
  for the session only. During the session those settings are locked (an
  F1 change to them reverts when the menu closes), and your
  `pikmin_settings.conf` always keeps your own values for them: F1 still
  saves presentation changes (window size, graphics, bindings), and a save
  with no such change leaves the file untouched. With the randomizer
  running, some settings are fixed by the randomizer anyway (day length,
  health, speeds).
- **Seed.** Without `--bootstrap`, the host starts the default new game:
  Forest of Hope day 2, 25 ship parts, red Pikmin, 10 Flarlic (the
  `tools/netplay/run_pair.py` profile). There is no Archipelago in a netplay
  session: the game gives itself a fixed ready state (the unlock mask the
  pair tools use, 127; no parts, no Flarlic, no received items).

## Host steps

1. Open a console (PowerShell or Command Prompt) in your game folder and
   run:
   `.\nectar.exe --netplay-host-ice`
   (PowerShell needs the `.\`: it does not run a program from the current
   folder by its bare name; Command Prompt accepts it too. Every command
   on this page is written so that it works in both.)
   - To play a randomizer seed, add its bootstrap file:
     `.\nectar.exe --netplay-host-ice --bootstrap C:\path\to\bootstrap.txt`.
     Seeds with P2 enemies (`ENEMY_P2` in the file) work too: host from the
     seed's own folder (the one holding the seed's `assets\` overlay and its
     `p2-*.txt` / `sarai-*.txt` files); see "Seeds with P2 enemies".
2. The game prints a one-line **offer code** (it starts with `NPIX2-`) and
   copies it to the clipboard.
3. Send the offer code to the joiner (chat, DM, anything).
4. When the joiner sends the **answer code** back (it starts with `NPIX1-`),
   paste it into the host's console and press Enter. A bad paste prints
   why and asks again; it does not end the session.
   (Scripts can pass `--netplay-answer-in <file>` instead: the game waits
   for a valid answer in that file.)
5. Both games print `[netplay] ice completed in ...ms` and start. The input
   delay is measured automatically, and then follows the connection during
   the session (see "Input delay and hitches").

## Joiner steps

1. Copy the host's whole offer code, open a console in your game folder,
   and run one of:
   - `.\nectar.exe --netplay-join-ice "@clipboard"` (reads the clipboard:
     the easiest, and it has no length limit),
   - `.\nectar.exe --netplay-join-ice "@C:\path\to\offer.txt"` (a file
     holding the code),
   - `.\nectar.exe --netplay-join-ice NPIX2-...` (the code itself; a big
     offer can exceed the console's command-line limit, 8,191 characters in
     Command Prompt, so prefer `@clipboard` or `@file` for large seeds).
   Keep the double quotes around `"@..."`: in PowerShell a bare `@clipboard`
   is its splatting syntax and silently passes nothing, so the game would
   get no offer code. Command Prompt removes the quotes as usual.
   You need no file from the host: the offer carries the seed file, the
   netplay seed and the host's sim settings.
2. The game prints a one-line **answer code** and copies it to the
   clipboard. Send it to the host. (`--netplay-code-out <file>` also writes
   it to a file, on either side.)
   For a seed with P2 enemies, also pass `--netplay-p2-assets <folder>`:
   your own copy of that seed's P2 assets overlay (see "Seeds with P2
   enemies"); without it the joiner refuses before creating anything.
3. Wait for `[netplay] ice completed in ...ms`; the session starts.

Controls: by default each game takes input the usual way. To pin a device,
add `--netplay-input keyboard` (keys and mouse only, every gamepad
ignored), `--netplay-input gamepad` or `gamepad:N` (the first or the N-th
gamepad only, every key ignored; the pad keeps working while another window
has focus, and a pad plugged in later is picked up), or
`--netplay-input auto` (the default behaviour). In a session the debug
hotkeys (F5, F6, F9) and photo mode (F3, or its touch button) do nothing: they
would change one player's game only. Start skips a cutscene for both players,
whichever of you presses it, and the button names in text windows read the
same on both screens (A, B, X, Y, Z, L, R, C-Stick) whatever each of you plays on.

Keep the console open: it shows the codes and the session log. To keep a
log file, start the game with `> host.log 2>&1` added (the code is still
copied to the clipboard and written to the run folder).

## Input delay and hitches

Both games run the same frames with the same inputs (lockstep), so each
press takes effect a few frames after you make it: the **input delay**, 1
to 8 frames (33 to 267 ms). Each game has its own delay; it gives your
inputs time to reach the other game.

- It starts at the value the connection test picks when the session starts
  (`[netplay] auto delay: ... delay=N`).
- Then it follows the connection. When your inputs reach the other game too
  late, that game has to wait for them, and in lockstep both games wait: a
  **hitch** (the picture holds still for a moment). The other game reports
  its waits to yours four times a second. About a tenth of a second of
  waiting within 3 s raises your delay by one frame (by two when the waits
  keep coming), usually within a second or two. After 15 s without waits,
  if the ping allows, it drops back one frame. A drop that brings the waits
  back is undone at once, and the next drop waits longer (30 s, then 60 s,
  up to 2 minutes).
- Every change prints one line, for example
  `[netplay] delay change: 2 -> 3 at frame=591 ... (up: peer late 215ms ...)`.
- It never changes while a stage is loading, for a moment after a stage
  load, or in the first 5 s (150 frames). It
  never goes more than 2 frames above what the ping needs, and a slow
  moment on your own PC (a shader being built) does not raise it: a delay
  only hides network time.
- Changing the delay never changes the game: both games still apply
  exactly the same inputs on exactly the same frames. Only the moment your
  presses take effect changes.
- A hitch longer than the delay still shows as a short freeze, for example
  a Wi-Fi hiccup of a few hundred ms. While the game waits for the other
  game's input it does not draw new frames; the music keeps playing and
  the window stays responsive (it can be moved, and closing it works).

The console shows a `[netplay] stats:` line every 300 frames (10 s): your
delay and the other game's, the waits (`stalls=`, `last10s=`), the ping
(`rtt ... p50 p95`, jitter) and the frame times. At the end of the session
it shows `[netplay] stats final:`, the `delay timeline:` and a frame-time
histogram. The HUD (below) shows the same delay, but its waits are a
different count: `stalls=` counts every wait of any length, including
waits during a stage load and the first 5 s (they are also listed as
`excluded=`) and long hitches, and `last10s=` counts the waits that
*began* in the last 10 s; the HUD counts a wait only after it ends, only if
it lasted at least one frame (34 ms), and never during a stage load. The
`[netplay] link:` line (every 30 s) uses the HUD's count. So after the
same hitch the two can disagree; see "The netplay HUD".

To keep the delay at its starting value (for a comparison), set
`PIKMIN_NETPLAY_ADAPTIVE_DELAY` to `0` in the console you start the game
from, then start the game as usual. In PowerShell, the host runs:

```powershell
$env:PIKMIN_NETPLAY_ADAPTIVE_DELAY = '0'
.\nectar.exe --netplay-host-ice
```

and the joiner runs (with the host's offer code on the clipboard):

```powershell
$env:PIKMIN_NETPLAY_ADAPTIVE_DELAY = '0'
.\nectar.exe --netplay-join-ice "@clipboard"
```

(or `.\host.bat` / `.\join.bat` in the playtest folder). In Command
Prompt: `set PIKMIN_NETPLAY_ADAPTIVE_DELAY=0`, then the same command.

**Undo it.** `$env:` stays set for the whole PowerShell window, so every
later session started from that window keeps the delay fixed until you
either close the window or run:

```powershell
Remove-Item Env:PIKMIN_NETPLAY_ADAPTIVE_DELAY
```

In Command Prompt: `set PIKMIN_NETPLAY_ADAPTIVE_DELAY=` (or close the
window). The game says which you have: `[netplay] adaptive delay: ...`
in the console at the start of the session.

## Camera

Your camera answers your camera buttons at once, on the next frame,
although your captain's moves still arrive with the session's input delay
(see "Input delay and hitches"; typically 2-5 frames, 67-167 ms, and it can
change during the session). That covers turning (hold L a little and push
the stick sideways), recentring behind your captain (L click), zoom (R) and
the camera angle (Z). The camera still follows your captain where the game
actually has them, so during a fast turn the view swings round straight
away and your captain starts walking in the new direction a moment later,
the same moment as any other move. When the delay changes (see "Input
delay and hitches"), the camera still answers on the next frame, but a turn
in progress can show one small jump or hold: when the delay grows by k
frames, that frame's camera input is applied k extra times in one frame
(the extra frames repeat it), and when it shrinks by k frames, the k
skipped frames sample no camera input, so a turn holds still for them.
Adaptive changes are 1 to 2 frames, so this is small, and it has not been
judged in a human playtest yet. Your stick always means "the way your
camera was facing on your screen when you pushed it", for the host and the
joiner alike (the joiner's stick used to follow the host captain's camera
instead, so after either player turned a camera the joiner walked off at an
angle). With the Free Camera mod, the mouse and the right stick turn your
own captain's camera on both PCs (the joiner's used to do nothing). When
the day ends, the view stops leading as the sunset starts, and the sunset
takes over within a frame.

To go back to the old camera, which moves with the same delay as your
captain, set `PIKMIN_NETPLAY_CAMERA_LEAD` to `0` before starting the game
(either player; it only changes that player's own view). That keeps the two
joiner fixes; to undo those too (the joiner's stick and mouse follow the
host captain's camera again, as before), also set
`PIKMIN_NETPLAY_JOINER_OWN_CAMERA` to `0`. In PowerShell, in the console
you start the game from, the host runs:

```powershell
$env:PIKMIN_NETPLAY_CAMERA_LEAD = '0'
$env:PIKMIN_NETPLAY_JOINER_OWN_CAMERA = '0'   # only to undo the joiner fixes too
.\nectar.exe --netplay-host-ice
```

and the joiner runs (with the host's offer code on the clipboard):

```powershell
$env:PIKMIN_NETPLAY_CAMERA_LEAD = '0'
$env:PIKMIN_NETPLAY_JOINER_OWN_CAMERA = '0'   # only to undo the joiner fixes too
.\nectar.exe --netplay-join-ice "@clipboard"
```

(or `.\host.bat` / `.\join.bat` in the playtest folder). In Command
Prompt: `set PIKMIN_NETPLAY_CAMERA_LEAD=0` and, for the joiner fixes too,
`set PIKMIN_NETPLAY_JOINER_OWN_CAMERA=0`, then the same command. The console
says what you have: `[netplay] camera lead: on` or `off`, and `own-camera
yaw and drag: on` or `off` on the same line.

**Undo it.** `$env:` stays set for the whole PowerShell window, so every
later session started from that window keeps the old camera until you
close the window or run:

```powershell
Remove-Item Env:PIKMIN_NETPLAY_CAMERA_LEAD
Remove-Item Env:PIKMIN_NETPLAY_JOINER_OWN_CAMERA
```

In Command Prompt: `set PIKMIN_NETPLAY_CAMERA_LEAD=` and
`set PIKMIN_NETPLAY_JOINER_OWN_CAMERA=` (or close the window).

The old *camera* is not the old *input stream*. Even with both switches at
`0`, the game only sends exactly the inputs the build before the instant
camera sent if the adaptive delay is off as well
(`PIKMIN_NETPLAY_ADAPTIVE_DELAY=0`, see "Input delay and hitches"): with
the adaptive delay on, a gamepad's sample is repeated on the extra frames
when the delay grows and the taps of skipped frames merge into one when it
shrinks. Set all three to compare the feel of that older build or to chase
a desync against it.

## Sound

Both PCs simulate both captains, so each PC would otherwise play every
captain-owned sound twice over: the whistle, the footsteps, the captain and
Pikmin voices and the C-stick (swarm) sound of the *other* player's captain
as well as your own. In a session each PC plays those sounds for its own
captain only (the host's is Olimar, the joiner's Louie). Positional sounds
(enemies, Pikmin, the ship, items) are unchanged and heard from where the
other captain really is, from your own point of view: the listener follows
your captain and your own camera, never the other player's. Music, the
day clock signals, the cinematic sound (including the day-end march and the
take-off) and the "captain down" cue and music change are shared and play on
both PCs. A deterministic replay of a recorded input log (no host or join
switch) mutes nothing: one person watches both captains.

Audio is local output and never part of the simulation, so none of this can
change a state hash or desynchronise a session. To compare with the older
behaviour set `PIKMIN_NETPLAY_AUDIO_LEGACY=1` on a PC. To log what the audio
side does (the sequencer, mixer and stream clocks against wall time, the
listener, cinematic sound events, the C-stick sound's starts and stops, each
cinematic's sound-frame requests, and the BGM, demo-sequence and effect
sequencers' ticks against their tempo), set `PIKMIN_NETPLAY_AUDIO_TRACE=1`;
the `[audio-trace]` lines go to the game's console output.

## The netplay HUD

During a session a small box on the right, just below the day counter,
shows how the connection is doing:

```
NETPLAY  good
ping 42 ms  jitter 3 ms
delay 2 (67 ms)  stalls 0 / 10 s
```

- **NETPLAY good / fair / poor** (green / yellow / red; `measuring` in grey
  until the first ping): *good* is a ping of at most 100 ms, jitter of at
  most 15 ms and no stall in the last 10 s; *fair* is a ping of at most
  200 ms, jitter of at most 40 ms and at most 3 stalls in the last 10 s;
  anything worse is *poor*.
- **ping**: the round trip to the other game (the average of the last 10
  measurements); **jitter**: how much it changes between measurements.
  The games exchange their inputs once per frame, so the ping includes up
  to one frame (33 ms) of that rhythm: two games on the same PC or LAN
  read about 33 ms, not 1 ms.
- **delay**: the input delay in frames (one frame is 33 ms at 30 Hz). Your
  own captain moves this many frames after you press, so both games can
  apply every input on the same frame. It follows the connection, so the
  number can change during a session (see "Input delay and hitches").
- **stalls / 10 s**: how often, in the last 10 seconds, this game had to
  wait at least one frame (34 ms) for the other game's input (the picture
  pauses briefly). A wait is counted when it ends, and by when it ended.
  Waits during a stage load are not counted; long hitches are. This is not
  the count of the `[netplay] stats:` line: that one counts every wait of
  any length (also the ones during a stage load and the first 5 s, which it
  lists under `excluded=`), and its `last10s=` counts the waits that began
  in the last 10 s. The `[netplay] link:` line uses the HUD's count. The
  `[netplay] tick=...` line's `stalls=` counts single loop turns without a
  frame, not waits.

**F4** shows or hides the box; on a gamepad press **both sticks in (L3 +
R3)** together. F4 does nothing while you have bound it to a game action in
the controls; a keyboard-only game (`--netplay-input keyboard`) ignores the
pad chord. The stick buttons are first person (L3) and lock-on (R3) by
default; while the host has turned either mode on for the session (or you
bound another action to a stick button), pressing both sticks does only that
in the game, not the box, and only F4 toggles it (the log says so once). The box is hidden while the F1 menu is open. It never changes
the game: the other player's game is not told about it. The same numbers go
to the log every 30 s (`[netplay] link: ...`); the fuller
`[netplay] stats:` line comes every 10 s (see "Input delay and hitches").

## When a session ends (desync, lost connection, quit)

If the two games stop agreeing (a desync), the connection is lost, or the
other player closes their game, the session ends. The game then shows a
banner for up to 10 seconds (any key or button closes it early) and prints
a short recovery screen with save status and fresh host/join steps. The console
keeps the full diagnostics and launch commands, for example:

```
[netplay] ==== netplay session ended ====
[netplay] CONNECTION LOST: no data from the other game for too long (it may have crashed or lost its network).
[netplay] Last save: the end of day 2; the campaign continues from the start of day 3 (checkpoint 1).
[netplay] To carry on from that day, run this in the game's folder (PowerShell or Command Prompt):
[netplay]   .\host.bat --continue
[netplay]   or: .\nectar.exe --netplay-host-ice --continue
[netplay] Your partner joins as usual (.\join.bat); your saved day is sent to them automatically.
```

The save is made at the **end** of a day, so the next session starts at the
**start** of the following day; the `Last save` line names both.

The `or:` line repeats this game's own `--netplay-input` switch, if it had
one. The joiner's console message names the same commands for the host. If you renamed the exe to a name
with spaces (for example `nectar (2).exe`), the console gives two lines
instead of `or:`: `or in PowerShell: & '.\nectar (2).exe' ...` and `or in
Command Prompt: ".\nectar (2).exe" ...`, because each console quotes it
differently.

- **DESYNC** (exit code 5): the games disagreed about the game state.
  Both games then trade a short report over the connection (up to 4 s) and
  each writes it into its own run folder; the game window can linger for that
  time and Windows may call it "Not responding", which is harmless: wait for
  the banner. **If a desync happens, BOTH players send their whole run
  folder** (zip it): the host's and the joiner's folder are needed together,
  and a replay of a continued session needs the host's folder (it holds the
  start checkpoint the replay begins from). The message names the folder. It
  holds:
  - `session-inputs.pknl`: every frame's two inputs and this game's state hash
    (written all session, flushed every 2 s, about 3 MB per hour), so the
    session can be replayed offline on one machine from its start checkpoint
    (`tools/netplay/replay_session.py`; the replay compares its hashes with
    the recorded ones and names the first frame that differs);
  - `desync-report.txt`: both games' sub-hashes at the desynced tick (navi,
    piki, teki, item, world, rng, rand and an extra `xtra` hash over state the
    other columns do not cover), which of them differ, the first tick where
    the two games differ, and the objects that differ there;
  - `desync-subs.txt` (the last ~68 s of per-tick sub-hashes, both games),
    `desync-objects.txt` (one line per object at the first differing tick: ids,
    positions, states, health, per-object hashes) and `desync-peer-objects.txt`.
  `tools/netplay/diff_desync.py <your run>/desync-objects.txt <their
  run>/desync-objects.txt` shows the objects that differ. Test knobs:
  `PIKMIN_NETPLAY_INPUT_LOG=<file>` (or `0`) moves or disables the input log,
  `PIKMIN_NETPLAY_FORENSICS=0` turns the per-tick object capture off.
- **DESYNC AT THE DAY-END SAVE** (exit code 5) / **SAVE NOT AGREED** (exit
  code 6): the day-end save did not finish the same way on both games, so
  that day does not count; the campaign continues from the day before.
- **CONNECTION LOST**: no data from the other game for 15 s (60 s during a
  stage load).
- **THE OTHER PLAYER LEFT**: the other game was closed. A game that is
  closed mid-session tells the other one at once, so it no longer waits
  15 s.

Nothing is lost except the day in progress: the campaign continues from the
last day that ended with the day-end save on both games (see below). If no
day has ended yet, the message says so, and the next session starts a new
campaign. If the session ends right at a day-end save, the joiner's message
may say that save `may not count`: the joiner cannot tell whether the host
finished it (the host counts it only once it has heard back from the
joiner). The host's message is the one that knows, and the host's
`--continue` uses exactly that day. A joiner's own run folder counts the
save only once the joiner has played on 10 frames past it **while the host
was still connected**; a host that had just left does not count.

## Local two-window test (one PC, one player)

```
tools\netplay\play_local.bat -Exe C:\path\to\netplay\nectar.exe
```

It starts a host window (keyboard) and a joiner window (first gamepad) on
this PC and moves the codes between them through files, so there is nothing
to paste. The keyboard window is the host; the gamepad drives the joiner
even while the host window has focus (connect it before you start; a pad
plugged in later is also picked up). Close both game windows (or press Ctrl+C in the console) to finish.

- Each window gets its own working folder under `-OutDir` (default
  `%LOCALAPPDATA%\Nectar\netplay-local\host` and `...\join`), with an
  `assets` junction and its own settings file; each writes its console log
  there (`native.log`).
- Game data: `-Assets <folder>`, else `assets\` next to the exe, else the
  installed game data `%APPDATA%\PikminRandomizer\game-data\assets`.
- It uses this PC only (loopback, no STUN server), and on a build tree it
  puts `C:\msys64\mingw64\bin` on `PATH` for the two games when `SDL2.dll`
  is not next to the exe.
- Both windows open windowed at 960x540, centred on the screen: drag one
  aside, and click the host window before you use the keyboard (keys only
  reach the window that has focus; the gamepad does not need focus).
  `-WindowSize WxH` changes the size, `-WindowSize off` keeps each
  window's own settings.
- `-Bootstrap <file>` plays a seed; `-HostInput`/`-JoinInput` change the
  devices. `-Hidden` is the automated test mode (hidden, bounded).

## Seeds with P2 enemies

A seed with `ENEMY_P2` (or any `P2_...` word) reads extra per-run files from
the working directory: the P2 sidecars (`p2-*.txt`, `sarai-*.txt`,
`demon-*.txt`, `damagumo-*.json` and `p2_bigtreasure_events.txt`, next to
the seed's `bootstrap.txt`) and a P2 `assets\` overlay (the room models in
`assets\dataDir\courses\pikmin2room\`, about 35 MB, the stage files in
`assets\dataDir\stages\`, `assets\config.ini` and `assets\p2-*.txt`).
For such a seed the launcher:

- makes `<run folder>\play\` the working directory before anything loads,
  with `play\assets` a junction to the overlay (the host's is the seed
  folder's `assets\`; the joiner's is its `--netplay-p2-assets` folder);
  your `pikmin_settings.conf` stays the one in the folder you started from;
- copies the host's sidecars into its `play\`, and sends them to the joiner
  before the session starts (the joiner's `play\` receives them);
- never sends the overlay: it is game content. Each player brings their own
  copy (a full copy, or one with junctioned folders: only the content
  counts), and the handshake compares a digest of both (`handshake refused:
  p2assets` when they differ). The sidecars are checked against the host's
  digest too (`handshake refused: sidecars`).

With the low-level switches the joiner's working folder receives the host's
sidecars the same way; its own sidecar files that differ are moved to
`sidecar-set-aside-<time>\` (never deleted). The host's P2 receipt ledgers
(`p2-*-receipts.txt`) are sidecars too, so they travel with the set.

`p2-binding-receipt.json`, the `*-install.json` files and
`overlay-manifest.json` are not needed at run time and are not sent.

## Two sessions in a row (resume)

At the end of a day both games save at the same moment. The host writes the
real campaign checkpoint (`session\campaign\<generation>.sav`) and the
card; the joiner writes the same files as a mirror; the two games then agree
on the host's result before either continues (a `[netplay] save barrier`
line in both logs). The joiner's mirror is written as `<generation>.sav.pending`
and only becomes `<generation>.sav` once the host reports success. If the
other game disconnects there (no network traffic for 15 s), or is still
connected but has not reached the save within 60 s, the day is abandoned as
it would be without netplay (exit 6); if the two saves differ, both games stop
with exit 5 (a desync). Either way the joiner renames its unconfirmed mirror
to `*.sav.unconfirmed` (never deleted), so the next session sees the last
day both games agreed on and simply receives the host's checkpoint.

When a session starts, the two games compare their newest checkpoints:
the same checkpoint on both sides plays on; a joiner that is behind (or has
none) gets the host's checkpoint and card before the session starts
(`[netplay] checkpoint adopted`); a joiner that is ahead of the host, or has
a different checkpoint of the same day, refuses (`handshake refused:
checkpoint`). A joiner checkpoint from another seed or a damaged one is set
aside (renamed `*.sav.stale-<time>`, never deleted) and replaced.

### Continue the campaign (`--continue`)

The one-command launcher starts every session in a new run folder. Without
`--continue` that is a new campaign. To carry on with the last campaign,
the **host** adds `--continue`:

```
.\nectar.exe --netplay-host-ice --continue
```

or, in the playtest folder, `.\host.bat --continue` (host.bat passes its
switches on; a host.bat that asks `Continue last campaign? [Y/n]` adds it
for you). The joiner does nothing different: it joins with the usual offer
code, and the host's saved day reaches it at the handshake (`[netplay]
checkpoint adopted`).

- `--continue` picks the newest host run folder (under `netplay\` next to
  the exe, or `%LOCALAPPDATA%\Nectar\netplay\`) whose campaign has a
  day-end save **both** games agreed on, and says which:
  `[netplay] launch: --continue: continuing the campaign of ...\run-...:
  checkpoint 1 (day 3)`. Both games then start that day from its
  beginning.
- When the exe's folder path is too long for the run folder to fit under
  it (about 105 characters), the game makes the run folder under
  `%LOCALAPPDATA%\Nectar\netplay\` instead, and `--continue` looks in both
  places.
- It never continues a half-saved day: a day-end save that did not finish
  on both games (exit 5 or 6 at the save, or a game that crashed during
  it) is skipped, and the day before it is used. Each run folder keeps a
  small `campaign-record.txt` for this (which saves both games agreed on;
  the joiner writes a save there only once the session has played on
  10 frames past it with the host still connected: the host sends its
  input for those frames only after its own save finished, while a host
  that dropped out gets neutral input from the network layer, which does
  not count).
- A run folder without `campaign-record.txt` (made by an older build) is
  skipped, because it cannot tell which saves both games agreed on; the log
  names it. A record that a crash damaged stops the search there, rather
  than continue an older campaign by mistake. Either can still be continued
  by naming the folder (below); the game then warns that the save it uses
  (`UNCONFIRMED`) may not have been agreed.
- If the newest host session saved nothing (a new campaign whose first day
  never ended) and an older campaign has a saved day, `--continue` asks
  `Continue the older campaign of ... (checkpoint 1, day 3) instead? [Y/n]`
  before it uses the older one (n starts a new campaign).
- Runs are ordered by when they started (`started_utc` in `launch.txt`),
  so a clock change (daylight saving) does not make an older run look
  newer.
- `--continue <run folder>` continues that run folder instead (for example
  an older campaign, or a run where you were the joiner: its campaign is the
  same, so either player can host the next session). Quote a folder that
  holds spaces:
  `.\nectar.exe --netplay-host-ice --continue "C:\My Games\netplay\run-20260929-140000-join-pid1234"`.
- `--continue` with `--bootstrap <seed file>` continues the newest campaign
  **of that seed**.
- The seed file and the netplay seed come from the continued run; the
  settings are this session's, as always.
- Nothing is moved or deleted: the saved day, the memory card and the
  campaign's other files are **copied** into the new run folder, and the
  old run folder stays exactly as it was. The new run's record names the
  continued save only after every copy is on the disk, so a crash while
  copying leaves a folder that a later `--continue` does not pick.
- The memory card and the campaign's other files (for example the P2
  receipt ledgers) are carried as the old run left them, which can be a
  little later than the saved day (a card written by a save that did not
  count, or P2 receipts of the day in progress). Both games get the same
  files at the handshake, so they stay in step. A run where you were the
  joiner has no `p2-delivery-receipts.txt` (the host keeps it), so P2
  deliveries recorded there are granted again when you continue it.
- No saved day yet (the first day never ended with a save): `--continue`
  says so (`--continue: no saved day yet ...`) and offers a new campaign
  instead (`Start a new campaign instead? [Y/n]`; without a console it
  starts one).

Seeds with P2 enemies continue too: the continued run's `play\` folder
(its sidecars and P2 receipt ledgers) and its P2 assets overlay are used
again; if that overlay was moved, pass `--netplay-p2-assets <folder>`.

Resuming through the pair tools (`tools/netplay/run_pair.py --run-name ...
--token ...`, which keep both campaign folders) keeps working as before.

Every session needs a new run folder on both sides (the game refuses a run
folder that was already used), and the joiner's `mirror-events.txt` starts
again at frame 0 in each one. A runner that ingests the joiner's mirror must
therefore treat each session as its own run (a new peer token and run
folder), not append the second evening to the first evening's run.

## Troubleshooting

- `[netplay] handshake refused: exe` or `protocol`: the builds differ. Use
  the same `nectar.exe` on both PCs.
- `[netplay] handshake refused: config`, `bootstrap` or `seed`: the two
  games did not agree on the session setup. With `--netplay-host-ice` /
  `--netplay-join-ice` the offer carries it, so this means different builds.
  The low-level switches `--netplay-ice-host` / `--netplay-ice-join` (note
  the word order) use each side's own settings, seed file and seed and do
  refuse here; the game prints a hint when that is the likely cause.
- `[netplay] launch: ...` at start-up: the launcher refused before creating
  anything, and says why (for example a P2 offer without
  `--netplay-p2-assets`, a pasted answer code where
  the offer belongs, an offer from an older build, or a switch that cannot
  be combined with the launcher).
- `[netplay] handshake refused: checkpoint`: the two campaigns cannot be
  reconciled (the joiner is ahead of the host, or both saved different
  worlds). `sidecars` / `p2assets`: the P2 files differ (see "Seeds with P2
  enemies").
- `[netplay] ice setup failed: bad ICE code: ...`: the code was cut off or
  belongs to the other direction (offers start `NPIX2-`, answers
  `NPIX1-`). Copy the whole single line.
- `[netplay] ice setup failed: ...timed out`: no network path between the
  PCs. Behind symmetric NATs, play over a VPN mesh (Tailscale, ZeroTier) so
  both PCs see each other's VPN address, forward a UDP port range
  (`PIKMIN_NETPLAY_ICE_PORT_BEGIN`/`_END`), or bring your own TURN server
  (`PIKMIN_NETPLAY_TURN=host:port:user:pass` on both sides).
- `[netplay] input: gamepad #0 is not connected yet`: the pad was not
  plugged in at start; it is picked up as soon as it connects.
- `[netplay] disconnected: handle=...`: the other game stopped answering
  for 15 s (60 s while a stage is loading, from the load until 30 frames
  later), or it quit or crashed. Shader compiles, stage and file loads and
  the day-end save's card writes keep the connection alive while they run,
  and a stage load may take up to 60 s even as one uninterrupted step. A
  slow PC can still drop the session if one single step outside a stage
  load (for example one very slow disk write, or a driver hang) freezes the
  game for more than 15 s. `[netplay] long tick: ...` lines show any tick
  that blocked for more than 2 s and how often the network was polled during
  it.
- Many `[netplay] delay change:` lines, up and down: the connection's
  timing keeps changing (typically Wi-Fi). A cable, or moving closer to the
  router, helps; the delay settles after a few failed drops either way.
- `[netplay] delay hold at N: capped ...`: the other game keeps waiting
  although your delay is already 2 frames above what the ping needs. The
  network is not the cause (a slow PC, a busy disk), so the delay stays.
- `[netplay] save barrier timeout ...` (exit 6): at the end of a day both
  games save and compare the result. The other game disconnected there, or
  it did not reach the save within 60 s while still connected; that day is
  not saved, and the next session continues from the last day both games
  saved.
- `[netplay] launch: --continue: no saved day yet ...`: none of the host's
  run folders has a day that ended with the day-end save on both games (for
  example the first day never ended). Answer Y (or just press Enter) to
  start a new campaign; `--continue <run folder>` picks a specific run.
- `--continue: ... made by an older build` / `stopped at ...: its campaign
  record is damaged`: that run cannot tell which saves both games agreed on.
  Name the folder you want with `--continue <run folder>`; the game warns
  (`UNCONFIRMED`) that its newest save may not have been agreed.
- `[crowd-slot] MISMATCH ...`, `REINIT ...`, `COUNT_DRIFT ...` or
  `INVALID_SLOT ...` (issue #1033): a Pikmin's squad slot is booked on a
  different captain's formation plate than the captain it follows, or a
  plate's count and slots disagree. The game sizes each plate from the slots
  it holds, keeps each plate's count, and re-homes such a Pikmin to its
  captain's plate (or re-joins it when its slot is gone) instead of ending
  the session, so these lines are diagnostics, not errors (at most 24 per
  game). Please send them: the write that first moved the Pikmin was never
  found in normal play. `at=` says where it was seen, `navi=` is the captain
  the Pikmin follows, `plate_owner=` the captain whose plate it joined,
  `piki_mode=` and `state=` what it was doing.
- Logs: the console output (or your `> file` redirect; `native.log` in the
  local test), plus the run folder `netplay\run-...\` next to the exe.

## What differs from the original game

These are deliberate changes, in a session and (for the pellet one) in single
player too:

- **Pellet seeds never get stranded in an Onion.** In the original game, seeds
  a pellet credited while the Onion was still in its start-up animation, or
  that were left over when the Onion dropped back to waiting mid-emission
  (in co-op one captain can take the last Pikmin out of an Onion while it is
  still sprouting a pellet's seeds), only came out with the next pellet, or
  were lost at day end. The Onion now re-posts the "pellet in" event once when
  it is waiting with seeds still pending, so the sprouts come out at once. The
  pellet-in sound and effect play once more at that moment (cosmetic). Which
  Onion a pellet goes to is unchanged: it is the colour most of its carriers
  are, not the pellet's own colour, so a red squad carrying a blue pellet gets
  the non-matching seed count at the red Onion (issue #1034). Each lift and
  each delivery logs a `[pellet]` line with the carrier colours, the Onion,
  the seeds and whether the colour matched.
- **A geyser throws only the captain standing on it, when there are two
  captains.** A captain more than 80 units from the geyser is left where it
  is (issue #1035; the same rule as Open Nectar 0.9). It applies whenever two
  captains exist, so it also holds in a single-player game with
  `PIKMIN_P2_SECOND_CAPTAIN` set, not only in a netplay session. With one
  captain nothing changes.

## Current limits

- No Archipelago: a netplay session plays a seed offline with a fixed
  ready state; nothing is sent or received.
- A desync, a lost connection or a quit ends the session for both players;
  nothing carries over but the last day both games saved, which the host
  continues with `--continue` (see "Continue the campaign"). There is no
  mid-session reconnect.
- The instant camera covers the gameplay view only: cutscenes, the day-end
  sequence and the results screens show what both games show, and the
  first-person view (First Person mod) keeps the delayed camera. The camera's
  click sound for a zoom or angle change still plays when the input reaches
  the game, a moment after the view has moved. If you pause (or the other
  player does) in the middle of a turn, the view stays where it was and
  settles once play resumes. The markers drawn over the world (enemy health
  gauges, item and captain labels) follow the game's camera, not the
  instant one, so while you turn they trail the world by those few frames;
  they catch up when the turn ends.
- A hitch longer than the input delay (a Wi-Fi hiccup, a slow load on one
  PC) freezes the picture until the other game's input arrives: frames are
  not drawn while the game waits (the music keeps playing). The adaptive
  delay reduces repeated hitches, not a single long one. The HUD's stall
  count is this game's own waits, so it shows a stall only after it ends
  (and it counts differently from the `[netplay] stats:` line; see "The
  netplay HUD").
- Seeds with P2 enemies need each player's own copy of the seed's P2
  assets overlay (see "Seeds with P2 enemies").
- The low-level switches (`--netplay-host`/`--netplay-join`,
  `--netplay-ice-host`/`--netplay-ice-join`) and their environment
  variables keep working; they are the test surface.

## Test knobs (harness only)

These change the simulation or start a scripted situation; they are for the
hidden test pairs (`tools/netplay/run_pair.py` scrubs them from the inherited
environment, so pass them with `--env`), not for play. When a knob changes
the sim, give it to both peers.

- `PIKMIN_NETPLAY_TEST_NAVI_TO_BOSS=<BossID>,<tick>[,<dx>,<dz>]` (issue
  #1036): once the session tick (in single player, the sim update count)
  reaches `<tick>`, captain 1 (and captain 2 in co-op, 40 units further
  along z) is placed `dx`,`dz` (default 100, 0) from the first active boss of
  that id, so its appear trigger fires and both cameras see it without a
  scripted walk. Ids: 0 Beady Long Legs, 1 Burrowing Snagret, 2 Goolix
  (no profile loads one, so there is nothing to pull to), 3 Emperor Bulblax.
  Inert when unset. It prints `[netplay-test] navis pulled to boss`.
- `PIKMIN_TEST_ONLY_PELLET_BONUS=1` (or `carry`) (issue #1034): spawns a
  matching and a non-matching number pellet of every size around each Onion
  and logs the seeds credited (`tools/netplay/pellet_bonus_check.py` checks
  the log). `carry` uses real carriers. `show` lays every colour and size out
  on the ground around the first captain for a visual check (the drawn pellet
  colour against the logged data) and never delivers them.
- `PIKMIN_NETPLAY_TEST_TELEPORT="<tick>:<navi>:<x>:<z>;..."` (issue #1037):
  once the deterministic tick reaches `<tick>`, captain `<navi>` (0 = P1, 1 =
  P2) and every Pikmin it owns are placed next to (x, z), so a scripted pair
  reaches a boss without a long walk (the Final Trial Emperor Bulblax is about
  x=17 z=2450). It changes the sim, so give it to both peers; it only works
  in a hidden test run (`PIKMIN_RANDOMIZER_TEST_BACKGROUND=1`, which
  `--netplay-test-hidden` sets) and is inert in normal play. Also
  `PIKMIN_NETPLAY_TEST_DESYNC_NUDGE=<frame>[:<kind>[:<ord>]]`, which nudges
  one object on one peer so the forensics can be shown to name it.
- `PIKMIN_TEST_CLOCK_TOD=<hour>` (issue #1031): jumps the world clock to
  that hour once, on the first gameplay tick, so a short run sits in the
  end-of-day countdown window (18.5 to 19.5).
- `PIKMIN_TEST_RAW_START=<t1,t2,...>` and `PIKMIN_TEST_PROMPT_GAMEPAD=1`
  (issue #1029): model a physical local Start press on a peer (which the
  session must ignore) and make a peer's text-window labels read as a
  gamepad player's.
