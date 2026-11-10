"""Validate two independent duration-form exports and report overlap and disagreements."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path

KINDS={"prior experience","recent action","availability or schedule","benefit or leave","other","unclear"}

class Packet(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
    def handle_starttag(self,tag,attrs):
        if tag=="fieldset":
            key=dict(attrs).get("data-id")
            if not key or key in self.ids: raise ValueError("Invalid or repeated form ID")
            self.ids.add(key)

def index(rows,ids):
    if not isinstance(rows,list): raise ValueError("Expected an exported JSON array")
    result={}
    for row in rows:
        if not isinstance(row,dict): raise ValueError("Expected an answer object")
        key=row.get("id")
        if not isinstance(key,str) or key not in ids or key in result: raise ValueError(f"Unknown or repeated ID: {key}")
        if row.get("kind") not in KINDS or not isinstance(row.get("scope"),str) or not row["scope"].strip():
            raise ValueError(f"Incomplete or invalid answer: {key}")
        result[key]=row
    return result

def compare(ids,left,right):
    if not ids: raise ValueError("No review items in form")
    a,b=index(left,ids),index(right,ids)
    shared=sorted(a.keys()&b.keys())
    same=sum(a[k]["kind"]==b[k]["kind"] for k in shared)
    reviews=[dict(id=k,first=a[k],second=b[k]) for k in shared
             if a[k]["kind"]!=b[k]["kind"] or a[k]["scope"].strip().casefold()!=b[k]["scope"].strip().casefold()]
    return dict(form_items=len(ids),first_completed=len(a),second_completed=len(b),
                shared_items=len(shared),shared_coverage_pct=round(100*len(shared)/len(ids),1),
                matching_kinds=same,kind_agreement_pct_on_shared=round(100*same/len(shared),1) if shared else None,
                missing_first=sorted(ids-a.keys()),missing_second=sorted(ids-b.keys()),
                items_for_manual_comparison=reviews,
                interpretation="Kind agreement covers shared answers only. Scope wording differences need human interpretation; they are not automatically errors.")

def main():
    cli=argparse.ArgumentParser(description=__doc__)
    for key in ("form","first","second"):cli.add_argument(key,type=Path)
    args=cli.parse_args()
    if args.first.samefile(args.second):raise ValueError("Provide two independently completed exports")
    packet=Packet();packet.feed(args.form.read_text("utf8"))
    print(json.dumps(compare(packet.ids,*[json.loads(p.read_text("utf-8-sig")) for p in (args.first,args.second)]),indent=2,ensure_ascii=False))

if __name__=="__main__": main()
