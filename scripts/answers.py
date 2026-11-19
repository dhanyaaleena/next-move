#!/usr/bin/env python3
"""Application-question answers for a job: check them, save them, find gaps.

    python scripts/answers.py check --id "<job id>" --file /tmp/answers.json   # check only
    python scripts/answers.py set   --id "<job id>" --file /tmp/answers.json   # check, then save to jobs.json
    python scripts/answers.py audit                                             # re-check every saved answer
    python scripts/answers.py missing                                           # "To apply"-style jobs with no answers

answers.json is a list: [{"q": "Why do you want to work here?", "a": "...", "limit": 500}, ...]
("limit" is the form's character limit, if it has one.)

Blocking problems (not saved):
  * a number/metric that isn't in cv.json, confirmed_extras or application_facts
  * a skill from cv.ask_before_claiming that the CV doesn't show
  * over the form's character limit, or an empty answer
Warnings (saved, but fix them):
  * stock AI-sounding phrases ("passionate about", "thrilled", "leverage", "I am writing to"…)
  * a "why us" answer that never names the company
  * a long answer that is mostly copied from another company's answer
  * [brackets] left for the user to fill in (listed so they know)
"""
import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, load_profile, me_path, save_json  # noqa: E402
from tailor_cv import nums  # noqa: E402

CLICHES = [
    "passionate about", "i am passionate", "i'm passionate", "thrilled", "excited to apply", "i am writing to",
    "leverage", "leveraging", "synergy", "synergies", "cutting-edge", "cutting edge", "fast-paced environment",
    "dynamic environment", "team player", "results-driven", "detail-oriented", "go-getter", "think outside the box",
    "hit the ground running", "i believe i would be a great fit", "perfect fit", "dream job", "unique blend",
    "proven track record", "spearheaded", "delve", "tapestry", "in today's", "ever-evolving", "seamless",
    "robust solutions", "furthermore", "moreover", "i would be honored", "honoured to", "align perfectly",
]
WHY_US = re.compile(r"\bwhy\b.*\b(here|us|join|work (at|for|here|with us)|this company|our (company|team|mission))\b|\bwhat (excites|draws|attracts) you\b.*\b(us|company|here)\b", re.I)
NEGATION = re.compile(r"\b(haven'?t|have not|not yet|never|no (production |hands-on )?experience|would (need to|have to) learn|keen to learn|pick (it|that) up)\b", re.I)


def bare(ns):
    return {re.sub(r"[^\d.,]", "", n).rstrip(".,") for n in ns}


def aliases(company):
    """Ways an answer may name the company: full name, first word, initials (American Express -> AE/Amex)."""
    co = re.sub(r"\s*\(.*?\)", "", company).strip()
    words = re.findall(r"[A-Za-z0-9&]+", co)
    out = {co.lower()}
    if words:
        out.add(words[0].lower())
        if len(words) > 1:
            out.add("".join(w[0] for w in words).lower())
            out.add((words[0][:2] + words[1][:2]).lower())   # American Express -> amex
    return {a for a in out if len(a) >= 2}


def fact_text(profile):
    pcv = profile.get("cv") or {}
    f = profile.get("application_facts") or {}
    parts = [str(v) for k, v in f.items() if k != "other" and v] + [str(x) for x in f.get("other") or []]
    return " ".join(parts + [str(x) for x in pcv.get("confirmed_extras") or []])


