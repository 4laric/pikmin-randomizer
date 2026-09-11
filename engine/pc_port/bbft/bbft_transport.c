// Shared BBFT Windows transport. Canonical source; vendor using the checked copy tool.
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

// Do not erase identically named fields in game headers included by adapters.
#ifdef near
#undef near
#endif
#ifdef far
#undef far
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#include "bbft_transport.h"
#ifdef _MSC_VER
#pragma comment(lib, "ws2_32.lib")
#endif

#define BBFT_MAX_NAME   64
#define BBFT_MAX_ITEMS  128
#define BBFT_MAX_LOCKS  32
#define BBFT_MAX_CHECKS 512

#define BBFT_STATE_FILE "bbft_state.txt"
#define BBFT_LOG_FILE   "bbft_log.txt"

#define BBFT_RELOAD_INTERVAL 60 // frames

static const char *sGameName;
static void (*sFileReset)(void);
static void (*sFileLine)(char *);
static int sStateReady = 0;
static char sRemoteChecks[BBFT_MAX_CHECKS][BBFT_MAX_NAME];
static int sNumRemoteChecks = 0;

struct BbftItem {
    char name[BBFT_MAX_NAME];
    int count;
};

struct BbftLock {
    char id[BBFT_MAX_NAME];
    char key[BBFT_MAX_NAME];
};

static struct BbftItem sItems[BBFT_MAX_ITEMS];
static int sNumItems = 0;

static struct BbftLock sLocks[BBFT_MAX_LOCKS];
static int sNumLocks = 0;

static char sChecks[BBFT_MAX_CHECKS][BBFT_MAX_NAME];
static int sNumChecks = 0;

static int sFrameCounter = 0;
static int sInited = 0;


#define BBFT_NOTIFY_CAP 64
#define BBFT_NOTIFY_TEXT 256
static char sNotifications[BBFT_NOTIFY_CAP][BBFT_NOTIFY_TEXT];
static int sNotifyHead, sNotifyCount;
static char sDestination[32];

int bbft_take_destination(char *text, int capacity) {
    if (!text || capacity <= 0 || !sDestination[0]) return 0;
    strncpy(text, sDestination, capacity - 1);
    text[capacity - 1] = '\0';
    sDestination[0] = '\0';
    return 1;
}

int bbft_next_notification(char *text, int capacity) {
    if (!text || capacity <= 0 || !sNotifyCount) return 0;
    strncpy(text, sNotifications[sNotifyHead], capacity - 1);
    text[capacity - 1] = '\0';
    sNotifyHead = (sNotifyHead + 1) % BBFT_NOTIFY_CAP;
    --sNotifyCount;
    return 1;
}

static void bbft_queue_notification(const char *text) {
    int tail;
    if (sNotifyCount == BBFT_NOTIFY_CAP) {
        sNotifyHead = (sNotifyHead + 1) % BBFT_NOTIFY_CAP;
        --sNotifyCount;
        bbft_logf("NOTIFY queue full; dropped oldest");
    }
    tail = (sNotifyHead + sNotifyCount) % BBFT_NOTIFY_CAP;
    strncpy(sNotifications[tail], text, BBFT_NOTIFY_TEXT - 1);
    sNotifications[tail][BBFT_NOTIFY_TEXT - 1] = '\0';
    ++sNotifyCount;
}

// ---------------------------------------------------------------- logging

void bbft_logf(const char *fmt, ...) {
    va_list args;
    FILE *f = fopen(BBFT_LOG_FILE, "a");
    if (f == NULL) {
        return;
    }
    va_start(args, fmt);
    vfprintf(f, fmt, args);
    va_end(args);
    fputc('\n', f);
    fclose(f);
}

// ---------------------------------------------------------------- state file

// Trim trailing whitespace/newlines in place.
static void bbft_rstrip(char *s) {
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' || s[n - 1] == ' ' || s[n - 1] == '\t')) {
        s[--n] = '\0';
    }
}

