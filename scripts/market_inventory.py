"""Inventory all titles at configured boards. Preserve uncategorized roles for review."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "iOS": r"\bios\b|swiftui",
    "Android": r"\bandroid\b",
    "Mobile (general/cross-platform)": r"mobile (?:application |software )?(?:engineer|developer)|flutter|react native|mobil geliştirici",
    "Embedded and firmware": r"embedded|firmware|gömülü|rtos|bare.metal|fpga",
    "Backend": r"back.?end|arka uç",
    "Frontend": r"front.?end|ön yüz",
    "Full stack": r"full.?stack",
    "Software engineering (general)": r"software (?:developer|engineer|architect)|yazılım (?:geliştirici|mühendis|mimarı)|uygulama entegrasyon mühendisi",
    "Data and AI": r"data (?:engineer|scien|analyst|architect)|machine learning|yapay zeka|veri mühendis|\bml engineer|\bai (?:engineer|researcher)",
    "Platform and reliability": r"devops|platform engineer|cloud engineer|infrastructure engineer|(?:site|database) reliability|\bsre\b|bt altyapı mühendisi|veritabanı yöneticisi",
    "Financial software": r"quantitative developer|payments engineer|blockchain engineer",
    "Security": r"security engineer|penetration test|siber güvenlik|bilgi güvenliği mühendisi|security analyst",
    "QA and testing": r"\bqa\b|test (?:automation|engineer)|quality assurance",
    "Games": r"(?:game|gameplay(?: & UI)?|unity|unreal) (?:software )?(?:engineer|developer|programmer)|oyun geliştirici",
    "Robotics and controls": r"robotics|robotik|control systems",
    "Networking and systems": r"network engineer|systems programmer|kernel engineer|network software",
}
TR_LOCATION = re.compile(r"\b(?:turkey|türkiye|turkiye|istanbul|i̇stanbul|ankara|izmir|i̇zmir|bursa|kocaeli|antalya)\b", re.I)


def in_turkiye(country, location):
    if country:
        return country.casefold() in {"tr", "turkey", "türkiye", "turkiye"}
    return bool(TR_LOCATION.search(location or ""))


def fetch(source):
    ats, slug = source["ats"], source["slug"]
    url = {"lever": f"https://api.lever.co/v0/postings/{slug}?mode=json",
           "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
           "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
           "workable": f"https://www.workable.com/api/accounts/{slug}?details=true",
           "smartrecruiters": f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?country=tr&limit=100"}[ats]
    try:
        request = Request(url, headers={"User-Agent":"JobRadar/1.0 (+https://github.com/rezanicgil/job-radar-evidence)", "Accept":"application/json"})
        with urlopen(request if ats in {"ashby","workable"} else url, timeout=15) as response:
            payload = json.load(response)
        if ats == "smartrecruiters":
            rows = payload["content"]
            while len(rows) < payload["totalFound"]:
                with urlopen(f"{url}&offset={len(rows)}", timeout=15) as response:
                    page = json.load(response)["content"]
                if not page or page[0]["id"] == rows[0]["id"]:
                    raise ValueError("Incomplete SmartRecruiters pagination")
                rows.extend(page)
        else:
            rows = payload if ats == "lever" else payload["jobs"]
        jobs = []
        for row in rows:
            if ats == "workable":
                title = row["title"]
                link = f"https://apply.workable.com/{slug}/j/{row['shortcode']}/"
                locations = row.get("locations") or [row]
                place = next((p for p in locations if not p.get("hidden") and in_turkiye(
                    p.get("countryCode") or p.get("country"), p.get("city"))), None)
                if place is None:
                    continue
                country = place.get("countryCode") or place.get("country")
                location = ", ".join(dict.fromkeys(filter(None,[place.get("city"),
                    place.get("region") or place.get("state"), place.get("country") or country])))
            elif ats == "lever":
                title, link = row["text"], row["hostedUrl"]
                country, location = row.get("country"), row["categories"].get("location", "")
            elif ats == "ashby":
                if row.get("isListed") is False:
                    continue
                title, link = row["title"], row["jobUrl"]
                country = (row.get("address") or {}).get("postalAddress", {}).get("addressCountry")
                location = row.get("location", "")
                if not in_turkiye(country, location):
                    for alternate in row.get("secondaryLocations") or []:
                        address = (alternate.get("address") or {}).get("postalAddress") or {}
                        if in_turkiye(address.get("addressCountry"), alternate.get("location")):
                            country, location = address.get("addressCountry"), alternate.get("location")
                            break
            elif ats == "smartrecruiters":
                title = row["name"]
                link = f"https://jobs.smartrecruiters.com/{slug}/{row['id']}"
                country, location = row["location"]["country"], row["location"].get("city")
            else:
                title, link = row["title"], row["absolute_url"]
                country, location = None, row["location"]["name"]
            if in_turkiye(country, location):
                jobs.append(dict(employer=source["name"], title=title, url=link, location=location,
                                 areas=[area for area, pattern in PATTERNS.items() if re.search(pattern,title,re.I)]))
        return dict(source=source["name"], url=url, status="ok", scanned=len(rows)), jobs
    except (URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        return dict(source=source["name"], url=url, status=f"{type(exc).__name__}: {exc}"), []


def main():
    sources = json.loads((ROOT / "data/market_sources.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(fetch, sources))
    jobs = {job["url"]:job for _, rows in results for job in rows}
    now = datetime.now(timezone.utc)
    inventory = dict(collected_at=now.isoformat(), sources=[s for s,_ in results], jobs=list(jobs.values()))
    target = ROOT / "reports" / f"inventory-{now:%Y-%m-%dT%H%M%S%fZ}.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Boards responding:", sum(s["status"]=="ok" for s,_ in results), "/", len(results))
    print("TR-location records:", len(jobs), "with role tags:",sum(bool(j["areas"]) for j in jobs.values()))
    for area in PATTERNS:
        print(area, sum(area in j["areas"] for j in jobs.values()))


if __name__ == "__main__":
    main()
