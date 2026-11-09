"""Fit an English unigram naive Bayes selector with a development-selected threshold."""

from collections import Counter
import json
from math import log
from pathlib import Path
import re

from huggingface_hub import hf_hub_download
from train_skill_sentences import DATA, VERSION, ROOT, metrics


def tokens(text):
    return re.findall(r"[\w+#]+",text.casefold())


def score(text,model):
    return model["bias"]+sum(model["weights"].get(word,0) for word in tokens(text))


def main():
    counts=[Counter(),Counter()]
    seen=set()
    model={}
    report={}
    for split in ("train","dev","test"):
        rows=[]
        path=Path(hf_hub_download(DATA,split+".json",repo_type="dataset",revision=VERSION))
        for line in path.read_text(encoding="utf-8").splitlines():
            row=json.loads(line)
            text=" ".join(row["tokens"])
            key=" ".join(text.casefold().split())
            if key in seen:
                continue
            seen.add(key)
            label=int(any(t!="O" for t in row["tags_skill"]+row["tags_knowledge"]))
            rows.append((text,label))
        if split=="train":
            for text,label in rows:
                counts[label].update(tokens(text))
            vocab=set(counts[0])|set(counts[1])
            denominator=[len(vocab)+c.total() for c in counts]
            positive=sum(label for _,label in rows)
            model=dict(bias=log(positive/(len(rows)-positive)),weights={
                w:log((1+counts[1][w])/denominator[1])-log((1+counts[0][w])/denominator[0])
                for w in sorted(vocab) if counts[0][w]+counts[1][w]>=5})
            continue
        truth=[label for _,label in rows]
        scores=[score(text,model) for text,_ in rows]
        if split=="dev":
            model["threshold"]=max(range(-20,21),key=lambda t:metrics(truth,[s>=t for s in scores])["f1"])
        report[split]=metrics(truth,[s>=model["threshold"] for s in scores])
    (ROOT/"runs/skill-sentence-nb.json").write_text(json.dumps(model),encoding="utf-8")
    report["threshold"]=model["threshold"]
    (ROOT/"reports/skill-sentence-nb.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(report)


if __name__=="__main__":
    main()
