# Next Move — instructions for Claude

Next Move is a personal job-search tracker. Each user keeps their own data in `me/`
(git-ignored); everything else is shared code. Read this file at the start of every
session, then read the user's `me/profile.yaml` and `me/notes.md` before doing anything.

## What lives where

| Path | What it is |
|---|---|
| `me/profile.yaml` | The user's targets: role tracks, location groups (+ visa need per country), salary, fit rules, search sources, contacts, CV rules, writing style, hard rules. **Source of truth for every decision.** |
| `me/cv.json` | Their base CV, structured (shape: `examples/cv.example.json`). Tailored CVs may only use facts from here or `profile.cv.confirmed_extras`. |
| `me/jobs.json` | Every role the tracker shows. Only change it through `scripts/jobs.py`. |
| `me/statuses.json` | Statuses copied out of the browser (`backup.py`). Embedded in the page on every build so a new or cleared browser gets them back. |
| `me/notes.md` | Running notes: interviews in progress, recruiter replies, open questions, last pull summary. Keep it short and current. |
| `me/output/*.html` (or `profile.output_file`) | The tracker page. Rebuilt by `scripts/build.py`. |
| `countries/<CODE>.yaml` | Per-country visa route, official sponsor register, job boards. |
| `template/tracker.html` | Shared page template. Don't put user data in it. Design notes: `docs/tracker-design.md`. |

If `me/` doesn't exist, the user hasn't been set up — use the **job-tracker-setup** skill.

## Skills (in `.claude/skills/`)

- **job-tracker-setup** — first run: CV → `cv.json`, a short interview → `profile.yaml`, first build.
- **job-tracker-refresh** — "pull latest jobs" / "refresh my tracker": search, verify, add, contacts, tailored CVs, rebuild, report.
- **job-tracker-add** — the user shares one job link to log.
- **job-tracker-tailor-cv** — make or redo a one-page tailored CV for a job.
- **job-tracker-portals** — find job boards for the user's countries, role tracks and visa needs → `profile.portals` (shown under Job portals).
- **job-tracker-answers** — draft and check answers to a job's application-form questions (shown under 📝 Answers).

If your environment doesn't load skills automatically, open the matching `SKILL.md` and follow it.

## Commands

```bash
pip install -r requirements.txt                       # once
python scripts/build.py                               # rebuild the tracker page
python scripts/jobs.py known|stats|list|add|update|pulled|bump
python scripts/search_jobs.py                         # candidates -> me/candidates.json
python scripts/fetch_posting.py <url>                 # full posting text (LinkedIn/Ashby/Greenhouse/Lever/Workable)
python scripts/check_sponsor.py <CODE> "Company"      # official sponsor register (UK automated)
python scripts/tailor_cv.py --id <job id> --cv f.json # check + fit one page + save PDF
python scripts/answers.py set|check|audit|missing    # application answers (quality + truth checks)
python scripts/sync_xlsx.py                           # Excel copy (Jobs + People + Portals)
python scripts/backup.py statuses|save|restore        # browser statuses → me/statuses.json; zip / unpack everything
python tests/test_scripts.py                          # offline tests
```

## Non-negotiable rules (apply to every user)

1. **Never invent.** Not on a CV, not in a job record. Salary, years asked, visa wording and contacts come from what you actually read. If you didn't see it, leave it out.
2. **Visa evidence or nothing.** For a location with `needs_visa_sponsorship: true`, add a job only if the posting says it sponsors (quote it) or the employer is on that country's official register (name the register). "Big company, probably sponsors" is not evidence. Postings that say they can't sponsor are dropped.
3. **Never delete or reset the user's work.** Don't remove jobs from `jobs.json`, don't regenerate their Excel file, don't change `storage_prefix` or job IDs (the browser keys statuses on them). Ask before deleting any file.
4. **Never act as the user.** Don't apply, message, connect, or submit anything. Don't type passwords — the user signs in themselves. Contacts are names + public profile links only.
5. **Follow `profile.rules` and `profile.writing`** for anything written in the user's name.
6. **Ask before claiming** anything in `profile.cv.ask_before_claiming`, and don't use skills or numbers that aren't in `cv.json` / `confirmed_extras` / `application_facts`, in CVs or in application answers (`tailor_cv.py` and `answers.py` enforce this — don't work around them).

## Network

The scripts call LinkedIn's public job search, the Ashby/Greenhouse/Lever/Workable public APIs and gov.uk.
If they fail with connection/proxy errors, the sandbox is blocking those hosts: say so once, then do the same
work with a browser (preferred when the user is signed in to LinkedIn) or web search/fetch. Don't retry the
script with other tools to get around the block.
