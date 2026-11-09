"""Publish the latest local reports and daily history together to the public Space."""

import json
from pathlib import Path
import subprocess
import sys

from huggingface_hub import HfApi, hf_hub_download, CommitOperationAdd
from market_inventory import ROOT

REPO="rezanicgil/job-radar-evidence"


def main():
    staged=Path(subprocess.check_output([sys.executable,str(ROOT/"scripts/build_static_space.py")],text=True).strip())
    history=json.loads((staged/"market-history.json").read_text(encoding="utf-8"))
    if not history or not history[-1]["readable"]:
        raise ValueError("Latest collection has no readable descriptions")
    api=HfApi()
    info=api.space_info(REPO)
    if any(s.rfilename=="market-history.json" for s in info.siblings):
        path=hf_hub_download(REPO,"market-history.json",repo_type="space",revision=info.sha)
        prior=json.loads(Path(path).read_text(encoding="utf-8"))
        by_day={d["date"]:d for d in history}
        for day in prior:
            new=by_day.get(day["date"])
            if not new or new["collected_at"]<day["collected_at"]:
                raise ValueError("Local reports are missing a published observation")
    operations=[CommitOperationAdd(path_in_repo=n,path_or_fileobj=staged/n)
                for n in ("market.json","market-history.json")]
    print(api.create_commit(repo_id=REPO,repo_type="space",operations=operations,
                            parent_commit=info.sha,commit_message="Refresh market snapshot and daily history").oid)


if __name__=="__main__":
    main()
