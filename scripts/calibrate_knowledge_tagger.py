"""Set the knowledge-tag decision bias using development annotations only."""
import json
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification
from train_knowledge_spans import ROOT,TAGS,prepare,batch_inputs,read_splits,evaluate,exact,BATCH


def word_logits(model,tokenizer,rows):
    chunks=prepare(tokenizer,rows)
    result=[[] for _ in rows]
    with torch.inference_mode():
        for i in range(0,len(chunks),BATCH):
            batch=chunks[i:i+BATCH]
            inputs,labels=batch_inputs(batch,tokenizer.pad_token_id)
            logits=model(**inputs).logits
            for j,(index,_,_) in enumerate(batch):
                result[index].append(logits[j][labels[j]!=-100])
    return [torch.cat(parts) if parts else torch.empty(0,3) for parts in result]


def main():
    torch.set_num_threads(4)
    data,_=read_splits()
    checkpoint=ROOT/"runs/knowledge-span-tagger"
    tokenizer=AutoTokenizer.from_pretrained(checkpoint)
    model=AutoModelForTokenClassification.from_pretrained(checkpoint).eval()
    logits=word_logits(model,tokenizer,data["dev"])
    grid=[]
    for off in range(-8,9):
        bias=off/4
        shift=torch.tensor([0,bias,bias])
        predictions=[[TAGS[i] for i in (word+shift).argmax(1).tolist()] for word in logits]
        grid.append(dict(bias=bias,**exact(data["dev"],predictions)))
    best=max(grid,key=lambda entry:(entry["f1"],-abs(entry["bias"])))
    with torch.no_grad():
        model.classifier.bias[1:]+=best["bias"]
    dest=ROOT/"runs/knowledge-span-calibrated"
    model.config.id2label={0:"O",1:"B-KNOWLEDGE",2:"I-KNOWLEDGE"}
    model.config.label2id={name:i for i,name in model.config.id2label.items()}
    model.save_pretrained(dest)
    tokenizer.save_pretrained(dest)
    test=evaluate(model,data["test"],prepare(tokenizer,data["test"]),tokenizer.pad_token_id)
    report=dict(dev_grid=grid,selected_bias=best["bias"],selected_dev=best,test=test)
    (ROOT/"reports/knowledge-span-calibration.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print("development",best,"test",test,flush=True)


if __name__=="__main__":
    main()
