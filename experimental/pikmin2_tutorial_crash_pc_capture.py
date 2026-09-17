"""Faulting-PC capture for the tutorial P1 post-audio crash (issue 750)."""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import time

SCHEMA = "p2-tutorial-crash-pc-capture-1"
EXE_SHA256 = "f235e032d9d12ef1c7290416e69684bbec484f924691743fbdeb8d93c6ff3a9d"
CRASH_CODE = 0xC0000005
GUARD_SHA256 = "d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474"

SUSPECTS = (
    {"rank": 1, "phase": "first-frame JAI audio pump",
     "files": ["pc_port/audio/jaudio_host.cpp renderJAudioFrame",
               "pc_port/audio/jaudio_host.cpp pumpAudio call site"]},
    {"rank": 2, "phase": "JAI-tail init inside Jac_Start",
     "files": ["src/jaudio/verysimple.c Jac_Start",
               "src/jaudio/verysimple.c Jac_PlayInit et al."]},
    {"rank": 3, "phase": "sink-thread teardown race",
     "files": ["pc_port/audio/jaudio_host.cpp beginSinkOpen",
               "pc_port/audio/jaudio_host.cpp serviceSinkOpen"]},
    {"rank": 4, "phase": "gsys tail",
     "files": ["src/sysDolphin/system.cpp System Initialise tail"]},
)


def sha256_file(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def parse_export_names(path):
    try:
        with open(path, "rb") as stream:
            data = stream.read()
    except OSError:
        return {}
    try:
        if data[0:2] != b"MZ":
            return {}
        e_lfanew = struct.unpack("<I", data[60:64])[0]
        if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
            return {}
        num_sections = struct.unpack("<H", data[e_lfanew + 6:e_lfanew + 8])[0]
        opt_size = struct.unpack("<H", data[e_lfanew + 20:e_lfanew + 22])[0]
        opt = e_lfanew + 24
        magic = struct.unpack("<H", data[opt:opt + 2])[0]
        dd = opt + (112 if magic == 0x20B else 96)
        exp_rva, exp_size = struct.unpack("<II", data[dd:dd + 8])
        if not exp_rva or not exp_size:
            return {}
        sections = []
        base = opt + opt_size
        for i in range(num_sections):
            off = base + i * 40
            vaddr, _vsize, raw_ptr = struct.unpack("<III", data[off + 12:off + 24])
            sections.append((vaddr, raw_ptr))

        def rva_to_offset(rva):
            best = None
            for vaddr, raw_ptr in sections:
                if vaddr <= rva and (best is None or vaddr > best[0]):
                    best = (vaddr, raw_ptr)
            if best is None:
                return None
            return best[1] + (rva - best[0])

        exp_off = rva_to_offset(exp_rva)
        if exp_off is None:
            return {}
        fields = struct.unpack("<11I", data[exp_off:exp_off + 44])
        (_flags, _stamp, _maj, _minor, _name_rva, ordinal_base, _ac,
         name_count, addr_tab_rva, name_ptr_rva, ord_tab_rva) = fields
        if not name_count or not addr_tab_rva:
            return {}
        addr_off = rva_to_offset(addr_tab_rva)
        name_ptr_off = rva_to_offset(name_ptr_rva)
        ord_off = rva_to_offset(ord_tab_rva)
        if addr_off is None or name_ptr_off is None or ord_off is None:
            return {}
        out = {}
        for i in range(name_count):
            nr = name_ptr_off + 4 * i
            name_rva = struct.unpack("<I", data[nr:nr + 4])[0]
            name_off = rva_to_offset(name_rva)
            if name_off is None:
                continue
            end = data.index(b"\x00", name_off)
            name = data[name_off:end].decode("ascii", "replace")
            orr = ord_off + 2 * i
            ordinal = struct.unpack("<H", data[orr:orr + 2])[0]
            arr = addr_off + 4 * (ordinal - ordinal_base)
            func_rva = struct.unpack("<I", data[arr:arr + 4])[0]
            if func_rva:
                out[func_rva] = name
        return out
    except (struct.error, ValueError, IndexError):
        return {}


def nearest_export(exports, rva):
    best = None
    for addr, name in exports.items():
        if addr <= rva and (best is None or addr > best[0]):
            best = (addr, name)
    return best[1] if best else None


def parse_minidump_crash(dump_path):
    try:
        with open(dump_path, "rb") as stream:
            data = stream.read()
    except OSError:
        return None
    if data[0:4] != b"MDMP":
        return None
    stream_count = struct.unpack("<I", data[8:12])[0]
    dir_rva = struct.unpack("<I", data[12:16])[0]
    streams = {}
    for i in range(stream_count):
        off = dir_rva + 12 * i
        stype, _size, rva = struct.unpack("<III", data[off:off + 12])
        streams[stype] = rva
    if 6 not in streams or 4 not in streams:
        return None
    exc = streams[6]
    exc_code, _flags, _rec, addr = struct.unpack("<IIQQ", data[exc + 8:exc + 32])
    nparams = struct.unpack("<I", data[exc + 32:exc + 36])[0]
    info = struct.unpack("<15Q", data[exc + 36:exc + 156])
    mod_base = streams[4]
    count = struct.unpack("<I", data[mod_base:mod_base + 4])[0]
    modules = []
    skipped = 0
    for i in range(count):
        off = mod_base + 4 + 92 * i
        try:
            base = struct.unpack("<Q", data[off:off + 8])[0]
            size = struct.unpack("<I", data[off + 8:off + 12])[0]
            name_rva = struct.unpack("<I", data[off + 20:off + 24])[0]
            length = struct.unpack("<I", data[name_rva:name_rva + 4])[0]
            if length > 2048 or name_rva + 4 + length > len(data):
                skipped += 1
                continue
            path = data[name_rva + 4:name_rva + 4 + length].decode(
                "utf-16-le", "replace").rstrip(chr(0))
        except (struct.error, ValueError, IndexError):
            skipped += 1
            continue
        modules.append({"base": base, "size": size, "path": path})
    if not modules:
        return None
    return {"code": exc_code, "address": addr, "nparams": nparams,
            "info": list(info[:max(0, min(nparams, 15))]),
            "modules": modules, "modules_skipped": skipped}


def collapse_suspects(record):
    if not isinstance(record, dict) or record.get("exit_code") != 3221225477:
        return ("REFUSED", "not a crash capture record")
    fault = record.get("fault") or {}
    module = (fault.get("module") or "").lower().replace("/", "\\").split("\\")[-1]
    if not module or fault.get("address") is None:
        return ("REFUSED", "fault address/module missing")
    resolved = fault.get("resolved_symbol")
    if resolved:
        return ("COLLAPSED-EXE-FUNCTION",
                "fault resolved to %s; recorded for fix owner" % resolved)
    if module != "p2_tutorial_p1_runtime.exe":
        return ("NARROWED-AUDIO-HOST",
                "fault outside the exe image (%s); consistent with audio "
                "pump/sink suspects ranks 1/3" % module)
    symbol = fault.get("nearest_export")
    if symbol:
        return ("NARROWED-EXE-SYMBOL",
                "fault inside the exe near exported %s; recorded for fix owner" % symbol)
    return ("NARROWED-EXE-OFFSET",
            "fault inside the exe at recorded offset; recorded for fix owner")


def set_wer_localdumps(exe_name, dump_dir):
    import winreg
    key_path = ("SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting"
                "\\LocalDumps\\" + exe_name)
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
    winreg.SetValueEx(key, "DumpFolder", 0, winreg.REG_SZ, dump_dir)
    winreg.SetValueEx(key, "DumpCount", 0, winreg.REG_DWORD, 2)
    winreg.SetValueEx(key, "DumpType", 0, winreg.REG_DWORD, 1)
    winreg.CloseKey(key)
    return key_path


def clear_wer_localdumps(exe_name):
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER,
                         "SOFTWARE\\Microsoft\\Windows\\Windows Error Reporting"
                         "\\LocalDumps\\" + exe_name)
        return True
    except OSError:
        return False


