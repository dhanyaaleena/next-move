---
name: job-tracker-tailor-cv
description: Make a one-page CV tailored to one job in the user's tracker, using only facts from their base CV, and save it as a PDF in their tailored-CV folder. Use only when the user asks to tailor/optimise their CV for a specific role (refreshes use the fixed CV variants instead), when they want to change or add a CV variant, or to regenerate CVs after their base CV changed.
---

# Tailor a CV for one job

Inputs: a job id from `me/jobs.json`, the full posting text, `me/cv.json`, and `profile.cv`.

## Write the tailored JSON

Start from a copy of `me/cv.json`. Change only:

- **title** — exactly one of `profile.cv.allowed_titles` (or their own title). Pick the closest plain match; never invent a niche title.
- **profile** — 2–3 sentences for this company, opening with that title as the role ("Backend engineer with five years' experience…").
- **skills** — same line structure; reorder lines and items to lead with what the job asks for; drop irrelevant items. You may use the job's wording for a skill only if it's the same thing they listed (e.g. "LLM Agents" if the CV shows agents). An optional final line `{"label": "Ways of Working", "items": [...]}` may hold things from `confirmed_extras`.
- **bullets** — reorder within each role and reword to foreground what the job needs. Keep every number exactly as written. You may add a bullet only if it's in `profile.cv.conditional_bullets` (when its `when` matches the job) or is stated in `confirmed_extras`.

Never change name, contact, right to work, companies, roles, locations, dates, education, or the order of
roles. Never add a tool, number, employer claim or achievement that isn't in `cv.json` / `confirmed_extras`.
If the job leans on a skill in `ask_before_claiming`, don't use it — list it for the user to confirm.

Aim for ATS keyword overlap through honest emphasis, not stuffing. Bold key phrases and metrics with `**…**`.

## Check, fit, save

```bash
python scripts/tailor_cv.py --id "<job id>" --cv /tmp/<slug>_cv.json
```
The script refuses invented numbers/skills, wrong titles or changed facts — fix the JSON and re-run.
It trims the oldest roles' last bullets until the CV fits one page (if `cv.one_page`), saves the PDF to
`<tailored_cv_folder>/<Company>/` (or `<Company> - <Role>/` when several roles at that company are tracked),
and records it on the job so the tracker shows **📎 PDF ready**.

Look at the PDF once (render a page image) the first time in a session to check the layout.

## Regenerating after the base CV changes

`python scripts/tailor_cv.py --list-missing` lists jobs without a CV. To redo existing ones, ask the user
first (they may have sent the old version), and only for jobs they haven't applied to yet.

## CV variants (the default instead of per-job CVs)

The user keeps a handful of fixed CVs in `profile.cv.variants` (key, label, title, `match` regex on the
job title, one `default`). Each is a CV JSON at `me/cv_variants/<key>.json`, written with the same rules as
above but for a kind of role (Forward Deployed, Full Stack, AI Engineer, Backend…), with a general profile
line rather than a company-specific one. Build or rebuild them (after editing one, or after cv.json
changes):
```bash
python scripts/cv_variants.py build            # all, or --key backend
python scripts/cv_variants.py list             # which variant each job uses
```
The tracker's job dialog shows "CV to send" for every job: its tailored CV if one exists, otherwise its
variant.

