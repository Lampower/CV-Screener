"""Synthetic headshot generation via gpt-image-1.

Uses the cheapest tier (`quality="low"`, 1024x1024) — this is a headshot for
a mock resume, not print material, and the task's budget is a few dollars.
Cost is roughly $0.01-0.02 per image at this tier.

Generated photos are uploaded straight to S3-compatible object storage
(`cv_screener.storage`) rather than written to local disk — see
docker-compose.yml / storage.py for why. The resized image is also handed
back in memory so `pdf_render.py` can embed it into the PDF without a round
trip back through storage.
"""

from __future__ import annotations

import base64
import io

from openai import OpenAI
from PIL import Image

from cv_screener.config import IMAGE_MODEL, require_api_key
from cv_screener.schemas import CandidateProfile
from cv_screener.storage import photo_key, upload_bytes


def _photo_prompt(profile: CandidateProfile) -> str:
    return (
        "A professional corporate headshot photo of a person for a resume/CV. "
        f"They work as a {profile.seniority} {profile.role}. "
        "Plain neutral studio background, shoulders-up framing, business "
        "casual attire, natural lighting, friendly neutral expression, "
        "realistic photograph style, high quality. No text, no logos, no "
        "watermarks in the image."
    )


def generate_headshot(client: OpenAI, profile: CandidateProfile) -> tuple[str, Image.Image]:
    """Generates a headshot, uploads it to S3 under `photos/{id}.png`, and
    returns (object_key, resized_PIL_image) — the image is reused directly
    by pdf_render.py to avoid re-downloading it from storage."""
    require_api_key()
    result = client.images.generate(
        model=IMAGE_MODEL,
        prompt=_photo_prompt(profile),
        size="1024x1024",
        quality="low",
        n=1,
    )
    raw_bytes = base64.b64decode(result.data[0].b64_json)

    # Downsize before storing — the resume only needs a small headshot, and
    # this keeps per-candidate PDFs a few hundred KB instead of multiple MB.
    img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    img.thumbnail((400, 400))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)

    key = photo_key(profile.id)
    upload_bytes(key, buffer.getvalue(), content_type="image/png")
    return key, img
