"""Evaluate train-only exact-phrase extraction of experience entities in Green et al. (2022)."""
from collections import Counter
from pathlib import Path
import json
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

REPO="tabiya/job_ner_dataset"
REV="189792d21b7d1484fd73b067b09df57e7ffc456f"
ROOT=Path(__file__).resolve().parents[1]

def spans(tags):
    for i, tag in enumerate(tags):
        if tag==10:  # B-Experience, followed by I-Experience
            j=i+1
            while j<len(tags) and tags[j]==4:
                j+=1
            yield i,j

def main():
    seen=set(); phrases=set(); audit={}; scores=Counter()
    for split in ("train","test"):
        path=hf_hub_download(REPO,f"data/{split}-00000-of-00001.parquet",repo_type="dataset",revision=REV)
        rows=pq.read_table(path).to_pylist()
        kept=positives=0
        for row in rows:
            words=tuple(w.casefold() for w in row["tokens"])
            assert len(words)==len(row["ner_tags"])
            if not words or words in seen: continue
            seen.add(words);kept+=1
            gold=set(spans(row["ner_tags"]));positives+=len(gold)
            if split=="train":
                phrases.update(words[i:j] for i,j in gold)
            else:
                pred=set(); i=0
                while i<len(words):
                    end=next((j for j in range(min(len(words),i+max_len),i,-1) if words[i:j] in phrases),None)
                    if end is None: i+=1
                    else: pred.add((i,end));i=end
                scores.update(gold=len(gold),predicted=len(pred),correct=len(gold & pred))
        audit[split]=dict(source_rows=len(rows),kept_sentences=kept,experience_spans=positives)
        if split=="train": max_len=max(map(len,phrases))
    report=dict(source=REPO,revision=REV,attribution="Green, Maynard and Lin (2022); Hugging Face conversion by Tabiya. CC BY 4.0.",
                splits=audit,unique_training_phrases=len(phrases),test_exact_span=scores,
                f1=2*scores["correct"]/(scores["gold"]+scores["predicted"]))
    (ROOT/"reports/job-ner-experience.json").write_text(json.dumps(report,indent=2)+"\n","utf8")
    print(report)

if __name__=="__main__": main()