// Parse bbft_state.txt into the given tables. Returns 1 if the file was read.
static int bbft_parse_state(struct BbftItem *items, int *numItems,
                            struct BbftLock *locks, int *numLocks) {
    char line[256];
    FILE *f = fopen(BBFT_STATE_FILE, "r");

    *numItems = 0;
    *numLocks = 0;

    if (sFileReset) sFileReset();
    if (f == NULL) {
        return 0;
    }
    sNumRemoteChecks = 0;
    while (fgets(line, sizeof(line), f) != NULL) {
        bbft_rstrip(line);
        if (line[0] == '\0' || line[0] == '#') {
            continue;
        }

        if (strncmp(line, "item ", 5) == 0) {
            // "item <name with spaces> <count>": count is the last token.
            char *rest = line + 5;
            char *lastSpace = strrchr(rest, ' ');
            int count;
            if (lastSpace == NULL) {
                continue;
            }
            count = atoi(lastSpace + 1);
            *lastSpace = '\0';
            bbft_rstrip(rest);
            if (rest[0] == '\0' || count <= 0 || *numItems >= BBFT_MAX_ITEMS) {
                continue;
            }
            strncpy(items[*numItems].name, rest, BBFT_MAX_NAME - 1);
            items[*numItems].name[BBFT_MAX_NAME - 1] = '\0';
            items[*numItems].count = count;
            (*numItems)++;
        } else if (strncmp(line, "lock ", 5) == 0) {
            // "lock <lock_id> <key item name with spaces>"
            char *rest = line + 5;
            char *space = strchr(rest, ' ');
            if (space == NULL || *numLocks >= BBFT_MAX_LOCKS) {
                continue;
            }
            *space = '\0';
            while (*(space + 1) == ' ') {
                space++;
            }
            strncpy(locks[*numLocks].id, rest, BBFT_MAX_NAME - 1);
            locks[*numLocks].id[BBFT_MAX_NAME - 1] = '\0';
            strncpy(locks[*numLocks].key, space + 1, BBFT_MAX_NAME - 1);
            locks[*numLocks].key[BBFT_MAX_NAME - 1] = '\0';
            (*numLocks)++;
        } else if (strncmp(line, "checked ", 8) == 0) {
            if (sNumRemoteChecks < BBFT_MAX_CHECKS && line[8] && strlen(line + 8) < BBFT_MAX_NAME) {
                strcpy(sRemoteChecks[sNumRemoteChecks++], line + 8);
            }
        } else if (sFileLine) {
            sFileLine(line);
        }
    }

    fclose(f);
    return 1;
}

// Re-read the state file; log and swap in only if something actually changed.
static void bbft_reload_state(void) {
    static struct BbftItem newItems[BBFT_MAX_ITEMS];
    static struct BbftLock newLocks[BBFT_MAX_LOCKS];
    int newNumItems = 0;
    int newNumLocks = 0;
    int changed;

    if (bbft_parse_state(newItems, &newNumItems, newLocks, &newNumLocks)) sStateReady = 1;

    changed = (newNumItems != sNumItems) || (newNumLocks != sNumLocks)
              || (newNumItems > 0 && memcmp(newItems, sItems, newNumItems * sizeof(struct BbftItem)) != 0)
              || (newNumLocks > 0 && memcmp(newLocks, sLocks, newNumLocks * sizeof(struct BbftLock)) != 0);

    if (!changed) {
        return;
    }

    memcpy(sItems, newItems, sizeof(sItems));
    memcpy(sLocks, newLocks, sizeof(sLocks));
    sNumItems = newNumItems;
    sNumLocks = newNumLocks;

    bbft_logf("STATE items=%d locks=%d", sNumItems, sNumLocks);
}

// ---------------------------------------------------------------- transport
//
// M2/M4: newline-delimited JSON over a localhost TCP socket to the conductor.
// The port comes from "--bbft-port N" on the command line or the BBFT_PORT
// environment variable. With no port, or while the connection is down, the
// bbft_state.txt file stub above stays in charge, so nothing else in the game
// needs to care which transport is live.

#define BBFT_RECONNECT_MS 2000
#define BBFT_RX_CAP 65536

static int sTcpWanted = 0; // a port was configured
static int sTcpPort = 0;
static int sTcpConnected = 0;
static SOCKET sSock = INVALID_SOCKET;
static unsigned long sNextConnectTick = 0;
static char sRx[BBFT_RX_CAP];
static int sRxLen = 0;
static int sWarpHeld = 0;

// Debug hooks (BBFT_DEBUG_CHECK / BBFT_DEBUG_WARP), fired N ms after connect.
static char sDebugCheck[BBFT_MAX_NAME] = "";
static int sDebugWarp = 0;
static unsigned long sConnectTick = 0;
static int sDebugCheckDone = 0;
static int sDebugWarpDone = 0;

