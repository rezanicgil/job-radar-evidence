"""Compare passage rankings locally against quotes previously selected by a reviewer."""

import argparse
import hashlib
import json
import re
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer
from evaluate_pooled_retrieval import BASE, REVISION, embeddings, terms, bm25, fuse_ranks, order as rank_scores
from review_cv import read_passages


def evidence_rows(report):
    if report.lstrip().startswith("{"):
        data=json.loads(report)
        if data.get("format")!="job-radar-review-v1":
            raise ValueError("Unknown JSON review format")
        rows=[(row["condition"],row["label"],[(q["page"],q["passage"]) for q in row["quotes"]])
              for row in data["conditions"]]
        if not rows:
            raise ValueError("The JSON review has no conditions")
        return rows
    sections=list(re.finditer(r"^([^\n]+)\nAssessment: (supported|partial|unverified|skip)$",report,re.M))
    rows=[]
    for i,section in enumerate(sections):
        end=sections[i+1].start() if i+1<len(sections) else len(report)
        quotes=[(int(page),text) for page,text in re.findall(
            r"^Page (\d+) · (.+)$",report[section.end():end],re.M)
            if not re.search(r" \| CV: [\d.]+ months · minimum: [\d.]+ months · ",text)]
        rows.append((section[1],section[2],quotes))
    if not rows:
        raise ValueError("No assessment rows in the exported review")
    return rows


def rerank_shortlist(requirement,passages,order,model,tokenizer):
    from train_clause_attribution import clauses,encode
    candidates=order[:10]
    pairs=[(i,dict(requirement=requirement,cv_passage=part)) for i in candidates
           for part in clauses(passages[i][1])]
    scores={i:float("-inf") for i in candidates}
    with torch.inference_mode():
        for start in range(0,len(pairs),24):
            batch=pairs[start:start+24]
            logits=model(**encode([row for _,row in batch],tokenizer)).logits
            values=logits.softmax(-1)[:,model.config.label2id["applicant"]].tolist()
            for (i,_),value in zip(batch,values,strict=True):
                scores[i]=max(scores[i],value)
    return sorted(candidates,key=scores.get,reverse=True)+order[len(candidates):]


def transition_counts(records,method):
    keys={(True,True):"retained",(False,True):"gained",
          (True,False):"lost",(False,False):"missed_by_both"}
    changes=dict.fromkeys(keys.values(),0)
    for row in records:
        before=row["adapted_best_rank"]<=3
        after=row[method+"_best_rank"]<=3
        changes[keys[before,after]]+=1
    return changes


def compare(cv,report,candidate,attribution=None):
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
        if name=="adapted":
            adapted_orders=orders
        for record,order,(_,_,quotes) in zip(results,orders,rows,strict=True):
            ranks=[order.index(passages.index(q))+1 for q in quotes if q in passages]
            record[name+"_best_rank"]=min(ranks,default=None)
            record[name+"_all_ranks"]=ranks
    docs=[terms(text) for _,text in passages]
    methods=["base","adapted","hybrid"]
    for record,dense_order,(q,_,quotes) in zip(results,adapted_orders,rows,strict=True):
        fused=rank_scores(fuse_ranks(dense_order,bm25(q,docs)))
        ranks=[fused.index(passages.index(p))+1 for p in quotes if p in passages]
        record["hybrid_best_rank"]=min(ranks,default=None)
        record["hybrid_all_ranks"]=ranks
    if attribution:
        from transformers import AutoModelForSequenceClassification
        model=AutoModelForSequenceClassification.from_pretrained(attribution,local_files_only=True).eval()
        tokenizer=AutoTokenizer.from_pretrained(attribution,local_files_only=True)
        for record,order,(q,_,quotes) in zip(results,adapted_orders,rows,strict=True):
            ranked=rerank_shortlist(q,passages,order,model,tokenizer)
            ranks=[ranked.index(passages.index(p))+1 for p in quotes if p in passages]
            record["reranked_best_rank"]=min(ranks,default=None)
            record["reranked_all_ranks"]=ranks
        methods.append("reranked")
    eligible=[r for r in results if r["selected_quotes"] and not r["unmatched_quotes"]]
    current_hash=hashlib.sha256(cv.read_bytes()).hexdigest()
    if report.lstrip().startswith("{"):
        prior_hash=json.loads(report)["cv"].get("sha256")
    else:
        match=re.search(r"^CV SHA256: ([a-f0-9]{64})$",report,re.M)
        prior_hash=match[1] if match else None
    return dict(cv_sha256=current_hash,review_cv_sha256=prior_hash,
                same_cv_input=current_hash==prior_hash if prior_hash else None,passages=len(passages),
                conditions=len(rows),fully_reproducible_conditions=len(eligible),
                summary={name:{f"top{k}":sum(r[name+"_best_rank"]<=k for r in eligible) for k in (1,3,10)}
                         for name in methods},
                top3_changes={name:transition_counts(eligible,name) for name in methods if name!="adapted"},
                results=results)


def render_comparison(result):
    eligible=[row for row in result["results"] if row["selected_quotes"] and not row["unmatched_quotes"]]
    lines=["# CV evidence retrieval comparison","",
           f"{len(eligible)} of {result['conditions']} conditions have a fully reproducible set of selected passages.",
           "A hit means that at least one selected passage appears within the stated rank.",
           "Other passages may also be relevant.",""]
    if result["same_cv_input"] is not True:
        lines.extend(["The review and current CV fingerprints do not match or could not be verified.",""])
    lines.extend(["| Method | First | Top 3 | Top 10 |","| --- | ---: | ---: | ---: |"])
    for method,counts in result["summary"].items():
        lines.append(f"| {method} | {counts['top1']} | {counts['top3']} | {counts['top10']} |")
    lines.extend(["","## Conditions with selected evidence outside the first ten semantic results",""])
    outside=[r for r in eligible if r["adapted_best_rank"]>10]
    lines.extend([f"- Rank {r['adapted_best_rank']} · {r['condition']}" for r in outside] or ["None."])
    for method,changes in result["top3_changes"].items():
        lines.extend(["",f"## {method} compared with the adapted encoder","",
                      f"{changes['retained']} retained · {changes['gained']} gained · {changes['lost']} lost · "
                      f"{changes['missed_by_both']} missed by both",""])
        for row in eligible:
            prior,current=row["adapted_best_rank"],row[method+"_best_rank"]
            if (prior<=3)!=(current<=3):
                lines.append(f"- {prior} → {current} · {row['condition']}")
    return "\n".join(lines)+"\n"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cv",type=Path)
    parser.add_argument("review",type=Path)
    parser.add_argument("candidate",type=Path,help="Local encoder checkpoint")
    parser.add_argument("output",type=Path,help="Private JSON report destination")
    parser.add_argument("--attribution",type=Path,help="Local clause classifier to rerank the adapted encoder's first ten passages")
    parser.add_argument("--markdown",type=Path,help="Optional private, readable comparison report")
    args=parser.parse_args()
    torch.set_num_threads(4)
    result=compare(args.cv,args.review.read_text(encoding="utf-8"),args.candidate,args.attribution)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(render_comparison(result),encoding="utf-8")
    print(result["fully_reproducible_conditions"],result["summary"])


if __name__=="__main__":
    main()
