"""Record a blind review locally. Run again with the same directory to resume."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from reviewer_agreement import LABELS, indexed


def decision(row):
    print(f"\n{row['id']}\nRequirement: {row['requirement']}\nCV: {row['cv_passage']}")
    while True:
        label = input("Choose supported, partial, unverified or quit: ").strip().lower()
        if label == "quit":
            return None
        if label in LABELS:
            break
    while True:
        evidence = input("Quote the deciding CV text (empty allowed for unverified): ").strip()
        if evidence and evidence in row["cv_passage"]:
            break
        if not evidence and label == "unverified":
            break
        print("Use an exact quote from the CV passage.")
    return dict(id=row["id"], label=label, evidence=evidence or None)


def main(packet_path, destination):
    packet = indexed(packet_path)
    destination.mkdir(parents=True, exist_ok=True)
    packet_hash = hashlib.sha256(packet_path.read_bytes()).hexdigest()
    for key, row in packet.items():
        filename = hashlib.sha256(key.encode()).hexdigest() + ".json"
        path = destination / filename
        if path.exists():
            saved = json.loads(path.read_text(encoding="utf-8"))
            if saved.get("packet_sha256") != packet_hash:
                raise ValueError("Packet changed. Choose a new review directory.")
            continue
        answer = decision(row)
        if answer is None:
            return
        answer["packet_sha256"] = packet_hash
        with NamedTemporaryFile(dir=destination, delete=False) as file:
            temp = Path(file.name)
            file.write(json.dumps(answer,ensure_ascii=False).encode("utf-8"))
        try:
            os.link(temp,path)
        finally:
            temp.unlink()
        print("Saved.")
    print(f"Review complete: {len(packet)} decisions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet",type=Path)
    parser.add_argument("directory",type=Path)
    args = parser.parse_args()
    try:
        main(args.packet,args.directory)
    except (EOFError,KeyboardInterrupt):
        parser.exit(0,"\nReview interrupted. Completed decisions are saved.\n")
    except (ValueError,OSError) as error:
        parser.exit(2,f"{error}\n")
