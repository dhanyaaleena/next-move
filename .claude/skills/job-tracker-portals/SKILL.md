---
name: job-tracker-portals
description: Find the job boards that matter for this user - the main boards in each country they're targeting, boards for their role tracks (AI, design, fintech...), and, where they need a visa, boards that filter for sponsorship or relocation - check every link loads, and save them to their profile so they show under "Job portals" in the tracker and are searched on every refresh. Use during setup, when the user adds a country or role track, or says "find job portals for X", "which job boards should I use".
---

# Find job portals for this user

Read `me/profile.yaml` first. The list you write is the user's own (`profile.portals`); never edit
`countries/*.yaml` for this. Boards already in the country pack for a location are added to the page
automatically, so don't repeat them.

## 1. Work out what to look for

From the profile, list:
- each distinct `locations[].country` (and the cities in `places`), with `needs_visa_sponsorship`;
- each `role_tracks[]` label and its `titles`;
- `languages` (skip boards whose postings are all in a language they can't work in).

## 2. Research

For each country, find 4–8 boards, in this order of usefulness:
1. **The biggest general boards** people there actually use (not a global aggregator's copy of the same
   listings if the local one is the original).
2. **The government job portal**, if it lists skilled private-sector roles.
3. **Tech / startup boards** for that country or city.
4. **Role boards** for each track (e.g. AI/ML, data, design, product, security, fintech), national ones
   first, then good international ones that cover this country.
5. **Only if `needs_visa_sponsorship: true`:** boards that let you filter by visa sponsorship or
   relocation. Include one only if the board's own site says it offers that filter or only lists such
   jobs. Quote that wording in `desc`.

Skip recruitment-agency sites (and anything in `search.skip_agencies` / `fit.avoid_companies`), paid or
sign-up-walled boards, and boards whose newest postings are months old.

## 3. Check every link

Open each board's URL (a script request, web fetch or the browser). Keep it only if it loads a real job
board. A bot check page ("Just a moment…", HTTP 403 from Cloudflare) means the site is up but blocking
scripts: confirm it in a browser if you can, otherwise leave it out and mention it. Use the final URL
after redirects; drop boards that redirect to a different product or a sign-up page.

## 4. Save

Append to `portals:` in `me/profile.yaml` (keep existing entries; skip URLs already there or in the
country pack):

```yaml
portals:
  - {name: "NodeFlair", desc: "Singapore tech jobs with salary data", url: "https://nodeflair.com/jobs", badge: "SG"}
  - {name: "Relocate.me", desc: "Tech jobs that include relocation support", url: "https://relocate.me/", badge: "Visa"}
  - {name: "MLjobs", desc: "Machine-learning and AI roles", url: "https://www.mljobs.io/", badge: "AI Engineer"}
```

- `badge`: the country code for a country board, the track label for a role board, `Visa` for a
  sponsorship/relocation board.
- `desc`: one short, true line about what the board is good for. No marketing copy.
- When the user needs sponsorship anywhere, put the `Visa` boards first.

Then rebuild (`python scripts/build.py`, plus `python scripts/sync_xlsx.py` if `profile.excel`) and tell
the user in a few lines what you added per country and track, and anything you left out and why.
