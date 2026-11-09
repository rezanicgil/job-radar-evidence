"""Collect and validate one Türkiye market observation before adding it to the archive."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import market_inventory
import market_skills
import render_market


def validate(inventory,snapshot):
    data=json.loads(inventory.read_text(encoding="utf-8"))
    observation=json.loads(snapshot.read_text(encoding="utf-8"))
    if observation["inventory"]!=inventory.name:
        raise ValueError("Snapshot references a different inventory")
    expected={row["url"] for row in data["jobs"] if row["areas"]}
    measured=observation["postings"]
    if len(measured)!=len(expected) or {row["url"] for row in measured}!=expected:
        raise ValueError("Measured postings differ from title-selected inventory")
    readable=sum(row["status"]=="readable" for row in measured)
    if not readable:
        raise ValueError("No readable posting descriptions. Archive was not updated.")
    return readable


def refresh(folder):
    folder.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=folder) as tmp:
        inventory=market_inventory.main(Path(tmp))
        snapshot=market_skills.main(inventory)
        readable=validate(inventory,snapshot)
        chart=render_market.main(inventory)
        # Readers discover an observation via its JSON; expose that file last.
        for path in (inventory,chart,snapshot.with_suffix(".md"),snapshot):
            path.replace(folder/path.name)
        print(f"Archived {readable} readable descriptions in {snapshot.name}")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=market_inventory.ROOT/"reports")
    refresh(parser.parse_args().output)
