"""Summarize the last observed snapshot on each Türkiye calendar day."""

from collections import Counter
from datetime import datetime, timedelta, timezone
import json

TURKIYE = timezone(timedelta(hours=3))


def daily_history(folder):
    days = {}
    for path in sorted(folder.glob("skill-mentions-*.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        observed = datetime.fromisoformat(snapshot["collected_at"]).astimezone(TURKIYE)
        date = observed.date().isoformat()
        if date not in days or observed > days[date][0]:
            days[date] = (observed,path,snapshot)
    result = []
    for date, (_,path,snapshot) in sorted(days.items()):
        inventory = json.loads((folder/snapshot["inventory"]).read_text(encoding="utf-8"))
        rows = {row["url"]:row for row in snapshot["postings"]}
        counts = Counter()
        readable = [row for row in rows.values() if row["status"]=="readable"]
        for row in readable:
            counts.update(set(row["skills"]))
        result.append(dict(date=date, collected_at=snapshot["collected_at"], file=path.name,
                           boards_total=len(inventory["sources"]),
                           boards_ok=sum(s["status"]=="ok" for s in inventory["sources"]),
                           employers=len({row["employer"] for row in readable}),
                           readable=len(readable),selected=len(rows),mentions=dict(sorted(counts.items()))))
    return result
