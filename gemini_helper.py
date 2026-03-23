import google.generativeai as genai
import json
import re
from datetime import datetime


def split_work_into_days(api_key: str, work_description: str, dates: list, num_days: int) -> list:
    """Split work description into N daily parts using Gemini."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""Divide the following internship work into {num_days} logical daily parts.
    Maintain realistic progression and continuity. Each day should be distinct but related.

    Work:
    {work_description}

    Return ONLY a valid JSON array (no markdown, no explanation):
    [
      {{ "day": 1, "work": "..." }},
      ...
    ]
    Make sure to return exactly {num_days} items."""

    response = model.generate_content(prompt)
    text = response.text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        daily_splits = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse Gemini response as JSON. "
            f"Please try again or verify your API key. Details: {exc}"
        ) from exc

    result = []
    for i, item in enumerate(daily_splits[:num_days]):
        result.append({
            "day": i + 1,
            "date": dates[i] if i < len(dates) else "",
            "work": item["work"]
        })
    return result


def generate_journal_entry(api_key: str, date: str, work: str) -> dict:
    """Generate structured journal entry for one day using Gemini."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = f"""Generate a professional internship daily journal entry.

Date: {date}
Work Done: {work}

Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "my_space": "Brief personal reflection (1-2 sentences)",
  "tasks_carried_out": "Detailed tasks done today (3-5 bullet points as plain text separated by newlines)",
  "key_learnings": "Key learnings and observations (2-3 points as plain text separated by newlines)",
  "tools_used": "Tools, equipment, technologies or techniques used (comma-separated list)",
  "special_achievements": "Any special achievements or milestones (1-2 sentences or 'N/A')"
}}

Keep it concise, professional, realistic, and non-repetitive."""

    response = model.generate_content(prompt)
    text = response.text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse Gemini journal response as JSON. "
            f"Please try again or verify your API key. Details: {exc}"
        ) from exc
