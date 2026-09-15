"""Write the explicit Purple direct-hit capability profile."""

from pathlib import Path


def write_profile(output: Path, adult_generators: list[int]) -> Path:
    ids = list(adult_generators)
    if len(ids) > 32 or len(set(ids)) != len(ids):
        raise ValueError("adult generator IDs must be unique (maximum 32)")
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 0xFFFFFFFF for value in ids):
        raise ValueError("adult generator ID outside uint32 range")
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "P2_PURPLE_DIRECT_1\n"
        "adult_fp36 50\n"
        f"adult_generators {len(ids)}"
        + (" " + " ".join(map(str, ids)) if ids else "")
        + "\n",
        encoding="ascii",
    )
    return output
