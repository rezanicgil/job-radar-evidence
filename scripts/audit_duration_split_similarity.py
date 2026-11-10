"""Audit frozen duration splits for repeated wording without inspecting held-out labels."""
from itertools import combinations
from collections import Counter
from difflib import SequenceMatcher
import json
import re
from split_duration_candidates import ROOT, digest, normalized, read
from hashlib import sha256


def tokens(text):
    words=re.findall(r"\d+(?:[.,]\d+)?|[^\W\d_]+|[+#]",normalized(text))
    numbers=set("one two three four five six seven eight nine ten bir iki üç dört beş altı yedi sekiz dokuz on".split())
    return tuple("<n>" if w[0].isdigit() or w in numbers else w for w in words)


def main():
    path=ROOT/"research/duration-splits-20261110.json"
    manifest=json.loads(path.read_text("utf8"))
    part={key:name for name,group in manifest["splits"].items() for key in group["text_sha256"]}
    texts={}
    for name,checksum in manifest["snapshots"].items():
        raw=ROOT/"data/raw"/name/"candidates.jsonl"
        assert sha256(raw.read_bytes()).hexdigest()==checksum
        for row in read(raw):texts[digest(normalized(row["text"]))]=tokens(row["text"])
    assert texts.keys()==part.keys()
    flagged=[];count=Counter()
    for a,b in combinations(sorted(texts),2):
        if part[a]==part[b]:continue
        pair="/".join(sorted([part[a],part[b]]))
        count[pair]+=1
        x,y=texts[a],texts[b]
        score=max(SequenceMatcher(None,x,y,autojunk=False).ratio(),SequenceMatcher(None,y,x,autojunk=False).ratio())
        if x==y or (min(len(x),len(y))>=5 and score>=0.85):
            flagged.append(dict(first=a,second=b,splits=pair,ratio=round(score,4),same_template=x==y))
    result=dict(manifest_sha256=sha256(path.read_bytes()).hexdigest(),pairs_checked=count,
                method="Mask numbers in digits and selected English/Turkish number words, normalize punctuation, compare ordered tokens. Flag equal templates or similarity >=0.85 with at least five tokens in each. Does not detect translations or semantic paraphrases.",
                flagged=flagged)
    excluded={key for row in flagged for key in (row["first"],row["second"]) if part[key]=="train"}
    result["exclude_from_training"]=sorted(excluded)
    eligible={key for key in texts if part[key]=="train"}-excluded
    result["eligible_training_ids"]=sorted(eligible)
    assert not any(key in eligible for row in flagged for key in (row["first"],row["second"]))
    (ROOT/"reports/duration-split-similarity.json").write_text(json.dumps(result,indent=2)+"\n","utf8")
    print(count,len(flagged),Counter(r["splits"] for r in flagged))

if __name__=="__main__":main()
