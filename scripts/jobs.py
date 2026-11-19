#!/usr/bin/env python3
"""Manage me/jobs.json — the list of roles the tracker page shows.

    python scripts/jobs.py add  --json '{...}'          # one job
    python scripts/jobs.py add  --file new_jobs.json     # a list of jobs (refresh results)
    python scripts/jobs.py update --id "acme|backend engineer" --json '{"salary":"£90k"}'
    python scripts/jobs.py known                         # ids, urls and companies already tracked (for searches)
    python scripts/jobs.py list [--location X] [--track Y] [--since 2026-11-01]
    python scripts/jobs.py stats
    python scripts/jobs.py bump                          # set data version to today (marks this refresh's jobs "New")
    python scripts/jobs.py pulled                        # record today as the last pull (next search starts here)

Rules this enforces, so every user's tracker stays consistent:
  * IDs are company|role normalised and never change once a job is stored — the
    browser keys your statuses on them.
  * No duplicates: same ID, or same direct posting URL, is refused.
  * Jobs are never deleted by a refresh. Closed roles are marked by you in the page.
  * location / track must exist in profile.yaml.
  * Where a location needs visa sponsorship, a job needs visa.status of
    "sponsors" or "not_needed" plus evidence — otherwise it's refused
    (pass --allow-unclear to keep it flagged "Visa unclear" instead).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, load_profile, make_id, me_path, save_json, today, url_key  # noqa: E402

FIELDS = ["id", "location", "track", "company", "role", "place", "experience", "salary", "salary_num", "skills", "url", "source",
          "fit", "direct", "note", "visa", "people", "cv_pdf", "posted", "added"]
VISA = {"sponsors", "not_needed", "unclear", "no"}


def load(me):
    return load_json(me_path(me, "jobs.json"), default={"version": today(), "jobs": []})


def validate(job, profile, allow_unclear=False):
    errs = []
    for k in ("company", "role", "url", "location", "track"):
        if not job.get(k):
            errs.append(f"missing '{k}'")
    locs = {l["id"]: l for l in profile.get("locations") or []}
    tracks = {t["id"] for t in profile.get("role_tracks") or []}
    if job.get("location") and job["location"] not in locs:
        errs.append(f"location '{job['location']}' not in profile ({', '.join(locs)})")
    if job.get("track") and job["track"] not in tracks:
        errs.append(f"track '{job['track']}' not in profile ({', '.join(tracks)})")
    if job.get("fit") not in ("High", "Medium"):
        errs.append("fit must be 'High' or 'Medium' (don't add Low-fit jobs)")
    v = job.get("visa") or {}
    if v and v.get("status") not in VISA:
        errs.append(f"visa.status must be one of {sorted(VISA)}")
    loc = locs.get(job.get("location"))
    if loc and loc.get("needs_visa_sponsorship"):
        st = v.get("status", "unclear")
        if st == "no":
            errs.append("posting says no sponsorship, and this location needs it")
        elif st in ("sponsors", "not_needed") and not v.get("evidence"):
            errs.append("visa.evidence is required (quote the posting, or name the register)")
        elif st == "unclear" and not allow_unclear:
            errs.append("visa sponsorship unclear for a location that needs it (use --allow-unclear to keep it flagged)")
    for p in job.get("people") or []:
        if not isinstance(p, dict) or not p.get("name"):
            errs.append("each person needs at least a name")
    return errs


def clean(job):
    j = {k: job[k] for k in FIELDS if k in job and job[k] not in (None, "")}
    j.setdefault("id", make_id(j.get("company"), j.get("role")))
    j.setdefault("direct", True)
    j.setdefault("skills", [])
    j.setdefault("people", [])
    j.setdefault("salary", "Not listed")
    j.setdefault("added", today())
    try:
        j["salary_num"] = float(j.get("salary_num") or 0)
        if j["salary_num"].is_integer():
            j["salary_num"] = int(j["salary_num"])
    except (TypeError, ValueError):
        j["salary_num"] = 0
    return j


def cmd_add(a):
    profile = load_profile(a.me)
    data = load(a.me)
    if a.json:
        incoming = json.loads(a.json)
    else:
        with open(a.file, encoding="utf-8") as f:
            incoming = json.load(f)
    if isinstance(incoming, dict) and "jobs" in incoming:
        incoming = incoming["jobs"]
    if isinstance(incoming, dict):
        incoming = [incoming]
    ids = {j["id"] for j in data["jobs"]}
    urls = {url_key(j["url"]): j["id"] for j in data["jobs"] if j.get("direct", True) and j.get("url")}
    added, skipped, refused = 0, 0, 0
    for raw in incoming:
        j = clean(raw)
        errs = validate(j, profile, a.allow_unclear)
        label = f"{j.get('company')} – {j.get('role')}"
        if errs:
            refused += 1
            print(f"REFUSED  {label}: " + "; ".join(errs))
            continue
        uk = url_key(j["url"]) if j.get("direct", True) else None
        if j["id"] in ids or (uk and uk in urls):
            skipped += 1
            print(f"already tracked  {label}  ({j['id'] if j['id'] in ids else urls[uk]})")
            continue
        data["jobs"].append(j)
        ids.add(j["id"])
        if uk:
            urls[uk] = j["id"]
        added += 1
        print(f"added  {label}  [{j['location']} · {j['track']} · {j['fit']}]")
    if added and not a.no_bump:
        data["version"] = today()
    save_json(me_path(a.me, "jobs.json"), data)
    print(f"\n{added} added, {skipped} already tracked, {refused} refused. Total {len(data['jobs'])}.")


def cmd_update(a):
    data = load(a.me)
    patch = json.loads(a.json)
    patch.pop("id", None)
    hit = [j for j in data["jobs"] if j["id"] == a.id]
    if not hit:
        sys.exit(f"no job with id {a.id!r}")
    j = hit[0]
    j.update(patch)
    errs = validate(j, load_profile(a.me), allow_unclear=True)
    if errs:
        sys.exit("update would make the job invalid: " + "; ".join(errs))
    save_json(me_path(a.me, "jobs.json"), data)
    print("updated", a.id)


def cmd_known(a):
    data = load(a.me)
    out = {"ids": sorted(j["id"] for j in data["jobs"]),
           "urls": sorted(url_key(j["url"]) for j in data["jobs"] if j.get("url")),
           "companies": sorted({j["company"] for j in data["jobs"]})}
    print(json.dumps(out, ensure_ascii=False, indent=0 if a.compact else 1))


def cmd_list(a):
    for j in load(a.me)["jobs"]:
        if a.location and j.get("location") != a.location:
            continue
        if a.track and j.get("track") != a.track:
            continue
        if a.since and str(j.get("added", "")) < a.since:
            continue
        v = (j.get("visa") or {}).get("status", "-")
        print(f"{j.get('added','')}  {j['fit']:<6} {j['location']:<14} {j['track']:<14} visa:{v:<10} {j['company']} – {j['role']}")


def cmd_stats(a):
    from collections import Counter
    data = load(a.me)
    jobs = data["jobs"]
    print(f"data version {data.get('version')} · last pull {data.get('last_pull', 'never')} · {len(jobs)} jobs")
    for key in ("location", "track", "fit"):
        print(f"  by {key}: " + ", ".join(f"{k} {n}" for k, n in Counter(j.get(key) for j in jobs).most_common()))
    print("  by visa: " + ", ".join(f"{k} {n}" for k, n in Counter((j.get('visa') or {}).get('status', '-') for j in jobs).most_common()))
    print(f"  added today: {sum(1 for j in jobs if j.get('added') == today())}")


def cmd_pulled(a):
    data = load(a.me)
    data["last_pull"] = today()
    save_json(me_path(a.me, "jobs.json"), data)
    print("last pull", data["last_pull"])


def cmd_bump(a):
    data = load(a.me)
    data["version"] = today()
    save_json(me_path(a.me, "jobs.json"), data)
    print("data version", data["version"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me", help="your data folder (default ./me)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--json"); g.add_argument("--file")
    s.add_argument("--allow-unclear", action="store_true"); s.add_argument("--no-bump", action="store_true")
    s = sub.add_parser("update"); s.add_argument("--id", required=True); s.add_argument("--json", required=True)
    s = sub.add_parser("known"); s.add_argument("--compact", action="store_true")
    s = sub.add_parser("list"); s.add_argument("--location"); s.add_argument("--track"); s.add_argument("--since")
    sub.add_parser("stats"); sub.add_parser("bump"); sub.add_parser("pulled")
    a = ap.parse_args()
    # allow --me after the subcommand too
    globals()["cmd_" + a.cmd](a)
