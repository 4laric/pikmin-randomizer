#ifndef P2_COOP_FIXTURE_INPUT_SNAPSHOT_H
#define P2_COOP_FIXTURE_INPUT_SNAPSHOT_H
// Engine-free byte boundary: no SDK handles or engine aliases cross this API.
enum PcCoopSnapshotResult { PC_COOP_SNAPSHOT_MISSING, PC_COOP_SNAPSHOT_OK,
    PC_COOP_SNAPSHOT_IO_ERROR, PC_COOP_SNAPSHOT_TOO_LONG };
PcCoopSnapshotResult pc_coop_fixture_input_snapshot(const char* path,
    char* bytes, unsigned capacity, unsigned* count);
#endif
