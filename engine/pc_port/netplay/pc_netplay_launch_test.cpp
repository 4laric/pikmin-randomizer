// Netplay launch lane (issue #887): host-run test for the launcher's pure
// pieces (pc_netplay_launch_util.h, header-only, no SDL/game).
//
// Covers: the SESSION re-stamp against the root M4c helper's rules (m2), the
// bootstrap acceptance rules including the P2 sidecar refusal (M3) and the
// u16 size cap (m1), the per-run/per-peer layout and the randomizer's
// campaign-dir derivation (M1), and connection-code classification (m3).

#include "netplay/pc_netplay_launch_util.h"

#include <cstdio>
#include <string>

namespace {

int sFailures = 0;
int sChecks   = 0;

void check(bool ok, const char* what, int line)
{
	++sChecks;
	if (!ok) {
		++sFailures;
		std::printf("FAIL line %d: %s\n", line, what);
	}
}
#define CHECK(ok, what) check((ok), (what), __LINE__)

const std::string kTok(64, 'b');
const std::string kTok2(64, 'c');

std::string boot(const std::string& session)
{
	return "PIKMIN_RANDOMIZER 5\n" + session + "FINGERPRINT " + std::string(64, 'f')
	     + "\nPROFILE foh-day2\nCATALOG gameplay-checks-v5\nPLACEMENT identity-v1\nGOAL 25\n"
	       "DAYS repeat-day29-v1\nCOLOR red\nSTARTING_FLARLIC 10\nEND\n";
}

} // namespace

