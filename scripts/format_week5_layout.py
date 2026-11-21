"""Restore two-column article prose while allowing wide tables/figures.

Usage (from repository root):
    python scripts/build_week5_article.py
    python scripts/format_week5_layout.py

The script reads docs/week5/USD_Capstone_Week_5_Group_1.docx and creates
USD_Capstone_Week_5_Formatted_Review.docx. It does not overwrite the source.
"""
from copy import deepcopy
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/week5/USD_Capstone_Week_5_Group_1.docx"
DEST = ROOT / "docs/week5/USD_Capstone_Week_5_Formatted_Review.docx"


def two_or_one(sect, count):
    col = sect.find(qn("w:cols"))
    if col is None:
        col = OxmlElement("w:cols")
        sect.append(col)
    col.set(qn("w:num"), str(count))
    col.set(qn("w:space"), "480" if count == 2 else "0")
    if count == 2:
        col.attrib.pop(qn("w:equalWidth"), None)
        for child in list(col):
            col.remove(child)


def find_paragraph(body, prefix):
    for el in body.iterchildren():
        if el.tag == qn("w:p") and Paragraph(el, doc).text.startswith(prefix):
            return el
    raise ValueError(f"Cannot find paragraph starting: {prefix!r}")


def next_table(el):
    n = el.getnext()
    while n is not None and n.tag != qn("w:tbl"):
        n = n.getnext()
    if n is None:
        raise ValueError("Cannot find expected table after heading")
    return n



def compact_table_1(doc, body):
    """Replace Table 1 with a concise, single-column-width, two-field table."""
    old = next_table(find_paragraph(body, "Table 1"))
    data = [
        ("Variable", "Role and use"),
        ("UTC time", "Unique timeline key; supports sorting and lag features."),
        ("Local date/hour", "Calendar features and daily peak timing."),
        ("Demand", "Observed raw target; cleaned adjusted history for lags."),
        ("Raw/imputed", "Separate fields retained for quality auditing."),
        ("EIA forecast", "Retrospective reference only; not a predictor."),
        ("Calendar/history", "Hour, holiday, seasonal and lag predictors."),
    ]
    new = doc.add_table(rows=len(data), cols=2)
    new.autofit = False
    new.alignment = WD_TABLE_ALIGNMENT.CENTER
    try:
        new.style = 'Table Grid'
    except KeyError:
        pass
    for idx, (left, right) in enumerate(data):
        for col, txt in enumerate((left, right)):
            c = new.cell(idx,col)
            c.text = txt
            c.width = Inches(1.02 if col==0 else 2.22)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            for p in c.paragraphs:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.name='Times New Roman'
                    r.font.size=Pt(8)
                    if idx==0: r.bold=True
                    # Week 5 revised descriptions follow blue-text convention.
                    elif col==1: r.font.color.rgb=RGBColor(0,0,255)
    for col, width in zip(new.columns,(Inches(1.02), Inches(2.22))):
        col.width = width
    old.addprevious(new._tbl)
    old.getparent().remove(old)

def insert_boundary_after(element, count, base_sect):
    new_p = OxmlElement("w:p")
    p_pr = OxmlElement("w:pPr")
    sect = deepcopy(base_sect)
    two_or_one(sect, count)
    section_type = sect.find(qn("w:type"))
    if section_type is None:
        section_type = OxmlElement("w:type")
        sect.insert(0, section_type)
    section_type.set(qn("w:val"), "continuous")
    p_pr.append(sect)
    new_p.append(p_pr)
    element.addnext(new_p)


if not SOURCE.exists():
    raise FileNotFoundError(f"First generate your Week 5 article: {SOURCE}")
doc = Document(SOURCE)
body = doc.element.body

# Guard against accidentally applying the patch twice or to a very different draft.
if len(doc.sections) != 5:
    raise ValueError(
        f"Expected the original five-section Week 5 draft, found {len(doc.sections)}. "
        "Run the article builder first and then run this script once."
    )

# The fourth original section is the one-column Data Understanding/Methods span.
base = deepcopy(doc.sections[3]._sectPr)

compact_table_1(doc, body)


# End of each consecutive article segment and number of columns in that segment.
# These boundaries are based on unique manuscript anchors, not brittle line numbers.
boundaries = [
    (find_paragraph(body, "UTC time is the unique chronological key"), 2),
    (find_paragraph(body, "The source audit found all"), 2),
    (next_table(find_paragraph(body, "Table 2")), 1),
    (find_paragraph(body, "After continuity treatment"), 2),
    (find_paragraph(body, "Note. Daily maxima vary substantially"), 1),
    (find_paragraph(body, "Figure 1 shows recurring seasonality"), 2),
    (find_paragraph(body, "Note. Summer demand remains higher"), 1),
    (find_paragraph(body, "Note. The darkest cells occur"), 1),
    (find_paragraph(body, "METHODOLOGY"), 2),
    (find_paragraph(body, "Note. Annual validation determines"), 1),
    (find_paragraph(body, "The forecast is defined as a batch prediction"), 2),
    (next_table(find_paragraph(body, "Table 3")), 1),
]

# Set the inherited section end (before Modeling) to two columns.
original_end = None
model_p = find_paragraph(body, "Modeling")
node = model_p.getprevious()
while node is not None:
    if node.tag == qn("w:p") and node.pPr is not None and node.pPr.sectPr is not None:
        original_end = node.pPr.sectPr
        break
    node = node.getprevious()
if original_end is None:
    raise ValueError("Could not locate the section break immediately before Modeling")
two_or_one(original_end, 2)

for el, count in boundaries:
    insert_boundary_after(el, count, base)

doc.save(DEST)
print(f"Saved formatted review document: {DEST}")