---
name: job-tracker-setup
description: First-time setup of the job tracker for a new user - turns their resume into me/cv.json, interviews them for target roles, countries, visa needs and preferences into me/profile.yaml, and builds their first tracker page. Use when me/ doesn't exist, or the user says "set up my job tracker", "start my job search", or wants to change countries/roles from scratch.
---

# Set up a new user

Goal: in one short conversation, produce `me/cv.json`, `me/profile.yaml`, `me/notes.md`,
an empty `me/jobs.json`, and a built tracker page. Then offer the first pull.

## 1. Get the resume

Ask for their CV/resume (PDF, DOCX, text, or a LinkedIn profile export). Read the whole thing.
Convert it to `me/cv.json` in exactly the shape of `examples/cv.example.json`:

- Copy wording faithfully. Don't improve, summarise or add anything.
- Wrap metrics and key technologies in `**double asterisks**`, as the example does.
- `skills` is a list of lines; each line is a list of `{label, items}` groups.
- `rightToWork`: one plain line, e.g. "Authorised to work in the UK" or "Will need visa sponsorship for DE and NL". Ask if unclear; omit if they'd rather not show it.
- Show them the parsed CV briefly (name, title, roles, dates) and fix anything they flag.

Render it once to check: `python scripts/cv_pdf.py me/cv.json /tmp/base.pdf` (should be 1–2 pages).

## 2. Interview for the profile

Ask only what you can't infer from the CV. Use multiple-choice questions where the tool exists. Cover:

1. **Roles** — 2–4 role tracks (e.g. Backend / AI Engineer / Full Stack) and the job titles to search for each.
2. **Where** — cities/countries, grouped the way they want sections in the tracker (e.g. "London" and "Other UK"; or "Berlin", "Netherlands", "Remote EU").
3. **Visa** — for each country: do they already have the right to work there? That sets `needs_visa_sponsorship`.
4. **Level & pay** — seniority, max years of experience a posting may ask for, salary floor + currency, keep roles without a listed salary?
5. **Languages** they can work in (drops postings that require others).
6. **Avoid / prefer** — industries, companies, clearance roles, agencies to skip.
7. **Dream companies** for the watchlist (find each one's careers board: `jobs.ashbyhq.com/<slug>`, `boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `apply.workable.com/<slug>`).
8. **LinkedIn** — are they signed in to LinkedIn in a browser you can use? (`search.linkedin_signed_in`)
9. **CV rules** — titles they're happy to use; skills to ask about before claiming; anything true that isn't in the CV yet (`confirmed_extras`).
10. **Voice** — how messages should sound and their sign-off; a 2–3 line outreach blurb (who they are, right-to-work/relocation line, portfolio link).
11. **Application facts** — location line, right to work / sponsorship per country, notice period, salary expectation (or leave blank to fill per role), start date, work mode, links (`application_facts`).
12. **Files** — where tailored CV PDFs should go (`tailored_cv_folder`), whether they want an Excel copy, and where to save the tracker page.

Write `me/profile.yaml` from `examples/profile.example.yaml`, keeping its comments. Rules:
- `storage_prefix`: lowercase first name (a–z, 0–9, _). Never change it later.
- Location `id`s and track `id`s are stored on every job — keep them short and stable.
- Each location needs a `country` code. If `countries/<CODE>.yaml` is missing, create it (see below).
- Write `outreach.message` and `outreach.note` (≤280 chars after filling in) in their voice, with `{NAME}`, `{ROLE}`, `{COMPANY}`.

### Missing country pack

Research and write `countries/<CODE>.yaml` in the same shape as the others: the main skilled-work visa
route (official link), whether an official sponsor register exists (official link + how to check it),
phrases in postings that signal sponsorship, language notes, the `linkedin_location` string, and 4–6
well-known job boards (verify each URL loads). Don't write salary thresholds — link to the official page.

## 3. Job portals

Run the **job-tracker-portals** skill: it finds the main boards for each country they chose, boards for
their role tracks and, where they need a visa, sponsorship/relocation boards, checks each link, and adds
them to `profile.portals`.

## 4. Create the rest and build

```bash
mkdir -p me
echo '{"version": "'$(date +%F)'", "jobs": []}' > me/jobs.json
python scripts/build.py
python scripts/sync_xlsx.py          # only if profile.excel is true
```

Create `me/notes.md`:

```markdown
# Job search notes
## Status
- Set up on <date>. No pulls yet.
## Interviews in progress
## Recruiter notes
## Open questions for me
```

Send them the tracker page. If they have an older tracker in the array format, import it first with
`python scripts/import_legacy.py <file>`, and make the profile's location/track ids match what it prints.

## 5. Offer next steps

Offer to (a) run the first pull now (job-tracker-refresh), and (b) set up a scheduled task that pulls
on a schedule they choose, e.g. weekday mornings, using this prompt:

> In the next-move repo at <path>: read CLAUDE.md, then run the job-tracker-refresh skill for me.
> Use my profile in me/. Don't apply or message anyone. Finish with the short report.
