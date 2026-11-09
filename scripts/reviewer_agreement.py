"""Compare two independently completed JSONL reviews against a blind packet."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

LABELS = ("supported", "partial", "unverified")


def indexed(path):
    rows = {}
    if path.is_dir():
        lines = [p.read_text(encoding="utf-8") for p in sorted(path.glob("*.json"))]
    else:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    for number, line in enumerate(lines, 1):
        row = json.loads(line)
        key = row.get("id")
        if not isinstance(key,str) or not key or key in rows:
            raise ValueError(f"{path.name} line {number}: invalid or duplicate id")
        rows[key] = row
    if not rows:
        raise ValueError(f"{path.name}: empty packet")
    return rows


def review(path, packet, packet_hash, allow_partial=False):
    rows = indexed(path)
    if rows.keys()-packet.keys() or (not allow_partial and rows.keys() != packet.keys()):
        raise ValueError(f"{path.name}: missing {sorted(packet.keys()-rows.keys())}, unexpected {sorted(rows.keys()-packet.keys())}")
    for key, row in rows.items():
        if ("packet_sha256" in row or path.is_dir()) and row.get("packet_sha256") != packet_hash:
            raise ValueError(f"{path.name} {key}: review belongs to a different packet version")
        if row.get("label") not in LABELS:
            raise ValueError(f"{path.name} {key}: unknown label")
        evidence = row.get("evidence")
        if evidence is None and row["label"] == "unverified":
            continue
        if not isinstance(evidence,str) or not evidence.strip() or evidence not in packet[key]["cv_passage"]:
            raise ValueError(f"{path.name} {key}: evidence must quote the CV passage")
    return rows


def compare(packet_path, first_path, second_path, allow_partial=False):
    if first_path.samefile(second_path):
        raise ValueError("Supply two separate review files")
    packet = indexed(packet_path)
    packet_hash = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    a = review(first_path, packet, packet_hash, allow_partial)
    b = review(second_path, packet, packet_hash, allow_partial)
    shared = a.keys() & b.keys()
    n = len(shared)
    if not n:
        raise ValueError("The reviewers did not assess any common examples")
    a_counts = Counter(a[key]["label"] for key in shared)
    b_counts = Counter(b[key]["label"] for key in shared)
    disagreements = []
    different_quotes = []
    for key, case in packet.items():
        if key not in shared:
            continue
        first, second = a[key], b[key]
        if first["label"] == second["label"] and first.get("evidence") == second.get("evidence"):
            continue
        detail = dict(id=key, requirement=case.get("requirement"), cv_passage=case["cv_passage"],
                      first=first, second=second)
        if first["label"] != second["label"]:
            disagreements.append(detail)
        else:
            different_quotes.append(detail)
    observed = (n-len(disagreements))/n
    chance = sum(a_counts[l]*b_counts[l] for l in LABELS)/(n*n)
    verified_versions = all("packet_sha256" in row for rows in (a,b) for row in rows.values())
    return dict(records=n,packet_records=len(packet),first_reviewed=len(a),second_reviewed=len(b),
                packet_sha256=packet_hash,all_review_versions_verified=verified_versions,
                agreement=observed,kappa=None if chance == 1 else (observed-chance)/(1-chance),
                first_label_counts=a_counts,second_label_counts=b_counts,disagreements=disagreements,
                same_label_different_excerpt=different_quotes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("packet","first","second"):
        parser.add_argument(arg,type=Path)
    parser.add_argument("--allow-partial",action="store_true",help="Compare only the examples both reviewers assessed")
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.packet,args.first,args.second,args.allow_partial),ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:
        parser.exit(2,f"{exc}\n")
