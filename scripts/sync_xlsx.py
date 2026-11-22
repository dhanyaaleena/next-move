#!/usr/bin/env python3
"""Keep an Excel copy of your tracker: me/Job_Tracker.xlsx (or --file).

    python scripts/sync_xlsx.py            # create the workbook if needed, then add new jobs + people

Sheets: Jobs (one row per role; Status / Applied on / Notes are yours to edit),
People (contacts per role), Portals, Summary, How to use.

Existing rows are never changed, reordered or deleted — only new jobs and new
people are appended. A job already in the sheet (same company + role, or same
posting URL) is skipped. Close the file in Excel before running.
"""
import argparse
import os
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, load_profile, make_id, me_path, url_key, pick_variant, variant_file  # noqa: E402
import build  # noqa: E402

F = "Arial"
BODY = Font(name=F, size=10)
BOLD = Font(name=F, size=10, bold=True)
HEAD = Font(name=F, bold=True, color="FFFFFF", size=10)
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
LINK = Font(name=F, size=10, color="0563C1", underline="single")
INPUT = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="D9D9D9")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
STATUSES = ["To apply", "Applied", "Screening", "Interviewing", "Offer", "Rejected", "Not interested", "Closed", "Skipped", "Duplicate", "Wrong location"]
COLS = ["#", "Company", "Role", "Location", "Region", "Experience asked", "Visa / sponsorship", "Salary",
        "Job link", "Resume", "Status", "Applied on", "Follow up on", "Notes"]
WIDTHS = [5, 24, 36, 24, 14, 14, 36, 16, 13, 28, 12, 12, 12, 50]
PCOLS = ["Company", "Role", "Name", "Type", "Title", "LinkedIn", "Contacted?", "Email", "Email confidence"]
PWIDTHS = [22, 32, 22, 14, 34, 40, 11, 30, 14]
MAXR = 3000


def header(ws, cols, widths):
    ws.append(cols)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    for c in ws[1]:
        c.font, c.fill, c.border = HEAD, HEAD_FILL, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "C2" if len(cols) > 9 else "A2"
    ws.auto_filter.ref = f"A1:{ws.cell(1, len(cols)).column_letter}{MAXR}"


def create(path, profile, portals):
    wb = Workbook()
    ws = wb.active
    ws.title = "Jobs"
    header(ws, COLS, WIDTHS)
    dv = DataValidation(type="list", formula1='"' + ",".join(STATUSES) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"K2:K{MAXR}")
    fills = {"Applied": "DDEBF7", "Screening": "BDD7EE", "Interviewing": "C6E0B4", "Offer": "A9D08E",
             "Rejected": "F8CBAD", "Not interested": "EDEDED", "Closed": "D9D9D9", "Skipped": "EDEDED", "Duplicate": "EDEDED", "Wrong location": "EDEDED"}
    for s, col in fills.items():
        ws.conditional_formatting.add(f"A2:J{MAXR}", FormulaRule(formula=[f'$K2="{s}"'], fill=PatternFill("solid", fgColor=col)))
    ws.conditional_formatting.add(f"M2:M{MAXR}", FormulaRule(
        formula=['AND($M2<>"",$M2<=TODAY(),OR($K2="Applied",$K2="Screening"))'], fill=PatternFill("solid", fgColor="FFC7CE")))

    p = wb.create_sheet("People")
    header(p, PCOLS, PWIDTHS)
    dv2 = DataValidation(type="list", formula1='"No,Yes"', allow_blank=True)
    p.add_data_validation(dv2)
    dv2.add(f"G2:G{MAXR * 3}")

    s = wb.create_sheet("Summary")
    s["A1"], s["B1"] = "Status", "Count"
    for c in (s["A1"], s["B1"]):
        c.font, c.fill = HEAD, HEAD_FILL
    for i, st in enumerate(STATUSES, 2):
        s.cell(i, 1, st).font = BODY
        s.cell(i, 2, f"=COUNTIF(Jobs!$K$2:$K${MAXR},A{i})").font = BODY
    n = len(STATUSES) + 2
    s.cell(n, 1, "Total").font = BOLD
    s.cell(n, 2, f"=SUM(B2:B{n - 1})").font = BOLD
    s.cell(n + 1, 1, "Follow-ups due").font = BOLD
    s.cell(n + 1, 2, f'=SUMPRODUCT((Jobs!$M$2:$M${MAXR}<>"")*(Jobs!$M$2:$M${MAXR}<=TODAY())*((Jobs!$K$2:$K${MAXR}="Applied")+(Jobs!$K$2:$K${MAXR}="Screening")))').font = BOLD
    s.column_dimensions["A"].width = 18
    # role track x location group (notes start with "<track> · ")
    locs = [l["id"] for l in profile.get("locations") or []]
    tracks = [t["id"] for t in profile.get("role_tracks") or []]
    s.cell(1, 4, "Role type").font = HEAD
    s.cell(1, 4).fill = HEAD_FILL
    for k, lid in enumerate(locs):
        c = s.cell(1, 5 + k, lid)
        c.font, c.fill = HEAD, HEAD_FILL
    for r, tid in enumerate(tracks, 2):
        s.cell(r, 4, tid).font = BODY
        for k, lid in enumerate(locs):
            col = s.cell(1, 5 + k).column_letter
            s.cell(r, 5 + k, f'=COUNTIFS(Jobs!$E$2:$E${MAXR},{col}$1,Jobs!$N$2:$N${MAXR},$D{r}&" ·*")').font = BODY
    s.column_dimensions["D"].width = 18

    g = wb.create_sheet("Portals")
    header(g, ["Portal", "What it's good for", "Link", "Scope", "Last checked", "Alert set up?"], [32, 48, 12, 10, 14, 14])
    for name, desc, url, badge in portals:
        g.append([name, desc, "Open", badge, None, None])
        r = g.max_row
        g.cell(r, 3).hyperlink = url
        g.cell(r, 3).font = LINK
        for c in range(1, 7):
            g.cell(r, c).border = BORDER
            if c != 3:
                g.cell(r, c).font = BODY

    h = wb.create_sheet("How to use")
    h.column_dimensions["A"].width = 110
    for i, t in enumerate([
        "Edit the yellow columns (Status, Applied on, Notes). Status is a dropdown; rows colour by status.",
        "Follow up on = Applied on + 7 days, and turns red when due while status is Applied/Screening.",
        "People lists who to contact for each role. Tick Contacted? when you've messaged them.",
        "Claude only ever ADDS rows here (new jobs and people). Your edits are never overwritten.",
        "The HTML tracker is the main view; its statuses are separate from this sheet's.",
    ], 1):
        c = h.cell(i, 1, t)
        c.font, c.alignment = BODY, Alignment(wrap_text=True)
    wb.save(path)
    print(f"created {path}")


