"""Test whether skill-list examples help distinguish mentions from delivered work."""

import hashlib
import json

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from train_pair_encoder import BASE, REVISION, LABELS, ROOT, encode, run


def main():
    torch.set_num_threads(4)
    names = ["match_training_v1", "match_contrasts_v2", "match_mentions_train",
             "match_challenge_dev", "match_mentions_dev"]
    datasets = {}
    hashes = {}
    for name in names:
        path = ROOT / "data" / (name + ".jsonl")
        datasets[name] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    training = sum((datasets[name] for name in names[:3]), [])
    dev = datasets[names[3]] + datasets[names[4]]
    assert {row["family"] for row in training}.isdisjoint(row["family"] for row in dev)
    tokenizer = AutoTokenizer.from_pretrained(ROOT / "runs/pair-v2")
    previous = AutoModelForSequenceClassification.from_pretrained(ROOT / "runs/pair-v2").eval()
    with torch.inference_mode():
        indices = previous(**encode(dev, tokenizer)).logits.argmax(1).tolist()
    current = run(training, dev, tokenizer, True, "mentions-v3")
    records = [dict(**row, split="challenge" if i < len(datasets[names[3]]) else "mention",
                    previous=LABELS[idx], adapted=prediction)
               for i, (row, idx, prediction) in enumerate(zip(dev, indices, current["predictions"], strict=True))]
    report = dict(base=BASE, revision=REVISION, training_rows=len(training), seed=17,
                  file_hashes=hashes, synthetic_development_only=True, records=records)
    (ROOT / "reports/pair-mentions-v3.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for split in ("challenge","mention"):
        rows = [r for r in records if r["split"] == split]
        for model in ("previous","adapted"):
            print(split,model,"correct",sum(r[model]==r["label"] for r in rows),
                  "false support",sum(r[model]=="supported" and r["label"]!="supported" for r in rows))


if __name__ == "__main__":
    main()
