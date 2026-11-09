"""Compare a retrained CPU checkpoint and its evaluation with the published release."""
import argparse
from hashlib import file_digest
import json
from pathlib import Path
import platform
from importlib.metadata import version

from huggingface_hub import HfApi, hf_hub_download
from safetensors import safe_open

ROOT=Path(__file__).resolve().parents[1]
REPO="rezanicgil/python-tr-en-retriever"
REV="813078062d92ba7d57487fd97b14af3acd620522"


def compare(run):
    reference=json.loads((ROOT/"reports/translation-retrieval.json").read_text("utf8"))
    report=json.loads((run/"training-report.json").read_text("utf8"))
    weights=run/"model.safetensors"
    with weights.open("rb") as stream:
        local=file_digest(stream,"sha256").hexdigest()
    published=HfApi().model_info(REPO,revision=REV,files_metadata=True)
    target=next(f.lfs.sha256 for f in published.siblings if f.rfilename=="model.safetensors")
    equal=local==target
    mismatches=[]
    if not equal:
        baseline=hf_hub_download(REPO,"model.safetensors",revision=REV)
        with safe_open(baseline,framework="pt") as a,safe_open(weights,framework="pt") as b:
            for key in sorted(set(a.keys())|set(b.keys())):
                if key not in a.keys() or key not in b.keys() or not a.get_tensor(key).equal(b.get_tensor(key)):
                    mismatches.append(key)
    return dict(published_repo=REPO,published_revision=REV,published_sha256=target,local_sha256=local,
                weight_file_identical=equal,tensors_identical=not mismatches,differing_tensors=mismatches,
                metrics_and_protocol_identical=reference==report,
                differing_report_fields=sorted(k for k in set(reference)|set(report) if reference.get(k)!=report.get(k)),
                python=platform.python_version(),platform=platform.system(),packages={k:version(k) for k in
                    ["torch","transformers","tokenizers","numpy","huggingface-hub","safetensors","polib","requests"]})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run",type=Path)
    args=parser.parse_args()
    result=compare(args.run)
    print(json.dumps(result,indent=2))
    if not (result["tensors_identical"] and result["metrics_and_protocol_identical"]):
        raise SystemExit(1)


if __name__=="__main__":
    main()
