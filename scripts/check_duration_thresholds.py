"""Check whether changing only the duration threshold changes both predictions correctly."""

import json

import torch
from train_pair_encoder import ROOT, LABELS, AutoModelForSequenceClassification, AutoTokenizer, encode


def main():
    torch.set_num_threads(4)
    cases=[json.loads(s) for s in (ROOT/"data/duration_threshold_dev.jsonl").read_text(encoding="utf-8").splitlines()]
    pairs=[dict(cv_passage=c["cv_passage"],requirement=c[key]) for c in cases for key in ("met","short")]
    report={}
    for name in ("pair-mentions-v3","pair-duration-weak"):
        path=ROOT/"runs"/name
        tokenizer=AutoTokenizer.from_pretrained(path)
        model=AutoModelForSequenceClassification.from_pretrained(path).eval()
        with torch.inference_mode():
            ids=model(**encode(pairs,tokenizer)).logits.argmax(-1).tolist()
        predictions=[dict(skill=c["skill"],met=LABELS[a],short=LABELS[b])
                     for c,a,b in zip(cases,ids[::2],ids[1::2],strict=True)]
        report[name]=dict(both_correct=sum(c["met"]=="supported" and c["short"]=="partial" for c in predictions),
                          predictions=predictions)
    (ROOT/"reports/duration-thresholds.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print({k:v["both_correct"] for k,v in report.items()})


if __name__=="__main__":
    main()
