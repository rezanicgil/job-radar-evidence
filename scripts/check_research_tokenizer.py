"""Check the browser research tokenizer against the pinned Python tokenizer."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from transformers import AutoTokenizer
from review_cv import ENCODERS

ROOT=Path(__file__).resolve().parents[1]


def check(url):
    rows=[json.loads(line) for line in (ROOT/"releases/match-pilot/language_switch.jsonl").read_text(encoding="utf-8").splitlines()]
    texts=sorted({row[key] for row in rows for key in ("requirement","cv_passage")})+["word "*150]
    repo,revision=ENCODERS["fine-tuned"]
    reference=AutoTokenizer.from_pretrained(repo,revision=revision)(texts,truncation=True,max_length=128)["input_ids"]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel="chrome")
        page=browser.new_page()
        page.goto(url)
        actual=page.evaluate("""async texts=>{
          const {AutoTokenizer,env}=await import('https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2/dist/transformers.min.js');
          const {researchTokenizer}=await import(new URL('research-tokenizer.js',location.href));
          env.allowLocalModels=false;
          const t=researchTokenizer(await AutoTokenizer.from_pretrained('Xenova/paraphrase-multilingual-MiniLM-L12-v2',{revision:'2c4055b12046f11709e9df2c122e59ffbdc2f900'}));
          return texts.map(s=>t(s,{truncation:true,padding:true}).input_ids.tolist()[0].map(Number));
        }""",texts)
        browser.close()
    assert actual==reference
    print(len(actual),"exact token sequences, including 128-token truncation")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url",nargs="?",default="https://rezanicgil-job-radar-evidence.static.hf.space/")
    check(parser.parse_args().url)
