"""Test adding source-linked employer history counterexamples to frozen-encoder head fitting."""
import json,re,runpy
from pathlib import Path
from difflib import SequenceMatcher
from huggingface_hub import snapshot_download
from train_duration_context_head import fit,embeddings,features,ROOT,BASE,REVISION,checked,AutoModel,AutoTokenizer,torch
from evaluate_job_ner_experience import REPO,REV,pq,hf_hub_download
from audit_duration_split_similarity import tokens
from probe_experience_context import CASES

# Reviewed in upstream train, not used as an independent validation set.
HISTORY={18:"fifty years",1982:"twenty years",2136:"50 years",2546:"five years",5552:"30 years",6094:"75 years",6173:"30 years",6912:"100 years",7070:"60 years"}
def main(paired=False):
    torch.set_num_threads(4)
    src=pq.read_table(hf_hub_download(REPO,"data/train-00000-of-00001.parquet",repo_type="dataset",revision=REV)).to_pylist()
    text=lambda i:" ".join(src[i]["tokens"])
    meta=json.loads((ROOT/"reports/duration-augmentation.json").read_text())
    train=checked(ROOT/"data/interim/duration-training-augmented.jsonl",meta["sha256"])
    ext=json.loads((ROOT/"reports/duration-implicit-external.json").read_text())["cases"]
    protected=[text(r["row_index"]) for r in ext]+[t for _,_,p,n in CASES for t in (p,n)]
    split=json.loads((ROOT/"research/duration-splits-20261110.json").read_text())
    held={e for s in ("dev","test") for e in split["splits"][s]["employers"]}
    for folder,h in split["snapshots"].items():
        protected.extend(r["text"] for r in checked(ROOT/"data/raw"/folder/"candidates.jsonl",h) if r["employer"] in held)
    contexts=[" ".join(features(r)) for r in train]; y=[int(r["kind"]=="prior_experience") for r in train]
    checks=[]
    for i,term in ([] if paired else HISTORY.items()):
        t=text(i); assert i not in {r["row_index"] for r in ext} and t.count(term)==1
        x=tokens(t); sim=max(max(SequenceMatcher(None,a,b,autojunk=False).ratio() for a,b in ((x,tokens(p)),(tokens(p),x))) for p in protected)
        assert sim<.85
        a=t.index(term);contexts.append(" ".join(features(dict(text=t,mention=dict(start=a,end=a+len(term))))));y.append(0)
        checks.append(dict(row_index=i,term=term,max_word_similarity=round(sim,3),draft_kind="employer_history"))
    mod=runpy.run_path(str(ROOT/"releases/duration-context/predict.py"));tok=AutoTokenizer.from_pretrained(BASE,revision=REVISION);enc=AutoModel.from_pretrained(BASE,revision=REVISION).eval()
    if paired:
        for line in (ROOT/"research/duration-actor-training-pairs.jsonl").read_text("utf8").splitlines():
            pair=json.loads(line)
            assert re.findall(r"\[([^\]]+)\]",pair["applicant"])==re.findall(r"\[([^\]]+)\]",pair["employer"])
            for role in ("applicant","employer"):
                t=pair[role];x=tokens(t)
                assert all(SequenceMatcher(None,x,tokens(p),autojunk=False).ratio()<.85 for p in protected)
                contexts.append(mod["context"](t));y.append(int(role=="applicant"))
            checks.append(pair)
    name="duration-actor-paired" if paired else "duration-history-candidate"
    def vectors(ts):return torch.cat([embeddings(enc,tok,ts[i:i+16]) for i in range(0,len(ts),16)])
    w,b=fit(vectors(contexts),torch.tensor(y,dtype=torch.float32))
    dest=ROOT/"runs"/name;dest.mkdir(exist_ok=True);torch.save(dict(weight=w,bias=b),dest/"head.pt")
    tests=[]
    for r in ext:
        t=text(r["row_index"]);m=re.search(r"\b(?:\d+|two) years?\b",t,re.I)
        tests.append(("external",str(r["row_index"]),t[:m.start()]+"["+m.group()+"]"+t[m.end():],r["expected"]=="prior experience"))
    for f,lang,p,n in CASES:tests.extend([(lang,f,p,True),(lang,f,n,False)])
    pred=(vectors([mod["context"](t) for _,_,t,_ in tests])@w+b>=0).tolist()
    cases=[dict(slice=s,case=i,expected=a,predicted=p) for (s,i,_,a),p in zip(tests,pred,strict=True)]
    summary={s:sum(r["expected"]==r["predicted"] for r in cases if r["slice"]==s) for s in ("external","en","tr")}
    result=dict(upstream=REPO,source_revision=REV,training_sha256=meta["sha256"],added=checks,summary=summary,cases=cases,limitations="Selected after prior diagnostic failures. Reused diagnostic is not an independent test. Upstream employer identity is not available for all rows.")
    (ROOT/"reports"/(name+".json")).write_text(json.dumps(result,indent=2)+"\n","utf8");print(summary,[(r["case"],r["predicted"]) for r in cases if r["case"] in ("3835","8391")])
if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument("--paired",action="store_true");main(cli.parse_args().paired)
