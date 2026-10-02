"""ICE pair launcher for netplay M5a (issue #887).

Runs a host and a joiner as two hidden, private, bounded instances over a
libjuice ICE agent pair, moving the copy-paste connection codes between the
two processes through files -- exactly as a human would copy and paste them:

  host --netplay-ice-host  -> prints offer code -> PIKMIN_NETPLAY_ICE_CODE_OUT
  tool copies the offer to the joiner's --netplay-ice-join @file
  joiner prints answer code -> PIKMIN_NETPLAY_ICE_CODE_OUT
  tool copies ("pastes") the answer to the host's PIKMIN_NETPLAY_ICE_ANSWER_IN
  both connect, then the normal M3 handshake + session runs over ICE.

No external STUN/TURN is used unless asked: the default is
PIKMIN_NETPLAY_STUN=none (host candidates over loopback). With --turn-only
the tool starts the local netplay_turn_server helper (libjuice
juice_server) and both peers use it in relay-only mode.

Modelled on run_pair.py; most launch/compare helpers are reused from it.

M4 lane B2 (issue #885): --token HEX64 reuses a run token, and
--host-campaign-from DIR runs the pair with per-peer campaign dirs (the
run_pair layout out/host/run + out/join/peer/run, so the campaigns are
out/campaign and out/join/campaign) after copying DIR's checkpoints and
card into the host's campaign: with an empty joiner campaign the session
starts with the checkpoint transfer over ICE (bulk channel 0x03).
After both peers exit it compares hash logs, greps for desync/refused lines,
and reports each peer's time to ICE completed plus the selected pairs.
"""

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_pair as rp

DEFAULT_ASSETS = rp.DEFAULT_ASSETS

ICE_SCRUB_KEYS = (
    "PIKMIN_NETPLAY_ICE_HOST",
    "PIKMIN_NETPLAY_ICE_JOIN",
    "PIKMIN_NETPLAY_ICE_CODE_OUT",
    "PIKMIN_NETPLAY_ICE_ANSWER_IN",
    "PIKMIN_NETPLAY_STUN",
    "PIKMIN_NETPLAY_TURN",
    "PIKMIN_NETPLAY_ICE_TURN_ONLY",
    "PIKMIN_NETPLAY_ICE_PORT_BEGIN",
    "PIKMIN_NETPLAY_ICE_PORT_END",
    "PIKMIN_NETPLAY_ICE_TIMEOUT_MS",
    "PIKMIN_NETPLAY_ICE_GATHER_TIMEOUT_MS",
    "PIKMIN_NETPLAY_ICE_BIND",
)


