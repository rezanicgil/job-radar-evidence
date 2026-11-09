"""Evaluate fixed English/Turkish retrieval models on upstream Git localization."""
from collections import Counter,defaultdict
from hashlib import sha256
import json
import re

import polib
import requests
import torch
from transformers import AutoModel,AutoTokenizer
from check_progit_retrieval import MODELS
from train_translation_retrieval import ROOT,vectorize

REV="0a961ebf01737f50c491ce12f7be3998a7f73fd1"
DIGEST="a6b929ac2a78c2acdf3238db00558175748637f8c6bc427db0a21e79ddc2149b"
SOURCE=f"https://github.com/git/git/blob/{REV}/po/tr.po"


def digest(text):
    return sha256(text.encode()).hexdigest()


def pairs():
    path=ROOT/"runs/git-tr-0a961eb.po"
    if not path.exists():
        response=requests.get(f"https://raw.githubusercontent.com/git/git/{REV}/po/tr.po",timeout=30)
        response.raise_for_status()
        path.write_bytes(response.content)
    if sha256(path.read_bytes()).hexdigest()!=DIGEST:
        raise ValueError("Git catalog digest mismatch")
    excluded=set()
    for filename in ("python-translation-index-train.jsonl","python-translation-index-validation.jsonl",
                     "progit_section_index.jsonl"):
        for line in (ROOT/"releases/match-pilot"/filename).read_text("utf8").splitlines():
            row=json.loads(line)
            excluded.update((row["en_sha256"],row["tr_sha256"]))
    catalog=polib.pofile(str(path))
    candidates=[]
    for entry in catalog:
        if entry.obsolete or not entry.translated() or entry.msgid_plural:continue
        en,tr=entry.msgid,entry.msgstr
        if any("\n" in s or "%" in s for s in (en,tr)):continue
        en,tr=[" ".join(s.split()) for s in (en,tr)]
        if en.casefold()==tr.casefold() or not all(3<=len(s.split())<=24 for s in (en,tr)):continue
        if {digest(en),digest(tr)} & excluded:continue
        candidates.append((entry.linenum,en,tr))
    en_counts=Counter(en.casefold() for _,en,_ in candidates)
    tr_counts=Counter(tr.casefold() for _,_,tr in candidates)
    rows=[r for r in candidates if en_counts[r[1].casefold()]==tr_counts[r[2].casefold()]==1]
    return sorted(rows,key=lambda r:digest(r[1])),len(catalog)


def ranks(query,candidates):
    result=[]
    for i in range(0,len(query),128):
        scores=query[i:i+128]@candidates.T
        target=scores[torch.arange(len(scores)),torch.arange(i,i+len(scores))]
        result.extend((scores>=target[:,None]).sum(1).tolist())
    return result


def lexical_baseline(corpus):
    tokens=lambda text:set(re.findall(r"[\w+#]+",text.casefold()))
    views={}
    for label,source,target in [("en-tr",1,2),("tr-en",2,1)]:
        lookup=defaultdict(list)
        for i,row in enumerate(corpus):
            for token in tokens(row[target]):
                lookup[token].append(i)
        found=Counter()
        for i,row in enumerate(corpus):
            scores=Counter(j for token in tokens(row[source]) for j in lookup[token])
            if scores[i]:
                rank=sum(s>=scores[i] for s in scores.values())
                for k in (1,3,10):
                    found[k]+=rank<=k
        views[label]={f"top{k}":found[k] for k in (1,3,10)}
    return views


def main():
    torch.set_num_threads(4)
    corpus,total=pairs()
    corpus_index=[dict(line=line,en_sha256=digest(en),tr_sha256=digest(tr),source=f"{SOURCE}#L{line}")
                  for line,en,tr in corpus]
    index=ROOT/"releases/match-pilot/git_localization_index.jsonl"
    index.write_bytes("".join(json.dumps(row)+"\n" for row in corpus_index).encode())
    report=dict(revision=REV,catalog_sha256=DIGEST,catalog_entries=total,pairs=len(corpus),
                index_sha256=sha256(index.read_bytes()).hexdigest(),shared_words=lexical_baseline(corpus),methods={})
    per_pair_ranks={}
    for method,repo,revision in MODELS:
        model=AutoModel.from_pretrained(repo,revision=revision).eval()
        tokenizer=AutoTokenizer.from_pretrained(repo,revision=revision)
        en=vectorize(model,tokenizer,[r[1] for r in corpus])
        tr=vectorize(model,tokenizer,[r[2] for r in corpus])
        views={}
        for label,query,candidates in [("en-tr",en,tr),("tr-en",tr,en)]:
            positions=ranks(query,candidates)
            per_pair_ranks[method,label]=positions
            views[label]={f"top{k}":sum(p<=k for p in positions) for k in (1,3,10)}
        report["methods"][method]=dict(repo=repo,revision=revision,views=views)
        print(method,len(corpus),views,flush=True)
    for label in ("en-tr","tr-en"):
        pairs_of_ranks=list(zip(per_pair_ranks["base",label],per_pair_ranks["adapted",label],strict=True))
        report.setdefault("top3_changes",{})[label]=dict(gained=sum(x>3>=y for x,y in pairs_of_ranks),
                                                        lost=sum(y>3>=x for x,y in pairs_of_ranks))
    (ROOT/"reports/git-localization-retrieval.json").write_text(json.dumps(report,indent=2)+"\n","utf8")


if __name__=="__main__":
    main()
