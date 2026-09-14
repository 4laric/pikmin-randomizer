# Fixture command-length sweep (#437)

Owner Codex through shared 4laric. Root baseline 8babbce; native 41304fd7 unchanged. Integrated only the run_command portion of candidate 321db4e: compiler/linker argv longer than 7000 characters is passed through a private GCC response file, preserving the existing selected objects/libraries and escaping backslashes and quotes. Short commands are unchanged.

Validation: 14 fixture-builder tests passed, 9 subtests passed. Actual MinGW preprocessor execution through a response file with 400 padding macros, quoted macro value and source path containing spaces PASS. Evidence under output/p2-rsp-sweep. No production build/export or gameplay run.

The candidate's expand_response_files heuristic remains held: reconstructing deleted Ninja response files from transitive inputs is not yet proven to preserve exact direct link inputs, library order and escaping. Do not claim this sweep fixes parsing every long Ninja target; it fixes execution after commands have been safely selected. Next lane-07/fixture handoff should capture exact Ninja response contents or validate reconstruction against the actual link edge, including static libraries and paths with spaces.

New family/provider handoffs seen: lane 11 two-process cave restart 13b7dec, lanes 02/03/05 accepted-placement gate 4dbe7c4, lifecycle new-scene finding 84502c7 and lane 13/15 combined native c22e219. These remain queued for native/shared-contract review; no whole-family promotion from this sweep.

Open lanes refreshed: 33/33 (32 implementation/QA + integration), change 0. This tracks full-lane acceptance, not running sessions or completed handoff slices.