int main()
{
	using namespace pc_netplay_launch_util;

	// 1. Re-stamp, M4c rules: exactly one SESSION line, must change, lines
	//    joined with "\n" plus a final "\n", every other byte kept.
	{
		std::string out, err;
		const std::string in = boot("SESSION " + kTok + "\n");
		CHECK(restamp_session(in, kTok2, &out, &err), "one SESSION line re-stamps");
		CHECK(out == boot("SESSION " + kTok2 + "\n"), "only the SESSION line changes");
		CHECK(!restamp_session(in, kTok, &out, &err) && err == "bootstrap SESSION line unchanged",
		      "same token refused (M4c: SESSION line unchanged)");
		CHECK(!restamp_session(boot(""), kTok2, &out, &err) && err == "bootstrap has no single SESSION line",
		      "no SESSION line refused");
		CHECK(!restamp_session(boot("SESSION " + kTok + "\nSESSION " + kTok + "\n"), kTok2, &out, &err),
		      "two SESSION lines refused");
		CHECK(!restamp_session("", kTok2, &out, &err), "empty bootstrap refused");
		CHECK(!restamp_session(in, "XYZ", &out, &err) && err == "invalid peer token", "bad token refused");
		CHECK(!restamp_session(in, std::string(64, 'B'), &out, &err), "uppercase token refused (M4c _is_hex)");
		// "SESSION" needs its space: "SESSIONX" is not a SESSION line.
		CHECK(!restamp_session(boot("SESSIONX " + kTok + "\n"), kTok2, &out, &err),
		      "SESSIONX is not a SESSION line");
		// CRLF input: the SESSION line is replaced whole (its \r goes, as in
		// M4c); every other line keeps its \r.
		const std::string crlf = "PIKMIN_RANDOMIZER 5\r\nSESSION " + kTok + "\r\nEND\r\n";
		CHECK(restamp_session(crlf, kTok2, &out, &err)
		          && out == "PIKMIN_RANDOMIZER 5\r\nSESSION " + kTok2 + "\nEND\r\n",
		      "CRLF: only the SESSION line loses its CR");
		// No final newline: M4c appends one.
		CHECK(restamp_session("PIKMIN_RANDOMIZER 5\nSESSION " + kTok + "\nEND", kTok2, &out, &err)
		          && out == "PIKMIN_RANDOMIZER 5\nSESSION " + kTok2 + "\nEND\n",
		      "missing final newline is added (M4c join)");
		// Blank lines in the middle are kept.
		CHECK(restamp_session("A\n\nSESSION " + kTok + "\n\nEND\n", kTok2, &out, &err)
		          && out == "A\n\nSESSION " + kTok2 + "\n\nEND\n",
		      "inner blank lines kept");
	}

	// 2. Bootstrap acceptance.
	{
		std::string err;
		bool p2 = false;
		CHECK(validate_bootstrap(boot("SESSION " + kTok + "\n"), &err, &p2) && !p2, "stock bootstrap accepted");
        CHECK(validate_bootstrap("PIKMIN_THELYNK 1\nSESSION " + kTok + "\nFINGERPRINT abc\nCHECKS 1 71400\nEND\n", &err, &p2) && !p2, "TheLynk1 header accepted without P2 overlay");
        CHECK(!validate_bootstrap("PIKMIN_THELYNK 2\nSESSION " + kTok + "\nEND\n", &err, &p2), "unsupported TheLynk version refused");
        CHECK(!validate_bootstrap("PIKMIN_THELYNK 1x\nSESSION " + kTok + "\nEND\n", &err, &p2), "ambiguous TheLynk header refused");
        CHECK(!validate_bootstrap("PIKMIN_THELYNK 1\nEND\n", &err, &p2), "TheLynk missing session refused");

		CHECK(!validate_bootstrap("", &err, &p2), "empty refused");
		CHECK(!validate_bootstrap("hello\nSESSION " + kTok + "\n", &err, &p2), "missing header refused");
		CHECK(!validate_bootstrap(boot(""), &err, &p2), "no SESSION refused");
		std::string nul = boot("SESSION " + kTok + "\n");
		nul[5]          = '\0';
		CHECK(!validate_bootstrap(nul, &err, &p2), "NUL bytes refused");
		// The real 918-byte P2 seeds carry ENEMY_P2 (+ optional P2_PROXY_TIER).
		// M4 lane B2: accepted and flagged P2 (the launcher runs them in a
		// play/ directory); detection is token-based (review R13).
		const std::string withP2 = "PIKMIN_RANDOMIZER 9\nSESSION " + kTok
		                         + "\nENEMIES 0\nENEMY_P2 1 abc 1 5465461 76\nEND\n";
		CHECK(validate_bootstrap(withP2, &err, &p2) && p2, "ENEMY_P2 accepted and flagged P2");
		const std::string withTier = "PIKMIN_RANDOMIZER 9\nSESSION " + kTok + "\nP2_PROXY_TIER 1\nEND\n";
		CHECK(validate_bootstrap(withTier, &err, &p2) && p2, "P2_PROXY_TIER flagged P2");
		const std::string crlfP2 = "PIKMIN_RANDOMIZER 9\r\nSESSION " + kTok + "\r\nENEMY_P2 1\r\nEND\r\n";
		CHECK(validate_bootstrap(crlfP2, &err, &p2) && p2, "ENEMY_P2 on a CRLF line flagged P2");
		const std::string indented = "PIKMIN_RANDOMIZER 9\nSESSION " + kTok + "\n   \tENEMY_P2 1 abc 1 5 7\nEND\n";
		CHECK(validate_bootstrap(indented, &err, &p2) && p2, "indented ENEMY_P2 flagged P2 (R13)");
		const std::string joined = "PIKMIN_RANDOMIZER 9\nSESSION " + kTok + "\nENEMIES 0 ENEMY_P2 1 abc 1 5 7 END\n";
		CHECK(validate_bootstrap(joined, &err, &p2) && p2, "ENEMY_P2 joined onto another line flagged P2 (R13)");
		const std::string joinedTier = "PIKMIN_RANDOMIZER 9\nSESSION " + kTok + "\nEND P2_PROXY_TIER 1\n";
		CHECK(validate_bootstrap(joinedTier, &err, &p2) && p2, "joined P2_PROXY_TIER flagged P2 (R13)");
		CHECK(bootstrap_needs_p2("x\tP2_ANYTHING y") && bootstrap_needs_p2("ENEMY_P2") && !bootstrap_needs_p2("ENEMY_P21")
		          && !bootstrap_needs_p2("XENEMY_P2 AP2_X") && !bootstrap_needs_p2("") && !bootstrap_needs_p2("p2_lower"),
		      "token rules: whole ENEMY_P2 token or a P2_ prefix, case-sensitive");
		CHECK(validate_bootstrap(boot("SESSION " + kTok + "\nENEMIES_P2X 1\n"), &err, &p2) && !p2,
		      "a token merely containing P2 is not P2");
		// m1: the u16 cap, 65535 accepted, 65536 refused.
		std::string big = boot("SESSION " + kTok + "\n");
		big.resize(kMaxBootstrapBytes, ' ');
		CHECK(validate_bootstrap(big, &err, &p2), "65535-byte bootstrap accepted");
		big.push_back(' ');
		CHECK(!validate_bootstrap(big, &err, &p2) && !p2, "65536-byte bootstrap refused");
		static_assert(kMaxBootstrapBytes == 0xFFFF, "cap equals the u16 field range");
	}

	// 3. Layout: private campaign dir per run and per peer (M1).
	{
		const RunLayout host = run_layout("C:/game/netplay/run-20260928-120000-host-pid10", kTok);
		const RunLayout join = run_layout("C:/game/netplay/run-20260928-120000-join-pid11", kTok2);
		const RunLayout next = run_layout("C:/game/netplay/run-20260928-121500-host-pid12", kTok);
		CHECK(host.bootstrapPath == "C:/game/netplay/run-20260928-120000-host-pid10/session/runs/" + kTok
		                              + "/bootstrap.txt",
		      "bootstrap two levels inside the session dir");
		CHECK(derived_campaign_dir(host.bootstrapPath) == host.campaignDir,
		      "randomizer derivation lands on the run's own campaign dir");
		CHECK(host.campaignDir == "C:/game/netplay/run-20260928-120000-host-pid10/session/campaign",
		      "campaign dir inside the run dir");
		CHECK(derived_campaign_dir(join.bootstrapPath) != derived_campaign_dir(host.bootstrapPath),
		      "host and joiner never share a campaign dir");
		CHECK(derived_campaign_dir(next.bootstrapPath) != derived_campaign_dir(host.bootstrapPath),
		      "consecutive sessions never share a campaign dir");
		CHECK(derived_campaign_dir("C:/game/netplay/run-x/bootstrap.txt") == "C:/game/campaign",
		      "the old one-level layout derived the shared <exe dir>/campaign (the M1 bug)");
		CHECK(host.saveDir == "C:/game/netplay/run-20260928-120000-host-pid10/save", "save dir inside the run dir");
	}

	// 4. Code classification (m3).
	{
		CHECK(classify_code("") == kCodeEmpty, "empty");
		CHECK(classify_code("NPIX2-abc") == kCodeOfferV2, "v2 offer");
		CHECK(classify_code("NPIX1-abc") == kCodeV1, "v1 offer or answer");
		CHECK(classify_code("hello") == kCodeGarbage, "garbage");
		CHECK(classify_code("npix2-abc") == kCodeGarbage, "prefix is case-sensitive");
	}

	// 5. Run-layout path budget and run roots (issue #965 item 1).
	{
		const size_t nameLen = std::string("run-20260929-235959-join-pid4294967295").size() + 3;
		CHECK(nameLen <= kRunStampMax, "the run name constant covers the longest stamp plus the -<n> suffix");
		// The layout the launcher really builds: no file under it is deeper than the model says.
		const std::string runName = "run-20260929-235959-join-pid4294967295-99";
		const RunLayout deep      = run_layout("B/" + runName, kTok);
		CHECK(deep.bootstrapPath.size() - (std::string("B/") + runName).size() - 1 <= run_deepest_below(kTok.size()),
		      "bootstrap.txt is inside the modelled depth");
		CHECK(run_deepest_below(64) == 13 + 64 + 1 + kTokenDirFileMax || run_deepest_below(64) == kOtherBelowRunMax,
		      "depth model = token dir path + longest file, or the other-files bound");
		CHECK(run_deepest_below(64) >= 96, "at least the measured deepest file (96 below the run folder)");
		CHECK(run_deepest_below(128) > run_deepest_below(64), "a longer token deepens the layout");

		// A short exe folder: the layout is unchanged (exe root chosen, no fallback).
		const RunRoots shortR = run_roots("C:/Users/me/Downloads/pikmin-netplay", "C:\\Users\\me\\AppData\\Local");
		CHECK(shortR.exeBase == "C:/Users/me/Downloads/pikmin-netplay/netplay", "exe root is <exe dir>/netplay");
		CHECK(shortR.fallback == "C:/Users/me/AppData/Local/Nectar/netplay", "fallback root is %LOCALAPPDATA%/Nectar/netplay");
		const RunBaseChoice shortC = choose_run_base(shortR, true, true, nameLen, kTok.size());
		CHECK(!shortC.useFallback && shortC.why == kRunBaseExe, "short writable exe folder keeps the exe root");

		// Boundary: the largest exe folder that fits, and one more character.
		size_t maxExe = 0;
		for (size_t len = 1; len < 200; ++len) {
			if (run_path_fits(len + 8, nameLen, kTok.size())) maxExe = len;
		}
		CHECK(maxExe >= 82 && maxExe <= 119, "the exe-folder limit sits between the measured-good 82 and the measured-bad 119+");
		const RunRoots atLimit = run_roots(std::string(maxExe, 'x'), "C:/L");
		const RunRoots pastLimit = run_roots(std::string(maxExe + 1, 'x'), "C:/L");
		CHECK(!choose_run_base(atLimit, true, true, nameLen, kTok.size()).useFallback, "exactly at the limit stays on the exe root");
		const RunBaseChoice past = choose_run_base(pastLimit, true, true, nameLen, kTok.size());
		CHECK(past.useFallback && past.why == kRunBaseTooLong, "one character past the limit goes to the fallback");
		// The measured cases from the packaging run: 100 and 82 worked, 133 failed.
		CHECK(!choose_run_base(run_roots(std::string(82, 'x'), "C:/L"), true, true, nameLen, 64).useFallback, "82 characters: exe root");
		CHECK(choose_run_base(run_roots(std::string(133, 'x'), "C:/L"), true, true, nameLen, 64).useFallback, "133 characters: fallback");
		CHECK(choose_run_base(run_roots(std::string(150, 'x'), "C:/L"), true, true, nameLen, 64).useFallback, "150 characters: fallback");
		// Read-only exe folder: fallback with its own reason (the old behaviour, now with a fit check).
		const RunBaseChoice ro = choose_run_base(shortR, false, true, nameLen, kTok.size());
		CHECK(ro.useFallback && ro.why == kRunBaseNotWritable, "read-only exe folder uses the fallback");
		// Nothing usable.
		CHECK(!choose_run_base(shortR, false, false, nameLen, kTok.size()).useFallback
		          && choose_run_base(shortR, false, false, nameLen, kTok.size()).why == kRunBaseNone,
		      "neither root writable: none");
		CHECK(choose_run_base(run_roots(std::string(150, 'x'), ""), true, false, nameLen, 64).why == kRunBaseExe,
		      "too long with no fallback: the exe root is still tried (old behaviour)");
		// A fallback that is itself too long is not chosen either.
		CHECK(!choose_run_base(run_roots(std::string(150, 'x'), std::string(150, 'y')), true, true, nameLen, 64).useFallback,
		      "a too-long fallback is refused");
		// Same folder as the exe root: no duplicate fallback.
		CHECK(run_roots("C:/Users/me/AppData/Local/Nectar", "C:\\Users\\me\\AppData\\Local").fallback.empty(),
		      "fallback equal to the exe root (any case) is dropped");
		CHECK(run_roots("C:/Users/ME/AppData/Local/Nectar", "c:\\users\\me\\appdata\\local").fallback.empty(),
		      "case-insensitive equality");
		CHECK(run_roots("", "").exeBase == "netplay" && run_roots("", "").fallback.empty(),
		      "unknown exe dir and no LOCALAPPDATA: relative netplay, no fallback");
		// The fallback root is what --continue searches: a run created there is inside run_roots().fallback.
		const std::string fbRun = shortR.fallback + "/" + runName;
		CHECK(fbRun.compare(0, shortR.fallback.size(), shortR.fallback) == 0, "runs in the fallback live under the searched root");
	}

	std::printf("pc_netplay_launch_test: %s (%d checks, %d failures)\n", sFailures == 0 ? "PASS" : "FAIL",
	            sChecks, sFailures);
	return sFailures == 0 ? 0 : 1;
}
