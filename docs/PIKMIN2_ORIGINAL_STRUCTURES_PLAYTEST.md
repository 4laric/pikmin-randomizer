# Original bridge and barrel gameplay checks (#1262)

Use a private original-course session with the literal tutorial day-5 source inventory admitted by Startup, source resources verified, 20 starting Pikmin, and a centered 960x540 window. Record the exact native/root commits, executable SHA-256, session/card identity and selected source inventory. The bounded engine fixture is a diagnostic executable with injected controls; use the ordinary game executable for these checks. Current source drafts still await composed original-course and campaign resume qualification.

Controls from the native port README: WASD moves, Space throws, Left Shift whistles, X dismisses, T/F/G/H direct formation, Enter pauses. In mouse pointer mode, left click throws and right click whistles. Use the configured camera controls to see the workers and completed walking surface.

## Bridge: actual work, crossing and resume

1. Find the authored long bridge near (540, 100, 775), tutorial/initgen.txt#11, and sloped bridge near (-316.782, 114, -1664.510), #12. Confirm their position and orientation against the source course; record a screenshot before work.
2. Send ordinary Pikmin onto the unfinished work face. Observe real worker assignment and repeated construction, without setting health/stage or calling fixture controls. Confirm six construction stages for the slope and fifteen for the long bridge. Recall workers during a partially worked stage and return them; prior work must remain.
3. Save using the ordinary supported campaign/card UI during partial construction. Close the game, launch the same session/card and return. Confirm completed stages, remaining work and pending extension agree with the saved world. Record whether the supported UI can actually save that moment; do not substitute an injected cache for this step.
4. Complete construction using Pikmin. Walk the captain over the physical deck, then lead non-Blue Pikmin across in both directions and carry an ordinary supported object across. Confirm no invisible collision barrier, water classification or route failure prevents crossing. Test the slope separately.
5. Save a completed bridge, close and resume the same campaign. Confirm completed deck collision, open route endpoints and ordinary worker behavior remain correct.

## Barrel: actual attacks, death, drain and resume

1. Find the original barrel near (800, 0, 1380), tutorial/initgen.txt#10. Record its authored mesh and nearby water before attacks.
2. Assign ordinary Pikmin attacks. Confirm actual attack animation events reduce health using their native work damage. Recall them before destruction and resume; the barrel must retain damage. Captain contact/attacks must not destroy it.
3. Continue ordinary Pikmin work until HP becomes strictly negative. Exact zero alone must leave the barrel intact. Observe the authored death animation finish before the barrel leaves physical collision/manager state and water begins lowering.
4. Observe the first intersecting source-order water box lower by 100 units. Check actual water queries and Pikmin/captain traversal after lowering. Record rendering separately: dynamic physics queries are implemented, but visual/audio/movie parity has not been established.
5. Save while damaged, while the death clip is pending where the ordinary UI permits it, and after destruction/draining. For each case close and resume the same card/session. Confirm state and lowering continue correctly, the destroyed barrel does not reappear, and there is no duplicate death/calendar bookkeeping or crash leaving/re-entering the course.

## Report

For each step provide expected/observed behavior, screenshots or a short video, source/session/card identity, and the private log path. Keep saves, logs and legal assets under ignored output. A failure stays open with its original evidence. Engine build/control success does not satisfy these player gameplay or campaign save/resume checks.
