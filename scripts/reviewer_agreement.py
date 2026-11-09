"""Compare two independently completed JSONL reviews against a blind packet."""

import argparse
from collections import Counter
import json
from pathlib import Path

LABELS = ("supported", "partial", "unverified")


def indexed(path):
    rows = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        row = json.loads(line)
        key = row.get("id")
        if not isinstance(key,str) or not key or key in rows:
            raise ValueError(f"{path.name} line {number}: invalid or duplicate id")
        rows[key] = row
    if not rows:
        raise ValueError(f"{path.name}: empty packet")
    return rows


def review(path, packet):
    rows = indexed(path)
    if rows.keys() != packet.keys():
        raise ValueError(f"{path.name}: missing {sorted(packet.keys()-rows.keys())}, unexpected {sorted(rows.keys()-packet.keys())}")
    for key, row in rows.items():
        if row.get("label") not in LABELS:
            raise ValueError(f"{path.name} {key}: unknown label")
        evidence = row.get("evidence")
        if evidence is None and row["label"] == "unverified":
            continue
        if not isinstance(evidence,str) or not evidence.strip() or evidence not in packet[key]["cv_passage"]:
            raise ValueError(f"{path.name} {key}: evidence must quote the CV passage")
    return rows


def compare(packet_path, first_path, second_path):
    if first_path.samefile(second_path):
        raise ValueError("Supply two separate review files")
    packet = indexed(packet_path)
    a, b = review(first_path,packet), review(second_path,packet)
    n = len(packet)
    a_counts = Counter(r["label"] for r in a.values())
    b_counts = Counter(r["label"] for r in b.values())
    disagreements = [dict(id=k,first=a[k],second=b[k]) for k in packet if a[k]["label"] != b[k]["label"]]
    observed = (n-len(disagreements))/n
    chance = sum(a_counts[l]*b_counts[l] for l in LABELS)/(n*n)
    return dict(records=n,agreement=observed,kappa=None if chance == 1 else (observed-chance)/(1-chance),
                first_label_counts=a_counts,second_label_counts=b_counts,disagreements=disagreements)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("packet","first","second"):
        parser.add_argument(arg,type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.packet,args.first,args.second),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:
        parser.exit(2,f"{exc}\n")
