# Tracker page — design notes

Reference for anyone (or any Claude session) changing `template/tracker.html`. It records the current
design, so changes stay consistent.

## Application answers

**How they're stored.** Each job in `me/jobs.json` can have
`"answers": [{"q": "Why do you want to work here?", "a": "…"}, …]`, in the order the form asks them.
The page also reads older trackers' row arrays, where answers sit at index 16 as `[question, answer]`
pairs. Only `scripts/answers.py set` writes them, after checking them.

**Where the questions come from.** In order of preference: the job's own application form (Greenhouse
questions come through `scripts/fetch_posting.py`; other boards are read from the apply page), then
questions written in the posting, then a standard set (location, right to work, sponsorship, notice,
salary, links, why us, why this role). Name, email, phone, CV upload and diversity questions are left
to the user.

**Quality bar** (full version in `.claude/skills/job-tracker-answers/SKILL.md`):
- Routine facts come word for word from `profile.application_facts`; a blank fact becomes `[your …]`
  for the user to fill in.
- "Why us" (60–110 words) opens with something specific and true about the company and names it.
- "Why this role" (80–130 words) maps the role to real experience, with 2–3 pieces of CV evidence and
  their exact numbers, and is honest about gaps.
- Casual, brief, first person; no stock phrases; different reasons for every company.
- `answers.py` blocks numbers and ask-first skills that aren't in the CV/facts (an honest "I haven't
  used X yet" is allowed), checks form character limits, and warns on generic wording, answers that
  don't name the company, and near-copies of another company's answer.

## 📝 Answers button

- **When it shows:** the job has answers **and** its status is *To apply*. Once the user applies, skips
  or closes the job, the button goes away.
- **Cards:** in the footer button row, in the slot the old 📎 PDF-ready button used, before
  ✨ Optimize (if enabled) and Apply. Class `ansb a-opt`, label "📝 Answers".
- **Table:** in the Actions column, before the Apply/Open link. Class `ansb ans-t`, label "📝 Answers":
  inline-flex, 36px high, 0 14px padding, 10px radius, 13px / 650 weight, no wrapping. The Actions
  column is 200px wide.
- **Styling:** warm accent pill: border `#e9c9ae`, background `#fdf0e6`, text `#9a3f1f`; hover
  background `#fbe2d0`.

## Answers dialog

- An overlay (`#ansModal.ans-ov`), created on first use, centred vertically and horizontally, sitting
  above everything (z-index 1000). Dimmed backdrop `rgba(41,28,18,.45)`.
- The box (`.ans-box`, up to 720px wide, 85vh tall, scrolls inside) shows the company and role at the
  top, a one-line tip ("Anything in [brackets] needs your input. Read each one before pasting."), then
  one card per question: question in small bold text, answer below with line breaks kept.
- **📋 Copy** button in each card's top-right corner copies just that answer, using the same
  clipboard fallback as outreach messages.
- **Close:** the ✕ button, or a click on the backdrop.

## People column (table view)

- Narrow column (96px). Each row shows a compact pill button **"👥 N ▾"** (`.t-ppl`, 999px radius,
  11.5px text); with contacts saved, N is followed by "· ✓k" when k of them are messaged.
- Rows with no contacts show **"👥 0 ▾"** too, slightly faded (`.t-ppl0`, opacity .75). It opens the
  same dialog with the general actions: copy a message, copy a connection note, tick "messaged", and
  ＋ Add person.

## People dialog

- Clicking the pill opens a centred dialog (`.ans-ov.pp-ov` with `.pp-box`, up to 520px wide) instead
  of expanding the row. It shows company and role at the top, then the row's existing people list
  moved inside: per person an avatar, name (opens their profile link), tag (Talent / Founder / Hiring
  manager / Team / Added by you), title (wrapping), and actions (📋 message, ✉️ note, 📧 email if known,
  messaged tick, ✕ for people you added), then ＋ Add person.
- Each person is a bordered card (10px radius, `#fbf7f1` background).
- Close with ✕, a click on the backdrop, or **Esc**. The list goes back into its row when closed, so
  ticks and edits made in the dialog are kept.
- Card view is unchanged: people still expand inside the card (`details.ppl`).

## Removed (off by default)

- **📎 PDF ready**: the 📝 Answers button replaced it. Turn it back on with `features.pdf_button: true`.
- **"How this tracker works"** box: turn it back on with `features.how_it_works: true`.

## Warm theme colours

| Token | Value | Use |
|---|---|---|
| `--bg` | `#efe8de` | page background |
| `--surface` | `#fffdf9` | cards, dialogs, buttons |
| `--ink` / `--ink2` | `#1f1a16` / `#3a2f27` | main / secondary text |
| `--muted` / `--faint` | `#6b5d52` / `#8a7b6f` | hints, labels |
| `--line` / `--line2` | `#ddd2c4` / `#e9e0d4` | borders, dividers |
| `--accent` / `--accent-2` | `#b4532a` / `#c8643a` | primary accent (burnt orange) |
| `--accent-soft` | `#fbe7d8` | accent backgrounds |
| `--ok` / `--ok-soft` | `#047857` / `#ecfdf5` | high fit, visa OK |
| `--warn` / `--warn-soft` | `#b45309` / `#fffbeb` | warnings, visa unclear |
| Shadows | `--sh-1: 0 1px 3px rgba(60,40,20,.10)`; `--sh-2: 0 1px 3px rgba(60,40,20,.08), 0 10px 28px -10px rgba(60,40,20,.22)` | cards / raised |

Role-track and location colours are assigned in profile order from fixed palettes in the template
(`TRACK_COLORS`, `LOC_COLORS`): first track purple `#7c3aed`, then teal `#0f766e`, amber `#a16207`, and
so on; first location red `#ef4444`, then sky `#0ea5e9`, green `#16a34a`, and so on.
