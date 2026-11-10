"""Leave-one-employer-out binary baseline on drafts only; never reads the dev/test labels."""
import json, math,re
from collections import Counter
from augment_duration_training import ROOT,checked,read

def features(row):
    text=row["text"]; m=row["mention"]
    left=re.findall(r"\w+",text[:m["start"]].casefold())[-10:]
    right=re.findall(r"\w+",text[m["end"]:].casefold())[:10]
    return left+["<duration>"]+right

def main():
    report=json.loads((ROOT/"reports/duration-augmentation.json").read_text())
    rows=checked(ROOT/"data/interim/duration-training-augmented.jsonl",report["sha256"])
    splits=json.loads((ROOT/"research/duration-splits-20261110.json").read_text())
    names={r["source"]:r["employer"] for s in splits["snapshots"] for r in read(ROOT/"data/raw"/s/"candidates.jsonl")}
    names.update({r["source"]:r["employer"] for r in read(ROOT/"research/auxiliary-duration-contexts-20261110.jsonl")})
    cases=[(names[r["source"]],features(r),int(r["kind"]=="prior_experience")) for r in rows]
    results={}
    for method in ("always_experience","context_words"):
        cm=[[0,0],[0,0]]
        for employer in sorted({e for e,_,_ in cases}):
            train=[r for r in cases if r[0]!=employer]
            counts=[Counter(w for _,ws,c in train if c==k for w in ws) for k in (0,1)]
            vocab=counts[0].keys()|counts[1].keys()
            for e,ws,k in cases:
                if e!=employer: continue
                scores=[sum(math.log((table[w]+1)/(table.total()+len(vocab))) for w in ws if w in vocab) for table in counts]
                pred=1 if method=="always_experience" else int(scores[1]>=scores[0])
                cm[k][pred]+=1
        results[method]=dict(confusion_actual_by_predicted=cm,balanced_accuracy=sum(cm[i][i]/sum(cm[i]) for i in (0,1))/2)
    payload=dict(labels=["other duration","prior experience"],evaluation="Exploratory employer-held-out folds within assistant-draft training data; not independent human validation.",results=results)
    (ROOT/"reports/duration-context-baseline.json").write_text(json.dumps(payload,indent=2)+"\n","utf8");print(results)

if __name__=="__main__":main()
