"""Stage the free Hugging Face Static Space with its dated market snapshot."""

from hashlib import sha256
import json
import shutil
import tempfile
from pathlib import Path
from market_inventory import ROOT, PATTERNS, observation_date
from market_history import daily_history


def main():
    root = ROOT / "runs"
    root.mkdir(exist_ok=True)
    dest = Path(tempfile.mkdtemp(prefix="static-space-", dir=root))
    shutil.copytree(ROOT / "releases/static-space",dest,dirs_exist_ok=True)
    shutil.copyfile(ROOT / "LICENSE",dest / "LICENSE")
    shutil.copyfile(ROOT / "research/source_grounded_candidates.jsonl",dest / "review-packet.jsonl")
    git_cases=[]
    for line in (ROOT/"releases/match-pilot/git_evidence_transfer.jsonl").read_text(encoding="utf8").splitlines():
        row=json.loads(line)
        for job,cv in [("en","tr"),("tr","en")]:
            pair=dict(requirement=row["requirement_"+job],cv_passage=row["cv_"+cv])
            case_id=sha256(json.dumps(pair,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
            git_cases.append(dict(id=case_id,**pair))
    assert len({r["id"] for r in git_cases})==len(git_cases)
    (dest/"git-review-packet.jsonl").write_bytes("".join(json.dumps(r,ensure_ascii=False)+"\n"
        for r in sorted(git_cases,key=lambda r:r["id"])).encode())
    shutil.copyfile(ROOT / "reports/source-pairs-dev.json",dest / "model-examples.json")
    shutil.copyfile(ROOT / "reports/language-switch.json",dest / "model-languages.json")
    knowledge=json.loads((ROOT/"reports/bilingual-knowledge-spans.json").read_text("utf8"))
    examples=[json.loads(line) for line in (ROOT/"releases/match-pilot/bilingual_knowledge_spans.jsonl").read_text("utf8").splitlines()]
    predictions={(r["family"],r["language"]):r["predicted"] for r in knowledge["cases"]}
    reference=json.loads((ROOT/"reports/jobbert-bilingual-spans.json").read_text("utf8"))
    jobbert={(r["family"],r["language"]):r["predicted"] for r in reference["cases"]}
    for row in examples:
        key=(row["family"],row["language"])
        row["predicted"]=predictions[key]
        row["jobbert"]=jobbert[key]
    (dest/"knowledge-examples.json").write_text(json.dumps(examples,ensure_ascii=False),encoding="utf8")
    history=daily_history(ROOT/"reports")
    snapshot = json.loads((ROOT/"reports"/history[-1]["file"]).read_text(encoding="utf-8"))
    snapshot["observation_date"]=history[-1]["date"]
    inventory = json.loads((ROOT / "reports" / snapshot["inventory"]).read_text(encoding="utf-8"))
    snapshot["boards"] = [{"employer":source["source"], "available":source["status"] == "ok"}
                          for source in inventory["sources"]]
    postings = {row["url"]: row for row in snapshot["postings"]}
    reviews = []
    for line in (ROOT / "data/role_reviews.jsonl").read_text(encoding="utf-8").splitlines():
        review = json.loads(line)
        posting = postings.get(review["source_url"])
        if posting and review["review_date"] <= snapshot["observation_date"]:
            reviews.append(dict(review, title=posting["title"], employer=posting["employer"]))
            if review["area"] not in posting["areas"]:
                posting["areas"].append(review["area"])
    direct = [json.loads(line) for line in (ROOT / "data/reviewed_employer_postings.jsonl").read_text(encoding="utf-8").splitlines()]
    snapshot["direct"] = [row for row in direct if row["observed_on"] <= snapshot["observation_date"]]
    snapshot["reviews"] = reviews
    snapshot["areas"] = sorted(set(PATTERNS) | {r["area"] for r in reviews} |
                               {a for row in snapshot["direct"] for a in row["areas"]})
    (dest / "market.json").write_text(json.dumps(snapshot,ensure_ascii=False),encoding="utf-8")
    (dest / "market-history.json").write_text(json.dumps(history,ensure_ascii=False),encoding="utf-8")
    boards=sorted((ROOT/"reports").glob("baykar-roles-*.json"))
    if boards:
        board=json.loads(boards[-1].read_text(encoding="utf8"))
        board["observation_date"]=observation_date(board["collected_at"])
        (dest/"employer-board.json").write_text(json.dumps(board,ensure_ascii=False),encoding="utf8")
    print(dest)


if __name__ == "__main__":
    main()
