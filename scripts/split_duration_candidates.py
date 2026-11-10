"""Freeze label-free duration partitions; keep previously inspected employers in training."""
import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
def digest(s): return sha256(s.encode()).hexdigest()
def normalized(s): return " ".join(unicodedata.normalize("NFKC",s).casefold().split())
def read(path): return [json.loads(x) for x in path.read_text("utf8").splitlines()]

def main():
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument("snapshots",nargs="+",type=Path)
    files=cli.parse_args().snapshots
    rows=[r for p in files for r in read(p)]
    inspected={r["employer"] for name in ["duration-scope-draft-20261110.jsonl","duration-multi-scope-20261110.jsonl"] for r in read(ROOT/"research"/name)}
    groups=defaultdict(set)
    for r in rows:
        groups[r["employer"]].add(digest(normalized(r["text"])))
    components=[]
    for employer,texts in sorted(groups.items()):
        joined={employer}; shared=set(texts); keep=[]
        for names,keys in components:
            if shared & keys: joined.update(names);shared.update(keys)
            else:keep.append((names,keys))
        components=keep+[(joined,shared)]
    n=len(set.union(*groups.values()))
    buckets={s:set() for s in ("train","dev","test")}; assignments={}
    targets={"train":.70*n,"dev":.15*n,"test":.15*n}
    for names,keys in sorted(components,key=lambda c:(not bool(c[0]&inspected),-len(c[1]),sorted(c[0]))):
        split="train" if names & inspected else max(targets,key=lambda s:(s!="train" and list(assignments.values()).count(s)<2, (targets[s]-len(buckets[s]))/targets[s]))
        buckets[split].update(keys);assignments.update(dict.fromkeys(names,split))
    seen=defaultdict(set); links=defaultdict(set)
    for r in rows:
        h=digest(normalized(r["text"])); seen[h].add(assignments[r["employer"]]); links[r["source"]].add(assignments[r["employer"]])
    assert all(len(x)==1 for x in [*seen.values(),*links.values()]) and all(buckets.values())
    assert all(assignments[e]=="train" for e in inspected)
    result=dict(method="NFKC, casefold and collapse whitespace; group employers linked by identical normalized text; previously draft-labelled employers restricted to train. Near-duplicates and translations are not detected.",
                snapshots={p.parent.name:sha256(p.read_bytes()).hexdigest() for p in files},
                splits={s:dict(employers=sorted(k for k,v in assignments.items() if v==s),postings=sum(v=={s} for v in links.values()),unique_texts=len(keys),text_sha256=sorted(keys)) for s,keys in buckets.items()})
    (ROOT/"research/duration-splits-20261110.json").write_text(json.dumps(result,indent=2)+"\n","utf8")
    print([(s,len(d["employers"]),d["postings"],d["unique_texts"]) for s,d in result["splits"].items()])

if __name__=="__main__": main()
