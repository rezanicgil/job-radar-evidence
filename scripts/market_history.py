"""Summarize the last observed snapshot on each Türkiye calendar day."""

from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from market_inventory import observation_date
LEGACY_NAMES = json.loads((Path(__file__).resolve().parents[1]/"data/market_vocabulary_v1.json").read_text(encoding="utf-8"))


def compare_observations(previous,current):
    before,after=previous["rows"],current["rows"]
    shared=before.keys()&after.keys()
    vocabulary=sorted(set(previous["vocabulary"])&set(current["vocabulary"]))
    changes={skill:Counter() for skill in vocabulary}

    def count(group,skills):
        for skill in skills:
            if skill in changes:
                changes[skill][group]+=1

    for url in shared:
        prior=set(before[url]["skills"])
        now=set(after[url]["skills"])
        count("gained_on_shared",now-prior)
        count("lost_on_shared",prior-now)
    for key,other,only,groups in [
        (after,previous,after.keys()-before.keys(),("new_board","recovered_board","entered_sample")),
        (before,current,before.keys()-after.keys(),("removed_board","unavailable_board","left_sample"))
    ]:
        for url in only:
            employer=key[url]["employer"]
            boards=other["boards"]
            group=groups[0] if employer not in boards else groups[1] if not boards[employer] else groups[2]
            count(group,set(key[url]["skills"]))
    for skill,values in changes.items():
        entered=sum(values[k] for k in ("new_board","recovered_board","entered_sample","gained_on_shared"))
        left=sum(values[k] for k in ("removed_board","unavailable_board","left_sample","lost_on_shared"))
        delta=current["mentions"].get(skill,0)-previous["mentions"].get(skill,0)
        if entered-left!=delta:
            raise ValueError("URL comparison does not reproduce the change for "+skill)
    return dict(previous_date=previous["date"],previous_file=previous["file"],
                previous_collected_at=previous["collected_at"],shared_readable=len(shared),
                entered_readable=len(after)-len(shared),left_readable=len(before)-len(shared),changes=changes)


def daily_history(folder):
    days = {}
    for path in sorted(folder.glob("skill-mentions-*.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        observed = datetime.fromisoformat(snapshot["collected_at"])
        date = observation_date(snapshot["collected_at"])
        if date not in days or observed > days[date][0]:
            days[date] = (observed,path,snapshot)
    result = []
    previous = None
    for date, (_,path,snapshot) in sorted(days.items()):
        inventory = json.loads((folder/snapshot["inventory"]).read_text(encoding="utf-8"))
        rows = {row["url"]:row for row in snapshot["postings"]}
        counts = Counter()
        readable = [row for row in rows.values() if row["status"]=="readable"]
        for row in readable:
            counts.update(set(row["skills"]))
        day=dict(date=date, collected_at=snapshot["collected_at"], file=path.name,
                           boards_total=len(inventory["sources"]),
                           boards_ok=sum(s["status"]=="ok" for s in inventory["sources"]),
                           employers=len({row["employer"] for row in readable}),
                           readable=len(readable),selected=len(rows),vocabulary=snapshot.get("vocabulary",LEGACY_NAMES),
                           mentions=dict(sorted(counts.items())))
        state=dict(day,rows={row["url"]:row for row in readable},
                   boards={s["source"]:s["status"]=="ok" for s in inventory["sources"]})
        if previous is not None:
            day["comparison"]=compare_observations(previous,state)
        result.append(day)
        previous=state
    return result
