"""Check exact recall of tracked technology names on fingerprinted Turkish job bullets."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import torch
from transformers import AutoModelForTokenClassification,AutoTokenizer

from extract_knowledge_spans import predict
from market_skills import PATTERNS, ROOT
from train_turkish_preferences import examples
from check_jobbert_spans import REPO as JOBBERT,REV as JOBBERT_REV

SNAPSHOT=ROOT/"reports/skill-mentions-2026-11-09T205322478229Z.json"
VOCABULARY=json.loads(SNAPSHOT.read_text("utf8"))["vocabulary"]

MODELS={"Job Radar":("rezanicgil/job-radar-knowledge-spans","470f9c9b758d102170108d9f808a291d3da6752b"),
        "JobBERT":(JOBBERT,JOBBERT_REV)}


def mentions(text):
    hits=sorted((m.start(),-len(m.group()),name) for name in VOCABULARY for m in PATTERNS[name].finditer(text))
    selected=[]
    for start,neg_length,name in hits:
        if not selected or start>=selected[-1]["end"]:
            selected.append(dict(start=start,end=start-neg_length,name=name))
    return selected


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapted",action="store_true",help="Include the local Turkish augmentation experiment")
    args=parser.parse_args()
    torch.set_num_threads(4)
    root=ROOT/"releases/match-pilot"
    texts={}
    rows=[]
    for board,filename in [("roof","turkish_section_index.jsonl"),("crenno","turkish_crenno_sections.jsonl")]:
        path=root/filename
        source={}
        for line in path.read_text("utf8").splitlines():
            row=json.loads(line)
            source.setdefault(row["text_sha256"],set()).add(row["source_url"])
        for text,_ in examples(path,board):
            key=sha256(text.encode()).hexdigest()
            if key in texts:
                raise ValueError("A sentence occurs on both boards")
            texts[key]=text
            rows.append(dict(employer=board,text_sha256=key,source_urls=sorted(source[key]),mentions=mentions(text)))
    index=root/"turkish_technology_mentions.jsonl"
    index.write_bytes("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows).encode())
    report=dict(index_sha256=sha256(index.read_bytes()).hexdigest(),vocabulary=VOCABULARY,sentences=len(rows),models={})
    models=dict(MODELS)
    introduced=set()
    if args.adapted:
        adaptation=json.loads((ROOT/"reports/turkish-mention-adaptation.json").read_text("utf8"))
        introduced=set(adaptation["template_technologies"])
        models["Turkish augmentation"]=(str(ROOT/"runs/turkish-mention-adapted"),None)
    for name,(repo,revision) in models.items():
        tokenizer=AutoTokenizer.from_pretrained(repo,revision=revision)
        model=AutoModelForTokenClassification.from_pretrained(repo,revision=revision).eval()
        totals={}
        cases=[]
        for row in rows:
            predicted=predict(texts[row["text_sha256"]],model,tokenizer)
            guessed={(s["start"],s["end"]) for s in predicted}
            result=[]
            for m in row["mentions"]:
                exact=(m["start"],m["end"]) in guessed
                overlap=any(a<m["end"] and b>m["start"] for a,b in guessed)
                result.append(dict(**m,exact=exact,overlap=overlap))
            for scope in ["all",row["employer"]]:
                counts=totals.setdefault(scope,Counter())
                counts.update(sentences=1,with_reference=int(bool(result)),reference=len(result),predicted=len(predicted),
                              exact=sum(m["exact"] for m in result),overlap=sum(m["overlap"] for m in result))
            if args.adapted:
                for m in result:
                    key="template_name" if m["name"] in introduced else "non_template_name"
                    totals.setdefault(key,Counter()).update(reference=1,exact=int(m["exact"]),overlap=int(m["overlap"]))
            cases.append(dict(text_sha256=row["text_sha256"],mentions=result,predicted_offsets=sorted(guessed)))
        report["models"][name]=dict(repo=repo if revision else "local research checkpoint",revision=revision,totals=totals,cases=cases)
        print(name,totals,flush=True)
    (ROOT/"reports/turkish-technology-mentions.json").write_text(json.dumps(report,indent=2)+"\n","utf8")


if __name__=="__main__":
    main()