static unsigned long bbft_now_ms(void) {
    return (unsigned long) GetTickCount();
}

// Pull "--bbft-port N" (or "--bbft-port=N") out of the raw command line.
static int bbft_port_from_cmdline(void) {
    const char *cmd = GetCommandLineA();
    const char *p;
    if (cmd == NULL) {
        return 0;
    }
    p = strstr(cmd, "--bbft-port");
    if (p == NULL) {
        return 0;
    }
    p += strlen("--bbft-port");
    while (*p == ' ' || *p == '=' || *p == '\t' || *p == '"') {
        p++;
    }
    return atoi(p);
}

static void bbft_net_close(void) {
    if (sSock != INVALID_SOCKET) {
        closesocket(sSock);
        sSock = INVALID_SOCKET;
    }
    sTcpConnected = 0;
    sRxLen = 0;
    sWarpHeld = 0;
}

static int bbft_send_line(const char *line) {
    int len, sent = 0;
    if (!sTcpConnected) {
        return 0;
    }
    len = (int) strlen(line);
    while (sent < len) {
        int n = send(sSock, line + sent, len - sent, 0);
        if (n <= 0) {
            bbft_logf("TRANSPORT send failed, dropping connection");
            bbft_net_close();
            return 0;
        }
        sent += n;
    }
    return 1;
}

// Escape a string for a JSON value. Names are plain ASCII in practice.
static void bbft_json_escape(const char *in, char *out, int cap) {
    int o = 0;
    for (; *in != '\0' && o < cap - 2; in++) {
        if (*in == '"' || *in == '\\') {
            out[o++] = '\\';
        }
        out[o++] = *in;
    }
    out[o] = '\0';
}

static void bbft_json_unescape(const char *in, int len, char *out, int cap) {
    int o = 0, i;
    for (i = 0; i < len && o < cap - 1; i++) {
        if (in[i] == '\\' && i + 1 < len) {
            i++;
            switch (in[i]) {
                case 'n':
                    out[o++] = '\n';
                    break;
                case 't':
                    out[o++] = '\t';
                    break;
                default:
                    out[o++] = in[i];
                    break;
            }
        } else {
            out[o++] = in[i];
        }
    }
    out[o] = '\0';
}

// Read a JSON string starting at *p (which must point at the opening quote).
// Writes the unescaped contents to out and advances *p past the closing quote.
static int bbft_json_string(const char **p, char *out, int cap) {
    const char *s = *p;
    const char *start;
    if (*s != '"') {
        return 0;
    }
    s++;
    start = s;
    while (*s != '\0' && *s != '"') {
        if (*s == '\\' && s[1] != '\0') {
            s++;
        }
        s++;
    }
    if (*s != '"') {
        return 0;
    }
    bbft_json_unescape(start, (int) (s - start), out, cap);
    *p = s + 1;
    return 1;
}

// Find the value of a key in a conductor-authored JSON object. Returns a
// pointer just past the ':' or NULL.
static const char *bbft_json_find(const char *json, const char *key) {
    char pat[64];
    const char *p;
    snprintf(pat, sizeof(pat), "\"%s\"", key);
    p = strstr(json, pat);
    if (p == NULL) {
        return NULL;
    }
    p += strlen(pat);
    while (*p == ' ' || *p == ':') {
        p++;
    }
    return p;
}

