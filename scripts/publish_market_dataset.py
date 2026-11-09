"""Publish daily observations and their technology denominators on Hugging Face."""

from collections import Counter
import json
from pathlib import Path

from huggingface_hub import CommitOperationAdd, HfApi, hf_hub_download
from market_history import daily_history
from market_inventory import ROOT

REPO = "rezanicgil/turkiye-software-job-market"


def encode_rows(rows):
    return "".join(json.dumps(row, ensure_ascii=False)+"\n" for row in rows).encode("utf-8")


def daily_rows(day, folder):
    snapshot = json.loads((folder/day["file"]).read_text(encoding="utf-8"))
    inventory = json.loads((folder/snapshot["inventory"]).read_text(encoding="utf-8"))
    selected = {row["url"]:row for row in snapshot["postings"]}
    postings = []
    for job in inventory["jobs"]:
        measured = selected.get(job["url"], {})
        postings.append(dict(date=day["date"], collected_at=day["collected_at"],
                             employer=job["employer"], title=job["title"], location=job["location"],
                             url=job["url"], areas=job["areas"],
                             location_scope=job.get("location_scope"),
                             description_sha256=measured.get("description_sha256"),
                             source_requisition=measured.get("source_requisition"),
                             source_listed_date=measured.get("source_listed_date"),
                             sections=measured.get("sections"),
                             description_status=measured.get("status","not_selected"),
                             technologies=measured.get("skills") if measured.get("status")=="readable" else None))
    assert len(postings)==len({row["url"] for row in postings})
    readable = [p for p in postings if p["description_status"]=="readable"]
    counts = Counter(skill for p in readable for skill in set(p["technologies"]))
    employers = {p["employer"] for p in readable}
    assert len(readable)==day["readable"] and len(employers)==day["employers"] and counts==day["mentions"]
    employer_totals = Counter(p["employer"] for p in readable)
    has_digests = bool(readable) and all(p["description_sha256"] for p in readable)
    distinct = {(p["employer"],p["description_sha256"]) for p in readable} if has_digests else None
    technologies = []
    for skill in day["vocabulary"]:
        mentioning = Counter(p["employer"] for p in readable if skill in p["technologies"])
        distinct_mentions = {(p["employer"],p["description_sha256"]) for p in readable
                             if skill in p["technologies"]} if has_digests else None
        top = min(mentioning, key=lambda employer: (-mentioning[employer], employer), default=None)
        technologies.append(dict(date=day["date"], technology=skill, postings_mentioning=counts[skill],
                                 readable_postings=len(readable), employers_mentioning=len(mentioning),
                                 represented_employers=len(employers), top_employer=top,
                                 distinct_descriptions=len(distinct) if has_digests else None,
                                 distinct_descriptions_mentioning=len(distinct_mentions) if has_digests else None,
                                 top_employer_mentions=mentioning[top] if top else None,
                                 other_employer_mentions=counts[skill]-mentioning[top] if top else None,
                                 other_employer_postings=len(readable)-employer_totals[top] if top else None))
    return postings, technologies


def main():
    folder = ROOT/"reports"
    history = daily_history(folder)
    if not history or not history[-1]["readable"]:
        raise ValueError("No readable market observations to publish")
    api = HfApi()
    api.create_repo(REPO, repo_type="dataset", exist_ok=True)
    info = api.dataset_info(REPO)
    files = {s.rfilename for s in info.siblings}
    operations = [CommitOperationAdd("README.md", ROOT/"releases/market-dataset/README.md")]
    direct=[json.loads(line) for line in (ROOT/"data/reviewed_employer_postings.jsonl").read_text(encoding="utf8").splitlines()]
    direct=[dict(sector=None,minimum_technical=[],preferred_technical=[]) | row for row in direct]
    keys={(r["observed_on"],r["source_url"],r["title"],r["location"]) for r in direct}
    if len(keys)!=len(direct):
        raise ValueError("Repeated direct employer observation")
    operations.append(CommitOperationAdd("direct/observations.jsonl",encode_rows(direct)))
    for day in history:
        name = f"postings/{day['date']}.jsonl"
        if name in files:
            prior = hf_hub_download(REPO,name,repo_type="dataset",revision=info.sha)
            with Path(prior).open(encoding="utf-8") as stream:
                if json.loads(next(stream))["collected_at"]>day["collected_at"]:
                    raise ValueError(f"Published snapshot for {day['date']} is newer")
        postings, technologies = daily_rows(day,folder)
        operations.extend([CommitOperationAdd(name,encode_rows(postings)),
                           CommitOperationAdd(f"technologies/{day['date']}.jsonl",encode_rows(technologies))])
    print(api.create_commit(repo_id=REPO,repo_type="dataset",parent_commit=info.sha,
                            operations=operations,commit_message="Publish daily market observations").oid)


if __name__=="__main__":
    main()
