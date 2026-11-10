"""Build an English applicant brief from a dated snapshot of recognized qualification headings."""
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path
from market_inventory import PATTERNS,observation_date

def stats(rows):
    measured=[];counts=Counter();employers=defaultdict(set)
    for r in rows:
        sections=[s for s in r.get("sections") or [] if s["kind"]=="qualifications"]
        if not sections:continue
        measured.append(r)
        for tech in {x for s in sections for x in s["skills"]}:
            counts[tech]+=1;employers[tech].add(r["employer"])
    return measured,counts,employers

def brief(p):
    d=json.loads(p.read_text("utf8"));rows=[r for r in d["postings"] if r["status"]=="readable"]
    assert len(rows)==len({r["url"] for r in rows})
    measured,counts,employers=stats(rows);n=len(measured);e=len({r["employer"] for r in measured})
    out=["# Which technologies appear in qualifications for software roles in Türkiye?","",
         f"Observed {observation_date(d['collected_at'])}. Of {len(rows)} readable postings, {n} ({n/len(rows):.1%}) had a recognized qualifications heading. These {n} postings came from {e} employers. Other descriptions remain outside the qualification denominator.","",
         "## Most frequently named in measured qualifications","",
         "Each technology counts once per posting. Employer share counts each employer once, regardless of how many openings it listed. Ties are ordered alphabetically.","",
         "| Technology | Posting share | Employer share |","|---|---:|---:|"]
    for tech,num in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:8]:
        en=len(employers[tech]);out.append(f"| {tech} | {num}/{n} ({num/n:.1%}) | {en}/{e} ({en/e:.1%}) |")
    out+=["","## Coverage by role family","","A posting may appear in multiple roles. A leading technology is shown only when at least three employers have measured sections in that role. This display rule limits rankings driven by one or two employers; it does not establish representativeness.","",
          "| Role family | Qualifications / readable postings | Measured employers | Most frequent qualification mentions |","|---|---:|---:|---|"]
    for role in PATTERNS:
        rs=[r for r in rows if role in r["areas"]];ms,c,_=stats(rs);ne=len({r["employer"] for r in ms})
        lead="No readable postings" if not rs else "No measured sections" if not ms else "Too few employers" if ne<3 else "No tracked names"
        if ne>=3 and c:
            top=max(c.values());lead=", ".join(sorted(t for t,v in c.items() if v==top))+f" ({top}/{len(ms)} postings; {top/len(ms):.1%})"
        coverage=f"{len(ms)}/{len(rs)} ({len(ms)/len(rs):.1%})" if rs else "—"
        out.append(f"| {role} | {coverage} | {ne} | {lead} |")
    out+=["","Use the table to choose which employer postings to inspect. Before editing a CV, read the linked condition: examples, alternatives and preferred skills can all occur inside a qualifications section. These are shares of the observed panel, not national demand or hiring probabilities.","",
          f"[Source snapshot]({p.name}) · [Explore postings by role and employer](https://rezanicgil-job-radar-evidence.static.hf.space/#market)"]
    return "\n".join(out)+"\n"

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument("snapshot",type=Path);args=cli.parse_args();p=args.snapshot
    p.with_name("qualification-brief-"+p.stem.removeprefix("skill-mentions-")+".md").write_text(brief(p),"utf8")
