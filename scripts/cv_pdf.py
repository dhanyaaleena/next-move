#!/usr/bin/env python3
"""Render a CV (the cv.json shape) to an A4 PDF in a clean one-column layout.

    python scripts/cv_pdf.py me/cv.json out.pdf        # prints the page count
    from cv_pdf import render; pages = render(cv, "out.pdf", links=[...])

Same layout the tracker page uses for its CV preview: navy name and section
rules, Arial-style type at 10pt, right-aligned dates, round bullets.
"""
import html
import os
import re
import sys

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle


def _register_fonts():
    """Use Arial if present, else Liberation Sans (metric-compatible), else built-in Helvetica."""
    candidates = [
        ("/System/Library/Fonts/Supplemental/", ["Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf"]),
        ("/Library/Fonts/", ["Arial.ttf", "Arial Bold.ttf", "Arial Italic.ttf", "Arial Bold Italic.ttf"]),
        ("C:/Windows/Fonts/", ["arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf"]),
        ("/usr/share/fonts/truetype/liberation2/", ["LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf", "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf"]),
        ("/usr/share/fonts/truetype/liberation/", ["LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf", "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf"]),
    ]
    for d, files in candidates:
        if all(os.path.exists(os.path.join(d, f)) for f in files):
            from reportlab.lib.fonts import addMapping
            names = ["CV", "CV-Bold", "CV-Italic", "CV-BoldItalic"]
            for n, f in zip(names, files):
                pdfmetrics.registerFont(TTFont(n, os.path.join(d, f)))
            addMapping("CV", 0, 0, "CV"); addMapping("CV", 1, 0, "CV-Bold")
            addMapping("CV", 0, 1, "CV-Italic"); addMapping("CV", 1, 1, "CV-BoldItalic")
            return "CV", "CV-Bold", "CV-Italic"
    return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


REG, BOLD, ITAL = _register_fonts()
NAVY, INK, GREY, TAG = HexColor("#1F3A5F"), HexColor("#111111"), HexColor("#222222"), HexColor("#333333")
L, R, T, B = 33.7, 34, 19, 22
W = A4[0] - L - R
LEAD = 12.4


def S(name, **kw):
    base = dict(fontName=REG, fontSize=10, leading=LEAD, textColor=INK, spaceBefore=0, spaceAfter=0)
    base.update(kw)
    return ParagraphStyle(name, **base)


st_name = S("n", fontName=BOLD, fontSize=18, leading=20.7, textColor=NAVY)
st_title = S("t", fontName=BOLD, fontSize=10.5, leading=12.4, textColor=NAVY, spaceBefore=1)
st_contact = S("c", fontSize=9, leading=11.4, textColor=GREY, spaceBefore=1.6)
st_rtw = S("r", fontName=BOLD, fontSize=9, leading=11.4, textColor=GREY, spaceBefore=3.1)
st_body = S("b")
st_skill = S("s", spaceAfter=1.2)
st_tag = S("g", fontName=ITAL, textColor=TAG)
st_bul = S("u", leftIndent=14.3, bulletIndent=2.3, bulletFontSize=7, bulletFontName=REG)
st_l = S("l", fontName=BOLD, fontSize=9.9)
st_r = S("rr", alignment=TA_RIGHT)
st_h = S("h", fontName=BOLD, fontSize=10.2, leading=12, textColor=NAVY)


def e(s):
    return html.escape(str(s or ""), quote=False)


def md(s, links=()):
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e(s))
    for l in links or ():
        if l.get("text") and l.get("url"):
            t = t.replace(e(l["text"]), '<a href="%s"><u>%s</u></a>' % (e(l["url"]), e(l["text"])))
    return t


def contact(c):
    s = str(c)
    m = re.match(r"^(.*?)([\w.+-]+@[\w-]+\.[\w.]+|(?:[\w-]+\.)+[a-z]{2,}(?:/[\w/.-]*)?)$", s, re.I)
    if not m:
        return e(s)
    href = ("mailto:" if "@" in m.group(2) else "https://") + m.group(2)
    return e(m.group(1)) + '<a href="%s">%s</a>' % (e(href), e(m.group(2)))


class Rule(Flowable):
    def __init__(self, w):
        super().__init__()
        self.width, self.height = w, 0.75

    def draw(self):
        self.canv.setStrokeColor(NAVY)
        self.canv.setLineWidth(0.75)
        self.canv.line(0, 0, self.width, 0)


def sec(t):
    return [Spacer(1, 5.3), Paragraph(e(t), st_h), Spacer(1, 1), Rule(W), Spacer(1, 4.3)]


def row(left, right):
    tw = pdfmetrics.stringWidth(re.sub("<[^>]+>", "", html.unescape(right)), REG, 10) + 2
    t = Table([[Paragraph(left, st_l), Paragraph(right, st_r)]], colWidths=[W - tw, tw], hAlign="LEFT")
    t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                           ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    return t


def render(cv, out, links=()):
    """Write the PDF and return its page count."""
    bl = lambda items: [Paragraph(md(b, links), st_bul, bulletText="●") for b in items]  # noqa: E731
    story = [Paragraph(e(cv["name"]), st_name), Paragraph(e(cv["title"]), st_title),
             Paragraph(" | ".join(contact(c) for c in cv.get("contact", [])), st_contact)]
    if cv.get("rightToWork"):
        story.append(Paragraph("Right to work: " + e(cv["rightToWork"]), st_rtw))
    story += sec("PROFILE") + [Paragraph(md(cv["profile"], links), st_body)]
    story += sec("SKILLS")
    for line in cv.get("skills", []):
        story.append(Paragraph(" &nbsp;| &nbsp;".join("<b>%s:</b> %s" % (e(g["label"]), e(", ".join(g["items"]))) for g in line), st_skill))
    story += sec("EXPERIENCE")
    for i, x in enumerate(cv.get("experience", [])):
        if i:
            story.append(Spacer(1, 3.8))
        story.append(row(e(x["role"]) + " | " + e(x["company"]), e(x.get("location")) + " | " + e(x.get("dates"))))
        if x.get("tagline"):
            story.append(Paragraph(e(x["tagline"]), st_tag))
        story.append(Spacer(1, 1.5))
        story += bl(x["bullets"])
    if cv.get("projects"):
        story += sec("PROJECTS")
        for p in cv["projects"]:
            story.append(row(e(p["name"]) + (" | " + e(p["sub"]) if p.get("sub") else ""), e(p.get("dates"))))
            story.append(Spacer(1, 1.5))
            story += bl(p["bullets"])
    if cv.get("education"):
        story += sec("EDUCATION")
        for x in cv["education"]:
            story.append(row(e(x["degree"]) + " | " + e(x["school"]), e(x.get("location")) + " | " + e(x.get("dates"))))
    pages = {"n": 0}

    def onpage(c, d):
        pages["n"] = d.page

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    doc = BaseDocTemplate(out, pagesize=A4, leftMargin=L, rightMargin=R, topMargin=T, bottomMargin=B,
                          title="%s CV" % str(cv["name"]).title(), author=str(cv["name"]).title())
    fr = Frame(L, B, W, A4[1] - T - B, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[fr], onPage=onpage)])
    doc.build(story)
    return pages["n"]


if __name__ == "__main__":
    import json
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    print(render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]), "page(s)")
