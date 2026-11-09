"""Read country- or city-filtered listings from a public Workday employer board."""

import json
from urllib.request import Request, urlopen


def endpoint(host,site):
    tenant=host.split(".")[0]
    return f"https://{host}/wday/cxs/{tenant}/{site}"


def listing_rows(slug,in_turkiye):
    prefix,site=slug.split("/")
    host=prefix+".myworkdayjobs.com"
    api=endpoint(host,site)+"/jobs"
    def page(offset,filters):
        body=json.dumps(dict(limit=20,offset=offset,searchText="",appliedFacets=filters)).encode()
        req=Request(api,data=body,headers={"Content-Type":"application/json","Accept":"application/json"})
        with urlopen(req,timeout=20) as response:
            return json.load(response)
    initial=page(0,{})
    facets={}
    pending=list(initial["facets"])
    while pending:
        node=pending.pop()
        values=node.get("values",[])
        if node.get("facetParameter") in {"locationCountry","locations"}:
            facets[node["facetParameter"]]=values
        pending.extend(value for value in values if "values" in value)
    if not facets:
        raise ValueError("No country or city filters on this board")
    for field in ("locationCountry","locations"):
        ids=[item["id"] for item in facets.get(field,[]) if in_turkiye(None,item["descriptor"])]
        if ids:
            break
    else:
        return []
    filters={field:ids}
    result=[]
    paths=set()
    expected=None
    while expected is None or len(result)<expected:
        batch=page(len(result),filters)
        if expected is None:
            expected=batch["total"]
        for job in batch["jobPostings"]:
            path=job["externalPath"]
            if path in paths or not path.startswith("/job/"):
                raise ValueError("Invalid or repeated Workday posting path")
            paths.add(path)
            result.append(dict(title=job["title"],url=f"https://{host}/en-US/{site}{path}",
                               location=job.get("locationsText") or "Türkiye"))
        if not batch["jobPostings"] and len(result)<expected:
            raise ValueError("Incomplete Workday pagination")
    return result


def posting_info(url):
    _,site,job,tail=url.path.strip("/").split("/",3)
    if job!="job":
        raise ValueError("Unexpected Workday job path")
    with urlopen(endpoint(url.hostname,site)+"/job/"+tail,timeout=20) as response:
        return json.load(response)["jobPostingInfo"]
