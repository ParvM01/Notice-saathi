import os
from io import BytesIO
from urllib.parse import urlparse

import requests
from pypdf import PdfReader
from google import genai


ALLOWED_DOMAINS = {
    "jeemain.nta.nic.in",
    "cdnbbsr.s3waas.gov.in",
}
MAX_PDF_SIZE = 12 * 1024 * 1024  # 12 MB


def extract_notice_text(url):
    parsed_url = urlparse(url)

    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname not in ALLOWED_DOMAINS
    ):
        raise ValueError("Notice URL is not an approved official URL")

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 NoticeSaathi/1.0"},
        timeout=(10, 30),
        stream=True,
    )
    response.raise_for_status()

    final_url = urlparse(response.url)

    if (
        final_url.scheme != "https"
        or final_url.hostname not in ALLOWED_DOMAINS
    ):
        response.close()
        raise ValueError("PDF redirected to an unapproved domain")

    pdf_data = bytearray()

    for chunk in response.iter_content(chunk_size=65536):
        if chunk:
            pdf_data.extend(chunk)

            if len(pdf_data) > MAX_PDF_SIZE:
                response.close()
                raise ValueError("Notice PDF is too large")

    response.close()

    if not pdf_data.startswith(b"%PDF"):
        raise ValueError("The notice link did not return a PDF")

    reader = PdfReader(BytesIO(pdf_data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    text = text.strip()

    if not text:
        raise ValueError("Could not extract readable text from this PDF")

    return text[:30000]


def generate_notice_explanation(notice):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    notice_text = extract_notice_text(notice["url"])

    client = genai.Client(api_key=api_key)

    prompt = f"""
You help Indian students understand official exam notices.
Explain only information supported by the notice text.
Do not guess dates, fees, eligibility, or instructions.
Write in simple Hinglish.

Include:
1. Notice ka matlab
2. Important details
3. Student ko kya karna chahiye
4. Important caution

Notice title: {notice["title"]}
Notice category: {notice["category"]}

Notice text:
{notice_text}
"""

    result = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=prompt,
    )

    explanation = (result.text or "").strip()

    if not explanation:
        raise RuntimeError("Gemini returned an empty explanation")

    return {
        "mode": "gemini",
        "is_ai_generated": True,
        "notice_id": notice["id"],
        "notice_title": notice["title"],
        "category": notice["category"],
        "hinglish_explanation": explanation,
        "student_action": (
            "Original official notice mein dates aur instructions "
            "zaroor verify karein."
        ),
        "official_url": notice["url"],
        "important_note": (
            "Yeh AI-generated summary hai. Final information ke liye "
            "original official notice hi follow karein."
        ),
    }