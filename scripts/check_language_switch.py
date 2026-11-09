"""Hold the evidence constant and vary CV and requirement language independently."""

from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def language_views():
    def load(name):
        return [json.loads(l) for l in (ROOT/"data"/name).read_text(encoding="utf-8").splitlines()]
    originals=load("match_source_dev.jsonl")
    translations={r["family"]:r for r in load("source_pair_translations.jsonl")}
    assert {row["family"] for row in originals}==translations.keys()
    for row in originals:
        t=translations[row["family"]]
        cv=t["passages"][row["label"]]
        jobs={t["job_language"]:row["requirement"]}
        jobs["tr" if t["job_language"]=="en" else "en"]=t["alternate_requirement"]
        passages={cv["cv_language"]:row["cv_passage"]}
        passages["tr" if cv["cv_language"]=="en" else "en"]=cv["alternate"]
        for jl,job in jobs.items():
            for cl,passage in passages.items():
                yield dict(family=row["family"],label=row["label"],requirement=job,cv_passage=passage,
                           job_language=jl,cv_language=cl,source_url=row["source"]["url"],
                           original=(job==row["requirement"] and passage==row["cv_passage"]))


def main():
    import torch
    from train_pair_encoder import AutoModelForSequenceClassification,AutoTokenizer,LABELS,encode
    torch.set_num_threads(4)
    rows=list(language_views())
    model_path=ROOT/"runs/pair-mentions-v3"
    model=AutoModelForSequenceClassification.from_pretrained(model_path).eval()
    tokenizer=AutoTokenizer.from_pretrained(model_path)
    with torch.inference_mode():
        for start in range(0,len(rows),16):
            batch=rows[start:start+16]
            pred=model(**encode(batch,tokenizer)).logits.argmax(1).tolist()
            for row,i in zip(batch,pred,strict=True):row["prediction"]=LABELS[i]
    reference=json.loads((ROOT/"reports/source-pairs-dev.json").read_text(encoding="utf-8"))
    predictions={(r["family"],r["label"]):r["prediction"] for r in reference["examples"]}
    original=[r for r in rows if r["original"]]
    assert len(original)==len(predictions) and all(predictions[(r["family"],r["label"])]==r["prediction"] for r in original)
    slices={}
    groups=defaultdict(list)
    for r in rows:
        groups[r["family"],r["label"]].append(r["prediction"])
    for jl in ("tr","en"):
        for cl in ("tr","en"):
            group=[r for r in rows if r["job_language"]==jl and r["cv_language"]==cl]
            slices[jl+"/"+cl]=dict(total=len(group),correct=sum(r["prediction"]==r["label"] for r in group),
                 false_full=sum(r["label"]!="supported" and r["prediction"]=="supported" for r in group))
    changed=sum(len(set(v))>1 for v in groups.values())
    report=dict(model=reference["model"],unique_pairs=len(groups),changed_across_translations=changed,
                slices_job_then_cv=slices,hashes={n:sha256((ROOT/"data"/n).read_bytes()).hexdigest()
                for n in ["match_source_dev.jsonl","source_pair_translations.jsonl"]},records=rows)
    (ROOT/"reports/language-switch.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(slices,"Changed",changed,"of",len(groups))


if __name__=="__main__":
    main()
