"""Stage the free Hugging Face Static Space with its dated market snapshot."""

import json
import shutil
import tempfile
from pathlib import Path
from market_inventory import ROOT, PATTERNS
from market_history import daily_history


def main():
    root = ROOT / "runs"
    root.mkdir(exist_ok=True)
    dest = Path(tempfile.mkdtemp(prefix="static-space-", dir=root))
    shutil.copytree(ROOT / "releases/static-space",dest,dirs_exist_ok=True)
    shutil.copyfile(ROOT / "LICENSE",dest / "LICENSE")
    shutil.copyfile(ROOT / "research/source_grounded_candidates.jsonl",dest / "review-packet.jsonl")
    shutil.copyfile(ROOT / "reports/source-pairs-dev.json",dest / "model-examples.json")
    shutil.copyfile(ROOT / "reports/language-switch.json",dest / "model-languages.json")
    history=daily_history(ROOT/"reports")
    snapshot = json.loads((ROOT/"reports"/history[-1]["file"]).read_text(encoding="utf-8"))
    inventory = json.loads((ROOT / "reports" / snapshot["inventory"]).read_text(encoding="utf-8"))
    snapshot["boards"] = [{"employer":source["source"], "available":source["status"] == "ok"}
                          for source in inventory["sources"]]
    postings = {row["url"]: row for row in snapshot["postings"]}
    reviews = []
    for line in (ROOT / "data/role_reviews.jsonl").read_text(encoding="utf-8").splitlines():
        review = json.loads(line)
        posting = postings.get(review["source_url"])
        if posting and review["review_date"] <= snapshot["collected_at"][:10]:
            reviews.append(dict(review, title=posting["title"], employer=posting["employer"]))
            if review["area"] not in posting["areas"]:
                posting["areas"].append(review["area"])
    direct = [json.loads(line) for line in (ROOT / "data/reviewed_employer_postings.jsonl").read_text(encoding="utf-8").splitlines()]
    snapshot["direct"] = [row for row in direct if row["observed_on"] <= snapshot["collected_at"][:10]]
    snapshot["reviews"] = reviews
    snapshot["areas"] = sorted(set(PATTERNS) | {r["area"] for r in reviews} |
                               {a for row in snapshot["direct"] for a in row["areas"]})
    (dest / "market.json").write_text(json.dumps(snapshot,ensure_ascii=False),encoding="utf-8")
    (dest / "market-history.json").write_text(json.dumps(history,ensure_ascii=False),encoding="utf-8")
    boards=sorted((ROOT/"reports").glob("baykar-roles-*.json"))
    if boards:shutil.copyfile(boards[-1],dest/"employer-board.json")
    print(dest)


if __name__ == "__main__":
    main()
