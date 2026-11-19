#!/usr/bin/env python3
"""Check, fit and save a CV tailored for one job.

    python scripts/tailor_cv.py --id "acme|backend engineer" --cv /tmp/acme_cv.json
    python scripts/tailor_cv.py --id "acme|backend engineer" --base            # untailored copy
    python scripts/tailor_cv.py --list-missing                                  # jobs with no tailored CV yet

Claude writes the tailored CV as JSON in the same shape as me/cv.json, then runs
this. The script enforces the rules every user gets:

  * Fixed facts: name, contact, companies, roles, dates, schools stay exactly as in cv.json,
    and experience entries stay in the same order.
  * Title must be your own title or one of profile.cv.allowed_titles.
  * No invented numbers: every metric (95%, 200K+, 300 ms…) must already appear in cv.json
    or in profile.cv.confirmed_extras.
  * No invented skills: skill items must appear somewhere in cv.json / confirmed_extras.
  * Anything in profile.cv.ask_before_claiming is refused unless you've confirmed it.
  * One page (if profile.cv.one_page): the last bullets of the oldest roles are dropped
    first until it fits; anything dropped is reported.

Output: <tailored_cv_folder>/<Company>/<Name>_CV.pdf  (or "<Company> - <Role>" when you
track several roles there), the tailored JSON in me/tailored/, and the job's cv_pdf
field in jobs.json so the tracker shows "📎 PDF ready".
"""
import argparse
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, load_profile, me_path, save_json  # noqa: E402

NUM_RE = re.compile(r"(?<![A-Za-z\d.,])\d+(?:[.,]\d+)?(?:\s?(?:%|k\+?|\+|x|ms|min|s|m)(?![a-z]))?", re.I)
FIXED_EXP = ("company", "role", "location", "dates")
FIXED_EDU = ("degree", "school", "location", "dates")


def nums(s):
    return {n.replace(" ", "").lower() for n in NUM_RE.findall(re.sub(r"\*\*", "", str(s)))}


def safe(s):
    return re.sub(r"\s+", " ", re.sub(r'[/\\:*?"<>|]+', " ", str(s))).strip()


def check(base, cv, profile):
    """Return (errors, warnings). Errors block saving."""
    errs, warns = [], []
    pcv = profile.get("cv") or {}
    extras = " ".join(pcv.get("confirmed_extras") or [])
    for k in ("name", "contact", "rightToWork", "education"):
        if k in base and cv.get(k) != base.get(k):
            errs.append(f"'{k}' must stay exactly as in cv.json")
    be, te = base.get("experience", []), cv.get("experience", [])
    if len(be) != len(te):
        errs.append(f"experience must keep all {len(be)} entries in the same order (got {len(te)})")
    else:
        for a, b in zip(be, te):
            for k in FIXED_EXP:
                if a.get(k) != b.get(k):
                    errs.append(f"experience '{a.get('company')}': '{k}' changed")
            if not b.get("bullets"):
                errs.append(f"experience '{a.get('company')}' has no bullets")
    if len(base.get("projects") or []) != len(cv.get("projects") or []):
        errs.append("projects must keep the same entries")
    allowed = set(pcv.get("allowed_titles") or []) | {base.get("title")}
    if cv.get("title") not in allowed:
        errs.append(f"title '{cv.get('title')}' not allowed; use one of: {', '.join(sorted(t for t in allowed if t))}")

    base_txt = json.dumps(base, ensure_ascii=False).lower() + " " + extras.lower()
    new_parts = [cv.get("title", ""), cv.get("profile", "")]
    for x in te + (cv.get("projects") or []):
        new_parts += x.get("bullets", [])
    new_txt = " ".join(map(str, new_parts))
    odd = sorted(nums(new_txt) - nums(base_txt))
    if odd:
        errs.append("numbers not in your CV: " + ", ".join(odd))
    unknown = []
    for line in cv.get("skills") or []:
        for g in line:
            if g.get("label", "").lower() == "ways of working":
                continue
            for it in g.get("items", []):
                if str(it).lower() not in base_txt:
                    unknown.append(it)
    if unknown:
        errs.append("skills not in your CV (add them to cv.json or confirmed_extras if true): " + ", ".join(unknown))
    full = (new_txt + " " + json.dumps(cv.get("skills"), ensure_ascii=False)).lower()
    for w in pcv.get("ask_before_claiming") or []:
        if re.search(r"(?<![a-z])" + re.escape(w.lower()) + r"(?![a-z])", full) and w.lower() not in base_txt:
            errs.append(f"'{w}' is on your ask-before-claiming list — confirm it with the user first")
    if len(re.sub(r"\*\*", "", cv.get("profile", ""))) < 60:
        warns.append("profile is very short")
    return errs, warns


