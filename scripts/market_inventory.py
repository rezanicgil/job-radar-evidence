"""Inventory all titles at configured boards. Preserve uncategorized roles for review."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.error import URLError
from urllib.request import Request, urlopen
import workday_board

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "iOS": r"\bios\b|swiftui",
    "Android": r"\bandroid\b",
    "Mobile (general/cross-platform)": r"mobile (?:application |software )?(?:engineer|developer)|flutter|react native|mobil geliştirici",
    "Embedded and firmware": r"embedded|firmware|gömülü|rtos|bare.metal|fpga",
    "Backend": r"back.?end|arka uç",
    "Frontend": r"front.?end|ön yüz",
    "Full stack": r"full.?stack",
    "Software engineering (general)": r"software (?:developer|engineer|architect)|yazılım (?:geliştirici|mühendis|mimarı)|uygulama entegrasyon mühendisi|\b(?:java|python|c\+\+|kotlin|swift) (?:engineer|developer)\b|(?<!\w)\.net developer\b|\b(?:abap|low[- ]code application) developer\b",
    "Data and AI": r"data (?:engineer|scien|analyst|architect)|machine learning|yapay zeka|veri mühendis|\bml engineer|\bai (?:engineer|researcher)|image processing engineer|data analytics & digitalization engineer|data & ai chapter lead engineer",
    "Platform and reliability": r"dev(?:sec)?ops|platform engineer|cloud engineer|infrastructure engineer|(?:site|database) reliability|\bsre\b|bt altyapı mühendisi|veritabanı yöneticisi|sistem yöneticisi|\bsystems? administrator\b",
    "Financial software": r"quantitative developer|payments engineer|blockchain (?:ops |security )?engineer",
    "Security": r"security engineer|devsecops engineer|penetration test|siber güvenlik|bilgi güvenliği mühendisi|security analyst",
    "QA and testing": r"\bqa\b|test (?:automation|engineer)|quality assurance|\bsdet\b|\bsoftware development engineer in test\b",
    "Games": r"(?:game|gameplay(?: & UI)?|unity|unreal) (?:software )?(?:engineer|developer|programmer)|oyun geliştirici",
    "Robotics and controls": r"robotics|robotik|control systems",
    "Networking and systems": r"network engineer|systems programmer|kernel engineer|network software",
}
TR_LOCATION = re.compile(r"\b(?:turkey|türkiye|turkiye|istanbul|i̇stanbul|ankara|izmir|i̇zmir|bursa|kocaeli|antalya)\b", re.I)


def observation_date(timestamp):
    return datetime.fromisoformat(timestamp).astimezone(timezone(timedelta(hours=3))).date().isoformat()


def title_areas(title):
    normalized = " ".join(title.split())
    return [area for area, pattern in PATTERNS.items() if re.search(pattern, normalized, re.I)]


REVIEWED_TITLES = {
    (r["employer"], r["title"], r["source_url"]): r
    for r in (json.loads(line) for line in (ROOT/"data/reviewed_title_inclusions.jsonl").read_text("utf8").splitlines())
}


def posting_areas(employer,title,url):
    areas=title_areas(title)
    review=REVIEWED_TITLES.get((employer,title,url))
    if review:
        return list(dict.fromkeys([*areas,*review["areas"]]))
    return areas


def in_turkiye(country, location):
    if country:
        return country.casefold() in {"tr", "turkey", "türkiye", "turkiye"}
    return bool(TR_LOCATION.search(location or ""))


def fetch(source, *, retry_timeout=True):
    ats, slug = source["ats"], source["slug"]
    url = {"workday": f"https://{slug.split('/')[0]}.myworkdayjobs.com/en-US/{slug.split('/')[-1]}",
           "bamboohr": f"https://{slug}.bamboohr.com/careers/list",
           "lever": f"https://api.lever.co/v0/postings/{slug}?mode=json",
           "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
           "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
           "workable": f"https://www.workable.com/api/accounts/{slug}?details=true",
           "smartrecruiters": f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?country=tr&limit=100"}[ats]
    try:
        if ats=="workday":
            jobs=workday_board.listing_rows(slug,in_turkiye)
            for job in jobs:
                job["employer"]=source["name"]
                job["areas"]=posting_areas(source["name"],job["title"],job["url"])
            return dict(source=source["name"],url=url,status="ok",scanned=len(jobs)),jobs
        request = Request(url, headers={"User-Agent":"JobRadar/1.0 (+https://github.com/rezanicgil/job-radar-evidence)", "Accept":"application/json"})
        with urlopen(request if ats in {"ashby","workable","bamboohr"} else url, timeout=15) as response:
            payload = json.load(response)
        if ats == "smartrecruiters":
            rows = payload["content"]
            while len(rows) < payload["totalFound"]:
                with urlopen(f"{url}&offset={len(rows)}", timeout=15) as response:
                    page = json.load(response)["content"]
                if not page or page[0]["id"] == rows[0]["id"]:
                    raise ValueError("Incomplete SmartRecruiters pagination")
                rows.extend(page)
        elif ats == "bamboohr":
            rows = payload["result"]
            if len({str(row["id"]) for row in rows}) != payload["meta"]["totalCount"]:
                raise ValueError("Incomplete BambooHR board")
        else:
            rows = payload if ats == "lever" else payload["jobs"]
        jobs = []
        for row in rows:
            alternate_location=False
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
            elif ats == "bamboohr":
                title = row["jobOpeningName"]
                link = f"https://{slug}.bamboohr.com/careers/{row['id']}"
                place = row.get("location") or {}
                ats_place = row.get("atsLocation") or {}
                country = place.get("addressCountry") or ats_place.get("country")
                location = ", ".join(dict.fromkeys(filter(None, (place.get("city") or ats_place.get("city"),
                                                                  place.get("state"), country))))
            elif ats == "lever":
                title, link = row["text"], row["hostedUrl"]
                country, location = row.get("country"), row["categories"].get("location", "")
                if not in_turkiye(country, location):
                    for place in row["categories"].get("allLocations") or []:
                        if place!=location and in_turkiye(None,place):
                            country,location="TR",place
                            alternate_location=True
                            break
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
                            alternate_location=True
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
                                 areas=posting_areas(source["name"],title,link),**({"location_scope":"listed_alternative"} if alternate_location else {})))
        return dict(source=source["name"], url=url, status="ok", scanned=len(rows)), jobs
    except (URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
        if retry_timeout and isinstance(getattr(exc,"reason",exc),TimeoutError):
            return fetch(source,retry_timeout=False)
        return dict(source=source["name"], url=url, status=f"{type(exc).__name__}: {exc}"), []


def main(folder=None):
    sources = json.loads((ROOT / "data/market_sources.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(fetch, sources))
    jobs = {job["url"]:job for _, rows in results for job in rows}
    now = datetime.now(timezone.utc)
    inventory = dict(collected_at=now.isoformat(), sources=[s for s,_ in results], jobs=list(jobs.values()))
    target = (folder or ROOT/"reports") / f"inventory-{now:%Y-%m-%dT%H%M%S%fZ}.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Boards responding:", sum(s["status"]=="ok" for s,_ in results), "/", len(results))
    print("TR-location records:", len(jobs), "with role tags:",sum(bool(j["areas"]) for j in jobs.values()))
    for area in PATTERNS:
        print(area, sum(area in j["areas"] for j in jobs.values()))
    return target


if __name__ == "__main__":
    main()
