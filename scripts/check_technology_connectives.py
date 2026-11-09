"""Change only AND/OR in each requirement and measure the released classifier response."""

from hashlib import sha256
import json
from pathlib import Path
import runpy

import torch

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/"releases/match-pilot/technology_connectives.jsonl"
    rows=[json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
    release=runpy.run_path(str(ROOT/"releases/mentions-v3/predict.py"))
    torch.set_num_threads(4)
    model,tokenizer=release["load_research_model"](False)
    cases=[]
    for item in rows:
        present=set(item["evidenced"])
        tech=set(item["technologies"])
        assert present<=tech and len(tech)==2
        assert item["all_label"]==("supported" if present==tech else "partial" if present else "unverified")
        assert item["any_label"]==("supported" if present else "unverified")
        row=dict(family=item["family"],evidenced=item["evidenced"])
        for key in ("all","any"):
            pred=release["predict"](item["cv_passage"],item[key],model,tokenizer)
            row[key]=dict(expected=item[key+"_label"],predicted=pred["prediction"])
        cases.append(row)
    switches=[r for r in cases if r["all"]["expected"]!=r["any"]["expected"]]
    report=dict(source_sha256=sha256(path.read_bytes()).hexdigest(),model=release["REPO"],revision=release["REV"],
                families=len({r["family"] for r in rows}),passages=len(cases),comparisons=len(cases)*2,
                correct={key:sum(r[key]["expected"]==r[key]["predicted"] for r in cases) for key in ("all","any")},
                should_switch=len(switches),
                switched=sum(r["all"]["predicted"]!=r["any"]["predicted"] for r in switches),
                switched_both_correct=sum(all(r[k]["expected"]==r[k]["predicted"] for k in ("all","any")) for r in switches),
                cases=cases)
    (ROOT/"reports/technology-connectives.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print({k:v for k,v in report.items() if k!="cases"})


if __name__=="__main__":
    main()
