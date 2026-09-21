"""Synthetic headshot generation via gpt-image-1.

Uses the cheapest tier (`quality="low"`, 1024x1024) — this is a headshot for
a mock resume, not print material, and the task's budget is a few dollars.
Cost is roughly $0.01-0.02 per image at this tier.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

from openai import OpenAI
from PIL import Image

from cv_screener.config import IMAGE_MODEL, require_api_key
from cv_screener.schemas import CandidateProfile


def _photo_prompt(profile: CandidateProfile) -> str:
    return (
        "A professional corporate headshot photo of a person for a resume/CV. "
        f"They work as a {profile.seniority} {profile.role}. "
        "Plain neutral studio background, shoulders-up framing, business "
        "casual attire, natural lighting, friendly neutral expression, "
        "realistic photograph style, high quality. No text, no logos, no "
        "watermarks in the image."
    )


def generate_headshot(client: OpenAI, profile: CandidateProfile, out_dir: Path) -> Path:
    require_api_key()
    result = client.images.generate(
        model=IMAGE_MODEL,
        prompt=_photo_prompt(profile),
        size="1024x1024",
        quality="low",
        n=1,
    )
    image_b64 = result.data[0].b64_json
    raw_bytes = base64.b64decode(image_b64)

    # Downsize before saving — the resume only needs a small headshot, and
    # this keeps per-candidate PDFs a few hundred KB instead of multiple MB.
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img.thumbnail((400, 400))
    out_path = out_dir / f"{profile.id}.png"
    img.save(out_path, format="PNG", optimize=True)
    return out_path


def generate_headshots(profiles: list[CandidateProfile], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    for profile in profiles:
        path = generate_headshot(client, profile, out_dir)
        profile.photo_path = str(path)
