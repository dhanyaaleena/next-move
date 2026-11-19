#!/usr/bin/env python3
"""Pull candidate jobs that match your profile, for Claude to review.

    python scripts/search_jobs.py                     # all sources in profile.search.sources
    python scripts/search_jobs.py --source linkedin   # just one source
    python scripts/search_jobs.py --limit-queries 6   # fewer LinkedIn queries (faster)

Writes me/candidates.json: a list of postings not already in jobs.json, each
with a suggested location group and role track. These are *candidates* only —
the refresh skill opens each one, checks fit, language, years asked and visa
evidence, and adds the good ones with scripts/jobs.py add.

Sources (no logins, no API keys):
  linkedin       public LinkedIn job search, one query per (title x location)
  ats_watchlist  Greenhouse / Lever / Ashby / Workable boards of the companies in profile.watchlist
Web search across country job boards is done by Claude itself, not this script.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_country, load_json, load_profile, make_id, me_path, save_json, today, url_key  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept-Language": "en-GB,en;q=0.9"}


def get(url, tries=3, as_json=False):
    for attempt in range(tries):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read().decode("utf8", "ignore")
            return json.loads(raw) if as_json else raw
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return None
            time.sleep(4 * (attempt + 1))
        except Exception:
            time.sleep(4 * (attempt + 1))
    return None


def text(fr):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fr or ""))).strip()


# ── matching against the profile ─────────────────────────────────────────────
STOP = {"engineer", "developer", "software", "senior", "junior", "lead", "staff", "principal", "the", "and", "of", "-"}


def title_matcher(profile):
    """Return f(title) -> track id or None. A title matches a track if it contains
    all the 'meaningful' words of one of that track's search titles."""
    rules = []
    for t in profile.get("role_tracks") or []:
        for q in t.get("titles") or [t.get("label") or t["id"]]:
            words = [w for w in re.findall(r"[a-z0-9+#.]+", q.lower()) if w not in STOP]
            rules.append((t["id"], words or re.findall(r"[a-z0-9+#.]+", q.lower())))
    generic = re.compile(r"\b(engineer|developer|scientist|architect|sre|programmer)\b", re.I)

    def match(title):
        tl = title.lower()
        for tid, words in rules:
            if all(re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", tl) for w in words) and (generic.search(tl) or len(words) > 1):
                return tid
        return None
    return match


def location_matcher(profile):
    """Return f(place_text, hint) -> location group id or None.
    A place matches a group if it names one of the group's places; remote postings
    go to a group that lists a "Remote ..." place; a group with no places matches
    its whole country."""
    groups = []
    for l in profile.get("locations") or []:
        pack = load_country(l.get("country", "")) or {}
        places = [p.lower() for p in (l.get("places") or [])]
        cities = [p for p in places if not p.startswith("remote")]
        groups.append((l["id"], cities, any(p.startswith("remote") for p in places), (pack.get("name") or "").lower()))

    def match(place, hint=None):
        if hint:
            return hint
        s = (place or "").lower()
        for gid, cities, _, _ in groups:
            if any(c in s for c in cities):
                return gid
        if "remote" in s:
            for gid, _, remote, _ in groups:
                if remote:
                    return gid
        for gid, cities, remote, country in groups:
            if country and not cities and not remote and country in s:
                return gid
        return None
    return match


def avoid(profile, title, company):
    fit = profile.get("fit") or {}
    t = f"{title} {company}".lower()
    if any(k.lower() in t for k in fit.get("avoid_keywords") or []):
        return True
    if company and company.lower() in {c.lower() for c in fit.get("avoid_companies") or []}:
        return True
    agencies = [a.lower() for a in (profile.get("search") or {}).get("skip_agencies") or []]
    if company and any(a in company.lower() for a in agencies):
        return True
    sen = set(profile.get("seniority") or [])
    if sen and "junior" not in sen and re.search(r"\b(intern|internship|graduate|junior|apprentice)\b", title, re.I):
        return True
    if sen and not sen & {"staff", "lead"} and re.search(r"\b(principal|director|head of|vp)\b", title, re.I):
        return True
    return False


# ── sources ──────────────────────────────────────────────────────────────────
def parse_linkedin(page):
    """Parse the HTML list returned by LinkedIn's public job search."""
    out = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", page or "", re.S):
        jid = re.search(r"jobPosting:(\d+)", li) or re.search(r"/jobs/view/[^\"?]*?-?(\d{8,})", li)
        if not jid:
            continue
        g = lambda p: text((re.search(p, li, re.S) or [None, ""])[1])  # noqa: E731
        out.append({
            "source": "LinkedIn", "url": f"https://www.linkedin.com/jobs/view/{jid.group(1)}",
            "role": g(r'base-search-card__title[^>]*>(.*?)</h3>'),
            "company": g(r'base-search-card__subtitle[^>]*>(.*?)</h4>'),
            "place": g(r'job-search-card__location[^>]*>(.*?)</span>'),
            "posted": (re.search(r'datetime="([\d-]+)"', li) or [None, ""])[1],
        })
    return out


def linkedin(profile, days, max_queries, per_query=25):
    """Public LinkedIn search (jobs-guest endpoint). One page per title x place."""
    out, n = [], 0
    secs = max(1, days) * 86400
    pairs = []
    for l in profile.get("locations") or []:
        pack = load_country(l.get("country", "")) or {}
        places = [p for p in (l.get("places") or []) if "remote" not in p.lower()] or [pack.get("linkedin_location") or l.get("label")]
        remote = any("remote" in p.lower() for p in (l.get("places") or []))
        for t in profile.get("role_tracks") or []:
            for title in (t.get("titles") or [t["id"]])[:2]:
                for p in places[:3]:
                    pairs.append((title, p, l["id"], t["id"], remote and not l.get("places")))
                if remote:
                    pairs.append((title, pack.get("linkedin_location") or "European Union", l["id"], t["id"], True))
    for title, place, loc_id, track_id, remote in pairs[:max_queries]:
        q = {"keywords": title, "location": place, "f_TPR": f"r{secs}", "start": 0}
        if remote:
            q["f_WT"] = 2
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?" + urllib.parse.urlencode(q)
        page = get(url)
        n += 1
        if not page:
            print(f"  linkedin: no response for {title!r} in {place!r} (rate-limited?)", file=sys.stderr)
            time.sleep(8)
            continue
        for r in parse_linkedin(page)[:per_query]:
            out.append(dict(r, hint_location=loc_id, hint_track=track_id, query=f"{title} @ {place}"))
        time.sleep(2.5)  # be polite; LinkedIn rate-limits bursts
    print(f"  linkedin: {n} queries, {len(out)} postings", file=sys.stderr)
    return out


def ats_board(c):
    ats, slug, name = (c.get("ats") or "").lower(), c.get("slug"), c.get("name") or c.get("slug")
    res = []
    if ats == "greenhouse":
        d = get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", as_json=True) or {}
        for j in d.get("jobs", []):
            res.append({"role": j.get("title"), "url": j.get("absolute_url"), "place": (j.get("location") or {}).get("name", ""),
                        "posted": (j.get("updated_at") or "")[:10]})
    elif ats == "lever":
        d = get(f"https://api.lever.co/v0/postings/{slug}?mode=json", as_json=True) or []
        for j in d:
            ts = j.get("createdAt")
            res.append({"role": j.get("text"), "url": j.get("hostedUrl"), "place": (j.get("categories") or {}).get("location", ""),
                        "posted": dt.datetime.utcfromtimestamp(ts / 1000).date().isoformat() if ts else ""})
    elif ats == "ashby":
        d = get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true", as_json=True) or {}
        for j in d.get("jobs", []):
            comp = (j.get("compensation") or {}).get("compensationTierSummary") or ""
            res.append({"role": j.get("title"), "url": j.get("jobUrl"), "place": j.get("location", "") + (" (remote)" if j.get("isRemote") else ""),
                        "posted": (j.get("publishedAt") or "")[:10], "salary": comp})
    elif ats == "workable":
        d = get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}", as_json=True) or {}
        for j in d.get("jobs", []):
            place = ", ".join(x for x in (j.get("city"), j.get("country")) if x) + (" (remote)" if j.get("telecommuting") else "")
            res.append({"role": j.get("title"), "url": j.get("url") or j.get("application_url"), "place": place,
                        "posted": (j.get("published_on") or "")[:10]})
    else:
        print(f"  watchlist: unknown ats {ats!r} for {name}", file=sys.stderr)
    for r in res:
        r.update(company=name, source=f"{ats.capitalize()} (company ATS)")
    return res


