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

- **When it shows:** whenever the job has answers, whatever its status.
- **Also in the job-link dialog:** opening a job's link (Apply / Open) shows every answer, expanded, under
  the "Mark job as" buttons, each with its own 📋 Copy, so the user never has to close the dialog.
- **Cards:** in the footer button row, in the slot the old 📎 PDF-ready button used, before
  ✨ Optimize (if enabled) and Apply. Class `ansb a-opt`, label "📝 Answers".
- **Table:** in the Actions column, before the Apply/Open link. Class `ansb ans-t`, label "📝 Answers",
  30px high to match the row's other controls. The Actions column is 200px wide.
- **Styling:** soft accent button: `--accent-line` border, `--accent-soft` background, `--accent-ink` text.

## Answers dialog

- An overlay (`#ansModal.ans-ov`), created on first use, centred vertically and horizontally, sitting
  above everything (z-index 1000). Dimmed backdrop `rgba(36,24,14,.45)`.
- The box (`.ans-box`, up to 720px wide, 85vh tall, scrolls inside) shows the company and role at the
  top (company in the display serif), a one-line tip ("Anything in [brackets] needs your input. Read each
  one before pasting."), then one block per question split by hairlines: question in small muted bold
  text, answer below at 14px with line breaks kept.
- **📋 Copy** button in each block's top-right corner copies just that answer, using the same
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
- Each person is a bordered card (`--r` radius, `--surface-2` background).
- Close with ✕, a click on the backdrop, or **Esc**. The list goes back into its row when closed, so
  ticks and edits made in the dialog are kept.
- Card view is unchanged: people still expand inside the card (`details.ppl`).

## Status history and rejection stages

- **History.** Every status change is stored in the browser with the job's status, as
  `hist: [{s: "Applied", d: "2026-11-03"}, …]` (last 30 changes). A status saved before history existed
  becomes the first step the next time the status changes. Resetting to *To apply* clears the history.
- **Rejected after …** A rejection's stage is the furthest of Applied → Screening → Interviewing → Offer
  in its history. Cards show "Rejected after screening · 15 Nov 2026"; the table shows "after screening"
  under the status pill. Old rejections with no history show as *stage not recorded*.
- **Review rejections** dialog (from the dashboard): every rejected job with a three-way switch
  (Applied / Screened / Interviewed) that sets `rejStage`, a manual correction that wins over history.
  Unrecorded ones are listed first.
- **Dashboard outcomes row** (full width, shown once anything is applied): *How far your applications
  got* (applied, got a screening, got an interview, got an offer, each with count and % of applied) and
  *Where rejections happened* (after applying / screening / interviewing, plus not recorded, as % of
  rejections), with *Fill in N missing* / *Review* opening the dialog.
- **Interview rounds.** The status menu lists *Interviewing · R1* … *R5* (stored as status
  `Interviewing` plus `round`; each round change goes into `hist` with `r`). The funnel adds *Got to
  round 2+*, and rejections after interviewing split by round (*After interview R2*) once more than one
  round appears.
- **Not interested** is a status of its own (grey, counted with closed/skipped).
- Backups include `hist`, `rejStage` and `round`.

## Backups and moving to another computer

- **Where data lives.** On disk in `me/` (profile, CV, jobs with answers/contacts/dates, notes) plus the
  tailored-CV folder, tracker page and Excel file; in the browser: statuses + history, rounds, rejection
  stages, people added, messaged ticks, tailored CVs made in the page, CV edits.
- **Back up dialog.** *Download backup file* saves `<prefix>-tracker-backup-<date>.json` with all the
  browser data **and** the page's own data (profile, CV, every job with answers, people and dates).
  *Restore from file* merges one back. The old copy/paste text (statuses only) is still there.
- **Merging rule** (page and script): a status is replaced only by a newer change (`updated`), so a
  restore never undoes something done since. People and messaged ticks are added, never removed.
- **On disk.** `python scripts/backup.py statuses` copies the newest backup file from Downloads into
  `me/statuses.json`; `build.py` embeds it as `SAVED_STORE`, and the page merges it on load, so a new
  browser or computer shows your statuses without any manual restore.
- **Moving.** `python scripts/backup.py save` zips me/, tailored CVs, the tracker page, the Excel file and
  the browser backup into `~/Documents/Next Move backups/` (or `profile.backup_folder`).
  `python scripts/backup.py restore <zip>` unpacks it; it never overwrites (an existing `me/` gets a
  `me.restored-<date>/` folder alongside instead).

## Dark mode

- The header's **Theme** button cycles *Auto → Light → Dark*. Auto follows the system setting. The choice
  is saved in the browser (`nextmove_theme`); a tiny script in `<head>` sets `html.dark` before the page
  paints, so there's no flash.
- Dark tokens live in one `html.dark { … }` block. Text on solid ink/accent uses `--on-ink`; inputs and
  hover fills use `--field`; logo/avatar tints use `--lf/--ls/--lb`. Role-track chips are mixed lighter
  with a translucent fill in dark. The CV preview stays white (it's a document).

## Removed (off by default)

- **📎 PDF ready**: the 📝 Answers button replaced it. Turn it back on with `features.pdf_button: true`.
- **"How this tracker works"** box: turn it back on with `features.how_it_works: true`.

## Look and layout (design v5, 19 Nov 2026)

The stylesheet is one layer of tokens on `:root` followed by components; there are no stacked
overrides. Change a token before adding a one-off colour.

- **Type.** UI text is Inter; the page title, section headings, dashboard numbers and dialog titles
  use Fraunces (a warm serif) at a low optical size so numbers stay solid. Both load from Google
  Fonts and fall back to system sans / Georgia offline.
- **Header.** Title with the accent monogram, tagline, one quiet "Updated … · N roles" line. Two
  plain buttons on the right: *Back up statuses*, *My CV*.
- **Dashboard.** One panel split into four columns by hairlines (no nested cards, no gradients):
  jobs total with new / high-fit dots; pipeline count over a four-stage row (Applied, Screening,
  Interviewing, Offer) with rejected and messaged counts underneath; location bar; role-mix bar.
  Two columns under 1180px, one under 640px.
- **Toolbar.** Sticky, blurred, three tiers:
  1. search, then *Role*, *Status* and *Sort* as compact dropdowns (small grey label + value; a dropdown
     that's filtering gets a dark outline), then the Cards/Table toggle;
  2. quick-filter chips (Everything, High fit, Visa OK when a location needs a visa, Not applied yet,
     New since last refresh, Direct listings, LinkedIn), a live count on the right ("319 roles in London")
     and *Clear filters* when anything is filtering;
  3. the location tabs.
  On phones: the view toggle goes first, search is full width, the three dropdowns share a row (labels
  hidden), and the chips scroll sideways.
- **Location tabs.** The bottom edge of the sticky toolbar holds one tab per location group (colour dot,
  name, count under the current filters), plus *Other locations* when needed and *All locations* last. Only
  the selected group's jobs are drawn, so the page stays short; the choice is remembered per browser
  (`<prefix>_loctab`). The old Location chip row is hidden. Dashboard numbers still cover every location.
  With a single location group there are no tabs.
- **Sections.** Location heading in the serif with its colour dot and a muted count, subtitle beside
  it, hairline underneath.
- **Cards.** Flat: 1px border, 14px radius, no shadow, border darkens on hover. Jobs you've acted on
  get the `--surface-2` tint. *New* is a solid accent pill; *High fit* a green pill; *Medium fit* is
  plain faint text. Footer: status pill and date on the left; buttons on the right, with **Apply** as
  the one solid dark button (indirect listings get an outlined *Open page*).
- **Status pill.** Neutral outline for *To apply*; solid ink for Applied; tinted for Screening (blue),
  Interviewing (amber), Rejected (red); solid green for Offer; faint for closed/skipped/duplicate.
- **Table.** Same tokens; cells vertically centred; 30px controls; header on `--surface-2`.
- **Portals.** A single bordered grid of tiles split by 1px gaps, each with an "Open ↗" text link.

## Theme tokens ("paper and ink", 19 Nov 2026)

A neutral off-white page with near-black text and buttons and no colour accent. Colour is kept for
meaning only: fit, visa, status, and the location / role-track colours.

| Token | Value | Use |
|---|---|---|
| `--bg` / `--bg-2` | `#f6f6f4` / `#ebebe8` | page background / sunken fills (toggle track, hovers) |
| `--surface` / `--surface-2` | `#ffffff` / `#f8f8f6` | cards, dialogs / tracked jobs, table header |
| `--ink` / `--ink2` | `#161616` / `#333333` | main / secondary text, active chips |
| `--muted` / `--faint` | `#666660` / `#8f8f88` | labels, hints |
| `--line` / `--line2` / `--line-strong` | `#e3e3df` / `#efefec` / `#c9c9c3` | borders, dividers, hover borders |
| `--accent` / `--accent-ink` | `#1f1f1f` / `#000000` | Apply, New, primary buttons / hover |
| `--accent-soft` / `--accent-line` | `#ececea` / `#d0d0cb` | soft button backgrounds (📝 Answers, badges) / borders |
| `--ok`, `--warn`, `--bad`, `--info` | `#1d7a52`, `#9a5606`, `#b42318`, `#1f6a98` | each with `-soft` and `-line` variants |
| `--r-sm` / `--r` / `--r-lg` | 8 / 10 / 14px | radii |
| `--gut` | 32px (16px on phones) | page side gutter |

To re-theme, change these tokens only; nothing else in the stylesheet hard-codes a page colour.

Role-track and location colours are assigned in profile order from fixed palettes in the template
(`TRACK_COLORS`, `LOC_COLORS`): first track purple `#7c3aed`, then teal `#0f766e`, amber `#a16207`, and
so on; first location red `#ef4444`, then sky `#0ea5e9`, green `#16a34a`, and so on.
