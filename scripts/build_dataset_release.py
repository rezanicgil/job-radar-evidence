"""Build the public pilot package from the two original training sources."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("match_training_v1.jsonl", "match_contrasts_v2.jsonl")
FIELDS = {"family", "requirement", "cv_passage", "label"}


def main():
    destination = ROOT / "releases/match-pilot"
    rows = [json.loads(line) for name in SOURCES
            for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines()]
    if any(set(row) != FIELDS or not all(isinstance(v,str) and v.strip() for v in row.values()) for row in rows):
        raise ValueError("Unexpected release schema")
    groups = Counter((r["family"],r["label"]) for r in rows)
    families = {r["family"] for r in rows}
    if len(families) != 18 or groups != Counter((f,l) for f in families for l in ("partial","supported","unverified")):
        raise ValueError("Pilot contents differ from the release card")
    content = "".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows).encode("utf-8")
    (destination / "train.jsonl").write_bytes(content)
    shutil.copyfile(ROOT / "LICENSE",destination / "LICENSE")
    print(f"{len(rows)} records, SHA-256 {hashlib.sha256(content).hexdigest()}")


if __name__ == "__main__":
    main()
