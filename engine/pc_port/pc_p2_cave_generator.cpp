// Lane 41 (#480) cave-generator port: engine-linked facade over the header-only
// generator. Kept engine-free so it compiles both into the game binary and into
// the one-consumer test without dragging engine headers.
#include "pc_p2_cave_generator.h"

#include <fstream>
#include <sstream>

bool pc_p2_cave_generate_file(const std::string& table_path, int max_attempts, std::string& layout_json,
                              std::string& marker, std::string& error)
{
    std::ifstream in(table_path);
    if (!in) {
        error = "cannot open floor table: " + table_path;
        return false;
    }
    P2CaveCanonicalTable table;
    if (!p2CaveParseCanonical(in, table, error)) {
        return false;
    }
    const std::vector<std::string> violations = p2CaveValidateCanonical(table);
    if (!violations.empty()) {
        error = "floor table rejected: " + violations.front();
        return false;
    }
    P2CaveObservedLayout layout;
    int attempts = 0;
    if (!p2CaveGenerateWithRetry(table, max_attempts, layout, attempts, error)) {
        return false;
    }
    layout_json = p2CaveLayoutJson(layout);
    marker = p2CaveLayoutMarker(layout);
    return true;
}
