#!/usr/bin/env python3
"""Build your tracker page from  me/profile.yaml + me/cv.json + me/jobs.json.

    python scripts/build.py                 # writes me/output/<Name>_Job_Tracker.html
    python scripts/build.py --me path/to/me --out tracker.html
    python scripts/build.py --example       # builds the demo from examples/

The page is one self-contained HTML file. Your statuses, notes and tailored CVs
are saved in the browser, keyed by job ID, so rebuilding never loses them.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, load_country, load_json, load_yaml, make_id, me_path, today  # noqa: E402

TEMPLATE = os.path.join(ROOT, "template", "tracker.html")
MARK = "/*__CONFIG__*/"
PROFILE_KEYS = ["name", "tracker_title", "tagline", "storage_prefix", "role_tracks", "locations", "fit",
                "cv", "outreach", "features", "tailored_cv_folder"]


def js(obj):
    # JSON is valid JS; escape "</" so text inside can never close the <script> tag.
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def check(profile, cv, jobs):
    """Return a list of problems that would make the page wrong or empty."""
    errs, warns = [], []
    for k in ("name", "storage_prefix", "role_tracks", "locations"):
        if not profile.get(k):
            errs.append(f"profile.yaml: '{k}' is missing")
    if not re.fullmatch(r"[a-z0-9_]+", str(profile.get("storage_prefix", "x"))):
        errs.append("profile.yaml: storage_prefix may only use a-z, 0-9 and _")
    for k in ("name", "title", "profile", "skills", "experience"):
        if not cv.get(k):
            errs.append(f"cv.json: '{k}' is missing")
    locs = {l.get("id") for l in profile.get("locations") or []}
    tracks = {t.get("id") for t in profile.get("role_tracks") or []}
    seen = {}
    for n, j in enumerate(jobs.get("jobs", []), 1):
        where = f"jobs.json job {n} ({j.get('company')} – {j.get('role')})"
        for k in ("company", "role", "url", "location", "track"):
            if not j.get(k):
                errs.append(f"{where}: '{k}' is missing")
        if j.get("location") and j["location"] not in locs:
            warns.append(f"{where}: location '{j['location']}' isn't in profile.locations (shown under 'Other locations')")
        if j.get("track") and j["track"] not in tracks:
            warns.append(f"{where}: track '{j['track']}' isn't in profile.role_tracks")
        jid = j.get("id") or make_id(j.get("company"), j.get("role"))
        if jid in seen:
            warns.append(f"{where}: same ID as job {seen[jid]} — the page will show it once")
        seen[jid] = n
    return errs, warns


def portals_for(profile, jobs):
    out, urls = [], set()

    def add(name, desc, url, badge):
        if url and url not in urls:
            urls.add(url)
            out.append([name, desc, url, badge])

    for p in jobs.get("portals") or []:
        add(*(p + [""] * 4)[:4]) if isinstance(p, list) else add(p.get("name"), p.get("desc", ""), p.get("url"), p.get("badge", ""))
    for p in profile.get("portals") or []:
        add(p.get("name"), p.get("desc", ""), p.get("url"), p.get("badge", "Yours"))
    done = set()
    for loc in profile.get("locations") or []:
        code = loc.get("country")
        if not code or code in done:
            continue
        done.add(code)
        pack = load_country(code)
        for b in (pack or {}).get("boards") or []:
            add(b["name"], b.get("desc", ""), b["url"], code)
    add("LinkedIn Jobs", "Set your location and title filters", "https://www.linkedin.com/jobs/", "Global")
    return out


def build(me, out=None, example=False):
    if example:
        profile = load_yaml(os.path.join(ROOT, "examples", "profile.example.yaml"))
        cv = load_json(os.path.join(ROOT, "examples", "cv.example.json"))
        jobs = load_json(os.path.join(ROOT, "examples", "jobs.example.json"))
        out = out or os.path.join(ROOT, "examples", "Example_Job_Tracker.html")
    else:
        profile = load_yaml(me_path(me, "profile.yaml"))
        cv = load_json(me_path(me, "cv.json"))
        jobs = load_json(me_path(me, "jobs.json"), default={"version": today(), "jobs": []})
    errs, warns = check(profile, cv, jobs)
    for w in warns:
        print("warning:", w)
    if errs:
        sys.exit("Can't build:\n  " + "\n  ".join(errs))

    data = {"jobs": jobs.get("jobs", []), "portals": portals_for(profile, jobs)}
    cfg = (
        "var PROFILE = " + js({k: profile.get(k) for k in PROFILE_KEYS if profile.get(k) is not None}) + ";\n"
        "var DEFAULT_CV_JSON = " + js(cv) + ";\n"
        "var DATA = " + js(data) + ";\n"
        "var DATA_VERSION = " + js(str(jobs.get("version") or today())) + ";\n"
    )
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    if html.count(MARK) != 1:
        sys.exit("template/tracker.html is missing the config marker")
    html = html.replace(MARK, cfg)

    if not out and not example and profile.get("output_file"):
        out = os.path.expanduser(str(profile["output_file"]))
        if not os.path.isabs(out):
            out = me_path(me, out)
    if not out:
        base = re.sub(r"[^A-Za-z0-9]+", "_", str(profile.get("name", "My"))).strip("_")
        out = me_path(me, "output", f"{base}_Job_Tracker.html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"built {out}  ({len(data['jobs'])} jobs, data version {jobs.get('version')})")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me", help="folder with profile.yaml, cv.json, jobs.json (default: ./me)")
    ap.add_argument("--out", help="output HTML path")
    ap.add_argument("--example", action="store_true", help="build the demo tracker from examples/")
    a = ap.parse_args()
    build(a.me, a.out, a.example)