def fit_one_page(cv, path, links, one_page=True):
    from cv_pdf import render
    pages, dropped = render(cv, path, links), []
    if not one_page:
        return pages, dropped
    # Trim order: last bullet of the oldest role first, then move to newer roles; keep >=1 bullet each.
    # A "Ways of Working" skills line, if any, goes before touching the two most recent roles.
    while pages > 1:
        exp = cv.get("experience", [])
        target = None
        for idx in range(len(exp) - 1, 1, -1):
            if len(exp[idx]["bullets"]) > 1:
                target = idx
                break
        if target is None and any(g[0].get("label", "").lower() == "ways of working" for g in cv.get("skills", [])):
            cv["skills"] = [ln for ln in cv["skills"] if ln[0].get("label", "").lower() != "ways of working"]
            dropped.append("Ways of Working line")
        elif target is None:
            for idx in range(min(len(exp), 2) - 1, -1, -1):
                if len(exp[idx]["bullets"]) > 2:
                    target = idx
                    break
            if target is None:
                break
        if target is not None:
            b = exp[target]["bullets"].pop()
            dropped.append(f"{exp[target]['company']}: “{re.sub(r'[*]', '', b)[:60]}…”")
        pages = render(cv, path, links)
    return pages, dropped


def folder_for(job, jobs):
    co = safe(re.sub(r"\s*\((?:via|client)[^)]*\)", "", job["company"]))
    same = [j for j in jobs if j["company"] == job["company"] and j["id"] != job["id"]]
    return co if not same else safe(f"{co} - {re.sub(r'[(].*?[)]', '', job['role']).strip()[:40]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me")
    ap.add_argument("--id", help="job id from jobs.json")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--cv", help="tailored CV JSON written by Claude")
    g.add_argument("--base", action="store_true", help="file the base CV for this job, untailored")
    ap.add_argument("--list-missing", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()

    profile = load_profile(a.me)
    base = load_json(me_path(a.me, "cv.json"))
    data = load_json(me_path(a.me, "jobs.json"), default={"jobs": []})
    jobs = data["jobs"]

    if a.list_missing:
        for j in jobs:
            if not j.get("cv_pdf"):
                print(f"{j['id']}\t{j['company']} – {j['role']}")
        return
    if not a.id or not (a.cv or a.base):
        sys.exit("need --id and --cv (or --base)")
    job = next((j for j in jobs if j["id"] == a.id), None)
    if not job:
        sys.exit(f"no job with id {a.id!r} in jobs.json")

    cv = copy.deepcopy(base) if a.base else load_json(a.cv)
    errs, warns = check(base, cv, profile)
    for w in warns:
        print("warning:", w)
    if errs:
        sys.exit("NOT SAVED — fix these:\n  - " + "\n  - ".join(errs))
    if a.check_only:
        print("ok")
        return

    pcv = profile.get("cv") or {}
    root = os.path.expanduser(str(profile.get("tailored_cv_folder") or "Tailored CVs"))
    if not os.path.isabs(root):
        root = me_path(a.me, root)
    folder = folder_for(job, jobs)
    fname = re.sub(r"[^A-Za-z0-9]+", "_", str(base["name"]).title()).strip("_") + "_CV.pdf"
    out = os.path.join(root, folder, fname)
    pages, dropped = fit_one_page(cv, out, pcv.get("links") or [], pcv.get("one_page", True))
    save_json(me_path(a.me, "tailored", re.sub(r"[^a-z0-9]+", "_", a.id) + ".json"), cv)
    job["cv_pdf"] = f"{folder}/{fname}"
    save_json(me_path(a.me, "jobs.json"), data)
    print(f"saved {out}  ({pages} page{'s' if pages != 1 else ''})")
    if dropped:
        print("trimmed to fit one page: " + "; ".join(dropped))
    if pages > 1:
        print("warning: still longer than one page — shorten the profile or bullets and run again")


if __name__ == "__main__":
    main()
