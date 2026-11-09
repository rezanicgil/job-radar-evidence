"""Build the training and development splits used in the mention experiment."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "train": ("match_training_v1", "match_contrasts_v2", "match_mentions_train"),
    "validation": ("match_challenge_dev", "match_mentions_dev"),
}
FIELDS = {"family", "requirement", "cv_passage", "label"}


def read_split(names):
    rows = [json.loads(line) for name in names
            for line in (ROOT / "data" / (name+".jsonl")).read_text(encoding="utf-8").splitlines()]
    if any(set(row) != FIELDS or not all(isinstance(v,str) and v.strip() for v in row.values()) for row in rows):
        raise ValueError("Unexpected release schema")
    groups = Counter((r["family"],r["label"]) for r in rows)
    families = {r["family"] for r in rows}
    if groups != Counter((f,l) for f in families for l in ("partial","supported","unverified")):
        raise ValueError("Pilot contents differ from the release card")
    return rows


def main():
    destination = ROOT / "releases/match-pilot"
    splits = {split:read_split(names) for split,names in SOURCES.items()}
    for field in ("family", "requirement", "cv_passage"):
        overlap = {row[field] for row in splits["train"]} & {row[field] for row in splits["validation"]}
        if overlap:
            raise ValueError(f"{field} overlaps across splits: {overlap}")
    for split, rows in splits.items():
        content = "".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows).encode("utf-8")
        (destination / (split+".jsonl")).write_bytes(content)
        print(f"{split}: {len(rows)} records, SHA-256 {hashlib.sha256(content).hexdigest()}")
    shutil.copyfile(ROOT / "LICENSE",destination / "LICENSE")
    shutil.copyfile(ROOT / "data/match_source_dev.jsonl",destination / "source_validation.jsonl")
    shutil.copyfile(ROOT / "data/match_duration_weak.jsonl",destination / "duration_weak.jsonl")
    shutil.copyfile(ROOT / "data/match_employer_training.jsonl",destination / "employer_tr.jsonl")
    cases = [json.loads(s) for s in (ROOT/"data/requirement_switch_dev.jsonl").read_text(encoding="utf-8").splitlines()]
    shutil.copyfile(ROOT/"data/match_switch_training.jsonl",destination/"requirement_switch_train.jsonl")
    shutil.copyfile(ROOT/"data/compound_evidence_dev.jsonl",destination/"compound_evidence.jsonl")
    switches = [dict(family=c["family"],cv_passage=c["cv_passage"],requirement=requirement,label=label)
                for c in cases for label,requirement in c["requirements"].items()]
    (destination/"requirement_switch.jsonl").write_bytes(
        "".join(json.dumps(r,ensure_ascii=False)+"\n" for r in switches).encode("utf-8"))


if __name__ == "__main__":
    main()
