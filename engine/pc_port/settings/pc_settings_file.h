#ifndef PC_SETTINGS_FILE_H
#define PC_SETTINGS_FILE_H
// No constructed globals: PAL language lookup can run before main.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <stdint.h>
#include <time.h>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
// The game uses an unrelated u32 HWND in AtxStream.h. Keep the SDK's
// opaque window handle under a private name without changing the game ABI.
// Restore any caller macro exactly after importing SDK declarations.
#pragma push_macro("HWND")
#undef HWND
#define HWND PcSettingsFileWindowsHWND
#include <windows.h>
#pragma pop_macro("HWND")
#include <wchar.h>
#include <io.h>
#include <fcntl.h>
#include <sys/stat.h>
typedef wchar_t PcSettingsChar;
#else
#include <unistd.h>
#include <fcntl.h>
typedef char PcSettingsChar;
#endif

struct PcSettingsFilePath { PcSettingsChar value[32768]; };

static inline int pc_settings_file_resolve(const char* fallback, PcSettingsFilePath* path) {
#ifdef _WIN32
    SetLastError(ERROR_SUCCESS);
    DWORD length = GetEnvironmentVariableW(L"PIKMIN_SETTINGS_PATH", path->value, 32768);
    if (length >= 32768) { errno = ENAMETOOLONG; return 0; }
    if (!length) {
        DWORD error = GetLastError();
        if (error != ERROR_SUCCESS && error != ERROR_ENVVAR_NOT_FOUND) { errno = EINVAL; return 0; }
        // Existing B2 pins originate in GetCurrentDirectoryA, hence ACP, while
        // the explicit environment override above is already native UTF-16.
        if (!MultiByteToWideChar(CP_ACP, 0, fallback, -1, path->value, 32768)) {
            errno = EINVAL; return 0;
        }
        return 1; // Legacy fallback may be relative; explicit overrides may not.
    }
    const wchar_t* p = path->value;
    int drive = ((p[0] >= L'A' && p[0] <= L'Z') || (p[0] >= L'a' && p[0] <= L'z')) && p[1] == L':' && (p[2] == L'\\' || p[2] == L'/');
    int unc = p[0] == L'\\' && p[1] == L'\\' && p[2] && p[2] != L'?' && p[2] != L'.';
    if (unc) {
        const wchar_t* slash = wcschr(p + 2, L'\\');
        unc = slash && slash != p + 2 && slash[1] && wcschr(slash + 1, L'\\') != NULL;
    }
    if (!drive && !unc) { errno = EINVAL; return 0; }
    for (; *p; ++p) if (*p < 32 || *p == L'"') { errno = EINVAL; return 0; }
#else
    const char* value = getenv("PIKMIN_SETTINGS_PATH");
    int explicitPath = value && *value;
    if (!explicitPath) value = fallback;
    if (!value || strlen(value) >= sizeof(path->value)) { errno = ENAMETOOLONG; return 0; }
    if (explicitPath) {
        if (value[0] != '/') { errno = EINVAL; return 0; }
        for (const char* p = value; *p; ++p) if ((unsigned char)*p < 32 || *p == '"') { errno = EINVAL; return 0; }
    }
    strcpy(path->value, value);
#endif
    return 1;
}

static inline FILE* pc_settings_file_open(const PcSettingsFilePath* path) {
#ifdef _WIN32
    return _wfopen(path->value, L"rb");
#else
    return fopen(path->value, "rb");
#endif
}

// Checked same-directory publication. The old target is never truncated or
// deleted. File contents are synced; power-loss directory durability is not
// promised. Fault controls use this exact function with injected operations.
#ifndef PC_SETTINGS_FILE_WRITE
#define PC_SETTINGS_FILE_WRITE fwrite
#endif
#ifndef PC_SETTINGS_FILE_FLUSH
#define PC_SETTINGS_FILE_FLUSH fflush
#endif
#ifndef PC_SETTINGS_FILE_CLOSE
#define PC_SETTINGS_FILE_CLOSE fclose
#endif
static inline int pc_settings_file_commit(const PcSettingsFilePath* path, const char* text, size_t size) {
    PcSettingsChar temp[32768];
    static unsigned long sequence = 0; // Constant-initialized, used after main.
    ++sequence;
#ifdef _WIN32
    if (wcslen(path->value) > 32600) { errno = ENAMETOOLONG; return 0; }
    swprintf(temp, 32768, L"%ls.tmp-%lu-%llu-%lu", path->value, (unsigned long)GetCurrentProcessId(), (unsigned long long)GetTickCount64(), sequence);
    int fd = _wopen(temp, _O_WRONLY | _O_CREAT | _O_EXCL | _O_BINARY, _S_IREAD | _S_IWRITE);
    if (fd < 0) return 0;
    FILE* out = _fdopen(fd, "wb");
    if (!out) { int error = errno; _close(fd); _wremove(temp); errno = error; return 0; }
#else
    if (strlen(path->value) > 32600) { errno = ENAMETOOLONG; return 0; }
    snprintf(temp, sizeof(temp), "%s.tmp-%ld-%llu-%lu", path->value, (long)getpid(), (unsigned long long)time(NULL), sequence);
    int fd = open(temp, O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (fd < 0) return 0;
    FILE* out = fdopen(fd, "wb");
    if (!out) { int error = errno; close(fd); remove(temp); errno = error; return 0; }
#endif
    int error = 0;
    if (PC_SETTINGS_FILE_WRITE(text, 1, size, out) != size) error = errno ? errno : EIO;
    if (!error && PC_SETTINGS_FILE_FLUSH(out) != 0) error = errno ? errno : EIO;
#ifdef _WIN32
    if (!error && _commit(fd) != 0) error = errno ? errno : EIO;
#else
    if (!error && fsync(fd) != 0) error = errno ? errno : EIO;
#endif
    if (PC_SETTINGS_FILE_CLOSE(out) != 0 && !error) error = errno ? errno : EIO;
    if (!error) {
#ifdef _WIN32
        // One atomic replacement; never delete-old-then-rename or fall back to
        // in-place writes. MoveFileExW leaves the existing target on failure.
        if (!MoveFileExW(temp, path->value, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) error = EIO;
#else
        if (rename(temp, path->value) != 0) error = errno ? errno : EIO;
#endif
    }
    if (error) {
#ifdef _WIN32
        if (_wremove(temp) != 0) fprintf(stderr, "[PC Settings] Failed to remove owned temporary file: %d\n", errno);
#else
        if (remove(temp) != 0) fprintf(stderr, "[PC Settings] Failed to remove owned temporary file: %d\n", errno);
#endif
        errno = error;
        return 0;
    }
    return 1;
}
#endif
