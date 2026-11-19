# Next Move

**Your CV, your countries, your rules — a job search your own Claude runs for you.**

Next Move is a personal job tracker that **pulls roles matching your CV, in the countries you choose — whether you already have the right to work there or need visa sponsorship** — and keeps everything in one page you open in your browser.

Your own Claude session does the searching. This repo gives it the rules, scripts and page template,
so the results are consistent and nothing about your search is hard-coded: roles, cities, countries,
visa needs, salary floor, languages and tone all come from your `profile.yaml`.

![Example tracker](docs/example-tracker.png)

## What you get

- **A tracker page** (one HTML file): roles grouped by your locations, filters by role type, fit, visa and status, a pipeline dashboard, and statuses that survive every refresh. Cards and table view.
- **Pulls that match you**: LinkedIn (signed-in browser or public search), the career boards of companies you like *and* of every company already in your tracker, and the main job boards of each country you target.
- **Visa-aware filtering**: for each country you mark as needing sponsorship, a role is added only with evidence — the posting's own words, or the employer on the country's official sponsor register (the UK register is checked automatically).
- **Answers to each job's application questions**, ready under 📝 Answers: routine facts (location, right to work, notice, salary) taken word for word from your profile, and short, specific "why us / why this role" answers backed by real numbers from your CV. A checker blocks invented numbers or skills and flags generic, AI-sounding wording.
- **A one-page tailored CV per job**, as a PDF, built only from facts in your CV. Invented numbers or skills are rejected by a checker, and skills you list as "ask first" are never claimed without you.
- **People to reach out to** for each role (names and public profile links; Claude never messages anyone), plus a ready outreach message and a ≤280-character connection note in your voice.
- **An Excel copy** (Jobs, People, Portals, Summary) if you want one. Claude only ever adds rows.

## Get started (5 minutes)

