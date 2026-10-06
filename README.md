# OJT Journal Maker

A **Daily Activity Journal PDF Auto-Filler** powered by Google Gemini AI. Upload your OJT (On-the-Job Training) PDF template, describe your internship work, and the app intelligently splits it into per-day entries, generates professional journal content, and fills every page of your PDF—automatically.

---

## ✨ Features

- **AI-Powered Content Generation** – Google Gemini (Flash-Lite) writes realistic, professional daily journal entries based on your overall work description.
- **Smart Work Splitting** – Automatically divides your internship work across every day in your date range, excluding the holidays/leave days you choose to skip.
- **PDF Template Filling** – Overlays generated text onto your existing PDF template using coordinate detection and text-label scanning.
- **3-Step Wizard UI** – Clean dark-themed single-page app: upload → review → download.
- **Editable Previews** – Review and edit AI-generated daily work before PDF generation.
- **Progress Tracking** – Real-time progress bar while the PDF is being generated in the background.

---

## 🗂 File Structure

```
OJT-maker/
├── main.py             # FastAPI backend (API endpoints + background task)
├── api/
│   └── main.py         # Vercel entrypoint (re-exports the app from main.py)
├── vercel.json         # Vercel deployment config
├── gemini_helper.py    # Google Gemini API integration
├── pdf_filler.py       # PDF overlay filling (ReportLab + pypdf)
├── requirements.txt    # Python dependencies
├── static/
│   └── index.html      # Single-page frontend (vanilla HTML5/CSS3/JS)
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- **Python 3.10 or newer.** Older versions can't install the dependencies. Check with `python3 --version` (macOS/Linux) or `py --version` (Windows).
  - **macOS:** the built-in `python3` is often 3.9. Install a newer one from [python.org](https://www.python.org/downloads/) or with `brew install python@3.12`. If `python3 --version` still shows 3.9 afterwards, use `python3.12` in place of `python3` in step 2.
  - **Windows:** install from [python.org](https://www.python.org/downloads/) (tick **"Add python.exe to PATH"**). If typing `python` opens the Microsoft Store, use the `py` command shown below instead.
- **Git** (optional, for cloning the repository).

### 1. Clone the Repository
```bash
git clone https://github.com/Va16hav07/OJT-maker.git
cd OJT-maker
```

### 2. Create a Virtual Environment and Install Dependencies

#### 🐧 Linux & 🍎 macOS
```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

#### 🪟 Windows (PowerShell or Command Prompt)
```powershell
py -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
```
These commands call the venv's Python directly, so you don't need to activate it. That avoids PowerShell's *"running scripts is disabled on this system"* error.

### 3. Get a Gemini API Key
Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey). You paste it into the app's form; it is not read from the environment.

Optionally, set `GEMINI_MODEL` in your environment to use a different Gemini model (default: `gemini-3.5-flash-lite`). See `.env.example`.

### 4. Run the Server

**Linux & macOS** (with the venv activated):
```bash
python -m uvicorn main:app --reload
```

**Windows:**
```powershell
venv\Scripts\python -m uvicorn main:app --reload
```

The app will be available at **http://localhost:8000**.

### Troubleshooting
- **`ERROR: ... requires a different Python` during install:** your Python is older than 3.10. Install a newer one (see Prerequisites), delete the `venv` folder and repeat step 2.
- **`'uvicorn' is not recognized` / `command not found: uvicorn`:** run it through Python as shown above (`python -m uvicorn …`).
- **Windows: `running scripts is disabled on this system`:** use the `venv\Scripts\python …` commands above instead of activating the venv.
- **Port 8000 already in use:** add `--port 8001` and open http://localhost:8001.

---

## 🚀 How to Use

### Step 1 – Upload & Configure
1. Open **http://localhost:8000** in your browser.
2. Drag-and-drop (or click to upload) your OJT journal **PDF template**. 
   - *No template? Use the **Default template PDF** link at the top of the page.*
3. Fill in:
   - **Start Date / End Date** – your internship period.
   - **Days to Skip** *(optional)* – pick holidays or leave days from the calendar.
   - **OJT Timing** – e.g. `8:00 AM – 5:00 PM`.
   - **Department** and **Designation**.
   - **Work Description** – a paragraph or more describing everything you did during the internship.
   - **Gemini API Key** – your key from Google AI Studio.
4. Click **Split my work into days**. Gemini will split your work description into daily tasks.

### Step 2 – Review Daily Work
- A scrollable list of day cards appears, one per working day.
- Each card shows the date and an editable textarea with the AI-generated work for that day.
- Edit any entry as needed.
- Click **✨ Generate PDF** when ready.

### Step 3 – Generate & Download
- A progress bar tracks each journal entry being generated and filled into the PDF.
- When complete, click **⬇️ Download PDF** to save your finished journal.
- Click **↩ Start Over** to begin a new session.

---

## 🛠 Tech Stack

| Layer     | Technology |
|-----------|-----------|
| **Backend**   | FastAPI, Uvicorn |
| **AI**        | Google Gemini Flash-Lite (`google-genai`) |
| **PDF Processing** | ReportLab (drawing) + pypdf (merging/reading) |
| **Frontend**  | Vanilla HTML5 / CSS3 / JavaScript |

---

## 📝 Notes

- The app fills PDFs using a **text overlay** strategy. Text is drawn at fixed A4 coordinate positions, scaled to each page's size.
- If the PDF template has more pages than working days, the extra pages are left blank.
- The date range must have at least as many pages in the PDF as there are working days.
- All processing is done locally except for the Gemini API calls.

---

## ☕ Support

If this project helps you, you can support it here:  
[buymeachai.in/va16hav](https://buymeachai.in/va16hav)
