"""Renders a CandidateProfile to a one-page PDF resume using fpdf2.

fpdf2 is pure Python (no system dependencies like WeasyPrint/Cairo), which
keeps `cvscreener generate` a single command on any platform, including
Windows without extra native libraries.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from cv_screener.schemas import CandidateProfile

ACCENT = (33, 66, 99)
TEXT_DARK = (30, 30, 30)
TEXT_MUTED = (100, 100, 100)

# fpdf2's core fonts (Helvetica) only support Latin-1. LLM-written prose
# often contains smart punctuation (em dashes, curly quotes, bullets) that
# falls outside that range, which would otherwise crash rendering. Map the
# common offenders to plain ASCII instead of shipping a Unicode font file.
_UNICODE_TO_ASCII = str.maketrans({
    "—": "-", "–": "-",  # em dash, en dash
    "‘": "'", "’": "'",  # curly single quotes
    "“": '"', "”": '"',  # curly double quotes
    "…": "...",  # ellipsis
    "•": "-", "●": "-",  # bullets
    " ": " ",  # non-breaking space
})


def _s(text: str) -> str:
    """Sanitize text for the Latin-1-only core font."""
    if not text:
        return text
    text = text.translate(_UNICODE_TO_ASCII)
    return text.encode("latin-1", errors="replace").decode("latin-1")


class ResumePDF(FPDF):
    pass


def render_resume(profile: CandidateProfile, out_path: Path) -> Path:
    pdf = ResumePDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    left_x = 15
    photo_size = 30
    text_x = left_x + photo_size + 6

    # --- Header: photo + name/title/contact ---
    if profile.photo_path and Path(profile.photo_path).exists():
        pdf.image(profile.photo_path, x=left_x, y=15, w=photo_size, h=photo_size)

    pdf.set_xy(text_x, 15)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*TEXT_DARK)
    pdf.cell(0, 9, _s(profile.full_name), new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(text_x)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*ACCENT)
    title = profile.experience[-1].title if profile.experience else profile.role
    pdf.cell(0, 7, _s(f"{title} ({profile.seniority})"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(text_x)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*TEXT_MUTED)
    contact_line = f"{profile.email}  |  {profile.phone}  |  {profile.location}"
    pdf.multi_cell(0, 5.5, _s(contact_line), new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(15 + photo_size + 4)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    def section_header(label: str) -> None:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*ACCENT)
        pdf.cell(0, 7, _s(label.upper()), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*TEXT_DARK)

    # --- Summary ---
    if profile.summary:
        section_header("Summary")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.2, _s(profile.summary), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # --- Experience ---
    if profile.experience:
        section_header("Experience")
        for exp in reversed(profile.experience):  # most recent first
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.cell(0, 6, _s(f"{exp.title} - {exp.company}"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "I", 9.5)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.cell(0, 5, _s(exp.duration_label), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(*TEXT_DARK)
            pdf.set_font("Helvetica", "", 10)
            for h in exp.highlights:
                pdf.multi_cell(0, 5, _s(f"-  {h}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1.5)

    # --- Education ---
    if profile.education:
        section_header("Education")
        pdf.set_font("Helvetica", "", 10)
        for edu in profile.education:
            pdf.multi_cell(
                0, 5.5,
                _s(f"{edu.degree} - {edu.institution} ({edu.graduation_year})"),
                new_x="LMARGIN", new_y="NEXT",
            )
        pdf.ln(2)

    # --- Skills ---
    if profile.skills:
        section_header("Skills")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, _s(", ".join(profile.skills)), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # --- Languages ---
    if profile.languages:
        section_header("Languages")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 5.5, _s(", ".join(profile.languages)), new_x="LMARGIN", new_y="NEXT")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    return out_path