// Parse {"items":{"Name":n,...},"locks":{"id":"Key",...}} into the live tables.
static int sRegionUnlocks = 0;
static int sPikminSkipTutorial = 0;
static int sPikminProgression = 0;
static int sSeparateCannons = 0;
int bbft_separate_cannons(void) { return sSeparateCannons; }
static int sSharedCapabilities = 0;
int bbft_shared_capabilities(void) { return sSharedCapabilities; }
static int sMarioAbilities = 0;
static int sSkulltulaChecks = 0;
int bbft_mario_abilities(void) { return sMarioAbilities; }
int bbft_skulltula_checks(void) { return sSkulltulaChecks; }
int bbft_pikmin_progression(void) { return sPikminProgression; }
int bbft_pikmin_skip_tutorial(void) { return sPikminSkipTutorial || sPikminProgression; }
int bbft_region_unlocks(void) { return sRegionUnlocks; }
static void bbft_apply_state(const char *json) {
    const char *p;
    int n;

    p = bbft_json_find(json, "separate_cannons");
    sSeparateCannons = p && (!strncmp(p, "true", 4) || *p == '1');
    p = bbft_json_find(json, "shared_capabilities");
    sSharedCapabilities = p && (!strncmp(p, "true", 4) || *p == '1');
    p = bbft_json_find(json, "mario_abilities");
    sMarioAbilities = p && (!strncmp(p, "true", 4) || *p == '1');
    p = bbft_json_find(json, "skulltula_checks");
    sSkulltulaChecks = p && (!strncmp(p, "true", 4) || *p == '1');
    p = bbft_json_find(json, "region_unlocks");
    sRegionUnlocks = p && (!strncmp(p, "true", 4) || *p == '1');
    p = bbft_json_find(json, "pikmin_progression");
    sPikminProgression = p && (!strncmp(p, "true", 4) || *p == '1');
    p = bbft_json_find(json, "pikmin_skip_tutorial");
    sPikminSkipTutorial = p && (!strncmp(p, "true", 4) || *p == '1');

    p = bbft_json_find(json, "items");
    if (p != NULL && *p == '{') {
        p++;
        n = 0;
        while (*p != '\0' && *p != '}') {
            char name[BBFT_MAX_NAME];
            if (*p == ',' || *p == ' ') {
                p++;
                continue;
            }
            if (!bbft_json_string(&p, name, sizeof(name))) {
                break;
            }
            while (*p == ' ' || *p == ':') {
                p++;
            }
            if (n < BBFT_MAX_ITEMS) {
                strncpy(sItems[n].name, name, BBFT_MAX_NAME - 1);
                sItems[n].name[BBFT_MAX_NAME - 1] = '\0';
                sItems[n].count = atoi(p);
                n++;
            }
            while (*p != '\0' && *p != ',' && *p != '}') {
                p++;
            }
        }
        sNumItems = n;
    }

    p = bbft_json_find(json, "locks");
    if (p != NULL && *p == '{') {
        p++;
        n = 0;
        while (*p != '\0' && *p != '}') {
            char id[BBFT_MAX_NAME];
            char key[BBFT_MAX_NAME];
            if (*p == ',' || *p == ' ') {
                p++;
                continue;
            }
            if (!bbft_json_string(&p, id, sizeof(id))) {
                break;
            }
            while (*p == ' ' || *p == ':') {
                p++;
            }
            if (!bbft_json_string(&p, key, sizeof(key))) {
                break;
            }
            if (n < BBFT_MAX_LOCKS) {
                strncpy(sLocks[n].id, id, BBFT_MAX_NAME - 1);
                sLocks[n].id[BBFT_MAX_NAME - 1] = '\0';
                strncpy(sLocks[n].key, key, BBFT_MAX_NAME - 1);
                sLocks[n].key[BBFT_MAX_NAME - 1] = '\0';
                n++;
            }
            while (*p == ' ') {
                p++;
            }
            if (*p == ',') {
                p++;
            }
        }
        sNumLocks = n;
    }

    p = bbft_json_find(json, "checked");
    if (p && *p == '[') {
        char checked[BBFT_MAX_CHECKS][BBFT_MAX_NAME];
        int count = 0;
        int valid = 1;
        ++p;
        while (*p && *p != ']') {
            while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') ++p;
            if (*p == ']') break;
            if (count >= BBFT_MAX_CHECKS || !bbft_json_string(&p, checked[count], BBFT_MAX_NAME)) {
                valid = 0;
                break;
            }
            ++count;
            while (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') ++p;
            if (*p == ',') ++p;
            else if (*p != ']') { valid = 0; break; }
        }
        if (valid && *p == ']') {
            memcpy(sRemoteChecks, checked, count * BBFT_MAX_NAME);
            sNumRemoteChecks = count;
        }
    }
    p = bbft_json_find(json, "ready");
    if (!p || *p == '1' || strncmp(p, "true", 4) == 0) sStateReady = 1;

    bbft_logf("STATE items=%d locks=%d", sNumItems, sNumLocks);

    {
        int i;
        for (i = 0; i < sNumLocks; i++) {
            bbft_logf("LOCK %s key=%s open=%d", sLocks[i].id, sLocks[i].key, bbft_lock(sLocks[i].id));
        }
        bbft_logf("COUNT Power Star=%d", bbft_count("Power Star"));
    }
}

// Find the target by PID locally: HWND never crosses JSON or narrows to int.
struct BbftForegroundWindow { DWORD pid; HWND hwnd; };
static BOOL CALLBACK bbft_find_foreground_window(HWND hwnd, LPARAM value) {
    struct BbftForegroundWindow *target = (struct BbftForegroundWindow *)value;
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == target->pid && IsWindowVisible(hwnd) && GetWindowTextLengthA(hwnd) > 0 &&
        GetWindow(hwnd, GW_OWNER) == NULL) {
        target->hwnd = hwnd;
        return FALSE;
    }
    return TRUE;
}

