"""Stage only the Space runtime in a fresh, allowlisted directory."""

from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    root = ROOT / "runs"
    root.mkdir(exist_ok=True)
    dest = Path(tempfile.mkdtemp(prefix="space-",dir=root))
    for name in ("README.md","Dockerfile","requirements.txt"):
        shutil.copyfile(ROOT / "releases/evidence-space" / name,dest / name)
    snapshot = max((ROOT / "reports").glob("skill-mentions-*.json")).relative_to(ROOT)
    for name in ("scripts/demo.py","scripts/review_cv.py","scripts/train_smoke.py","scripts/market_inventory.py","templates/review.html","templates/market.html",snapshot,"LICENSE"):
        target = dest / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(ROOT / name,target)
    print(dest)


if __name__ == "__main__":
    main()
