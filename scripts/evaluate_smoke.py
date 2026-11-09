"""Evaluate the local checkpoint on the synthetic development challenge."""

import json
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

ROOT = Path(__file__).resolve().parents[1]


def main():
    checkpoint = ROOT / "runs/smoke"
    data = ROOT / "data/match_challenge_dev.jsonl"
    rows = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines()]
    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    model = AutoModelForSequenceClassification.from_pretrained(checkpoint).eval()
    torch.set_num_threads(4)
    with torch.inference_mode():
        pairs = tokenizer([r["requirement"] for r in rows], [r["cv_passage"] for r in rows],
                          padding=True, truncation=True, max_length=128, return_tensors="pt")
        predictions = model(**pairs).logits.argmax(dim=1).tolist()
    for row, index in zip(rows, predictions, strict=True):
        row["prediction"] = model.config.id2label[index]
    report = dict(training=json.loads((checkpoint / "run.json").read_text(encoding="utf-8")),
                  correct=sum(r["prediction"] == r["label"] for r in rows), total=len(rows),
                  false_support=sum(r["prediction"] == "supported" and r["label"] != "supported" for r in rows),
                  examples=rows)
    target = ROOT / "reports/smoke-challenge.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(report["correct"], report["total"], report["false_support"], [r["prediction"] for r in rows])


if __name__ == "__main__":
    main()
