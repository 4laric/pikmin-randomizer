"""Refresh the public engine snapshot from a local native worktree/checkout.

Defaults to the shared ``native/`` checkout, but ``--source`` may point at any
native worktree (e.g. a private integration line) so exporting never has to
wait for the shared checkout to be clean. Modified tracked files are copied
from the worktree as-is; the recorded dirty baseline is expected.
"""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]

# Exact non-desktop resources audited at native 3a19ad89 (#1171).
# A new binary in any of these directories must still fail preflight.
EXCLUDED_BINARY_RESOURCES = frozenset({
    'android/app/src/main/res/mipmap-hdpi/ic_launcher.png',
    'android/app/src/main/res/mipmap-mdpi/ic_launcher.png',
    'android/app/src/main/res/mipmap-xhdpi/ic_launcher.png',
    'android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png',
    'android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png',
    'android/gradle/wrapper/gradle-wrapper.jar',
    'pc_port/touch/assets/art/back.png',
    'pc_port/touch/assets/art/bubble.png',
    'pc_port/touch/assets/art/bubble_pressed.png',
    'pc_port/touch/assets/art/camera_angle.png',
    'pc_port/touch/assets/art/camera_center.png',
    'pc_port/touch/assets/art/charge.png',
    'pc_port/touch/assets/art/coop_louie.png',
    'pc_port/touch/assets/art/coop_olimar.png',
    'pc_port/touch/assets/art/coop_portrait_louie.png',
    'pc_port/touch/assets/art/disband.png',
    'pc_port/touch/assets/art/layout.png',
    'pc_port/touch/assets/art/lock_on.png',
    'pc_port/touch/assets/art/map.png',
    'pc_port/touch/assets/art/pause.png',
    'pc_port/touch/assets/art/photo_mode.png',
    'pc_port/touch/assets/art/pinch.png',
    'pc_port/touch/assets/art/settings.png',
    'pc_port/touch/assets/art/stick_knob.png',
    'pc_port/touch/assets/art/stick_ring.png',
    'pc_port/touch/assets/art/swipe_l.png',
    'pc_port/touch/assets/art/swipe_r.png',
    'pc_port/touch/assets/art/throw.png',
    'pc_port/touch/assets/art/whistle.png',
    'third_party/SDL2-android/Xcode-iOS/Demos/Default.png',
    'third_party/SDL2-android/Xcode-iOS/Demos/Icon.png',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/bitmapfont/kromasky_16x16.bmp',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/drums/ds_brush_snare.wav',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/drums/ds_china.wav',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/drums/ds_kick_big_amb.wav',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/drums/ds_loose_skin_mute.wav',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/icon.bmp',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/ship.bmp',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/space.bmp',
    'third_party/SDL2-android/Xcode-iOS/Demos/data/stroke.bmp',
    'third_party/SDL2-android/android-project-ant/res/drawable-hdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project-ant/res/drawable-mdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project-ant/res/drawable-xhdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project-ant/res/drawable-xxhdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project/app/src/main/res/mipmap-hdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project/app/src/main/res/mipmap-mdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project/app/src/main/res/mipmap-xhdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project/app/src/main/res/mipmap-xxhdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png',
    'third_party/SDL2-android/android-project/gradle/wrapper/gradle-wrapper.jar',
    'third_party/SDL2-android/src/hidapi/testgui/TestGUI.app.in/Contents/Resources/English.lproj/InfoPlist.strings',
    'third_party/SDL2-android/src/hidapi/testgui/TestGUI.app.in/Contents/Resources/Signal11.icns',
    'third_party/SDL2-android/src/main/winrt/SDL2-WinRTResource_BlankCursor.cur',
})
# Existing desktop packaging inputs, including the Windows resource-script icon.
COPIED_BINARY_RESOURCES = frozenset({
    'packaging/icon/nectar.ico',
    'packaging/icon/open_nectar.png',
})


def plan_export(source):
    """Validate and retain working-tree bytes without writing the target."""
    source = Path(source)
    names = subprocess.check_output(['git', '-C', str(source), 'ls-files', '-z']).decode().split('\0')
    files, skipped = [], []
    for name in filter(None, names):
        path = Path(name)
        if path.parts[0] in {'.github', '.vscode'} or path.suffix.lower() in {'.exe', '.gz'}:
            continue
        if name in EXCLUDED_BINARY_RESOURCES:
            skipped.append(name)
            continue
        data = (source / path).read_bytes()
        if b'\0' in data and name not in COPIED_BINARY_RESOURCES:
            raise ValueError(f'Unexpected binary source: {name}')
        files.append((path, data))
    return files, skipped


def export(source=None, target=None):
    source = Path(source) if source is not None else ROOT / 'native'
    target = Path(target) if target is not None else ROOT / 'engine'
    # Complete input preflight before the first mkdir or write. Use the validated
    # bytes so a later source edit cannot bypass validation or change the snapshot.
    files, skipped = plan_export(source)
    for path, data in files:
        out = target / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    print(f'Exported {len(files)} tracked files from {source} '
          f'({len(skipped)} known non-desktop binary resources skipped; '
          'no history or local untracked files).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'native',
                        help='native worktree/checkout to export (default: native/)')
    parser.add_argument('--target', type=Path, default=ROOT / 'engine',
                        help='engine snapshot destination (default: engine/)')
    args = parser.parse_args()
    export(args.source, args.target)