def check(job, answers, profile, cv, others=()):
    errs, warns, todo = [], [], []
    base = (json.dumps(cv, ensure_ascii=False) + " " + fact_text(profile)).lower()
    base_nums = nums(base)
    ask = (profile.get("cv") or {}).get("ask_before_claiming") or []
    co = re.sub(r"\s*\(.*?\)", "", job["company"]).strip()
    for n, item in enumerate(answers, 1):
        q, a = str(item.get("q", "")).strip(), str(item.get("a", "")).strip()
        tag = f"Q{n} “{q[:50]}”"
        if not q or not a:
            errs.append(f"{tag}: empty question or answer")
            continue
        if item.get("limit") and len(a) > int(item["limit"]):
            errs.append(f"{tag}: {len(a)} characters, form allows {item['limit']}")
        found = nums(re.sub(r"\[[^\]]*\]", "", a))
        # "30 seconds" vs "30 s" in the CV: the same figure with a different unit spelling is fine
        odd = sorted(n for n in found - base_nums if not (bare({n}) & bare(base_nums)))
        if odd:
            errs.append(f"{tag}: numbers not in your CV/facts: {', '.join(odd)}")
        for w in ask:
            if w.lower() in base:
                continue
            pat = r"(?<![a-z])" + re.escape(w.lower()) + r"(?![a-z])"
            for sent in re.split(r"(?<=[.!?])\s+", a):
                if re.search(pat, sent.lower()) and not NEGATION.search(sent):
                    errs.append(f"{tag}: claims '{w}' (ask-before-claiming) — confirm with the user, or say honestly you haven't used it")
                    break
        low = a.lower()
        hits = [c for c in CLICHES if c in low]
        if hits:
            warns.append(f"{tag}: sounds generic/AI-written: {', '.join(hits)}")
        named = any(re.search(r"(?<![a-z])" + re.escape(x) + r"(?![a-z])", low) for x in aliases(job["company"]))
        if (WHY_US.search(q) or any(x in q.lower() for x in aliases(job["company"]) if len(x) > 3)) and not named and len(a) > 80:
            warns.append(f"{tag}: a 'why us' answer that never names {co}")
        if len(a) > 200:
            for oq, oa, oco in others:
                if oco != job["company"] and difflib.SequenceMatcher(None, a, oa).ratio() > 0.8:
                    warns.append(f"{tag}: ~same as the answer for {oco} — make it specific")
                    break
        if a.count("—") > 2:
            warns.append(f"{tag}: lots of em dashes — reads as AI-written")
        todo += [f"{tag}: {b}" for b in re.findall(r"\[[^\]]+\]", a)]
    return errs, warns, todo


def report(errs, warns, todo):
    for e in errs:
        print("✘", e)
    for w in warns:
        print("!", w)
    if todo:
        print("For the user to fill in before sending:")
        for t in todo:
            print("  ·", t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("check", "set"):
        s = sub.add_parser(c)
        s.add_argument("--id", required=True)
        s.add_argument("--file", required=True)
    sub.add_parser("audit")
    sub.add_parser("missing")
    a = ap.parse_args()

    profile = load_profile(a.me)
    cv = load_json(me_path(a.me, "cv.json"))
    data = load_json(me_path(a.me, "jobs.json"), default={"jobs": []})
    jobs = data["jobs"]
    others = [(x.get("q", ""), x.get("a", ""), j["company"]) for j in jobs for x in j.get("answers") or []]

    if a.cmd == "missing":
        for j in jobs:
            if not j.get("answers"):
                print(f"{j['id']}\t{j['company']} – {j['role']}")
        return
    if a.cmd == "audit":
        bad = 0
        for j in jobs:
            if not j.get("answers"):
                continue
            errs, warns, _ = check(j, j["answers"], profile, cv, others)
            if errs or warns:
                bad += 1
                print(f"\n== {j['company']} – {j['role']}  ({j['id']})")
                report(errs, warns, [])
        print(f"\n{bad} job(s) with answers to fix")
        return

    job = next((j for j in jobs if j["id"] == a.id), None)
    if not job:
        sys.exit(f"no job with id {a.id!r}")
    answers = load_json(a.file)
    if not isinstance(answers, list):
        sys.exit("answers file must be a list of {q, a}")
    errs, warns, todo = check(job, answers, profile, cv, others)
    report(errs, warns, todo)
    if errs:
        sys.exit("NOT SAVED — fix the ✘ items")
    if a.cmd == "set":
        job["answers"] = [{"q": x["q"].strip(), "a": x["a"].strip()} for x in answers]
        save_json(me_path(a.me, "jobs.json"), data)
        print(f"saved {len(answers)} answers for {job['company']} – {job['role']}")
    else:
        print("ok")


if __name__ == "__main__":
    main()