ATS_URL = [
    ("ashby", re.compile(r"jobs\.ashbyhq\.com/([^/?#]+)")),
    ("greenhouse", re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/([^/?#]+)")),
    ("lever", re.compile(r"jobs\.(?:eu\.)?lever\.co/([^/?#]+)")),
    ("workable", re.compile(r"apply\.workable\.com/([^/?#]+)")),
]


def tracked_boards(jobs):
    """Career boards of companies already in the tracker, read from their posting URLs."""
    out, seen = [], set()
    for j in jobs:
        for ats, rx in ATS_URL:
            m = rx.search(j.get("url") or "")
            if m and (ats, m.group(1).lower()) not in seen:
                seen.add((ats, m.group(1).lower()))
                out.append({"name": j["company"], "ats": ats, "slug": m.group(1)})
    return out


def watchlist(profile, extra=()):
    out, seen = [], set()
    for c in list(profile.get("watchlist") or []) + list(extra):
        k = ((c.get("ats") or "").lower(), str(c.get("slug")).lower())
        if k in seen:
            continue
        seen.add(k)
        rows = ats_board(c)
        print(f"  watchlist: {c.get('name')}: {len(rows)} open roles", file=sys.stderr)
        out += rows
    return out


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me")
    ap.add_argument("--source", choices=["linkedin", "ats_watchlist"], action="append")
    ap.add_argument("--days", type=int, help="override search.freshness_days")
    ap.add_argument("--limit-queries", type=int, default=24, help="max LinkedIn queries (default 24)")
    ap.add_argument("--out")
    a = ap.parse_args()

    profile = load_profile(a.me)
    search = profile.get("search") or {}
    jobs_doc = load_json(me_path(a.me, "jobs.json"), default={"jobs": []})
    days = a.days or int(search.get("freshness_days") or 14)
    if not a.days and jobs_doc.get("last_pull"):
        # only look back to the last pull (+1 day overlap), capped at freshness_days
        since = (dt.date.today() - dt.date.fromisoformat(jobs_doc["last_pull"][:10])).days + 1
        days = max(1, min(days, since))
    sources = a.source or [s for s in (search.get("sources") or ["linkedin", "ats_watchlist"]) if s in ("linkedin", "ats_watchlist")]
    jobs = jobs_doc["jobs"]
    known_ids = {j["id"] for j in jobs}
    known_urls = {url_key(j["url"]) for j in jobs if j.get("url")}

    raw = []
    if "linkedin" in sources:
        raw += linkedin(profile, days, a.limit_queries)
    if "ats_watchlist" in sources:
        raw += watchlist(profile, tracked_boards(jobs) if search.get("sweep_tracked_boards", True) else ())

    tmatch, lmatch = title_matcher(profile), location_matcher(profile)
    cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    seen, out = set(), []
    stats = {"raw": len(raw), "known": 0, "title": 0, "location": 0, "old": 0, "avoid": 0, "dupe": 0}
    for r in raw:
        if not r.get("role") or not r.get("url"):
            continue
        jid, uk = make_id(r.get("company"), r["role"]), url_key(r["url"])
        if jid in known_ids or uk in known_urls:
            stats["known"] += 1; continue
        if jid in seen or uk in seen:
            stats["dupe"] += 1; continue
        track = tmatch(r["role"]) or (r.get("hint_track") if r.get("source") == "LinkedIn" else None)
        if not track:
            stats["title"] += 1; continue
        loc = lmatch(r.get("place"), r.get("hint_location"))
        if not loc:
            stats["location"] += 1; continue
        if r.get("posted") and r["posted"] < cutoff:
            stats["old"] += 1; continue
        if avoid(profile, r["role"], r.get("company", "")):
            stats["avoid"] += 1; continue
        seen.update((jid, uk))
        r.pop("hint_location", None); r.pop("hint_track", None)
        out.append(dict(r, id=jid, location=loc, track=track))

    path = a.out or me_path(a.me, "candidates.json")
    save_json(path, {"generated": today(), "days": days, "candidates": out})
    print(f"{len(out)} new candidates -> {path}")
    print("filtered: " + ", ".join(f"{k} {v}" for k, v in stats.items()))


if __name__ == "__main__":
    main()
