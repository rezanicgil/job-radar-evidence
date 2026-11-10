"""Run the published linear head on fixed bilingual positive/negative duration pairs."""
import json
import runpy
from pathlib import Path
from huggingface_hub import snapshot_download
from probe_experience_context import CASES,ROOT,torch,normalize

def main():
    revision="ed338d59d26219b6574245aaf9488cda4dc3c5e9"
    snapshot=Path(snapshot_download("rezanicgil/job-radar-duration-context",revision=revision))
    local=ROOT/"releases/duration-context/predict.py"
    assert local.read_text("utf-8-sig")== (snapshot/"predict.py").read_text("utf-8-sig")
    module=runpy.run_path(str(snapshot/"predict.py"))
    torch.set_num_threads(4)
    passages=[p for _,_,pos,neg in CASES for p in (pos,neg)]
    train={normalize(json.loads(l)["text"]) for l in (ROOT/"data/interim/duration-training-augmented.jsonl").read_text("utf8").splitlines()}
    assert not train & {normalize(p) for p in passages}
    preds=iter(module["predict"](passages)); rows=[]
    for family,lang,pos,neg in CASES:
        rows.append(dict(family=family,lang=lang,experience=next(preds),other=next(preds)))
    summary={}
    for lang in ("en","tr"):
        subset=[r for r in rows if r["lang"]==lang]
        summary[lang]=dict(experience_correct=sum(r["experience"]=="prior experience" for r in subset),
            other_correct=sum(r["other"]=="other duration" for r in subset),
            pairs_both_correct=sum(r["experience"]=="prior experience" and r["other"]=="other duration" for r in subset),pairs=len(subset))
    result=dict(model_revision=revision,design="Four authored bilingual scenarios; no normalized exact overlap with the 75 training examples. Diagnostic, not a population estimate.",summary=summary,cases=rows)
    (ROOT/"reports/duration-context-bilingual.json").write_text(json.dumps(result,indent=2)+"\n","utf8")
    print(summary)
if __name__=="__main__":main()
