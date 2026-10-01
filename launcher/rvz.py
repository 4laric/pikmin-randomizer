"""Convert a Dolphin RVZ (or WIA) GameCube disc image back to a plain ISO.

Standard library only. Zstandard needs Python 3.14 (compression.zstd) or the `zstandard`
package; bzip2 and LZMA/LZMA2 use bz2/lzma. GameCube images have no partitions, so the
disc is a single raw-data region stored as fixed-size groups; RVZ additionally "packs"
runs of Nintendo's junk padding as a 68-byte seed for a lagged Fibonacci generator.
Format reference: Dolphin's docs/WiaAndRvz.md and DiscIO/WIABlob.cpp (CC0 generator).
"""
import bz2
import lzma
import struct
from pathlib import Path

LFG_K, LFG_J, SEED_WORDS = 521, 32, 17
BLOCK_BYTES = LFG_K * 4
SECTOR = 0x8000
MASK32 = 0xFFFFFFFF
COMPRESSION_NAMES = {0: "none", 1: "purge", 2: "bzip2", 3: "lzma", 4: "lzma2", 5: "zstd"}


class RvzError(Exception):
    """Actionable failure; the message is complete on its own."""


def is_rvz(path):
    return bool(path) and Path(path).suffix.lower() in (".rvz", ".wia")


class LaggedFibonacci:
    """Nintendo's disc padding generator, as reconstructed by Dolphin."""

    def __init__(self):
        self.words = [0] * LFG_K
        self.position = 0
        self.block = b""

    def set_seed(self, seed):
        words = list(struct.unpack(">17I", seed))
        for i in range(SEED_WORDS, LFG_K):
            words.append((((words[i - 17] << 23) & MASK32) ^ (words[i - 16] >> 9) ^ words[i - 1]))
        # Dolphin folds the "shift by 18 instead of 16" output quirk into the state once.
        self.words = [(x & 0xFF00FFFF) | ((x >> 2) & 0x00FF0000) for x in words]
        for _ in range(4):
            self._step()
        self.position = 0
        self.block = struct.pack(">521I", *self.words)

    def _step(self):
        w = self.words
        for i in range(LFG_J):
            w[i] ^= w[i + LFG_K - LFG_J]
        for i in range(LFG_J, LFG_K):
            w[i] ^= w[i - LFG_J]

    def _advance_block(self):
        self._step()
        self.position = 0
        self.block = struct.pack(">521I", *self.words)

    def forward(self, count):
        self.position += count
        while self.position >= BLOCK_BYTES:
            self._step()
            self.position -= BLOCK_BYTES
        self.block = struct.pack(">521I", *self.words)

    def get_bytes(self, count):
        parts = []
        while count > 0:
            take = min(count, BLOCK_BYTES - self.position)
            parts.append(self.block[self.position:self.position + take])
            self.position += take
            count -= take
            if self.position == BLOCK_BYTES:
                self._advance_block()
        return b"".join(parts)


def unpack_rvz(packed, data_offset, lfg=None):
    """Expand an RVZ packed stream; data_offset is the disc offset where the group starts."""
    lfg = lfg or LaggedFibonacci()
    out = []
    pos = 0
    while pos < len(packed):
        size, = struct.unpack_from(">I", packed, pos)
        pos += 4
        if size & 0x80000000:
            size &= 0x7FFFFFFF
            lfg.set_seed(packed[pos:pos + SEED_WORDS * 4])
            pos += SEED_WORDS * 4
            lfg.forward(data_offset % SECTOR)
            out.append(lfg.get_bytes(size))
        else:
            out.append(packed[pos:pos + size])
            pos += size
        data_offset += size
    return b"".join(out)


def _zstd_decompress():
    try:
        from compression import zstd  # Python 3.14+
        return zstd.decompress
    except ImportError:
        pass
    try:
        import zstandard
        return lambda data: zstandard.ZstdDecompressor().decompressobj().decompress(data)
    except ImportError:
        return None


