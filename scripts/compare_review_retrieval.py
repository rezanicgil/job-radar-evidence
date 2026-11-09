"""Compare passage rankings locally against quotes previously selected by a reviewer."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer
from evaluate_pooled_retrieval import BASE, REVISION, embeddings
from review_cv import read_passages


def evidence_rows(report):
    sections=list(re.finditer(r"^([^\n]+)\nAssessment: (supported|partial|unverified|skip)$",report,re.M))
    rows=[]
    for i,section in enumerate(sections):
        end=sections[i+1].start() if i+1<len(sections) else len(report)
        quotes=[(int(page),text) for page,text in re.findall(
            r"^Page (\d+) · (.+)$",report[section.end():end],re.M)]
        rows.append((section[1],section[2],quotes))
    if not rows:
        raise ValueError("No assessment rows in the exported review")
    return rows


def compare(cv,report,candidate):
    rows=evidence_rows(report)
    passages=list(dict.fromkeys(read_passages(cv)))
    texts=[r[0] for r in rows]+[text for _,text in passages]
    results=[dict(condition=q,assessment=label,selected_quotes=len(quotes),
                  unmatched_quotes=sum(pair not in passages for pair in quotes)) for q,label,quotes in rows]
    for name,checkpoint,revision in [("base",BASE,REVISION),("adapted",candidate,None)]:
        model=AutoModel.from_pretrained(checkpoint,revision=revision,local_files_only=True).eval()
        tokenizer=AutoTokenizer.from_pretrained(checkpoint,revision=revision,local_files_only=True)
        vectors=torch.cat([embeddings(model,tokenizer,texts[i:i+24]) for i in range(0,len(texts),24)])
        orders=(vectors[:len(rows)]@vectors[len(rows):].T).argsort(descending=True).tolist()
        for record,order,(_,_,quotes) in zip(results,orders,rows,strict=True):
            ranks=[order.index(passages.index(q))+1 for q in quotes if q in passages]
            record[name+"_best_rank"]=min(ranks,default=None)
            record[name+"_all_ranks"]=ranks
    eligible=[r for r in results if r["selected_quotes"] and not r["unmatched_quotes"]]
    return dict(cv_sha256=hashlib.sha256(cv.read_bytes()).hexdigest(),passages=len(passages),
                conditions=len(rows),fully_reproducible_conditions=len(eligible),
                summary={name:{f"top{k}":sum(r[name+"_best_rank"]<=k for r in eligible) for k in (1,3)}
                         for name in ("base","adapted")},results=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cv",type=Path)
    parser.add_argument("review",type=Path)
    parser.add_argument("candidate",type=Path,help="Local encoder checkpoint")
    parser.add_argument("output",type=Path,help="Private JSON report destination")
    args=parser.parse_args()
    torch.set_num_threads(4)
    result=compare(args.cv,args.review.read_text(encoding="utf-8"),args.candidate)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(result["fully_reproducible_conditions"],result["summary"])


if __name__=="__main__":
    main()
