// Netplay M5c lane C (issue #887): host-run test for the continue/recovery
// pure pieces (pc_netplay_continue.h, header-only, no SDL/game).
//
// Covers: run folder names and newest-first order, launch.txt values, the
// bootstrap FINGERPRINT, checkpoint names and the integrity rules against a
// checkpoint built exactly like pc_randomizer.cpp write_campaign_checkpoint,
// the campaign record (confirmed generations, days, abandoned saves, legacy
// runs without a record) and which generation --continue picks (never a
// half-saved day), and the final recovery message per end kind and role.

#include "netplay/pc_netplay_continue.h"

#include <algorithm>
#include <cstdio>
#include <string>
#include <vector>

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

using namespace pc_netplay_continue;

// pc_randomizer.cpp write_campaign_checkpoint(), restated.
std::string make_checkpoint(const std::string& fp, unsigned long long gen, int usedCount, char fill)
{
	std::string meta = "PIKMIN_CAMPAIGN_1 " + fp + " " + std::to_string(gen);
	for (int i = 0; i < usedCount; ++i) meta += " " + std::to_string(i);
	std::string block(kCheckpointBlock, fill);
	block[0] = 'x';
	block[kCheckpointBlock - 1] = '\n'; // a newline inside the block must not confuse the header parse
	const uint64_t hash = fnv1a64(meta + "\n" + block);
	return meta + " " + std::to_string(hash) + "\n" + block;
}

bool contains(const std::vector<std::string>& lines, const std::string& needle)
{
	for (const std::string& l : lines) {
		if (l.find(needle) != std::string::npos) return true;
	}
	return false;
}

} // namespace