class Image:
    def __init__(self, path):
        self.path = Path(path)
        self.file = self.path.open("rb")
        head = self.file.read(0x48)
        if len(head) < 0x48 or head[:4] not in (b"RVZ\x01", b"WIA\x01"):
            raise RvzError(f"{self.path.name} is not an RVZ/WIA image.")
        self.rvz = head[:4] == b"RVZ\x01"
        version, compatible, disc_struct_size = struct.unpack_from(">III", head, 4)
        self.iso_size, = struct.unpack_from(">Q", head, 0x24)
        disc = self.file.read(disc_struct_size)
        (self.disc_type, self.compression, self.level, self.chunk_size) = struct.unpack_from(">IIII", disc, 0)
        self.disc_header = disc[0x10:0x90]
        n_part, part_size, part_off = struct.unpack_from(">IIQ", disc, 0x90)
        (n_raw, raw_off, raw_size, n_groups, group_off, group_size) = struct.unpack_from(">IQIIQI", disc, 0xB4)
        self.compressor_data = disc[0xD5:0xD5 + disc[0xD4]]
        if self.disc_type != 1:
            raise RvzError(f"{self.path.name} is not a GameCube image (disc type {self.disc_type}).")
        if n_part:
            raise RvzError(f"{self.path.name} has Wii partitions; only GameCube images are supported.")
        if self.compression not in COMPRESSION_NAMES or self.compression == 1:
            raise RvzError(f"{self.path.name} uses unsupported compression {self.compression}.")
        self.decompress = self._make_decompressor()
        raw = self._read_table(raw_off, raw_size, n_raw * 24)
        self.raw_entries = [struct.unpack_from(">QQII", raw, i * 24) for i in range(n_raw)]
        entry_size = 12 if self.rvz else 8
        groups = self._read_table(group_off, group_size, n_groups * entry_size)
        self.groups = []
        for i in range(n_groups):
            if self.rvz:
                off4, size, packed = struct.unpack_from(">III", groups, i * 12)
            else:
                off4, size = struct.unpack_from(">II", groups, i * 8)
                packed = 0
                size |= 0x80000000  # WIA groups always use the file's compression.
            self.groups.append((off4 * 4, size, packed))

    def close(self):
        self.file.close()

    def _make_decompressor(self):
        if self.compression == 0:
            return lambda data: data
        if self.compression == 2:
            return bz2.decompress
        if self.compression in (3, 4):
            if self.compression == 3:
                props, dict_size = self.compressor_data[0], struct.unpack("<I", self.compressor_data[1:5])[0]
                lc, rest = props % 9, props // 9
                filters = [{"id": lzma.FILTER_LZMA1, "lc": lc, "lp": rest % 5, "pb": rest // 5, "dict_size": dict_size}]
            else:
                prop = self.compressor_data[0]
                dict_size = 0xFFFFFFFF if prop == 40 else (2 | (prop & 1)) << (prop // 2 + 11)
                filters = [{"id": lzma.FILTER_LZMA2, "dict_size": dict_size}]
            return lambda data: lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=filters).decompress(data)
        zstd = _zstd_decompress()
        if zstd is None:
            raise RvzError("This image uses Zstandard. Converting it needs the bundled runtime (Python 3.14) "
                           "or the 'zstandard' package; alternatively convert the image to ISO with dolphin-tool.")
        return zstd

    def _read_table(self, offset, compressed_size, decompressed_size):
        self.file.seek(offset)
        data = self.decompress(self.file.read(compressed_size)) if self.compression else self.file.read(compressed_size)
        if len(data) < decompressed_size:
            raise RvzError(f"{self.path.name}: damaged table at offset {offset:#x}.")
        return data[:decompressed_size]

    def group_bytes(self, index, group_offset_in_data, chunk_size):
        file_offset, size_word, packed_size = self.groups[index]
        compressed = bool(size_word & 0x80000000)
        size = size_word & 0x7FFFFFFF
        if size == 0:
            return bytes(chunk_size)
        self.file.seek(file_offset)
        data = self.file.read(size)
        if compressed:
            data = self.decompress(data)
        if packed_size:
            data = unpack_rvz(data[:packed_size], group_offset_in_data)
        if len(data) < chunk_size:
            raise RvzError(f"{self.path.name}: group {index} decoded to {len(data)} bytes, expected {chunk_size}.")
        return data[:chunk_size]

    def iter_disc(self, on_progress=None):
        """Yield the raw disc bytes from offset 0 to the end of the last raw-data region."""
        produced = 0
        for data_offset, data_size, group_index, n_groups in self.raw_entries:
            skipped = data_offset % SECTOR  # The first entry starts at 0x80 but stores from 0.
            data_offset -= skipped
            data_size += skipped
            if data_offset != produced:
                raise RvzError(f"{self.path.name}: raw data regions are not contiguous.")
            for i in range(n_groups):
                offset_in_data = i * self.chunk_size
                chunk = min(self.chunk_size, data_size - offset_in_data)
                if chunk <= 0:
                    break
                yield self.group_bytes(group_index + i, offset_in_data, chunk)
                produced += chunk
                if on_progress:
                    on_progress(produced, self.iso_size)


def convert_to_iso(rvz_path, iso_path, on_progress=None):
    """Write the full ISO next to nothing else; returns the output path. Progress gets (done, total)."""
    image = Image(rvz_path)
    iso_path = Path(iso_path)
    partial = iso_path.with_name(iso_path.name + ".partial")
    try:
        with partial.open("wb") as out:
            written = 0
            for chunk in image.iter_disc(on_progress):
                out.write(chunk)
                written += len(chunk)
            if written < image.iso_size:
                out.write(bytes(image.iso_size - written))
        partial.replace(iso_path)
    finally:
        image.close()
        if partial.exists():
            partial.unlink()
    return iso_path


def describe(path):
    image = Image(path)
    try:
        game_id = image.disc_header[:6].decode("ascii", "replace")
        return dict(game_id=game_id, revision=image.disc_header[7], iso_size=image.iso_size,
                    compression=COMPRESSION_NAMES[image.compression], chunk_size=image.chunk_size, groups=len(image.groups))
    finally:
        image.close()
