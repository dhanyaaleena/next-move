---
name: job-tracker-answers
description: Draft high-quality answers to a job's application-form questions (why us, why this role, motivation, technical questions, plus routine facts like location, right to work, notice and salary) from the user's CV and profile, check them, and save them so the tracker's 📝 Answers button shows them. Use during a refresh for every new job, when the user asks for application answers, or says "help me answer these questions".
---

# Application answers

The goal: when the user opens **📝 Answers** on a job, every question on that job's application form
already has an answer they could paste after a quick read. That means each answer is true, specific to
this company, and sounds like them, not like a template.

## 1. Get the real questions

In order of preference:
1. **The application form itself.** `python scripts/fetch_posting.py <url>` returns Greenhouse custom
   questions. For Ashby, Lever, Workable, company sites or LinkedIn Easy Apply, open the apply page with
   web fetch or the browser and read the form. Never fill in, upload to, or submit the form.
2. **Questions written in the posting** ("In your application, tell us…").
3. If neither is visible, use this standard set: Location · Are you authorised to work in <country>? ·
   Will you need visa sponsorship now or in the future? · Notice period · Salary expectation ·
   LinkedIn / GitHub / portfolio · Why do you want to work here? · Why this role / why are you a good fit?

Skip name, email, phone, CV upload and EEO/diversity questions; the user answers those themselves.

## 2. Routine questions: use the facts, word for word

Location, right to work, sponsorship, notice period, salary, start date, work mode, links and "how did you
hear about us" come from `profile.application_facts`. Use them as written; adapt only the yes/no shape to
the question ("Are you based in London?" → "Yes, London (moving there next month)"). A blank fact becomes a
bracket placeholder the user fills in: `[your notice period]`, `[your expectation]`. Never guess these.
For "how did you hear", use the job's `source` (e.g. "LinkedIn") if the fact is blank. Office-days
questions ("happy to be in 4 days a week?") get a direct Yes/No based on `work_mode`, plus at most a few words.

## 3. Open questions: the quality bar

Before writing, read the full posting and one or two pages about the company (product, customers, recent
news) so you have something specific to say.

**Why do you want to work here?** (60–110 words)
- Open with something specific and true about *this* company: what it builds, for whom, a hard problem it
  takes on. Not "I'm excited about your mission".
- Link it to something the user has actually done or cares about (from `cv.json` / `notes.md`).
- Name the company at least once. Add a practical line only if useful (e.g. "moving to London next month").

**Why this role / why are you a good fit?** (80–130 words)
- First sentence maps the role to their experience directly ("This role is about owning the AI layer:
  prompting, retrieval and output quality. That's very close to what I do at Instead.").
- 2–3 pieces of evidence from the CV with their real numbers, chosen to match the posting's requirements.
- If the posting asks for something they don't have, say so plainly and bridge to the closest real
  experience ("I haven't built an MCP server yet, but I've built the tool-calling layer it's based on").

**"Tell us about yourself"**: two short paragraphs: who they are and what they've done recently (with one
metric), then why this company. **"Anything you'd like to learn in the first call?"**: 1–2 genuine
questions about how the team works on this role's real problems. **Technical / opinion questions**: answer
directly with how *they* work, based on their stack; if it goes beyond the CV, mark the spot with
`[edit to match what you've actually used]` rather than inventing experience.

**Voice** — follow `profile.writing`: casual, brief, first person, plain words, short sentences. No clichés
("passionate about", "thrilled", "leverage", "fast-paced", "proven track record", "I am writing to"), no
em-dash chains, no lists unless the question asks for them. It should read like the user typed it in five
minutes on a good day.

**Truth** — only facts from `cv.json`, `profile.cv.confirmed_extras` and `application_facts`. Every number
must already be there. Never claim a skill from `profile.cv.ask_before_claiming`; say honestly they haven't
used it yet, or ask the user. Respect any character/word limit on the form.

**Different for every company** — don't reuse a "why us" paragraph across companies; the evidence can
repeat, the reasons shouldn't.

## 4. Check and save

Write `/tmp/<slug>_answers.json` as `[{"q": "...", "a": "...", "limit": 500}]` (limit only if the form has one), then:

```bash
python scripts/answers.py set --id "<job id>" --file /tmp/<slug>_answers.json
```

✘ items block saving: fix them. ! items are warnings: fix them unless there's a good reason. The script
lists every `[placeholder]` left for the user; mention those in your report. Rebuild the page afterwards
(`python scripts/build.py`). The 📝 Answers button shows while the job's status is **To apply**.

To review everything saved so far: `python scripts/answers.py audit`.
