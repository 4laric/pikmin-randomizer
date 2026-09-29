// Portable _putenv_s for the engine-free runtime tools: the MSVC/MinGW CRT
// provides it; POSIX builds (Linux CI) map it to setenv.
#pragma once
#if !defined(_WIN32)
#include <cstdlib>
static inline int _putenv_s(const char* name, const char* value)
{
    return value && *value ? setenv(name, value, 1) : unsetenv(name);
}
#endif