static void bbft_foreground_handoff(const char *line, int receiving) {
    const char *p = bbft_json_find(line, "handoff_id");
    unsigned long serial = p ? strtoul(p, NULL, 10) : 0;
    struct BbftForegroundWindow target;
    int ok = 0;
    char reply[160];
    if (!serial) return; // Older conductor, ordinary hold only.
    p = bbft_json_find(line, "target_pid");
    target.pid = receiving ? GetCurrentProcessId() : (p ? strtoul(p, NULL, 10) : 0);
    target.hwnd = NULL;
    if (target.pid) EnumWindows(bbft_find_foreground_window, (LPARAM)&target);
    if (target.hwnd) {
        // Do not restore an already-visible exclusive fullscreen window.
        if (IsIconic(target.hwnd)) ShowWindow(target.hwnd, SW_RESTORE);
        ok = SetForegroundWindow(target.hwnd) != 0;
    }
    if (!ok) {
        // Permission is process-specific. Source grants the destination first;
        // the destination's retry grants the conductor for the last fallback.
        p = bbft_json_find(line, "conductor_pid");
        DWORD allowed = receiving ? (p ? strtoul(p, NULL, 10) : 0) : target.pid;
        if (allowed) AllowSetForegroundWindow(allowed);
    }
    bbft_logf("FOREGROUND handoff %s target_pid=%lu", ok ? "ok" : "failed", (unsigned long)target.pid);
    snprintf(reply, sizeof(reply), "{\"t\":\"foreground_result\",\"handoff_id\":%lu,\"ok\":%d}\n", serial, ok);
    bbft_send_line(reply);
}

static void bbft_handle_line(const char *line) {
    const char *t = bbft_json_find(line, "t");
    char type[32];
    if (t == NULL || !bbft_json_string(&t, type, sizeof(type))) {
        return;
    }
    if (strcmp(type, "travel") == 0) {
        char destination[32];
        const char *value = bbft_json_find(line, "destination");
        if (value && bbft_json_string(&value, destination, sizeof(destination)) &&
            (!strcmp(destination, "bbf") || !strcmp(destination, "wf") || !strcmp(destination, "ccm") ||
             !strcmp(destination, "forest") || !strcmp(destination, "dc") || !strcmp(destination, "ice") ||
             !strcmp(destination, "jrb") || !strcmp(destination, "deku") || !strcmp(destination, "bbh") || !strcmp(destination, "fire") || !strcmp(destination, "hmc") || !strcmp(destination, "shadow") || !strcmp(destination, "lll") || !strcmp(destination, "ssl") || !strcmp(destination, "water") || !strcmp(destination, "ddd") || !strcmp(destination, "spirit") || !strcmp(destination, "sl") || !strcmp(destination, "wdw") || !strcmp(destination, "spiral") || !strcmp(destination, "ttm") || !strcmp(destination, "thi") || !strcmp(destination, "ttc") || !strcmp(destination, "rr") || !strcmp(destination, "sa") || !strcmp(destination, "pss") || !strcmp(destination, "bitdw") || !strcmp(destination, "bitfs") || !strcmp(destination, "clocktown"))) {
            strcpy(sDestination, destination);
            bbft_logf("TRAVEL %s", sDestination);
        }
    } else if (strcmp(type, "notify") == 0) {
        char text[BBFT_NOTIFY_TEXT];
        const char *value = bbft_json_find(line, "text");
        if (value && bbft_json_string(&value, text, sizeof(text))) bbft_queue_notification(text);
    } else if (strcmp(type, "state") == 0) {
        bbft_apply_state(line);
    } else if (strcmp(type, "warp_in") == 0) {
        sWarpHeld = 0;
        bbft_logf("WARP_IN");
    } else if (strcmp(type, "warp_hold") == 0) {
        bbft_foreground_handoff(line, 0);
        sWarpHeld = 1;
        bbft_logf("WARP_HOLD");
    } else if (strcmp(type, "foreground") == 0) {
        bbft_foreground_handoff(line, 1);
    } else if (strcmp(type, "ping") == 0) {
        bbft_send_line("{\"t\":\"pong\"}\n");
    }
}

