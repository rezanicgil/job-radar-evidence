"""Classify the context of a bracketed duration. Runs locally on CPU."""
import argparse
import re
from pathlib import Path
import torch
from safetensors.torch import load_file
from transformers import AutoModel, AutoTokenizer

BASE="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REV="e8f8c211226b894fcb81acc59f3b34ba3efd5f42"

def context(text):
    m=re.fullmatch(r"([^\[\]]*)\[([^\[\]]+)\]([^\[\]]*)",text,re.S)
    if not m or not m[2].strip(): raise ValueError("Mark exactly one duration in square brackets.")
    return " ".join(re.findall(r"\w+",m[1].casefold())[-10:]+["<duration>"]+re.findall(r"\w+",m[3].casefold())[:10])

@torch.inference_mode()
def predict(texts):
    inputs=[context(t) for t in texts]
    tokenizer=AutoTokenizer.from_pretrained(BASE,revision=REV)
    model=AutoModel.from_pretrained(BASE,revision=REV).eval()
    batch=tokenizer(inputs,padding=True,truncation=True,max_length=128,return_tensors="pt")
    mask=batch.attention_mask.unsqueeze(-1)
    vectors=torch.nn.functional.normalize((model(**batch).last_hidden_state*mask).sum(1)/mask.sum(1))
    head=load_file(str(Path(__file__).with_name("head.safetensors")))
    return ["prior experience" if s>=0 else "other duration" for s in vectors@head["weight"]+head["bias"]]

if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__);cli.add_argument("passages",nargs="+")
    torch.set_num_threads(4)
    for result in predict(cli.parse_args().passages): print(result)
