"""Structured candidate profile schema.

This is the single source of truth for what a "candidate" looks like — the
same model is used by the generator (to build candidates), the indexer (to
derive embedding text + metadata), and the agent tools (to format results).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Education(BaseModel):
    degree: str
    field: str
    institution: str
    graduation_year: int


class Experience(BaseModel):
    title: str
    company: str
    start_year: int
    end_year: int | None = None  # None == current role
    highlights: list[str] = Field(default_factory=list)

    @property
    def duration_label(self) -> str:
        end = str(self.end_year) if self.end_year else "Present"
        return f"{self.start_year}-{end}"


class CandidateProfile(BaseModel):
    """Full structured + narrative profile for one synthetic candidate."""

    id: str
    full_name: str
    role: str
    seniority: str  # junior | mid | senior | staff/lead
    years_of_experience: int
    location: str
    email: str
    phone: str

    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)  # spoken languages
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)

    summary: str = ""  # LLM-written professional summary paragraph

    photo_path: str | None = None
    resume_pdf_path: str | None = None

    def embedding_text(self) -> str:
        """Text blob used for semantic embedding — narrative content only."""
        exp_lines = []
        for e in self.experience:
            bullets = "; ".join(e.highlights)
            exp_lines.append(
                f"{e.title} at {e.company} ({e.duration_label}): {bullets}"
            )
        edu_lines = [
            f"{ed.degree}, {ed.institution} ({ed.graduation_year})"
            for ed in self.education
        ]
        return "\n".join(
            [
                f"{self.full_name} — {self.role}, {self.seniority} "
                f"({self.years_of_experience} years experience), {self.location}",
                self.summary,
                "Experience:",
                *exp_lines,
                "Education:",
                *edu_lines,
                "Skills: " + ", ".join(self.skills),
                "Languages: " + ", ".join(self.languages),
            ]
        )

    def metadata(self) -> dict:
        """Structured fields stored alongside the vector for filtered lookup."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "role": self.role,
            "seniority": self.seniority,
            "years_of_experience": self.years_of_experience,
            "location": self.location,
            "skills": self.skills,
            "languages": self.languages,
            "companies": [e.company for e in self.experience],
            "resume_pdf_path": self.resume_pdf_path,
            "photo_path": self.photo_path,
        }
