# OJT Journal Maker

Fill your OJT (On-the-Job Training) daily journal PDF automatically. Upload your template, describe your internship work, and AI writes one entry per day straight onto the PDF pages.

Works with **Google Gemini** or **OpenRouter**.

---

## ⚙️ Setup

You need **Python 3.10 or newer**. Check with `python3 --version` (macOS/Linux) or `py --version` (Windows).

**1. Download the project**
```bash
git clone https://github.com/Va16hav07/OJT-maker.git
cd OJT-maker
```

**2. Install**

Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Windows:
```powershell
py -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
```

**3. Run**

Linux / macOS:
```bash
python -m uvicorn main:app --reload
```

Windows:
```powershell
venv\Scripts\python -m uvicorn main:app --reload
```

Open **http://localhost:8000** in your browser.

---

## 🔑 API Key

You need a key from **one** of these:

- **Google Gemini** (free): [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **OpenRouter** (free models available): [openrouter.ai/keys](https://openrouter.ai/keys)

**Paste your key in the app, under "AI provider".** Don't put it in a `.env` file or environment variable, because the app doesn't read keys from there. Your key is only used for that request and is never saved.

---

## 🚀 How to Use

1. **Upload** your journal PDF template. If you don't have one, use the **Default template PDF** link on the page.
2. **Fill in** your dates, the days to skip, OJT timing, department, designation and a description of your work.
3. **Choose an AI provider** and paste your API key. Leave the model field blank to use the default. For OpenRouter, the default is a free model.
4. Click **Split my work into days**, then check and edit each day.
5. Click **Generate PDF**, wait for it to finish, and **download** your journal.

---

## ❓ Troubleshooting

- **Install error about Python version:** install Python 3.10+, delete the `venv` folder and install again.
- **`uvicorn` not found:** use the `python -m uvicorn …` command shown above.
- **Port 8000 in use:** add `--port 8001` and open http://localhost:8001.
- **API key rejected:** make sure the key matches the provider you picked. Gemini keys start with `AIza` and OpenRouter keys start with `sk-or-`.
- **Rate limit / quota reached:** wait a minute and try again, or switch provider.
- **OpenRouter out of credits:** add credits, or type a free model ending in `:free` in the model field.

---

## ☕ Support

If this project helps you, you can support it here:
[buymeachai.in/va16hav](https://buymeachai.in/va16hav)
