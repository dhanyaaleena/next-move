---
name: job-tracker-add
description: Log one job the user shares (a link or pasted posting) into their tracker - reads the full posting, checks it against their profile including visa needs, adds it with contacts, points it at the right one of the user's fixed CVs, and rebuilds the page. Use when the user pastes a job link or says "add this job", "track this role".
---

# Add one job

1. **Read the whole posting**: `python scripts/fetch_posting.py <url>` (LinkedIn, Ashby, Greenhouse, Lever, Workable), otherwise web fetch or the browser. If it's already tracked (`python scripts/jobs.py known`), say so with its status hint and stop.
2. **Check it against `me/profile.yaml`** — location group, seniority/years, language, salary floor, avoid list, and visa evidence where the location needs sponsorship (see the table in job-tracker-refresh). If it clearly fails a rule, say which in one line and ask before adding. The user can override; if they do and sponsorship is unclear, add with `--allow-unclear` so it shows "Visa unclear".
3. **Add it** with `python scripts/jobs.py add --json '{…}'` (fields as in job-tracker-refresh step 3). Rate fit High/Medium honestly.
4. **Contacts** (if enabled) and **application answers** (job-tracker-answers). Don't tailor a CV: check which fixed CV it gets (`python scripts/cv_variants.py pick "<role>"`) and set `cv_variant` with `jobs.py update` if the pick is wrong. Tailor only if the user asks. If the user seems to want a quick log only, offer these instead of doing them.
5. **Rebuild**: `python scripts/build.py` (and `python scripts/sync_xlsx.py` if `profile.excel`).
6. Confirm in one line: company, role, fit, and anything to watch (e.g. "asks for 6+ years").
