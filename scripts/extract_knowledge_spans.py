"""Extract knowledge spans with exact source offsets from one job condition."""
import argparse
import json
import re

import torch
from transformers import AutoModelForTokenClassification,AutoTokenizer
from train_knowledge_spans import ROOT,prepare,batch_inputs,spans


def predict(text,model,tokenizer):
    words=list(re.finditer(r"\w+(?:\+\+|#)?|[^\w\s]",text))
    if not words:
        return []
    tokens=[w.group() for w in words]
    chunks=prepare(tokenizer,[(tokens,["O"]*len(words))])
    predicted=[]
    with torch.inference_mode():
        for chunk in chunks:
            inputs,word_mask=batch_inputs([chunk],tokenizer.pad_token_id)
            tags=model(**inputs).logits.argmax(-1)[0]
            predicted.extend(model.config.id2label[k].split("-")[0] for k in tags[word_mask[0]!=-100].tolist())
    assert len(predicted)==len(words)
    found=[]
    for start,end in spans(predicted):
        a,b=words[start].start(),words[end-1].end()
        found.append(dict(start=a,end=b,text=text[a:b]))
    return found


def diagnostic(model,tokenizer,output=None):
    path=ROOT/"releases/match-pilot/bilingual_knowledge_spans.jsonl"
    summary={}
    cases=[]
    for line in path.read_text("utf8").splitlines():
        row=json.loads(line)
        predicted=predict(row["text"],model,tokenizer)
        truth={(s["start"],s["end"]) for s in row["knowledge_spans"]}
        assert all(row["text"][s["start"]:s["end"]]==s["text"] for s in row["knowledge_spans"])
        guessed={(s["start"],s["end"]) for s in predicted}
        counts=summary.setdefault(row["language"],dict(tp=0,fp=0,fn=0))
        counts["tp"]+=len(truth&guessed)
        counts["fp"]+=len(guessed-truth)
        counts["fn"]+=len(truth-guessed)
        cases.append(dict(family=row["family"],language=row["language"],predicted=predicted))
    for counts in summary.values():
        tp,fp,fn=counts["tp"],counts["fp"],counts["fn"]
        counts["f1"]=2*tp/max(1,2*tp+fp+fn)
    out=output or ROOT/"reports/bilingual-knowledge-spans.json"
    out.write_text(json.dumps(dict(summary=summary,cases=cases),indent=2,ensure_ascii=False)+"\n","utf8")
    return summary


def main():
    cli=argparse.ArgumentParser(description=__doc__)
    mode=cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("text",nargs="?")
    mode.add_argument("--evaluate",action="store_true")
    cli.add_argument("--checkpoint",default=str(ROOT/"runs/knowledge-span-calibrated"))
    args=cli.parse_args()
    torch.set_num_threads(4)
    revision="470f9c9b758d102170108d9f808a291d3da6752b" if args.checkpoint=="rezanicgil/job-radar-knowledge-spans" else None
    weights=AutoModelForTokenClassification.from_pretrained(args.checkpoint,revision=revision).eval()
    tokenizer=AutoTokenizer.from_pretrained(args.checkpoint,revision=revision)
    result=diagnostic(weights,tokenizer) if args.evaluate else predict(args.text,weights,tokenizer)
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    main()
