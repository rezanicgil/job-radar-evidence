"""Single fixed-setting last-block fine-tune; test is never used for selection."""
import json
import random
import torch
from evaluate_job_ner_experience import pq, hf_hub_download, REPO, REV, spans as source_spans
from train_knowledge_spans import BASE, REVISION, ROOT, TAGS, AutoTokenizer, AutoModelForTokenClassification, prepare, batch_inputs, evaluate

def main():
    torch.manual_seed(42)
    torch.set_num_threads(4)
    rng=random.Random(42)
    seen=set(); rows={}
    for split in ("train","test"):
        path=hf_hub_download(REPO,f"data/{split}-00000-of-00001.parquet",repo_type="dataset",revision=REV)
        selected=[]
        for r in pq.read_table(path).to_pylist():
            tokens=r["tokens"]; key=tuple(w.casefold() for w in tokens)
            if not key or key in seen: continue
            seen.add(key)
            tags=["O"]*len(tokens)
            for a,b in source_spans(r["ner_tags"]):
                tags[a:b]=["B"]+["I"]*(b-a-1)
            selected.append((tokens,tags))
        rows[split]=selected
    pos=[r for r in rows["train"] if "B" in r[1]]
    training=pos+rng.sample([r for r in rows["train"] if "B" not in r[1]],2*len(pos))
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REVISION)
    model=AutoModelForTokenClassification.from_pretrained(BASE,revision=REVISION,num_labels=3,id2label=dict(enumerate(TAGS)),label2id={v:i for i,v in enumerate(TAGS)},ignore_mismatched_sizes=True)
    model.base_model.requires_grad_(False)
    model.base_model.encoder.layer[-1].requires_grad_(True)
    opt=torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],lr=5e-5)
    train=prepare(tokenizer,training)
    for epoch in range(3):
        model.train();rng.shuffle(train)
        for start in range(0,len(train),16):
            x,y=batch_inputs(train[start:start+16],tokenizer.pad_token_id)
            opt.zero_grad()
            loss=torch.nn.functional.cross_entropy(model(**x).logits.reshape(-1,3),y.flatten(),weight=torch.tensor([1.,4.,3.]))
            loss.backward();opt.step()
        print("epoch",epoch+1,flush=True)
    dest=ROOT/"runs/job-ner-experience";model.save_pretrained(dest);tokenizer.save_pretrained(dest)
    test=rows["test"]
    report=dict(dataset_revision=REV,base=BASE,base_revision=REVISION,seed=42,epochs=3,positive_sentences=len(pos),sampled_negative_sentences=2*len(pos),test_sentences=len(test),exact_spans=evaluate(model,test,prepare(tokenizer,test),tokenizer.pad_token_id))
    (ROOT/"reports/job-ner-experience-tuned.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(report,flush=True)

if __name__=="__main__": main()
