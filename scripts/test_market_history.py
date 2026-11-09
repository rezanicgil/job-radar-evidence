"""Check calendar boundaries, changing board coverage and comparable technology counts."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from market_history import daily_history


def write_observation(folder,timestamp,boards,rows,vocabulary):
    key=timestamp.replace(":","")
    inventory=f"inventory-{key}.json"
    (folder/inventory).write_text(json.dumps({"sources":[{"source":e,"status":s} for e,s in boards.items()]}),"utf8")
    data=dict(collected_at=timestamp,inventory=inventory,vocabulary=vocabulary,postings=[
        dict(url=url,employer=e,skills=skills,status="readable") for url,(e,skills) in rows.items()])
    (folder/f"skill-mentions-{key}.json").write_text(json.dumps(data),"utf8")


class MarketHistoryTest(unittest.TestCase):
    def test_compare_last_snapshots_across_local_midnight(self):
        with TemporaryDirectory() as tmp:
            folder=Path(tmp)
            old={"a":("A",[]),"b":("A",["Git"]),"c":("C",["Git"]),"d":("D",["Git"]),"e":("E",["Git"])}
            new={"a":("A",["Git","Git"]),"b":("A",[]),"g":("G",["Git"]),"f":("F",["Git"]),"h":("A",["Git","Yocto"])}
            write_observation(folder,"2026-11-09T17:00:00+00:00",{}, {}, [])
            write_observation(folder,"2026-11-09T20:59:00+00:00",dict(A="ok",C="ok",D="ok",E="ok",F="timeout"),old,["Git","SQL"])
            write_observation(folder,"2026-11-09T21:01:00+00:00",dict(A="ok",C="timeout",E="ok",F="ok",G="ok"),new,["Git","SQL","Yocto"])
            first,second=daily_history(folder)
            self.assertEqual((first["date"],second["date"]),("2026-11-09","2026-11-10"))
            self.assertNotIn("comparison",first)
            comparison=second["comparison"]
            self.assertEqual(comparison["previous_file"],first["file"])
            self.assertEqual((comparison["shared_readable"],comparison["entered_readable"],comparison["left_readable"]),(2,3,3))
            self.assertEqual(comparison["changes"]["Git"],dict.fromkeys(
                ("new_board","recovered_board","entered_sample","gained_on_shared","removed_board",
                 "unavailable_board","left_sample","lost_on_shared"),1))
            self.assertEqual(comparison["changes"]["SQL"],{})
            self.assertNotIn("Yocto",comparison["changes"])


if __name__=="__main__":
    unittest.main()
