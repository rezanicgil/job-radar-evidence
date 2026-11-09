"""Evaluate the published JobBERT knowledge tagger on the same word boundaries."""
import json
import torch
from transformers import AutoModelForTokenClassification,AutoTokenizer
from train_knowledge_spans import ROOT,read_splits,prepare,evaluate
from extract_knowledge_spans import diagnostic

REPO="jjzha/jobbert_knowledge_extraction"
REV="9dea9759b7e290413cb4d92e8cae338affab9be4"


def main():
    torch.set_num_threads(4)
    data,_=read_splits()
    tokenizer=AutoTokenizer.from_pretrained(REPO,revision=REV)
    model=AutoModelForTokenClassification.from_pretrained(REPO,revision=REV).eval()
    assert set(model.config.id2label.values())=={"B","I","O"}
    test=evaluate(model,data["test"],prepare(tokenizer,data["test"]),tokenizer.pad_token_id)
    bilingual=diagnostic(model,tokenizer,ROOT/"reports/jobbert-bilingual-spans.json")
    report=dict(repo=REPO,revision=REV,test=test,bilingual=bilingual)
    (ROOT/"reports/jobbert-span-reference.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(report)


if __name__=="__main__":
    main()