static void bbft_net_connect(void) {
    struct sockaddr_in addr;
    unsigned long nb = 1;
    int one = 1;
    char hello[128];

    sNextConnectTick = bbft_now_ms() + BBFT_RECONNECT_MS;

    sSock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sSock == INVALID_SOCKET) {
        return;
    }

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short) sTcpPort);
    addr.sin_addr.s_addr = htonl(0x7F000001); // 127.0.0.1

    if (connect(sSock, (struct sockaddr *) &addr, sizeof(addr)) != 0) {
        static unsigned long sLastFailLog = 0;
        unsigned long now = bbft_now_ms();
        if (sLastFailLog == 0 || now - sLastFailLog > 10000) {
            sLastFailLog = now;
            bbft_logf("TRANSPORT connect port=%d failed err=%d", sTcpPort, WSAGetLastError());
        }
        closesocket(sSock);
        sSock = INVALID_SOCKET;
        return;
    }

    ioctlsocket(sSock, FIONBIO, &nb);
    setsockopt(sSock, IPPROTO_TCP, TCP_NODELAY, (const char *) &one, sizeof(one));

    sTcpConnected = 1;
    sRxLen = 0;
    sConnectTick = bbft_now_ms();
    bbft_logf("TRANSPORT tcp port=%d connected", sTcpPort);

    snprintf(hello, sizeof(hello), "{\"t\":\"hello\",\"game\":\"%s\",\"pid\":%lu}\n", sGameName, (unsigned long)GetCurrentProcessId());
    bbft_send_line(hello);
}

static void bbft_net_poll(void) {
    for (;;) {
        int n;

        if (sRxLen >= BBFT_RX_CAP - 1) {
            sRxLen = 0; // oversized garbage; resynchronise
        }
        n = recv(sSock, sRx + sRxLen, BBFT_RX_CAP - 1 - sRxLen, 0);
        if (n == 0) {
            bbft_logf("TRANSPORT disconnected");
            bbft_net_close();
            return;
        }
        if (n < 0) {
            if (WSAGetLastError() != WSAEWOULDBLOCK) {
                bbft_logf("TRANSPORT recv error %d", WSAGetLastError());
                bbft_net_close();
                return;
            }
            break;
        }
        sRxLen += n;
        sRx[sRxLen] = '\0';
    }

    // Drain whole lines out of the buffer.
    for (;;) {
        char *nl = (char *) memchr(sRx, '\n', sRxLen);
        int used;
        if (nl == NULL) {
            break;
        }
        *nl = '\0';
        bbft_handle_line(sRx);
        used = (int) (nl - sRx) + 1;
        memmove(sRx, sRx + used, sRxLen - used);
        sRxLen -= used;
        if (!sTcpConnected) {
            return;
        }
    }
}

static void bbft_net_init(void) {
    WSADATA wsa;
    const char *env;

    sTcpPort = bbft_port_from_cmdline();
    if (sTcpPort == 0) {
        env = getenv("BBFT_PORT");
        if (env != NULL) {
            sTcpPort = atoi(env);
        }
    }

    env = getenv("BBFT_DEBUG_CHECK");
    if (env != NULL) {
        strncpy(sDebugCheck, env, BBFT_MAX_NAME - 1);
        sDebugCheck[BBFT_MAX_NAME - 1] = '\0';
    }
    env = getenv("BBFT_DEBUG_WARP");
    sDebugWarp = (env != NULL && atoi(env) != 0);

    if (sTcpPort <= 0 || sTcpPort > 65535) {
        sTcpWanted = 0;
        bbft_logf("TRANSPORT file");
        return;
    }

    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        sTcpWanted = 0;
        bbft_logf("TRANSPORT file (WSAStartup failed)");
        return;
    }
    sTcpWanted = 1;
    sNextConnectTick = 0;
    bbft_net_connect();
    if (!sTcpConnected) {
        bbft_logf("TRANSPORT file (port %d refused, retrying)", sTcpPort);
    }
}