def wait_file(path, timeout, what):
    start = time.time()
    while time.time() - start < timeout:
        try:
            text = path.read_text(errors="replace").strip()
        except OSError:
            text = ""
        if text:
            return text
        time.sleep(0.5)
    raise SystemExit(f"ice_pair: timeout waiting for {what} at {path}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exe", type=Path, required=True, help="netplay game executable")
    p.add_argument("--turn-server-exe", type=Path, default=None,
                   help="netplay_turn_server helper (required with --turn-only)")
    p.add_argument("--ticks", type=int, required=True)
    p.add_argument("--out", type=Path, required=True, help="private output dir (host/ + join/ below)")
    p.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    p.add_argument("--profile", default="foh-day2")
    p.add_argument("--seed-a", type=int, default=101)
    p.add_argument("--seed-b", type=int, default=202)
    p.add_argument("--netplay-seed", type=int, default=1)
    p.add_argument("--delay", type=str, default="2")
    p.add_argument("--latency-ms", type=float, default=0.0)
    p.add_argument("--jitter-ms", type=float, default=0.0)
    p.add_argument("--loss-pct", type=float, default=0.0)
    p.add_argument("--impair-seed", type=int, default=7)
    p.add_argument("--timeout", type=float, default=1200)
    p.add_argument("--code-timeout", type=float, default=180,
                   help="seconds to wait for each connection code file")
    p.add_argument("--handshake-timeout-ms", type=int, default=30000)
    p.add_argument("--ice-timeout-ms", type=int, default=120000)
    p.add_argument("--stun", type=str, default="none",
                   help="PIKMIN_NETPLAY_STUN for both peers (default none: host candidates)")
    p.add_argument("--turn-only", action="store_true",
                   help="relay-only mode against a local juice_server")
    p.add_argument("--turn-port", type=int, default=48020)
    p.add_argument("--turn-bind", type=str, default="127.0.0.2",
                   help="bind address for the local TURN server and its relays. "
                        "M1: a distinct loopback address (not 127.0.0.1) forces "
                        "relay<->relay: per-IP TURN permissions then block the direct path")
    p.add_argument("--turn-user", type=str, default="m5a")
    p.add_argument("--turn-pass", type=str, default="m5a-relay-test")
    p.add_argument("--turn-relay-begin", type=int, default=48030)
    p.add_argument("--turn-relay-end", type=int, default=48049)
    p.add_argument("--ice-port-begin-host", type=int, default=48000)
    p.add_argument("--ice-port-end-host", type=int, default=48009)
    p.add_argument("--ice-port-begin-join", type=int, default=48010)
    p.add_argument("--ice-port-end-join", type=int, default=48019)
    p.add_argument("--env", nargs="*", default=[], metavar="K=V")
    p.add_argument("--env-host", nargs="*", default=[], metavar="K=V")
    p.add_argument("--env-join", nargs="*", default=[], metavar="K=V")
    p.add_argument("--config-overrides", nargs="*", default=[], metavar="key=value")
    p.add_argument("--exe-args", nargs="*", default=[])
    p.add_argument("--throttled", action="store_true")
    p.add_argument("--neg-bad-code", action="store_true",
                   help="negative test only: join with a corrupted offer, expect clean reject")
    p.add_argument("--token", type=str, default=None, metavar="HEX64",
                   help="M4 B2: reuse this run token (SESSION and FINGERPRINT)")
    p.add_argument("--host-campaign-from", type=Path, default=None,
                   help="M4 B2: per-peer campaigns; copy this campaign folder (*.sav + card/) "
                        "into the host's before launch")
    a = p.parse_args(argv)

    for key in ICE_SCRUB_KEYS:
        os.environ.pop(key, None)

    out = a.out.resolve()
    if a.host_campaign_from is not None:
        # B2: per-peer campaign dirs (parent^2 of each run dir differs).
        host_run = out / "host" / "run"
        join_run = out / "join" / "peer" / "run"
    else:
        host_run = out / "host"
        join_run = out / "join"
    host_run.mkdir(parents=True, exist_ok=True)
    join_run.mkdir(parents=True, exist_ok=True)
    if a.host_campaign_from is not None:
        dst = out / "campaign"
        if dst.exists():
            raise SystemExit(f"ice_pair: {dst} exists; use a fresh --out")
        shutil.copytree(str(a.host_campaign_from.resolve()), str(dst))
        print(f"ice_pair: host campaign copied from {a.host_campaign_from} "
              f"({sorted(q.name for q in dst.iterdir())})")

    token = a.token if a.token is not None else uuid.uuid4().hex * 2
    host_boot = host_run / "bootstrap.txt"
    rp.write_bootstrap(host_boot, token, a.profile)
    join_boot = join_run / "bootstrap.txt"
    rp.write_bootstrap(join_boot, token, a.profile)
    rp.link_assets(host_run, a.assets)
    rp.link_assets(join_run, a.assets)
    overrides = rp.parse_kv(a.config_overrides, "config-overrides")
    if overrides:
        for run in (host_run, join_run):
            with open(run / "pikmin_settings.conf", "w") as f:
                for key, value in sorted(overrides.items()):
                    f.write(f"{key} = {value}\n")
    for run in (host_run, join_run):
        (run / "save").mkdir(exist_ok=True)

    host_inputs = out / "host_inputs.pkni"
    join_inputs = out / "join_inputs.pkni"
    rp.gen_inputs(a.ticks + 50, a.seed_a, host_inputs)
    rp.gen_inputs(a.ticks + 50, a.seed_b, join_inputs)

    host_hash = host_run / "hashes.txt"
    join_hash = join_run / "hashes.txt"
    host_log = host_run / "native.log"
    join_log = join_run / "native.log"
    host_offer = out / "host_offer.txt"
    join_answer = out / "join_answer.txt"
    host_answer_in = out / "host_answer_in.txt"
    for f in (host_offer, join_answer, host_answer_in):
        try:
            f.unlink()
        except OSError:
            pass

    # Optional local TURN server (libjuice juice_server helper).
    turn_proc = None
    turn_env_turn = {}
    if a.turn_only:
        if a.turn_server_exe is None:
            raise SystemExit("ice_pair: --turn-only needs --turn-server-exe")
        cmd = [str(a.turn_server_exe.resolve()), "--port", str(a.turn_port),
               "--user", a.turn_user, "--pass", a.turn_pass,
               "--bind", a.turn_bind,
               "--relay-begin", str(a.turn_relay_begin),
               "--relay-end", str(a.turn_relay_end)]
        startup = None
        if sys.platform == "win32":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
        turn_log = open(out / "turn.log", "w")
        turn_proc = subprocess.Popen(cmd, stdout=turn_log, stderr=subprocess.STDOUT,
                                     startupinfo=startup)
        ready = False
        start = time.time()
        while time.time() - start < 30:
            try:
                if "listening" in (out / "turn.log").read_text(errors="replace"):
                    ready = True
                    break
            except OSError:
                pass
            if turn_proc.poll() is not None:
                break
            time.sleep(0.5)
        if not ready:
            rc = turn_proc.poll()
            raise SystemExit(f"ice_pair: TURN server did not start (exit={rc})")
        print(f"ice_pair: TURN server pid {turn_proc.pid} on {a.turn_bind}:{a.turn_port}")
        turn_env_turn = {
            "PIKMIN_NETPLAY_TURN": f"{a.turn_bind}:{a.turn_port}:{a.turn_user}:{a.turn_pass}",
            "PIKMIN_NETPLAY_ICE_TURN_ONLY": "1",
        }

    impair = {
        "PIKMIN_NETPLAY_TEST_LATENCY_MS": str(a.latency_ms),
        "PIKMIN_NETPLAY_TEST_JITTER_MS": str(a.jitter_ms),
        "PIKMIN_NETPLAY_TEST_LOSS_PCT": str(a.loss_pct),
        "PIKMIN_NETPLAY_TEST_SEED": str(a.impair_seed),
    }
    base_extra = {
        "PIKMIN_NETPLAY_SEED": str(a.netplay_seed),
        "PIKMIN_NETPLAY_DELAY": str(a.delay),
        "PIKMIN_NETPLAY_EXIT_AFTER_TICKS": str(a.ticks),
        "PIKMIN_NETPLAY_HANDSHAKE_TIMEOUT_MS": str(a.handshake_timeout_ms),
        "PIKMIN_NETPLAY_ICE_TIMEOUT_MS": str(a.ice_timeout_ms),
        "PIKMIN_NETPLAY_STUN": a.stun,
        "PIKMIN_STATE_HASH_LOG": "",
    }
    base_extra.update(impair)
    base_extra.update(turn_env_turn)
    base_extra.update(rp.parse_kv(a.env, "env"))

    # Negative test: a corrupted offer must be rejected cleanly.
    # m1: corrupt a real, well-formed offer by flipping one base64 char, so
    # the joiner must fail on CRC (not on a synthetic version error).
    if a.neg_bad_code:
        import base64
        import binascii

        def _encode_offer(sdp: str) -> str:
            raw = bytearray()
            raw.append(0x01)
            raw.append(ord("O"))
            raw.append((len(sdp) >> 8) & 0xFF)
            raw.append(len(sdp) & 0xFF)
            raw.extend(sdp.encode())
            raw.extend(binascii.crc32(bytes(raw)).to_bytes(4, "big"))
            return "NPIX1-" + base64.urlsafe_b64encode(bytes(raw)).decode().rstrip("=")

        _sdp = ("a=ice-ufrag:negUfrag1234\r\n"
                "a=ice-pwd:negPasswordPassword1234567890\r\n"
                "a=candidate:1 1 UDP 2113937151 192.168.2.61 50001 typ host\r\n")
        _good = _encode_offer(_sdp)
        _lst = list(_good)
        _pos = 12 if len(_lst) > 12 else len(_lst) - 1
        _lst[_pos] = "B" if _lst[_pos] != "B" else "A"
        bad = "".join(_lst)
        neg_extra = dict(base_extra)
        neg_extra["PIKMIN_STATE_HASH_LOG"] = str(join_hash)
        neg_extra["PIKMIN_NETPLAY_LOCAL_INPUT_FILE"] = str(join_inputs.resolve())
        neg_extra["PIKMIN_NETPLAY_EXIT_AFTER_TICKS"] = "10"
        stop = threading.Event()

        def refresh(run, tok):
            while not stop.is_set():
                try:
                    pending = run / "state.tmp"
                    pending.write_text(f"PIKMIN_STATE 5 {tok} 1 0 127 0 0 END\n")
                    os.replace(pending, run / "state.txt")
                except OSError:
                    pass
                stop.wait(0.1)

        t = threading.Thread(target=refresh, args=(join_run, token))
        t.start()
        try:
            proc, fout = rp.launch(a.exe, join_run, join_boot,
                                   ["--netplay-ice-join", bad] + list(a.exe_args),
                                   neg_extra, join_log, unthrottled=True)
            try:
                rc = proc.wait(timeout=180)
            except subprocess.TimeoutExpired:
                proc.kill()
                rc = 124
            fout.close()
        finally:
            stop.set()
            t.join()
            if proc.poll() is None:
                proc.kill()
        bad_lines = rp.grep(join_log, "bad ICE code")
        print(f"ice_pair negative: join exit={rc} bad-code lines={len(bad_lines)}")
        ok = (rc != 0 and rc != 124 and len(bad_lines) > 0)
        print(f"ice_pair negative: {'PASS' if ok else 'FAIL'}")
        if turn_proc is not None and turn_proc.poll() is None:
            turn_proc.kill()
        return 0 if ok else 1

    host_extra = dict(base_extra)
    host_extra["PIKMIN_STATE_HASH_LOG"] = str(host_hash)
    host_extra["PIKMIN_NETPLAY_LOCAL_INPUT_FILE"] = str(host_inputs.resolve())
    host_extra["PIKMIN_NETPLAY_ICE_CODE_OUT"] = str(host_offer)
    host_extra["PIKMIN_NETPLAY_ICE_ANSWER_IN"] = str(host_answer_in)
    host_extra["PIKMIN_NETPLAY_ICE_PORT_BEGIN"] = str(a.ice_port_begin_host)
    host_extra["PIKMIN_NETPLAY_ICE_PORT_END"] = str(a.ice_port_end_host)
    host_extra.update(rp.parse_kv(a.env_host, "env-host"))
    join_extra = dict(base_extra)
    join_extra["PIKMIN_STATE_HASH_LOG"] = str(join_hash)
    join_extra["PIKMIN_NETPLAY_LOCAL_INPUT_FILE"] = str(join_inputs.resolve())
    join_extra["PIKMIN_NETPLAY_ICE_CODE_OUT"] = str(join_answer)
    join_extra["PIKMIN_NETPLAY_ICE_PORT_BEGIN"] = str(a.ice_port_begin_join)
    join_extra["PIKMIN_NETPLAY_ICE_PORT_END"] = str(a.ice_port_end_join)
    join_extra.update(rp.parse_kv(a.env_join, "env-join"))

    stop = threading.Event()

    def refresh(run, tok):
        while not stop.is_set():
            try:
                pending = run / "state.tmp"
                pending.write_text(f"PIKMIN_STATE 5 {tok} 1 0 127 0 0 END\n")
                os.replace(pending, run / "state.txt")
            except OSError:
                pass
            stop.wait(0.1)

    threads = [threading.Thread(target=refresh, args=(host_run, token)),
               threading.Thread(target=refresh, args=(join_run, token))]
    for t in threads:
        t.start()

    rc_host, rc_join = 1, 1
    host_proc = join_proc = None
    host_out = join_out = None
    start = time.time()
    try:
        host_proc, host_out = rp.launch(a.exe, host_run, host_boot,
                                        ["--netplay-ice-host"] + list(a.exe_args),
                                        host_extra, host_log,
                                        unthrottled=not a.throttled)
        # Human copy-paste, mechanised: wait for the offer, "paste" it to the
        # joiner CLI, wait for the answer, "paste" it to the host file.
        offer = wait_file(host_offer, a.code_timeout, "host offer")
        print(f"ice_pair: offer ({len(offer)} chars) host -> join")
        join_proc, join_out = rp.launch(a.exe, join_run, join_boot,
                                        ["--netplay-ice-join", f"@{host_offer}"]
                                        + list(a.exe_args),
                                        join_extra, join_log,
                                        unthrottled=not a.throttled)
        answer = wait_file(join_answer, a.code_timeout, "join answer")
        print(f"ice_pair: answer ({len(answer)} chars) join -> host")
        host_answer_in.write_text(answer + "\n")
        try:
            rc_host = host_proc.wait(timeout=a.timeout)
        except subprocess.TimeoutExpired:
            host_proc.kill()
            try:
                rc_host = host_proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                rc_host = 124
            print(f"ice_pair: host timeout after {a.timeout}s, killed pid {host_proc.pid}")
        try:
            rc_join = join_proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            join_proc.kill()
            try:
                rc_join = join_proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                rc_join = 124
            print("ice_pair: joiner timeout, killed pid "
                  f"{join_proc.pid if join_proc else '?'}")
    finally:
        stop.set()
        for t in threads:
            t.join()
        for f in (host_out, join_out):
            try:
                if f is not None:
                    f.close()
            except OSError:
                pass
        for proc in (host_proc, join_proc):
            try:
                if proc is not None and proc.poll() is None:
                    proc.kill()
            except OSError:
                pass
        if turn_proc is not None and turn_proc.poll() is None:
            turn_proc.kill()
    secs = time.time() - start

    n_host = rp.count_lines(host_hash)
    n_join = rp.count_lines(join_hash)
    r = subprocess.run([sys.executable, str(rp.CMP), str(host_hash), str(join_hash)],
                       capture_output=True, text=True)
    cmp_rc = r.returncode
    cmp_tail = (r.stdout + r.stderr).strip().splitlines()
    cmp_tail = cmp_tail[-1] if cmp_tail else ""
    des_host = rp.grep(host_log, "desync detected")
    des_join = rp.grep(join_log, "desync detected")
    ref_host = rp.grep(host_log, "handshake refused")
    ref_join = rp.grep(join_log, "handshake refused")
    ice_done_host = rp.grep(host_log, "ice completed in")
    ice_done_join = rp.grep(join_log, "ice completed in")
    ice_sel_host = rp.grep(host_log, "ice selected:")
    ice_sel_join = rp.grep(join_log, "ice selected:")

    print(f"ice_pair: turn_only={a.turn_only} ticks={a.ticks} time={secs:.1f}s")
    print(f"ice_pair: host exit={rc_host} hashes={n_host} log={host_log}")
    print(f"ice_pair: join exit={rc_join} hashes={n_join} log={join_log}")
    print(f"ice_pair: compare exit={cmp_rc}: {cmp_tail}")
    print(f"ice_pair: desync lines host={len(des_host)} join={len(des_join)}")
    print(f"ice_pair: refused lines host={len(ref_host)} join={len(ref_join)}")
    # B2: the checkpoint decision / transfer / resume lines of both peers.
    for who, log in (("host", host_log), ("join", join_log)):
        for needle in ("[netplay] checkpoint", "[netplay] transfer", "CAMPAIGN_RESUMED", "bulk msg complete"):
            for ln in rp.grep(log, needle):
                print(f"ice_pair: {who} {ln.strip()}")
        print(f"ice_pair: {who} START_STAGE={len(rp.grep(log, 'START_STAGE'))} "
              f"randomizer_lines={len(rp.grep(log, '[Pikmin Randomizer]'))}")
    print(f"ice_pair: distinct tuples host={rp.hash_tuples(host_hash)} join={rp.hash_tuples(join_hash)}")
    for ln in ice_done_host:
        print(f"ice_pair: host {ln.strip()}")
    for ln in ice_done_join:
        print(f"ice_pair: join {ln.strip()}")
    for ln in ice_sel_host:
        print(f"ice_pair: host {ln.strip()}")
    for ln in ice_sel_join:
        print(f"ice_pair: join {ln.strip()}")

    ok = True
    if rc_host != 0 or rc_join != 0:
        ok = False
    if cmp_rc != 0:
        ok = False
    if des_host or des_join:
        ok = False
    if n_host != a.ticks or n_join != a.ticks:
        print(f"ice_pair: FAIL: hash lines {n_host}/{n_join} != requested {a.ticks}")
        ok = False
    if not ice_done_host or not ice_done_join:
        print("ice_pair: FAIL: missing ice completed lines")
        ok = False
    if a.turn_only:
        # M1: require "typ relay" inside the local [...] bracket of BOTH
        # peers. Checking the whole line is not enough: the host can select
        # local srflx + remote relay while the joiner learns the host's
        # direct address as prflx.
        def _local_is_relay(line: str) -> bool:
            i = line.find("local [")
            if i < 0:
                return False
            j = line.find("]", i)
            seg = line[i:j] if j >= 0 else line[i:]
            return "typ relay" in seg

        relay_host = [ln for ln in ice_sel_host if _local_is_relay(ln)]
        relay_join = [ln for ln in ice_sel_join if _local_is_relay(ln)]
        print(f"ice_pair: relay-local selected lines host={len(relay_host)} join={len(relay_join)}")
        if not relay_host or not relay_join:
            print("ice_pair: FAIL: TURN-only pair did not select a relay candidate LOCALLY on both peers")
            ok = False
    print(f"ice_pair: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
