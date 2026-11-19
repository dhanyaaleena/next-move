#!/usr/bin/env python3
"""Is this employer on the country's official visa-sponsor register?

    python scripts/check_sponsor.py UK "Monzo"
    python scripts/check_sponsor.py UK "Acme" "Globex" "Initech"    # several at once
    python scripts/check_sponsor.py NL "Adyen"                       # prints where to check by hand

UK: downloads the Home Office "Register of licensed sponsors: workers" CSV
(found through the GOV.UK content API, cached for a day in me/cache/) and
matches loosely, because licences use legal names ("Monzo Bank Ltd").
Other countries: prints the register link and how to check it from
countries/<CODE>.yaml — Claude then checks it with web search / fetch.

Exit code 0 = at least one match (or manual check needed), 1 = no match.
A match means the company CAN sponsor; the posting itself is still the best evidence.
"""
import csv
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DEFAULT_ME, load_country  # noqa: E402

UA = {"User-Agent": "next-move/1.0"}
UK_API = "https://www.gov.uk/api/content/government/publications/register-of-licensed-sponsors-workers"
SUFFIX = re.compile(r"\b(ltd|limited|plc|llp|llc|inc|incorporated|gmbh|b\.?v\.?|uk|group|holdings|technologies|technology|the|co|company)\b\.?", re.I)


def simplify(name):
    s = re.sub(r"\(.*?\)", " ", str(name).lower()).replace("&", " and ")
    s = SUFFIX.sub(" ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def uk_register():
    cache = os.path.join(DEFAULT_ME, "cache", "uk_sponsors.csv")
    if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < 86400:
        return open(cache, encoding="utf-8", errors="ignore").read()
    meta = json.loads(fetch(UK_API))
    urls = [a.get("url") for a in (meta.get("details") or {}).get("attachments", []) if str(a.get("url", "")).lower().endswith(".csv")]
    if not urls:  # fall back to scraping the page
        page = fetch("https://www.gov.uk/government/publications/register-of-licensed-sponsors-workers").decode("utf8", "ignore")
        urls = re.findall(r'https://assets\.publishing\.service\.gov\.uk/[^"]+\.csv', page)
    if not urls:
        sys.exit("Couldn't find the register CSV on gov.uk — check by hand: " + UK_API.replace("/api/content", ""))
    raw = fetch(urls[0]).decode("utf-8", "ignore")
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        f.write(raw)
    return raw


def check_uk(names):
    rows = list(csv.DictReader(io.StringIO(uk_register())))
    key = next((k for k in rows[0] if "organisation" in k.lower()), list(rows[0])[0]) if rows else None
    index = [(simplify(r[key]), r) for r in rows]
    found_any = False
    for name in names:
        q = simplify(name)
        hits = [r for s, r in index if s == q] or [r for s, r in index if q and (s.startswith(q + " ") or f" {q} " in f" {s} ")]
        if hits:
            found_any = True
            print(f"✔ {name}: on the UK register ({len(hits)} match{'es' if len(hits) > 1 else ''})")
            for r in hits[:5]:
                print("    " + " | ".join(str(v) for v in r.values() if v))
        else:
            print(f"✘ {name}: not found on the UK register (try the legal name, e.g. '{name} Ltd')")
    return found_any


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    code, names = sys.argv[1].upper(), sys.argv[2:]
    if code in ("UK", "GB"):
        sys.exit(0 if check_uk(names) else 1)
    pack = load_country(code)
    if not pack:
        sys.exit(f"No countries/{code}.yaml yet — ask Claude to add a country pack for {code}.")
    reg = (pack.get("visa") or {}).get("register") or {}
    print(f"{pack['name']}: {reg.get('name', 'no register')}\n  {reg.get('url', '')}\n  {reg.get('how', '')}")
    print("Check by hand (or with web search) for: " + ", ".join(names))


if __name__ == "__main__":
    main()
