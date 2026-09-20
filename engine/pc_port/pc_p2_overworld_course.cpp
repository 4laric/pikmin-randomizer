#include "pc_p2_overworld_course.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
const char* kCourses[] = {"tutorial", "forest", "yakushima", "last"};
int gCourse = -1;
bool gRegistered = false;
int indexOf(const char* id) {
    for (int i = 0; i < 4; ++i) {
        if (!std::strcmp(id, kCourses[i])) return i;
    }
    return -1;
}
}

void pc_pikipelago_overworld_course_parse(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (!std::strcmp(argv[i], "--experimental-overworld-course")) {
            if (++i >= argc || gCourse >= 0 || indexOf(argv[i]) < 0) {
                std::fprintf(stderr, "--experimental-overworld-course requires one ID: tutorial forest yakushima last\\n");
                std::exit(2);
            }
            gCourse = indexOf(argv[i]);
        }
    }
}

int pc_pikipelago_overworld_course() { return gCourse; }

const char* pc_pikipelago_overworld_course_id() { return gCourse < 0 ? 0 : kCourses[gCourse]; }

bool pc_pikipelago_overworld_course_register() {
    if (gCourse < 0) return false;
    gRegistered = true;
    return true;
}
