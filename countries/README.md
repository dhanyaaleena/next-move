# Country packs

One file per country (ISO code, plus `EU` for remote-Europe). Each profile location has a `country`, which picks the pack used for:

- **visa** — the work route, the official sponsor register (if the country has one) and how to check it, and wording in postings that signals sponsorship.
- **boards** — job boards shown at the bottom of the tracker and searched during a refresh.
- **linkedin_location** — the location string used for LinkedIn searches.

Salary thresholds and fees are left out on purpose: they change, so Claude reads them live from the official link.

**Your country isn't here?** Ask Claude: *"add a country pack for Portugal"*. It researches the work-visa route, any official sponsor register, and the main job boards, and writes `countries/PT.yaml` in the same shape. Pull requests with new packs are welcome.
