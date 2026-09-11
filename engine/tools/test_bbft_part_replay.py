"""Opt-in normal-app replay smoke. Uses private state, cwd, saves and process."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import runpy
import subprocess
import time

async def main(args):
    names = list(runpy.run_path(args.catalog)["PART_IDS"])
    assert len(names) == 28
    work = Path(args.work).resolve()
    assert (work / "assets").is_dir(), "Supply an isolated cwd with the existing read-only assets junction"
    packets, writers = [], []
    state = {"t": "state", "ready": 1, "region_unlocks": 1,
             "pikmin_skip_tutorial": 1, "pikmin_progression": 1,
             "items": {"Pikmin Access": 1}, "locks": {},
             "checked": [name for name in names if name != "Pikmin: Eternal Fuel Dynamo"]}
    async def client(reader, writer):
        writers.append(writer)
        assert json.loads(await reader.readline())["game"] == "pikmin"
        for message in (state, {"t": "warp_in"}):
            writer.write((json.dumps(message) + "\n").encode())
        await writer.drain()
        try:
            while line := await reader.readline():
                packets.append(json.loads(line))
        except ConnectionError:
            pass
    server = await asyncio.start_server(client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    process = None
    output = work / "replay-smoke.log"
    try:
        with output.open("w") as log:
            env = dict(os.environ, PIKMIN_BBFT_TEST_BACKGROUND="1", SDL_AUDIODRIVER="dummy")
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
            process = subprocess.Popen([str(Path(args.exe).resolve()), "--bbft-port", str(port)],
                cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT, startupinfo=startup)
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                assert process.poll() is None, f"Native exit {process.returncode}; {output}"
                text = output.read_text(errors="replace")
                if "PIKMIN_WORLD_RENDERED" in text and "PIKMIN_FOH_READY" in text:
                    break
                await asyncio.sleep(.2)
            else:
                raise AssertionError(f"Native boot not ready; {output}")
            # Restore the physical Dynamo after the level has spawned, then
            # re-deliver exactly the same authoritative snapshot. It must not
            # double count native parts or emit any AP checks/items.
            state["checked"] = names
            for writer in writers:
                writer.write((json.dumps(state) + "\n").encode())
                writer.write((json.dumps(state) + "\n").encode())
                await writer.drain()
            await asyncio.sleep(3)
            assert process.poll() is None
            text = output.read_text(errors="replace")
            for name in names:
                assert text.count("PIKMIN_PART_REPLAY " + name + " total=") == 1, name
            assert "total=29 " in text, "28 replayed parts plus starting Main Engine"
            assert "PIKMIN_PART_REPLAY_PELLET_REMOVED" in text, "Late snapshot left physical Dynamo behind"
            assert not any(packet.get("t") == "check" for packet in packets), packets
            print("PASS: native boot/render; 28 parts restored once, total 29; duplicate snapshot emits no checks")
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            await asyncio.to_thread(process.wait, 10)
        for writer in writers:
            writer.close()
        server.close()
        await server.wait_closed()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("exe", "work", "catalog"):
        parser.add_argument("--" + name, required=True)
    asyncio.run(main(parser.parse_args()))
