"""Read-only, click-through Windows HUD for a running native game."""
import argparse
from collections import Counter
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import time
import tkinter as tk

from .catalog import ITEM_IDS, REPAIR, RED, YELLOW, BLUE, field_capacity, color_inventory
from .seed import fingerprint, solo_rewards


def snapshot(manifest, data):
    if data['fingerprint'] != fingerprint(manifest):
        raise ValueError('Overlay session mismatch')
    if manifest['mode'] == 'solo':
        rewards = solo_rewards(manifest)
        events = [(name, rewards[name]) for name in data['checked']]
    else:
        names = {v: k for k, v in ITEM_IDS.items()}
        events = [('Received from Archipelago', names[item]) for item in data['received']]
    inventory = Counter(item for _, item in events)
    return events, field_capacity(inventory, manifest['schema'] >= 2), min(25, inventory[REPAIR])


def main(manifest_path, session_path, pid):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    user = c.WinDLL('user32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    user.GetForegroundWindow.restype = w.HWND
    user.GetParent.argtypes = [w.HWND]
    user.GetParent.restype = w.HWND
    user.GetWindowLongW.argtypes = [w.HWND, c.c_int]
    user.SetWindowLongW.argtypes = [w.HWND, c.c_int, c.c_long]
    user.GetWindowThreadProcessId.argtypes = [w.HWND, c.POINTER(w.DWORD)]
    user.GetClientRect.argtypes = [w.HWND, c.POINTER(w.RECT)]
    user.ClientToScreen.argtypes = [w.HWND, c.POINTER(w.POINT)]
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    process = kernel.OpenProcess(0x100000, False, pid)
    if not process:
        raise OSError('Game process is not available')
    root = tk.Tk()
    root.withdraw()
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes('-transparentcolor', '#010203')
    root.configure(bg='#010203')
    canvas = tk.Canvas(root, width=430, height=235, bg='#010203', highlightthickness=0)
    canvas.pack()
    root.update_idletasks()
    hwnd = user.GetParent(root.winfo_id()) or root.winfo_id()
    # Layered, click-through, tool window, never activate or take game input.
    user.SetWindowLongW(hwnd, -20, user.GetWindowLongW(hwnd, -20) | 0x80000 | 0x20 | 0x80 | 0x08000000)
    previous = None
    changed_at = time.monotonic()
    state = ([], 20 if manifest['schema'] >= 2 else 100, 0)
    cache = None

    def draw(text, y, color, size=13, x=12):
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            canvas.create_text(x+dx, y+dy, anchor='nw', text=text, fill='#101820', font=('Segoe UI', size, 'bold'))
        canvas.create_text(x, y, anchor='nw', text=text, fill=color, font=('Segoe UI', size, 'bold'))

    def tick():
        nonlocal previous, changed_at, state, cache
        if kernel.WaitForSingleObject(process, 0) != 258:
            root.destroy()
            return
        try:
            raw = (session_path / 'session.json').read_text(encoding='utf-8')
            if raw != cache:
                state = snapshot(manifest, json.loads(raw))
                cache = raw
                if previous is not None and len(state[0]) > previous:
                    changed_at = time.monotonic()
                previous = len(state[0])
        except (OSError, ValueError, KeyError):
            pass  # Atomic save replacement may briefly deny a reader on Windows.
        game = user.GetForegroundWindow()
        foreground_pid = w.DWORD()
        user.GetWindowThreadProcessId(game, c.byref(foreground_pid))
        if foreground_pid.value != pid:
            root.withdraw()
        else:
            rect, origin = w.RECT(), w.POINT(0, 0)
            user.GetClientRect(game, c.byref(rect))
            user.ClientToScreen(game, c.byref(origin))
            root.geometry(f'430x235+{origin.x + max(0, rect.right-450)}+{origin.y+20}')
            root.deiconify()
            canvas.delete('all')
            events, cap, repairs = state
            draw(f'FIELD CAP {cap}    REPAIRS {repairs}/25', 8, '#bce8da', 12)
            owned = color_inventory(Counter(item for _, item in events), manifest)
            for index, (label, color, unlocked) in enumerate((
                    ('RED', '#ff7979', RED in owned), ('YELLOW', '#ffe17b', YELLOW in owned),
                    ('BLUE', '#7fbcff', BLUE in owned))):
                x = 14 + index * 138
                canvas.create_oval(x, 41, x+16, 57, fill=color if unlocked else '#27313c',
                                   outline=color if unlocked else '#86939e', width=2)
                if not unlocked:
                    canvas.create_line(x+3, 54, x+13, 44, fill='#86939e', width=2)
                draw(label, 36, color if unlocked else '#a1aab4', 10, x+24)
                draw('UNLOCKED' if unlocked else 'LOCKED', 53, '#c6d5dc' if unlocked else '#a1aab4', 8, x+24)
            draw('RECEIVED' if time.monotonic()-changed_at < 12 else 'RECENT ITEMS', 84, '#9dc9da', 10)
            for index, (source, item) in enumerate(events[-3:][::-1]):
                draw(item.replace('Pikmin: ', ''), 106+index*40, '#ffffff', 12)
                short = source.replace('Bestiary: ', '').replace('Pikmin: ', '').replace('Explore: ', '')
                draw(short[:56], 126+index*40, '#b5c4cc', 9)
        root.after(250, tick)

    try:
        tick()
        root.mainloop()
    finally:
        kernel.CloseHandle(process)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--session-dir', type=Path, required=True)
    parser.add_argument('--pid', type=int, required=True)
    args = parser.parse_args()
    main(args.manifest, args.session_dir, args.pid)
