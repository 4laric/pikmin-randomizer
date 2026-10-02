#pragma once
// Netplay launch lane (issue #887): engine-free pieces of the one-command
// launcher (pc_netplay_launch.cpp). Header-only and pure (no SDL, no game,
// no file I/O), so the host-run test (pc_netplay_launch_test) links nothing
// else.
//
//   restamp_session        SESSION re-stamp, exactly like the root M4c helper
//                          randomizer/netplay_mirror.py
//                          restamp_bootstrap_for_peer()
//   validate_bootstrap     what the launcher accepts as a session bootstrap
//                          (bounded, one SESSION line, no P2 sidecar seeds)
//   run_layout             the per-run, per-peer directory layout, chosen so
//                          the randomizer's derived campaign dir
//                          (bootstrap dir -> parent -> parent -> "campaign")
//                          lands inside the run dir
//   classify_code          which connection code the user pasted

#include <cstddef>
#include <cstdint>
#include <string>

namespace pc_netplay_launch_util {

// The v2 offer carries the bootstrap length in a u16 field (see
// pc_netplay_ice.h); the launcher refuses anything longer before it is
// read in full.
constexpr size_t kMaxBootstrapBytes = 65535;

// M4c `_is_hex(text, len)` for a token: lowercase hex only, 8..128 chars.
inline bool is_token(const std::string& t)
{
	if (t.size() < 8 || t.size() > 128) return false;
	for (char c : t) {
		if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
	}
	return true;
}

// Re-stamps the SESSION line exactly like the root M4c helper
// restamp_bootstrap_for_peer(bootstrap_text, peer_token):
//   * the text is split on "\n" and one trailing empty element is dropped;
//   * every line starting with "SESSION " becomes "SESSION <token>" (the
//     whole line is replaced, so a CRLF SESSION line loses its "\r"; every
//     other line keeps its bytes, "\r" included);
//   * exactly one SESSION line must exist, else refuse;
//   * the stamped text must differ from the input, else refuse;
//   * the result is the lines joined with "\n" plus a final "\n".
// Returns false with a one-line reason in *err.
inline bool restamp_session(const std::string& text, const std::string& token, std::string* out,
                            std::string* err)
{
	auto fail = [&](const char* why) {
		if (err != nullptr) *err = why;
		return false;
	};
	if (!is_token(token)) return fail("invalid peer token");
	std::string result;
	result.reserve(text.size() + token.size() + 16);
	size_t sessions = 0;
	bool changed    = false;
	size_t pos      = 0;
	const size_t n  = text.size();
	// Number of "\n"-separated elements is (count of '\n') + 1; the last one
	// is dropped when empty (text ends with "\n" or is empty).
	while (pos <= n) {
		const size_t eol = text.find('\n', pos);
		const size_t end = (eol == std::string::npos) ? n : eol;
		const bool last  = (eol == std::string::npos);
		if (last && end == pos) break; // trailing empty element dropped
		const std::string line = text.substr(pos, end - pos);
		if (line.compare(0, 8, "SESSION ") == 0) {
			++sessions;
			const std::string stamped = "SESSION " + token;
			if (stamped != line) changed = true;
			result += stamped;
		} else {
			result += line;
		}
		result += '\n';
		if (last) break;
		pos = eol + 1;
	}
	if (sessions != 1) return fail("bootstrap has no single SESSION line");
	if (!changed) return fail("bootstrap SESSION line unchanged");
	*out = result;
	return true;
}

// True when the bootstrap needs the P2 enemy bridge: any whitespace-
// separated token ENEMY_P2 or P2_* (review R13: the randomizer's parser reads
// tokens, not lines, so an indented or joined ENEMY_P2 / P2_PROXY_TIER is P2
// too). Those seeds read per-run sidecar files from the working directory
// (p2-*.txt, sarai-*.txt) and an assets/ overlay; M4 lane B2 (issue #885)
// runs them in a per-run play/ directory: the host's sidecars travel in the
// transfer phase, each peer brings its own overlay, and the handshake
// checks both digests.
inline bool bootstrap_needs_p2(const std::string& text)
{
	auto ws = [](char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f'; };
	size_t i = 0;
	const size_t n = text.size();
	while (i < n) {
		while (i < n && ws(text[i])) ++i;
		const size_t start = i;
		while (i < n && !ws(text[i])) ++i;
		if (i == start) break;
		const size_t len = i - start;
		if ((len == 8 && text.compare(start, 8, "ENEMY_P2") == 0) || (len >= 3 && text.compare(start, 3, "P2_") == 0))
			return true;
	}
	return false;
}

// What the launcher accepts as a session bootstrap, before the randomizer's
// own parser sees it:
//   * non-empty and at most kMaxBootstrapBytes;
//   * no NUL bytes;
//   * starts with "PIKMIN_RANDOMIZER ";
//   * exactly one "SESSION " line (the re-stamp rule).
// Returns false with a one-line reason. *p2 tells whether the seed needs the
// P2 enemy bridge (bootstrap_needs_p2); M4 lane B2 no longer refuses those,
// the launcher runs them in a play/ directory instead.
inline bool validate_bootstrap(const std::string& text, std::string* err, bool* p2 = nullptr)
{
	if (p2 != nullptr) *p2 = false;
	auto fail = [&](const std::string& why) {
		if (err != nullptr) *err = why;
		return false;
	};
	if (text.empty()) return fail("bootstrap is empty");
	if (text.size() > kMaxBootstrapBytes)
		return fail("bootstrap is larger than " + std::to_string(kMaxBootstrapBytes) + " bytes");
	if (text.find('\0') != std::string::npos) return fail("bootstrap contains NUL bytes");
    const size_t firstEnd = text.find('\n');
    std::string header = text.substr(0, firstEnd);
    if (!header.empty() && header.back() == '\r') header.pop_back();
    const bool thelynk = header == "PIKMIN_THELYNK 1";
    if (!thelynk && text.compare(0, 18, "PIKMIN_RANDOMIZER ") != 0)
        return fail("not a supported randomizer bootstrap (PIKMIN_RANDOMIZER or PIKMIN_THELYNK 1 required)");
	size_t sessions = 0;
	size_t pos      = 0;
	while (pos < text.size()) {
		size_t eol = text.find('\n', pos);
		if (eol == std::string::npos) eol = text.size();
		std::string line = text.substr(pos, eol - pos);
		if (!line.empty() && line.back() == '\r') line.pop_back();
		if (line.compare(0, 8, "SESSION ") == 0) ++sessions;
		pos = eol + 1;
	}
	if (sessions != 1) return fail("bootstrap has no single SESSION line");
	if (p2 != nullptr) *p2 = !thelynk && bootstrap_needs_p2(text);
	return true;
}

// M4 lane B2: the P2 play directory. A P2 session runs with <run>/play as its
// working directory (the sidecars and assets/ are read cwd-relative there):
// play/assets is a junction to the overlay (host: <bootstrap dir>/assets;
// joiner: --netplay-p2-assets DIR) and play/ holds the sidecar set.
inline std::string play_dir(const std::string& runDir) { return runDir + "/play"; }

// Per-run, per-peer layout under the run dir R (absolute):
//   R/session/runs/<token>/bootstrap.txt   --randomizer-seed target
//   R/session/campaign/                    derived campaign dir (card,
//                                          day-end checkpoints)
//   R/save/                                NECTAR_SAVE_DIR (shader cache,
//                                          non-randomizer card fallback)
// The randomizer derives campaign = bootstrap dir .. .. / "campaign"
// (pc_randomizer.cpp), so R/session/campaign is private to this run and
// this peer as long as R is.
struct RunLayout {
	std::string bootstrapDir;
	std::string bootstrapPath;
	std::string campaignDir;
	std::string saveDir;
};

inline RunLayout run_layout(const std::string& runDir, const std::string& token)
{
	RunLayout l;
	l.bootstrapDir  = runDir + "/session/runs/" + token;
	l.bootstrapPath = l.bootstrapDir + "/bootstrap.txt";
	l.campaignDir   = runDir + "/session/campaign";
	l.saveDir       = runDir + "/save";
	return l;
}

// ---- Run-layout path budget (issue #965 item 1) ----
// The run layout nests R/session/runs/<64-hex token>/<file> under the run dir
// R = <base>/run-<stamp>-<role>-pid<N>[-k], and the base is <exe dir>/netplay.
// Everything the session opens (the randomizer, the launcher, the campaign
// code) uses narrow Win32 paths, which stop at MAX_PATH (260 with the NUL),
// so an exe folder longer than about 119 characters made the launcher die
// with "cannot create the run layout". The fix keeps the layout as it is and
// moves the base to the fallback root (%LOCALAPPDATA%/Nectar/netplay, the
// root --continue and host.bat already search) when the exe-relative base
// cannot hold the deepest path the session will create. A "\\?\" long-path
// prefix was not chosen: the randomizer, the save code and the netplay
// record writers open these files with narrow (ANSI) APIs and their own
// string handling, which do not take the prefix.
constexpr size_t kPathBudget        = 254; // MAX_PATH-1 is 259: 5 characters of safety margin
constexpr size_t kRunStampMax       = 41;  // "run-YYYYMMDD-HHMMSS-join-pid4294967295" (38) + "-99"
constexpr size_t kTokenDirFileMax   = 20;  // longest name in session/runs/<token>/ (bootstrap.txt is 13; a .tmp twin 17)
constexpr size_t kOtherBelowRunMax  = 98;  // floor for every other file below R (measured deepest 96 below R; play/assets/... <= 73)

// Characters below the run dir R (without the leading '/') of the deepest
// path the session creates, for a peer token of tokenLen characters.
inline size_t run_deepest_below(size_t tokenLen)
{
	const size_t viaToken = std::string("session/runs/").size() + tokenLen + 1 + kTokenDirFileMax;
	return viaToken > kOtherBelowRunMax ? viaToken : kOtherBelowRunMax;
}

// True when <base>/<run name of runNameLen characters>/<deepest file> stays
// inside kPathBudget.
inline bool run_path_fits(size_t baseLen, size_t runNameLen, size_t tokenLen)
{
	return baseLen + 1 + runNameLen + 1 + run_deepest_below(tokenLen) <= kPathBudget;
}

inline std::string ascii_lower(std::string s)
{
	for (char& c : s) {
		if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
	}
	return s;
}

// The run roots, in search order: <exe dir>/netplay first, then the fallback
// %LOCALAPPDATA%/Nectar/netplay (omitted when LOCALAPPDATA is unset or names
// the same folder). Both '/'-separated. Launcher run creation, --continue and
// the host.bat lookup all use this one definition.
struct RunRoots {
	std::string exeBase;  // never empty ("netplay" when the exe dir is unknown)
	std::string fallback; // empty when there is none
};

inline RunRoots run_roots(const std::string& exeDir, const std::string& localAppData)
{
	RunRoots r;
	r.exeBase = exeDir.empty() ? std::string("netplay") : exeDir + "/netplay";
	if (!localAppData.empty()) {
		std::string local = localAppData;
		for (char& c : local) {
			if (c == '\\') c = '/';
		}
		const std::string fb = local + "/Nectar/netplay";
		if (ascii_lower(fb) != ascii_lower(r.exeBase)) r.fallback = fb;
	}
	return r;
}

enum RunBaseWhy {
	kRunBaseExe,          // <exe dir>/netplay: the layout is unchanged
	kRunBaseNotWritable,  // fallback: the exe folder is read-only
	kRunBaseTooLong,      // fallback: the exe folder path is too long for the layout
	kRunBaseNone,         // neither root can be used
};

struct RunBaseChoice {
	RunBaseWhy why = kRunBaseNone;
	bool useFallback = false;
};

// Picks the root a new run folder goes under. The exe-relative root wins
// whenever it is writable and holds the deepest path (so short paths behave
// exactly as before); otherwise the fallback, provided it is writable and
// holds it too.
inline RunBaseChoice choose_run_base(const RunRoots& roots, bool exeWritable, bool fallbackWritable,
                                     size_t runNameLen, size_t tokenLen)
{
	RunBaseChoice c;
	const bool exeFits = run_path_fits(roots.exeBase.size(), runNameLen, tokenLen);
	if (exeWritable && exeFits) {
		c.why = kRunBaseExe;
		return c;
	}
	const RunBaseWhy reason = exeWritable ? kRunBaseTooLong : kRunBaseNotWritable;
	if (!roots.fallback.empty() && fallbackWritable && run_path_fits(roots.fallback.size(), runNameLen, tokenLen)) {
		c.why         = reason;
		c.useFallback = true;
		return c;
	}
	// No usable fallback: a writable exe root is still tried as before (the
	// estimate is conservative; the launcher's own error then names the length).
	if (exeWritable) c.why = kRunBaseExe;
	return c;
}

// The randomizer's derivation, restated over '/'-separated strings for the
// test: parent(parent(dirname(bootstrapPath))) + "/campaign".
inline std::string derived_campaign_dir(const std::string& bootstrapPath)
{
	std::string p = bootstrapPath;
	for (int i = 0; i < 3; ++i) {
		const size_t slash = p.find_last_of("/\\");
		if (slash == std::string::npos) return std::string();
		p.erase(slash);
	}
	return p + "/campaign";
}

enum CodeKind {
	kCodeEmpty,
	kCodeOfferV2, // "NPIX2-": the launcher's bundle offer
	kCodeV1,      // "NPIX1-": an M5a offer or any answer (decode tells which)
	kCodeGarbage, // anything else
};

inline CodeKind classify_code(const std::string& trimmed)
{
	if (trimmed.empty()) return kCodeEmpty;
	if (trimmed.compare(0, 6, "NPIX2-") == 0) return kCodeOfferV2;
	if (trimmed.compare(0, 6, "NPIX1-") == 0) return kCodeV1;
	return kCodeGarbage;
}

} // namespace pc_netplay_launch_util
