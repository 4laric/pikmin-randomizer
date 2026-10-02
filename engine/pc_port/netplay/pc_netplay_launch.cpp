// Netplay launch lane (issue #887): the one-command launcher's pre-init
// stage. See pc_netplay_launch.h for the order of events and the contract.

#include "netplay/pc_netplay_launch.h"

#include "netplay/pc_netplay_continue.h"
#include "netplay/pc_netplay_ice.h"
#include "netplay/pc_netplay_input_sel.h"
#include "netplay/pc_netplay_launch_util.h"
#include "netplay/pc_netplay_transfer.h"
#include "settings/pc_settings.h"
#include "pc_coop.h"

#include <SDL2/SDL.h>

#include <algorithm>
#include <cctype>
#include <cerrno>
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <random>
#include <string>
#include <vector>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <winioctl.h>
#include <io.h>
#else
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#endif

// Netplay M4 lane B2: pins the settings file (pc_settings.cpp, netplay builds).
void pc_settings_pin_config_path(const char* absolutePath);

namespace {

using namespace pc_netplay_launch_util;

PcNetplayLaunch sSetup;
long long sRunStartUtc = 0; // M5c lane C: this run's start (launch.txt started_utc)
// Rewritten argv (original + --randomizer-seed <path>), kept alive for the
// whole process because every later consumer holds the pointer.
std::vector<std::string> sArgStore;
std::vector<char*> sArgv;
// M4 lane B2: the host's P2 sidecar source folder (its --bootstrap folder).
std::string sP2SidecarDir;

[[noreturn]] void die(const char* fmt, ...)
{
	char buf[2048];
	va_list ap;
	va_start(ap, fmt);
	vsnprintf(buf, sizeof(buf), fmt, ap);
	va_end(ap);
	printf("[netplay] launch: %s\n", buf);
	fflush(stdout);
	std::exit(2);
}

const char* getenv_nonempty(const char* name)
{
	const char* v = std::getenv(name);
	return (v != nullptr && *v != '\0') ? v : nullptr;
}

bool argv_present(int argc, char** argv, const char* flag)
{
	for (int i = 1; i < argc; ++i) {
		if (argv[i] != nullptr && std::strcmp(argv[i], flag) == 0) return true;
	}
	return false;
}

// Value after `flag`; dies when the flag is the last argument.
const char* argv_value(int argc, char** argv, const char* flag)
{
	for (int i = 1; i < argc; ++i) {
		if (argv[i] == nullptr || std::strcmp(argv[i], flag) != 0) continue;
		if (i + 1 >= argc || argv[i + 1] == nullptr) die("%s needs a value", flag);
		return argv[i + 1];
	}
	return nullptr;
}

void set_env(const char* name, const std::string& value)
{
#ifdef _WIN32
	_putenv_s(name, value.c_str());
#else
	setenv(name, value.c_str(), 1);
#endif
}

unsigned current_pid()
{
#ifdef _WIN32
	return (unsigned)GetCurrentProcessId();
#else
	return (unsigned)getpid();
#endif
}

// 64 lowercase hex chars. random_device mixed with the clock and the pid:
// a per-run identity token, not a secret.
std::string fresh_token()
{
	std::random_device rd;
	const uint64_t clock = (uint64_t)std::chrono::high_resolution_clock::now().time_since_epoch().count();
	std::seed_seq seq{ rd(), rd(), rd(), rd(), (unsigned)(clock & 0xFFFFFFFFu), (unsigned)(clock >> 32),
		               current_pid() };
	std::mt19937_64 gen(seq);
	std::string tok;
	char cell[17];
	for (int i = 0; i < 4; ++i) {
		snprintf(cell, sizeof(cell), "%016llx", (unsigned long long)gen());
		tok += cell;
	}
	return tok;
}

std::string forward_slashes(std::string p)
{
	for (char& c : p) {
		if (c == '\\') c = '/';
	}
	return p;
}

std::string exe_dir()
{
#ifdef _WIN32
	char path[4096];
	DWORD n = GetModuleFileNameA(nullptr, path, sizeof(path));
	if (n == 0 || n >= sizeof(path)) return std::string();
	std::string p = forward_slashes(std::string(path, n));
#else
	char path[4096];
	ssize_t n = readlink("/proc/self/exe", path, sizeof(path) - 1);
	if (n <= 0) return std::string();
	std::string p(path, (size_t)n);
#endif
	const size_t slash = p.find_last_of('/');
	return slash == std::string::npos ? std::string() : p.substr(0, slash);
}

// Creates one directory. Returns 1 created, 0 already exists, -1 failed.
int make_dir(const std::string& path)
{
#ifdef _WIN32
	if (CreateDirectoryA(path.c_str(), nullptr)) return 1;
	return GetLastError() == ERROR_ALREADY_EXISTS ? 0 : -1;
#else
	if (mkdir(path.c_str(), 0755) == 0) return 1;
	return errno == EEXIST ? 0 : -1;
#endif
}

bool make_dirs(const std::string& path)
{
	for (size_t i = 1; i <= path.size(); ++i) {
		if (i == path.size() || path[i] == '/') {
			const std::string part = path.substr(0, i);
			if (part.size() == 2 && part[1] == ':') continue; // drive root
			if (make_dir(part) < 0) return false;
		}
	}
	return true;
}

bool write_file(const std::string& path, const std::string& data)
{
	FILE* f = fopen(path.c_str(), "wb");
	if (f == nullptr) return false;
	bool ok = data.empty() || fwrite(data.data(), 1, data.size(), f) == data.size();
	ok      = (fclose(f) == 0) && ok;
	return ok;
}

// M5c lane C fix round 1: a write that is on the disk when the call returns
// (fflush, then _commit / fsync), for the campaign record and the files a
// --continue copies. A crash can zero or cut a file that was only in the
// cache (this machine did so in a bugcheck), so the record's `carried` line
// is written only after every copy is on the disk, and is itself committed.
bool write_file_durable(const std::string& path, const std::string& data, const char* mode = "wb")
{
	FILE* f = fopen(path.c_str(), mode);
	if (f == nullptr) return false;
	bool ok = data.empty() || fwrite(data.data(), 1, data.size(), f) == data.size();
	ok      = fflush(f) == 0 && ok;
#ifdef _WIN32
	ok = _commit(_fileno(f)) == 0 && ok;
#else
	ok = fsync(fileno(f)) == 0 && ok;
#endif
	ok = (fclose(f) == 0) && ok;
	return ok;
}

// Reads at most cap + 1 bytes, so an oversized file is refused without
// being read in full (m1). Returns -1 when the file cannot be opened.
long read_file_bounded(const std::string& path, size_t cap, std::string* out)
{
	FILE* f = fopen(path.c_str(), "rb");
	if (f == nullptr) return -1;
	out->clear();
	char chunk[8192];
	while (out->size() <= cap) {
		const size_t want = std::min(sizeof(chunk), cap + 1 - out->size());
		const size_t n    = fread(chunk, 1, want, f);
		if (n > 0) out->append(chunk, n);
		if (n < want) break;
	}
	fclose(f);
	return (long)out->size();
}

bool dir_writable(const std::string& dir)
{
	const std::string probe = dir + "/.nectar-write-test";
	if (!write_file(probe, "1")) return false;
	remove(probe.c_str());
	return true;
}

// ---- M4 lane B2 (issue #885): P2 play directory helpers ----
bool is_dir(const std::string& path)
{
#ifdef _WIN32
	const DWORD a = GetFileAttributesA(path.c_str());
	return a != INVALID_FILE_ATTRIBUTES && (a & FILE_ATTRIBUTE_DIRECTORY) != 0;
#else
	struct stat st;
	return stat(path.c_str(), &st) == 0 && S_ISDIR(st.st_mode);
#endif
}

std::string absolute_path(const std::string& path)
{
#ifdef _WIN32
	char buf[4096];
	const DWORD n = GetFullPathNameA(path.c_str(), sizeof(buf), buf, nullptr);
	if (n == 0 || n >= sizeof(buf)) return std::string();
	std::string p = forward_slashes(std::string(buf, n));
#else
	char buf[4096];
	if (realpath(path.c_str(), buf) == nullptr) return std::string();
	std::string p(buf);
#endif
	while (p.size() > 3 && p.back() == '/') p.pop_back();
	return p;
}

std::string current_dir()
{
#ifdef _WIN32
	char buf[4096];
	const DWORD n = GetCurrentDirectoryA(sizeof(buf), buf);
	if (n == 0 || n >= sizeof(buf)) return std::string();
	return forward_slashes(std::string(buf, n));
#else
	char buf[4096];
	return getcwd(buf, sizeof(buf)) != nullptr ? std::string(buf) : std::string();
#endif
}

bool change_dir(const std::string& path)
{
#ifdef _WIN32
	return SetCurrentDirectoryA(path.c_str()) != 0;
#else
	return chdir(path.c_str()) == 0;
#endif
}

// Directory junction link -> target (Windows: an NTFS mount point, which
// needs no privilege; elsewhere a directory symlink). The junction lives in
// this run's private play/ folder; nothing ever writes through it (the game
// only reads assets/), and it is removed with the run folder by rmdir, which
// never follows it.
bool make_junction(const std::string& link, const std::string& target, std::string* err)
{
#ifdef _WIN32
	auto widen = [](const std::string& s) {
		const int n = MultiByteToWideChar(CP_ACP, 0, s.c_str(), (int)s.size(), nullptr, 0);
		std::wstring w((size_t)(n > 0 ? n : 0), L'\0');
		if (n > 0) MultiByteToWideChar(CP_ACP, 0, s.c_str(), (int)s.size(), &w[0], n);
		return w;
	};
	std::wstring wtarget = widen(target);
	wchar_t full[4096];
	const DWORD fn = GetFullPathNameW(wtarget.c_str(), 4096, full, nullptr);
	if (fn == 0 || fn >= 4096) {
		*err = "cannot resolve " + target;
		return false;
	}
	std::wstring print(full, fn);
	while (print.size() > 3 && (print.back() == L'\\' || print.back() == L'/')) print.pop_back();
	const std::wstring subst = std::wstring(1, L'\\') + L"??" + std::wstring(1, L'\\') + print;
	const std::wstring wlink = widen(link);
	if (!CreateDirectoryW(wlink.c_str(), nullptr)) {
		*err = "cannot create " + link;
		return false;
	}
	HANDLE h = CreateFileW(wlink.c_str(), GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
	                       FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_BACKUP_SEMANTICS, nullptr);
	if (h == INVALID_HANDLE_VALUE) {
		RemoveDirectoryW(wlink.c_str());
		*err = "cannot open " + link;
		return false;
	}
	// REPARSE_DATA_BUFFER, MountPointReparseBuffer variant: an 8-byte header
	// (tag, data length, reserved), then four USHORT offsets/lengths and the
	// substitute and print names, each NUL-terminated.
	const size_t substBytes = subst.size() * sizeof(wchar_t);
	const size_t printBytes = print.size() * sizeof(wchar_t);
	const size_t dataLen    = 8 + substBytes + sizeof(wchar_t) + printBytes + sizeof(wchar_t);
	std::vector<uint8_t> buf(8 + dataLen, 0);
	auto put16 = [&](size_t at, size_t v) {
		buf[at]     = (uint8_t)(v & 0xFF);
		buf[at + 1] = (uint8_t)((v >> 8) & 0xFF);
	};
	const DWORD tag = IO_REPARSE_TAG_MOUNT_POINT;
	memcpy(buf.data(), &tag, 4);
	put16(4, dataLen);
	put16(8, 0);                                  // SubstituteNameOffset
	put16(10, substBytes);                        // SubstituteNameLength
	put16(12, substBytes + sizeof(wchar_t));      // PrintNameOffset
	put16(14, printBytes);                        // PrintNameLength
	memcpy(buf.data() + 16, subst.data(), substBytes);
	memcpy(buf.data() + 16 + substBytes + sizeof(wchar_t), print.data(), printBytes);
	DWORD ret = 0;
	const BOOL ok = DeviceIoControl(h, FSCTL_SET_REPARSE_POINT, buf.data(), (DWORD)buf.size(), nullptr, 0, &ret, nullptr);
	CloseHandle(h);
	if (!ok) {
		RemoveDirectoryW(wlink.c_str());
		*err = "cannot make the junction " + link + " (error " + std::to_string((unsigned long)GetLastError()) + ")";
		return false;
	}
	return true;
#else
	if (symlink(target.c_str(), link.c_str()) != 0) {
		*err = "cannot link " + link;
		return false;
	}
	return true;
#endif
}

// Host: copies the P2 sidecar set (regular files directly in `from` whose
// names match ^(p2|sarai)-[a-z0-9-]+\.txt$) into `to`. Returns the count.
bool copy_sidecars(const std::string& from, const std::string& to, size_t* count, size_t* bytes, std::string* err)
{
	*count = 0;
	*bytes = 0;
	std::vector<std::string> names;
#ifdef _WIN32
	WIN32_FIND_DATAA fd;
	HANDLE h = FindFirstFileA((from + "/*").c_str(), &fd);
	if (h == INVALID_HANDLE_VALUE) {
		*err = "cannot list " + from;
		return false;
	}
	do {
		if ((fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) == 0 && pc_netplay_xfer::sidecar_name_ok(fd.cFileName))
			names.push_back(fd.cFileName);
	} while (FindNextFileA(h, &fd));
	FindClose(h);
#else
	*err = "P2 sidecar copy needs Windows here";
	return false;
#endif
	std::sort(names.begin(), names.end());
	for (const std::string& n : names) {
		std::string data;
		const long got = read_file_bounded(from + "/" + n, pc_netplay_xfer::kMaxBundleFileBytes, &data);
		if (got < 0 || (size_t)got > pc_netplay_xfer::kMaxBundleFileBytes) {
			*err = "sidecar " + n + " is unreadable or too large";
			return false;
		}
		if (!write_file(to + "/" + n, data)) {
			*err = "cannot write " + to + "/" + n;
			return false;
		}
		++*count;
		*bytes += data.size();
	}
	if (*bytes > pc_netplay_xfer::kMaxSidecarTotal) {
		*err = "the sidecar set is larger than 2 MiB";
		return false;
	}
	return true;
}

// The run_pair.py profile (foh-day2, identity placements, 25-repair goal,
// red start, 10 Flarlic), with a fresh FINGERPRINT per session so every
// launcher session is its own campaign. Its SESSION line is a placeholder:
// like any --bootstrap file it is re-stamped with the run token after.
std::string default_bootstrap()
{
	const std::string fingerprint = fresh_token();
	return "PIKMIN_RANDOMIZER 5\nSESSION " + fresh_token() + "\nFINGERPRINT " + fingerprint
	     + "\nPROFILE foh-day2\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\nGOAL 25\n"
	       "DAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n";
}

#ifdef _WIN32
// @clipboard before SDL exists: the Win32 clipboard, CF_UNICODETEXT, as
// UTF-8 (codes are ASCII; anything else fails the decode with a reason).
bool read_clipboard(std::string* out, std::string* err)
{
	bool opened = false;
	for (int attempt = 0; attempt < 10 && !opened; ++attempt) {
		opened = OpenClipboard(nullptr) != 0;
		if (!opened) Sleep(50); // another process may hold it briefly
	}
	if (!opened) {
		*err = "cannot open the clipboard";
		return false;
	}
	bool ok = false;
	HANDLE h = GetClipboardData(CF_UNICODETEXT);
	if (h != nullptr) {
		const wchar_t* w = static_cast<const wchar_t*>(GlobalLock(h));
		if (w != nullptr) {
			const size_t cap = pc_netplay_ice::kMaxOfferV2Chars + 4096;
			size_t wlen      = 0;
			while (w[wlen] != L'\0' && wlen <= cap) ++wlen;
			if (wlen > cap) {
				*err = "clipboard text is too large to be a connection code";
			} else {
				const int n = WideCharToMultiByte(CP_UTF8, 0, w, (int)wlen, nullptr, 0, nullptr, nullptr);
				std::string s((size_t)(n > 0 ? n : 0), '\0');
				if (n > 0) WideCharToMultiByte(CP_UTF8, 0, w, (int)wlen, &s[0], n, nullptr, nullptr);
				*out = s;
				ok   = true;
			}
			GlobalUnlock(h);
		}
	} else {
		*err = "the clipboard holds no text";
	}
	CloseClipboard();
	return ok;
}
#endif

std::string trim(const std::string& s)
{
	size_t b = 0, e = s.size();
	while (b < e && (s[b] == ' ' || s[b] == '\t' || s[b] == '\r' || s[b] == '\n')) ++b;
	while (e > b && (s[e - 1] == ' ' || s[e - 1] == '\t' || s[e - 1] == '\r' || s[e - 1] == '\n')) --e;
	return s.substr(b, e - b);
}

// Offer text from a literal, @file, or @clipboard. Read exactly once (m12:
// the adopted bundle and the SDP always come from the same text).
std::string read_offer_arg(const std::string& arg)
{
	std::string code, err;
	if (trim(arg) == "@clipboard") {
#ifdef _WIN32
		if (!read_clipboard(&code, &err)) die("cannot read the offer code from the clipboard: %s", err.c_str());
#else
		die("@clipboard needs Windows here; pass the code itself or @file");
#endif
		code = trim(code);
		if (code.empty()) die("the clipboard is empty; copy the host's offer code first");
		return code;
	}
	if (!pc_netplay_ice::ice_read_code_arg(arg, &code, &err)) die("cannot read the offer code: %s", err.c_str());
	return code;
}

void parse_captains(const std::string& block)
{
	auto value = [&](const char* key, int* out) {
		const std::string k = std::string(";") + key + "=";
		const size_t at     = block.find(k);
		if (at == std::string::npos) return false;
		char* end    = nullptr;
		const char* v = block.c_str() + at + k.size();
		long n        = strtol(v, &end, 10);
		if (end == v || *end != ';') return false;
		n %= PC_CAPTAIN_COUNT;
		if (n < 0) n += PC_CAPTAIN_COUNT;
		*out = (int)n;
		return true;
	};
	int p1 = 0, p2 = 1;
	if (value("captainP1", &p1) && value("captainP2", &p2)) {
		sSetup.haveCaptains = true;
		sSetup.captainP1    = p1;
		sSetup.captainP2    = p2;
	}
}

// M4 lane B2: where the P2 overlay comes from. Runs before any run folder
// exists, so every refusal leaves nothing behind.
void resolve_p2_overlay(int argc, char** argv, const char* bootCli)
{
	const char* assetsArg = argv_value(argc, argv, "--netplay-p2-assets");
	if (sSetup.isHost && assetsArg != nullptr)
		die("--netplay-p2-assets is joiner-only: the host's P2 overlay is <its --bootstrap folder>/assets");
	if (!sSetup.p2) {
		if (assetsArg != nullptr)
			die("--netplay-p2-assets is only for P2 seeds; %s has no ENEMY_P2", sSetup.isHost ? "--bootstrap" : "this offer");
		return;
	}
	if (sSetup.isHost) {
		const std::string boot = absolute_path(bootCli != nullptr ? bootCli : "");
		const size_t slash = boot.find_last_of('/');
		const std::string dir = slash == std::string::npos ? std::string() : boot.substr(0, slash);
		sSetup.p2AssetsDir = dir.empty() ? std::string() : dir + "/assets";
		if (sSetup.p2AssetsDir.empty() || !is_dir(sSetup.p2AssetsDir))
			die("this seed uses P2 enemies (ENEMY_P2), but its folder has no assets/ overlay (%s); host from the "
			    "seed's own folder",
			    sSetup.p2AssetsDir.c_str());
		sP2SidecarDir = dir;
	} else {
		if (assetsArg == nullptr)
			die("this offer is a P2 seed (ENEMY_P2): pass --netplay-p2-assets <folder> with your own copy of the "
			    "seed's P2 assets overlay (the one the host plays from); it is checked, never sent");
		sSetup.p2AssetsDir = absolute_path(assetsArg);
		if (sSetup.p2AssetsDir.empty() || !is_dir(sSetup.p2AssetsDir))
			die("--netplay-p2-assets %s is not a folder", assetsArg);
	}
}

// M4 lane B2: the P2 play directory, made the working directory here (before
// pc_settings_init and every cwd-relative asset or sidecar read).
void setup_play_dir()
{
	const std::string original = current_dir();
	if (original.empty()) die("cannot read the working directory");
	sSetup.settingsPath = original + "/pikmin_settings.conf";
	sSetup.playDir      = play_dir(sSetup.runDir);
	if (!make_dirs(sSetup.playDir)) die("cannot create %s", sSetup.playDir.c_str());
	std::string err;
	if (!make_junction(sSetup.playDir + "/assets", sSetup.p2AssetsDir, &err)) die("%s", err.c_str());
	size_t copied = 0, bytes = 0;
	if (sSetup.isHost && !copy_sidecars(sP2SidecarDir, sSetup.playDir, &copied, &bytes, &err))
		die("cannot stage the P2 sidecars: %s", err.c_str());
	// Paths the session opens later stay the ones the player gave.
	if (!sSetup.codeOut.empty()) sSetup.codeOut = absolute_path(sSetup.codeOut);
	if (!sSetup.answerIn.empty()) sSetup.answerIn = absolute_path(sSetup.answerIn);
	pc_settings_pin_config_path(sSetup.settingsPath.c_str());
	if (!change_dir(sSetup.playDir)) die("cannot enter %s", sSetup.playDir.c_str());
	printf("[netplay] launch: P2 seed: working directory %s (assets -> %s)\n", sSetup.playDir.c_str(),
	       sSetup.p2AssetsDir.c_str());
	if (sSetup.isHost)
		printf("[netplay] launch: P2 sidecars: %llu files (%llu B) copied from %s\n", (unsigned long long)copied,
		       (unsigned long long)bytes, sP2SidecarDir.c_str());
	else
		printf("[netplay] launch: P2 sidecars arrive from the host before the session starts\n");
	printf("[netplay] launch: settings file pinned to %s\n", sSetup.settingsPath.c_str());
	fflush(stdout);
}

// ---- M5c lane C (issue #887): --continue, recovery v1 ----
// `--netplay-host-ice --continue [run folder]` starts a new session (new run
// folder, new peer token, as always) from the newest day-end save both games
// agreed on. The picked checkpoint, the card and the campaign's other files
// are COPIED into the new run's campaign dir; the old run folder is only
// read, never changed, and nothing is ever deleted. The bootstrap is the old
// run's (its FINGERPRINT is what the checkpoint carries), re-stamped with the
// new token; the netplay seed is the old run's too. The joiner needs no extra
// step: B2's handshake sends it the host's checkpoint and card.
namespace fs = std::filesystem;
using namespace pc_netplay_continue;

bool read_path_bounded(const fs::path& p, size_t cap, std::string* out)
{
	const long n = read_file_bounded(p.string(), cap, out);
	return n >= 0 && (size_t)n <= cap;
}

// One run folder, as --continue sees it.
struct ContinueCandidate {
	std::string dir;          // absolute, '/'-separated
	bool named = false;       // the folder name parsed as a launcher run
	RunName name;
	bool hostRole = false;    // launch.txt role (else the name's)
	std::string launchText;   // <run>/launch.txt
	std::string bootText;     // the run's stamped bootstrap
	std::string fingerprint;
	fs::path campaign;        // <run>/session/campaign
	unsigned long long gen = 0; // picked checkpoint (0 = none)
	int day = 0;              // the day it plays on from (0 = unknown)
	int dayEnded = 0;
	bool recordPresent = false;
	bool recordDamaged = false; // present but not whole (no header, NUL bytes)
	bool unconfirmed = false;   // picked without a whole record (a named folder only)
	long long startKey = 0;     // run_start_key: newest first by this
	std::string why;          // why nothing was picked
};

// The run's start, seconds since the epoch, for newest-first order
// (run_newer_at): launch.txt's started_utc when this build wrote it, else
// the folder stamp read as local time (a clock change can misorder those).
long long run_start_key(const std::string& dir, const RunName& n)
{
	std::string launch;
	if (read_path_bounded(fs::path(dir) / "launch.txt", 1u << 16, &launch)) {
		const std::string v = launch_value(launch, "started_utc");
		char* end           = nullptr;
		const long long t   = std::strtoll(v.c_str(), &end, 10);
		if (!v.empty() && end != nullptr && *end == '\0' && t > 0) return t;
	}
	int f[6];
	if (!stamp_fields(n.stamp, f)) return 0;
	struct tm lt = {};
	lt.tm_year   = f[0] - 1900;
	lt.tm_mon    = f[1] - 1;
	lt.tm_mday   = f[2];
	lt.tm_hour   = f[3];
	lt.tm_min    = f[4];
	lt.tm_sec    = f[5];
	lt.tm_isdst  = -1;
	const time_t t = mktime(&lt);
	return t == (time_t)-1 ? 0 : (long long)t;
}

// Reads one run folder: launch.txt, its bootstrap, the campaign dir, and the
// record; picks the newest valid checkpoint the record confirms. A run
// without a whole record gives nothing unless `named` (the player named the
// folder): then its newest valid checkpoint, marked unconfirmed.
void evaluate_run(ContinueCandidate* c, bool named)
{
	std::error_code ec;
	const fs::path dir(c->dir);
	if (!read_path_bounded(dir / "launch.txt", 1u << 16, &c->launchText)) c->launchText.clear();
	const std::string role = launch_value(c->launchText, "role");
	c->hostRole = role.empty() ? (c->named && c->name.host) : role == "host";
	// The bootstrap: session/runs/<token>/bootstrap.txt (the token from
	// launch.txt; else the only folder under session/runs).
	fs::path boot;
	const std::string token = launch_value(c->launchText, "token");
	if (pc_netplay_launch_util::is_token(token)) boot = dir / "session" / "runs" / token / "bootstrap.txt";
	if (boot.empty() || !fs::is_regular_file(boot, ec)) {
		boot.clear();
		int found = 0;
		for (fs::directory_iterator it(dir / "session" / "runs", ec), end; !ec && it != end; it.increment(ec)) {
			if (it->is_directory(ec) && fs::is_regular_file(it->path() / "bootstrap.txt", ec)) {
				boot = it->path() / "bootstrap.txt";
				++found;
			}
		}
		if (found != 1) boot.clear();
	}
	if (boot.empty() || !read_path_bounded(boot, kMaxBootstrapBytes, &c->bootText)) {
		c->why = "no readable session bootstrap";
		return;
	}
	c->fingerprint = bootstrap_fingerprint(c->bootText);
	if (c->fingerprint.empty()) {
		c->why = "its bootstrap has no FINGERPRINT";
		return;
	}
	c->campaign = dir / "session" / "campaign";
	std::vector<unsigned long long> valid;
	size_t seen = 0;
	for (fs::directory_iterator it(c->campaign, ec), end; !ec && it != end; it.increment(ec)) {
		unsigned long long g = 0;
		if (!it->is_regular_file(ec) || !checkpoint_gen_from_name(it->path().filename().string(), &g)) continue;
		++seen;
		std::string bytes;
		if (!read_path_bounded(it->path(), 1u << 20, &bytes)) continue;
		const CkptCheck chk = check_checkpoint(bytes, c->fingerprint, g);
		if (chk == CkptCheck::Ok) valid.push_back(g);
		else
			printf("[netplay] launch: --continue: %s: %s is %s; not used\n", c->dir.c_str(),
			       it->path().filename().string().c_str(), ckpt_check_name(chk));
	}
	std::string recText;
	// A record that exists but cannot be read (or is over 1 MiB) is damaged,
	// not absent: only a missing file means an older build made the run.
	const bool recExists  = fs::is_regular_file(dir / "campaign-record.txt", ec);
	const bool recPresent = read_path_bounded(dir / "campaign-record.txt", 1u << 20, &recText);
	Record rec            = parse_record(recPresent ? recText : std::string(), recPresent);
	if (recExists && !recPresent) {
		rec.present = true;
		rec.damaged = true;
	}
	c->recordPresent = rec.present;
	c->recordDamaged = rec.damaged;
	c->gen           = pick_generation(valid, rec, named);
	c->unconfirmed   = c->gen != 0 && !record_trusted(rec);
	if (c->gen == 0) {
		if (!rec.present)
			c->why = "made by an older build (it has no campaign record, so it cannot tell which day-end saves "
			         "both games agreed on); to continue it anyway, name it: --continue <that folder>";
		else if (rec.damaged)
			c->why = "its campaign record is damaged (a crash while it was written?)";
		else
			c->why = seen == 0 ? "no saved day"
			                   : (valid.empty() ? "no valid checkpoint" : "no day-end save both games agreed on");
		return;
	}
	auto d = rec.dayOf.find(c->gen);
	if (d != rec.dayOf.end()) c->day = d->second;
	auto e = rec.dayEnded.find(c->gen);
	if (e != rec.dayEnded.end()) c->dayEnded = e->second;
}

// Where launcher run folders live: <exe dir>/netplay and the read-only-exe
// fallback %LOCALAPPDATA%/Nectar/netplay.
std::vector<std::string> run_bases()
{
	// One definition of the two roots (pc_netplay_launch_util.h run_roots), shared
	// with run creation below: a run written to the fallback because the exe
	// folder path is too long (issue #965 item 1) is found by a bare --continue.
	const char* local     = getenv_nonempty("LOCALAPPDATA");
	const RunRoots roots  = run_roots(exe_dir(), local != nullptr ? std::string(local) : std::string());
	std::vector<std::string> bases;
	bases.push_back(roots.exeBase);
	if (!roots.fallback.empty()) bases.push_back(roots.fallback);
	return bases;
}

// Copies the continued campaign into the new run: the picked checkpoint, the
// card files, and the campaign's other ledgers (for example
// p2-delivery-receipts.txt). Never a temporary, pending, unconfirmed or
// set-aside file, and never another checkpoint than the picked one. The card
// and the ledgers are carried as the old run left them, which can be later
// than the picked checkpoint: the card an abandoned day-end save wrote, or
// P2 receipts of the day in progress. That is what B2's resume in the same
// folder does too, and B2 sends both to the joiner at the handshake, so the
// two games stay in step. A continue from a JOINER's run has no host-only
// p2-delivery-receipts.txt, so the P2 deliveries it recorded are granted
// again. Every copy is on the disk (write_file_durable) before the caller
// records the continue.
void copy_campaign(const ContinueCandidate& c, const std::string& toDir, size_t* files, uint64_t* bytes)
{
	*files = 0;
	*bytes = 0;
	std::error_code ec;
	const fs::path to(toDir);
	fs::create_directories(to / "card" / "card0", ec);
	if (ec) die("--continue: cannot create %s", (to / "card" / "card0").string().c_str());
	auto copy_one = [&](const fs::path& from, const fs::path& dst) {
		std::string data;
		if (!read_path_bounded(from, pc_netplay_xfer::kMaxBundleFileBytes, &data))
			die("--continue: cannot read %s (or it is larger than %u bytes); nothing was changed in %s",
			    from.string().c_str(), (unsigned)pc_netplay_xfer::kMaxBundleFileBytes, c.dir.c_str());
		if (!write_file_durable(dst.string(), data)) die("--continue: cannot write %s", dst.string().c_str());
		++*files;
		*bytes += data.size();
	};
	copy_one(c.campaign / checkpoint_name(c.gen), to / checkpoint_name(c.gen));
	for (fs::directory_iterator it(c.campaign / "card" / "card0", ec), end; !ec && it != end; it.increment(ec)) {
		const std::string n = it->path().filename().string();
		if (it->is_regular_file(ec) && pc_netplay_xfer::card_file_name_ok(n)) copy_one(it->path(), to / "card" / "card0" / n);
	}
	for (fs::directory_iterator it(c.campaign, ec), end; !ec && it != end; it.increment(ec)) {
		const std::string n = it->path().filename().string();
		if (!it->is_regular_file(ec)) continue;
		if (n.find(".sav") != std::string::npos || n.find(".tmp") != std::string::npos || n[0] == '.') continue;
		copy_one(it->path(), to / n);
	}
}

// The P2 overlay and sidecar source of a continued P2 campaign: the old run's
// recorded overlay (launch.txt p2_assets; older runs: the host's original
// --bootstrap folder's assets/, or --netplay-p2-assets here), and the old
// run's play/ folder, which holds the sidecars as that session left them
// (the P2 receipt ledgers included).
void continue_p2_sources(const ContinueCandidate& c, const char* assetsArg)
{
	std::string overlay = assetsArg != nullptr ? absolute_path(assetsArg) : launch_value(c.launchText, "p2_assets");
	if (overlay.empty() && c.hostRole) {
		const std::string src = launch_value(c.launchText, "bootstrap_source");
		const size_t slash = forward_slashes(src).find_last_of('/');
		if (slash != std::string::npos) overlay = forward_slashes(src).substr(0, slash) + "/assets";
	}
	if (overlay.empty() || !is_dir(overlay))
		die("--continue: this campaign uses P2 enemies, but its P2 assets overlay is not known or missing (%s); "
		    "pass --netplay-p2-assets <folder> with the seed's assets overlay",
		    overlay.empty() ? "not recorded" : overlay.c_str());
	sSetup.p2AssetsDir = overlay;
	const std::string oldPlay = c.dir + "/play";
	if (is_dir(oldPlay)) sP2SidecarDir = oldPlay;
	else {
		const std::string src = forward_slashes(launch_value(c.launchText, "bootstrap_source"));
		const size_t slash = src.find_last_of('/');
		sP2SidecarDir = slash == std::string::npos ? std::string() : src.substr(0, slash);
		if (sP2SidecarDir.empty() || !is_dir(sP2SidecarDir))
			die("--continue: this P2 campaign's sidecar files are gone (%s has no play/ folder)", c.dir.c_str());
	}
}

// Interactive consoles get a question; scripts and hidden runs get the default.
bool ask_yes_default(const char* question)
{
#ifdef _WIN32
	const bool interactive = _isatty(_fileno(stdin)) != 0;
#else
	const bool interactive = isatty(fileno(stdin)) != 0;
#endif
	if (!interactive || sSetup.testHidden) {
		printf("[netplay] launch: %s [Y/n] Y (not an interactive console)\n", question);
		fflush(stdout);
		return true;
	}
	printf("[netplay] launch: %s [Y/n] ", question);
	fflush(stdout);
	char line[64];
	if (fgets(line, sizeof(line), stdin) == nullptr) return true;
	const std::string a = trim(line);
	return !(a == "n" || a == "N" || a == "no" || a == "No" || a == "NO");
}

// Resolves --continue. Returns false (after saying so) when there is no saved
// day to continue and the player takes a new campaign instead. `fpFilter`: a
// --bootstrap seed's FINGERPRINT (only that seed's campaigns), or "".
bool resolve_continue(const std::string& folderArg, const std::string& fpFilter, ContinueCandidate* out)
{
	std::vector<ContinueCandidate> cands;
	std::string where;
	if (!folderArg.empty()) {
		ContinueCandidate c;
		c.dir = absolute_path(folderArg);
		if (c.dir.empty() || !is_dir(c.dir)) die("--continue %s: no such folder", folderArg.c_str());
		const size_t slash = c.dir.find_last_of('/');
		c.named = parse_run_name(slash == std::string::npos ? c.dir : c.dir.substr(slash + 1), &c.name);
		if (!c.named && !is_dir(c.dir + "/session/campaign"))
			die("--continue %s: not a netplay run folder (expected netplay\\run-...-host-pid...\\ with "
			    "session\\campaign inside)",
			    folderArg.c_str());
		cands.push_back(c);
		where = c.dir;
	} else {
		for (const std::string& base : run_bases()) {
			std::error_code ec;
			if (!is_dir(base)) continue;
			where += (where.empty() ? "" : " and ") + base;
			for (fs::directory_iterator it(base, ec), end; !ec && it != end; it.increment(ec)) {
				if (!it->is_directory(ec)) continue;
				ContinueCandidate c;
				c.named = parse_run_name(it->path().filename().string(), &c.name);
				if (!c.named || !c.name.host) continue; // bare --continue: the host's own campaigns
				c.dir = forward_slashes(it->path().string());
				cands.push_back(c);
			}
		}
		for (ContinueCandidate& c : cands) c.startKey = run_start_key(c.dir, c.name);
		std::stable_sort(cands.begin(), cands.end(), [](const ContinueCandidate& a, const ContinueCandidate& b) {
			return run_newer_at(a.name, a.startKey, b.name, b.startKey);
		});
		if (where.empty()) where = run_bases()[0];
	}
	const bool named = !folderArg.empty();
	size_t checked = 0;
	const ContinueCandidate* damaged = nullptr;
	for (ContinueCandidate& c : cands) {
		++checked;
		evaluate_run(&c, named);
		if (c.gen != 0 && !fpFilter.empty() && c.fingerprint != fpFilter) {
			c.gen = 0;
			c.why = "another seed than --bootstrap";
		}
		if (c.gen != 0) {
			if (c.unconfirmed)
				printf("[netplay] launch: --continue: WARNING: %s %s, so it cannot tell whether both games agreed "
				       "on its day-end saves; continuing its newest valid checkpoint because you named the folder. "
				       "If that save was not agreed (the session ended with SAVE NOT AGREED or a desync at the "
				       "save), continue an earlier run instead.\n",
				       c.dir.c_str(),
				       c.recordDamaged ? "has a damaged campaign record" : "was made by an older build (no campaign "
				                                                           "record)");
			if (!named && checked > 1) {
				// Never slip silently into an older campaign: the newest host
				// session saved nothing (a new campaign whose first day never
				// ended, or a run that stopped before its session).
				char dayText[64] = "day unknown";
				if (c.day > 0) snprintf(dayText, sizeof(dayText), "day %d", c.day);
				else if (c.dayEnded > 0) snprintf(dayText, sizeof(dayText), "the day after day %d", c.dayEnded);
				printf("[netplay] launch: --continue: the newest host session (%s) has no day-end save to continue "
				       "(%s).\n",
				       cands[0].dir.c_str(), cands[0].why.c_str());
				const std::string q = "Continue the older campaign of " + c.dir + " (checkpoint " +
				                      std::to_string(c.gen) + ", " + dayText + ") instead?";
				fflush(stdout);
				if (!ask_yes_default(q.c_str())) {
					printf("[netplay] launch: --continue: starting a new campaign instead.\n");
					fflush(stdout);
					return false;
				}
			}
			*out = c;
			return true;
		}
		if (named || checked <= 5)
			printf("[netplay] launch: --continue: %s: %s\n", c.dir.c_str(), c.why.c_str());
		if (!named && c.recordDamaged) {
			// Falling through would pick an OLDER campaign than this one
			// without knowing what this one saved: stop and say so.
			damaged = &c;
			break;
		}
	}
	if (damaged != nullptr)
		printf("[netplay] launch: --continue: stopped at %s: its campaign record is damaged, so --continue cannot "
		       "tell which of its day-end saves both games agreed on, and it does not skip past it to an older "
		       "campaign. To continue it anyway (its newest valid checkpoint, which may not be agreed) or an older "
		       "run, name the folder: --continue <run folder>.\n",
		       damaged->dir.c_str());
	else if (!named)
		printf("[netplay] launch: --continue: no saved day yet: none of the %llu host run folder%s under %s has a "
		       "day-end save that both games agreed on%s.\n",
		       (unsigned long long)checked, checked == 1 ? "" : "s", where.c_str(),
		       fpFilter.empty() ? "" : " (only campaigns of the --bootstrap seed count)");
	else
		printf("[netplay] launch: --continue: no saved day yet: %s has no day-end save that both games agreed "
		       "on%s.\n",
		       where.c_str(), fpFilter.empty() ? "" : " for the --bootstrap seed");
	if (damaged == nullptr)
		printf("[netplay] launch: --continue: a campaign can be continued once one of its days has ended with the "
		       "day-end save on both games.\n");
	fflush(stdout);
	if (!ask_yes_default("Start a new campaign instead?")) {
		printf("[netplay] launch: not starting: there is no saved campaign to continue.\n");
		fflush(stdout);
		std::exit(2);
	}
	printf("[netplay] launch: --continue: starting a new campaign instead.\n");
	fflush(stdout);
	return false;
}

} // namespace

