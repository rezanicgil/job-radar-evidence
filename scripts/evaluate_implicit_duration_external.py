"""External English diagnostic for the released duration head; no training or threshold selection."""
import json,re,runpy
from pathlib import Path
from huggingface_hub import snapshot_download
from evaluate_job_ner_experience import ROOT,REPO,REV,pq,hf_hub_download,spans
from split_duration_candidates import normalized
import torch

def main():
    torch.set_num_threads(4)
    rev="ed338d59d26219b6574245aaf9488cda4dc3c5e9"
    predict=runpy.run_path(str(Path(snapshot_download("rezanicgil/job-radar-duration-context",revision=rev))/"predict.py"))["predict"]
    rows=pq.read_table(hf_hub_download(REPO,"data/train-00000-of-00001.parquet",repo_type="dataset",revision=REV)).to_pylist()
    # Assistant-reviewed binary meanings, not the upstream BIO tags.
    other={954:"licence tenure",2895:"CV history coverage",3835:"company history",7703:"contract term",8391:"company history",8979:"benefit eligibility"}
    prior={1073,1402,1915,2205,3556,4409,5509,6046,6503,6908,7390,8028}
    cases=[];texts=[]
    trained={normalized(json.loads(l)["text"]) for l in (ROOT/"data/interim/duration-training-augmented.jsonl").read_text("utf8").splitlines()}
    for i,r in enumerate(rows):
        t=" ".join(r["tokens"])
        if re.search("experien",t,re.I) or not list(spans(r["ner_tags"])) or not re.search(r"\byears?\b",t,re.I):continue
        if i in (207,942):continue # abbreviated 'exp', malformed '00 years'
        assert i in prior or i in other
        m=re.search(r"\b(?:\d+|two) years?\b",t,re.I)
        assert m and normalized(t) not in trained
        texts.append(t[:m.start()]+"["+m.group()+"]"+t[m.end():])
        cases.append(dict(row_index=i,expected="prior experience" if i in prior else "other duration",scope=other.get(i,"work history")))
    assert len(texts)==len(set(texts))==18
    for r,p in zip(cases,predict(texts),strict=True):r["predicted"]=p
    summary={k:dict(total=sum(r["expected"]==k for r in cases),correct=sum(r["expected"]==r["predicted"]==k for r in cases)) for k in ("prior experience","other duration")}
    report=dict(model_revision=rev,source=REPO,source_revision=REV,annotation="Assistant-reviewed English challenge slice from the upstream training partition; this released head was not trained on that corpus. Not representative of Turkish jobs.",summary=summary,cases=cases)
    (ROOT/"reports/duration-implicit-external.json").write_text(json.dumps(report,indent=2)+"\n","utf8");print(summary)
if __name__=="__main__":main()
