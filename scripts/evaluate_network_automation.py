"""Check the released clause classifier on a closed posting kept outside market totals."""
import json
import torch
from train_clause_attribution import ROOT,AutoTokenizer,AutoModelForSequenceClassification,encode,clauses

@torch.inference_mode()
def main():
    repo="rezanicgil/job-radar-clause-attribution";rev="c818969bb437370febedbfe2f5a80adac976d331"
    torch.set_num_threads(4);model=AutoModelForSequenceClassification.from_pretrained(repo,revision=rev).eval()
    tok=AutoTokenizer.from_pretrained(repo,revision=rev)
    rows=[json.loads(s) for s in (ROOT/"research/network-automation-probe.jsonl").read_text("utf8").splitlines()]
    groups={}
    for r in rows:
        pairs=[dict(requirement=r["requirement"],cv_passage=c) for c in clauses(r["cv"])]
        prob=model(**encode(pairs,tok)).logits.softmax(-1)[:,model.config.label2id["applicant"]].max().item()
        groups.setdefault(r["family"],{})[r["category"]]=prob
    hits=sum(v["direct"]>max(v["adjacent"],v["other_actor"]) for v in groups.values())
    (ROOT/"reports/network-automation-probe.json").write_text(json.dumps(dict(model=repo,revision=rev,direct_unique_first=hits,families=groups),indent=2)+"\n","utf8");print(hits,groups)
if __name__=="__main__":main()
