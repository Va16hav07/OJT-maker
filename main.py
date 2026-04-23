import io
import os
import sys
import uuid
import threading
import tempfile
import traceback
import time
from datetime import datetime, timedelta

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil.parser import parse as parse_date
import PyPDF2
from starlette.exceptions import HTTPException as StarletteHTTPException

from gemini_helper import split_work_into_days, generate_journal_entry, generate_all_journals
from pdf_filler import fill_pdf_with_overlay

# Set temp directory for Vercel
if 'VERCEL' in os.environ:
    tempfile.tempdir = '/tmp'

app = FastAPI(title="OJT Journal Maker")

# Configure for larger uploads (50MB limit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler for large uploads
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    if exc.status_code == 413:
        return JSONResponse(
            status_code=413,
            content={"error": "File too large. Maximum upload size is 50MB. Please use a smaller PDF or compress it."}
        )
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})

# In-memory task storage
tasks: dict = {}
task_files: dict = {}  # task_id -> temp file path
task_timestamps: dict = {}  # task_id -> creation time (for cleanup)

TASK_TTL_SECONDS = 3600  # Clean up tasks older than 1 hour


def cleanup_old_tasks():
    """Remove tasks and temp files older than TASK_TTL_SECONDS."""
    now = time.time()
    stale = [tid for tid, ts in list(task_timestamps.items()) if now - ts > TASK_TTL_SECONDS]
    for tid in stale:
        path = task_files.pop(tid, None)
        if path and os.path.exists(path):
            try:
                os.unlink(path)
            except OSError:
                pass
        tasks.pop(tid, None)
        task_timestamps.pop(tid, None)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def get_working_days(start: datetime, end: datetime, skip: list) -> list:
    """Return list of date strings (YYYY-MM-DD) for Mon-Fri between start and end, excluding skip."""
    skip_set = set()
    for s in skip:
        s = s.strip()
        if s:
            try:
                skip_set.add(parse_date(s).date())
            except Exception:
                pass

    days = []
    current = start.date()
    end_date = end.date()
    while current <= end_date:
        if current.weekday() < 5 and current not in skip_set:
            days.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return days


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

def generate_pdf_background(task_id: str, api_key: str):
    """Background thread: generate all journal entries and fill PDF."""
    task = tasks.get(task_id)
    if not task:
        return

    try:
        task["status"] = "generating"
        task["progress"] = 0
        daily_work = task["daily_work"]
        pdf_bytes = task["pdf_bytes"]
        ojt_timing = task["ojt_timing"]
        department = task["department"]
        designation = task["designation"]
        user_details = task.get("user_details", {})
        journal_start_page = task.get("journal_start_page", 8)
        journal_end_page = task.get("journal_end_page")
        total = len(daily_work)

        # STEP 1: Generate ALL entries in ONE API call
        task["message"] = "Generating all journal entries..."
        print(f"[Task {task_id}] Generating all entries in one call...")

        try:
            all_entries = generate_all_journals(api_key, daily_work)
            print(f"[Task {task_id}] All entries generated successfully")
        except Exception as exc:
            print(f"[Task {task_id}] ERROR (batch): {exc}")
            print(traceback.format_exc())

            # fallback: create basic entries
            all_entries = []
            for day_item in daily_work:
                all_entries.append({
                    "my_space": "Worked on assigned tasks for the day.",
                    "tasks_carried_out": day_item["work"],
                    "key_learnings": "Gained practical experience.",
                    "tools_used": "Various tools",
                    "special_achievements": "N/A",
                })

        # STEP 2: Build pages_data locally (NO API CALLS HERE)
        pages_data = []

        for i, day_item in enumerate(daily_work):
            task["current_page"] = i + 1
            task["message"] = f"Processing page {i + 1} of {total}..."

            entry = all_entries[i]

            pages_data.append({
                "date": day_item["date"],
                "ojt_timing": ojt_timing,
                "department": department,
                "designation": designation,
                "my_space": entry.get("my_space", ""),
                "tasks_carried_out": entry.get("tasks_carried_out", ""),
                "key_learnings": entry.get("key_learnings", ""),
                "tools_used": entry.get("tools_used", ""),
                "special_achievements": entry.get("special_achievements", ""),
            })

            task["progress"] = int(((i + 1) / total) * 100)

        task["message"] = "Filling PDF template..."
        print(f"[Task {task_id}] {task['message']}")
        filled_pdf = fill_pdf_with_overlay(
            pdf_bytes, pages_data, user_details,
            journal_start_page=journal_start_page,
            journal_end_page=journal_end_page
        )
        print(f"[Task {task_id}] PDF filled successfully")

        # Write to a temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(filled_pdf)
        tmp.flush()
        tmp.close()

        task_files[task_id] = tmp.name
        task["status"] = "done"
        task["progress"] = 100
        task["message"] = "PDF generated successfully!"
        print(f"[Task {task_id}] COMPLETE - File saved to {tmp.name}")

    except Exception as e:
        task["status"] = "error"
        task["message"] = str(e)
        print(f"[Task {task_id}] FAILED: {e}")
        print(traceback.format_exc())


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    task_id: str
    api_key: str
    daily_work: list  # [{day, date, work}, ...]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/upload")
