// Netplay M5a local TURN server helper (issue #887).
//
// A tiny executable around libjuice's own STUN/TURN server
// (juice_server_create) for the TURN-only pair test. Listens on loopback,
// serves TURN allocations for one username/password, and runs until killed.
//
// Usage:
//   netplay_turn_server --port 48020 --user <u> --pass <p>
//     [--bind 127.0.0.1] [--realm pikmin-netplay]
//     [--relay-begin 48030 --relay-end 48049] [--run-seconds N]
// Prints "[turn] listening 127.0.0.1:<port>" once ready (ice_pair.py waits
// for that line), then sleeps. Exit 0 on --run-seconds expiry or SIGINT.

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "juice/juice.h"

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#else
#include <unistd.h>
#endif

namespace {

const char* flag_value(int argc, char** argv, const char* flag)
{
	for (int i = 1; i + 1 < argc; ++i) {
		if (argv[i] != nullptr && strcmp(argv[i], flag) == 0) return argv[i + 1];
	}
	return nullptr;
}

bool flag_present(int argc, char** argv, const char* flag)
{
	for (int i = 1; i < argc; ++i) {
		if (argv[i] != nullptr && strcmp(argv[i], flag) == 0) return true;
	}
	return false;
}

void sleep_ms(unsigned ms)
{
#ifdef _WIN32
	Sleep(ms);
#else
	usleep((useconds_t)ms * 1000);
#endif
}

} // namespace

int main(int argc, char** argv)
{
	if (flag_present(argc, argv, "--help") || flag_present(argc, argv, "-h")) {
		printf("usage: netplay_turn_server --port P --user U --pass W [--bind IP] "
		       "[--realm R] [--relay-begin B --relay-end E] [--run-seconds N]\n");
		return 0;
	}
	const char* portArg = flag_value(argc, argv, "--port");
	const char* user    = flag_value(argc, argv, "--user");
	const char* pass    = flag_value(argc, argv, "--pass");
	const char* bind    = flag_value(argc, argv, "--bind");
	const char* realm   = flag_value(argc, argv, "--realm");
	if (portArg == nullptr || user == nullptr || pass == nullptr || *user == '\0'
	    || *pass == '\0') {
		fprintf(stderr, "netplay_turn_server: need --port, --user and --pass\n");
		return 2;
	}
	char* end  = nullptr;
	long portL = strtol(portArg, &end, 10);
	if (end == portArg || *end != '\0' || portL <= 0 || portL > 65535) {
		fprintf(stderr, "netplay_turn_server: bad --port %s\n", portArg);
		return 2;
	}
	uint16_t relayBegin = 0, relayEnd = 0;
	if (const char* rb = flag_value(argc, argv, "--relay-begin")) {
		long n = strtol(rb, &end, 10);
		if (end == rb || *end != '\0' || n < 0 || n > 65535) {
			fprintf(stderr, "netplay_turn_server: bad --relay-begin %s\n", rb);
			return 2;
		}
		relayBegin = (uint16_t)n;
	}
	if (const char* re = flag_value(argc, argv, "--relay-end")) {
		long n = strtol(re, &end, 10);
		if (end == re || *end != '\0' || n < 0 || n > 65535) {
			fprintf(stderr, "netplay_turn_server: bad --relay-end %s\n", re);
			return 2;
		}
		relayEnd = (uint16_t)n;
	}
	unsigned runSeconds = 0;
	if (const char* rs = flag_value(argc, argv, "--run-seconds")) {
		unsigned long n = strtoul(rs, &end, 10);
		if (end == rs || *end != '\0' || n == 0 || n > 86400) {
			fprintf(stderr, "netplay_turn_server: bad --run-seconds %s\n", rs);
			return 2;
		}
		runSeconds = (unsigned)n;
	}

	juice_server_credentials_t cred;
	memset(&cred, 0, sizeof(cred));
	cred.username          = user;
	cred.password          = pass;
	cred.allocations_quota = 32;

	juice_server_config_t scfg;
	memset(&scfg, 0, sizeof(scfg));
	scfg.credentials            = &cred;
	scfg.credentials_count      = 1;
	scfg.max_allocations        = 16;
	scfg.max_peers              = 16;
	scfg.bind_address           = bind != nullptr ? bind : "127.0.0.1";
	scfg.port                   = (uint16_t)portL;
	scfg.relay_port_range_begin = relayBegin;
	scfg.relay_port_range_end   = relayEnd;
	scfg.realm                  = realm != nullptr ? realm : "pikmin-netplay";

	juice_server_t* server = juice_server_create(&scfg);
	if (server == nullptr) {
		fprintf(stderr, "netplay_turn_server: juice_server_create failed\n");
		return 1;
	}
	uint16_t bound = juice_server_get_port(server);
	printf("[turn] listening %s:%u user=%s realm=%s\n", scfg.bind_address, (unsigned)bound,
	       user, scfg.realm);
	fflush(stdout);

	unsigned waited = 0;
	while (runSeconds == 0 || waited < runSeconds * 10) {
		sleep_ms(100);
		++waited;
	}
	juice_server_destroy(server);
	return 0;
}
