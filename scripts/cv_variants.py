#!/usr/bin/env python3
"""Build the fixed set of CV variants and show which one each job should use.

Instead of a tailored CV per job, you keep a handful of CVs (profile.cv.variants), e.g.
Forward Deployed / AI Engineer / Backend / Full Stack. Each variant is a CV JSON in
me/cv_variants/<key>.json, written once by Claude from me/cv.json under the same rules as
a tailored CV (no invented facts, allowed titles only). The tracker's job dialog tells you
which variant to send for each job.

    python scripts/cv_variants.py build              # check + render every variant to PDF
    python scripts/cv_variants.py build --key backend
    python scripts/cv_variants.py pick "Senior Forward Deployed Engineer"
    python scripts/cv_variants.py list               # every job and the variant it uses

PDFs go to <tailored_cv_folder>/CV variants/<Name>_CV - <Label>.pdf. Rebuild after the base
CV changes. To override the rule for one job:  jobs.py update --id ID --json '{"cv_variant": "backend"}'
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import cv_variants, load_json, load_profile, me_path, pick_variant, variant_file  # noqa: E402
from tailor_cv import check, fit_one_page  # noqa: E402


def root_folder(profile, me):
    root = os.path.expanduser(str(profile.get("tailored_cv_folder") or "Tailored CVs"))
    return root if os.path.isabs(root) else me_path(me, root)


def cmd_build(a, profile):
    base = load_json(me_path(a.me, "cv.json"))
    pcv = profile.get("cv") or {}
    vs = [v for v in cv_variants(profile) if not a.key or v["key"] == a.key]
    if not vs:
        sys.exit("no variants: add profile.cv.variants (see examples/profile.example.yaml)")
    bad = 0
    for v in vs:
        src = me_path(a.me, "cv_variants", f"{v['key']}.json")
        if not os.path.exists(src):
            print(f"✘ {v['key']}: {src} is missing — write it from cv.json first")
            bad += 1
            continue
        cv = load_json(src)
        errs, warns = check(base, cv, profile)
        for w in warns:
            print(f"  warning ({v['key']}):", w)
        if errs:
            print(f"✘ {v['key']}: not built —\n    " + "\n    ".join(errs))
            bad += 1
            continue
        out = os.path.join(root_folder(profile, a.me), variant_file(profile, v))
        pages, dropped = fit_one_page(cv, out, pcv.get("links") or [], pcv.get("one_page", True))
        print(f"✔ {v['key']:<14} {out}  ({pages} page{'s' if pages != 1 else ''})" + (f"  trimmed: {len(dropped)}" if dropped else ""))
    if bad:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--key")
    p = sub.add_parser("pick")
    p.add_argument("role")
    sub.add_parser("list")
    a = ap.parse_args()
    profile = load_profile(a.me)
    if a.cmd == "build":
        cmd_build(a, profile)
    elif a.cmd == "pick":
        v = pick_variant(profile, {"role": a.role})
        print(f"{v['key']}  ({v.get('label')})" if v else "no variants defined")
    else:
        for j in load_json(me_path(a.me, "jobs.json"), default={"jobs": []})["jobs"]:
            v = pick_variant(profile, j)
            print(f"{(v or {}).get('key', '-'):<14} {j['company']} – {j['role']}")


if __name__ == "__main__":
    main()
