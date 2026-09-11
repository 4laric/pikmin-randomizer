# Graphics validation

`verify_graphics_windows.py` builds separate fixtures from a completed Windows
Ninja build's compiler flags and object files. It does not overwrite `nectar.exe`.
Use the same source revision for the build and the fixtures. Put MinGW64 on PATH;
Python and Pillow are required for PNG conversion.

```powershell
python tools/verify_graphics_windows.py --build build-graphics --assets C:/path/to/assets --output output/menus --fixture menus
python tools/verify_graphics_windows.py --build build-graphics --assets C:/path/to/assets --output output/post --fixture post
python tools/verify_graphics_windows.py --build build-graphics --assets C:/path/to/assets --output output/forest --fixture scene --area forest
```

The output directory owns all temporary executables, logs, captures, settings
and saves. An assets junction reads the supplied extracted assets. The scene
fixture uses a private direct-area bootstrap and heartbeat, without connecting
to Archipelago or an existing randomizer session. Use `--area navel` or
`--area spring` for other environments, and `--width` / `--height` for capture size.

- **menus:** preset field checks, non-graphics settings preservation, and 20
  real GX/P2D page captures. Pages 17–19 show Original, Enhanced and Custom.
  The wrapper checks that closing clears the menu and reopening restores it.
- **post:** real OpenGL bloom, FXAA and grading under disabled/mixed color
  masks. Every destination is poisoned before a case, preventing stale pixels
  from disguising a failure. Checks processed pixels and mask restoration.
- **scene:** frozen native scene under Original, Enhanced preview and cancellation
  back to Original. Captures and synchronized draw timings are for visual
  comparison; they are not a full gameplay FPS benchmark. The wrapper verifies
  that Enhanced changes the image and cancellation restores its lower 80%
  exactly, excluding the independently animated sun HUD at the top.

The existing `pc_postprocess_test` and `pc_tev_shader_test` CTest targets remain
useful for shader generation regression checks without a GPU.