def capture(exe_path, run_dir, out_dir, timeout=150):
    import shutil
    os.makedirs(out_dir, exist_ok=True)
    dumps_dir = os.path.join(out_dir, "dumps")
    os.makedirs(dumps_dir, exist_ok=True)
    record = {"schema": SCHEMA, "exe": exe_path,
              "exe_sha256": sha256_file(exe_path),
              "mechanism": "WER LocalDumps harvest on un-debugged run + "
                           "minidump parse (debugger attach perturbs timing)",
              "timeout": timeout}
    env = dict(os.environ)
    env["PATH"] = "C:\\msys64\\mingw64\\bin;" + env.get("PATH", "")
    record["run_start"] = time.time()
    exe_name = os.path.basename(exe_path)
    set_wer_localdumps(exe_name, dumps_dir)
    try:
        log_path = os.path.join(out_dir, "capture-run.log")
        with open(log_path, "wb") as log:
            proc = subprocess.Popen(
                [exe_path, "--experimental-pikmin2-room"], cwd=run_dir,
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            try:
                out, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate()
                record["error"] = "run timed out without crashing"
                record["exit_code"] = None
                return record
            log.write(out or b"")
        record["exit_code"] = proc.returncode
        if proc.returncode not in (3221225477, -1073741515):
            record["error"] = "run did not crash: exit %s" % proc.returncode
            return record
        record["exit_code"] = 3221225477
        time.sleep(3)
        candidates = []
        if os.path.isdir(dumps_dir):
            candidates += [os.path.join(dumps_dir, f) for f in os.listdir(dumps_dir)]
        default_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "CrashDumps")
        if os.path.isdir(default_dir):
            candidates += [os.path.join(default_dir, f) for f in os.listdir(default_dir)]
        dumps = sorted(
            (p for p in candidates
             if p.lower().endswith(".dmp")
             and os.path.basename(p).lower().startswith("p2_tutorial_p1_runtime")
             and os.path.getmtime(p) >= record.get("run_start", 0)),
            key=os.path.getmtime)
        if not dumps:
            record["error"] = "no WER dump harvested"
            return record
        dump_path = os.path.join(dumps_dir, "capture.dmp")
        shutil.copyfile(dumps[-1], dump_path)
        record["dump_source"] = dumps[-1]
        record["dump_sha256"] = sha256_file(dump_path)
        parsed = parse_minidump_crash(dump_path)
        if parsed is None:
            record["error"] = "minidump parse failed: %s" % dump_path
            return record
        if parsed["code"] != CRASH_CODE:
            record["error"] = "dump exception is not crash: %s" % parsed["code"]
            return record
        addr = parsed["address"]
        hit = None
        for mod in parsed["modules"]:
            if mod["base"] <= addr < mod["base"] + mod["size"]:
                hit = mod
                break
        fault = {"code": parsed["code"], "address": addr,
                 "access": parsed["info"][0] if parsed["info"] else None,
                 "target": parsed["info"][1] if len(parsed["info"]) > 1 else None}
        if hit is None:
            fault["module"] = None
            fault["offset"] = None
            fault["nearest_export"] = None
        else:
            fault["module"] = hit["path"]
            fault["offset"] = addr - hit["base"]
            fault["nearest_export"] = nearest_export(
                parse_export_names(hit["path"]), fault["offset"])
        record["fault"] = fault
        record["module_count"] = len(parsed["modules"])
        record["addr2line"] = try_addr2line(exe_path, fault["address"])
        record["modules_skipped"] = parsed.get("modules_skipped", 0)
    finally:
        record["wer_key_removed"] = clear_wer_localdumps(exe_name)
    with open(os.path.join(out_dir, "capture-record.json"), "w", encoding="utf-8") as stream:
        stream.write(json.dumps(record, indent=1, sort_keys=True))
        stream.write("\n")
    return record


