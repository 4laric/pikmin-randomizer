#pragma once

// Fatal-exit breadcrumbs (claude/p2-king-silent-exit).
//
// A game process that dies without a reason in native.log is unactionable. This
// makes every death the process can observe leave one line, and makes the
// orderly exits recognisable:
//   - "[PC Port Fatal] ..." : unhandled exception, std::terminate, abort(),
//     invalid CRT parameter, console close/logoff/shutdown event.
//   - "[PC Port] orderly process exit": the CRT atexit chain ran.
// A log that ends with NEITHER was terminated from outside (TerminateProcess:
// taskkill /F, Stop-Process, Popen.terminate, all of which report exit code 1)
// or the OS pulled the process; nothing in-process can log that.
void pc_fatal_log_install();
