---
name: job-tracker-refresh
description: Pull new jobs into the user's tracker according to their profile - searches LinkedIn and company career boards for their role tracks and locations, checks fit, language, seniority and visa-sponsorship evidence, adds contacts, makes a tailored one-page CV and application answers per job, rebuilds the tracker page and Excel copy, and reports. Use when the user says "pull latest jobs", "refresh my tracker", "find new jobs", or a scheduled run asks for a refresh.
---

# Pull latest jobs

Read `CLAUDE.md`, `me/profile.yaml` and `me/notes.md` first. Use only this repo's scripts: the page is rebuilt
by `scripts/build.py` alone, never from older script or template copies (see CLAUDE.md rule 6). Everything below is driven by the profile —
never assume a country, role or visa situation. Set up a task list: search → review → add → contacts →
CVs → answers → rebuild → report.

## 0. Where to start from

```bash
python scripts/jobs.py stats          # shows last pull date and counts
python scripts/jobs.py known --compact > /tmp/known.json
```
Search from the last pull date (inclusive) to today; if there's no last pull, use `search.freshness_days`.

## 1. Search — collect candidates

Do all that apply (from `search.sources`):

**a. Scripted search** (fast, no login):
```bash
python scripts/search_jobs.py
```
Writes `me/candidates.json` from LinkedIn's public search (each title × place in the profile) and the
career boards of `watchlist` companies **plus every company already tracked** (`sweep_tracked_boards`).
If it fails on network/proxy errors, say so once and use b/c instead.

**b. LinkedIn in the browser** — if `search.linkedin_signed_in` and a browser tool is available. The user
signs in themselves; never type credentials. For each query in `search.linkedin_queries` (or the track
titles) and each location group: search with the date filter covering the time since the last pull. Read
results page by page. **Browse gently**: pause a few seconds between pages, don't open dozens of tabs,
stop if LinkedIn shows a warning or captcha and tell the user.

**c. Web search across job boards** — the boards in each location's country pack (`countries/<CODE>.yaml`
→ `boards`) and the user's own `profile.portals`: search for the track titles + place. If a location's
country or a role track has no boards in `profile.portals` yet (the profile changed since setup), run
the **job-tracker-portals** skill first. Prefer links to the company's own posting (ATS page) over
aggregators.

Merge everything into one candidate list. Drop anything already in `/tmp/known.json` (same id
`norm(company)|norm(role)` or same posting URL).

## 2. Review each candidate — read the full posting

For every candidate, open the full description (`python scripts/fetch_posting.py <url>` for
LinkedIn/Ashby/Greenhouse/Lever/Workable; otherwise web fetch or the browser). Never judge from the title.
Drop it, and note why, if any of these fail:

| Check | Rule (from profile) |
|---|---|
| Location | Fits one of `locations` (city, or remote rules for that group). Note work mode. |
| Seniority | Not above `max_years_asked`; not intern/junior unless `seniority` includes junior. |
| Language | Doesn't *require* a language outside `languages`. |
| Salary | Not clearly below `salary.minimum` (keep unlisted if `keep_unlisted`). |
| Avoid | No `fit.avoid_keywords` / `avoid_companies`; not a `search.skip_agencies` recruiter post or an anonymous agency ad. |
| Visa | If the location `needs_visa_sponsorship`: posting states sponsorship (quote it), or the employer is on the official register (`python scripts/check_sponsor.py <CODE> "<Company>"` or the pack's `register.how`). "Cannot sponsor" → drop. Unclear → drop unless the user asked to keep unclear ones. |
| Still open | The posting loads and accepts applications. |
| Fit | **High** = matches `fit.high`; **Medium** = matches `fit.medium`; anything weaker → drop. |

Stop at `search.max_new_per_refresh` good roles; mention if more were left.

## 3. Add the good ones

Write them to `/tmp/new_jobs.json` as a list in the `examples/jobs.example.json` shape:

- `location` / `track`: ids from the profile. `place`: as the posting says ("London (hybrid)").
- `experience`: years asked, as written ("3+ yrs"), if stated.
- `salary`: exactly as posted, or "Not listed"; `salary_num`: top of range in thousands, else 0.
- `skills`: 3–4 short tags from the posting. `note`: one short line — what the company does / why it fits / any gap.
- `url`: the direct posting (`direct: true`). If you only have a search/careers page, `direct: false`.
- `source`: "LinkedIn", "Ashby (company ATS)", "Greenhouse (company ATS)", a board name, etc.
- `visa`: `{"status": "sponsors"|"not_needed"|"unclear", "evidence": "<quote or register name>"}` — required where sponsorship is needed; omit otherwise.
- `posted`: posting date if shown.

```bash
python scripts/jobs.py add --file /tmp/new_jobs.json
```
It refuses duplicates and invalid records and prints why — fix and re-run, don't bypass it.

## 4. Contacts (if `contacts.enabled`)

For each new job find up to `contacts.max_per_job` people, in `contacts.order` (e.g. talent/recruiter →
founder → hiring manager → team). Use web search / LinkedIn search results; record **name, title, public
profile URL, tag** (Talent | Founder | Hiring manager | Team). Only people you actually found — never guess
a name. Never message, connect or follow.

Emails (if `contacts.guess_emails`): only when you can find the company's email pattern from public
sources. Mark `email_confidence` **likely** if the pattern is clear (~85%+ of examples), otherwise
**guess**; **public** if the address itself is published. Add with:
```bash
python scripts/jobs.py update --id "<id>" --json '{"people": [{"name": "...", "title": "...", "url": "...", "tag": "Talent", "email": "...", "email_confidence": "likely"}]}'
```

## 5. Tailored CVs

For every new job run the **job-tracker-tailor-cv** skill (one PDF per job). If there are many, do the
High-fit ones first and tell the user how many are left.

## 6. Application answers

For every new job run the **job-tracker-answers** skill: read the application form's questions and save
checked answers, so **📝 Answers** is ready in the tracker. High-fit jobs first; note any `[placeholders]`
the user must fill in.

## 7. Rebuild and sync

```bash
python scripts/backup.py statuses      # if a newer <prefix>-tracker-backup-*.json is in Downloads (skip if none)
python scripts/jobs.py pulled          # records today as the last pull
python scripts/build.py                # tracker page (keeps all statuses — they live in the browser)
python scripts/sync_xlsx.py            # if profile.excel
```
If `profile.artifact` names a published copy of the tracker, republish the new page to it.
Send the user the rebuilt page.

## 8. Report (short)

Update `me/notes.md` (Status: date of pull, how many added). Then reply with:
- **Best matches** — High fit, one line each: company, role, place, why.
- **Other matches** — count + a few names.
- **Skipped** — grouped by reason (seniority, language, no sponsorship, agency, closed, duplicate…) with counts.
- Anything that needs the user: answer placeholders to fill (notice period, salary…), a skill to confirm for a CV or answer, a LinkedIn warning, blocked network.

No step-by-step recap of what you did.