def try_addr2line(exe_path, address):
    try:
        proc = subprocess.run(
            ["C:/msys64/mingw64/bin/addr2line.exe", "-e", exe_path,
             "-f", "-C", hex(address)],
            capture_output=True, text=True, timeout=60)
        return (proc.stdout or "").strip()[:400]
    except (OSError, subprocess.SubprocessError):
        return "addr2line unavailable"


def build_packet(record, out_dir):
    verdict, detail = collapse_suspects(record)
    packet = {
        "schema": SCHEMA,
        "kind": "capture",
        "lane": "tutorial-crash-pc-capture",
        "issue": 750,
        "exe_sha256": record.get("exe_sha256"),
        "exit_code": record.get("exit_code"),
        "fault": record.get("fault"),
        "verdict": verdict,
        "detail": detail,
        "suspects": [dict(s) for s in SUSPECTS],
        "downstream": {"lane": "p2-overworld-tutorial-p1-staged-rerun", "issue": 148},
        "gates": "all six UNTESTED",
    }
    with open(os.path.join(out_dir, "packet-pc-capture.json"), "w", encoding="utf-8") as stream:
        stream.write(json.dumps(packet, indent=1, sort_keys=True))
        stream.write("\n")
    return packet, verdict


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tutorial post-audio crash-PC capture")
    parser.add_argument("--root", default="C:/Users/alari/pikmin-randomizer")
    parser.add_argument("--out", default=None)
    parser.add_argument("--timeout", type=int, default=150)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--resolve-symbol", default=None)
    parser.add_argument("--resolve-detail", default="")
    args = parser.parse_args(argv)
    exe_rel = "output/tutorial-p1-native-runtime-build/p2_tutorial_p1_runtime.exe"
    run_rel = ("output/workflow/autofill/planning-shards/overworld-tutorial/"
               "prepared/tutorial-p1-staged-rerun-output/run-tutorial")
    if args.check:
        problems = []
        if not os.path.isfile(os.path.join(args.root, exe_rel)):
            problems.append("exe-missing")
        print("CHECK " + ("PASS" if not problems else "FAIL " + ",".join(problems)))
        return 0 if not problems else 1
    out_dir = args.out or os.path.join(
        args.root, "output/workflow/autofill/planning-shards/overworld-tutorial",
        "prepared/pc-capture-output")
    if args.resolve_symbol:
        rec_path = os.path.join(out_dir, "capture-record.json")
        with open(rec_path, encoding="utf-8") as stream:
            record = json.load(stream)
        record.setdefault("fault", {})["resolved_symbol"] = args.resolve_symbol
        record["resolve_detail"] = args.resolve_detail
        with open(rec_path, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(record, indent=1, sort_keys=True))
            stream.write("\\n")
        packet, verdict = build_packet(record, out_dir)
        print("RESOLVED verdict=%s" % verdict)
        return 0 if verdict == "COLLAPSED-EXE-FUNCTION" else 1
    exe_path = os.path.join(args.root, exe_rel)
    if sha256_file(exe_path) != EXE_SHA256:
        print("REFUSED exe hash mismatch")
        return 1
    record = capture(exe_path, os.path.join(args.root, run_rel), out_dir,
                     timeout=args.timeout)
    packet, verdict = build_packet(record, out_dir)
    print("CAPTURE exit=%s verdict=%s" % (record.get("exit_code"), verdict))
    return 0 if record.get("fault") else 1


if __name__ == "__main__":
    sys.exit(main())