int main()
{
	// 1. Run folder names.
	{
		RunName a, b, c, d;
		CHECK(parse_run_name("run-20260929-101500-host-pid1234", &a) && a.host && a.pid == 1234 && a.seq == 0
		          && a.stamp == "20260929-101500",
		      "host run name");
		CHECK(parse_run_name("run-20260929-101500-join-pid99-3", &b) && !b.host && b.pid == 99 && b.seq == 3,
		      "joiner run name with an exclusive-create retry");
		CHECK(!parse_run_name("run-2026092-101500-host-pid1", nullptr), "short date refused");
		CHECK(!parse_run_name("run-20260929-101500-peer-pid1", nullptr), "unknown role refused");
		CHECK(!parse_run_name("run-20260929-101500-host-pid", nullptr), "missing pid refused");
		CHECK(!parse_run_name("run-20260929-101500-host-pid1-x", nullptr), "bad retry suffix refused");
		CHECK(!parse_run_name("sidecar-set-aside-1", nullptr), "other folders refused");
		CHECK(parse_run_name("run-20260930-000001-host-pid1", &c) && run_newer(c, a), "a later stamp is newer");
		CHECK(parse_run_name("run-20260929-101500-host-pid1-1", &d) && run_newer(d, a), "a retry of the same second is newer");
		CHECK(!run_newer(a, a), "newer is strict");
		std::vector<RunName> v = { a, c, d };
		std::sort(v.begin(), v.end(), run_newer);
		CHECK(v[0].stamp == "20260930-000001" && v[1].seq == 1 && v[2].seq == 0, "newest first");
		// Fix round 1: by start time. After a DST fall-back the later run's
		// local stamp (01:10) is earlier than the earlier run's (01:40).
		RunName early, late;
		CHECK(parse_run_name("run-20261101-014000-host-pid10", &early) &&
		          parse_run_name("run-20261101-011000-host-pid20", &late),
		      "two runs across a clock change");
		CHECK(run_newer(early, late), "by stamp, the earlier run looks newer");
		CHECK(run_newer_at(late, 1793513400LL, early, 1793511600LL) &&
		          !run_newer_at(early, 1793511600LL, late, 1793513400LL),
		      "by start time, the later run is newer");
		CHECK(run_newer_at(d, 5, a, 5) && !run_newer_at(a, 5, a, 5), "same second: the retry, strict");
		int f[6];
		CHECK(stamp_fields("20260929-101502", f) && f[0] == 2026 && f[1] == 9 && f[2] == 29 && f[3] == 10 &&
		          f[4] == 15 && f[5] == 2,
		      "stamp fields");
		CHECK(!stamp_fields("20260929_101502", f) && !stamp_fields("2026092-101502", f), "bad stamps");
	}

	// 2. launch.txt and the bootstrap fingerprint.
	{
		const std::string launch = "role host\r\ntoken abc\nbootstrap C:/a b/boot.txt\nseed 7\n";
		CHECK(launch_value(launch, "role") == "host", "role (CRLF stripped)");
		CHECK(launch_value(launch, "bootstrap") == "C:/a b/boot.txt", "a value keeps its spaces");
		CHECK(launch_value(launch, "seed") == "7", "seed");
		CHECK(launch_value(launch, "see").empty(), "a key prefix is not a key");
		CHECK(launch_value(launch, "campaign").empty(), "absent key");
		const std::string boot = "PIKMIN_RANDOMIZER 5\nSESSION aa\nFINGERPRINT 0123abcd\nPROFILE foh-day2\nEND\n";
		CHECK(bootstrap_fingerprint(boot) == "0123abcd", "fingerprint");
		CHECK(bootstrap_fingerprint("PIKMIN_RANDOMIZER 5\nEND\n").empty(), "no fingerprint");
	}

	// 3. Checkpoint names and integrity.
	{
		unsigned long long g = 0;
		CHECK(checkpoint_gen_from_name("00000000000000000007.sav", &g) && g == 7, "gen from name");
		CHECK(checkpoint_name(7) == "00000000000000000007.sav", "name from gen");
		CHECK(!checkpoint_gen_from_name("7.sav", nullptr), "short name");
		CHECK(!checkpoint_gen_from_name("00000000000000000007.sav.pending", nullptr), "pending is not a checkpoint");
		CHECK(!checkpoint_gen_from_name("00000000000000000007.sav.unconfirmed", nullptr), "unconfirmed is not a checkpoint");
		const std::string fp = std::string(64, 'f');
		const std::string ok = make_checkpoint(fp, 2, 3, 'a');
		CHECK(check_checkpoint(ok, fp, 2) == CkptCheck::Ok, "a checkpoint written like the randomizer's passes");
		CHECK(check_checkpoint(make_checkpoint(fp, 2, 7, 'q'), fp, 2) == CkptCheck::Ok, "7 used counts (schema 5)");
		CHECK(check_checkpoint(ok, std::string(64, 'e'), 2) == CkptCheck::Fingerprint, "another seed");
		CHECK(check_checkpoint(ok, fp, 3) == CkptCheck::Generation, "gen mismatch with the name");
		std::string cut = ok;
		cut.pop_back();
		CHECK(check_checkpoint(cut, fp, 2) == CkptCheck::Size, "truncated");
		std::string flip = ok;
		flip[flip.size() - 100] ^= 1;
		CHECK(check_checkpoint(flip, fp, 2) == CkptCheck::Hash, "one flipped block byte");
		CHECK(check_checkpoint("garbage", fp, 2) == CkptCheck::BadHeader, "garbage");
		CHECK(check_checkpoint("PIKMIN_CAMPAIGN_1 x\n" + std::string(kCheckpointBlock, 'a'), "x", 2)
		          == CkptCheck::BadHeader,
		      "too few header fields");
	}

	// 4. The campaign record and the pick.
	{
		const std::string rec = record_header() + record_line_carried(1, 3, 2, "C:/games/netplay/run-1 x")
		                      + record_line_start(1, true) + record_line_day(1, 3)
		                      + record_line_saved(2, 58000, 3) + record_line_day(2, 4)
		                      + record_line_abandoned(3, 6) + record_line_end("save-timeout", 6, 90000);
		const Record r = parse_record(rec);
		CHECK(r.present && r.confirmedMax == 2, "confirmed max is the newest agreed save");
		CHECK(r.dayOf.at(1) == 3 && r.dayOf.at(2) == 4, "days per generation");
		CHECK(r.dayEnded.at(2) == 3, "day ended by the save");
		CHECK(r.dayEnded.at(1) == 2, "day ended by the carried save");
		CHECK(!r.damaged && record_trusted(r), "a whole record");
		CHECK(r.carriedFrom == "C:/games/netplay/run-1 x", "carried-from path keeps spaces");
		CHECK(r.abandoned.size() == 1 && r.abandoned[0] == 3, "abandoned save");
		CHECK(r.endKind == "save-timeout" && r.endCode == 6, "end line");
		CHECK(pick_generation({ 1, 2, 3 }, r) == 2, "an abandoned (half-saved) day is never picked");
		CHECK(pick_generation({ 1 }, r) == 1, "the newest valid confirmed checkpoint");
		CHECK(pick_generation({}, r) == 0, "nothing valid");
		const Record fresh = parse_record(record_header() + record_line_start(0, true));
		CHECK(fresh.present && fresh.confirmedMax == 0, "a new campaign confirms nothing");
		CHECK(pick_generation({ 1 }, fresh) == 0, "a checkpoint written but never agreed is not continued");
		// Fix round 1 (review MAJOR-2): a run without a record (an older
		// build, or a crash before the record) confirms nothing on its own;
		// only a folder the player names uses its newest valid checkpoint.
		const Record legacy = parse_record("", false);
		CHECK(!record_trusted(legacy) && pick_generation({ 1, 4, 2 }, legacy) == 0,
		      "a run without a record: nothing for a bare --continue");
		CHECK(pick_generation({ 1, 4, 2 }, legacy, true) == 4, "a named run without a record: its newest valid one");
		// A damaged record (a crash): NUL bytes, or no header line.
		const Record zeroed = parse_record(std::string(200, '\0'));
		CHECK(zeroed.present && zeroed.damaged && pick_generation({ 1 }, zeroed) == 0, "a zeroed record is damaged");
		const Record tail = parse_record(record_header() + record_line_saved(1, 9, 2) + std::string(40, '\0'));
		CHECK(tail.damaged && pick_generation({ 1 }, tail) == 0, "NUL bytes after good lines: damaged");
		CHECK(pick_generation({ 1 }, tail, true) == 1, "a named damaged run: its newest valid one");
		const Record headless = parse_record(record_line_saved(1, 9, 2));
		CHECK(headless.damaged, "no header line: damaged");
		const Record headerOnly = parse_record(record_header());
		CHECK(!headerOnly.damaged && pick_generation({ 1 }, headerOnly) == 0,
		      "a header only (a continue whose copies never finished): nothing confirmed");
		const Record junk = parse_record(record_header() + "saved gen=x\nday gen=1\nstart\n# comment gen=9\n");
		CHECK(junk.confirmedMax == 0 && junk.dayOf.empty(), "malformed lines are ignored");
		CHECK(record_field("day gen=1 day_ended=5 day=4", "day") == "4", "day= is not day_ended=");
	}

	// 5. The final message.
	{
		EndInfo e;
		e.kind = EndKind::Desync;
		e.host = true;
		e.frame = 30012;
		e.gen = 1;
		e.day = 3;
		e.exe = "nectar.exe";
		e.extraArgs = "--netplay-input keyboard";
		std::vector<std::string> l = recovery_lines(e);
		CHECK(contains(l, "DESYNC") && contains(l, "at frame 30012"), "what happened");
		CHECK(!contains(l, "netplay run folder"), "no run folder request without a forensics folder");
		{
			// #1037: a desync with a run folder asks the players to send it.
			EndInfo f = e;
			f.forensicsDir = "C:\\game\\netplay\\run-1";
			const std::vector<std::string> fl = recovery_lines(f);
			CHECK(contains(fl, "send your whole netplay run folder") && contains(fl, "The run folder: C:\\game\\netplay\\run-1"),
			      "desync names the run folder to send");
			CHECK(contains(fl, "desync-report.txt") && contains(fl, "session-inputs.pknl"), "and what it holds");
			CHECK(fl.back() == "The run folder: C:\\game\\netplay\\run-1", "the folder path is the last line");
			f.kind = EndKind::Disconnect;
			CHECK(!contains(recovery_lines(f), "netplay run folder"), "only a desync asks for it");
		}
		CHECK(contains(l, "Last save: the end of day 2; the campaign continues from the start of day 3 (checkpoint 1)."),
		      "the last save names the day that ended and the day that follows (day known: the day before ended)");
		e.dayEnded = 2;
		l = recovery_lines(e);
		CHECK(contains(l, "Last save: the end of day 2; the campaign continues from the start of day 3 (checkpoint 1)."),
		      "both known: the same line");
		{
			EndInfo d1 = e;
			d1.day      = 1;
			d1.dayEnded = 0;
			CHECK(contains(recovery_lines(d1), "Last save: the campaign continues from the start of day 1 (checkpoint 1)."),
			      "day 1 (no day before it): the day only");
		}
		CHECK(contains(l, "  or: .\\nectar.exe --netplay-host-ice --continue --netplay-input keyboard"),
		      "the exact command, PowerShell-ready (.\\ prefix)");
		CHECK(contains(l, "  .\\host.bat --continue"), "the .bat route with --continue");
		CHECK(contains(l, "PowerShell or Command Prompt"), "which consoles the commands are for");
		e.host = false;
		l = recovery_lines(e);
		CHECK(contains(l, "the host runs .\\host.bat --continue (or .\\nectar.exe --netplay-host-ice --continue)") &&
		          contains(l, "You join as usual"),
		      "joiner wording");
		e.kind = EndKind::SaveTimeout;
		e.gen = 0;
		e.day = 0;
		l = recovery_lines(e);
		CHECK(contains(l, "SAVE NOT AGREED") && contains(l, "Nothing is saved yet") && contains(l, "new campaign"),
		      "no saved day: a new campaign");
		CHECK(!contains(l, "--continue"), "no continue command without a saved day");
		CHECK(contains(l, "the host runs .\\host.bat and you join as before") && !contains(l, "--netplay-input"),
		      "joiner: the host's command, not this peer's switches");
		e.host = true;
		l = recovery_lines(e);
		CHECK(contains(l, "run .\\host.bat (or .\\nectar.exe --netplay-host-ice --netplay-input keyboard)"),
		      "host: its own command with its switches");
		CHECK(local_command("nectar.exe") == ".\\nectar.exe", "plain exe name: .\\ prefix");
		CHECK(local_command_cmd("nectar.exe") == ".\\nectar.exe", "plain exe name: the same in Command Prompt");
		CHECK(local_command_cmd("nectar (2).exe") == "\".\\nectar (2).exe\"", "spaces: Command Prompt quotes");
		// Fix round 1 (reviews): a name that needs quoting gets both forms,
		// each labelled; the '(PowerShell or Command Prompt)' claim stays only
		// on the lines that hold for both.
		{
			EndInfo q = e;
			q.kind     = EndKind::Desync;
			q.host     = true;
			q.gen      = 1;
			q.day      = 3;
			q.dayEnded = 2;
			q.exe      = "nectar (2).exe";
			const std::vector<std::string> ql = recovery_lines(q);
			CHECK(contains(ql, "  or in PowerShell: & '.\\nectar (2).exe' --netplay-host-ice --continue") &&
			          contains(ql, "  or in Command Prompt: \".\\nectar (2).exe\" --netplay-host-ice --continue"),
			      "quoted exe: a PowerShell line and a Command Prompt line");
			CHECK(!contains(ql, "  or: &"), "quoted exe: the call operator is never offered to both consoles");
			std::vector<std::string> qb(ql.begin() + 1, ql.end());
			const std::vector<std::string> qbl = banner_lines(qb, 6);
			CHECK(!contains(qbl, "Command Prompt:") && contains(qbl, "Your partner joins"),
			      "quoted exe banner: the Command Prompt-only line is left out, the rest fits");
			q.host = false;
			CHECK(contains(recovery_lines(q),
			               "(or, in PowerShell, & '.\\nectar (2).exe' --netplay-host-ice --continue)"),
			      "quoted exe, joiner: labelled PowerShell");
			q.gen  = 0;
			q.host = true;
			CHECK(contains(recovery_lines(q),
			               "run .\\host.bat (or, in PowerShell, & '.\\nectar (2).exe' --netplay-host-ice"),
			      "quoted exe, new campaign: labelled PowerShell");
		}
		CHECK(local_command("nectar (2).exe") == "& '.\\nectar (2).exe'", "spaces: PowerShell call operator");
		CHECK(local_command("it's.exe") == "& '.\\it''s.exe'", "a quote is doubled");
		// The banner font has no backslash: PowerShell's '/' form, labelled.
		CHECK(banner_line("  .\\host.bat --continue") == "  ./host.bat --continue", "banner: ./ form");
		CHECK(banner_line("run this in the game's folder (PowerShell or Command Prompt):") ==
		          "run this in the game's folder (PowerShell; the console window has the Command Prompt form):",
		      "banner: says the / form is PowerShell's");
		for (const std::string& ln : recovery_lines(e)) {
			CHECK(banner_line(ln).find('\\') == std::string::npos, "banner: no backslash left");
		}
		// Fix round 1: banner_lines labels the first '/' command once, for the
		// joiner too (its lines had no label).
		{
			EndInfo jb   = e;
			jb.kind      = EndKind::Desync;
			jb.gen       = 1;
			jb.day       = 3;
			jb.dayEnded  = 2;
			jb.host      = false;
			std::vector<std::string> body = recovery_lines(jb);
			body.erase(body.begin());
			const std::vector<std::string> b = banner_lines(body, 6);
			size_t labelled = 0;
			for (const std::string& x : b) {
				if (x.find("(PowerShell form)") != std::string::npos) ++labelled;
				CHECK(x.find('\\') == std::string::npos, "joiner banner: no backslash");
			}
			CHECK(labelled == 1 && contains(b, "./host.bat --continue (or ./nectar.exe"),
			      "joiner banner: the first command line says it is PowerShell's form, once");
			EndInfo hb = jb;
			hb.host    = true;
			std::vector<std::string> hbody = recovery_lines(hb);
			hbody.erase(hbody.begin());
			const std::vector<std::string> h = banner_lines(hbody, 6);
			CHECK(!contains(h, "(PowerShell form)") && contains(h, "the console window has the Command Prompt form"),
			      "host banner: the heading line carries the label, no second one");
		}
		// A joiner whose agreed day-end save the host may have abandoned
		// (the savetimeout pair): no saved day claimed, the host decides.
		{
			EndInfo j;
			j.kind            = EndKind::PeerQuit;
			j.host            = false;
			j.gen             = 0;
			j.pendingGen      = 1;
			j.pendingDayEnded = 2;
			const std::vector<std::string> pl = recovery_lines(j);
			CHECK(contains(pl, "Nothing is saved yet") && contains(pl, "The day-end save at the end of day 2 may not count"),
			      "pending: not claimed, said so");
			CHECK(contains(pl, "To carry on: the host runs .\\host.bat --continue") && !contains(pl, "new campaign"),
			      "pending: the host's --continue decides");
			CHECK(pl.size() - 1 <= 6, "pending: fits the banner");
			j.gen = 1;
			j.day = 3;
			j.pendingGen = 2;
			j.pendingDayEnded = 3;
			CHECK(contains(recovery_lines(j), "To carry on from that day: the host runs"), "pending over a saved day");
		}
		e.kind = EndKind::PeerQuit;
		e.gen = 2;
		e.day = 0;
		e.dayEnded = 3;
		e.host = true;
		l = recovery_lines(e);
		CHECK(contains(l, "OTHER PLAYER LEFT") && contains(l, "the end of day 3"), "day unknown: the day it ended");
		e.launcher = false;
		l = recovery_lines(e);
		CHECK(contains(l, "same switches") && !contains(l, "host.bat"), "low-level switches");
		CHECK(std::string(end_kind_name(EndKind::Disconnect)) == "disconnect", "kind names");
	}

    // Regression: verbose desync diagnostics/pending saves used to push the
    // restart actions beyond the renderer's 14-row cap. Bound every combination
    // conservatively with 13 pixels per glyph and 568 pixels of content width.
    // DGXGraphics uses a 640-wide logical render mode (dgxGraphics.cpp),
    // independent of the desktop window dimensions.
    for (int kind = 0; kind < 6; ++kind) for (bool host : {false, true})
    for (bool launcher : {false, true}) for (int saved = 0; saved < 5; ++saved)
    for (bool pending : {false, true}) {
        EndInfo e;
        e.kind = static_cast<EndKind>(kind); e.host = host; e.launcher = launcher;
        e.gen = saved; e.day = saved == 1 ? 3 : (saved == 4 ? 1 : 0); e.dayEnded = saved == 2 ? 9 : 0;
        e.pendingGen = pending ? 99 : 0;
        e.exe = std::string(220, 'x'); e.extraArgs = std::string(400, 'x');
        e.forensicsDir = std::string(240, 'x');
        const auto before = recovery_lines(e);
        const auto lines = recovery_banner_lines(e);
        CHECK(lines.size() <= 6, "player banner fits feed line cap");
        int rows = 0;
        for (const auto& line : lines) {
            int width = 0; ++rows;
            size_t at = 0;
            while (at < line.size()) {
                const size_t end = line.find(' ', at);
                const size_t stop = end == std::string::npos ? line.size() : end;
                const int word = int(stop - at) * 13;
                CHECK(word <= 568, "player words fit minimum content width");
                if (width && width + 13 + word > 568) { ++rows; width = word; }
                else width += (width ? 13 : 0) + word;
                at = stop + 1;
            }
            CHECK(line.find("checkpoint") == std::string::npos && line.find("frame") == std::string::npos &&
                line.find("--") == std::string::npos, "player banner omits implementation detail");
        }
        CHECK(rows <= 14, "all player actions survive wrapped row cap");
        CHECK(recovery_lines(e) == before, "player formatting leaves console unchanged");
        CHECK(contains(lines, "Details and launch commands"), "console alternative always visible");
        CHECK(saved != 4 || !contains(lines, "Day 1 saved"), "unknown ended day is never invented");
        CHECK(!pending || contains(lines, "unconfirmed"), "pending save is explicitly unconfirmed");
        CHECK(saved || pending || contains(lines, "new campaign"), "unsaved restart explained");
        if (launcher) CHECK(contains(lines, "new offer code") && contains(lines, "answer code"), "fresh exchange required");
        else CHECK(!contains(lines, "host.bat") && contains(lines, "same launch options") &&
            contains(lines, "sets up the campaign") && !contains(lines, "sends the saved day"), "low-level path accurate");
    }

	std::printf("pc_netplay_continue_test: %s (%d checks, %d failures)\n", sFailures == 0 ? "PASS" : "FAIL",
	            sChecks, sFailures);
	return sFailures == 0 ? 0 : 1;
}