// Called every frame. Returns 1 if the TCP transport owns the state tables.
static int bbft_net_update(void) {
    if (!sTcpWanted) {
        return 0;
    }
    if (!sTcpConnected) {
        if (bbft_now_ms() >= sNextConnectTick) {
            bbft_net_connect();
        }
        return 0;
    }

    bbft_net_poll();

    if (sTcpConnected) {
        unsigned long since = bbft_now_ms() - sConnectTick;
        if (!sDebugCheckDone && sDebugCheck[0] != '\0' && since > 3000) {
            sDebugCheckDone = 1;
            bbft_logf("BBFT_DEBUG_CHECK firing %s", sDebugCheck);
            bbft_check(sDebugCheck);
        }
        if (!sDebugWarpDone && sDebugWarp && since > 5000) {
            sDebugWarpDone = 1;
            bbft_logf("BBFT_DEBUG_WARP firing");
            bbft_warp_out();
        }
    }
    return sTcpConnected;
}

int bbft_warp_held(void) {
    return sWarpHeld;
}

// BBFT: input focus. Both games read the same gamepad through SDL/libultraship
// regardless of window focus, so without this playing one game also drives the
// other. A game that does not own the foreground window is deaf: the pad state
// is blanked at the single point where it enters the game. Comparing the
// foreground window's owning process id against our own also covers exclusive
// fullscreen, where the window handle itself can change under us.
static int sFgKnown = 0;
static int sFgLast = 0;

int bbft_is_foreground(void) {
    HWND fg = GetForegroundWindow();
    DWORD pid = 0;
    int foreground = 0;

    if (fg != NULL) {
        GetWindowThreadProcessId(fg, &pid);
        foreground = (pid == GetCurrentProcessId());
    }

    if (!sFgKnown || foreground != sFgLast) {
        sFgKnown = 1;
        sFgLast = foreground;
        bbft_logf("INPUT %s", foreground ? "foreground" : "background");
    }
    return foreground;
}

// ---------------------------------------------------------------- public API

void bbft_transport_init(const char *game, void (*file_reset)(void), void (*file_line)(char *)) {
    if (sInited) return;
    sInited = 1;
    sGameName = game;
    sFileReset = file_reset;
    sFileLine = file_line;
    sNumItems = sNumLocks = sNumChecks = sFrameCounter = 0;
    {
        FILE *f = fopen(BBFT_LOG_FILE, "w");
        if (f) fclose(f);
    }
    bbft_logf("INIT bbft shared transport game=%s", game);
    bbft_reload_state();
    bbft_net_init();
}

void bbft_transport_update(void) {
    if (!sInited) return;
    if (!bbft_net_update() && ++sFrameCounter >= BBFT_RELOAD_INTERVAL) {
        sFrameCounter = 0;
        bbft_reload_state();
    }
}

int bbft_state_ready(void) { return sStateReady; }

int bbft_checked(const char *location_name) {
    int i;
    if (!location_name) return 0;
    for (i = 0; i < sNumChecks; ++i)
        if (!strcmp(location_name, sChecks[i])) return 1;
    for (i = 0; i < sNumRemoteChecks; ++i)
        if (!strcmp(location_name, sRemoteChecks[i])) return 1;
    return 0;
}

