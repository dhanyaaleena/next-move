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

The test for every open answer: **could it be sent to another company by swapping the name?** If yes, it
isn't done. Each one has to show that the user read about *this* company and connect it to something
*they* actually built, in their own voice.

### a. Research first: a company brief (write it down before drafting)

Read the full posting, the company's own site (product pages, about, customers, engineering blog) and one
recent item (launch, funding, case study, talk). Note 3–5 concrete facts in your scratch notes, each with
where you read it:
- what they sell and to whom (in plain words, e.g. "brokerage APIs that let AI agents trade for users");
- the hard problem underneath it (scale, latency, regulation, data quality, reliability…);
- what this team/role owns, in the posting's own words;
- one recent, specific thing (a launch, a customer, a technical choice they've written about).
Use only what you read; don't infer funding, size or tech stack.

### b. Pick the user's stories, not just their skills

From `cv.json` (and `notes.md`, `profile.writing.about_me`), pick the 2–3 experiences that best match the
posting's main requirements. For each, have the story ready: **the situation, what they personally did,
how, and the result with its real number**. "Rebuilt the payments
API at Acme (idempotency keys, retries, webhooks); it now handles 2M requests a day at p99 under 200 ms"
beats "experience with APIs".
Prefer the experience that is closest to the company's hard problem from (a).

### c. Write

**Why do you want to work here?** (60–110 words)
- Open with the specific thing from the brief that genuinely connects to the user, in their words: what
  the company does and why that problem is interesting *to them*. Not "I'm excited about your mission".
- Tie it to one real experience or interest of theirs (a problem they've hit, a domain they've worked in,
  a thing they built that touches the same space) — say what it was.
- Name the company and at least one concrete product/customer/technical detail. Add a practical line only
  if it helps (e.g. "I'm moving to London next month").

**Why this role / why are you a good fit?** (80–130 words)
- First sentence maps the role to their experience directly ("This role is about owning the AI layer:
  prompting, retrieval and output quality. That's very close to what I do at Instead.").
- Then the 2–3 stories from (b), short: what they built, how, the number. Match the posting's wording for
  the requirement each one answers.
- If the posting asks for something they don't have, say so plainly and bridge to the closest real
  experience ("I haven't built an MCP server yet, but I've built the tool-calling layer it's based on").

### d. Make it sound like them

- Follow `profile.writing` (tone, and `about_me` if present: what they enjoy, why they're moving, what they
  want next). If `about_me` is missing, ask the user 2–3 quick questions once (what they enjoyed most in
  their last role, what kind of product they want to work on, anything personal they're happy to mention)
  and save the answers to `profile.writing.about_me`.
- First person, plain words, short sentences, contractions. One real opinion or feeling is fine ("the bit
  I enjoyed most was…"). No clichés ("passionate about", "thrilled", "leverage", "fast-paced", "proven
  track record", "I am writing to"), no em-dash chains, no lists unless the question asks for them.
- It should read like the user typed it in five minutes on a good day.

### e. Self-check before saving (rewrite anything that fails)

1. Swap test: would it still work for a competitor? → add the specific detail from the brief.
2. Does it name a concrete thing they built, with what/how/result? → add the story.
3. Is every fact about the company something you actually read? Every number from the CV/facts?
4. Is the "why us" different from every other company's (`python scripts/answers.py audit`)?
5. Read it aloud in their voice: anything they wouldn't say? → cut it.

**"Tell us about yourself"**: two short paragraphs: who they are and what they've done recently (with one
metric), then why this company. **"Anything you'd like to learn in the first call?"**: 1–2 genuine
questions about how the team works on this role's real problems. **Technical / opinion questions**: answer
directly with how *they* work, based on their stack; if it goes beyond the CV, mark the spot with
`[edit to match what you've actually used]` rather than inventing experience.

**Truth** — only facts from `cv.json`, `profile.cv.confirmed_extras` and `application_facts`. Every number
must already be there. Never claim a skill from `profile.cv.ask_before_claiming`; say honestly they haven't
used it yet, or ask the user. Respect any character/word limit on the form.

**Different for every company** — don't reuse a "why us" paragraph across companies; the evidence can
repeat, the reasons shouldn't.

**Redoing old answers** — when the user asks to improve existing answers, keep the routine facts, redo the
open ones with steps a–e, and save with `answers.py set` (it replaces that job's answers).

## 4. Check and save

Write `/tmp/<slug>_answers.json` as `[{"q": "...", "a": "...", "limit": 500}]` (limit only if the form has one), then:

```bash
python scripts/answers.py set --id "<job id>" --file /tmp/<slug>_answers.json
```

✘ items block saving: fix them. ! items are warnings: fix them unless there's a good reason. The script
lists every `[placeholder]` left for the user; mention those in your report. Rebuild the page afterwards
(`python scripts/build.py`). The answers show under the job's 📝 Answers button and inside its job-link dialog.

To review everything saved so far: `python scripts/answers.py audit`.
