"""Evaluate whole-document rankings on a pinned external CV/job dataset."""

from collections import Counter,defaultdict
import csv
from hashlib import file_digest
from itertools import combinations
import json
import math
import re

from huggingface_hub import hf_hub_download
import numpy as np
import torch
from transformers import AutoModel,AutoTokenizer
from evaluate_pooled_retrieval import BASE,REVISION,ROOT

DATASET="cnamuangtoun/resume-job-description-fit"
DATA_REV="08978e21714984bb417547d2c0f9b477f5298163"
CANDIDATE="rezanicgil/python-tr-en-retriever"
CANDIDATE_REV="5621cc7f11eac83bb1be35b849797e5dba153218"
LABEL={"No Fit":0,"Potential Fit":1,"Good Fit":2}


def read(split):
    path=hf_hub_download(DATASET,split+".csv",revision=DATA_REV,repo_type="dataset")
    with open(path,encoding="utf-8-sig",newline="") as stream:
        return [(r["resume_text"],r["job_description_text"],LABEL[r["label"]]) for r in csv.DictReader(stream)]


def ranking(rows,scores,group):
    groups=defaultdict(list)
    for row,score in zip(rows,scores,strict=True):
        groups[row[group]].append((row[2],score))
    rates=[]
    by_contrast=defaultdict(list)
    for items in groups.values():
        credit=defaultdict(list)
        for (a,x),(b,y) in combinations(items,2):
            if a==b:
                continue
            value=0.5 if x==y else float((a>b)==(x>y))
            credit[f"{min(a,b)}-{max(a,b)}"].append(value)
        total=sum(len(values) for values in credit.values())
        if total:
            rates.append(sum(map(sum,credit.values()))/total)
        for key,values in credit.items():
            by_contrast[key].append(sum(values)/len(values))
    return dict(eligible_groups=len(rates),macro_concordance=float(np.mean(rates)),
                label_contrasts={k:dict(groups=len(v),concordance=float(np.mean(v))) for k,v in sorted(by_contrast.items())})


def lexical(train,test):
    train_docs={s for r in train for s in r[:2]}
    def counts(s):
        return Counter(re.findall(r"[\w+#]+",s.casefold()))
    df=Counter()
    for text in train_docs:
        df.update(counts(text).keys())
    vectors={}
    for text in {s for r in test for s in r[:2]}:
        v={k:(1+math.log(n))*(1+math.log((len(train_docs)+1)/(df[k]+1))) for k,n in counts(text).items() if k in df}
        norm=math.sqrt(sum(w*w for w in v.values())) or 1
        vectors[text]={k:w/norm for k,w in v.items()}
    return [sum(w*vectors[j].get(k,0) for k,w in vectors[c].items()) for c,j,_ in test]


@torch.inference_mode()
def encode_documents(model,tokenizer,docs):
    chunks=[]
    owners=[]
    for i,ids in enumerate(tokenizer(docs,add_special_tokens=False,verbose=False)["input_ids"]):
        for start in range(0,len(ids),126):
            chunks.append(tokenizer.build_inputs_with_special_tokens(ids[start:start+126]))
            owners.append(i)
    totals=torch.zeros(len(docs),model.config.hidden_size)
    for start in range(0,len(chunks),24):
        tokens=tokenizer.pad({"input_ids":chunks[start:start+24]},return_tensors="pt",padding=True)
        mask=tokens.attention_mask.unsqueeze(-1)
        pooled=(model(**tokens).last_hidden_state*mask).sum(1)
        totals.index_add_(0,torch.tensor(owners[start:start+24]),pooled)
    return torch.nn.functional.normalize(totals),len(chunks)


def main():
    train,test=read("train"),read("test")
    conflicts=defaultdict(set)
    for c,j,l in train:
        conflicts[c,j].add(l)
    assert len({(c,j) for c,j,_ in test})==len(test)
    docs=sorted({s for r in test for s in r[:2]})
    index={s:i for i,s in enumerate(docs)}
    report=dict(dataset=DATASET,revision=DATA_REV,label_levels=LABEL,train=len(train),test=len(test),
                train_unique_pairs=len(conflicts),train_conflicting_pairs=sum(len(v)>1 for v in conflicts.values()),
                overlap={},results={})
    for i,name in enumerate(("cv","job")):
        a,b=({r[i] for r in rows} for rows in (train,test))
        report["overlap"][name]=dict(train=len(a),test=len(b),shared=len(a&b))
    def record(name,scores):
        report["results"][name]=dict(jobs_for_same_cv=ranking(test,scores,0),cvs_for_same_job=ranking(test,scores,1))
        print(name,{k:round(v["macro_concordance"],3) for k,v in report["results"][name].items()},flush=True)
    prior=defaultdict(list)
    for c,_,label in train:
        prior[c].append(label)
    mean_label=sum(r[2] for r in train)/len(train)
    record("training_cv_label_mean",[sum(prior[c])/len(prior[c]) if c in prior else mean_label for c,_,_ in test])
    record("tfidf_cosine",lexical(train,test))
    torch.set_num_threads(4)
    for name,model_id,revision in [("base",BASE,REVISION),("adapted",CANDIDATE,CANDIDATE_REV)]:
        local=ROOT/"runs/python-tr-retriever"
        source=local if name=="adapted" and local.is_dir() else model_id
        if source==local:
            with (local/"model.safetensors").open("rb") as stream:
                if file_digest(stream,"sha256").hexdigest()!="b26ba551d721af2c3060c0cb0a205af1a9b761a7536cca460e3ac8752bcdd21b":
                    raise ValueError("Local weights differ from the published evaluation revision")
        model=AutoModel.from_pretrained(source,revision=None if source==local else revision).eval()
        tokenizer=AutoTokenizer.from_pretrained(source,revision=None if source==local else revision)
        vec,n=encode_documents(model,tokenizer,docs)
        scores=[float(vec[index[c]]@vec[index[j]]) for c,j,_ in test]
        record(name,scores)
        report["results"][name].update(model=model_id,revision=revision,chunks=n)
    (ROOT/"reports/external-fit-ranking.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
