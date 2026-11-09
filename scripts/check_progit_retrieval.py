"""Retrieve matching Pro Git section headings across languages using frozen encoders."""
from collections import Counter
from hashlib import sha256
import json
import re
from zipfile import ZipFile

import requests
import torch
from transformers import AutoModel, AutoTokenizer
from evaluate_pooled_retrieval import BASE, REVISION, ROOT, embeddings

SOURCES={"en":("progit/progit2","a013e3230a1207cfa5ae94d28ba7d2021063c337"),
         "tr":("progit/progit2-tr","b7c3c05b2ba37a03ee7aef68d760773e0373c7ec")}
MODELS=[("base",BASE,REVISION),("adapted","rezanicgil/python-tr-en-retriever","813078062d92ba7d57487fd97b14af3acd620522")]


def headings(lang):
    repo,revision=SOURCES[lang]
    path=ROOT/"runs"/f"{revision}.zip"
    if not path.exists():
        response=requests.get(f"https://codeload.github.com/{repo}/zip/{revision}",timeout=120)
        response.raise_for_status()
        path.write_bytes(response.content)
    found={}
    with ZipFile(path) as archive:
        for name in archive.namelist():
            relative=name.partition("/")[2]
            if not relative.startswith("book/") or not relative.endswith(".asc"):continue
            lines=archive.read(name).decode("utf8").splitlines()
            first=True
            for i,line in enumerate(lines):
                match=re.fullmatch(r"(={2,6})\s+(.+)",line)
                if not match:continue
                anchor=re.fullmatch(r"\[\[([\w-]+)\]\]",lines[i-1].strip()) if i else None
                if not first and not anchor:continue
                identity=(relative,"first" if first else anchor[1])
                first=False
                found[identity]=dict(title=match[2].strip(),line=i+1)
    return found


def main():
    torch.set_num_threads(4)
    en,tr=headings("en"),headings("tr")
    candidates=[k for k in sorted(en.keys()&tr.keys()) if en[k]["title"].casefold()!=tr[k]["title"].casefold()]
    counts=[Counter(data[k]["title"].casefold() for k in candidates) for data in (en,tr)]
    keys=[k for k in candidates if all(counts[i][data[k]["title"].casefold()]==1 for i,data in enumerate((en,tr)))]
    rows=[]
    for path,anchor in keys:
        row=dict(path=path,section=anchor)
        for lang,data in [('tr',tr),('en',en)]:
            heading=data[(path,anchor)]
            repo,revision=SOURCES[lang]
            row[lang+"_url"]=f"https://github.com/{repo}/blob/{revision}/{path}#L{heading['line']}"
            row[lang+"_line"]=heading["line"]
            row[lang+"_sha256"]=sha256(heading["title"].encode()).hexdigest()
        rows.append(row)
    index=ROOT/"releases/match-pilot/progit_section_index.jsonl"
    index.write_text("".join(json.dumps(r)+"\n" for r in rows),"utf8")
    report=dict(sources=SOURCES,index_sha256=sha256(index.read_text("utf8").encode()).hexdigest(),files=len({path for path,_ in keys}),pairs=len(keys),methods={})
    titles={lang:[data[k]["title"] for k in keys] for lang,data in [('en',en),('tr',tr)]}
    for method,repo,revision in MODELS:
        model=AutoModel.from_pretrained(repo,revision=revision).eval()
        tokenizer=AutoTokenizer.from_pretrained(repo,revision=revision)
        vectors={lang:torch.cat([embeddings(model,tokenizer,text[i:i+32]) for i in range(0,len(text),32)])
                 for lang,text in titles.items()}
        scores=vectors['en']@vectors['tr'].T
        directions={}
        for language,matrix in [('en-tr',scores),('tr-en',scores.T)]:
            ranks=[order.index(i)+1 for i,order in enumerate(matrix.argsort(descending=True).tolist())]
            directions[language]=dict(first=ranks.count(1),first_three=sum(r<=3 for r in ranks),ranks=ranks)
        report['methods'][method]=dict(repo=repo,revision=revision,views=directions)
        print(method,[(k,v['first'],v['first_three']) for k,v in directions.items()],len(keys),flush=True)
    (ROOT/'reports/progit-section-retrieval.json').write_text(json.dumps(report,indent=2)+'\n','utf8')


if __name__=="__main__":
    main()
