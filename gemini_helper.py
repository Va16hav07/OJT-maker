import json
import os
import re
import time
from datetime import datetime

from google import genai
from google.genai import errors, types

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")


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


def call_gemini(api_key, prompt, retries=3):
    client = genai.Client(api_key=api_key)
    for i in range(retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    top_p=0.9,
                    response_mime_type="application/json",
                ),
            )
            text = response.text.strip()
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return text

        except errors.APIError as e:
            if e.code == 429:
                time.sleep(40)
            else:
                raise e
    raise Exception("Gemini failed after retries")

def split_work_into_days(api_key: str, work_description: str, dates: list, num_days: int) -> list:
    prompt = f"""
You are a professional OJT training supervisor.

Divide the following work into EXACTLY {num_days} day-wise entries.

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

OUTPUT JSON ONLY:
[
  {{ "day": 1, "work": "..." }}
]

WORK:
{work_description}
"""

    text = call_gemini(api_key, prompt)

    daily_splits = json.loads(text)

    result = []
    for i, item in enumerate(daily_splits[:num_days]):
        formatted_date = format_date(dates[i]) if i < len(dates) else ""
        result.append({
            "day": i + 1,
            "date": formatted_date,
            "work": item["work"]
        })

    return result

def generate_all_journals(api_key: str, daily_data: list) -> list:
    combined_input = "\n".join([
        f"Day {d['day']} ({d['date']}): {d['work']}"
        for d in daily_data
    ])

    prompt = f"""
Generate professional OJT daily journal entries for college students.

RULES:
- Each day must be unique
- No repetition
- No HR/company content
- Keep concise and realistic
- Avoid professional/enterprise tools (no Jira, Azure, Salesforce, etc.)
- Use college-friendly tools: Python, JavaScript, Git, SQL, VS Code, Linux, React, etc.

For EACH day return:
- my_space: Minimum 4 lines of detailed personal reflection
- tasks_carried_out: List items separated by NEWLINE (NOT array)
- key_learnings: List items separated by NEWLINE (NOT array)
- tools_used: comma-separated list
- special_achievements: 1-2 lines (NEVER "N/A")

OUTPUT JSON (use plain text with newlines for multi-line fields):
[
  {{
    "day": 1,
    "my_space": "reflection text",
    "tasks_carried_out": "Task 1\\nTask 2\\nTask 3",
    "key_learnings": "Learning 1\\nLearning 2",
    "tools_used": "tool1, tool2, tool3",
    "special_achievements": "achievement text"
  }}
]

INPUT:
{combined_input}
"""

    text = call_gemini(api_key, prompt)

    return json.loads(text)