You need: [Claude Code](https://claude.com/claude-code) or the Claude desktop app with a folder connected, and Python 3.9+.

```bash
git clone https://github.com/dhanyaaleena/next-move.git
cd next-move
pip install -r requirements.txt
```

Then open the folder in Claude and use **one** of the two prompts below.

### Option A: let Claude ask you

Copy this, attach your CV, and answer Claude's questions as they come:

```text
Set up my job tracker. My CV is attached.
Read CLAUDE.md, then run the job-tracker-setup skill. Ask me everything you need (roles, places,
visa needs, salary, application details) a few questions at a time, and suggest sensible defaults
from my CV so I can just confirm. Don't apply, message anyone or submit anything.
```

### Option B: fill in the form and hand it over

Fill in what you can (leave anything blank and Claude will ask), attach your CV, and send it:

```text
Set up my job tracker. Read CLAUDE.md, then run the job-tracker-setup skill using the answers below.
Ask me only about blanks or anything unclear. Don't apply, message anyone or submit anything.

CV: (attached)

## What I'm looking for
Role types and job titles to search (2–4 groups):
  - e.g. Backend: Backend Engineer, Python Engineer
  - e.g. AI Engineer: AI Engineer, LLM Engineer, Applied AI Engineer
Seniority (junior / mid / senior / staff / lead):
Skip roles asking for more than __ years of experience:
Industries or companies to avoid:
Recruitment agencies to skip:
Dream companies (career pages if you know them):

## Where
Places, grouped the way you want them in the tracker:
  - e.g. "London": London, Greater London, Canary Wharf
  - e.g. "Remote EU": remote roles open to Europe
For each country — do you already have the right to work there? (yes / need visa sponsorship):
Work modes you're open to (onsite / hybrid / remote):
Languages you can work in:

## Pay
Minimum salary and currency (per country if different):
Keep roles that don't list a salary? (yes / no):

## Application details (used word for word in application forms)
Location line (e.g. "London, UK" or "Berlin, relocating in March"):
Right to work, per country:
Need sponsorship now or in future, per country:
Notice period:
Salary expectation (or leave blank to fill per job):
Earliest start date:
LinkedIn / GitHub / portfolio links:

## CV rules
Job titles you're happy to appear as on tailored CVs:
Skills to ask you about before claiming them:
True things that aren't on the CV yet (projects, tools, certifications):

## Your voice
How messages and answers should sound (e.g. casual and brief, not AI-sounding):
Sign-off (e.g. "Thanks, Sam"):
2–3 lines about you for outreach (who you are, right to work / relocation, one link):
A few true personal lines for application answers (what you enjoyed most, what you want next):

## Practical
Are you signed in to LinkedIn in a browser Claude can use? (yes / no):
Where to save the tracker page (default: me/output/):
Where to save tailored CV PDFs:
Excel copy too? (yes / no):
Pull new jobs automatically? (e.g. weekday mornings at 8, or no):
```

Claude reads your CV, fills in the rest, writes `me/profile.yaml` and `me/cv.json`, finds the job
boards for your countries and roles, and builds your page. Then:

> **Pull latest jobs.**

Every later pull only adds what's new since the last one. Your statuses, notes and messaged-ticks
are never reset.

### Make it automatic

Ask Claude to *"set up a scheduled task to pull my jobs every weekday morning"*. It uses this prompt:

> In the next-move repo at `<path>`: read CLAUDE.md, then run the job-tracker-refresh skill for me.
> Use my profile in me/. Don't apply or message anyone. Finish with the short report.

## Your data

Everything personal lives in `me/`, which is **git-ignored** — your CV, profile, jobs and notes never
get committed. To keep a private backup, put `me/` in its own private repo or cloud folder.

| File | Purpose |
|---|---|
| `me/profile.yaml` | What you're looking for and how Claude should work for you ([commented example](examples/profile.example.yaml)) |
| `me/cv.json` | Your base CV, structured ([example](examples/cv.example.json)) |
| `me/jobs.json` | All tracked roles ([example](examples/jobs.example.json)) |
| `me/notes.md` | Interviews, recruiter notes, open questions ([example](examples/notes.example.md)) |

| `me/statuses.json` | Your statuses copied out of the browser (made by `backup.py`, see below) |

### Backups and moving to another computer

Your data lives in two places:

- **On disk:** everything in `me/`, plus your tailored-CV folder, the tracker page and the Excel copy.
- **In your browser:** statuses and their history, interview rounds, where each rejection happened,
  people you added and "messaged" ticks. These are saved in the browser you use the tracker in.

**1. Download a backup from the page.** Click **Back up statuses** → **⬇ Download backup file**. You get
`<you>-tracker-backup-<date>.json` in Downloads. It holds everything from the browser *and* every job's
details, answers, people and dates. **Restore from file** in the same dialog loads it back. A restore
only ever applies changes that are newer than what's there.

**2. Keep your statuses on disk.**

```bash
python scripts/backup.py statuses
```

This copies the newest backup file from Downloads into `me/statuses.json`. Every rebuild puts those
statuses into the page, so a new or cleared browser shows them without restoring anything. (A refresh
by Claude does this step too when there's a newer backup file.)

**3. Make one archive of everything.**

```bash
python scripts/backup.py save
```

This zips `me/`, your tailored CVs, the tracker page, the Excel file and the newest browser backup into
`~/Documents/Next Move backups/` (set `backup_folder:` in your profile to change it).

**4. Restore on a new computer.** Clone this repo, then:

```bash
python scripts/backup.py restore "~/Documents/Next Move backups/next-move-<you>-<date>.zip"
python scripts/build.py
```

Restore never overwrites anything: files that already exist are left alone, and if `me/` already has
data it unpacks into `me.restored-<date>/` so you can compare first.

Tip: do steps 1–3 every week or two, and keep the backups folder in iCloud Drive, Dropbox or similar.
`me/` is never committed to git.

## Countries

Country packs in [`countries/`](countries/) hold each country's work-visa route, official sponsor
register (and how to check it) and main job boards: UK, IE, DE, NL, FR, US, CA, AU, SG, AE, IN and
remote-EU. Missing yours? Ask Claude to *"add a country pack for Portugal"* — and send a PR.

## Common things to ask Claude

- "Pull latest jobs" · "Add this job: <link>" · "Tailor my CV for the Acme role" · "Write answers for the Acme application"
- "Also look in Amsterdam" · "I now have the right to work in Ireland" · "Skip agency posts from X"
- "What follow-ups are due?" · "Regenerate tailored CVs for jobs I haven't applied to"
- "Find job portals for Germany" · "Back up my tracker" · "Redo the answers for the Acme application"

## How it works

```
profile.yaml + cv.json ──► search_jobs.py / browser / web search ──► candidates
                                                                        │  Claude reads each posting:
                                                                        │  fit, years, language, salary, visa evidence
                                                                        ▼
                       jobs.py add (dedupe, stable IDs, visa gate) ──► jobs.json
                                                                        │
           tailor_cv.py (fact check, one page) ──► Tailored CVs/<Company>/…pdf
           answers.py (truth + quality check)  ──► 📝 Answers on each job
                                                                        │
                    build.py ──► <Name>_Job_Tracker.html     sync_xlsx.py ──► Job_Tracker.xlsx
```

Scripts (all `--help`-documented): `build.py`, `jobs.py`, `search_jobs.py`, `fetch_posting.py`,
`check_sponsor.py`, `tailor_cv.py`, `answers.py`, `cv_pdf.py`, `sync_xlsx.py`, `backup.py`, `import_legacy.py`. Claude's
instructions are in [`CLAUDE.md`](CLAUDE.md) and [`.claude/skills/`](.claude/skills/).

Try the demo without any setup: `python scripts/build.py --example` and open `examples/Example_Job_Tracker.html`.

### Network access

The scripts call LinkedIn's public job search, the Ashby / Greenhouse / Lever / Workable public job
APIs and gov.uk. If Claude runs in a sandbox that blocks them, it falls back to a browser or web
search. To let the scripts run, allow: `www.linkedin.com`, `api.ashbyhq.com`, `boards-api.greenhouse.io`,
`api.lever.co`, `apply.workable.com`, `www.gov.uk`, `assets.publishing.service.gov.uk`.

## Ground rules Claude follows

Never invents facts on a CV or job record · never applies, messages or connects for you · never types
your passwords · never deletes your jobs or overwrites your edits · asks before deleting files · respects
LinkedIn by browsing slowly. See [`CLAUDE.md`](CLAUDE.md).

## Contributing

Country packs, ATS sources and template improvements are welcome. Run `python tests/test_scripts.py`
before sending a PR. Don't commit anything from `me/`.

MIT licence.
