# OJT Journal Maker

A **Daily Activity Journal PDF Auto-Filler** powered by Google Gemini AI. Upload your OJT (On-the-Job Training) PDF template, describe your internship work, and the app intelligently splits it into per-day entries, generates professional journal content, and fills every page of your PDF—automatically.

---

## ✨ Features

- **AI-Powered Content Generation** – Google Gemini 1.5 Flash writes realistic, professional daily journal entries based on your overall work description.
- **Smart Work Splitting** – Automatically divides your internship work across all working days (Mon–Fri), respecting holidays/skip dates.
- **PDF Template Filling** – Overlays generated text onto your existing PDF template using coordinate detection and text-label scanning.
- **3-Step Wizard UI** – Clean dark-themed single-page app: upload → review → download.
- **Editable Previews** – Review and edit AI-generated daily work before PDF generation.
- **Progress Tracking** – Real-time progress bar while the PDF is being generated in the background.

---

## 🗂 File Structure

```
OJT-Pranjal/
├── main.py             # FastAPI backend (API endpoints + background task)
├── gemini_helper.py    # Google Gemini API integration
├── pdf_filler.py       # PDF overlay filling (ReportLab + PyPDF2)
├── requirements.txt    # Python dependencies
├── static/
│   └── index.html      # Single-page frontend (vanilla HTML5/CSS3/JS)
└── README.md
```

---

## ⚙️ Setup & Installation

### Prerequisites
- **Python 3.8 or higher** installed on your system.
- **Git** (optional, for cloning the repository).

### 1. Clone the Repository
```bash
git clone https://github.com/Va16hav07/OJT-maker.git
cd OJT-maker
```

### 2. Create and Activate Virtual Environment

#### 🐧 Linux & 🍎 macOS
```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate
```

#### 🪟 Windows
```bash
# Create venv
python -m venv venv

# Activate venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
You can either paste your API key directly into the application UI or set it in a `.env` file:
1. Copy `.env.example` to `.env`:
   - **Linux/macOS:** `cp .env.example .env`
   - **Windows:** `copy .env.example .env`
2. Open `.env` and add your **GEMINI_API_KEY**.
   - Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey).

### 5. Run the Server
```bash
uvicorn main:app --reload
```
The app will be available at **http://localhost:8000**.

---

## 🚀 How to Use

### Step 1 – Upload & Configure
1. Open **http://localhost:8000** in your browser.
2. Drag-and-drop (or click to upload) your OJT journal **PDF template**. 
   - *Note: You can download the default template `ojt_template.pdf` from the "Start Over" screen if needed.*
3. Fill in:
   - **Start Date / End Date** – your internship period.
   - **Skip Dates** *(optional)* – holidays or leave days, comma-separated (e.g. `2024-12-25, 2025-01-01`).
   - **OJT Timing** – e.g. `8:00 AM – 5:00 PM`.
   - **Department** and **Designation**.
   - **Work Description** – a paragraph or more describing everything you did during the internship.
   - **Gemini API Key** – your key from Google AI Studio.
4. Click **Upload & Process**. Gemini will split your work description into daily tasks.

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
| **AI**        | Google Gemini 1.5 Flash (`google-generativeai`) |
| **PDF Processing** | ReportLab (drawing) + PyPDF2 (merging/reading) |
| **Frontend**  | Vanilla HTML5 / CSS3 / JavaScript |

---

## 📝 Notes

- The app fills PDFs using a **text overlay** strategy. It first tries to detect field labels in the PDF using AcroForm metadata, then falls back to hardcoded A4 coordinate positions.
- If the PDF template has more pages than working days, the extra pages are left blank.
- The date range must have at least as many pages in the PDF as there are working days.
- All processing is done locally except for the Gemini API calls.
