// Standalone tests of the production helper: no SDL/engine/asset dependency.
#include <stdio.h>
#include <errno.h>
#include <string>
#include <filesystem>
#include <fstream>
#include <assert.h>
static int fault = 0;
static size_t checked_write(const void* p, size_t a, size_t b, FILE* f) {
    if (fault == 1) { errno = ENOSPC; return 0; }
    return fwrite(p, a, b, f);
}
static int checked_flush(FILE* f) {
    if (fault == 2) { errno = EIO; return -1; }
    return fflush(f);
}
static int checked_close(FILE* f) {
    int result = fclose(f);
    if (fault == 3) { errno = EIO; return -1; }
    return result;
}
#define PC_SETTINGS_FILE_WRITE checked_write
#define PC_SETTINGS_FILE_FLUSH checked_flush
#define PC_SETTINGS_FILE_CLOSE checked_close
#include "../pc_port/settings/pc_settings_file.h"

static void env(const std::filesystem::path& p) {
#ifdef _WIN32
    assert(SetEnvironmentVariableW(L"PIKMIN_SETTINGS_PATH", p.c_str()));
#else
    assert(setenv("PIKMIN_SETTINGS_PATH", p.c_str(), 1) == 0);
#endif
}
static std::string bytes(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
}
int main(int argc, char** argv) {
    assert(argc == 2);
    auto base = std::filesystem::absolute(argv[1]);
    assert(!std::filesystem::exists(base));
    std::filesystem::create_directories(base / "a");
    std::filesystem::create_directories(base / "b");
    auto target = base / std::filesystem::u8path("settings-\xc3\xa9.conf");
    env(target);
    PcSettingsFilePath path;
    assert(pc_settings_file_resolve("legacy.conf", &path));
    assert(pc_settings_file_commit(&path, "language=fr\n", 12));
    std::filesystem::current_path(base / "a");
    FILE* in = pc_settings_file_open(&path);
    assert(in);
    char data[32]; assert(fgets(data, sizeof(data), in)); fclose(in);
    assert(strcmp(data, "language=fr\n") == 0);
    std::filesystem::current_path(base / "b");
    PcSettingsFilePath after;
    assert(pc_settings_file_resolve("different-pin.conf", &after));
    assert(std::filesystem::path(path.value) == std::filesystem::path(after.value));
    for (fault = 1; fault <= 3; ++fault) {
        assert(!pc_settings_file_commit(&after, "changed", 7));
        assert(bytes(target) == "language=fr\n");
        assert(errno == (fault == 1 ? ENOSPC : EIO));
        for (auto& item : std::filesystem::directory_iterator(base))
            assert(item.path().filename().string().find(".tmp-") == std::string::npos);
    }
    fault = 0;
    assert(pc_settings_file_commit(&after, "language=en\n", 12));
    assert(bytes(target) == "language=en\n");
    env("relative.conf"); assert(!pc_settings_file_resolve("legacy.conf", &after));
    env(""); assert(pc_settings_file_resolve("legacy.conf", &after));
    assert(std::filesystem::path(after.value) == "legacy.conf");
    env(base / "missing" / "config.conf");
    assert(pc_settings_file_resolve("legacy.conf", &after));
    assert(!pc_settings_file_commit(&after, "new", 3));
    assert(!std::filesystem::exists(base / "b" / "legacy.conf"));
    printf("Settings helper PASS: Unicode path, cwd changes, override/pin precedence, write/flush/close failure preservation, successful retry, empty/invalid override and missing parent\n");
}
