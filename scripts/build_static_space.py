"""Stage the free Hugging Face Static Space with its dated market snapshot."""

import json
import shutil
import tempfile
from pathlib import Path
from market_inventory import ROOT, PATTERNS


def main():
    root = ROOT / "runs"
    root.mkdir(exist_ok=True)
    dest = Path(tempfile.mkdtemp(prefix="static-space-", dir=root))
    shutil.copytree(ROOT / "releases/static-space",dest,dirs_exist_ok=True)
    shutil.copyfile(ROOT / "LICENSE",dest / "LICENSE")
    snapshot = json.loads(max((ROOT / "reports").glob("skill-mentions-*.json")).read_text(encoding="utf-8"))
    snapshot["areas"] = list(PATTERNS)
    (dest / "market.json").write_text(json.dumps(snapshot,ensure_ascii=False),encoding="utf-8")
    print(dest)


if __name__ == "__main__":
    main()