async def upload(
    pdf_file: UploadFile = File(...),
    start_date: str = Form(...),
    end_date: str = Form(...),
    skip_dates: str = Form(""),
    ojt_timing: str = Form(...),
    department: str = Form(...),
    designation: str = Form(...),
    name: str = Form(default=""),
    registration_number: str = Form(default=""),
    program_name: str = Form(default=""),
    semester: str = Form(default=""),
    location: str = Form(default=""),
    industry_partner_name: str = Form(default=""),
    phone_no: str = Form(default=""),
    email_id: str = Form(default=""),
    journal_page_type: str = Form(default="all"),
    journal_custom_range: str = Form(default=""),
    work_description: str = Form(...),
    api_key: str = Form(...),
):
    # Opportunistically clean up old tasks on each upload
    cleanup_old_tasks()

    try:
        # Parse dates
        start_dt = parse_date(start_date)
        end_dt = parse_date(end_date)
        if end_dt < start_dt:
            return JSONResponse(status_code=400, content={"error": "end_date must be after start_date"})

        skip_list = [s.strip() for s in skip_dates.split(",") if s.strip()] if skip_dates else []
        working_days = get_working_days(start_dt, end_dt, skip_list)

        if not working_days:
            return JSONResponse(status_code=400, content={"error": "No working days found in the given range."})

        num_days = len(working_days)

        # Read PDF
        pdf_bytes = await pdf_file.read()

        # Get page count using PyPDF2
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": "Invalid PDF file: " + str(e)})

        # Validate N <= PDF page count
        if num_days > page_count:
            return JSONResponse(
                status_code=400,
                content={
                    "error": (
                        f"The selected date range produces {num_days} working days, "
                        f"but the uploaded PDF has only {page_count} page(s). "
                        "Please upload a PDF with more pages or shorten the date range."
                    )
                },
            )

        # Parse journal pages
        journal_start_page = 8
        journal_end_page = None
        if journal_page_type == "custom" and journal_custom_range:
            parts = journal_custom_range.split("-")
            try:
                journal_start_page = int(parts[0].strip())
                if len(parts) > 1 and parts[1].strip():
                    journal_end_page = int(parts[1].strip())
            except ValueError:
                pass

        # Split work into days via Gemini
        daily_work = split_work_into_days(api_key, work_description, working_days, num_days)

        task_id = str(uuid.uuid4())
        tasks[task_id] = {
            "status": "pending",
            "pdf_bytes": pdf_bytes,
            "working_days": working_days,
            "daily_work": daily_work,
            "ojt_timing": ojt_timing,
            "department": department,
            "designation": designation,
            "user_details": {
                "name": name,
                "registration_number": registration_number,
                "start_date": start_date,
                "program_name": program_name,
                "semester": semester,
                "location": location,
                "industry_partner_name": industry_partner_name,
                "phone_no": phone_no,
                "email_id": email_id,
            },
            "journal_start_page": journal_start_page,
            "journal_end_page": journal_end_page,
            "progress": 0,
            "total_pages": num_days,
            "current_page": 0,
            "message": "Ready to generate.",
        }
        task_timestamps[task_id] = time.time()

        return {
            "task_id": task_id,
            "working_days": working_days,
            "total_days": num_days,
            "pdf_pages": page_count,
            "daily_work": daily_work,
        }

    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception:
        return JSONResponse(status_code=500, content={"error": traceback.format_exc()})


@app.post("/generate")
async def generate(req: GenerateRequest):
    task = tasks.get(req.task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Task not found"})

    # Update daily_work with user edits
    task["daily_work"] = req.daily_work
    task["status"] = "pending"
    task["progress"] = 0
    task["current_page"] = 0
    task["message"] = "Starting generation…"

    thread = threading.Thread(
        target=generate_pdf_background,
        args=(req.task_id, req.api_key),
        daemon=True,
    )
    thread.start()

    return {"task_id": req.task_id, "status": "generating"}


@app.get("/status/{task_id}")
async def get_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    return {
        "task_id": task_id,
        "status": task["status"],
        "progress": task["progress"],
        "current_page": task["current_page"],
        "total_pages": task["total_pages"],
        "message": task.get("message", ""),
    }


@app.get("/download/{task_id}")
async def download(task_id: str):
    task = tasks.get(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    if task["status"] != "done":
        return JSONResponse(status_code=400, content={"error": "PDF not ready yet"})

    file_path = task_files.get(task_id)
    if not file_path or not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File not found"})

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"ojt_journal_{task_id[:8]}.pdf",
    )


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/download-template")
async def download_template():
    """Download the template PDF if it exists."""
    template_path = "ojt_template.pdf"
    if os.path.exists(template_path):
        return FileResponse(
            path=template_path,
            media_type="application/pdf",
            filename="ojt_template.pdf",
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"error": "Template PDF not available. Please upload ojt_template.pdf to the deployment or use your own PDF template."}
        )


app.mount("/static", StaticFiles(directory="static"), name="static")
