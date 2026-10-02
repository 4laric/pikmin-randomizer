#include "p2_coop_fixture_input_snapshot.h"
#if defined(_WIN32)
#define NOMINMAX
#include <windows.h>
#else
#include <cstdio>
#endif

PcCoopSnapshotResult pc_coop_fixture_input_snapshot(const char* path,
    char* bytes, unsigned capacity, unsigned* count) {
    if (!path || !bytes || !count || !capacity) return PC_COOP_SNAPSHOT_IO_ERROR;
    *count = 0;
#if defined(_WIN32)
    HANDLE file = CreateFileA(path, GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, nullptr,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return PC_COOP_SNAPSHOT_MISSING;
    DWORD size = 0;
    const BOOL read = ReadFile(file, bytes, capacity, &size, nullptr);
    const BOOL closed = CloseHandle(file);
    if (!read || !closed) return PC_COOP_SNAPSHOT_IO_ERROR;
    *count = size;
#else
    FILE* file = std::fopen(path, "rb");
    if (!file) return PC_COOP_SNAPSHOT_MISSING;
    const unsigned size = static_cast<unsigned>(std::fread(bytes, 1, capacity, file));
    const bool error = std::ferror(file) != 0;
    const bool closed = std::fclose(file) == 0;
    if (error || !closed) return PC_COOP_SNAPSHOT_IO_ERROR;
    *count = size;
#endif
    return *count < capacity ? PC_COOP_SNAPSHOT_OK : PC_COOP_SNAPSHOT_TOO_LONG;
}