void bbft_check(const char *location_name) {
    int i;
    if (bbft_pikmin_skip_tutorial() && location_name && !strcmp(location_name, "Pikmin: Main Engine")) return;

    if (sTcpWanted && !sStateReady) return;
    if (sRegionUnlocks && location_name) {
        const char *access = NULL;
        if (!strncmp(location_name, "BBF:", 4)) access = "Bob-omb Battlefield Access";
        else if (!strncmp(location_name, "WF:", 3)) access = "Whomp's Fortress Access";
        else if (!strncmp(location_name, "CCM:", 4)) access = "Cool, Cool Mountain Access";
        else if (!strncmp(location_name, "JRB:", 4)) access = "Jolly Roger Bay Access";
        else if (!strncmp(location_name, "BBH:", 4)) access = "Big Boo's Haunt Access";
        else if (!strncmp(location_name, "HMC:", 4)) access = "Hazy Maze Cave Access";
        else if (!strncmp(location_name, "LLL:", 4)) access = "Lethal Lava Land Access";
        else if (!strncmp(location_name, "SSL:", 4)) access = "Shifting Sand Land Access";
        else if (!strncmp(location_name, "DDD:", 4)) access = "Dire, Dire Docks Access";
        else if (!strncmp(location_name, "MM:", 3)) access = "Clock Town Access";
        else if (!strncmp(location_name, "BITFS:", 6)) access = "Bowser in the Fire Sea Access";
        else if (!strncmp(location_name, "BITDW:", 6)) access = "Bowser in the Dark World Access";
        else if (!strncmp(location_name, "SA:", 3)) access = "Secret Aquarium Access";
        else if (!strncmp(location_name, "PSS:", 4)) access = "Princess's Secret Slide Access";
        else if (!strncmp(location_name, "RR:", 3)) access = "Rainbow Ride Access";
        else if (!strncmp(location_name, "TTC:", 4)) access = "Tick Tock Clock Access";
        else if (!strncmp(location_name, "THI:", 4)) access = "Tiny-Huge Island Access";
        else if (!strncmp(location_name, "TTM:", 4)) access = "Tall, Tall Mountain Access";
        else if (!strncmp(location_name, "WDW:", 4)) access = "Wet-Dry World Access";
        else if (!strncmp(location_name, "BK:", 3)) access = "Spiral Mountain Access";
        else if (!strncmp(location_name, "SL:", 3)) access = "Snowman's Land Access";
        else if (!strncmp(location_name, "FT:", 3)) access = "Forest Temple Access";
        else if (!strncmp(location_name, "DC:", 3)) access = "Dodongo's Cavern Access";
        else if (!strncmp(location_name, "IC:", 3)) access = "Ice Cavern Access";
        else if (!strncmp(location_name, "DT:", 3)) access = "Deku Tree Access";
        else if (!strncmp(location_name, "FIRE:", 5)) access = "Fire Temple Access";
        else if (!strncmp(location_name, "SHADOW:", 7)) access = "Shadow Temple Access";
        else if (!strncmp(location_name, "WATER:", 6)) access = "Water Temple Access";
        else if (!strncmp(location_name, "SPIRIT:", 7)) access = "Spirit Temple Access";
        else if (!strncmp(location_name, "Pikmin:", 7)) access = "Pikmin Access";
        if (access && !bbft_has(access)) return;
    }

    if (location_name == NULL || bbft_checked(location_name)) {
        return;
    }

    for (i = 0; i < sNumChecks; i++) {
        if (strcmp(sChecks[i], location_name) == 0) {
            return; // already fired this run
        }
    }

    if (sNumChecks < BBFT_MAX_CHECKS) {
        strncpy(sChecks[sNumChecks], location_name, BBFT_MAX_NAME - 1);
        sChecks[sNumChecks][BBFT_MAX_NAME - 1] = '\0';
        sNumChecks++;
    }

    bbft_logf("CHECK %s", location_name);

    {
        char esc[BBFT_MAX_NAME * 2];
        char msg[BBFT_MAX_NAME * 2 + 32];
        bbft_json_escape(location_name, esc, sizeof(esc));
        snprintf(msg, sizeof(msg), "{\"t\":\"check\",\"id\":\"%s\"}\n", esc);
        bbft_send_line(msg);
    }
}

int bbft_count(const char *item) {
    int i;
    if (item == NULL) {
        return 0;
    }
    for (i = 0; i < sNumItems; i++) {
        if (strcmp(sItems[i].name, item) == 0) {
            return sItems[i].count;
        }
    }
    return 0;
}

int bbft_has(const char *item) {
    return bbft_count(item) > 0 ||
           (item && strcmp(item, "Hookshot") == 0 && bbft_count("Longshot") > 0);
}

int bbft_lock(const char *lock_id) {
    int i;
    if (lock_id == NULL) {
        return 0;
    }
    for (i = 0; i < sNumLocks; i++) {
        if (strcmp(sLocks[i].id, lock_id) == 0) {
            return bbft_has(sLocks[i].key);
        }
    }
    return 0; // unknown lock is closed
}

void bbft_warp_out(void) {
    if (sWarpHeld) {
        return; // already held; F9 spam is a no-op
    }
    bbft_logf("WARP_OUT");
    if (bbft_send_line("{\"t\":\"warp_out\"}\n")) {
        // Freeze immediately; the conductor's warp_hold confirms and warp_in releases.
        sWarpHeld = 1;
    }
}

