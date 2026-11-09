"""Adapt the last MiniLM layer on Python documentation translations and test CV retrieval."""

from hashlib import sha256
import argparse
import json
from pathlib import Path
import random
import re
from zipfile import ZipFile

import polib
import requests
import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer

from evaluate_pooled_retrieval import BASE, REVISION, ROOT, embeddings

SOURCE = "caa8b1e08b8534a1e1344a82889fc6c820768a91"


def corpus():
    path = ROOT/"runs/python-tr.zip"
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        response = requests.get(f"https://codeload.github.com/python/python-docs-tr/zip/{SOURCE}",timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)
    seen_en,seen_tr=set(),set()
    groups={"train":[],"validation":[]}
    with ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.endswith(".po"):
                continue
            prefix,document=name.split("/",1)
            if not prefix.endswith(SOURCE):
                raise ValueError("Archive revision mismatch")
            split="validation" if int(sha256(document.encode()).hexdigest(),16)%5==0 else "train"
            for entry in polib.pofile(archive.read(name).decode("utf-8-sig")):
                if entry.obsolete or not entry.translated():
                    continue
                en,tr=[re.sub(r"\s+"," ",s).strip() for s in (entry.msgid,entry.msgstr)]
                if en==tr or not all(6<=len(s.split())<=35 for s in (en,tr)):
                    continue
                if en in seen_en or tr in seen_tr:
                    continue
                seen_en.add(en)
                seen_tr.add(tr)
                groups[split].append((document,en,tr))
    return groups


def vectorize(model,tokenizer,texts):
    return torch.cat([embeddings(model,tokenizer,texts[i:i+24]) for i in range(0,len(texts),24)])


def cv_ranks(model,tokenizer,rows):
    rows.sort(key=lambda r:sha256(r["cv_passage"].encode()).digest())
    targets=[i for i,r in enumerate(rows) if r["label"]=="supported"]
    jobs=vectorize(model,tokenizer,[rows[i]["requirement"] for i in targets])
    cvs=vectorize(model,tokenizer,[r["cv_passage"] for r in rows])
    return {rows[i]["family"]:ranking.index(i)+1 for i,ranking in zip(targets,(jobs@cvs.T).argsort(descending=True).tolist(),strict=True)}


def evaluate(model,tokenizer,heldout):
    model.eval()
    en=vectorize(model,tokenizer,[en for _,en,_ in heldout])
    tr=vectorize(model,tokenizer,[tr for _,_,tr in heldout])
    scores=en@tr.T
    expected=torch.arange(len(heldout))
    rows=[json.loads(s) for s in (ROOT/"data/match_source_dev.jsonl").read_text(encoding="utf-8").splitlines()]
    ranks=cv_ranks(model,tokenizer,rows)
    translated=[json.loads(s) for s in (ROOT/"releases/match-pilot/language_switch.jsonl").read_text(encoding="utf-8").splitlines()]
    views={}
    for job_lang in ("tr","en"):
        for cv_lang in ("tr","en"):
            subset=[r for r in translated if r["job_language"]==job_lang and r["cv_language"]==cv_lang]
            assert len(subset)==30 and len({r["cv_passage"] for r in subset})==30
            positions=cv_ranks(model,tokenizer,subset)
            views[f"{job_lang}-{cv_lang}"]=dict(top1=sum(v==1 for v in positions.values()),
                                              top3=sum(v<=3 for v in positions.values()),ranks=positions)
    return dict(en_to_tr_top1=int((scores.argmax(1)==expected).sum()),tr_to_en_top1=int((scores.argmax(0)==expected).sum()),
                cv_top1=sum(i==1 for i in ranks.values()),cv_top3=sum(i<=3 for i in ranks.values()),cv_ranks=ranks,
                cv_language_views=views)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export",action="store_true",help="Export text pairs locally and update the public source index")
    parser.add_argument("--output-dir",type=Path,help="Save a new checkpoint and its metrics here instead of the default research paths")
    args=parser.parse_args()
    if args.output_dir and args.export:
        parser.error("--output-dir cannot be combined with --export")
    if args.output_dir and args.output_dir.exists():
        if not args.output_dir.is_dir() or any(args.output_dir.iterdir()):
            parser.error("--output-dir requires a new or empty directory")
    groups=corpus()
    if args.export:
        for split,rows in groups.items():
            full=ROOT/"runs"/f"python-translations-{split}.jsonl"
            index=ROOT/"releases/match-pilot"/f"python-translation-index-{split}.jsonl"
            with full.open("w",encoding="utf-8") as local,index.open("w",encoding="utf-8") as public:
                for document,en,tr in rows:
                    record=dict(document=document,en_sha256=sha256(en.encode()).hexdigest(),
                                tr_sha256=sha256(tr.encode()).hexdigest(),
                                source=f"https://github.com/python/python-docs-tr/blob/{SOURCE}/{document}")
                    public.write(json.dumps(record)+"\n")
                    local.write(json.dumps(dict(**record,en=en,tr=tr),ensure_ascii=False)+"\n")
        return
    for split, rows in groups.items():
        path=ROOT/"releases/match-pilot"/f"python-translation-index-{split}.jsonl"
        index_rows=map(json.loads,path.read_text("utf8").splitlines())
        expected=[(r["document"],r["en_sha256"],r["tr_sha256"]) for r in index_rows]
        actual=[(document,sha256(en.encode()).hexdigest(),sha256(tr.encode()).hexdigest())
                for document,en,tr in rows]
        if actual!=expected:
            raise ValueError(f"Reconstructed {split} pairs differ from the published index")
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    model=AutoModel.from_pretrained(BASE,revision=REVISION)
    torch.manual_seed(17)
    torch.set_num_threads(4)
    train,heldout=groups["train"],groups["validation"]
    result=dict(source_revision=SOURCE,base=BASE,base_revision=REVISION,
                train_pairs=len(train),validation_pairs=len(heldout),
                documents={k:sorted({doc for doc,_,_ in rows}) for k,rows in groups.items()},
                seed=17,batch_size=16,epochs=1,learning_rate=2e-5,temperature=0.07,
                before=evaluate(model,tokenizer,heldout))
    model.requires_grad_(False)
    model.encoder.layer[-1].requires_grad_(True)
    optimizer=torch.optim.AdamW(model.encoder.layer[-1].parameters(),lr=result["learning_rate"])
    model.train()
    random.Random(17).shuffle(train)
    for start in range(0,len(train),16):
        batch=train[start:start+16]
        if len(batch)<2:
            continue
        texts=[row[1] for row in batch]+[row[2] for row in batch]
        tokens=tokenizer(texts,padding=True,truncation=True,max_length=128,return_tensors="pt")
        mask=tokens.attention_mask.unsqueeze(-1)
        vectors=F.normalize((model(**tokens).last_hidden_state*mask).sum(1)/mask.sum(1))
        left,right=vectors.chunk(2)
        scores=(left@right.T)/result["temperature"]
        gold=torch.arange(len(batch))
        loss=(F.cross_entropy(scores,gold)+F.cross_entropy(scores.T,gold))/2
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    result["after"]=evaluate(model,tokenizer,heldout)
    destination=args.output_dir or ROOT/"runs/python-tr-retriever"
    model.save_pretrained(destination)
    tokenizer.save_pretrained(destination)
    report_path=destination/"training-report.json" if args.output_dir else ROOT/"reports/translation-retrieval.json"
    report_path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="documents"}))


if __name__=="__main__":
    main()
