"""Measure English skill-sentence recall on annotated TECHWOLF positives."""

import csv
from hashlib import sha256
import io
import json

import requests
from huggingface_hub import hf_hub_download
from skill_sentence_baseline import DATA,VERSION,ROOT,score


def main():
    revision="19305c85e35a74fb2a5128d8ee3798b06470b596"
    url=f"https://raw.githubusercontent.com/jensjorisdecorte/skill-extraction-benchmark/{revision}/data/techwolf_test_annotations.csv"
    response=requests.get(url,timeout=20)
    response.raise_for_status()
    annotations=list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    def normalized(text):
        return " ".join(text.casefold().split())
    seen=set()
    for split in ("train","dev"):
        path=hf_hub_download(DATA,split+".json",revision=VERSION,repo_type="dataset")
        with open(path,encoding="utf-8") as stream:
            seen.update(normalized(" ".join(json.loads(line)["tokens"])) for line in stream)
    sentences={normalized(row["sentence"]) for row in annotations}
    eligible=sorted(sentences-seen)
    model_path=ROOT/"releases/static-space/skill-sentences.json"
    model=json.loads(model_path.read_text(encoding="utf-8"))
    recalled=sum(score(s,model)>=model["threshold"] for s in eligible)
    result=dict(source=url,source_sha256=sha256(response.content).hexdigest(),annotations=len(annotations),
                unique_sentences=len(sentences),excluded_seen=len(sentences&seen),eligible=len(eligible),
                recalled=recalled,recall=recalled/len(eligible),model_sha256=sha256(model_path.read_bytes()).hexdigest(),
                scope="Headings absent. Positive skill-annotated sentences only. Precision and CV fit cannot be estimated.")
    (ROOT/"reports/external-skill-recall.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(result["recalled"],"/",result["eligible"],"overlap",result["excluded_seen"])


if __name__=="__main__":
    main()