const PcNetplayLaunch& pc_netplay_launch_setup(void) { return sSetup; }

bool pc_netplay_launch_wants_local_state(void) { return sSetup.active && !sSetup.externalState; }

void pc_netplay_launch_preinit(int* argcp, char*** argvp)
{
	const int argc = *argcp;
	char** argv    = *argvp;

	// --netplay-input works with every netplay mode; resolve it first so a
	// gamepad peer's background-joystick hint is set before SDL_Init (m6).
	{
		const char* inputCli = argv_value(argc, argv, "--netplay-input");
		const char* inputEnv = getenv_nonempty("PIKMIN_NETPLAY_INPUT");
		const char* spec     = inputCli != nullptr ? inputCli : inputEnv;
		if (spec != nullptr) {
			pc_netplay_input_sel::Kind kind = pc_netplay_input_sel::kInputAuto;
			int index                       = 0;
			if (!pc_netplay_input_sel::parse_input_spec(spec, &kind, &index))
				die("bad --netplay-input %s (want keyboard|gamepad[:N]|auto)", spec);
			sSetup.inputSpec  = spec;
			sSetup.inputKind  = (int)kind;
			sSetup.inputIndex = index;
			if (kind == pc_netplay_input_sel::kInputGamepad) {
				// Keep reading the pad while the other window has focus.
				SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
			}
		}
	}

	const bool hostIce   = argv_present(argc, argv, "--netplay-host-ice");
	const bool joinIce   = argv_present(argc, argv, "--netplay-join-ice");
	const char* launcherOnly[] = { "--bootstrap", "--netplay-code-out", "--netplay-answer-in",
		                           "--netplay-test-hidden", "--netplay-test-ticks",
		                           "--netplay-p2-assets", "--continue", "--netplay-external-state", "--netplay-run-root" };
	if (!hostIce && !joinIce) {
		for (const char* flag : launcherOnly) {
			if (argv_present(argc, argv, flag))
				die("%s needs --netplay-host-ice or --netplay-join-ice", flag);
		}
		return;
	}
	if (hostIce && joinIce) die("--netplay-host-ice and --netplay-join-ice are exclusive");

	// Launcher mode is exclusive with the low-level switches (they stay the
	// test surface) and with every other way to pick a game mode: the run
	// bootstrap is the launcher's, so a hand-passed seed would silently
	// differ from the bundle the joiner receives.
	{
		const char* legacy[] = { "--netplay-host", "--netplay-join", "--netplay-ice-host",
			                     "--netplay-ice-join" };
		for (const char* flag : legacy) {
			if (argv_present(argc, argv, flag))
				die("--netplay-host-ice/--netplay-join-ice are exclusive with "
				    "--netplay-host/--netplay-join/--netplay-ice-host/--netplay-ice-join (%s given)",
				    flag);
		}
		const char* iceHostEnv = getenv_nonempty("PIKMIN_NETPLAY_ICE_HOST");
		if (getenv_nonempty("PIKMIN_NETPLAY_HOST") != nullptr || getenv_nonempty("PIKMIN_NETPLAY_JOIN") != nullptr
		    || (iceHostEnv != nullptr && iceHostEnv[0] == '1') || getenv_nonempty("PIKMIN_NETPLAY_ICE_JOIN") != nullptr)
			die("--netplay-host-ice/--netplay-join-ice are exclusive with the PIKMIN_NETPLAY_HOST/JOIN/"
			    "ICE_HOST/ICE_JOIN environment variables; unset them");
		const char* modes[] = { "--randomizer-seed", "--bbft-port", "--experimental-pikmin2-room",
			                    "--experimental-challenge-level", "--experimental-challenge-stage" };
		for (const char* flag : modes) {
			if (argv_present(argc, argv, flag))
				die("%s cannot be combined with --netplay-host-ice/--netplay-join-ice%s", flag,
				    std::strcmp(flag, "--randomizer-seed") == 0
				        ? " (the host passes a seed with --bootstrap <file>; the joiner gets it from the offer)"
				        : "");
		}
		if (getenv_nonempty("BBFT_PORT") != nullptr)
			die("BBFT_PORT is set: BBFT sessions cannot be combined with --netplay-host-ice/--netplay-join-ice");
	}

	sSetup.active = true;
	sSetup.isHost = hostIce;
    sSetup.externalState = argv_present(argc, argv, "--netplay-external-state");
    if (const char* path = argv_value(argc, argv, "--netplay-run-root")) {
        if (!*path) die("--netplay-run-root requires a nonempty private directory");
        sSetup.requestedRunRoot = fs::absolute(path).lexically_normal().generic_string();
    }
	if (!hostIce) {
		if (argv_present(argc, argv, "--bootstrap"))
			die("--bootstrap is host-only: the joiner gets the bootstrap from the offer code");
		if (argv_present(argc, argv, "--netplay-answer-in"))
			die("--netplay-answer-in is host-only (the joiner prints its answer)");
		if (argv_present(argc, argv, "--continue")) {
			// M5c lane C: nothing to do on this side; say so instead of refusing.
			printf("[netplay] launch: --continue is for the host; the joiner needs no extra step (the host's "
			       "saved day arrives at the handshake). Ignored.\n");
			fflush(stdout);
		}
	}
	// M5c lane C (issue #887): --continue [run folder] (host). The optional
	// folder is the next argument unless that is another switch.
	bool wantContinue = false;
	std::string continueArg;
	if (hostIce) {
		for (int i = 1; i < argc; ++i) {
			if (argv[i] == nullptr || std::strcmp(argv[i], "--continue") != 0) continue;
			wantContinue = true;
			if (i + 1 < argc && argv[i + 1] != nullptr && argv[i + 1][0] != '-' && argv[i + 1][0] != '\0')
				continueArg = argv[i + 1];
			break;
		}
	}
	if (const char* v = argv_value(argc, argv, "--netplay-code-out")) sSetup.codeOut = v;
	if (const char* v = argv_value(argc, argv, "--netplay-answer-in")) sSetup.answerIn = v;
	sSetup.testHidden = argv_present(argc, argv, "--netplay-test-hidden");
	if (const char* tt = argv_value(argc, argv, "--netplay-test-ticks")) {
		char* end       = nullptr;
		unsigned long n = strtoul(tt, &end, 10);
		if (end == tt || *end != '\0' || n == 0) die("bad --netplay-test-ticks %s", tt);
		sSetup.testTicks = n;
	}
	if (sSetup.testHidden) {
		// Hidden, private test runs: the randomizer creates its window hidden
		// under PIKMIN_RANDOMIZER_TEST_BACKGROUND=1, and audio stays silent.
		set_env("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
		if (getenv_nonempty("SDL_AUDIODRIVER") == nullptr) set_env("SDL_AUDIODRIVER", "dummy");
	}

	sSetup.token = fresh_token();

	// ---- the session bootstrap (and, for the joiner, the whole bundle) ----
	std::string boot;
	ContinueCandidate cont; // M5c lane C: the continued campaign (cont.gen != 0)
	if (sSetup.isHost) {
		const char* bootCli = argv_value(argc, argv, "--bootstrap");
		if (bootCli != nullptr) {
			const long n = read_file_bounded(bootCli, kMaxBootstrapBytes, &boot);
			if (n < 0) die("cannot read --bootstrap %s", bootCli);
			if ((size_t)n > kMaxBootstrapBytes)
				die("--bootstrap %s is larger than %u bytes (the offer code's limit)", bootCli,
				    (unsigned)kMaxBootstrapBytes);
			sSetup.bootstrapSource = bootCli;
		} else {
			boot                   = default_bootstrap();
			sSetup.bootstrapSource = "default";
		}
		const char* seedEnv = getenv_nonempty("PIKMIN_NETPLAY_SEED");
		if (seedEnv != nullptr) {
			char* end               = nullptr;
			const unsigned long long v = strtoull(seedEnv, &end, 0);
			if (end != seedEnv && *end == '\0' && v <= 0xFFFFFFFFull) sSetup.seed = (uint32_t)v;
		}
		// M5c lane C: --continue replaces the bootstrap (and the netplay
		// seed) with the continued run's. With --bootstrap only that seed's
		// campaigns are candidates. No saved day: a new campaign, as above.
		if (wantContinue) {
			const std::string fpFilter = bootCli != nullptr ? bootstrap_fingerprint(boot) : std::string();
			if (bootCli != nullptr && fpFilter.empty()) die("--bootstrap %s has no FINGERPRINT line", bootCli);
			if (resolve_continue(continueArg, fpFilter, &cont)) {
				boot                   = cont.bootText;
				sSetup.bootstrapSource = "continue " + cont.dir;
				sSetup.continued       = true;
				sSetup.continueFrom    = cont.dir;
				sSetup.continueGen     = cont.gen;
				sSetup.continueDay     = cont.day;
				sSetup.continueDayEnded = cont.dayEnded;
				const std::string oldSeed = launch_value(cont.launchText, "seed");
				char* end                 = nullptr;
				const unsigned long long v = strtoull(oldSeed.c_str(), &end, 10);
				if (seedEnv == nullptr && !oldSeed.empty() && end != nullptr && *end == '\0' && v <= 0xFFFFFFFFull) {
					sSetup.seed = (uint32_t)v;
					// The deterministic day reseed reads the seed from the
					// environment (pc_netplay_det), like the joiner's.
					set_env("PIKMIN_NETPLAY_SEED", std::to_string(sSetup.seed));
				} else if (seedEnv != nullptr && !oldSeed.empty() && oldSeed != std::to_string(sSetup.seed)) {
					printf("[netplay] launch: --continue: PIKMIN_NETPLAY_SEED=%u replaces the campaign's netplay "
					       "seed %s\n",
					       sSetup.seed, oldSeed.c_str());
				}
				char dayText[48] = "day unknown";
				if (cont.day > 0) snprintf(dayText, sizeof(dayText), "day %d", cont.day);
				else if (cont.dayEnded > 0) snprintf(dayText, sizeof(dayText), "the day after day %d", cont.dayEnded);
				printf("[netplay] launch: --continue: continuing the campaign of %s: checkpoint %llu (%s)%s\n",
				       cont.dir.c_str(), cont.gen, dayText,
				       !cont.unconfirmed    ? ""
				       : cont.recordDamaged ? " (UNCONFIRMED: its campaign record is damaged)"
				                            : " (UNCONFIRMED: a run from an older build, without a campaign record)");
				fflush(stdout);
			}
		}
	} else {
		const char* joinArg = argv_value(argc, argv, "--netplay-join-ice");
		sSetup.offerCode    = read_offer_arg(joinArg);
		std::string err;
		switch (classify_code(sSetup.offerCode)) {
		case kCodeEmpty:
			die("the offer code is empty; copy the host's whole offer line");
		case kCodeGarbage:
			die("that is not a connection code (the host's offer starts with NPIX2-); copy the "
			    "host's whole offer line");
		case kCodeV1: {
			bool isOffer = false;
			std::string sdp;
			if (!pc_netplay_ice::ice_decode_code(sSetup.offerCode, &isOffer, &sdp, &err))
				die("%s", err.c_str());
			if (!isOffer)
				die("that is an answer code (NPIX1- answer): it goes to the host, not to "
				    "--netplay-join-ice; ask the host for the offer (NPIX2-...)");
			die("that offer (NPIX1-) comes from an older build without the session bundle; the "
			    "one-command joiner needs the NPIX2- offer that --netplay-host-ice prints (same "
			    "build on both sides). For an old host, use --netplay-ice-join with matching local "
			    "bootstrap and settings files instead");
		}
		case kCodeOfferV2:
			break;
		}
		std::string sdp;
		pc_netplay_ice::SessionBundle bundle;
		if (!pc_netplay_ice::ice_decode_offer_v2(sSetup.offerCode, &sdp, &bundle, &err)) die("%s", err.c_str());
		if (bundle.bootstrapBytes.empty())
			die("the offer carries no bootstrap (host build too old?); both sides need the same build");
		if (bundle.configText.compare(0, 13, "m3-config-v1;") != 0)
			die("the offer's settings block is not m3-config-v1; both sides need the same build");
		boot                   = bundle.bootstrapBytes;
		sSetup.bootstrapSource = "offer bundle";
		sSetup.seed            = bundle.seed;
		sSetup.configBlock     = bundle.configText;
		parse_captains(sSetup.configBlock);
	}
	{
		std::string err;
		bool p2 = false;
		if (!validate_bootstrap(boot, &err, &p2))
			die("refusing %s: %s", sSetup.isHost ? "--bootstrap" : "the offer's bootstrap", err.c_str());
		sSetup.p2 = p2;
	}
	// M4 lane B2: a P2 seed needs its overlay (refused here, before any run
	// folder exists, when it is missing). M5c lane C: a continued P2 campaign
	// takes the overlay and sidecars its previous run used.
	if (sSetup.continued && sSetup.p2) {
		continue_p2_sources(cont, argv_value(argc, argv, "--netplay-p2-assets"));
	} else {
		if (sSetup.continued && argv_present(argc, argv, "--netplay-p2-assets"))
			die("--netplay-p2-assets is only for P2 seeds; the continued campaign has no ENEMY_P2");
		resolve_p2_overlay(argc, argv, sSetup.isHost ? argv_value(argc, argv, "--bootstrap") : nullptr);
	}
	std::string stamped;
	{
		std::string err;
		if (!restamp_session(boot, sSetup.token, &stamped, &err))
			die("cannot re-stamp the bootstrap SESSION line: %s", err.c_str());
	}

	// ---- this run's private dir (per run and per peer) ----
	// Issue #965 item 1: the run root is <exe dir>/netplay unless that folder is
	// read-only or its path is too long for the deepest file the session
	// creates (Win32 MAX_PATH), in which case it is the fallback root
	// %LOCALAPPDATA%/Nectar/netplay that --continue and host.bat also search.
	// Short, writable exe folders keep exactly the old layout.
	const time_t now = time(nullptr);
	sRunStartUtc     = (long long)now;
	struct tm lt;
#ifdef _WIN32
	localtime_s(&lt, &now);
#else
	localtime_r(&now, &lt);
#endif
	char stamp[128];
	snprintf(stamp, sizeof(stamp), "run-%04d%02d%02d-%02d%02d%02d-%s-pid%u", lt.tm_year + 1900, lt.tm_mon + 1,
	         lt.tm_mday, lt.tm_hour, lt.tm_min, lt.tm_sec, sSetup.isHost ? "host" : "join", current_pid());
	std::string base;
    if (!sSetup.requestedRunRoot.empty()) {
        base = sSetup.requestedRunRoot;
        if (!run_path_fits(base.size(), strlen(stamp) + 3, sSetup.token.size())
            || !make_dirs(base) || !dir_writable(base))
            die("--netplay-run-root is unwritable or exceeds the existing run path budget");
    } else 	{
		const char* local    = getenv_nonempty("LOCALAPPDATA");
		const RunRoots roots = run_roots(exe_dir(), local != nullptr ? std::string(local) : std::string());
		const size_t nameLen = strlen(stamp) + 3; // room for the "-<n>" exclusive-create suffix
		const size_t allowedBase = kPathBudget - 1 - nameLen - 1 - run_deepest_below(sSetup.token.size());
		const bool exeWritable = make_dirs(roots.exeBase) && dir_writable(roots.exeBase);
		const bool exeFits     = run_path_fits(roots.exeBase.size(), nameLen, sSetup.token.size());
		// The fallback is only probed when the exe root cannot be used (no stray folders otherwise).
		const bool needFallback = !exeWritable || !exeFits;
		const bool fbWritable   = needFallback && !roots.fallback.empty() && make_dirs(roots.fallback)
		                          && dir_writable(roots.fallback);
		const RunBaseChoice pick = choose_run_base(roots, exeWritable, fbWritable, nameLen, sSetup.token.size());
		if (pick.useFallback) {
			base = roots.fallback;
			if (pick.why == kRunBaseTooLong)
				printf("[netplay] launch: the game folder path (%u characters) is too long for the run layout "
				       "(the limit is about %u); run folders are written to %s (--continue looks there too)\n",
				       (unsigned)(roots.exeBase.size() - 8), (unsigned)(allowedBase - 8), base.c_str());
			else
				printf("[netplay] launch: %s is not writable; run folders are written to %s\n",
				       roots.exeBase.c_str(), base.c_str());
		} else if (exeWritable) {
			base = roots.exeBase;
			if (!exeFits)
				printf("[netplay] launch: warning: the game folder path (%u characters) may be too long for the run "
				       "layout and %s is not usable as a fallback; unzip the game to a shorter folder if the run "
				       "cannot be created\n",
				       (unsigned)roots.exeBase.size(), roots.fallback.empty() ? "no fallback folder" : roots.fallback.c_str());
		} else {
			die("cannot create a run dir: %s is not writable and the fallback %s is not usable",
			    roots.exeBase.c_str(), roots.fallback.empty() ? "(none: LOCALAPPDATA is not set)" : roots.fallback.c_str());
		}
		fflush(stdout);
	}
	{
		// Exclusive create: a run dir is never reused, so no stale hello.txt,
		// checks.txt or campaign checkpoint can meet a new session.
		for (int n = 0; n < 100 && sSetup.runDir.empty(); ++n) {
			const std::string dir = base + "/" + stamp + (n == 0 ? std::string() : "-" + std::to_string(n));
			const int r           = make_dir(dir);
			if (r == 1) sSetup.runDir = dir;
			else if (r < 0) die("cannot create run dir %s", dir.c_str());
		}
		if (sSetup.runDir.empty()) die("cannot create a fresh run dir under %s", base.c_str());
	}
	const RunLayout layout = run_layout(sSetup.runDir, sSetup.token);
	sSetup.bootstrapPath   = layout.bootstrapPath;
	sSetup.campaignDir     = layout.campaignDir;
	sSetup.saveDir         = layout.saveDir;
	if (!make_dirs(layout.bootstrapDir) || !make_dirs(layout.saveDir))
		die("cannot create the run layout under %s (%u characters; Windows stops at 259, so a shorter game folder or "
		    "LOCALAPPDATA may be needed)",
		    sSetup.runDir.c_str(), (unsigned)sSetup.runDir.size());
	if (!write_file(layout.bootstrapPath, stamped)) die("cannot write %s", layout.bootstrapPath.c_str());
	// M5c lane C: the continued campaign's files, copied (never moved) into
	// this run's campaign dir before the randomizer loads it; the record
	// names the carried checkpoint as agreed (it was, in the run it came from).
	// Fix round 1: the record's header goes to the disk FIRST (a record that
	// confirms nothing), then the copies, then the `carried` line, each
	// committed. A crash or a die() part-way leaves a run folder whose record
	// confirms nothing, which a later --continue never picks.
	{
		const std::string recPath = sSetup.runDir + "/campaign-record.txt";
		if (!write_file_durable(recPath, record_header())) die("cannot write %s", recPath.c_str());
		if (sSetup.continued) {
			size_t files   = 0;
			uint64_t bytes = 0;
			copy_campaign(cont, layout.campaignDir, &files, &bytes);
			printf("[netplay] launch: --continue: copied checkpoint %s and %llu more file%s (%llu B in all) into "
			       "this run; %s is unchanged\n",
			       checkpoint_name(cont.gen).c_str(), (unsigned long long)(files - 1), files == 2 ? "" : "s",
			       (unsigned long long)bytes, cont.dir.c_str());
			fflush(stdout);
			if (!write_file_durable(recPath, record_line_carried(cont.gen, cont.day, cont.dayEnded, cont.dir), "ab"))
				die("cannot append to %s", recPath.c_str());
		}
	}

	// ---- process environment for the engine ----
	// B2: the card/save root is resolved at boot (CARDInit), so the private
	// save dir is set here, before anything can resolve it. With the
	// randomizer active the card itself lives in the derived campaign dir;
	// NECTAR_SAVE_DIR then holds the shader cache (and the card fallback).
	if (const char* prev = getenv_nonempty("NECTAR_SAVE_DIR"))
		printf("[netplay] launch: NECTAR_SAVE_DIR was %s; this session uses its private save dir\n", prev);
	set_env("NECTAR_SAVE_DIR", layout.saveDir);
	if (!sSetup.isHost) {
		// The deterministic reseed (pc_netplay_det) reads the netplay seed
		// from the environment at every stage load: the joiner takes the
		// host's.
		set_env("PIKMIN_NETPLAY_SEED", std::to_string(sSetup.seed));
	}

	// ---- records (never read back by the game) ----
	{
		std::string conf;
		if (read_file_bounded("pikmin_settings.conf", 1u << 20, &conf) >= 0)
			write_file(sSetup.runDir + "/settings-at-start.conf", conf);
		std::string rec;
		rec += std::string("role ") + (sSetup.isHost ? "host" : "join") + "\n";
		rec += "token " + sSetup.token + "\n";
        rec += std::string("state_authority ") + (sSetup.externalState ? "external" : "local") + "\n";
		rec += "bootstrap " + layout.bootstrapPath + "\n";
		rec += "bootstrap_source " + sSetup.bootstrapSource + "\n";
		rec += "campaign " + layout.campaignDir + "\n";
		rec += "save " + layout.saveDir + "\n";
		rec += "seed " + std::to_string(sSetup.seed) + "\n";
		rec += "input " + (sSetup.inputSpec.empty() ? std::string("auto") : sSetup.inputSpec) + "\n";
		// M5c lane C: what --continue reads back from this run later.
		if (sSetup.p2) rec += "p2_assets " + sSetup.p2AssetsDir + "\n";
		if (sSetup.continued) {
			rec += "continue_from " + sSetup.continueFrom + "\n";
			rec += "continue_gen " + std::to_string(sSetup.continueGen) + "\n";
			rec += "continue_day " + std::to_string(sSetup.continueDay) + "\n";
			rec += "continue_day_ended " + std::to_string(sSetup.continueDayEnded) + "\n";
		}
		// Fix round 1: --continue orders runs by this (the folder stamp is
		// local time, which a clock change can turn back).
		rec += "started_utc " + std::to_string(sRunStartUtc) + "\n";
		write_file(sSetup.runDir + "/launch.txt", rec);
	}
	// M4 lane B2: a P2 seed runs in <run>/play (after the records above, which
	// read the original working directory's settings file).
	if (sSetup.p2) setup_play_dir();

	// ---- argv: feed the run bootstrap through the ordinary seed path ----
	sArgStore.clear();
	for (int i = 0; i < argc; ++i) sArgStore.push_back(argv[i] != nullptr ? argv[i] : "");
	sArgStore.push_back("--randomizer-seed");
	sArgStore.push_back(layout.bootstrapPath);
	sArgv.clear();
	for (std::string& a : sArgStore) sArgv.push_back(&a[0]);
	sArgv.push_back(nullptr);
	*argcp = (int)sArgStore.size();
	*argvp = sArgv.data();

	printf("[netplay] launch: role=%s run dir %s\n", sSetup.isHost ? "host" : "join", sSetup.runDir.c_str());
	printf("[netplay] launch: bootstrap %s (%lluB from %s, SESSION %.8s...)\n", layout.bootstrapPath.c_str(),
	       (unsigned long long)stamped.size(), sSetup.bootstrapSource.c_str(), sSetup.token.c_str());
	printf("[netplay] launch: campaign dir %s (private to this run and this peer)\n", layout.campaignDir.c_str());
	printf("[netplay] launch: NECTAR_SAVE_DIR=%s\n", layout.saveDir.c_str());
	if (!sSetup.isHost)
		printf("[netplay] launch: offer bundle seed=%u config=%lluB bootstrap=%lluB\n", sSetup.seed,
		       (unsigned long long)sSetup.configBlock.size(), (unsigned long long)boot.size());
	fflush(stdout);
}

void pc_netplay_launch_post_settings(void)
{
	if (!sSetup.active) return;
	// Both roles: sim-relevant settings are locked for the session and the
	// settings file keeps each player's own values (B3). The joiner adopts
	// the host's block here, before anything reads a sim setting.
	pc_settings_session_begin(sSetup.isHost ? nullptr : sSetup.configBlock.c_str());
}

void pc_netplay_launch_apply_captains(void)
{
	if (!sSetup.active || sSetup.isHost || !sSetup.haveCaptains) return;
	pc_coop_set_captain(0, sSetup.captainP1);
	pc_coop_set_captain(1, sSetup.captainP2);
}
