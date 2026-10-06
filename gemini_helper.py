import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Days written per Gemini request. Small batches keep each reply well under the
# output limit; one request for a whole month got cut off and produced no entries.
BATCH_SIZE = 7
MAX_PARALLEL_REQUESTS = 4
MAX_ATTEMPTS = 3
RETRY_DELAYS = [5, 15, 30]  # seconds to wait after a rate-limit / overload error

# Filler the model sometimes falls back to; never acceptable in a journal.
PLACEHOLDER_RE = re.compile(r"^\s*(n/?a|none|nil|-+|various( tools)?|tbd|not applicable)\s*\.?\s*$", re.IGNORECASE)


class GeminiError(Exception):
    """A Gemini failure with a message that can be shown to the user as-is."""


class DayWork(BaseModel):
    day: int
    work: str


class JournalEntry(BaseModel):
    day: int
    my_space: str
    tasks_carried_out: list[str]
    key_learnings: list[str]
    tools_used: list[str]
    special_achievements: str


def get_ordinal_suffix(day: int) -> str:
    if 11 <= (day % 100) <= 13:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')

def format_date(date_str: str) -> str:
    try:
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%y"]:
            try:
                parsed = datetime.strptime(date_str, fmt)
                day = parsed.day
                suffix = get_ordinal_suffix(day)
                return parsed.strftime(f"{day}{suffix} %B %Y")
            except ValueError:
                continue
        return date_str
    except Exception:
        return date_str


def _friendly_error(e: errors.APIError) -> GeminiError:
    msg = str(e)
    if e.code in (401, 403) or "API key" in msg or "API_KEY" in msg:
        return GeminiError("Gemini rejected the API key. Check that it is correct and enabled in Google AI Studio.")
    if e.code == 429:
        return GeminiError("Gemini's rate limit or daily quota was reached. Wait a minute and try again, or use a different API key.")
    if e.code == 404:
        return GeminiError(f"The Gemini model '{GEMINI_MODEL}' is not available. Set GEMINI_MODEL to a current model.")
    if e.code and e.code >= 500:
        return GeminiError("Gemini is overloaded right now. Please try again in a minute.")
    return GeminiError(f"Gemini request failed: {msg}")


def call_gemini(api_key, prompt, schema, on_retry=None):
    """Send one request and return the parsed JSON (list of dicts). Retries rate limits and overloads."""
    client = genai.Client(api_key=api_key)
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.95,
                    max_output_tokens=16384,
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        except errors.APIError as e:
            retryable = e.code == 429 or (e.code is not None and e.code >= 500)
            if retryable and attempt < len(RETRY_DELAYS):
                if on_retry:
                    on_retry(RETRY_DELAYS[attempt])
                time.sleep(RETRY_DELAYS[attempt])
                continue
            raise _friendly_error(e) from e

        if response.parsed is not None:
            return [item.model_dump() if isinstance(item, BaseModel) else item for item in response.parsed]
        # The reply didn't match the schema (usually cut off); fall back to raw JSON if it is valid.
        text = (response.text or "").strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []
    return []


def split_work_into_days(api_key: str, work_description: str, dates: list, num_days: int) -> list:
    prompt = f"""
You are a professional OJT training supervisor.

Divide the following work into EXACTLY {num_days} day-wise entries, numbered 1 to {num_days}.

RULES:
- No HR / meetings / company talk
- Only technical/project work
- Each day must be unique
- Maintain progression:
  understanding → planning → implementation → debugging → improvement
- Each day: 2–4 meaningful sentences
- No generic phrases
- No repetition
- No empty or incomplete entries
- Use college/student-level tools (avoid professional tools like Jira, Azure, enterprise software)

WORK:
{work_description}
"""

    by_day = {}
    for _ in range(MAX_ATTEMPTS):
        for item in call_gemini(api_key, prompt, list[DayWork]):
            day, work = item.get("day"), str(item.get("work", "")).strip()
            if isinstance(day, int) and 1 <= day <= num_days and work and not PLACEHOLDER_RE.match(work):
                by_day.setdefault(day, work)
        if len(by_day) == num_days:
            break
    if len(by_day) < num_days:
        raise GeminiError(
            f"Gemini only planned {len(by_day)} of {num_days} days. "
            "Please try again, or add more detail to your work description."
        )

    return [
        {"day": i, "date": format_date(dates[i - 1]) if i - 1 < len(dates) else "", "work": by_day[i]}
        for i in range(1, num_days + 1)
    ]


