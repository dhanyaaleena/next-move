#!/usr/bin/env python3
"""Import jobs from an older tracker (array rows) into me/jobs.json.

    python scripts/import_legacy.py old_tracker.html      # reads `var DATA = {...}` and DATA_VERSION
    python scripts/import_legacy.py old_jobs.json         # {"jobs": [[...], ...]}

Old row format:
  [section, category, company, role, location, salary text, salary number, skills[],
   url, source, fit, direct, note, id, people[], cv path, answers[]]
  answer: [question, answer]
  person: [name, title, linkedin, tag, email?, email confidence?]

Section and category become the job's location and track, so make sure
profile.yaml has location groups / role tracks with those exact ids.
IDs are kept as they are, so statuses saved in the browser still line up.
Jobs already in jobs.json (same id) are skipped; add --update to copy their
answers / people / cv path / note across from the old file.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, make_id, me_path, save_json, today  # noqa: E402


def read(path):
    raw = open(path, encoding="utf-8").read()
    if path.lower().endswith((".html", ".htm")):
        m = re.search(r"var DATA\s*=\s*(\{.*?\})\s*;\s*\n", raw, re.S)
        if not m:
            sys.exit("couldn't find `var DATA = {...};` in that file")
        data = json.loads(m.group(1))
        v = re.search(r"var DATA_VERSION\s*=\s*'([\d-]+)'", raw)
        return data, v.group(1) if v else None
    return json.loads(raw), None


def convert(r):
    r = list(r) + [None] * (18 - len(r))
    people = []
    for p in r[14] or []:
        p = list(p) + [None] * (6 - len(p))
        people.append({k: v for k, v in zip(["name", "title", "url", "tag", "email", "email_confidence"], p) if v})
    j = {"id": r[13] or make_id(r[2], r[3]), "location": r[0], "track": r[1], "company": r[2], "role": r[3],
         "place": r[4], "salary": r[5] or "Not listed", "salary_num": r[6] or 0, "skills": r[7] or [], "url": r[8],
         "source": r[9] or "", "fit": r[10] or "Medium", "direct": bool(r[11]), "note": r[12] or "", "people": people}
    if r[15]:
        j["cv_pdf"] = r[15]
    if r[16]:
        j["answers"] = [{"q": a[0], "a": a[1]} for a in r[16] if isinstance(a, (list, tuple)) and len(a) >= 2]
    if r[17]:
        j["visa"] = r[17]
    return j


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    me = None
    if "--me" in sys.argv:
        me = sys.argv[sys.argv.index("--me") + 1]
    src, version = read(sys.argv[1])
    path = me_path(me, "jobs.json")
    cur = load_json(path, default={"version": today(), "jobs": []})
    have = {j["id"] for j in cur["jobs"]}
    n = 0
    update = "--update" in sys.argv
    byid = {j["id"]: j for j in cur["jobs"]}
    for r in src.get("jobs", []):
        j = convert(r) if isinstance(r, list) else r
        if j["id"] in have:
            if update:  # refresh fields from the old tracker (e.g. new answers/people), keep everything else
                old = byid[j["id"]]
                for k in ("answers", "people", "cv_pdf", "note"):
                    if j.get(k) and j[k] != old.get(k):
                        old[k] = j[k]
            continue
        cur["jobs"].append(j)
        have.add(j["id"])
        n += 1
    if version:
        cur["version"] = version
        cur.setdefault("last_pull", version)
    if src.get("portals") and not cur.get("portals"):
        cur["portals"] = src["portals"]
    save_json(path, cur)
    locs = sorted({j["location"] for j in cur["jobs"]})
    tracks = sorted({j["track"] for j in cur["jobs"]})
    print(f"imported {n} jobs into {path} (total {len(cur['jobs'])})")
    print("location ids used:", locs)
    print("track ids used:   ", tracks)
    print("→ profile.yaml needs location groups and role tracks with exactly these ids.")


if __name__ == "__main__":
    main()
