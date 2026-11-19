#!/usr/bin/env python3
"""Fetch a job posting's full text, without logging in.

    python scripts/fetch_posting.py <url or LinkedIn job id>

Handles LinkedIn (public guest endpoint), Ashby, Greenhouse, Lever and Workable
links through their public APIs. Prints JSON: title, company, location,
salary (if published), description — and, for Greenhouse, the application
form's custom questions. For other boards, read the questions from the apply
page (web fetch or browser). For any other site it exits with a
message — use web fetch or a browser instead.
"""
import html
import json
import re
import sys
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def get(url, want=None, tries=4):
    for attempt in range(tries):
        try:
            s = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read().decode("utf8", "ignore")
            if want is None or want(s):
                return s
        except Exception:
            pass
        time.sleep(6 * (attempt + 1))  # back off; LinkedIn rate-limits bursts
    return ""


def text(fragment):
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", fragment or "", flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", s)).strip()


def linkedin(arg):
    m = re.search(r"(?:currentJobId=|/view/|jobPosting/|-)(\d{8,})", arg) or re.fullmatch(r"(\d{8,})", arg.strip())
    if not m:
        return None
    jid = m.group(1)
    ok = lambda s: "show-more-less-html__markup" in s or "description__text" in s  # noqa: E731
    s = get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}", ok) or get(f"https://www.linkedin.com/jobs/view/{jid}", ok)
    if not s:
        sys.exit("LinkedIn did not return the posting (rate-limited or removed). Wait a minute and retry, or open it in a browser.")
    g = lambda p: text((re.search(p, s, re.S) or [None, ""])[1])  # noqa: E731
    return dict(url=f"https://www.linkedin.com/jobs/view/{jid}", source="LinkedIn",
                title=g(r"top-card-layout__title[^>]*>(.*?)<") or g(r"<title>(.*?)</title>"),
                company=g(r"topcard__org-name-link[^>]*>(.*?)</a>"),
                location=g(r"topcard__flavor--bullet[^>]*>(.*?)</span>"),
                criteria=[text(x) for x in re.findall(r"description__job-criteria-text[^>]*>(.*?)<", s, re.S)],
                salary=g(r"salary compensation__salary[^>]*>(.*?)<"),
                description=g(r"show-more-less-html__markup[^>]*>(.*?)</div>"))


def ashby(url):
    m = re.search(r"jobs\.ashbyhq\.com/([^/?#]+)/([0-9a-f-]{36})", url)
    if not m:
        return None
    board, jid = m.groups()
    d = json.loads(get(f"https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true") or "{}")
    j = next((x for x in d.get("jobs", []) if x.get("id") == jid or jid in str(x.get("jobUrl"))), None)
    if not j:
        sys.exit("Not on the company's Ashby board any more — the role may be closed.")
    return dict(url=url, source="Ashby (company ATS)", title=j.get("title"), company=board, location=j.get("location"),
                remote=j.get("isRemote"), salary=(j.get("compensation") or {}).get("compensationTierSummary") or "",
                description=j.get("descriptionPlain") or text(j.get("descriptionHtml")))


def greenhouse(url):
    m = re.search(r"greenhouse\.io/(?:embed/job_app\?for=)?([^/?#&]+)/jobs/(\d+)", url) or re.search(r"[?&]for=([^&]+).*?[?&]token=(\d+)", url)
    if not m:
        return None
    board, jid = m.groups()
    s = get(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}?questions=true")
    if not s:
        sys.exit("Greenhouse didn't return the job — it may be closed.")
    j = json.loads(s)
    return dict(url=url, source="Greenhouse (company ATS)", title=j.get("title"), company=board,
                location=(j.get("location") or {}).get("name"), salary="", description=text(html.unescape(j.get("content") or "")),
                questions=[{"q": x.get("label"), "required": x.get("required"),
                            "type": ((x.get("fields") or [{}])[0]).get("type")} for x in j.get("questions") or []
                           if x.get("label") and not re.match(r"(first|last) name|email|phone|resume|cv|cover letter$", x.get("label", ""), re.I)])


def lever(url):
    m = re.search(r"jobs\.(?:eu\.)?lever\.co/([^/?#]+)/([0-9a-f-]{36})", url)
    if not m:
        return None
    board, jid = m.groups()
    host = "api.eu.lever.co" if ".eu." in url else "api.lever.co"
    s = get(f"https://{host}/v0/postings/{board}/{jid}")
    if not s:
        sys.exit("Lever didn't return the job — it may be closed.")
    j = json.loads(s)
    lists = "\n".join(x.get("text", "") + "\n" + text(x.get("content")) for x in j.get("lists") or [])
    sr = j.get("salaryRange") or {}
    sal = f"{sr.get('currency', '')} {sr.get('min', '')}–{sr.get('max', '')}".strip() if sr else ""
    return dict(url=url, source="Lever (company ATS)", title=j.get("text"), company=board,
                location=(j.get("categories") or {}).get("location"), salary=sal,
                description=(j.get("descriptionPlain") or "") + "\n" + lists + "\n" + (j.get("additionalPlain") or ""))


def workable(url):
    m = re.search(r"apply\.workable\.com/([^/?#]+)/j/([A-Z0-9]+)", url, re.I)
    if not m:
        return None
    board, code = m.groups()
    s = get(f"https://apply.workable.com/api/v2/accounts/{board}/jobs/{code}")
    if not s:
        sys.exit("Workable didn't return the job — it may be closed.")
    j = json.loads(s)
    loc = j.get("location") or {}
    return dict(url=url, source="Workable (company ATS)", title=j.get("title"), company=board,
                location=", ".join(x for x in (loc.get("city"), loc.get("country")) if x), salary="",
                description=text((j.get("description") or "") + (j.get("requirements") or "") + (j.get("benefits") or "")))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    for f in (ashby, greenhouse, lever, workable, linkedin):
        if f is linkedin and "linkedin" not in arg and not re.fullmatch(r"\d{8,}", arg.strip()):
            continue
        out = f(arg)
        if out:
            print(json.dumps(out, indent=1, ensure_ascii=False))
            return
    sys.exit("Not a LinkedIn / Ashby / Greenhouse / Lever / Workable link — open it with web fetch or a browser.")


if __name__ == "__main__":
    main()
