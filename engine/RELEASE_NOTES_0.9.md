# Open Nectar 0.9

A big one: a brand-new 1-vs-1 Versus mode, playable Pikmin captains, a
rebuilt F1 settings page and a round of fixes. Saves and settings carry over.

## New

- **Versus mode: "Parts Race" (1 vs 1).** A new entry in the main menu
  (Start / Co-op / VS / Options / Advanced Options / Challenge Mode). It
  revives the versus mode Nintendo left unfinished and always plays with two
  captains.
  - **Its own arena**, built in memory from the game's own Impact Site data:
    a flat walled field with a base at each end and the centre free for the
    big part. No extra files needed.
  - Each player gets their own three Onions, 15 Pikmin (5 of each colour)
    and their own rocket. Ship parts are picked by weight; deliver them to
    your rocket to score.
  - **Rocket siege (optional):** your free Pikmin near the rival rocket wear
    it down; destroying it wins the match. Each part delivered repairs it.
  - Bomb-rock gate at each base, with bombs nearby to open it.
  - **Rules menu before the match:** duration, rocket siege on/off, rocket
    health, when the big part appears, Pikmin per player and pellet respawn.
    Rules are saved with your settings.
  - 3-2-1-START countdown, per-player scoreboard and HUD, reinforcements
    for a player left with no Pikmin, and a final screen with rematch or
    back to title. Versus does not touch your save.
  - Rival sprouts can't be plucked; Pikmin fight the rival captain's squad.
  - Shortest-path routing on the arena so carriers don't take detours.
- **Pikmin captains.** In the captain picker you can now choose Olimar,
  Louie or a Red, Yellow or Blue Pikmin. A Pikmin captain looks the part
  (model, leaf light, portrait) and plays exactly like Olimar.
- **Per-player camera in Co-op/VS:** each controller's right stick turns its
  own player's camera; mouse and touch stay on Player 1.
- **New cheats:** "Invincible Pikmin" and "Unlock All Zones" (this one is
  saved to the file). Hard mode turns every cheat off.

## Changes

- **F1 settings rebuilt as a tabbed page** (Display, Graphics, Controls,
  Camera, Gameplay, Cheats, Data): rows with section headers on the left,
  the row's options and an explanation on the right. Works with controller,
  keyboard and touch, and scales up on phones.
- **Glass settings menu on the title screen** gets the same layout, with a
  scrollbar, a right-hand options column and shrinking long values.
- "Infinite Day" is now the "Infinite" stop at the end of the day-length list.
- More full-width screens (#46): file select, title, world map, course
  select, high scores and slide-in menus no longer clip to 4:3, and elements
  the original layout parks off-screen stay hidden.

## Fixes

- **Save export/import (Android):** exporting a backup no longer gets
  picked up by the HD models installer; backups hold only the two memory
  cards (the shader cache made our own ZIP fail the restore check); no more
  empty .zip when there is nothing to copy; exporting works on storage
  providers that reject overwrite mode.
- Menu key-repeat and window/resolution handling tidied up.
