"""Fine-tune a bilingual encoder to locate English SkillSpan knowledge spans."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

import torch
from huggingface_hub import hf_hub_download
from transformers import AutoModelForTokenClassification,AutoTokenizer
from train_pair_encoder import BASE,REVISION,ROOT
from train_skill_sentences import DATA,VERSION

TAGS=("O","B","I")
LIMIT=128
BATCH=24


def spans(tags):
    result=[]
    start=None
    for i,tag in enumerate([*tags,"O"]):
        if tag!="I" and start is not None:
            result.append((start,i))
            start=None
        if tag=="B" or (tag=="I" and start is None):
            start=i
    return result


def read_splits():
    seen=set()
    result={}
    hashes={}
    for split in ("train","dev","test"):
        path=Path(hf_hub_download(DATA,split+".json",repo_type="dataset",revision=VERSION))
        hashes[split]=sha256(path.read_bytes()).hexdigest()
        rows=[]
        for line in path.read_text("utf8").splitlines():
            row=json.loads(line)
            key=" ".join(" ".join(row["tokens"]).casefold().split())
            if key not in seen:
                assert len(row["tokens"])==len(row["tags_knowledge"])
                rows.append((row["tokens"],row["tags_knowledge"]))
                seen.add(key)
        result[split]=rows
    return result,hashes


def prepare(tokenizer,rows):
    chunks=[]
    for i,(words,gold) in enumerate(rows):
        encoded=tokenizer(words,is_split_into_words=True,add_special_tokens=False,verbose=False)
        pieces=encoded["input_ids"]
        word_ids=encoded.word_ids()
        groups=[[] for _ in words]
        for token,w in zip(pieces,word_ids,strict=True):
            groups[w].append(token)
        ids=[]
        tags=[]
        for group,tag in zip(groups,gold,strict=True):
            if not group:
                group=[tokenizer.unk_token_id]
            if len(group)>LIMIT-2:
                raise ValueError("A word exceeds the input window")
            if len(ids)+len(group)>LIMIT-2:
                chunks.append((i,tokenizer.build_inputs_with_special_tokens(ids),[-100,*tags,-100]))
                ids,tags=[],[]
            ids.extend(group)
            tags.extend([TAGS.index(tag)]+[-100]*(len(group)-1))
        if ids:
            chunks.append((i,tokenizer.build_inputs_with_special_tokens(ids),[-100,*tags,-100]))
    return chunks


def batch_inputs(batch,pad):
    width=max(len(ids) for _,ids,_ in batch)
    ids=torch.full((len(batch),width),pad,dtype=torch.long)
    labels=torch.full_like(ids,-100)
    mask=torch.zeros_like(ids)
    for i,(_,tokens,tags) in enumerate(batch):
        ids[i,:len(tokens)]=torch.tensor(tokens)
        mask[i,:len(tokens)]=1
        labels[i,:len(tokens)]=torch.tensor(tags)
    return {"input_ids":ids,"attention_mask":mask},labels


def exact(rows,predictions):
    tp=fp=fn=0
    for (_,gold),pred in zip(rows,predictions,strict=True):
        assert len(pred)==len(gold)
        g=set(spans(gold))
        p=set(spans(pred))
        tp+=len(g&p);fp+=len(p-g);fn+=len(g-p)
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/max(1,tp+fp),recall=tp/max(1,tp+fn),f1=2*tp/max(1,2*tp+fp+fn))


def evaluate(model,rows,chunks,pad):
    predictions=[[] for _ in rows]
    model.eval()
    with torch.inference_mode():
        for i in range(0,len(chunks),BATCH):
            batch=chunks[i:i+BATCH]
            x,gold=batch_inputs(batch,pad)
            predicted=model(**x).logits.argmax(-1)
            for j,(row,_,_) in enumerate(batch):
                predictions[row].extend(model.config.id2label[k].split("-")[0] for k in predicted[j][gold[j]!=-100].tolist())
    return exact(rows,predictions)


def vocabulary_baseline(training,test):
    phrases={}
    for words,tags in training:
        for a,b in spans(tags):
            phrase=tuple(w.casefold() for w in words[a:b])
            phrases.setdefault(phrase[0],set()).add(phrase)
    lookup={w:sorted(values,key=lambda v:(-len(v),v)) for w,values in phrases.items()}
    predictions=[]
    for words,_ in test:
        words=[w.casefold() for w in words]
        tags=["O"]*len(words)
        i=0
        while i<len(words):
            match=next((v for v in lookup.get(words[i],()) if tuple(words[i:i+len(v)])==v),None)
            if match:
                tags[i:i+len(match)]=["B"]+["I"]*(len(match)-1)
                i+=len(match)
            else:i+=1
        predictions.append(tags)
    return exact(test,predictions)


def main():
    torch.manual_seed(43)
    torch.set_num_threads(4)
    rows,hashes=read_splits()
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    model=AutoModelForTokenClassification.from_pretrained(BASE,revision=REVISION,num_labels=len(TAGS),
        id2label=dict(enumerate(TAGS)),label2id={v:k for k,v in enumerate(TAGS)},ignore_mismatched_sizes=True)
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=5e-5)
    chunks={split:prepare(tokenizer,data) for split,data in rows.items()}
    freq=Counter(t for _,tags in rows["train"] for t in tags)
    loss=torch.nn.CrossEntropyLoss(weight=torch.tensor([(freq["O"]/freq[t])**0.5 for t in TAGS]))
    report=dict(dataset=DATA,data_revision=VERSION,source_hashes=hashes,base=BASE,base_revision=REVISION,
                seed=43,epochs=2,max_tokens=LIMIT,batch_size=BATCH,learning_rate=5e-5,
                train_tag_counts=freq,rows={k:len(v) for k,v in rows.items()},dev_epochs=[])
    dest=ROOT/"runs/knowledge-span-tagger"
    best=-1
    for epoch in range(2):
        model.train()
        for indices in torch.randperm(len(chunks["train"])).split(BATCH):
            x,y=batch_inputs([chunks["train"][i] for i in indices.tolist()],tokenizer.pad_token_id)
            optimizer.zero_grad()
            loss(model(**x).logits.view(-1,3),y.flatten()).backward()
            optimizer.step()
        dev=evaluate(model,rows["dev"],chunks["dev"],tokenizer.pad_token_id)
        report["dev_epochs"].append(dev)
        if dev["f1"]>best:
            best=dev["f1"];report["selected_epoch"]=epoch+1
            model.save_pretrained(dest);tokenizer.save_pretrained(dest)
        print("dev",epoch+1,dev,flush=True)
    model=AutoModelForTokenClassification.from_pretrained(dest)
    report["test"]=evaluate(model,rows["test"],chunks["test"],tokenizer.pad_token_id)
    report["memorized_phrases"]=vocabulary_baseline(rows["train"],rows["test"])
    (ROOT/"reports/knowledge-spans.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print("test",report["test"],"baseline",report["memorized_phrases"],flush=True)


if __name__=="__main__":
    main()