def visa_text(j):
    v = j.get("visa") or {}
    if not v:
        return "-"
    lab = {"sponsors": "Sponsors", "not_needed": "Not needed", "unclear": "Unclear", "no": "No sponsorship"}.get(v.get("status"), v.get("status"))
    return lab + (": " + v["evidence"] if v.get("evidence") else "")


def sync(path, profile, jobs):
    try:
        wb = load_workbook(path)
    except PermissionError:
        sys.exit("Could not open the workbook — close it in Excel and try again.")
    ws = wb["Jobs"]
    have_ids, have_urls, last, num = set(), set(), 1, 0
    for r in range(2, ws.max_row + 1):
        co = ws.cell(r, 2).value
        if not co:
            continue
        last = r
        num = max(num, ws.cell(r, 1).value or 0) if isinstance(ws.cell(r, 1).value, (int, float)) else num
        have_ids.add(make_id(co, ws.cell(r, 3).value))
        h = ws.cell(r, 9).hyperlink
        if h and h.target:
            have_urls.add(url_key(h.target))
    added = 0
    new_jobs = []
    for j in jobs:
        if j["id"] in have_ids or make_id(j["company"], j["role"]) in have_ids or (j.get("direct", True) and url_key(j["url"]) in have_urls):
            continue
        last += 1
        num += 1
        r = last
        for c in range(1, 15):
            cell = ws.cell(r, c)
            cell.font, cell.border = BODY, BORDER
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        for c in (11, 12, 14):
            ws.cell(r, c).fill = INPUT
        ws.cell(r, 12).number_format = ws.cell(r, 13).number_format = "yyyy-mm-dd"
        parts = [f"{j['track']} · {j['fit']} fit", "via " + (j.get("source") or "?")]
        if not j.get("direct", True):
            parts.append("link opens results/careers page")
        if j.get("note"):
            parts.append(j["note"])
        if j.get("skills"):
            parts.append("Skills: " + ", ".join(j["skills"]))
        vals = [num, j["company"], j["role"], j.get("place"), j["location"], j.get("experience"), visa_text(j),
                None if j.get("salary") in (None, "Not listed") else j["salary"]]
        for c, v in enumerate(vals, 1):
            ws.cell(r, c, v)
        ws.cell(r, 9, "Open posting").hyperlink = j["url"]
        ws.cell(r, 9).font = LINK
        v = pick_variant(profile, j)
        ws.cell(r, 10, j.get("cv_pdf") or (variant_file(profile, v) if v else None))
        ws.cell(r, 11, "To apply")
        ws.cell(r, 13, f'=IF(L{r}="","",L{r}+7)')
        ws.cell(r, 14, " | ".join(parts))
        have_ids.add(j["id"])
        new_jobs.append(j)
        added += 1

    pp = wb["People"] if "People" in wb.sheetnames else None
    padded = 0
    if pp is not None:
        # one row per person per company (they're usually hiring for every role there)
        have_p = {(str(pp.cell(r, 1).value).lower(), str(pp.cell(r, 3).value).lower()) for r in range(2, pp.max_row + 1)}
        for j in jobs:
            for p in j.get("people") or []:
                p = p if isinstance(p, dict) else dict(zip(["name", "title", "url", "tag", "email", "email_confidence"], p))
                key = (str(j["company"]).lower(), str(p.get("name")).lower())
                if key in have_p:
                    continue
                pp.append([j["company"], j["role"], p.get("name"), p.get("tag"), p.get("title"), p.get("url"), "No",
                           p.get("email"), p.get("email_confidence")])
                r = pp.max_row
                for c in range(1, 10):
                    pp.cell(r, c).font, pp.cell(r, c).border = BODY, BORDER
                if p.get("url"):
                    pp.cell(r, 6).hyperlink = p["url"]
                    pp.cell(r, 6).font = LINK
                pp.cell(r, 7).fill = INPUT
                have_p.add(key)
                padded += 1
    try:
        wb.save(path)
    except PermissionError:
        sys.exit("Could not save — close the workbook in Excel and try again.")
    print(f"{added} new jobs and {padded} new people added to {path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--me")
    ap.add_argument("--file", help="workbook path (default me/Job_Tracker.xlsx)")
    a = ap.parse_args()
    profile = load_profile(a.me)
    data = load_json(me_path(a.me, "jobs.json"), default={"jobs": []})
    path = a.file or os.path.expanduser(str(profile.get("excel_file") or "Job_Tracker.xlsx"))
    if not os.path.isabs(path):
        path = me_path(a.me, path)
    if not os.path.exists(path):
        create(path, profile, build.portals_for(profile, data))
    sync(path, profile, data["jobs"])
