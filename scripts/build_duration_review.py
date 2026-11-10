"""Build offline, prediction-free duration review forms from the frozen split."""
import html
import json
from hashlib import sha256
from split_duration_candidates import ROOT, digest, normalized, read

def main():
    manifest=json.loads((ROOT/"research/duration-splits-20261110.json").read_text("utf8"))
    passages={}
    for name,checksum in manifest["snapshots"].items():
        raw=ROOT/"data/raw"/name/"candidates.jsonl"
        assert sha256(raw.read_bytes()).hexdigest()==checksum
        for row in read(raw):
            passages.setdefault(digest(normalized(row["text"])),row)
    for split in ("dev","test"):
        cards=[]; first=None
        for key in manifest["splits"][split]["text_sha256"]:
            row=passages[key]
            for i,m in enumerate(row["mentions"]):
                t=row["text"];a,b=m["start"],m["end"]
                assert t[a:b]==m["text"]
                esc=html.escape
                identifier=key+":"+str(i)
                cards.append(f'<fieldset data-id="{identifier}"><legend>Duration {len(cards)+1}</legend><p>{esc(t[:a])}<mark>{esc(t[a:b])}</mark>{esc(t[b:])}</p><label>Meaning <select><option value="">Choose…</option>'+''.join(f'<option>{x}</option>' for x in ('prior experience','recent action','availability or schedule','benefit or leave','other','unclear'))+'</select></label><label>What does the duration refer to? <input placeholder="Task, activity or benefit"></label></fieldset>')
                if first is None: first=(identifier,t,m["text"])
        dest=ROOT/"data/interim"/f"duration-review-{split}.html"
        dest.write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Duration review</title><style>body{font:17px/1.5 system-ui;max-width:50rem;margin:auto;padding:1rem}fieldset{margin:1rem 0;border:1px solid #aaa}label{display:block;margin:.5rem}input{width:min(95%,28rem)}mark{background:#ffda78}</style><h1>Duration review</h1><p>Classify only the highlighted duration. Give its scope in a few words. Choose unclear when the passage is insufficient. No suggested labels are shown. Export before closing; this page does not save answers automatically.</p>'''+''.join(cards)+'''<button id="save">Export reviewed answers</button><output aria-live="polite"></output><script>
document.querySelector('#save').onclick=()=>{
const rows=[];for(const f of document.querySelectorAll('fieldset')){const kind=f.querySelector('select').value,scope=f.querySelector('input').value.trim();if(!kind&&!scope)continue;if(!kind||!scope){f.scrollIntoView();document.querySelector('output').textContent='Complete both fields for each started answer.';return}rows.push({id:f.dataset.id,kind,scope})}
if(!rows.length){document.querySelector('output').textContent='No answers yet.';return}
const url=URL.createObjectURL(new Blob([JSON.stringify(rows,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='duration-answers-SPLIT.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);document.querySelector('output').textContent=rows.length+' answers exported.'}
</script></html>'''.replace('SPLIT',split),'utf8')
        print(split,len(cards))
        if split=='dev':print(first)
if __name__=="__main__": main()