# ── Journal entries ───────────────────────────────────────────────────────────
# Lengths are sized to the boxes on the journal page (see FIELD_COORDS in pdf_filler.py):
# long enough to fill them, short enough not to be cut off.
JOURNAL_PROMPT = """
You write daily OJT (on-the-job training) journal entries for a college student's internship.

The student's whole internship, day by day, for context:
{timeline}

Write the journal entries for these days only: {days}.

Every entry must be specific to that day's work: name the actual feature, module, bug, screen,
dataset or concept involved. Each day must read differently from the others.

Fields (fill every one; never write "N/A", "None", "Various tools" or similar):
- my_space: a first-person reflection of 110-150 words, in 5-7 sentences: what the student set out
  to do, how it went, what was tricky, how they handled it, and how they feel about the progress.
- tasks_carried_out: 5-6 items. Each item is one complete sentence of 10-14 words describing a
  concrete task done that day. No numbering or bullets.
- key_learnings: 4-5 items. Each item is one complete sentence of 8-14 words about something
  specific learned or observed. No numbering or bullets.
- tools_used: 5-7 items, each formatted "Tool – what it was used for today", at most 50 characters.
  Use realistic student tools (e.g. VS Code, Git, GitHub, Python, JavaScript, React, Flask, Node.js,
  MySQL, PostgreSQL, Postman, Chrome DevTools, Figma, Linux terminal). No enterprise tools such as
  Jira, Azure or Salesforce.
- special_achievements: 2-3 sentences, 35-55 words, about a concrete result or milestone that day
  (something finished, fixed, improved or understood). Never leave it empty.

No HR, meetings or company-policy content.
"""


def _words(text: str) -> int:
    return len(str(text).split())


def _clean_items(items) -> list:
    if isinstance(items, str):
        items = items.split("\n")
    out = []
    for item in items or []:
        item = re.sub(r"^\s*(?:[-•*]|\d+[.)])\s*", "", str(item)).strip()
        if item and not PLACEHOLDER_RE.match(item):
            out.append(item)
    return out


def _check_entry(raw: dict):
    """Return (entry, too_short). entry is None when the reply is unusable."""
    entry = {
        "my_space": str(raw.get("my_space", "")).strip(),
        "tasks_carried_out": _clean_items(raw.get("tasks_carried_out")),
        "key_learnings": _clean_items(raw.get("key_learnings")),
        "tools_used": _clean_items(raw.get("tools_used")),
        "special_achievements": str(raw.get("special_achievements", "")).strip(),
    }
    for key in ("my_space", "special_achievements"):
        if not entry[key] or PLACEHOLDER_RE.match(entry[key]):
            return None, True
    if min(len(entry["tasks_carried_out"]), len(entry["key_learnings"]), len(entry["tools_used"])) < 2:
        return None, True
    too_short = (
        _words(entry["my_space"]) < 80
        or len(entry["tasks_carried_out"]) < 4
        or len(entry["key_learnings"]) < 3
        or len(entry["tools_used"]) < 4
        or _words(entry["special_achievements"]) < 20
    )
    return entry, too_short


def _as_page_fields(entry: dict) -> dict:
    return {
        "my_space": entry["my_space"],
        "tasks_carried_out": "\n".join(entry["tasks_carried_out"]),
        "key_learnings": "\n".join(entry["key_learnings"]),
        "tools_used": "\n".join(entry["tools_used"]),
        "special_achievements": entry["special_achievements"],
    }


def _generate_batch(api_key: str, timeline: str, day_numbers: list, on_retry=None) -> dict:
    """Write entries for the given day numbers, retrying days that come back missing, empty or thin."""
    done, fallback = {}, {}
    pending = list(day_numbers)
    for attempt in range(MAX_ATTEMPTS):
        prompt = JOURNAL_PROMPT.format(timeline=timeline, days=", ".join(f"Day {d}" for d in pending))
        for raw in call_gemini(api_key, prompt, list[JournalEntry], on_retry):
            day = raw.get("day")
            if day not in pending or day in done:
                continue
            entry, too_short = _check_entry(raw)
            if entry and not too_short:
                done[day] = entry
            elif entry:
                fallback.setdefault(day, entry)  # usable, just shorter than asked; keep in case retries don't do better
        pending = [d for d in pending if d not in done]
        if not pending:
            break
    for day in pending:
        if day in fallback:
            done[day] = fallback[day]
    return done


def generate_all_journals(api_key: str, daily_data: list, on_progress=None, on_retry=None) -> list:
    """Return one page-ready entry per item in daily_data, in order. Raises GeminiError on failure.

    on_progress(done, total) is called as batches finish; on_retry(seconds) before waiting out a
    rate limit or overload, so the caller can tell the user why nothing is moving.
    """
    timeline = "\n".join(f"Day {d['day']} ({d['date']}): {d['work']}" for d in daily_data)
    day_numbers = [d["day"] for d in daily_data]
    batches = [day_numbers[i:i + BATCH_SIZE] for i in range(0, len(day_numbers), BATCH_SIZE)]

    results = {}
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as pool:
        futures = [pool.submit(_generate_batch, api_key, timeline, batch, on_retry) for batch in batches]
        for future in as_completed(futures):
            results.update(future.result())
            if on_progress:
                on_progress(len(results), len(day_numbers))

    missing = [d for d in day_numbers if d not in results]
    if missing:
        raise GeminiError(
            f"Gemini couldn't write {len(missing)} of {len(day_numbers)} days "
            f"(day {', '.join(map(str, missing[:5]))}{'…' if len(missing) > 5 else ''}). Please try again."
        )
    return [_as_page_fields(results[d]) for d in day_numbers]
