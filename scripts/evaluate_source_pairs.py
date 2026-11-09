"""Evaluate the published research classifier on source-grounded synthetic cases."""

from collections import Counter
import hashlib
import json

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from train_pair_encoder import ROOT, LABELS, encode


def main():
    path=ROOT/"data/match_source_dev.jsonl"
    rows=[json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
    index=json.loads((ROOT/"research/requirement_source_index.json").read_text(encoding="utf-8"))
    sources={r["fingerprint"]:r["sources"] for r in index["review_candidates"]}
    assert all(row["source"] in sources[row["source_fingerprint"]] for row in rows)
    training=[json.loads(s) for s in (ROOT/"releases/match-pilot/train.jsonl").read_text(encoding="utf-8").splitlines()]
    for field in ("family","requirement","cv_passage"):
        assert {r[field] for r in rows}.isdisjoint(r[field] for r in training)
    model_path=ROOT/"runs/pair-mentions-v3"
    model=AutoModelForSequenceClassification.from_pretrained(model_path).eval()
    tokenizer=AutoTokenizer.from_pretrained(model_path)
    with torch.inference_mode():
        predicted=model(**encode(rows,tokenizer)).logits.argmax(1).tolist()
    counts=Counter()
    for row,label in zip(rows,predicted,strict=True):
        row["prediction"]=LABELS[label]
        counts[(row["label"],row["prediction"])]+=1
    report=dict(dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                labels=LABELS,confusion_rows_actual_columns_predicted=[[counts[(a,b)] for b in LABELS] for a in LABELS],
                model="rezanicgil/job-radar-evidence-mentions-v3@790d07e85db18780d60e2d1a7ba4a968463fe257",
                examples=rows)
    (ROOT/"reports/source-pairs-dev.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(report["labels"],report["confusion_rows_actual_columns_predicted"])


if __name__=="__main__":
    main()
